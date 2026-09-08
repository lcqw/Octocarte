#!/usr/bin/env python3
"""Verify the real downloader launch without network, credentials or music writes."""
from pathlib import Path
import subprocess
import sys


def check_downloader_launch(image):
    script = Path(__file__).with_name('downloader_launch.mjs').read_text()
    subprocess.run(['docker', 'run', '--rm', '--network', 'none', '--read-only',
                    '--tmpfs', '/tmp', '-i', '--entrypoint', 'node', image,
                    '--input-type=module'], input=script, text=True, check=True, timeout=35)


if __name__ == '__main__':
    check_downloader_launch(sys.argv[1])
