import importlib.util
import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "docs/evidence/issue-6/release-lock.json"
LAUNCHER = ROOT / "scripts/orca-oct15-qualify.ps1"
GUIDE = ROOT / "docs/ISSUE_6_QUALIFICATION.md"
WINDOWS_ADAPTER = ROOT / "scripts/orca-oct15-windows-review.py"
BETA9_QUALIFIER = ROOT / "scripts/helix-beta9-qualify.py"
DISPLAY_QUALIFIER = ROOT / "scripts/helix-display-qualify.py"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
            "8f0269e6510ca11848144c14fc2c42a33ea288e8dd1bfa7bd1e5789636bf3d52",
            "7eb76b92928bc93a3592bb362128579d47d49fc4c5c6cf55f16d6575cf6f6999",
            ".helix-orca-issue-6-oct15-qualification",
            "issue-6-nightly-6a7763f",
            "WEBVIEW2_USER_DATA_FOLDER",
        ):
            self.assertIn(value, source)
        self.assertIn("Refusing non-empty unmarked data directory", source)
        self.assertIn("[Parameter(Mandatory = $true)][string]$QualifiedPluginSource", source)
        self.assertIn("Copy-Item -LiteralPath $QualifiedPluginSource", source)
        self.assertIn("accepted_plugin_sha256=$ExpectedAcceptedPluginSha256", source)
        self.assertNotIn("Invoke-WebRequest", source)
        self.assertNotIn("Start-Job", source)

    def test_existing_baseline_launcher_and_plugin_remain_pinned(self):
        old = (ROOT / "scripts/orca-nightly-qualify.ps1").read_text()
        self.assertIn("210bc927bc6fb3d3bf390fdf72e4a2767b5de4b3", old)
        manifest = json.loads((ROOT / "helix-plugin/orcacal/manifest.json").read_text())
        self.assertEqual(manifest["version"], "0.2.0")
        self.assertEqual(manifest["permissions"], [])
        self.assertEqual(manifest["helix_version"], ">=1.1.0-beta.4")

    def test_checkpoint_records_runtime_but_not_target_completion(self):
        lock = json.loads(LOCK.read_text())
        self.assertEqual(lock["orca"]["runtime_status"], "passed_isolated_native_preparation_and_export")
        guide = " ".join(GUIDE.read_text().split())
        self.assertIn("No event has been sent to the actual target", guide)
        self.assertIn("no `http` or `moonraker_write`", guide)
        self.assertIn("not a completed real-printer candidate", guide)

    def test_lock_binds_display_candidate_and_nonprinting_native_upload(self):
        lock = json.loads(LOCK.read_text())
        display = lock["display_only_adaptation"]
        for relative, digest in display["files"].items():
            self.assertEqual(sha256(ROOT / "integration/helix-orca-display" / relative), digest)
        self.assertEqual(sha256(ROOT / display["client"]["path"]), display["client"]["sha256"])
        self.assertEqual(
            display["client"]["rpc_allowlist"],
            ["server.connection.identify", "connection.send_event"],
        )
        self.assertIn("HTTP GET", display["client"]["remote_file_readback"])
        receiver = display["native_upload_receiver"]
        self.assertEqual(sha256(ROOT / receiver["path"]), receiver["sha256"])
        self.assertEqual(display["permissions"], [])
        self.assertFalse(display["actual_target_event_sent"])

        upload = lock["orca"]["native_qualification"]["native_upload_only"]
        self.assertEqual(upload["selected_action"], "Upload")
        self.assertEqual(upload["multipart"], {"root": "gcodes", "print": "false"})
        self.assertEqual(upload["forbidden_printer_routes_observed"], 0)
        self.assertTrue(upload["first_export_comparison"]["executable_lines_exact_match"])
        self.assertIn("synthetic", upload["status"])
        self.assertIn("not actual Moonraker", upload["limitation"])

    def test_beta9_qualifier_uses_exact_developer_artifact_and_accepted_harness(self):
        source = BETA9_QUALIFIER.read_text()
        for value in (
            "38685014257",
            "11955517186",
            "494826250f5b38020a8a06673bc58cad3da9370f607523babf4163499b8c1ba1",
            "e21a5a8ce2c3a7dfcc21f56d3c19b2ba31528be00313929f671b66197e3e4704",
            "accepted.run_viewport",
            '"container_network": "none"',
            "accepted._plugin_hashes()",
            '"qualification_sources": qualification_source_hashes()',
            'report.get("accepted_plugin_files") != accepted._plugin_hashes()',
        ):
            self.assertIn(value, source)
        self.assertNotIn("git clone", source)
        self.assertNotIn("make -j", source)

    def test_windows_adapter_pins_process_storage_and_digest(self):
        spec = importlib.util.spec_from_file_location("issue6_windows", WINDOWS_ADAPTER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        source = module.issue6_ui_source()
        self.assertIn("HelixOrcaCalibration\\issue-6-oct15-6a7763f", source)
        self.assertIn("HelixOrcaCalibration\\issue-6-nightly-6a7763f", source)
        self.assertIn("runtime\\orca-slicer.exe", source)
        self.assertIn(
            "e2b6da4c20e7080eade97379f326dcfcaa90f1ecb9991f1db9eb61e3065a9759",
            source,
        )
        self.assertIn("October 15 executable digest mismatch", source)
        self.assertNotIn("issue-4-nightly-210bc927", source)

    def test_windows_adapter_does_not_change_accepted_ui_driver(self):
        accepted = (ROOT / "scripts/orca-windows-ui.ps1").read_text()
        self.assertIn("HelixOrcaCalibration\\issue-4-nightly-210bc927", accepted)
        self.assertNotIn("issue-6-nightly-6a7763f", accepted)

    def test_display_qualifier_is_test_only_and_network_disabled(self):
        source = DISPLAY_QUALIFIER.read_text()
        self.assertIn("accepted.VIEWPORTS", source)
        self.assertIn("candidate_plugin_files", source)
        self.assertIn("qualification_sources", source)
        self.assertIn("extra-key-rejected-without-overlay", source)
        self.assertIn("dismiss-closes-receipt", source)
        self.assertNotIn("printer.print", source)
        self.assertNotIn("gcode.script", source)


if __name__ == "__main__":
    unittest.main()
