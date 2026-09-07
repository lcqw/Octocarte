"""Contracts for the ordinary Compose installation; no daemon or user data needed."""
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


def config(file):
    env = dict(os.environ, MUSIC_DIR='/tmp/fixture-music', HOST_BIND='127.0.0.1')
    return json.loads(subprocess.check_output(['docker', 'compose', '-f', str(ROOT / file), 'config', '--format', 'json'], env=env))


class SimpleComposeTests(unittest.TestCase):
    def test_bootstrap_retains_token_and_existing_navidrome_data(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            auth, nav = root / 'auth', root / 'nav'
            bootstrap.initialize(auth, nav, os.getuid(), os.getgid())
            token = (auth / 'token').read_bytes()
            (nav / 'database-fixture').write_text('keep')
            bootstrap.initialize(auth, nav, os.getuid(), os.getgid())
            self.assertEqual((auth / 'token').read_bytes(), token)
            self.assertEqual((auth / 'token').stat().st_mode & 0o777, 0o600)
            self.assertEqual(auth.stat().st_mode & 0o777, 0o700)
            self.assertEqual((nav / 'database-fixture').read_text(), 'keep')
            (auth / 'token').write_text('broken')
            with self.assertRaises(ValueError):
                bootstrap.initialize(auth, nav, os.getuid(), os.getgid())
            self.assertEqual((auth / 'token').read_text(), 'broken')

    def test_bootstrap_rejects_symlinks_and_does_not_create_addon_navidrome(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bootstrap.initialize(root / 'auth', None, os.getuid(), os.getgid())
            self.assertFalse((root / 'nav').exists())
            token = root / 'auth/token'
            token.unlink()
            (root / 'elsewhere').write_text('retain')
            token.symlink_to(root / 'elsewhere')
            with self.assertRaises(OSError):
                bootstrap.initialize(root / 'auth', None, os.getuid(), os.getgid())
            self.assertEqual((root / 'elsewhere').read_text(), 'retain')

    def test_full_stack_and_addon_share_services_without_owning_existing_navidrome(self):
        full, addon = config('compose.yml'), config('compose.existing-navidrome.yml')
        self.assertEqual(set(full['services']) - set(addon['services']), {'navidrome'})
        self.assertNotIn('navidrome-data', addon['volumes'])
        self.assertEqual(set(addon['services']['initialize'].get('environment', {})), set())
        for name in ('octocarte', 'alacarte', 'wrapper', 'yt-dlp-shim'):
            # The project name changes actual volume names, not service behavior.
            self.assertEqual(full['services'][name], addon['services'][name])
        services = full['services']
        for name in ('navidrome', 'octocarte', 'alacarte'):
            self.assertEqual(services[name]['depends_on']['initialize']['condition'], 'service_completed_successfully')
        self.assertEqual(services['initialize']['network_mode'], 'none')
        self.assertNotIn('ports', services['initialize'])
        music = lambda name: next(v for v in services[name]['volumes'] if v['target'] == '/music')
        self.assertEqual(music('navidrome')['source'], music('alacarte')['source'])
        self.assertTrue(music('navidrome')['read_only'])
        for name in ('octocarte', 'alacarte'):
            auth = next(v for v in services[name]['volumes'] if v['target'] == '/run/octocarte-auth')
            self.assertTrue(auth['read_only'])
            self.assertEqual(auth['type'], 'volume')
        self.assertEqual(services['alacarte']['environment']['AMDL_WRAPPER_IMAGE'], services['wrapper']['image'])
        for name, service in services.items():
            self.assertNotIn('build', service)
            self.assertNotIn('latest', service['image'])
            for mount in service.get('volumes', []):
                if mount['type'] == 'bind':
                    self.assertIn(mount['target'], {'/music', '/var/run/docker.sock', '/app/rootfs/dev/null', '/app/rootfs/dev/urandom', '/app/rootfs/dev/random', '/app/rootfs/dev/zero'})
        version = (ROOT / 'VERSION').read_text().strip()
        for name in set(services) - {'navidrome'}:
            self.assertTrue(services[name]['image'].endswith(':' + version))


if __name__ == '__main__':
    unittest.main()
