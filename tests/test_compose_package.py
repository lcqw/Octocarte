"""Deployment contract checks without starting services or accessing user data."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('initialize', ROOT / 'deploy/initialize.py')
initialize = importlib.util.module_from_spec(spec)
spec.loader.exec_module(initialize)


class PackageTests(unittest.TestCase):
    def test_initialization_retains_data_and_credential(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initialize.initialize(root, os.getuid(), os.getgid())
            token = root / 'secrets/alacarte-integration/token'
            first = token.read_bytes()
            sentinel = root / 'navidrome/existing-data'
            sentinel.write_text('retained')
            initialize.initialize(root, os.getuid(), os.getgid())
            self.assertEqual(first, token.read_bytes())
            self.assertEqual(token.stat().st_mode & 0o777, 0o600)
            self.assertEqual(token.parent.stat().st_mode & 0o777, 0o700)
            self.assertEqual(sentinel.read_text(), 'retained')
            token.write_text('invalid')
            with self.assertRaises(ValueError):
                initialize.initialize(root, os.getuid(), os.getgid())
            self.assertEqual(token.read_text(), 'invalid')

    def test_secret_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'outside').mkdir()
            (root / 'secrets').symlink_to(root / 'outside')
            with self.assertRaises(ValueError):
                initialize.initialize(root, os.getuid(), os.getgid())
            self.assertEqual(list((root / 'outside').iterdir()), [])

    def test_compose_storage_and_service_boundaries(self):
        env = dict(os.environ, DATA_DIR='/tmp/octocarte-test-data', MUSIC_DIR='/tmp/octocarte-test-music')
        for key in ('NAVIDROME_IMAGE', 'OCTOCARTE_IMAGE', 'ALACARTE_IMAGE', 'SHIM_IMAGE', 'WRAPPER_IMAGE'):
            env[key] = 'sha256:' + '1' * 64
        config = json.loads(subprocess.check_output(
            ['docker', 'compose', '-f', str(ROOT / 'deploy/compose.yml'), 'config', '--format', 'json'], env=env))
        services = config['services']
        self.assertEqual(set(services), {'navidrome', 'octocarte', 'alacarte', 'wrapper', 'yt-dlp-shim'})
        mounts = lambda name: {m['target']: m for m in services[name]['volumes']}
        self.assertEqual(mounts('navidrome')['/music']['source'], mounts('alacarte')['/music']['source'])
        self.assertTrue(mounts('navidrome')['/music']['read_only'])
        self.assertFalse(mounts('alacarte')['/music'].get('read_only', False))
        self.assertNotIn('/music', mounts('octocarte'))
        self.assertNotIn('/var/run/docker.sock', mounts('octocarte'))
        for name in ('alacarte', 'octocarte'):
            self.assertTrue(mounts(name)['/run/octocarte-auth']['read_only'])
        self.assertEqual(mounts('alacarte')['/run/octocarte-auth']['source'], mounts('octocarte')['/run/octocarte-auth']['source'])
        self.assertNotIn('Alacarte__SessionCookieFile', services['octocarte']['environment'])
        self.assertEqual(services['alacarte']['environment']['AMDL_WRAPPER_IMAGE'], services['wrapper']['image'])
        self.assertEqual(services['wrapper']['container_name'], 'alacarte-wrapper')
        for name in ('yt-dlp-shim', 'wrapper'):
            self.assertFalse(services[name].get('ports'))
        for service in services.values():
            self.assertEqual(service['pull_policy'], 'never')


if __name__ == '__main__':
    unittest.main()
