"""Focused qualification records must retain exact reviewed lifecycle bounds."""
import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('parameter_evidence_test', ROOT/'scripts/v1-parameter-evidence.py')
evidence = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evidence)


class ParameterEvidenceTests(unittest.TestCase):
    def record(self):
        return dict(state='complete', runtime_clear=True, exit_code=0, errors=[],
                    limits=dict(reserve=5*1024**3, peak=2*1024**3, margin=512*1024**2,
                                timeout=900, grace=1, log_bytes=1024**2))

    def test_reviewed_disk_allowance_preserves_all_other_bounds(self):
        evidence.check_lifecycle(self.record())
        for key, changed in (('peak', 2*1024**3+1), ('reserve', 1), ('margin', 1),
                             ('timeout', 901), ('log_bytes', 2*1024**2)):
            value = self.record()
            value['limits'][key] = changed
            with self.subTest(key=key), self.assertRaises(ValueError):
                evidence.check_lifecycle(value)

    def test_incomplete_or_uncleared_run_cannot_qualify(self):
        for key, changed in (('state', 'incomplete'), ('runtime_clear', False),
                             ('exit_code', False), ('errors', ['disk guard'])):
            value = copy.deepcopy(self.record())
            value[key] = changed
            with self.subTest(key=key), self.assertRaises(ValueError):
                evidence.check_lifecycle(value)


if __name__ == '__main__':
    unittest.main()
