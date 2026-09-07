"""Disposable ALACarte service-auth smoke test; no user secrets or downloads."""
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import tempfile
import time
import urllib.request
import urllib.error

name = 'octocarte-auth-smoke-' + secrets.token_hex(4)
with tempfile.TemporaryDirectory(prefix='octocarte-service-secret-') as temp:
    directory = Path(temp)
    token_file = directory / 'token'
    token = secrets.token_urlsafe(32)
    token_file.write_text(token)
    token_file.chmod(0o600)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    base = f'http://127.0.0.1:{port}'
    def status(path, credential=None):
        headers = {'Authorization': 'Bearer ' + credential} if credential else {}
        try:
            with urllib.request.urlopen(urllib.request.Request(base + path, headers=headers), timeout=20) as response:
                response.read()
                return response.status
        except urllib.error.HTTPError as error:
            return error.code
    def ready():
        for _ in range(100):
            try:
                if status('/api/settings') == 401: return
            except (urllib.error.URLError, TimeoutError, ConnectionError): pass
            time.sleep(0.1)
        raise RuntimeError('Disposable ALACarte did not start')
    try:
        subprocess.run(['docker', 'run', '--rm', '-d', '--name', name, '-p', f'127.0.0.1:{port}:7373', '--tmpfs', '/config', '--tmpfs', '/music', '-v', f'{directory}:/run/octocarte-auth:ro', '-e', 'OCTOCARTE_TOKEN_FILE=/run/octocarte-auth/token', '-e', 'AMDL_WRAPPER_HOST=127.0.0.1', os.environ.get('ALACARTE_TEST_IMAGE', 'octocarte-alacarte:auth-candidate')], check=True, stdout=subprocess.DEVNULL)
        ready()
        assert status('/api/search?q=Kid%20Cudi&limit=1&types=artists', token) == 200
        assert status('/api/settings', token) == 403
        subprocess.run(['docker', 'restart', name], check=True, stdout=subprocess.DEVNULL)
        ready()
        assert status('/api/search?q=Kid%20Cudi&limit=1&types=artists', token) == 200
        replacement = secrets.token_urlsafe(32)
        new_file = directory / 'replacement'
        new_file.write_text(replacement)
        new_file.chmod(0o600)
        new_file.replace(token_file)
        assert status('/api/search?q=Kid%20Cudi&limit=1&types=artists', token) == 401
        assert status('/api/search?q=Kid%20Cudi&limit=1&types=artists', replacement) == 200
        token_file.unlink()
        assert status('/api/search?q=Kid%20Cudi&limit=1&types=artists', replacement) == 401
        print('PASS: real isolated ALACarte catalog, admin denial, restart, atomic token rotation and revocation. No download submitted.')
    finally:
        subprocess.run(['docker', 'rm', '-f', name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
