import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "docs/evidence/issue-6/release-lock.json"
LAUNCHER = ROOT / "scripts/orca-oct15-qualify.ps1"
GUIDE = ROOT / "docs/ISSUE_6_QUALIFICATION.md"


class Issue6QualificationTests(unittest.TestCase):
    def test_release_lock_has_exact_immutable_pins(self):
        lock = json.loads(LOCK.read_text())
        self.assertEqual(lock["accepted_baseline"]["repository_commit"], "b49aa93dc0562f5394ac82b5c8c8f0b0b9b6c709")
        self.assertTrue(lock["accepted_baseline"]["preserved"])
        self.assertEqual(lock["helix"]["annotated_tag"], "cd9734ccd884784ac7f1aa07e2046b72de2d59e9")
        self.assertEqual(lock["helix"]["source_commit"], "e5cdc5dc523280bc3ead681a4f229bf84dfa726a")
        self.assertEqual(lock["orca"]["run_id"], 38671673715)
        self.assertEqual(lock["orca"]["source_commit"], "6a7763f08d1a175a464a00ce13f0b5a815662fc4")
        self.assertEqual(lock["official_calibration_bridge"]["decision"], "reject_unchanged_for_display_only")
        self.assertFalse(lock["target"]["mutation_performed"])

    def test_oct15_launcher_is_separate_and_hash_pinned(self):
        source = LAUNCHER.read_text()
        for value in (
            "6a7763f08d1a175a464a00ce13f0b5a815662fc4",
            "e2b6da4c20e7080eade97379f326dcfcaa90f1ecb9991f1db9eb61e3065a9759",
            "3c5b2accbdc7d8ad2eab9cf21705a9b04f2e0be9961cfe3016c7376c6fadc157",
            ".helix-orca-issue-6-oct15-qualification",
            "issue-6-nightly-6a7763f",
            "WEBVIEW2_USER_DATA_FOLDER",
        ):
            self.assertIn(value, source)
        self.assertIn("Refusing non-empty unmarked data directory", source)
        self.assertNotIn("Invoke-WebRequest", source)
        self.assertNotIn("Start-Job", source)

    def test_existing_baseline_launcher_and_plugin_remain_pinned(self):
        old = (ROOT / "scripts/orca-nightly-qualify.ps1").read_text()
        self.assertIn("210bc927bc6fb3d3bf390fdf72e4a2767b5de4b3", old)
        manifest = json.loads((ROOT / "helix-plugin/orcacal/manifest.json").read_text())
        self.assertEqual(manifest["version"], "0.2.0")
        self.assertEqual(manifest["permissions"], [])
        self.assertEqual(manifest["helix_version"], ">=1.1.0-beta.4")

    def test_checkpoint_does_not_claim_runtime_or_target_completion(self):
        lock = json.loads(LOCK.read_text())
        self.assertEqual(lock["orca"]["runtime_status"], "pending_isolated_native_qualification")
        guide = " ".join(GUIDE.read_text().split())
        self.assertIn("No event has been sent to the actual target", guide)
        self.assertIn("no `http` or `moonraker_write`", guide)
        self.assertIn("not a completed real-printer candidate", guide)


if __name__ == "__main__":
    unittest.main()
