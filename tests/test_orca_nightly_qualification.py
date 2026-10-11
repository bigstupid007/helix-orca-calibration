import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts" / "orca-nightly-qualify.ps1"
GUIDE = ROOT / "docs" / "ORCA_NIGHTLY_QUALIFICATION.md"


class OrcaNightlyQualificationContractTests(unittest.TestCase):
    def test_launcher_pins_exact_nightly_and_refuses_normal_settings(self):
        source = LAUNCHER.read_text(encoding="utf-8")
        self.assertIn("210bc927bc6fb3d3bf390fdf72e4a2767b5de4b3", source)
        self.assertIn("8d9db0bec8b8a8e0ad0a70485daaf7ee9fa1c88d5f1395f92eabf0430ce0339b", source)
        self.assertIn("5b71e5dbf2f6b3319d6d69f597e3aa3dbf9403f9ea63f93c3c72dc294efba0a4", source)
        self.assertIn("--datadir", source)
        self.assertIn("Refusing non-empty unmarked data directory", source)
        self.assertIn("existing Orca installation", source)
        self.assertIn(".helix-orca-issue-4-qualification", source)

    def test_launcher_stages_only_the_probe_and_test_inputs(self):
        source = LAUNCHER.read_text(encoding="utf-8")
        self.assertIn('"plugin\\helix_calibration.py"', source)
        self.assertIn('"testdata\\orca-profiles"', source)
        self.assertIn('"qualification-output"', source)
        self.assertIn("qualification-launch.json", source)
        self.assertNotIn("Start-Job", source)
        self.assertNotIn("Invoke-WebRequest", source)

    def test_operator_guide_requires_windows_runtime_evidence_before_round_trip(self):
        guide = GUIDE.read_text(encoding="utf-8")
        normalized = " ".join(guide.split())
        self.assertIn("Windows x64", guide)
        self.assertIn("runtime qualification is still pending", normalized)
        self.assertIn("PresetSelected", guide)
        self.assertIn("ProjectDirtyChanged", guide)
        self.assertIn("GCodeExportStarted", guide)
        self.assertIn("GCodeExportFinished", guide)
        self.assertIn("Do not click Print", guide)
        self.assertIn("does not authorize the round-trip implementation", normalized)


if __name__ == "__main__":
    unittest.main()
