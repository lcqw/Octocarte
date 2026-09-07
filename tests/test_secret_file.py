import re
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/create-alacarte-token.py'

class SecretFileTests(unittest.TestCase):
    def test_creation_is_private_and_never_overwrites_or_prints_token(self):
        with tempfile.TemporaryDirectory() as root:
            target = Path(root) / 'secrets' / 'alacarte-token'
            first = subprocess.run([sys.executable, str(SCRIPT), str(target)], capture_output=True, text=True)
            self.assertEqual(first.returncode, 0)
            value = target.read_text().strip()
            self.assertTrue(re.fullmatch(r'[A-Za-z0-9_-]{43}', value))
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(target.parent.stat().st_mode), 0o700)
            self.assertNotIn(value, first.stdout + first.stderr)
            again = subprocess.run([sys.executable, str(SCRIPT), str(target)], capture_output=True, text=True)
            self.assertNotEqual(again.returncode, 0)
            self.assertEqual(target.read_text().strip(), value)
            self.assertNotIn(value, again.stdout + again.stderr)

if __name__ == '__main__':
    unittest.main()
