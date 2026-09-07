#!/usr/bin/env python3
"""Create a 256-bit deployment token without printing it or replacing a file."""
import argparse
import os
from pathlib import Path
import secrets

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('path', type=Path, help='new secret file to create')
args = parser.parse_args()
args.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
try:
    fd = os.open(args.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
except FileExistsError:
    parser.exit(1, 'Secret file already exists; nothing changed.\n')
with os.fdopen(fd, 'w') as file:
    file.write(secrets.token_urlsafe(32) + '\n')
print('Secret file created. Its value was not printed.')
