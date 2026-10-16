import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('storage_link', ROOT / 'scripts/temperature-communication-storage-link.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
REQUEST_ID = 'a' * 32


class StorageLinkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.install = root / 'install'
        self.shared = root / 'shared'
        (self.install / 'config/plugin-data').mkdir(parents=True)
        (self.shared / 'plugins/orcacal').mkdir(parents=True)
        (self.shared / 'settings.json').write_text('{}')
        (self.install / 'config/settings.json').symlink_to(self.shared / 'settings.json')
        self.manifest = self.shared / 'plugins/orcacal/manifest.json'
        self.manifest.write_text(json.dumps({'id': 'orcacal', 'version': '0.3.0-issue8-native', 'permissions': ['storage']}))
        self.source = self.install / 'config/plugin-data/orcacal.json'
        self.source.write_text(json.dumps({'session': {'request': {
            'schema': 'helix-orca-temperature-session/v1', 'request_id': REQUEST_ID,
            'simulation_only': True, 'not_applied': True}}}))
        self.destination = self.shared / 'plugin-data/orcacal.json'

    def test_dry_run_creates_nothing(self):
        self.assertFalse(m.plan(self.install, self.shared, REQUEST_ID)['changed'])
        self.assertFalse(self.destination.parent.exists())

    def test_apply_creates_one_real_directory_and_file_link(self):
        before = self.source.read_bytes()
        self.assertTrue(m.plan(self.install, self.shared, REQUEST_ID, True)['changed'])
        self.assertFalse(self.destination.parent.is_symlink())
        self.assertTrue(self.destination.is_symlink())
        self.assertEqual(list(self.destination.parent.iterdir()), [self.destination])
        self.assertEqual(self.destination.read_bytes(), before)
        self.assertEqual(self.source.read_bytes(), before)
        self.assertTrue(m.plan(self.install, self.shared, REQUEST_ID, True)['already_linked'])

    def test_unrelated_destination_and_other_link_are_preserved(self):
        self.destination.parent.mkdir()
        self.destination.write_text('unrelated')
        with self.assertRaises(ValueError):
            m.plan(self.install, self.shared, REQUEST_ID, True)
        self.assertEqual(self.destination.read_text(), 'unrelated')
        self.destination.unlink()
        self.destination.symlink_to(self.shared / 'settings.json')
        with self.assertRaises(ValueError):
            m.plan(self.install, self.shared, REQUEST_ID, True)
        self.assertEqual(os.readlink(self.destination), str(self.shared / 'settings.json'))

    def test_directory_link_is_refused(self):
        self.destination.parent.symlink_to(self.source.parent)
        with self.assertRaises(ValueError):
            m.plan(self.install, self.shared, REQUEST_ID, True)

    def test_wrong_request_or_broader_permission_is_refused(self):
        for request_id in ('b' * 32, '', '../outside'):
            with self.subTest(request_id=request_id), self.assertRaises(ValueError):
                m.plan(self.install, self.shared, request_id, True)
        self.manifest.write_text(json.dumps({'id': 'orcacal', 'version': '0.3.0-issue8-native', 'permissions': ['storage', 'http']}))
        with self.assertRaises(ValueError):
            m.plan(self.install, self.shared, REQUEST_ID, True)
        self.assertFalse(self.destination.parent.exists())

    def test_native_symlink_or_unbounded_file_is_refused(self):
        self.source.unlink()
        self.source.symlink_to(self.shared / 'settings.json')
        with self.assertRaises(ValueError):
            m.plan(self.install, self.shared, REQUEST_ID, True)
        self.source.unlink()
        self.source.write_bytes(b'x' * 262145)
        with self.assertRaises(ValueError):
            m.plan(self.install, self.shared, REQUEST_ID, True)

    def test_wrong_settings_location_is_refused(self):
        settings = self.install / 'config/settings.json'
        settings.unlink()
        settings.write_text('{}')
        with self.assertRaises(ValueError):
            m.plan(self.install, self.shared, REQUEST_ID, True)
        self.assertFalse(self.destination.parent.exists())
