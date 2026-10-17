import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import test_plugin


ROOT = Path(__file__).resolve().parents[1]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


alpha_generator = load(ROOT / "scripts/orca-alpha-companion.py", "orca_alpha_companion")
accepted_generator = load(
    ROOT / "scripts/temperature-communication-companion.py", "accepted_temperature_companion")
windows_review = load(ROOT / "scripts/orca-alpha-windows-review.py", "orca_alpha_windows_review")

FILE = {
    "name": "temperature.gcode",
    "size": 1234,
    "sha256": "a" * 64,
    "bands": [230, 225, 220, 215, 210, 205, 200, 195, 190],
}


def bundle():
    value = test_plugin.FakeBundle(
        values={"nozzle_diameter": "0.4", "nozzle_temperature": "217"},
        names=["Original PLA"],
    )
    value.filaments = test_plugin.FakeCollection(
        test_plugin.FakePreset("Original PLA", values={"nozzle_temperature": "220"}),
        test_plugin.FakePreset("Original PLA", dirty=True, values={"nozzle_temperature": "217"}),
    )
    return value


def load_generated(source, root):
    generated = Path(root) / "helix_calibration.py"
    generated.write_text(source, encoding="utf-8")
    previous = test_plugin.PLUGIN_PATH
    test_plugin.PLUGIN_PATH = generated
    try:
        return test_plugin.load_plugin()
    finally:
        test_plugin.PLUGIN_PATH = previous


def selection(payload, value=205):
    return {
        "schema": "helix-orca-temperature-selection/v1",
        "simulation_only": True,
        "not_applied": True,
        "request_id": payload["request_id"],
        "origin_id": payload["origin_id"],
        "context_sha256": payload["context_sha256"],
        "file_sha256": payload["file_sha256"],
        "file": payload["file"],
        "file_bytes": payload["file_bytes"],
        "setting": payload["setting"],
        "value": value,
    }


class AlphaCompanionTests(unittest.TestCase):
    def test_pinned_sources_and_official_alpha_metadata(self):
        self.assertEqual(
            hashlib.sha256((ROOT / "scripts/temperature-communication-companion.py").read_bytes()).hexdigest(),
            alpha_generator.COMPANION_GENERATOR_SHA256,
        )
        self.assertEqual(
            hashlib.sha256(accepted_generator.generate().encode("utf-8")).hexdigest(),
            alpha_generator.ACCEPTED_COMPANION_SHA256,
        )
        source = alpha_generator.generate()
        self.assertIn('# version = "0.5.1"', source)
        self.assertIn('EXPORTER_VERSION = "0.5.1"', source)
        for value in (
            '"version": "OrcaSlicer 2.5.0-alpha"',
            '"build": "3880f2c5"',
            '"source_commit": "3880f2c58ec392ed2bd5938ab31c9c7c496c0eb2"',
            '"release_id": 410256856',
            '"asset_id": 647273931',
            '"asset_name": "OrcaSlicer_Windows_V2.5.0-alpha_x64_portable.zip"',
            '"asset_bytes": 221507287',
            '"asset_sha256": "9b4593697c9ec0f8e7c0dcbebd7f8ea08a5cd01c2bd68d2a5d48b45b4c18ff8c"',
            '"orca_slicer_exe_sha256": "a37d149ea315a0a2125c11625b7dc24e456dbd3bc309dd56519d90dcdcd77985"',
            '"orca_slicer_dll_sha256": "92bdf7493425b949934479164d0745ce5e28fe24c7a556af300792b788e94c8b"',
        ):
            self.assertIn(value, source)
        self.assertNotIn('"workflow_run":', source)
        self.assertNotIn('"artifact_digest":', source)

    def test_snapshot_and_export_use_alpha_provenance(self):
        with tempfile.TemporaryDirectory() as root:
            plugin, _ = load_generated(alpha_generator.generate(), root)
            host = test_plugin.FakeHost(
                bundle(), storage_root=root, version="2.5.0-alpha", build="3880f2c5")
            captured = plugin.datetime.datetime(
                2026, 10, 16, 12, 34, 56, tzinfo=plugin.datetime.timezone.utc)
            snapshot = plugin._qualification_snapshot(
                host, [{"event": "PresetSelected"}], captured_at=captured)
            self.assertEqual(snapshot["schema"], "helix-orca-alpha-qualification/v1")
            self.assertEqual(snapshot["runtime"]["info"]["version"], "2.5.0-alpha")
            self.assertTrue(snapshot["runtime"]["matches_target"])
            path = Path(plugin.write_qualification_evidence(snapshot, root, captured_at=captured))
            self.assertEqual(path.name, "alpha-qualification-20261016T123456.000000Z.json")
            self.assertNotIn("nightly", path.name)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), snapshot)

    def test_exact_alpha_tuple_is_the_only_accepted_runtime(self):
        with tempfile.TemporaryDirectory() as root:
            plugin, _ = load_generated(alpha_generator.generate(), root)
            valid = test_plugin.FakeHost(bundle(), version="2.5.0-alpha", build="3880f2c5")
            target = plugin.capture_temperature_target(valid)
            self.assertEqual(target["runtime"], {"version": "2.5.0-alpha", "build": "3880f2c5"})
            self.assertTrue(plugin._runtime_build(valid)["matches_target"])
            for version, build in (
                ("2.5.0-alpha", "3880f2c5-extra"),
                ("2.5.0-alpha", "210bc927"),
                ("2.5.0-dev", "3880f2c5"),
                ("2.5.0-dev", "6a7763f0"),
            ):
                with self.subTest(version=version, build=build):
                    host = test_plugin.FakeHost(bundle(), version=version, build=build)
                    self.assertFalse(plugin._runtime_build(host)["matches_target"])
                    with self.assertRaises(ValueError):
                        plugin.capture_temperature_target(host)

    def test_accepted_050_companion_still_rejects_alpha(self):
        with tempfile.TemporaryDirectory() as root:
            plugin, _ = load_generated(accepted_generator.generate(), root)
            host = test_plugin.FakeHost(bundle(), version="2.5.0-alpha", build="3880f2c5")
            with self.assertRaises(ValueError):
                plugin.capture_temperature_target(host)

    def test_alpha_state_persists_recovers_and_remains_digest_bound(self):
        with tempfile.TemporaryDirectory() as root:
            plugin, _ = load_generated(alpha_generator.generate(), root)
            host = test_plugin.FakeHost(bundle(), storage_root=root, version="2.5.0-alpha", build="3880f2c5")
            target = plugin.capture_temperature_target(host)
            state = plugin.TemperatureCommunicationState(root, now=lambda: 1000)
            state.start_new(target)
            state.select_file(FILE, plugin.validate_temperature_file)
            state.send()
            outbox = json.loads((Path(root) / "communication/outbox.json").read_text())
            self.assertEqual(plugin.validate_outbox(outbox, now=1000), outbox)
            recovered = plugin.TemperatureCommunicationState(root, now=lambda: 1000)
            self.assertIsNone(recovered.recovery_error)
            self.assertEqual(recovered.target["runtime"], target["runtime"])
            self.assertEqual(recovered.payload, state.payload)

            changed = copy.deepcopy(outbox)
            changed["target"]["saved_temperature"] += 1
            with self.assertRaisesRegex(plugin.CommunicationProtocolError, "digest mismatch"):
                plugin.validate_outbox(changed, now=1000)

            wrong_runtime = copy.deepcopy(outbox)
            wrong_runtime["target"]["runtime"]["build"] = "6a7763f0"
            wrong_runtime["payload"]["context_sha256"] = plugin.json_digest(wrong_runtime["target"])
            with self.assertRaisesRegex(plugin.CommunicationProtocolError, "exact qualified"):
                plugin.validate_outbox(wrong_runtime, now=1000)

    def test_205_duplicate_and_stale_result_guards_are_retained(self):
        with tempfile.TemporaryDirectory() as root:
            plugin, _ = load_generated(alpha_generator.generate(), root)
            host = test_plugin.FakeHost(bundle(), version="2.5.0-alpha", build="3880f2c5")
            state = plugin.TemperatureCommunicationState(root, now=lambda: 1000)
            state.start_new(plugin.capture_temperature_target(host))
            state.select_file(FILE, plugin.validate_temperature_file)
            state.send()
            result = selection(state.payload)
            directory = Path(root) / "communication"
            plugin.atomic_write_json(directory / "inbox.json", result)
            self.assertIn("NOT APPLIED", state.poll_inbox())
            self.assertEqual(state.instructions["selected_value"], 205)
            self.assertIn("Duplicate", state.poll_inbox())
            stale = copy.deepcopy(result)
            stale["request_id"] = "d" * 32
            with self.assertRaisesRegex(plugin.CommunicationProtocolError, "Stale or mismatched"):
                plugin.validate_selection_result(state.payload, stale, now=1000)
            self.assertEqual(state.result, result)


class AlphaWindowsReviewTests(unittest.TestCase):
    def test_wrapper_is_pinned_and_preserves_alpha_isolation_guards(self):
        self.assertEqual(
            hashlib.sha256(windows_review.OCT15_REVIEW.read_bytes()).hexdigest(),
            windows_review.OCT15_REVIEW_SHA256,
        )
        self.assertEqual(
            hashlib.sha256(windows_review.COMMUNICATION_REVIEW.read_bytes()).hexdigest(),
            windows_review.COMMUNICATION_REVIEW_SHA256,
        )
        review = windows_review._load_review()
        source = windows_review.alpha_ui_source(review)
        for value in (
            r"HelixOrcaCalibration\issue-10-alpha-3880f2c",
            r"$Exe=Join-Path $Stage 'runtime\orca-slicer.exe'",
            r"HelixOrcaCalibration\issue-10-alpha-3880f2c\data",
            ".helix-orca-issue-10-alpha-data",
            windows_review.EXE_SHA256,
            windows_review.DLL_SHA256,
            r"$Dll=Join-Path $Stage 'runtime\OrcaSlicer.dll'",
            "ExecutablePath -eq $Exe",
            "ParentProcessId -eq $Target.ProcessId",
            "Click is occluded.",
            "Capture is occluded.",
            "Test Orca is not foreground.",
        ):
            self.assertIn(value, source)
        self.assertNotIn(review.EXE_SHA256, source)
        exe_guard = source.index("$Actual=(Get-FileHash -LiteralPath $Exe")
        dll_guard = source.index("$ActualDll=(Get-FileHash -LiteralPath $Dll")
        process_admission = source.index("$Candidates=@(Get-CimInstance Win32_Process")
        self.assertLess(exe_guard, dll_guard)
        self.assertLess(dll_guard, process_admission)

    def test_passive_menu_and_bounded_region_reuse_accepted_guards(self):
        review = windows_review._load_review()
        source = windows_review.alpha_ui_source(
            review, passive_menu=True, region=[10, 20, 300, 200], op="capture")
        self.assertIn("Start-Sleep -Milliseconds 350", source)
        self.assertIn("Region outside target", source)
        self.assertIn("Region occluded", source)
        self.assertIn("[void]$Original", source)
        with self.assertRaisesRegex(ValueError, "only for capture"):
            windows_review.alpha_ui_source(review, region=[0, 0, 10, 10], op="click")


if __name__ == "__main__":
    unittest.main()
