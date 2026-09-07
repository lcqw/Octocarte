"""Initialize deployment-owned state. Runs in the shim image; emits no secrets."""
import os
from pathlib import Path
import re
import secrets


def initialize(root: Path, uid: int, gid: int):
    root.mkdir(mode=0o750, parents=True, exist_ok=True)
    for name in ('navidrome', 'octocarte', 'alacarte', 'wrapper', 'ytdlp-cache'):
        directory = root / name
        if directory.is_symlink():
            raise ValueError('State subdirectories must not be symbolic links')
        fresh = not directory.exists()
        directory.mkdir(mode=0o750, exist_ok=True)
        if fresh and name == 'navidrome':
            os.chown(directory, uid, gid)
    for directory in (root / 'secrets', root / 'secrets/alacarte-integration'):
        if directory.is_symlink():
            raise ValueError('Secret directories must not be symbolic links')
        directory.mkdir(mode=0o700, exist_ok=True)
        directory.chmod(0o700)
    token = root / 'secrets/alacarte-integration/token'
    try:
        fd = os.open(token, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        if token.is_symlink() or not token.is_file() or token.stat().st_size > 128:
            raise ValueError('Existing integration token is invalid; no token replaced')
        if not re.fullmatch(r'[A-Za-z0-9_-]{43}', token.read_text().strip()):
            raise ValueError('Existing integration token is invalid; no token replaced')
        token.chmod(0o600)
    else:
        with os.fdopen(fd, 'w') as file:
            file.write(secrets.token_urlsafe(32) + '\n')


if __name__ == '__main__':
    initialize(Path('/state'), int(os.environ['NAVIDROME_UID']), int(os.environ['NAVIDROME_GID']))
    print('State directories and private integration token are ready. Existing data retained.')
