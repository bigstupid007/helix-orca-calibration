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


protocol = load(ROOT / "integration/temperature-communication/protocol.py", "temperature_protocol")
generator = load(ROOT / "scripts/temperature-communication-companion.py", "temperature_generator")


def target():
    def pair(name):
        return {
            "selected_saved": {"name": name, "alias": name, "bundle_id": "", "dirty": False, "reason": None},
            "current_edited": {"name": name, "alias": name, "bundle_id": "", "dirty": True, "reason": None},
        }
    return {
        "runtime": {"version": "2.5.0-dev", "build": "6a7763f0"},
        "printer": pair("Voron 2.4"), "process": pair("0.20 Standard"), "filament": pair("Original PLA"),
        "slot_name": "Original PLA", "nozzle_mm": 0.4, "saved_temperature": 220,
        "edited_temperature": 217, "effective_temperature": 215,
        "temperature_semantics": "Saved, edited, and effective remain distinct.",
    }


FILE = {"name": "temperature.gcode", "size": 1234, "sha256": "a" * 64,
        "bands": [230, 225, 220, 215, 210, 205, 200, 195, 190]}


def file_validator(value):
    if value != FILE:
        raise ValueError("bad file")
    return copy.deepcopy(value)


def selection(payload, value=205):
    return {
        "schema": protocol.RESULT_SCHEMA, "simulation_only": True, "not_applied": True,
        "request_id": payload["request_id"], "origin_id": payload["origin_id"],
        "context_sha256": payload["context_sha256"], "file_sha256": payload["file_sha256"],
        "file": payload["file"], "file_bytes": payload["file_bytes"],
        "setting": payload["setting"], "value": value,
    }


def delivery(payload, phase="delivering"):
    return {
        "schema": protocol.DELIVERY_SCHEMA, "request_id": payload["request_id"],
        "origin_id": payload["origin_id"], "context_sha256": payload["context_sha256"],
        "phase": phase,
    }


class ProtocolTests(unittest.TestCase):
    def test_payload_has_exact_flattened_contract_and_distinct_sources(self):
        payload = protocol.make_forward_payload(target(), FILE, "b" * 32, now=1000, request_id="c" * 32)
        self.assertEqual(set(payload), set(protocol.PAYLOAD_KEYS))
        self.assertEqual((payload["saved_current"], payload["edited_current"], payload["current"]), (220, 217, 215))
        self.assertEqual(payload["expires_at"], 1900)
        self.assertTrue(payload["simulation_only"] and payload["not_applied"])

    def test_send_retry_persistence_recovery_and_atomic_artifacts(self):
        clock = lambda: 1000
        with tempfile.TemporaryDirectory() as root:
            state = protocol.TemperatureCommunicationState(root, now=clock)
            state.start_new(target())
            state.select_file(FILE, file_validator)
            state.send()
            request_id = state.payload["request_id"]
            outbox_bytes = (Path(root) / "communication/outbox.json").read_bytes()
            self.assertIn("reused", state.send())
            self.assertEqual(outbox_bytes, (Path(root) / "communication/outbox.json").read_bytes())
            recovered = protocol.TemperatureCommunicationState(root, now=clock)
            self.assertIsNone(recovered.recovery_error)
            self.assertEqual(recovered.payload["request_id"], request_id)
            self.assertEqual(recovered.target, target())
            self.assertFalse(list((Path(root) / "communication").glob("*.tmp")))

    def test_valid_result_commits_before_exact_ack_and_recovers_result_first(self):
        with tempfile.TemporaryDirectory() as root:
            state = protocol.TemperatureCommunicationState(root, now=lambda: 1000)
            state.start_new(target()); state.select_file(FILE, file_validator); state.send()
            result = selection(state.payload)
            protocol.atomic_write_json(Path(root) / "communication/inbox.json", result)
            self.assertIn("NOT APPLIED", state.poll_inbox())
            saved_state = json.loads((Path(root) / "communication/state.json").read_text())
            receipt = json.loads((Path(root) / "communication/receipt.json").read_text())
            self.assertEqual(saved_state["result"], result)
            self.assertEqual(receipt, protocol.make_ack(result))
            self.assertEqual(set(receipt), set(protocol.RESULT_KEYS))
            self.assertEqual(state.instructions["original_saved_value"], 220)
            self.assertEqual(state.instructions["original_edited_value"], 217)
            self.assertEqual(state.instructions["original_effective_value"], 215)
            recovered = protocol.TemperatureCommunicationState(root, now=lambda: 2500)
            self.assertEqual(recovered.instructions["selected_value"], 205)

    def test_expired_stale_wrong_origin_hash_file_and_conflict_rejected(self):
        payload = protocol.make_forward_payload(target(), FILE, "b" * 32, now=1000, request_id="c" * 32)
        with self.assertRaises(protocol.CommunicationProtocolError):
            protocol.validate_selection_result(payload, selection(payload), now=1900)
        for key, bad in (("origin_id", "d" * 32), ("request_id", "d" * 32),
                         ("context_sha256", "d" * 64), ("file_sha256", "d" * 64),
                         ("file", "other.gcode"), ("file_bytes", 999)):
            candidate = selection(payload); candidate[key] = bad
            with self.subTest(key=key), self.assertRaises(protocol.CommunicationProtocolError):
                protocol.validate_selection_result(payload, candidate, now=1001)
        with tempfile.TemporaryDirectory() as root:
            state = protocol.TemperatureCommunicationState(root, now=lambda: 1000)
            state.start_new(target()); state.select_file(FILE, file_validator); state.send()
            first = selection(state.payload)
            protocol.atomic_write_json(Path(root) / "communication/inbox.json", first); state.poll_inbox()
            self.assertIn("Duplicate", state.poll_inbox())
            conflict = selection(state.payload, 210)
            protocol.atomic_write_json(Path(root) / "communication/inbox.json", conflict)
            with self.assertRaisesRegex(protocol.CommunicationProtocolError, "Conflicting"):
                state.poll_inbox()
            self.assertEqual(state.result, first)

    def test_new_calibration_clears_old_pending_and_old_origin_cannot_commit(self):
        with tempfile.TemporaryDirectory() as root:
            current = [1000]
            state = protocol.TemperatureCommunicationState(root, now=lambda: current[0])
            state.start_new(target()); state.select_file(FILE, file_validator); state.send()
            old = selection(state.payload)
            old_origin = state.origin_id
            with self.assertRaisesRegex(protocol.CommunicationProtocolError, "still active"):
                state.start_new(target())
            current[0] = 1900
            state.start_new(target())
            self.assertNotEqual(state.origin_id, old_origin)
            self.assertFalse((Path(root) / "communication/outbox.json").exists())
            state.select_file(FILE, file_validator); state.send()
            protocol.atomic_write_json(Path(root) / "communication/inbox.json", old)
            with self.assertRaises(protocol.CommunicationProtocolError):
                state.poll_inbox()

    def test_malformed_local_state_fails_closed_and_paths_are_fixed(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root) / "communication"; directory.mkdir()
            (directory / "state.json").write_text('{"schema":"wrong"}', encoding="utf-8")
            state = protocol.TemperatureCommunicationState(root)
            self.assertIsNotNone(state.recovery_error)
            self.assertIsNone(state.target)
            with self.assertRaises(protocol.CommunicationProtocolError):
                protocol.atomic_write_json(Path(root) / "elsewhere.json", {})

    def test_publish_and_ack_never_outrun_durable_state(self):
        with tempfile.TemporaryDirectory() as root:
            state = protocol.TemperatureCommunicationState(root, now=lambda: 1000)
            state.start_new(target()); state.select_file(FILE, file_validator)
            real_write = protocol.atomic_write_json
            def fail_state(path, value):
                if Path(path).name == "state.json":
                    raise OSError("injected state failure")
                return real_write(path, value)
            protocol.atomic_write_json = fail_state
            try:
                with self.assertRaises(OSError):
                    state.send()
            finally:
                protocol.atomic_write_json = real_write
            self.assertIsNone(state.payload)
            self.assertFalse((Path(root) / "communication/outbox.json").exists())

            state.send()
            result = selection(state.payload)
            protocol.atomic_write_json(Path(root) / "communication/inbox.json", result)
            protocol.atomic_write_json = fail_state
            try:
                with self.assertRaises(OSError):
                    state.poll_inbox()
            finally:
                protocol.atomic_write_json = real_write
            self.assertIsNone(state.result)
            self.assertFalse((Path(root) / "communication/receipt.json").exists())
            state.poll_inbox()
            self.assertTrue((Path(root) / "communication/receipt.json").exists())

    def test_outbox_publish_failure_recovers_with_same_request(self):
        with tempfile.TemporaryDirectory() as root:
            state = protocol.TemperatureCommunicationState(root, now=lambda: 1000)
            state.start_new(target()); state.select_file(FILE, file_validator)
            real_write = protocol.atomic_write_json
            def fail_outbox(path, value):
                if Path(path).name == "outbox.json":
                    raise OSError("injected outbox failure")
                return real_write(path, value)
            protocol.atomic_write_json = fail_outbox
            try:
                with self.assertRaises(OSError):
                    state.send()
            finally:
                protocol.atomic_write_json = real_write
            request_id = state.payload["request_id"]
            recovered = protocol.TemperatureCommunicationState(root, now=lambda: 1000)
            self.assertEqual(recovered.payload["request_id"], request_id)
            self.assertIn("reused", recovered.send())
            outbox = json.loads((Path(root) / "communication/outbox.json").read_text())
            self.assertEqual(outbox["payload"]["request_id"], request_id)

    def test_filename_and_identity_boundaries_match_native_contract(self):
        for name in ("UPPER.GCODE", "bad..gcode", "bad\x7f.gcode", "../bad.gcode"):
            candidate = dict(FILE, name=name)
            with self.subTest(name=name), self.assertRaises(protocol.CommunicationProtocolError):
                protocol.make_forward_payload(target(), candidate, "b" * 32, now=1000, request_id="c" * 32)

    def test_delivery_status_is_exact_correlated_and_locally_mapped(self):
        payload = protocol.make_forward_payload(target(), FILE, "b" * 32, now=1000, request_id="c" * 32)
        for phase in protocol.DELIVERY_PHASES:
            value = protocol.validate_delivery(payload, delivery(payload, phase))
            self.assertEqual(value["phase"], phase)
            self.assertIn(phase, protocol.DELIVERY_MESSAGES)
        for key, bad in (("request_id", "d" * 32), ("origin_id", "d" * 32),
                         ("context_sha256", "d" * 64), ("phase", "relay.internal: failed")):
            candidate = delivery(payload); candidate[key] = bad
            with self.subTest(key=key), self.assertRaises(protocol.CommunicationProtocolError):
                protocol.validate_delivery(payload, candidate)
        candidate = delivery(payload); candidate["error"] = "private relay detail"
        with self.assertRaises(protocol.CommunicationProtocolError):
            protocol.validate_delivery(payload, candidate)

    def test_stale_delivery_cannot_replace_status_target_or_result(self):
        with tempfile.TemporaryDirectory() as root:
            state = protocol.TemperatureCommunicationState(root, now=lambda: 1000)
            state.start_new(target()); state.select_file(FILE, file_validator); state.send()
            directory = Path(root) / "communication"
            protocol.atomic_write_json(directory / "delivery.json", delivery(state.payload, "retrying"))
            self.assertEqual(state.poll_delivery(), protocol.DELIVERY_MESSAGES["retrying"])
            retained_target = copy.deepcopy(state.target)
            stale = delivery(state.payload, "failed"); stale["origin_id"] = "d" * 32
            protocol.atomic_write_json(directory / "delivery.json", stale)
            with self.assertRaises(protocol.CommunicationProtocolError):
                state.poll_delivery()
            self.assertEqual(state.delivery_phase, "retrying")
            self.assertEqual(state.target, retained_target)
            result = selection(state.payload)
            protocol.atomic_write_json(directory / "inbox.json", result); state.poll_inbox()
            instructions = copy.deepcopy(state.instructions)
            with self.assertRaises(protocol.CommunicationProtocolError):
                state.poll_delivery()
            self.assertEqual(state.instructions, instructions)

    def test_receipt_before_native_ack_keeps_slot_locked_across_restart(self):
        with tempfile.TemporaryDirectory() as root:
            state = protocol.TemperatureCommunicationState(root, now=lambda: 1000)
            state.start_new(target()); state.select_file(FILE, file_validator); state.send()
            directory = Path(root) / "communication"
            protocol.atomic_write_json(directory / "inbox.json", selection(state.payload))
            state.poll_inbox()
            instructions = copy.deepcopy(state.instructions)
            self.assertTrue((directory / "receipt.json").exists())
            self.assertFalse(state.can_start_new())
            with self.assertRaisesRegex(protocol.CommunicationProtocolError, "still active"):
                state.start_new(target())
            self.assertTrue((directory / "outbox.json").exists())
            self.assertTrue((directory / "inbox.json").exists())
            self.assertTrue((directory / "receipt.json").exists())

            protocol.atomic_write_json(directory / "delivery.json", delivery(state.payload, "waiting_companion"))
            state.poll_delivery()
            self.assertFalse(state.can_start_new())
            recovered = protocol.TemperatureCommunicationState(root, now=lambda: 1000)
            self.assertFalse(recovered.can_start_new())
            self.assertEqual(recovered.instructions, instructions)

            protocol.atomic_write_json(directory / "delivery.json", delivery(state.payload, "delivered"))
            recovered.poll_delivery()
            self.assertTrue(recovered.delivery_delivered)
            self.assertTrue(recovered.can_start_new())
            self.assertEqual(recovered.instructions, instructions)
            terminal = protocol.TemperatureCommunicationState(root, now=lambda: 1000)
            self.assertTrue(terminal.delivery_delivered)
            self.assertTrue(terminal.can_start_new())
            protocol.atomic_write_json(directory / "delivery.json", delivery(state.payload, "failed"))
            self.assertEqual(terminal.poll_delivery(), protocol.DELIVERY_MESSAGES["delivered"])
            self.assertEqual(terminal.instructions, instructions)

    def test_delivered_does_not_unlock_when_terminal_commit_fails(self):
        with tempfile.TemporaryDirectory() as root:
            state = protocol.TemperatureCommunicationState(root, now=lambda: 1000)
            state.start_new(target()); state.select_file(FILE, file_validator); state.send()
            directory = Path(root) / "communication"
            protocol.atomic_write_json(directory / "inbox.json", selection(state.payload)); state.poll_inbox()
            protocol.atomic_write_json(directory / "delivery.json", delivery(state.payload, "delivered"))
            real_persist = state._persist
            state._persist = lambda: (_ for _ in ()).throw(OSError("injected terminal-state failure"))
            try:
                with self.assertRaises(OSError):
                    state.poll_delivery()
            finally:
                state._persist = real_persist
            self.assertFalse(state.delivery_delivered)
            self.assertFalse(state.can_start_new())
            self.assertEqual(state.instructions["status"], "NOT APPLIED")

    def test_delivered_before_local_result_cannot_unlock_slot(self):
        with tempfile.TemporaryDirectory() as root:
            state = protocol.TemperatureCommunicationState(root, now=lambda: 1000)
            state.start_new(target()); state.select_file(FILE, file_validator); state.send()
            protocol.atomic_write_json(Path(root) / "communication/delivery.json", delivery(state.payload, "delivered"))
            with self.assertRaisesRegex(protocol.CommunicationProtocolError, "no committed"):
                state.poll_delivery()
            self.assertFalse(state.delivery_delivered)
            self.assertFalse(state.can_start_new())

    def test_old_state_without_terminal_field_recovers_locked(self):
        with tempfile.TemporaryDirectory() as root:
            state = protocol.TemperatureCommunicationState(root, now=lambda: 1000)
            state.start_new(target()); state.select_file(FILE, file_validator); state.send()
            path = Path(root) / "communication/state.json"
            old = json.loads(path.read_text()); old.pop("delivery_delivered")
            protocol.atomic_write_json(path, old)
            recovered = protocol.TemperatureCommunicationState(root, now=lambda: 1000)
            self.assertIsNone(recovered.recovery_error)
            self.assertFalse(recovered.delivery_delivered)
            self.assertFalse(recovered.can_start_new())

    def test_expiry_is_visible_without_clearing_pending_state(self):
        current = [1000]
        with tempfile.TemporaryDirectory() as root:
            state = protocol.TemperatureCommunicationState(root, now=lambda: current[0])
            state.start_new(target()); state.select_file(FILE, file_validator); state.send()
            request_id = state.payload["request_id"]
            origin_id = state.origin_id
            self.assertFalse(state.is_expired())
            current[0] = 1900
            self.assertTrue(state.is_expired())
            self.assertEqual(state.payload["request_id"], request_id)
            self.assertTrue(state.can_start_new())
            state.start_new(target())
            self.assertNotEqual(state.origin_id, origin_id)

    def test_expiry_allows_explicit_retirement_without_silent_result_mutation(self):
        current = [1000]
        with tempfile.TemporaryDirectory() as root:
            state = protocol.TemperatureCommunicationState(root, now=lambda: current[0])
            state.start_new(target()); state.select_file(FILE, file_validator); state.send()
            directory = Path(root) / "communication"
            protocol.atomic_write_json(directory / "inbox.json", selection(state.payload)); state.poll_inbox()
            result = copy.deepcopy(state.result)
            instructions = copy.deepcopy(state.instructions)
            self.assertFalse(state.can_start_new())
            current[0] = state.payload["expires_at"]
            self.assertTrue(state.can_start_new())
            self.assertEqual(state.result, result)
            self.assertEqual(state.instructions, instructions)
            self.assertTrue((directory / "receipt.json").exists())
            state.start_new(target())
            self.assertIsNone(state.result)
            self.assertIsNone(state.instructions)
            self.assertFalse((directory / "receipt.json").exists())


class GeneratedCompanionTests(unittest.TestCase):
    def test_accepted_sources_unchanged_and_generated_capabilities_preserved(self):
        self.assertEqual(hashlib.sha256((ROOT / "plugin/helix_calibration.py").read_bytes()).hexdigest(), generator.BASE_SHA256)
        self.assertEqual(hashlib.sha256((ROOT / "scripts/orca-oct15-plugin.py").read_bytes()).hexdigest(), generator.OCT15_GENERATOR_SHA256)
        source = generator.generate()
        self.assertIn('# version = "0.5.0"', source)
        for capability in ("HelixCalibrationContext", "ExportOrcaContextJson", "NightlyQualificationPanel",
                           "TemperatureRoundTripPanel", "TemperatureCommunicationPanel"):
            self.assertIn("orca.register_capability(" + capability + ")", source)
        self.assertIn('COMMUNICATION_ACTION_NAME = "Helix Temperature Communication (no printing)"', source)
        for banned in ("import socket", "import subprocess", "import threading", "import requests", "import pyautogui"):
            self.assertNotIn(banned, source)

    def test_generated_panel_uses_original_reader_and_reports_profile_switch(self):
        with tempfile.TemporaryDirectory() as root:
            generated = Path(root) / "helix_calibration.py"
            generated.write_text(generator.generate(), encoding="utf-8")
            previous = test_plugin.PLUGIN_PATH; test_plugin.PLUGIN_PATH = generated
            try:
                plugin, orca = test_plugin.load_plugin()
            finally:
                test_plugin.PLUGIN_PATH = previous
            bundle = test_plugin.FakeBundle(values={"nozzle_diameter": "0.4", "nozzle_temperature": "217"}, names=["Original PLA"])
            bundle.filaments = test_plugin.FakeCollection(
                test_plugin.FakePreset("Original PLA", values={"nozzle_temperature": "220"}),
                test_plugin.FakePreset("Original PLA", dirty=True, values={"nozzle_temperature": "217"}))
            host = test_plugin.FakeHost(bundle, storage_root=root, build="6a7763f0"); host.ui = test_plugin.FakeUI(); orca.host = host
            panel = plugin.TemperatureCommunicationPanel(); panel.execute(); panel.on_message({"command": "ready"}); panel.on_message({"command": "freeze"})
            self.assertEqual(panel.state.target["saved_temperature"], 220)
            bundle.names = ["Other PLA"]
            bundle.filaments = test_plugin.FakeCollection(test_plugin.FakePreset("Other PLA", values={"nozzle_temperature": "230"}), test_plugin.FakePreset("Other PLA", values={"nozzle_temperature": "230"}))
            panel.on_message({"command": "poll"})
            self.assertFalse(panel.panel.posts[-1]["current_matches_target"])
            self.assertEqual(panel.state.target["filament"]["selected_saved"]["name"], "Original PLA")


if __name__ == "__main__":
    unittest.main()
