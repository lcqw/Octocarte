#!/usr/bin/env python3
"""Fresh five-service package check. Uses generated accounts/music; no Apple login.

The only deployment overrides isolate names, ports, data and the Docker socket.
Never points to existing services or a user's configuration/library.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('package', type=Path)
args = parser.parse_args()
package = args.package.resolve()
images = json.loads((package / 'images.lock.json').read_text())['images']
project = 'octocarte-package-test-' + secrets.token_hex(4)


def run(*args):
    return subprocess.run(args, check=True, stdout=subprocess.DEVNULL)


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
            if request(base, path)[0] == 200:
                return
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            pass
        time.sleep(0.5)
    raise RuntimeError('Disposable service did not become ready')


with tempfile.TemporaryDirectory(prefix=project) as directory:
    root = Path(directory)
    state, music = root / 'data', root / 'music'
    music.mkdir(mode=0o755)
    # Prepare an owned token so the test can assert identity without exposing it.
    spec = importlib.util.spec_from_file_location('initialize', package / 'initialize.py')
    initializer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(initializer)
    initializer.initialize(state, os.getuid(), os.getgid())
    token_path = state / 'secrets/alacarte-integration/token'
    token = token_path.read_text().strip()
    fake_socket = root / 'disabled-docker-socket'
    fake_socket.touch()
    settings = root / 'settings.env'
    settings.write_text(f'DATA_DIR={state}\nMUSIC_DIR={music}\nHOST_BIND=127.0.0.1\n'
                        f'NAVIDROME_UID={os.getuid()}\nNAVIDROME_GID={os.getgid()}\n'
                        f'CONTAINER_SOCKET={fake_socket}\nOCTOCARTE_PORT=0\nNAVIDROME_PORT=0\nALACARTE_PORT=0\n')
    override = root / 'isolation.json'
    override.write_text(json.dumps({'services': {'wrapper': {
        'container_name': project + '-wrapper',
        'networks': {'default': {'aliases': ['alacarte-wrapper']}}
    }}}))
    common = ['docker', 'compose', '-p', project, '--env-file', str(package / 'images.env'), '--env-file', str(settings)]
    compose = common + ['-f', str(package / 'compose.yml'), '-f', str(override)]
    try:
        run(*(common + ['-f', str(package / 'initialize.compose.yml'), 'run', '--rm', 'initialize']))
        assert token_path.read_text().strip() == token, 'Initialization rotated an existing token'
        # Generate a real, silent ALAC file as a harmless shared-storage fixture.
        run('docker', 'run', '--rm', '--network', 'none', '-v', str(music) + ':/music', images['SHIM_IMAGE']['tag'],
            'ffmpeg', '-loglevel', 'error', '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo', '-t', '2',
            '-c:a', 'alac', '-metadata', 'title=Octocarte storage fixture', '-metadata', 'artist=Fixture Artist',
            '-metadata', 'album=Fixture Album', '/music/fixture.m4a')
        run(*(compose + ['up', '-d']))
        def address(service, port):
            value = subprocess.check_output(compose + ['port', service, str(port)], text=True).strip()
            return 'http://' + value
        nav, apple, proxy = address('navidrome', 4533), address('alacarte', 7373), address('octocarte', 8080)
        ready(nav, '/ping')
        ready(apple, '/api/auth/state')
        account = {'username': 'package-test', 'password': secrets.token_urlsafe(32)}
        assert request(nav, '/auth/createAdmin', account)[0] == 200, 'Fresh Navidrome account setup failed'
        salt = secrets.token_hex(8)
        auth = {'u': account['username'], 't': hashlib.md5((account['password'] + salt).encode()).hexdigest(),
                's': salt, 'v': '1.16.1', 'c': 'package-test', 'f': 'json'}
        def sub(path, **params):
            status, _, body = request(proxy, '/rest/' + path + '?' + urllib.parse.urlencode(auth | params))
            assert status == 200, 'Proxy HTTP request failed'
            result = json.loads(body)['subsonic-response']
            assert result['status'] == 'ok', 'Proxy Subsonic request failed'
            return result
        ready(proxy, '/rest/ping?' + urllib.parse.urlencode(auth))
        sub('ping')
        search = sub('search3', query='Kid Cudi', artistCount=5, songCount=5, albumCount=5)['searchResult3']
        assert any(a['id'].startswith('ext-apple-artist-') for a in search.get('artist', [])), 'Apple search absent'
        songs = sub('getTopSongs', artist='Kid Cudi', count=5)['topSongs']['song']
        assert len(songs) == 5, 'Included ranked top songs absent'
        artist = next(a for a in search['artist'] if a.get('name', '').lower() == 'kid cudi')
        info = sub('getArtistInfo2', id=artist['id'])['artistInfo2']
        assert info.get('largeImageUrl'), 'Included artist image absent'
        assert request(apple, '/api/settings', headers={'Authorization': 'Bearer ' + token})[0] == 403
        sub('startScan')
        local = []
        for _ in range(60):
            local = sub('search3', query='Octocarte storage fixture', songCount=10)['searchResult3'].get('song', [])
            local = [song for song in local if not song['id'].startswith('ext-')]
            if local:
                break
            time.sleep(0.5)
        assert local, 'Navidrome did not index the shared music mount'
        stream_path = '/rest/stream?' + urllib.parse.urlencode(auth | {'id': local[0]['id'], 'format': 'raw'})
        status, headers, body = request(proxy, stream_path, headers={'Range': 'bytes=0-127'})
        assert status == 206 and len(body) == 128 and headers.get('Content-Range', '').startswith('bytes 0-127/'), 'Native range playback failed'
        run(*(compose + ['restart', 'alacarte', 'octocarte']))
        # Docker can allocate new ephemeral host ports on restart.
        apple, proxy = address('alacarte', 7373), address('octocarte', 8080)
        ready(apple, '/api/auth/state')
        ready(proxy, '/rest/ping?' + urllib.parse.urlencode(auth))
        assert token_path.read_text().strip() == token
        assert len(sub('getTopSongs', artist='Kid Cudi', count=5)['topSongs']['song']) == 5
        print('PASS: fresh Compose initialization, account setup, Apple search/photos/top songs, scoped auth, shared ALAC storage, native Range playback and restart persistence.')
        print('Apple account login/downloads were not repeated; the existing acquisition HTTP fixture covers album submission.')
    finally:
        subprocess.run(compose + ['down', '--remove-orphans'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Generated container-owned state only, never user data.
        run('docker', 'run', '--rm', '--network', 'none', '-v', str(root) + ':/test-state', images['SHIM_IMAGE']['tag'],
            'python', '-c', "import shutil; shutil.rmtree('/test-state/data', ignore_errors=True); shutil.rmtree('/test-state/music', ignore_errors=True)")
