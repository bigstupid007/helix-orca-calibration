"""Transport-boundary checks; native interaction is retained separately as evidence."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import test_temperature_roundtrip

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('temperature_harness', ROOT / 'scripts/temperature-roundtrip.py')
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)


class RoundTripHarnessTests(unittest.TestCase):
    def setUp(self):
        setup = test_temperature_roundtrip.TemperatureRoundTripTests(); setup.setUp()
        self.plugin, self.target = setup.plugin, setup.target
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.file = self.root/'temperature.gcode'
        # Parser fixture only; no slicer, executable print, or product generator.
        self.file.write_text('\n'.join('M104 S'+str(v) for v in range(230,189,-5))+'\n')
        metadata = {'name':self.file.name,'size':self.file.stat().st_size,'sha256':harness.digest(self.file),'bands':list(range(230,189,-5))}
        self.request = self.plugin.make_temperature_request(self.target,metadata,'test-only')
        self.path = self.root/'request.json'
        self.path.write_text(json.dumps(self.request))

    def test_native_payload_binds_original_profiles_file_and_request(self):
        request,payload=harness.prepare(self.path,self.file)
        self.assertEqual(payload['request_id'],request['request_id'])
        self.assertEqual(payload['current'],217)
        self.assertEqual(payload['saved_current'],220)
        self.assertTrue(payload['mock_only'])
        self.assertEqual(payload['file_sha256'],harness.digest(self.file))
        self.assertEqual(payload['file'],request['bridge_file'])

    def test_mutated_export_bytes_are_rejected_before_native_handoff(self):
        self.file.write_text(self.file.read_text().replace('S205','S207'))
        with self.assertRaises(ValueError):harness.prepare(self.path,self.file)

    def test_tampered_context_request_and_real_mode_are_rejected(self):
        for key,value in [('mock_only',False),('context_sha256','a'*64),('request_id','a'*32),('bridge_file','../other.gcode')]:
            request=copy.deepcopy(self.request); request[key]=value
            self.path.write_text(json.dumps(request))
            with self.subTest(key=key),self.assertRaises(ValueError):harness.prepare(self.path,self.file)

    def test_bridge_is_separate_from_permissionless_product(self):
        product=json.loads((ROOT/'helix-plugin/orcacal/manifest.json').read_text())
        self.assertEqual(product['permissions'],[])
        ordinary=(ROOT/'scripts/helix_dev.py').read_text()
        self.assertNotIn('calibration-bridge',ordinary)
        bridge=json.loads((ROOT/'integration/calibration-bridge/manifest.json').read_text())
        self.assertEqual(bridge['permissions'],['storage','moonraker_write'])
        lua=(ROOT/'integration/calibration-bridge/main.lua').read_text()
        self.assertNotIn('on_agent_event',lua)
        self.assertNotIn('helix.http.',lua)
        self.assertIn('helix.storage.get("request")',lua)
        self.assertIn('pcall(helix.storage.set, "result", body)',lua)
