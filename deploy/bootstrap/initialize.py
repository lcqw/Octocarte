"""Initialize Docker-owned state without printing or rotating credentials."""
import fcntl
import os
from pathlib import Path
import re
import secrets
import stat


def initialize(auth: Path, navidrome: Path | None, uid: int, gid: int):
    if uid < 0 or gid < 0:
        raise ValueError('Container user/group IDs must be nonnegative')
    if auth.is_symlink():
        raise ValueError('Authentication storage must be a directory')
    auth.mkdir(mode=0o700, parents=True, exist_ok=True)
    auth.chmod(0o700)
    # Serialize concurrent initialization attempts without logging any credential.
    lock_fd = os.open(auth / '.initialize.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(lock_fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        token = auth / 'token'
        try:
            fd = os.open(token, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            fd = os.open(token, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(fd, 'r') as file:
                details = os.fstat(file.fileno())
                if not stat.S_ISREG(details.st_mode) or details.st_size > 128:
                    raise ValueError('Stored integration token is invalid; it was not replaced')
                if not re.fullmatch(r'[A-Za-z0-9_-]{43}', file.read().strip()):
                    raise ValueError('Stored integration token is invalid; it was not replaced')
                os.fchmod(file.fileno(), 0o600)
        else:
            with os.fdopen(fd, 'w') as file:
                file.write(secrets.token_urlsafe(32) + '\n')
                file.flush()
                os.fsync(file.fileno())
    if navidrome is not None:
        if navidrome.is_symlink():
            raise ValueError('Navidrome storage must be a directory')
        navidrome.mkdir(mode=0o750, parents=True, exist_ok=True)
        # Only this volume's root: never recursively change a library or database.
        os.chown(navidrome, uid, gid)
    print('Service storage is ready. Existing integration credentials retained.')


if __name__ == '__main__':
    nav = os.environ.get('NAVIDROME_DATA_DIR')
    initialize(Path('/auth'), Path(nav) if nav else None,
               int(os.environ.get('NAVIDROME_UID', '1000')),
               int(os.environ.get('NAVIDROME_GID', '10')))
