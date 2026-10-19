"""Synthetic build receipts exercise guards; no test fixture is a real build or UI proof."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from integration import v1_contract as contract
from integration import v1_engine as engine
from integration import v1_parity as parity


def fixture_gcode():
    lines = ['G90', 'M83', 'M140 S60', 'M190 S60', 'M109 S230']
    for i, temp in enumerate((230, 230, 225, 225, 220, 220)):
        lines += [';LAYER_CHANGE', f'G1 Z{(i+1)*.2:.1f}', f'M104 S{temp}', '; printing object temperature_tower.drc id:0 copy 0',
                  'G1 X1 Y1 E1 F1200', 'G1 X2 Y2 E1', '; stop printing object temperature_tower.drc id:0 copy 0']
    return '\n'.join(lines + ['M104 S0', 'M140 S0']) + '\n'


class NativeTransport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.exe = self.root / 'test-only-native'
        header = bytearray(64)
        header[:7] = b'\x7fELF\x02\x01\x01'
        header[18:20] = (62).to_bytes(2, 'little')
        self.exe.write_bytes(header + b'test-only header fixture; never an actual executable build')
        self.exe.chmod(0o700)
        self.resources = self.root / 'resources'
        assets = {}
        for name in engine._NATIVE_ASSETS:
            p = self.resources / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b'test-only native resource')
            assets[name] = engine._sha_file(p)
        effective = {f'fixture_native_key_{i}': '0' for i in range(100)}
        effective.update(plugins='', post_process='', slicing_pipeline_plugin='', belt_printer='0',
                         curr_bed_type='High Temp Plate', nozzle_diameter='0.4', gcode_flavor='marlin')
        self.snapshot = {'schema': 'helix-orca-v1-context/v1', 'origin_id': '1'*32,
                         'runtime': {'version': '2.5.0-dev', 'build': '6a7763f0'},
                         'nozzle_mm': .4, 'effective': effective}
        for role in ('printer', 'process', 'filament'):
            self.snapshot[role] = {state: {'name': role+'-'+state, 'config': {'retained': 'value'}}
                                   for state in ('saved', 'edited')}
        self.request = {'schema': 'helix-orca-v1-request/v1', 'request_id': '2'*32,
                        'origin_id': '1'*32, 'context_sha256': contract.digest(self.snapshot),
                        'calibration': 'temperature', 'parameters': {'start': 230, 'end': 220, 'step': 5, 'scale': True},
                        'created_at': 100, 'expires_at': 200, 'not_applied': True}
        self.inputs = {'source': {'source_commit': engine.ORCA_SOURCE, 'source_verified': True,
                                  'files': {name: {'sha256': sha} for name, sha in engine.SOURCE_HASHES.items()}},
                       'builder_image': 'sha256:f67960f55aa1b7cfa8af41bd89943b13730b791ce55e1925bc575d5eef89f6d9',
                       'owned_inputs': {name: engine._sha_file(engine._ROOT/name) for name in engine._OWNED_INPUTS}}
        self.receipt = {'schema': 'helix-orca-v1-native-build/v1', 'source_commit': engine.ORCA_SOURCE,
                        'built': True, 'qualified': False, 'resources': assets, 'target': dict(engine._TARGET),
                        'adapter': {'size': self.exe.stat().st_size, 'sha256': engine._sha_file(self.exe)},
                        'capabilities': {'schema': 'helix-orca-v1-native-capabilities/v1',
                                         'source_commit': engine.ORCA_SOURCE, 'routes': sorted(engine._NATIVE_ROUTES),
                                         'target': dict(engine._TARGET), 'max_parallelism': 2,
                                         'required_effective_keys': sorted(effective)}}
        self.config = {'native_executable': self.record(self.exe), 'native_resources': str(self.resources),
                       'now': 150, 'runner': self.runner}
        self.refresh_receipts()
        self.called = False

    def record(self, path):
        return {'path': str(path), 'sha256': engine._sha_file(path)}

    def refresh_receipts(self):
        p = self.root/'native-inputs.json'
        p.write_text(json.dumps(self.inputs))
        self.config['build_inputs'] = self.record(p)
        self.receipt['native_inputs_sha256'] = engine._sha_file(p)
        p = self.root/'native-build.json'
        p.write_text(json.dumps(self.receipt))
        self.config['build_receipt'] = self.record(p)

    def runner(self, argv, out):
        self.called = True
        self.assertEqual(argv[1:3], [str(out/'request.json'), str(out/'context.json')])
        artifact = out/'native-calibration.gcode'
        artifact.write_text(fixture_gcode())
        report = {key: self.request[key] for key in ('calibration', 'parameters', 'request_id', 'origin_id', 'context_sha256')}
        report.update(source_commit=engine.ORCA_SOURCE, artifact=artifact.name, size=artifact.stat().st_size,
                      qualified=False, not_applied=True, processing={'error_code': 0, 'warnings': []}, max_parallelism=2)
        (out/'native-generation.json').write_text(json.dumps(report))
        return 0

    def generate(self, name='job'):
        return engine.generate(self.request, self.snapshot, self.root/name, self.config)

    def add_reference(self):
        native = self.root/'independent-native.gcode'
        native.write_text(fixture_gcode())
        evidence = []
        for name in ('dialog.txt', 'export.txt'):
            p = self.root/name
            p.write_text('Synthetic checker-only UI evidence; never acceptance evidence.')
            evidence.append(p)
        manifest = parity.create_native_reference(native, self.snapshot, 'temperature', self.request['parameters'],
                                                  engine.ORCA_SOURCE, evidence)
        p = self.root/'reference.json'
        p.write_text(json.dumps(manifest))
        self.config['native_reference'] = {'manifest': self.record(p), 'gcode': self.record(native)}

    def test_built_fixture_without_independent_reference_cannot_be_ready(self):
        original = copy.deepcopy(self.snapshot)
        result = self.generate()
        self.assertTrue(self.called)
        self.assertFalse(result['parity']['qualified'])
        self.assertTrue(result['not_applied'])
        self.assertEqual(original, self.snapshot)
        self.assertEqual(contract.validate_prepared(result, self.request), result)
        self.assertEqual(result['parity']['report_sha256'], contract.digest(json.loads((self.root/'job/parity.json').read_text())))

    def test_foreign_host_or_elf_target_never_enables_native(self):
        for system, machine in [('Windows', 'AMD64'), ('Linux', 'aarch64'), ('Darwin', 'x86_64')]:
            with self.subTest(system=system, machine=machine), patch.object(engine.platform, 'system', return_value=system), patch.object(engine.platform, 'machine', return_value=machine):
                with self.assertRaises(engine.NativeEngineBlocked) as caught:
                    self.generate()
                self.assertEqual(caught.exception.code, 'native_platform')
                self.assertFalse(any(row['available'] for row in engine.capabilities(self.config)))
                self.assertFalse(self.called)
        self.exe.write_bytes(b'MZ' + b'not an ELF target' * 10)
        self.config['native_executable'] = self.record(self.exe)
        self.receipt['adapter'] = {'size': self.exe.stat().st_size, 'sha256': engine._sha_file(self.exe)}
        self.refresh_receipts()
        with self.assertRaises(engine.NativeEngineBlocked) as caught:
            self.generate()
        self.assertEqual(caught.exception.code, 'native_format')
        self.assertFalse(self.called)

    def test_missing_or_mutated_reference_retains_unqualified_artifact_report(self):
        self.add_reference()
        Path(self.config['native_reference']['gcode']['path']).write_text('substituted reference')
        result = self.generate()
        self.assertFalse(result['parity']['qualified'])
        self.assertIn('reference unavailable', result['parity']['reason'])
        self.assertTrue((self.root/'job/parity.json').is_file())

    def test_post_export_warning_cannot_reach_parity_or_ready(self):
        def warning_runner(argv, out):
            self.runner(argv, out)
            report = json.loads((out/'native-generation.json').read_text())
            report['processing']['warnings'] = [{'level': 1, 'message': 'outside retained envelope'}]
            (out/'native-generation.json').write_text(json.dumps(report))
            return 0
        self.config['runner'] = warning_runner
        with self.assertRaises(engine.NativeEngineBlocked) as caught:
            self.generate()
        self.assertEqual(caught.exception.code, 'native_result')
        self.assertFalse((self.root/'job/prepared.json').exists())

    def test_executable_receipt_and_owned_source_substitution_stop_before_runner(self):
        self.exe.write_text('substituted executable')
        with self.assertRaises(engine.NativeEngineBlocked):
            self.generate()
        self.assertFalse(self.called)
        self.assertFalse((self.root/'job').exists())
        self.config['native_executable'] = self.record(self.exe)
        with self.assertRaises(engine.NativeEngineBlocked):
            self.generate()
        self.receipt['adapter'] = {'size': self.exe.stat().st_size, 'sha256': engine._sha_file(self.exe)}
        self.inputs['owned_inputs']['integration/v1-native-engine/main.cpp'] = '0'*64
        self.refresh_receipts()
        with self.assertRaises(engine.NativeEngineBlocked):
            self.generate()
        self.assertFalse(self.called)

    def test_complete_native_key_inventory_and_empty_plugins_are_mandatory(self):
        del self.snapshot['effective']['fixture_native_key_3']
        self.request['context_sha256'] = contract.digest(self.snapshot)
        with self.assertRaisesRegex(engine.NativeEngineBlocked, 'unavailable'):
            self.generate()
        self.snapshot['effective']['fixture_native_key_3'] = '0'
        self.snapshot['effective']['slicing_pipeline_plugin'] = 'active-plugin'
        self.request['context_sha256'] = contract.digest(self.snapshot)
        with self.assertRaisesRegex(engine.NativeEngineBlocked, 'external processing'):
            self.generate()
        self.assertFalse(self.called)

    def test_false_build_receipt_and_mutated_asset_never_enable_availability(self):
        self.receipt['built'] = False
        self.refresh_receipts()
        self.assertFalse(any(row['available'] for row in engine.capabilities(self.config)))
        self.receipt['built'] = True
        self.refresh_receipts()
        next(self.resources.rglob('*.drc')).write_bytes(b'changed')
        with self.assertRaises(engine.NativeEngineBlocked):
            self.generate()
        self.assertFalse(self.called)

    def test_shared_real_parity_evaluator_qualifies_synthetic_checker_only(self):
        self.add_reference()
        result = self.generate()
        self.assertTrue(result['parity']['qualified'], result['parity']['reason'])
        report = json.loads((self.root/'job/parity.json').read_text())
        self.assertEqual(report['policy'], 'exact-executable-v1')
        self.assertEqual(report['candidate_executable_sha256'], report['native_executable_sha256'])
        self.assertNotEqual(report['candidate_path'], report['native_path'])

    def test_material_difference_stays_unqualified_even_when_native_runner_succeeds(self):
        self.add_reference()
        original = self.runner
        def different(argv, out):
            code = original(argv, out)
            p = out/'native-calibration.gcode'
            p.write_text(p.read_text().replace('G1 X2 Y2 E1', 'G1 X3 Y2 E1', 1))
            return code
        self.config['runner'] = different
        result = self.generate()
        self.assertFalse(result['parity']['qualified'])
        self.assertIn('executable behavior differs', result['parity']['reason'])

    def test_native_claimed_qualification_or_wrong_request_is_rejected(self):
        original = self.runner
        def forged(argv, out):
            code = original(argv, out)
            p = out/'native-generation.json'
            value = json.loads(p.read_text())
            value['qualified'] = True
            p.write_text(json.dumps(value))
            return code
        self.config['runner'] = forged
        with self.assertRaisesRegex(engine.NativeEngineBlocked, 'exact request'):
            self.generate()
        self.assertFalse((self.root/'job/prepared.json').exists())


if __name__ == '__main__':
    unittest.main()
