"""Portable evidence shape tests; no Docker, runtime cache or GUI is needed."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('v1_portable_test',ROOT/'scripts/v1-native-evidence.py');module=importlib.util.module_from_spec(s);s.loader.exec_module(module)
class NativePortableEvidenceTests(unittest.TestCase):
    def item(self):
        return dict(run_id='a'*32,manifest_sha256='b'*64,state='complete',runtime_clear=True,command_exit=0,limits=dict(reserve=5*1024**3,peak=512*1024**2,margin=512*1024**2,timeout=240,grace=1,log_bytes=1024**2),errors=[])
    def test_lifecycle_summary_requires_each_success_and_limit_field(self):
        item=self.item();module.check_summary(item)
        for key,bad in [('state','incomplete'),('runtime_clear',False),('command_exit',1),('command_exit',False),('errors',['drift']),('manifest_sha256','bad')]:
            value=copy.deepcopy(item);value[key]=bad
            with self.assertRaises(ValueError):module.check_summary(value)
        for key in item['limits']:
            value=copy.deepcopy(item);value['limits'][key]=0
            with self.assertRaises(ValueError):module.check_summary(value)
        value=dict(item,manifest='/private/path')
        with self.assertRaises(ValueError):module.check_summary(value)
    def test_evidence_paths_reject_traversal_symlinks_and_missing_files(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'frame.png').write_bytes(b'synthetic')
            self.assertEqual(module.safe_file(root,'frame.png'),root/'frame.png')
            (root/'link.png').symlink_to(root/'frame.png')
            for name in ('../frame.png','/etc/passwd','missing.png','link.png'):
                with self.assertRaises(ValueError):module.safe_file(root,name)
    def test_expected_frame_set_covers_five_full_workflows(self):
        self.assertEqual(len(module.FRAMES),28)
        for id in module.q.contract.CALIBRATIONS:
            self.assertIn(id+'-returned.png',module.FRAMES)
