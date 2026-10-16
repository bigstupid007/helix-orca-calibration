import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
EXTENSION = ROOT / "integration/temperature-communication/native-extension.lua"
TEMPLATES = ROOT / "integration/temperature-communication/ui"


def load_generator():
    path = ROOT / "scripts/temperature-communication-plugin.py"
    spec = importlib.util.spec_from_file_location("native_generator", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


generator = load_generator()


class TemperatureCommunicationNativeTests(unittest.TestCase):
    def test_accepted_baseline_is_hash_locked(self):
        self.assertEqual(generator.verify_baseline(), generator.BASELINE_HASHES)

    def test_generator_keeps_identity_and_adds_only_storage_permission(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "orcacal"
            report = generator.generate(output)
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertEqual(manifest["id"], "orcacal")
            self.assertEqual(manifest["helix_version"], ">=1.1.0-beta.9")
            self.assertEqual(manifest["permissions"], ["storage"])
            self.assertEqual(manifest["widgets"][0]["component"], "orcacal__tile")
            generated_main = (output / "main.lua").read_bytes()
            accepted_main = (ROOT / "helix-plugin/orcacal/main.lua").read_bytes()
            self.assertTrue(generated_main.startswith(accepted_main + b"\n"))
            self.assertEqual(report["accepted_baseline"], generator.BASELINE_HASHES)
            self.assertEqual(json.loads((output / generator.MARKER_NAME).read_text()), generator.MARKER)
            self.assertEqual(
                hashlib.sha256((output / "ui/orcacal__tile.xml").read_bytes()).hexdigest(),
                generator.BASELINE_HASHES["ui/orcacal__tile.xml"],
            )

    def test_generator_replaces_only_an_exact_owned_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "orcacal"
            generator.generate(output)
            first = (output / "main.lua").read_bytes()
            generator.generate(output, replace=True)
            self.assertEqual((output / "main.lua").read_bytes(), first)

            arbitrary = root / "arbitrary"
            arbitrary.mkdir()
            sentinel = arbitrary / "keep.txt"
            sentinel.write_text("owned by somebody else")
            with self.assertRaises(generator.GenerationError):
                generator.generate(arbitrary, replace=True)
            self.assertEqual(sentinel.read_text(), "owned by somebody else")

    def test_generator_refuses_symlink_tamper_and_extra_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "orcacal"
            generator.generate(output)
            (output / "unexpected.txt").write_text("do not delete")
            with self.assertRaises(generator.GenerationError):
                generator.generate(output, replace=True)
            self.assertTrue((output / "unexpected.txt").is_file())

            clean = root / "with-extra-directory"
            generator.generate(clean)
            (clean / "unexpected-empty").mkdir()
            with self.assertRaises(generator.GenerationError):
                generator.generate(clean, replace=True)
            self.assertTrue((clean / "unexpected-empty").is_dir())

            target = root / "target"
            target.mkdir()
            sentinel = target / "keep.txt"
            sentinel.write_text("safe")
            link = root / "linked-output"
            link.symlink_to(target, target_is_directory=True)
            with self.assertRaises(generator.GenerationError):
                generator.generate(link, replace=True)
            self.assertEqual(sentinel.read_text(), "safe")

    def test_request_contract_is_exact_and_bounded(self):
        source = EXTENSION.read_text()
        for marker in (
            "exact_keys(data, REQUEST_KEYS, 20)", 'data.schema ~= REQUEST_SCHEMA',
            "data.simulation_only ~= true", "data.not_applied ~= true",
            "exact_lower_hex(data.request_id, 32)", "exact_lower_hex(data.origin_id, 32)",
            "exact_lower_hex(data.context_sha256, 64)", "exact_lower_hex(data.file_sha256, 64)",
            "data.file_bytes < 1", "data.file_bytes > MAX_FILE_BYTES",
            "local MAX_FILE_BYTES = 20000000", "utf8.len(value) ~= nil",
            'value:find("\\127", 1, true) == nil', 'data.setting ~= "nozzle_temperature"',
            "exact_choices(data.choices)", "data.ttl_seconds < 1", "data.ttl_seconds > 900",
            "data.expires_at < 1",
        ):
            self.assertIn(marker, source)
        self.assertIn("local TEMPERATURE_CHOICES = {230, 225, 220, 215, 210, 205, 200, 195, 190}", source)
        for marker in (
            "exact_keys(data, ENVELOPE_KEYS, 2)", "exact_keys(data, LEASE_KEYS, 2)",
            "data.issued_eventtime < 0", "data.expires_eventtime <= data.issued_eventtime",
            "data.expires_eventtime - data.issued_eventtime > request.ttl_seconds",
            "local request, lease = validate_envelope(data)",
        ):
            self.assertIn(marker, source)

    def test_result_and_ack_have_exact_eleven_key_contract(self):
        source = EXTENSION.read_text()
        self.assertIn("exact_keys(result, RESULT_KEYS, 11)", source)
        self.assertIn('result.schema == schema', source)
        self.assertIn('local RESULT_SCHEMA = "helix-orca-temperature-selection/v1"', source)
        self.assertIn('local ACK_SCHEMA = "helix-orca-temperature-ack/v1"', source)
        keys = re.search(r"local RESULT_KEYS = \{(.*?)\n\}", source, re.S).group(1)
        self.assertEqual(set(re.findall(r"([a-z0-9_]+)=true", keys)), {
            "schema", "simulation_only", "not_applied", "request_id", "origin_id",
            "context_sha256", "file_sha256", "file", "file_bytes", "setting", "value",
        })
        result_literal = source[source.index("temperature_session.result = {"):source.index("tc_returned_value:set", source.index("temperature_session.result = {"))]
        self.assertNotIn("expires_at", result_literal)

    def test_state_machine_preserves_selection_and_requires_exact_ack(self):
        source = EXTENSION.read_text()
        for marker in (
            "same_request(temperature_session.request, request)",
            "same_identity(temperature_session.request, request)",
            'tc_status:set("Rejected conflicting request identity")',
            'tc_status:set("Busy with an earlier Temperature request")',
            "temperature_session.recovery_required = false",
            "temperature_session.result.value ~= value",
            'tc_status:set("First selection is immutable; waiting for its acknowledgement")',
            "data.value ~= temperature_session.result.value",
            "session.acknowledged = true",
            "session.lease.expires_eventtime - current",
            "MAX_TOMBSTONES = 16",
        ):
            self.assertIn(marker, source)
        queued = source.index('set_state("queued")')
        persisted = source.index("persist_session()", queued)
        waiting = source.index('set_state("waiting")', persisted)
        self.assertLess(queued, persisted)
        self.assertLess(persisted, waiting)
        self.assertNotIn("persisted", source.lower())

        duplicate = source[source.index("if temperature_session and same_request"):
                           source.index("if temperature_session and same_identity")]
        self.assertIn("math.min(temperature_session.lease.expires_eventtime", duplicate)
        self.assertNotIn("temperature_session.lease = lease", duplicate)
        self.assertIn("arm_expiry(current)", duplicate)
        expired_gate = source[source.index("if temperature_session and not temperature_session.acknowledged"):
                              source.index("local candidate = new_session")]
        self.assertIn('temperature_session.state ~= "expired"', expired_gate)
        self.assertIn('temperature_session.state == "expired"', expired_gate)
        self.assertIn("remember_tombstone(temperature_session, temperature_session.request)", source)

    def test_expired_storage_survives_restart_and_rejects_late_ack(self):
        source = EXTENSION.read_text()
        restore_start = source.index("local function restore_session")
        restore = source[restore_start:source.index("\nrestore_session()", restore_start)]
        for marker in (
            'local stored_expired = stored.state == "expired"',
            'recovery_required=not stored_expired',
            'state=stored_expired and "expired"',
            "remember_tombstone(temperature_session, request)",
            "local lease = validate_lease(stored.lease, request)",
        ):
            self.assertIn(marker, restore)
        self.assertNotIn("arm_expiry", restore)
        ack = source[source.index("local function on_temperature_ack"):
                     source.index("helix.moonraker.on_agent_event")]
        self.assertIn('temperature_session.state == "expired"', ack)

    def test_fresh_request_opens_accepted_stack_but_duplicate_does_not_reopen(self):
        source = EXTENSION.read_text()
        opener = source[source.index("local function open_request_stack"):
                        source.index("local function new_session")]
        self.assertIn('helix.ui.overlay("orcacal__wizard"', opener)
        self.assertIn('helix.ui.overlay("orcacal__temperature"', opener)
        self.assertEqual(opener.count("on_close = function()"), 2)
        duplicate = source[source.index("if temperature_session and same_request"):
                           source.index("if temperature_session and same_identity")]
        self.assertNotIn("open_request_stack", duplicate)
        fresh = source[source.index("temperature_session = candidate"):
                       source.index("local function on_temperature_ack")]
        self.assertIn("open_request_stack()", fresh)

    def test_storage_shape_is_one_bounded_session_and_never_claims_flush_success(self):
        source = EXTENSION.read_text()
        self.assertEqual(source.count('helix.storage.set, "session"'), 1)
        self.assertEqual(source.count('helix.storage.get, "session"'), 1)
        for marker in (
            'request=request, lease=lease, result=nil, acknowledged=false, recovery_required=false',
            'state="received", tombstones=bounded_tombstones(tombstones)',
            'tc_status:set("Selection queued; waiting for companion acknowledgement")',
            'tc_status:set("Waiting for originating companion acknowledgement")',
            'tc_status:set("Returned to originating companion \\u{00B7} not applied")',
        ):
            self.assertIn(marker, source)

    def test_only_permissionless_read_query_and_no_print_lifecycle_capabilities(self):
        source = EXTENSION.read_text()
        for forbidden in (
            "helix.http", "helix.moonraker.query",
            "helix.moonraker.subscribe", "helix.gcode", "helix.printer",
            "printer.print", "mock_only", "finish_simulation", "print_state",
        ):
            self.assertNotIn(forbidden, source)
        self.assertEqual(source.count('helix.moonraker.call("printer.objects.query"'), 1)
        self.assertIn('objects={print_stats={"state"}}', source)
        self.assertEqual(source.count("helix.moonraker.on_agent_event"), 2)

    def test_clock_gate_covers_receive_return_ack_and_restart(self):
        source = EXTENSION.read_text()
        self.assertGreaterEqual(source.count("query_eventtime(generation)"), 4)
        self.assertGreaterEqual(source.count("generation ~= operation_generation"), 3)
        self.assertIn("current >= lease.issued_eventtime and current < lease.expires_eventtime", source)
        self.assertIn("session.lease.expires_eventtime - current <= RETURN_SAFETY_SECONDS", source)
        self.assertIn("local RETURN_SAFETY_SECONDS = 2", source)
        self.assertIn("local QUERY_TIMEOUT_MS = 1000", source)
        self.assertIn("return current + QUERY_LATENCY_SECONDS", source)
        self.assertIn("if operation_generation == generation then next_operation() end", source)
        self.assertIn("local IDLE_PRINT_STATES = {standby=true, complete=true, cancelled=true}", source)
        self.assertIn("result.status", source)
        self.assertIn("status.print_stats", source)
        self.assertIn("not IDLE_PRINT_STATES[state]", source)
        restore = source[source.index("local function restore_session"):source.index("\nrestore_session()")]
        self.assertIn("recovery_required=not stored_expired", restore)
        self.assertNotIn("query_eventtime", restore)
        self.assertNotIn("arm_expiry", restore)
        ack = source[source.index("local function on_temperature_ack"):
                     source.index("helix.moonraker.on_agent_event")]
        queued = ack.index('tc_status:set("Acknowledgement received; committing returned state")')
        delay = ack.index("helix.timer.after(650", queued)
        returned = ack.index('session.state = "returned"', delay)
        cancel = ack.index("cancel_expiry_timer()", returned)
        self.assertLess(queued, delay)
        self.assertLess(delay, returned)
        self.assertLess(returned, cancel)

    def test_templates_extend_existing_native_shell_and_keep_back(self):
        wizard = ET.parse(TEMPLATES / "orcacal__wizard.xml").getroot()
        detail = ET.parse(TEMPLATES / "orcacal__temperature.xml").getroot()
        wizard_view = next(wizard.iter("view"))
        detail_view = next(detail.iter("view"))
        self.assertEqual(wizard_view.attrib["name"], "orcacal__wizard")
        self.assertEqual(detail_view.attrib["name"], "orcacal__temperature")
        self.assertEqual(wizard_view.attrib["extends"], "overlay_panel")
        self.assertEqual(detail_view.attrib["extends"], "overlay_panel")
        self.assertIsNone(next((n for n in wizard.iter() if n.attrib.get("name") == "back_button"), None))
        names = {node.attrib.get("name") for node in detail.iter()}
        self.assertIn("orcacal__start_button", names)
        self.assertIn("orcacal__temperature_selector", names)
        self.assertIn("orcacal__return_selection", names)
        selector = next(node for node in detail.iter("lv_dropdown"))
        self.assertEqual(selector.attrib["options"].split("\n"), [
            "230°C", "225°C", "220°C", "215°C", "210°C",
            "205°C", "200°C", "195°C", "190°C",
        ])
        for root in (wizard, detail):
            content = next(node for node in root.iter("lv_obj") if node.attrib.get("flex_grow") == "1")
            self.assertEqual(content.attrib["width"], "100%")
            self.assertEqual(content.attrib["scrollable"], "true")

    def test_qualifier_is_beta9_network_none_and_all_viewports(self):
        source = (ROOT / "scripts/temperature-communication-qualify.py").read_text()
        self.assertIn("beta9.verify_cache()", source)
        self.assertIn("for entry in accepted.VIEWPORTS", source)
        self.assertIn('"container_network": "none"', source)
        self.assertIn("generator.verify_baseline()", source)
        self.assertIn("request-updates-existing-temperature-detail", source)
        self.assertIn("request-auto-opens-accepted-stack", source)
        self.assertIn("ack-enters-returned", source)
        self.assertNotIn("requests.", source)
        self.assertIn("LOADED_SOURCE_SNAPSHOT = qualification_source_hashes()", source)
        self.assertIn("verify_source_snapshot()", source)
        self.assertIn('"clock_fixture"', source)

    def test_windows_origin_driver_leaves_result_unacknowledged(self):
        source = (ROOT / "scripts/temperature-communication-native-driver.py").read_text()
        for marker in (
            'parser.add_argument("--payload"', 'parser.add_argument("--result-output"',
            'accepted._assert_overlay(accepted.ctl(name, "current")',
            'accepted.ctl(name, "set_value"', 'session.get("result") != expected_result',
            'session.get("acknowledged") is not False', '"container_network": "none"',
            '"awaiting-originating-companion-ack"',
        ):
            self.assertIn(marker, source)
        self.assertIn("if expiry_proof:", source)

    def test_native_driver_has_bounded_expiry_restart_proof(self):
        source = (ROOT / "scripts/temperature-communication-native-driver.py").read_text()
        for marker in (
            'parser.add_argument("--expiry-proof"',
            'if remaining <= 2 or remaining > 5',
            'qualification.tap(name, "orcacal__qualify-ack"',
            '"late exact ACK changed an expired session"',
            '"expired restart re-enabled native selection"',
            '"duplicate expired request reopened native overlays"',
            '"expired-state-survived-restart"',
            '"duplicate-expired-recovery-rejected"',
        ):
            self.assertIn(marker, source)

    def test_driver_has_recovery_and_clock_failure_native_proofs(self):
        source = (ROOT / "scripts/temperature-communication-native-driver.py").read_text()
        for marker in (
            'parser.add_argument("--recovery-proof"',
            'parser.add_argument("--clock-failure-proof"',
            '"restart enabled selection before lease recovery"',
            '"validated exact recovery did not enable selection"',
            '"non-idle query state accepted a request"',
            '"missing query clock accepted a request"',
            '"delayed expired envelope opened native UI"',
        ):
            self.assertIn(marker, source)


if __name__ == "__main__":
    unittest.main()
