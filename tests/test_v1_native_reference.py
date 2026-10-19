"""Windows-local reference registration is evidence inspection, not qualification."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from integration import v1_contract as c, v1_parity as p
import test_v1_parity as schedule_fixtures

SCRIPT = Path(__file__).resolve().parents[1]/'scripts/v1-native-reference.py'
SPEC = importlib.util.spec_from_file_location('v1_native_reference', SCRIPT)
inspector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inspector)


class NativeReferenceInspector(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        text, inputs = schedule_fixtures.NativeCalibrationSchedules().mvs()
        self.context = {'schema': 'helix-orca-v1-context/v1', 'origin_id': '1'*32,
                        'runtime': p.PINS[inspector.PIN], 'nozzle_mm': inputs['nozzle_mm'],
                        'effective': {**inputs['effective'], 'private_hook': 'SECRET_PRIVATE_HOOK'}}
        for role in ('printer', 'process', 'filament'):
            self.context[role] = {state: {'name': 'SECRET_PROFILE', 'config': {'key': 'SECRET_VALUE'}}
                                  for state in ('saved', 'edited')}
        context_path = self.root/'SECRET-context.json'
        context_path.write_bytes(c.canonical(self.context))
        native = self.root/'SECRET-native.gcode'
        native.write_text(text)
        parameters = self.root/'parameters.json'
        parameters.write_bytes(c.canonical(inputs['parameters']))
        evidence = []
        for name in ('native-parameters.png', 'native-exported.png'):
            path = self.root/name
            path.write_bytes(b'\x89PNG\r\n\x1a\nSynthetic fixture, not real native capture')
            evidence.append(path)
        self.args = argparse.Namespace(native=native, context=context_path, calibration='max_volumetric_speed',
                                       parameters=parameters, native_evidence=evidence, output_dir=self.root/'reports')
        self.pin = patch.object(inspector, 'CONTEXT_SHA', c.digest(self.context))
        self.pin.start()
        self.addCleanup(self.pin.stop)

    def test_native_only_inspection_retains_provenance_without_qualification(self):
        summary = inspector.run(self.args)
        self.assertTrue(summary['reference_registered'])
        self.assertTrue(summary['invariants_passed'])
        self.assertFalse(summary['qualified'])
        self.assertFalse(summary['physical_actions'])
        self.assertFalse(summary['physical_readiness'])
        self.assertNotIn('SECRET', json.dumps(summary))
        self.assertNotIn('PRINT_START', json.dumps(summary))
        self.assertNotIn('G1 X', json.dumps(summary))
        self.assertLess(len(c.canonical(summary)), 65536)
        report = json.loads((self.args.output_dir/'native-inspection.json').read_text())
        self.assertIn('SECRET_PROFILE', json.dumps(report))
        self.assertIn('SECRET_PRIVATE_HOOK', json.dumps(report))
        self.assertEqual(inspector.sha(self.args.output_dir/'native-inspection.json'), summary['report_sha256'])
        manifest = json.loads((self.args.output_dir/'native-reference.json').read_text())
        self.assertEqual(manifest['artifact'], p.file_record(self.args.native))
        self.assertFalse(manifest['imported_candidate'])
        self.assertEqual(manifest['method'], 'native_orca_ui')

    def test_failed_native_invariant_is_retained_with_fixed_public_code(self):
        self.args.native.write_text('G90\nM83\n; SECRET_RAW_REASON\n')
        summary = inspector.run(self.args)
        self.assertTrue(summary['success'])
        self.assertTrue(summary['reference_registered'])
        self.assertFalse(summary['invariants_passed'])
        self.assertFalse(summary['qualified'])
        self.assertEqual(summary['invariant_failure_code'], 'no_actual_model_deposition')
        self.assertNotIn('SECRET', json.dumps(summary))
        report = json.loads((self.args.output_dir/'native-inspection.json').read_text())
        self.assertEqual(report['invariant_failure']['detail'], 'no actual model deposition')

    def test_unchanged_original_context_is_required(self):
        self.context['effective']['private_hook'] = 'changed'
        self.args.context.write_bytes(c.canonical(self.context))
        with self.assertRaises(inspector.Refused) as error:
            inspector.run(self.args)
        self.assertEqual(error.exception.code, 'immutable_original_context_or_runtime_mismatch')
        self.assertFalse(self.args.output_dir.exists())

    def test_distinct_actual_screenshot_files_and_new_output_directory_required(self):
        self.args.native_evidence[0].write_bytes(b'not an image')
        with self.assertRaises(inspector.Refused):
            inspector.run(self.args)
        self.args.native_evidence = [self.args.native_evidence[1]]*2
        with self.assertRaises(inspector.Refused):
            inspector.run(self.args)
        self.args.native_evidence[0] = self.root/'other.png'
        self.args.native_evidence[0].write_bytes(b'\x89PNG\r\n\x1a\nSynthetic second fixture')
        self.args.output_dir.mkdir()
        sentinel = self.args.output_dir/'native-inspection.json'
        sentinel.write_text('preserved original')
        with self.assertRaises(FileExistsError):
            inspector.run(self.args)
        self.assertEqual(sentinel.read_text(), 'preserved original')

    def test_defaults_are_bounded_and_explicit_parameter_file_is_validated(self):
        self.assertEqual(inspector.DEFAULTS['pressure_advance_pattern'], {'start': 0, 'end': .08, 'step': .005})
        self.assertEqual(inspector.DEFAULTS['retraction'], {'start': 0, 'end': 2, 'step': .1})
        self.assertEqual(inspector.DEFAULTS['max_volumetric_speed'], {'start': 5, 'end': 20, 'step': .5})
        self.args.parameters.write_text('{"start":5,"end":20,"step":0}')
        with self.assertRaises(ValueError):
            inspector.run(self.args)
        self.assertFalse(self.args.output_dir.exists())

    def test_cli_cannot_supply_candidate_or_export_argument_error_text(self):
        result = subprocess.run([sys.executable, '-I', '-S', str(SCRIPT), '--candidate', 'SECRET_PRIVATE_PATH'],
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['failure'], 'invalid_cli_arguments')
        self.assertNotIn('SECRET', result.stdout + result.stderr)
        self.assertEqual(result.stderr, '')

    def test_unknown_report_fields_and_strings_never_escape_whitelist(self):
        result = inspector.sanitized_invariants({'model_moves': 1, 'objects': ['SECRET_OBJECT'],
                                                'macro_semantics': {'start': 'SECRET_START', 'accepted_abi_signature': True},
                                                'calibration_semantics': {'policy': 'SECRET_POLICY', 'samples_per_layer': 17,
                                                                         'pressure_advance_values': [0, .005],
                                                                         'unknown': 'SECRET_VALUE'}})
        self.assertNotIn('SECRET', json.dumps(result))
        self.assertEqual(result['calibration']['samples_per_layer'], 17)
        self.assertTrue(result['accepted_abi_signature'])
        self.assertFalse(result['hardware_abi_qualified'])


if __name__ == '__main__':
    unittest.main()
