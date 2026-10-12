import contextlib
import importlib.util
import io
import json
from pathlib import Path
import unittest

from test_plugin import load_plugin

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('temperature_evidence',ROOT/'scripts/temperature-evidence.py')
e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)


class TemperatureEvidenceTests(unittest.TestCase):
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
