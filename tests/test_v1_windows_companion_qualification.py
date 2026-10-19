import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/v1-windows-companion-qualify.py'


class OptimizedQualificationGuards(unittest.TestCase):
    def test_optimized_mode_refuses_wrong_marker_before_synthetic_write(self):
        with tempfile.TemporaryDirectory() as temp:
            local = Path(temp)
            root = local / 'HelixOrcaCalibration/v1-qualification'
            storage = root / 'data/orca_plugins/plugin_data/helix_calibration/v1'
            storage.mkdir(parents=True)
            (root / 'data/.helix-orca-v1-qualification').write_text('unrelated marker')
            view = storage / 'view.json'
            view.write_text('preserve this unrelated view')
            result = subprocess.run([sys.executable, '-O', str(SCRIPT), 'result-simulation',
                '--root', str(root), '--checkout', str(root / 'runtime-lifecycle/x/checkout')],
                env=dict(os.environ, LOCALAPPDATA=str(local)), capture_output=True, text=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('marker_identity_mismatch', result.stderr)
            self.assertNotIn('physical_actions', result.stdout)
            self.assertEqual(view.read_text(), 'preserve this unrelated view')
            self.assertFalse((storage / 'inbox.json').exists())

    @unittest.skipIf(os.name == 'nt', 'Symlink creation is privilege-dependent on Windows')
    def test_optimized_mode_refuses_symlink_ancestor(self):
        with tempfile.TemporaryDirectory() as temp:
            local = Path(temp) / 'real'
            root = local / 'HelixOrcaCalibration/v1-qualification'
            root.mkdir(parents=True)
            alias = Path(temp) / 'alias'
            alias.symlink_to(local, target_is_directory=True)
            supplied = alias / 'HelixOrcaCalibration/v1-qualification'
            result = subprocess.run([sys.executable, '-O', str(SCRIPT), 'readback', '--root', str(supplied),
                '--checkout', str(supplied / 'runtime-lifecycle/x/checkout')],
                env=dict(os.environ, LOCALAPPDATA=str(alias)), capture_output=True, text=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('linked_or_reparse_path_refused', result.stderr)
            self.assertEqual(result.stdout, '')
