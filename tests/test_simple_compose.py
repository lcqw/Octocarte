"""Storage boundaries and persistent credentials for the standalone installation."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('bootstrap', ROOT / 'deploy/bootstrap/initialize.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


class SimpleComposeTests(unittest.TestCase):
    def test_bootstrap_retains_valid_token_and_rejects_invalid_token(self):
        with tempfile.TemporaryDirectory() as temp:
            auth = Path(temp) / 'auth'
            bootstrap.initialize(auth)
            token = (auth / 'token').read_bytes()
            bootstrap.initialize(auth)
            self.assertEqual((auth / 'token').read_bytes(), token)
            self.assertEqual((auth / 'token').stat().st_mode & 0o777, 0o600)
            self.assertEqual(auth.stat().st_mode & 0o777, 0o700)
            (auth / 'token').write_text('broken')
            with self.assertRaises(ValueError):
                bootstrap.initialize(auth)
            self.assertEqual((auth / 'token').read_text(), 'broken')

    def test_bootstrap_rejects_token_symlinks(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bootstrap.initialize(root / 'auth')
            token = root / 'auth/token'
            token.unlink()
            (root / 'elsewhere').write_text('retain')
            token.symlink_to(root / 'elsewhere')
            with self.assertRaises(OSError):
                bootstrap.initialize(root / 'auth')
            self.assertEqual((root / 'elsewhere').read_text(), 'retain')

    def test_installation_cannot_mount_or_initialize_navidrome_database(self):
        env = dict(os.environ, MUSIC_DIR='/tmp/fixture-music', HOST_BIND='127.0.0.1',
                   NAVIDROME_URL='http://existing-server:4533')
        config = json.loads(subprocess.check_output(
            ['docker', 'compose', '-f', str(ROOT / 'compose.yml'), 'config', '--format', 'json'], env=env))
        services = config['services']
        self.assertEqual(set(services), {'initialize', 'octocarte', 'alacarte', 'wrapper', 'yt-dlp-shim'})
        self.assertNotIn('navidrome-data', config['volumes'])
        self.assertFalse(services['initialize'].get('environment'))
        self.assertEqual(len(services['initialize']['volumes']), 1)
        self.assertEqual(services['initialize']['volumes'][0]['target'], '/auth')
        self.assertEqual(services['initialize']['network_mode'], 'none')
        self.assertEqual(services['octocarte']['environment']['Subsonic__Url'], env['NAVIDROME_URL'])
        for name in ('octocarte', 'alacarte'):
            self.assertEqual(services[name]['depends_on']['initialize']['condition'], 'service_completed_successfully')
            auth = next(v for v in services[name]['volumes'] if v['target'] == '/run/octocarte-auth')
            self.assertTrue(auth['read_only'])
            self.assertEqual(auth['type'], 'volume')
        self.assertEqual(services['alacarte']['environment']['AMDL_WRAPPER_IMAGE'], services['wrapper']['image'])
        for service in services.values():
            self.assertNotIn('build', service)
            self.assertTrue(service['image'].endswith(':' + (ROOT / 'VERSION').read_text().strip()))
            for mount in service.get('volumes', []):
                self.assertNotIn(mount['target'], {'/data', '/navidrome'})
                if mount['type'] == 'bind':
                    self.assertIn(mount['target'], {'/music', '/var/run/docker.sock', '/app/rootfs/dev/null', '/app/rootfs/dev/urandom', '/app/rootfs/dev/random', '/app/rootfs/dev/zero'})

    def test_missing_navidrome_url_stops_configuration(self):
        with tempfile.NamedTemporaryFile() as empty_env:
            env = dict(os.environ, MUSIC_DIR='/tmp/music')
            env.pop('NAVIDROME_URL', None)
            result = subprocess.run(['docker', 'compose', '--env-file', empty_env.name,
                                     '-f', str(ROOT / 'compose.yml'), 'config'],
                                    env=env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('NAVIDROME_URL', result.stderr)


if __name__ == '__main__':
    unittest.main()
