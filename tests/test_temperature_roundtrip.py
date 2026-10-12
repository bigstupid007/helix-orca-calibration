import copy
import json
import pathlib
import tempfile
import unittest

from test_plugin import FakeBundle, FakeCollection, FakeHost, FakePreset, FakeUI, load_plugin


class TemperatureRoundTripTests(unittest.TestCase):
    def setUp(self):
        self.plugin, self.orca = load_plugin()
        self.bundle = FakeBundle(values={"nozzle_diameter": "0.4", "nozzle_temperature": "217"}, names=["Original PLA"])
        self.bundle.filaments = FakeCollection(FakePreset("Original PLA", user=True, values={"nozzle_temperature": "220"}),
                                               FakePreset("Original PLA", user=True, dirty=True, values={"nozzle_temperature": "217"}))
        self.host = FakeHost(self.bundle)
        self.target = self.plugin.capture_temperature_target(self.host)
        self.file = {"name": "temperature.gcode", "size": 100, "sha256": "a" * 64, "bands": list(range(230, 189, -5))}

    def result(self, request, value=205):
        target = request["target"]
        return {"event": "chosen", "request_id": request["request_id"], "wizard": "temp_tower",
                "context_sha256": request["context_sha256"], "file_sha256": request["file"]["sha256"],
                "filament": target["filament"]["selected_saved"]["name"], "printer": target["printer"]["selected_saved"]["name"],
                "current": target["effective_temperature"], "saved_current": target["saved_temperature"],
                "setting": "nozzle_temperature", "mock_only": True, "value": value}

    def test_real_readers_keep_three_temperature_sources_distinct(self):
        self.assertEqual([self.target[k] for k in ("saved_temperature", "edited_temperature", "effective_temperature")], [220, 217, 217])
        self.assertTrue(self.target["filament"]["current_edited"]["dirty"])
        self.assertEqual(self.target["nozzle_mm"], 0.4)

    def test_missing_saved_value_cannot_be_filled_from_edited_or_merged(self):
        self.bundle.filaments._selected.values.clear()
        with self.assertRaises(ValueError):
            self.plugin.capture_temperature_target(self.host)

    def test_unqualified_build_and_ambiguous_slots_rejected(self):
        self.host._app_info["build"] = "other"
        with self.assertRaises(ValueError):
            self.plugin.capture_temperature_target(self.host)
        self.host._app_info["build"] = "210bc927"
        self.bundle.names.append("second")
        with self.assertRaises(ValueError):
            self.plugin.capture_temperature_target(self.host)

    def test_export_retry_reuses_exact_request_and_receipt_never_starts_a_print(self):
        state = self.plugin.TemperatureRoundTripState()
        state.freeze(self.target)
        state.select_file(self.file)
        with tempfile.TemporaryDirectory() as storage:
            first = state.export(storage)
            content = pathlib.Path(first).read_bytes()
            self.assertEqual(first, state.export(storage))
            self.assertEqual(content, pathlib.Path(first).read_bytes())
            self.assertEqual(len(list(pathlib.Path(storage).rglob('*.json'))), 1)
            request = json.loads(content)
            self.assertTrue(request["mock_only"])
            self.assertNotIn("print_host", json.dumps(request))
            self.assertIsNone(state.instructions)
            state.receive(self.result(request))
            self.assertEqual(state.instructions["status"], "not applied")
            self.assertEqual(state.instructions["original_saved_value"], 220)
            self.assertEqual(state.instructions["selected_value"], 205)

    def test_stale_mismatch_and_unprepared_choice_rejected(self):
        request = self.plugin.make_temperature_request(self.target, self.file, 'first')
        for key, value in (("request_id", "b"*32), ("context_sha256", "b"*64), ("file_sha256", "b"*64),
                           ("filament", "different"), ("printer", "different"), ("current", 220),
                           ("setting", "flow_ratio"), ("mock_only", False), ("value", 212), ("value", True)):
            with self.subTest(key=key, value=value):
                result = self.result(request)
                result[key] = value
                with self.assertRaises(ValueError):
                    self.plugin.validate_temperature_result(request, result)

    def test_duplicate_idempotence_and_conflicting_result_rejection(self):
        state = self.plugin.TemperatureRoundTripState()
        state.freeze(self.target)
        state.file = self.file
        state.request = self.plugin.make_temperature_request(self.target, self.file, 'first')
        result = self.result(state.request)
        state.receive(result)
        previous = copy.deepcopy(state.instructions)
        self.assertIn('Duplicate', state.receive(result))
        with self.assertRaises(ValueError):
            state.receive(self.result(state.request, 210))
        self.assertEqual(state.instructions, previous)
        state.freeze(self.target)
        with self.assertRaises(ValueError):
            state.receive(result)

    def test_invalid_file_clears_pending_request_instead_of_reusing_it(self):
        state = self.plugin.TemperatureRoundTripState()
        state.freeze(self.target)
        state.select_file(self.file)
        state.request = self.plugin.make_temperature_request(self.target, self.file)
        for key, value in (("bands", [230,220,190]), ("name", "../temp.gcode"), ("size", True), ("sha256", "invalid")):
            invalid = dict(self.file, **{key:value})
            with self.assertRaises(ValueError):
                state.select_file(invalid)
            self.assertIsNone(state.request)
            self.assertIsNone(state.file)

    def test_profile_switch_preserves_original_instructions_and_reports_current_difference(self):
        capability = self.plugin.TemperatureRoundTripPanel()
        self.orca.host = self.host
        self.host.ui = FakeUI()
        capability.panel = self.host.ui.create_dock_panel()
        capability.state.freeze(self.target)
        capability.state.file = self.file
        capability.state.request = self.plugin.make_temperature_request(self.target, self.file)
        self.bundle.names = ['Other PLA']
        self.bundle.filaments = FakeCollection(FakePreset('Other PLA', values={'nozzle_temperature':'230'}), FakePreset('Other PLA', values={'nozzle_temperature':'230'}))
        before = copy.deepcopy(self.bundle.filaments._selected.values)
        capability.on_message({'command':'result','result':self.result(capability.state.request)})
        post = capability.panel.posts[-1]
        self.assertFalse(post['current_matches_target'])
        self.assertEqual(post['instructions']['profile'], 'Original PLA')
        self.assertEqual(post['instructions']['setting'], 'nozzle_temperature')
        self.assertEqual(post['instructions']['status'], 'not applied')
        self.assertEqual(self.bundle.filaments._selected.values, before)

    def test_invalid_capture_does_not_leave_old_request_active(self):
        capability = self.plugin.TemperatureRoundTripPanel()
        capability.state.freeze(self.target)
        capability.state.request = self.plugin.make_temperature_request(self.target, self.file)
        self.orca.host = FakeHost(self.bundle, build='other')
        capability.on_message({'command':'freeze'})
        self.assertIsNone(capability.state.request)
        self.assertIsNone(capability.state.target)


if __name__ == '__main__':
    unittest.main()
