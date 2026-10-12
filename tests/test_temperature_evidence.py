import contextlib
import importlib.util
import io
import json
from pathlib import Path
import unittest
import tempfile
from unittest.mock import patch

from test_plugin import load_plugin

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('temperature_evidence',ROOT/'scripts/temperature-evidence.py')
e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)


class TemperatureEvidenceTests(unittest.TestCase):
    def test_runtime_binary_and_imported_harness_are_bound(self):
        directory=ROOT/'docs/evidence/issue-4/roundtrip'
        original=json.loads((directory/'report.json').read_text())
        self.assertIn('scripts/helix_dev.py',original['runtime_candidate_files'])
        for location in ('helix_binary_sha256','isolation_contract','viewport_runs'):
            report=json.loads(json.dumps(original))
            if location=='isolation_contract':report[location]['binary_sha256']='0'*64
            elif location=='viewport_runs':report[location][0]['binary_sha256']='0'*64
            else:report[location]='0'*64
            with tempfile.TemporaryDirectory() as temp:
                path=Path(temp);(path/'report.json').write_text(json.dumps(report))
                for name in ('request.json','result.json','matrix.tsv'):
                    (path/name).write_bytes((directory/name).read_bytes())
                with self.assertRaises(ValueError):e.verify(path)

    def test_drag_rejects_unbounded_and_noninteger_input_before_native_access(self):
        with patch.object(e.d,'inspect') as inspect:
            for coordinates in ((0,0,800,10),(0,-1,10,10),(True,0,10,10),(0,0,10.5,10)):
                with self.assertRaises(ValueError):e.drag(dict(zip(('x0','y0','x1','y1'),coordinates)))
            inspect.assert_not_called()

    def test_finish_mock_requires_a_started_isolated_request(self):
        with patch.object(e.d,'inspect',return_value=None),patch.object(e.d,'ctl') as ctl:
            with self.assertRaises(ValueError):e.finish_mock()
            ctl.assert_not_called()
        with patch.object(e.d,'inspect',return_value={'owned':True}),patch.object(e.d,'ctl',return_value={'value':1}) as ctl:
            with self.assertRaises(ValueError):e.finish_mock()
            self.assertEqual(ctl.call_args_list,[unittest.mock.call('get','calibration-bridge__state')])

    def test_exact_candidate_and_complete_native_matrix_integrity(self):
        with contextlib.redirect_stdout(io.StringIO()):
            e.verify(ROOT/'docs/evidence/issue-4/roundtrip')

    def test_actual_native_result_targets_actual_windows_request(self):
        directory=ROOT/'docs/evidence/issue-4/roundtrip'
        request=json.loads((directory/'request.json').read_text())
        result=json.loads((directory/'result.json').read_text())
        plugin,_=load_plugin()
        instructions=plugin.validate_temperature_result(request,result)
        self.assertEqual(instructions['profile'],'Generic PLA - Voron Rapido - Initial')
        self.assertEqual(instructions['setting'],'nozzle_temperature')
        self.assertEqual([instructions[k] for k in ('original_saved_value','original_edited_value','original_effective_value','selected_value')],[220,217,217,205])
        self.assertEqual(instructions['status'],'not applied')
        qualified=json.loads((ROOT/'docs/evidence/issue-4/windows/qualification.json').read_text())
        self.assertEqual(request['file']['sha256'],qualified['manual_file_selection']['sha256'])
        self.assertEqual(request['file']['bands'],list(range(230,189,-5)))
