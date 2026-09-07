#!/usr/bin/env python3
"""Publish previously tested release images and record their registry digests."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('directory', type=Path)
args = parser.parse_args()
manifest = json.loads((args.directory / 'images.lock.json').read_text())
for key, image in manifest['images'].items():
    if key == 'NAVIDROME_IMAGE':
        continue  # Navidrome is consumed directly from its existing official image.
    if not image['tag'].startswith('ghcr.io/'):
        raise SystemExit('Only an explicitly named GHCR release can be published')
    subprocess.run(['docker', 'push', image['tag']], check=True)
    digests = json.loads(subprocess.check_output(['docker', 'image', 'inspect', image['tag'], '--format', '{{json .RepoDigests}}'], text=True))
    repository = image['tag'].rsplit(':', 1)[0]
    matching = [digest for digest in digests if digest.startswith(repository + '@sha256:')]
    if not matching:
        raise SystemExit('Published image registry digest could not be verified')
    image['registryDigest'] = matching[0]
(args.directory / 'images.lock.json').write_text(json.dumps(manifest, indent=2) + '\n')
checksums = []
for path in sorted(args.directory.rglob('*')):
    if path.is_file() and path.name != 'SHA256SUMS':
        with path.open('rb') as file:
            checksum = hashlib.file_digest(file, 'sha256').hexdigest()
        checksums.append(checksum + '  ' + path.relative_to(args.directory).as_posix() + '\n')
(args.directory / 'SHA256SUMS').write_text(''.join(checksums))
