import pathlib
import hashlib
import json
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
        self.assertIn("passed qualification on Spare", normalized)
        report_dir = ROOT / "docs/evidence/issue-4/windows"
        report = json.loads((report_dir / "qualification.json").read_text())
        self.assertEqual(report["status"], "passed_with_manual_file_fallback")
        self.assertEqual(report["host"]["name"], "SPARE")
        self.assertTrue(report["runtime"]["matches_target"])
        self.assertTrue(all(report["lifecycle"]["required_observations"].values()))
        self.assertTrue(report["normal_preservation"]["unchanged"])
        self.assertEqual(report["normal_preservation"]["file_count"], 1429)
        original = report["original_context"]
        self.assertFalse(original["printer"]["selected_saved"]["is_system"]["raw_value"])
        self.assertEqual(original["printer"]["selected_saved"]["bundle_id"]["raw_value"], "helix-issue-4-original-context")
        sources = original["nozzle_temperature_sources"]
        self.assertEqual(sources["filament_editor.selected_saved"]["raw_value"], "220")
        self.assertEqual(sources["filament_editor.current_edited"]["raw_value"], "217")
        self.assertEqual(sources["preset_bundle.merged_full_config"]["raw_value"], "217")
        self.assertEqual(report["manual_file_selection"]["bands"], list(range(230, 189, -5)))
        for frame in report["frames"]:
            data = (report_dir / frame["name"]).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), frame["sha256"])
        for fixture in report["fixtures"]:
            data = (ROOT / "testdata/orca-profiles" / fixture["name"]).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), fixture["sha256"])
        self.assertIn("PresetSelected", guide)
        self.assertIn("ProjectDirtyChanged", guide)
        self.assertIn("GCodeExportStarted", guide)
        self.assertIn("GCodeExportFinished", guide)
        self.assertIn("Do not click Print", guide)
        self.assertIn("does not authorize the round-trip implementation", normalized)


if __name__ == "__main__":
    unittest.main()
