#!/usr/bin/env python3
"""Build a private AMD64 Compose package with the ALACarte integration included."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ALACARTE_REVISION = 'ef9b677c21b024a0acbf4f88d47c4ebff24802fa'
ALACARTE_URL = 'https://github.com/sosjalapeno/alacarte.git'
PATCHES = ('top-songs.patch', 'service-auth.patch', 'wrapper-image.patch')


def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def output(*args):
    return subprocess.check_output(args, text=True).strip()


def write_image_environment(destination, images):
    # Docker's containerd and classic stores can expose different .Id values
    # for the same archive. RepoTags survive export/import on both stores.
    destination.write_text(''.join(key + '=' + value['tag'] + '\n' for key, value in images.items()))


def archive(source, revision, destination, tar_path):
    run('git', '-C', str(source), 'archive', '--format=tar', '-o', str(tar_path), revision)
    destination.mkdir()
    # Only tracked files from the requested revision enter a build, never local secrets.
    with tarfile.open(tar_path) as archive_file:
        archive_file.extractall(destination, filter='data')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='new directory outside the checkout')
    parser.add_argument('--version', required=True, help='unique candidate version, e.g. nas-preview.1')
    parser.add_argument('--alacarte-source', type=Path, help='reuse a local Git object database (read-only)')
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z0-9][a-z0-9_.-]{0,63}', args.version):
        parser.error('version must be a lowercase Docker tag')
    for name in ('octocarte', 'octocarte-shim', 'octocarte-alacarte', 'octocarte-wrapper'):
        if subprocess.run(['docker', 'image', 'inspect', name + ':' + args.version],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            parser.error('candidate version already exists; choose a new version to retain previous images')
    destination = args.output.resolve()
    if destination == ROOT or ROOT in destination.parents or destination.exists():
        parser.error('output must be a new directory outside the checkout')
    if output('git', '-C', str(ROOT), 'status', '--porcelain'):
        parser.error('commit the candidate first; builds require a clean checkout')
    revision = output('git', '-C', str(ROOT), 'rev-parse', 'HEAD')
    destination.mkdir(parents=True)
    manifest = {'octocarteRevision': revision, 'alacarteRevision': ALACARTE_REVISION,
                'version': args.version, 'platform': 'linux/amd64', 'baseImages': {}, 'images': {}}
    try:
        with tempfile.TemporaryDirectory(prefix='octocarte-build-') as temp_name:
            temp = Path(temp_name)
            app = temp / 'octocarte'
            archive(ROOT, revision, app, destination / 'octocarte-source.tar')
            source = args.alacarte_source
            if source is None:
                source = temp / 'upstream'
                run('git', 'init', '-q', str(source))
                run('git', '-C', str(source), 'fetch', '--depth=1', ALACARTE_URL, ALACARTE_REVISION)
            alacarte = temp / 'alacarte'
            archive(source, ALACARTE_REVISION, alacarte, temp / 'upstream.tar')
            for patch in PATCHES:
                run('git', '-C', str(alacarte), 'apply', str(app / 'integrations/alacarte' / patch))
            # Preserve the upstream build; use its lockfiles and pin resolved base images.
            web_dockerfile = alacarte / 'backend/Dockerfile'
            web_dockerfile.write_text(web_dockerfile.read_text().replace('npm install ', 'npm ci '))
            dockerfiles = [app / 'Dockerfile', app / 'yt-dlp-shim/Dockerfile',
                           web_dockerfile, alacarte / 'wrapper/Dockerfile']
            for dockerfile in dockerfiles:
                text = dockerfile.read_text()
                for base in re.findall(r'^FROM (\S+)', text, flags=re.MULTILINE):
                    if base not in manifest['baseImages']:
                        run('docker', 'pull', '--platform', 'linux/amd64', base)
                        digests = json.loads(output('docker', 'image', 'inspect', base, '--format', '{{json .RepoDigests}}'))
                        if not digests:
                            raise RuntimeError('Base image did not resolve to a registry digest')
                        manifest['baseImages'][base] = digests[0]
                    text = text.replace('FROM ' + base + '\n', 'FROM ' + manifest['baseImages'][base] + '\n')
                    text = text.replace('FROM ' + base + ' AS ', 'FROM ' + manifest['baseImages'][base] + ' AS ')
                dockerfile.write_text(text)
            # Source corresponding to the modified ALACarte image travels with the package.
            with tarfile.open(destination / 'alacarte-source.tar.gz', 'w:gz') as tar:
                tar.add(alacarte, arcname='alacarte')
            builds = [
                ('OCTOCARTE_IMAGE', 'octocarte', app, app / 'Dockerfile'),
                ('SHIM_IMAGE', 'octocarte-shim', app / 'yt-dlp-shim', app / 'yt-dlp-shim/Dockerfile'),
                ('ALACARTE_IMAGE', 'octocarte-alacarte', alacarte, web_dockerfile),
                ('WRAPPER_IMAGE', 'octocarte-wrapper', alacarte / 'wrapper', alacarte / 'wrapper/Dockerfile'),
            ]
            for key, name, context, dockerfile in builds:
                tag = name + ':' + args.version
                run('docker', 'build', '--platform', 'linux/amd64', '-t', tag, '-f', str(dockerfile), str(context))
                manifest['images'][key] = {'tag': tag, 'id': output('docker', 'image', 'inspect', tag, '--format', '{{.Id}}')}
            navidrome = 'deluan/navidrome:0.63.2'
            run('docker', 'pull', '--platform', 'linux/amd64', navidrome)
            manifest['images']['NAVIDROME_IMAGE'] = {'tag': navidrome, 'id': output('docker', 'image', 'inspect', navidrome, '--format', '{{.Id}}')}
            for item in (app / 'deploy').iterdir():
                if item.is_file() and item.name != 'IMPLEMENTATION_PLAN.md':
                    shutil.copy2(item, destination / item.name)
            (destination / 'manage.sh').chmod(0o755)
            write_image_environment(destination / 'images.env', manifest['images'])
            (destination / 'images.lock.json').write_text(json.dumps(manifest, indent=2) + '\n')
            run('docker', 'save', '-o', str(destination / 'images.tar'), *(v['tag'] for v in manifest['images'].values()))
            checksums = []
            for path in sorted(destination.iterdir()):
                if path.is_file():
                    with path.open('rb') as file:
                        digest = hashlib.file_digest(file, 'sha256').hexdigest()
                    checksums.append(digest + '  ' + path.name + '\n')
            (destination / 'SHA256SUMS').write_text(''.join(checksums))
        print('Package built. No services started and no images published.')
    except Exception:
        print('Build incomplete. Output directory retained for inspection; do not install it.')
        raise


if __name__ == '__main__':
    main()
