#!/usr/bin/env python3
"""Test Octocarte lifecycle alongside an independently managed disposable Navidrome.

No user services, music, Apple login or credentials are accessed.
"""
import argparse
import hashlib
import io
import tarfile
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-archive', type=Path, help='verify source offer against this build artifact')
parser.add_argument('--image-base', default='octocarte')
parser.add_argument('--version', default=(ROOT / 'VERSION').read_text().strip())
args = parser.parse_args()
project = 'octocarte-install-test-' + secrets.token_hex(4)
shim_image = args.image_base + '-shim:' + args.version


def run(command):
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL)


def output(command):
    return subprocess.check_output(command, text=True).strip()


def request(base, path, data=None, headers=None):
    req = urllib.request.Request(base + path, data=json.dumps(data).encode() if data is not None else None,
                                 headers={'Content-Type': 'application/json', **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=40) as response:
            return response.status, response.headers, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.headers, error.read()


def ready(base, path):
    for _ in range(120):
        try:
            if request(base, path)[0] == 200: return
        except (urllib.error.URLError, TimeoutError, ConnectionError): pass
        time.sleep(0.5)
    raise RuntimeError('Disposable service did not become ready')


with tempfile.TemporaryDirectory(prefix=project) as temp:
    root = Path(temp)
    music = root / 'music'
    music.mkdir(mode=0o755)
    socket_file = root / 'disabled-docker-socket'
    socket_file.touch()
    settings = root / '.env'
    settings.write_text(f'MUSIC_DIR={music}\nHOST_BIND=127.0.0.1\nCONTAINER_SOCKET={socket_file}\n'
                        f'OCTOCARTE_IMAGE_BASE={args.image_base}\nOCTOCARTE_VERSION={args.version}\n'
                        'OCTOCARTE_PORT=0\nALACARTE_PORT=0\nNAVIDROME_URL=http://navidrome:4533\n'
                        f'NAVIDROME_UID={os.getuid()}\nNAVIDROME_GID={os.getgid()}\n')
    isolation = root / 'isolation.json'
    isolation.write_text(json.dumps({'services': {'wrapper': {
        'container_name': project + '-wrapper', 'networks': {'default': {'aliases': ['alacarte-wrapper']}}
    }}, 'networks': {'default': {'external': True, 'name': project + '-nav_default'}}}))
    common = ['docker', 'compose', '-p', project, '--env-file', str(settings)]
    existing = ['docker', 'compose', '-p', project + '-nav', '-f', str(root / 'existing.json')]
    data = root / 'navidrome'
    data.mkdir(mode=0o755)
    (root / 'existing.json').write_text(json.dumps({'services': {'navidrome': {
        'image': 'deluan/navidrome:0.63.2', 'user': f'{os.getuid()}:{os.getgid()}',
        'ports': ['127.0.0.1:0:4533'], 'environment': {'ND_ENABLEINSIGHTSCOLLECTOR': 'false'},
        'volumes': [f'{data}:/data', f'{music}:/music:ro']
    }}}))
    compose = common + ['-f', str(ROOT / 'compose.yml'), '-f', str(isolation)]
    try:
        run(['docker', 'run', '--rm', '--network', 'none', '-v', str(music) + ':/music', shim_image,
             'ffmpeg', '-loglevel', 'error', '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo', '-t', '2',
             '-c:a', 'alac', '-metadata', 'title=Octocarte storage fixture', '-metadata', 'artist=Fixture Artist',
             '-metadata', 'album=Fixture Album', '/music/fixture.m4a'])
        run(existing + ['up', '-d'])
        nav_before = output(existing + ['ps', '-q', 'navidrome'])
        # This is the complete installation action: no separate init command.
        run(compose + ['up', '-d'])
        assert output(existing + ['ps', '-q', 'navidrome']) == nav_before, 'Existing Navidrome was replaced'
        def address(service, port):
            return 'http://' + output(compose + ['port', service, str(port)])
        nav = 'http://' + output(existing + ['port', 'navidrome', '4533'])
        apple, proxy = address('alacarte', 7373), address('octocarte', 8080)
        ready(nav, '/ping')
        ready(apple, '/api/auth/state')
        if args.source_archive:
            status, headers, source = request(apple, '/octocarte-source.tar.gz')
            assert status == 200 and 'attachment' in headers.get('Content-Disposition', '')
            assert hashlib.sha256(source).digest() == hashlib.sha256(args.source_archive.read_bytes()).digest(), 'Served source differs from build artifact'
            with tarfile.open(fileobj=io.BytesIO(source), mode='r:gz') as archive:
                names = archive.getnames()
                assert 'alacarte/LICENSE' in names and 'alacarte/OCTOCARTE-NOTICE.md' in names
                assert 'alacarte/backend/routes/octocarteSource.mjs' in names
                assert 'alacarte/backend/octocarte-source.tar.gz' not in names
            for service, directory in [('octocarte', 'octocarte'), ('yt-dlp-shim', 'octocarte-shim'), ('alacarte', 'alacarte')]:
                run(compose + ['exec', '-T', service, 'test', '-s', f'/usr/share/doc/{directory}/LICENSE'])
        account = {'username': 'installation-test', 'password': secrets.token_urlsafe(32)}
        assert request(nav, '/auth/createAdmin', account)[0] == 200, 'Navidrome account setup failed'
        salt = secrets.token_hex(8)
        auth = {'u': account['username'], 't': hashlib.md5((account['password'] + salt).encode()).hexdigest(),
                's': salt, 'v': '1.16.1', 'c': 'installation-test', 'f': 'json'}
        ready(proxy, '/rest/ping?' + urllib.parse.urlencode(auth))
        def sub(path, **params):
            status, _, body = request(proxy, '/rest/' + path + '?' + urllib.parse.urlencode(auth | params))
            assert status == 200, 'Proxy HTTP request failed'
            result = json.loads(body)['subsonic-response']
            assert result['status'] == 'ok', 'Proxy Subsonic request failed'
            return result
        def token_fingerprint():
            # A fingerprint only; the generated secret never leaves its container.
            return output(compose + ['exec', '-T', 'alacarte', 'node', '-e',
                "const fs=require('fs'),c=require('crypto');console.log(c.createHash('sha256').update(fs.readFileSync('/run/octocarte-auth/token')).digest('hex'))"])
        fingerprint = token_fingerprint()
        search = sub('search3', query='Kid Cudi', artistCount=5, songCount=5, albumCount=5)['searchResult3']
        artist = next(a for a in search['artist'] if a.get('name', '').lower() == 'kid cudi')
        assert artist['id'].startswith('ext-apple-artist-')
        assert len(sub('getTopSongs', artist='Kid Cudi', count=5)['topSongs']['song']) == 5
        assert sub('getArtistInfo2', id=artist['id'])['artistInfo2'].get('largeImageUrl')
        denied = output(compose + ['exec', '-T', 'alacarte', 'node', '-e',
            "const t=require('fs').readFileSync('/run/octocarte-auth/token','utf8').trim();fetch('http://127.0.0.1:7373/api/settings',{headers:{Authorization:'Bearer '+t}}).then(r=>console.log(r.status))"])
        assert denied == '403', 'Service token granted administrative access'
        sub('startScan')
        local = []
        for _ in range(60):
            tracks = sub('search3', query='Octocarte storage fixture', songCount=10)['searchResult3'].get('song', [])
            local = [song for song in tracks if not song['id'].startswith('ext-')]
            if local: break
            time.sleep(0.5)
        assert local, 'Shared-library fixture was not indexed'
        path = '/rest/stream?' + urllib.parse.urlencode(auth | {'id': local[0]['id'], 'format': 'raw'})
        status, headers, body = request(proxy, path, headers={'Range': 'bytes=0-127'})
        assert status == 206 and len(body) == 128 and headers.get('Content-Range', '').startswith('bytes 0-127/')
        run(compose + ['down'])  # Retain Octocarte volumes; Navidrome must stay running.
        assert output(existing + ['ps', '-q', 'navidrome']) == nav_before, 'Navidrome stopped with Octocarte'
        assert request(nav, '/ping')[0] == 200
        run(compose + ['up', '-d'])
        apple, proxy = address('alacarte', 7373), address('octocarte', 8080)
        ready(apple, '/api/auth/state')
        ready(proxy, '/rest/ping?' + urllib.parse.urlencode(auth))
        assert token_fingerprint() == fingerprint, 'Restart changed integration credentials'
        sub('ping')  # The original Navidrome account still authenticates.
        assert len(sub('getTopSongs', artist='Kid Cudi', count=5)['topSongs']['song']) == 5
        assert output(existing + ['ps', '-q', 'navidrome']) == nav_before, 'Existing Navidrome changed during restart'
        print('PASS: standalone startup, catalog/photos/top songs, scoped token, shared ALAC storage, native ranges and persistent recreation; independent Navidrome unchanged.')
    finally:
        subprocess.run(compose + ['down', '--volumes', '--remove-orphans'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(existing + ['down', '--volumes'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Only this test's generated fixture and disposable Navidrome directory.
        run(['docker', 'run', '--rm', '--network', 'none', '-v', str(root) + ':/test-data', shim_image,
             'python', '-c', "import shutil;shutil.rmtree('/test-data/music',ignore_errors=True);shutil.rmtree('/test-data/navidrome',ignore_errors=True)"])
