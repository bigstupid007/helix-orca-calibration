"""Qualification must follow independently prepared retained native bytes."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from integration import v1_parity as parity


def temperature_gcode():
    lines = ['G90', 'M83', 'M140 S60', 'M190 S60', 'M109 S230']
    for i, temp in enumerate((230, 230, 225, 225, 220, 220)):
        lines += [';LAYER_CHANGE', f';Z:{(i+1)*.2:.1f}', f'G1 Z{(i+1)*.2:.1f}',
                  f'M104 S{temp}', '; printing object temperature_tower.drc id:0 copy 0',
                  'G1 X1 Y1 E1 F1200', 'G1 X2 Y2 E1', '; stop printing object temperature_tower.drc id:0 copy 0']
    return '\n'.join(lines + ['M104 S0', 'M140 S0']) + '\n'


class NativeParity(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.candidate = self.root / 'candidate.gcode'
        self.native = self.root / 'native.gcode'
        for p in (self.candidate, self.native):
            p.write_text(temperature_gcode())
        evidence = self.root / 'native-actions.txt'
        evidence.write_text('Test-only simulated native capture; not acceptance evidence.')
        self.inputs = {'calibration': 'temperature', 'parameters': {'start': 230, 'end': 220, 'step': 5, 'scale': True},
                       'nozzle_mm': .4, 'context_sha256': 'a' * 64,
                       'source_commit': next(iter(parity.PINS)), 'runtime': next(iter(parity.PINS.values()))}
        self.manifest = {'schema': 'helix-orca-v1-native-reference/v1', 'method': 'native_orca_ui',
                         'imported_candidate': False, 'inputs_sha256': parity.digest(self.inputs),
                         'source_commit': self.inputs['source_commit'], 'runtime': self.inputs['runtime'],
                         'artifact': parity.file_record(self.native),
                         'evidence': [{'path': str(evidence), 'artifact': parity.file_record(evidence)}]}

    def evaluate(self):
        return parity.evaluate(self.candidate, self.native, self.manifest, self.inputs)

    def test_exact_synthetic_reference_qualifies_checker_only(self):
        report = self.evaluate()
        self.assertTrue(report['qualified'], report['reason'])
        self.assertEqual(report['candidate_invariants']['deposition_temperatures'], [220., 225., 230.])

    def test_annotations_not_a_recipe_oracle(self):
        self.candidate.write_text(self.candidate.read_text().replace(';Z:', '; ignored nominal height '))
        self.assertTrue(self.evaluate()['qualified'])

    def test_late_band_cannot_be_repaired_after_first_deposition(self):
        s = self.candidate.read_text().replace('M104 S225', 'M104 S230', 1)
        self.candidate.write_text(s)
        report = self.evaluate()
        self.assertFalse(report['qualified'])
        self.assertIn('deposition', report['reason'])

    def test_nominal_layer_comments_cannot_hide_wrong_z(self):
        self.candidate.write_text(self.candidate.read_text().replace('G1 Z0.6', 'G1 Z0.8'))
        self.assertIn('printed Z', self.evaluate()['reason'])

    def test_motion_or_extrusion_difference_blocks(self):
        self.candidate.write_text(self.candidate.read_text().replace('G1 X2 Y2 E1', 'G1 X3 Y2 E1', 1))
        report = self.evaluate()
        self.assertFalse(report['qualified'])
        self.assertTrue(report['differences'])
        self.assertIn('executable behavior', report['reason'])

    def test_bed_change_blocks_even_with_correct_nozzle(self):
        self.candidate.write_text(self.candidate.read_text().replace('M140 S60', 'M140 S35'))
        self.assertFalse(self.evaluate()['qualified'])

    def test_self_reference_and_recipe_import_rejected(self):
        self.assertFalse(parity.evaluate(self.native, self.native, self.manifest, self.inputs)['qualified'])
        self.manifest['imported_candidate'] = True
        self.assertFalse(self.evaluate()['qualified'])

    def test_wrong_build_or_profiles_rejected(self):
        self.manifest['inputs_sha256'] = '0' * 64
        self.assertFalse(self.evaluate()['qualified'])

    def test_evidence_changed_blocks(self):
        Path(self.manifest['evidence'][0]['path']).write_text('changed')
        self.assertFalse(self.evaluate()['qualified'])

    def test_shutdown_and_external_actions_rejected(self):
        self.candidate.write_text(self.candidate.read_text().replace('M104 S0', 'SAVE_CONFIG'))
        self.assertFalse(self.evaluate()['qualified'])

    def test_qualified_report_is_recomputed_from_retained_bytes(self):
        report = self.evaluate()
        prepared = {'artifact': report['candidate'], 'calibration': 'temperature', 'parameters': self.inputs['parameters'],
                    'context_sha256': self.inputs['context_sha256'], 'generator': {'build': self.inputs['source_commit']},
                    'parity': {'qualified': True, 'report_sha256': parity.digest(report)}}
        self.assertTrue(parity.verify_report(report, prepared))
        self.candidate.write_text(self.candidate.read_text() + 'M500\n')
        self.assertFalse(parity.verify_report(report, prepared))

    def test_forged_flag_and_rehashed_report_still_rejected(self):
        self.candidate.write_text(self.candidate.read_text().replace('M140 S60', 'M140 S35'))
        report = self.evaluate()
        report['qualified'] = True
        prepared = {'artifact': report['candidate'], 'calibration': 'temperature', 'parameters': self.inputs['parameters'],
                    'context_sha256': self.inputs['context_sha256'], 'generator': {'build': self.inputs['source_commit']},
                    'parity': {'qualified': True, 'report_sha256': parity.digest(report)}}
        self.assertFalse(parity.verify_report(report, prepared))


if __name__ == '__main__':
    unittest.main()
