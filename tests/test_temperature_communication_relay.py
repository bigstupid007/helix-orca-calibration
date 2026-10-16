import importlib.util
import json
from pathlib import Path
import tempfile
import time
import unittest
from urllib.error import HTTPError


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/temperature-communication-relay.py"
spec = importlib.util.spec_from_file_location("temperature_communication_relay", SCRIPT)
relay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(relay)


def valid_outbox(now=1_800_000_000):
    target = {
        "runtime": {"version": "2.5.0-dev", "build": "6a7763f0"},
        "printer": {"selected_saved": {"name": "Voron 2.4 300"}},
        "filament": {"selected_saved": {"name": "Generic PLA"}},
        "process": {"selected_saved": {"name": "0.20 Standard"}},
        "nozzle_mm": 0.4,
        "saved_temperature": 215,
        "edited_temperature": 217,
        "effective_temperature": 218,
    }
    payload = {
        "schema": relay.SESSION_SCHEMA,
        "simulation_only": True,
        "not_applied": True,
        "request_id": "1" * 32,
        "origin_id": "2" * 32,
        "context_sha256": relay.canonical_sha256(target),
        "file_sha256": "a" * 64,
        "file": "temperature-230-190-step5.gcode",
        "file_bytes": 12345,
        "printer": "Voron 2.4 300",
        "filament": "Generic PLA",
        "process": "0.20 Standard",
        "nozzle_mm": 0.4,
        "saved_current": 215,
        "edited_current": 217,
        "current": 218,
        "setting": relay.SETTING,
        "choices": list(relay.CHOICES),
        "expires_at": now + 600,
        "ttl_seconds": 600,
    }
    return {"schema": relay.OUTBOX_SCHEMA, "target": target, "payload": payload}


def selection(request, value=205):
    return {
        "schema": relay.SELECTION_SCHEMA,
        "simulation_only": True,
        "not_applied": True,
        "request_id": request["request_id"],
        "origin_id": request["origin_id"],
        "context_sha256": request["context_sha256"],
        "file_sha256": request["file_sha256"],
        "file": request["file"],
        "file_bytes": request["file_bytes"],
        "setting": request["setting"],
        "value": value,
    }


class FakeClock:
    def __init__(self, wall=1_800_000_000):
        self.wall = float(wall)
        self.mono = 0.0

    def time(self):
        return self.wall

    def monotonic(self):
        return self.mono

    def sleep(self, seconds):
        self.wall += seconds
        self.mono += seconds


class FakeSpare:
    def __init__(self, outbox, outbox_delay=0):
        self.files = {"outbox.json": outbox} if outbox is not None else {}
        self.outbox_delay = outbox_delay
        self.script_hashes = ["b" * 64]
        self.writes = []

    def read_json(self, name, limit=relay.MAX_REQUEST_BYTES):
        if name == "outbox.json" and self.outbox_delay:
            self.outbox_delay -= 1
            return None
        return self.files.get(name)

    def write_json(self, name, value):
        self.files[name] = json.loads(json.dumps(value))
        self.writes.append((name, json.loads(json.dumps(value))))
        if name == "inbox.json":
            self.files["receipt.json"] = relay.make_ack(value)


class FakePhysical:
    def __init__(self, request, result_value=205):
        self.request = request
        self.result = selection(request, result_value)
        self.events = []
        self.ready_checks = 0
        self.file_checks = []
        self.acknowledged = False
        self.request_seen = False
        self.read_failures = 0
        self.send_failures = 0
        self.send_attempts = []

    def assert_ready(self):
        self.ready_checks += 1
        return {"print_state": "standby"}

    def verify_file(self, payload):
        self.file_checks.append(json.loads(json.dumps(payload)))
        return {"bytes": payload["file_bytes"], "sha256": payload["file_sha256"]}

    def send_event(self, event, data):
        self.send_attempts.append((event, json.loads(json.dumps(data))))
        if self.send_failures:
            self.send_failures -= 1
            raise relay.TransientRelayError("simulated transient send failure")
        self.events.append((event, json.loads(json.dumps(data))))
        if event == relay.REQUEST_EVENT:
            self.request_seen = True
        elif event == relay.ACK_EVENT:
            self.acknowledged = True

    def read_native_storage(self):
        if self.read_failures:
            self.read_failures -= 1
            raise relay.TransientRelayError("simulated physical read failure")
        if not self.request_seen:
            return {}
        return {
            "session": {
                "request": self.request,
                "result": self.result,
                "acknowledged": self.acknowledged,
                "recovery_required": not self.acknowledged,
                "state": "returned" if self.result else "waiting",
                "completed_request_ids": [],
            }
        }


class RelayContractTests(unittest.TestCase):
    def test_exact_request_selection_and_ack_contracts(self):
        box = valid_outbox()
        self.assertIs(relay.validate_outbox(box, 1_800_000_000), box)
        result = selection(box["payload"])
        self.assertIs(relay.validate_selection_result(box["payload"], result, 1_800_000_000), result)
        ack = relay.make_ack(result)
        self.assertEqual(set(ack), relay._result_keys())
        self.assertEqual(11, len(ack))
        self.assertIs(relay.validate_ack(box["payload"], ack, 1_800_000_000), ack)
        delivery = relay.make_delivery(box["payload"], "waiting_selection")
        self.assertEqual(5, len(delivery))
        self.assertIs(relay.validate_delivery(box["payload"], delivery), delivery)

    def test_contract_rejects_extra_stale_conflicting_and_unprepared_values(self):
        box = valid_outbox()
        cases = []
        extra = json.loads(json.dumps(box))
        extra["payload"]["print"] = False
        cases.append(extra)
        stale = json.loads(json.dumps(box))
        stale["payload"]["expires_at"] = 1_799_999_999
        cases.append(stale)
        context = json.loads(json.dumps(box))
        context["target"]["normal_profile"] = True
        cases.append(context)
        flattened = json.loads(json.dumps(box))
        flattened["payload"]["printer"] = "Different printer"
        cases.append(flattened)
        runtime = json.loads(json.dumps(box))
        runtime["target"]["runtime"]["build"] = "unqualified"
        runtime["payload"]["context_sha256"] = relay.canonical_sha256(runtime["target"])
        cases.append(runtime)
        for value in cases:
            with self.subTest(value=value), self.assertRaises(relay.RelayError):
                relay.validate_outbox(value, 1_800_000_000)

        result = selection(box["payload"], 204)
        with self.assertRaisesRegex(relay.RelayError, "prepared choices"):
            relay.validate_selection_result(box["payload"], result, 1_800_000_000)
        conflict = selection(box["payload"])
        conflict["origin_id"] = "3" * 32
        with self.assertRaisesRegex(relay.RelayError, "origin_id"):
            relay.validate_selection_result(box["payload"], conflict, 1_800_000_000)

    def test_true_end_to_end_state_waits_for_companion_receipt_before_native_ack(self):
        clock = FakeClock()
        outbox = valid_outbox(int(clock.wall))
        spare = FakeSpare(outbox)
        physical = FakePhysical(outbox["payload"])
        with tempfile.TemporaryDirectory() as temp:
            result = relay.SessionRelay(
                physical, spare, Path(temp), clock.time, clock.monotonic,
                clock.sleep, poll_seconds=0.01,
            ).run()
            journal = json.loads((Path(temp) / ("1" * 32 + ".json")).read_text())

        self.assertEqual("complete", result["state"])
        self.assertEqual(205, result["value"])
        self.assertEqual(
            ["delivery.json", "delivery.json", "inbox.json", "delivery.json", "delivery.json"],
            [name for name, _ in spare.writes],
        )
        self.assertEqual(
            ["delivering", "waiting_selection", "waiting_companion", "delivered"],
            [value["phase"] for name, value in spare.writes if name == "delivery.json"],
        )
        self.assertEqual(
            [relay.REQUEST_EVENT, relay.ACK_EVENT],
            [event for event, _ in physical.events],
        )
        self.assertEqual(relay.make_ack(spare.files["inbox.json"]), physical.events[-1][1])
        self.assertGreaterEqual(physical.ready_checks, 3)
        self.assertEqual([outbox["payload"]], physical.file_checks)
        self.assertTrue(physical.acknowledged)
        self.assertEqual("complete", journal["phase"])
        self.assertNotIn("target", journal)
        self.assertNotIn("api_key", json.dumps(journal))

    def test_recovery_resends_only_the_same_request_after_rechecking_file(self):
        clock = FakeClock()
        outbox = valid_outbox(int(clock.wall))
        spare = FakeSpare(outbox)
        physical = FakePhysical(outbox["payload"])
        physical.read_failures = relay.MAX_TRANSPORT_ATTEMPTS
        with tempfile.TemporaryDirectory() as temp:
            worker = relay.SessionRelay(
                physical, spare, Path(temp), clock.time, clock.monotonic,
                clock.sleep, poll_seconds=0.01,
            )
            with self.assertRaisesRegex(relay.RelayError, "five bounded attempts"):
                worker.run()
            result = worker.run()

        requests = [data for event, data in physical.events if event == relay.REQUEST_EVENT]
        self.assertEqual("complete", result["state"])
        self.assertEqual(2, len(requests))
        self.assertEqual(requests[0], requests[1])
        self.assertEqual([outbox["payload"], outbox["payload"]], physical.file_checks)

    def test_transient_send_reconnects_at_most_five_times_with_identical_request(self):
        clock = FakeClock()
        outbox = valid_outbox(int(clock.wall))
        spare = FakeSpare(outbox)
        physical = FakePhysical(outbox["payload"])
        physical.send_failures = 2
        with tempfile.TemporaryDirectory() as temp:
            result = relay.SessionRelay(
                physical, spare, Path(temp), clock.time, clock.monotonic,
                clock.sleep, poll_seconds=0.01,
            ).run()
        request_attempts = [data for event, data in physical.send_attempts if event == relay.REQUEST_EVENT]
        self.assertEqual("complete", result["state"])
        self.assertEqual(3, len(request_attempts))
        self.assertTrue(all(value == outbox["payload"] for value in request_attempts))
        phases = [value["phase"] for name, value in spare.writes if name == "delivery.json"]
        self.assertEqual(2, phases.count("retrying"))
        self.assertEqual("delivered", phases[-1])

    def test_fifth_transient_attempt_fails_with_static_delivery_status(self):
        clock = FakeClock()
        outbox = valid_outbox(int(clock.wall))
        spare = FakeSpare(outbox)
        physical = FakePhysical(outbox["payload"])
        physical.send_failures = relay.MAX_TRANSPORT_ATTEMPTS
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(relay.RelayError, "five bounded attempts"):
                relay.SessionRelay(
                    physical, spare, Path(temp), clock.time, clock.monotonic,
                    clock.sleep, poll_seconds=0.01,
                ).run()
        self.assertEqual(relay.MAX_TRANSPORT_ATTEMPTS, len(physical.send_attempts))
        delivery = spare.files["delivery.json"]
        self.assertEqual(relay.make_delivery(outbox["payload"], "failed"), delivery)
        self.assertNotIn("error", delivery)

    def test_operator_can_start_relay_before_outbox_exists(self):
        clock = FakeClock()
        outbox = valid_outbox(int(clock.wall))
        spare = FakeSpare(outbox, outbox_delay=3)
        physical = FakePhysical(outbox["payload"])
        with tempfile.TemporaryDirectory() as temp:
            result = relay.SessionRelay(
                physical, spare, Path(temp), clock.time, clock.monotonic,
                clock.sleep, poll_seconds=1,
            ).run()
        self.assertEqual("complete", result["state"])
        self.assertEqual(3, clock.mono)

    def test_missing_outbox_wait_is_bounded_by_session_deadline(self):
        clock = FakeClock()
        spare = FakeSpare(None)
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(relay.RelayError, "900-second"):
                relay.SessionRelay(
                    object(), spare, Path(temp), clock.time, clock.monotonic,
                    clock.sleep, poll_seconds=60,
                ).run()
        self.assertEqual(900, clock.mono)
        self.assertNotIn("delivery.json", spare.files)

    def test_conflicting_recovery_outbox_fails_closed(self):
        clock = FakeClock()
        outbox = valid_outbox(int(clock.wall))
        physical = FakePhysical(outbox["payload"])
        physical.read_failures = relay.MAX_TRANSPORT_ATTEMPTS
        spare = FakeSpare(outbox)
        with tempfile.TemporaryDirectory() as temp:
            worker = relay.SessionRelay(
                physical, spare, Path(temp), clock.time, clock.monotonic,
                clock.sleep, poll_seconds=0.01,
            )
            with self.assertRaises(relay.RelayError):
                worker.run()
            changed = valid_outbox(int(clock.wall))
            changed["payload"]["file_sha256"] = "c" * 64
            spare.files["outbox.json"] = changed
            with self.assertRaisesRegex(relay.RelayError, "conflicts"):
                worker.run()

    def test_total_deadline_is_bounded_to_900_seconds(self):
        clock = FakeClock()
        outbox = valid_outbox(int(clock.wall))
        outbox["payload"]["expires_at"] = int(clock.wall) + 900
        outbox["payload"]["ttl_seconds"] = 900
        spare = FakeSpare(outbox)
        physical = FakePhysical(outbox["payload"])
        physical.result = None
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(relay.RelayError, "900-second"):
                relay.SessionRelay(
                    physical, spare, Path(temp), clock.time, clock.monotonic,
                    clock.sleep, poll_seconds=60,
                ).run()

    def test_native_storage_conflict_never_reaches_inbox(self):
        clock = FakeClock()
        outbox = valid_outbox(int(clock.wall))
        spare = FakeSpare(outbox)
        physical = FakePhysical(outbox["payload"])
        physical.request = json.loads(json.dumps(outbox["payload"]))
        physical.request["request_id"] = "9" * 32
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(relay.RelayError, "conflicting request"):
                relay.SessionRelay(
                    physical, spare, Path(temp), clock.time, clock.monotonic,
                    clock.sleep,
                ).run()
        self.assertNotIn("inbox.json", spare.files)


class AdapterBoundaryTests(unittest.TestCase):
    def test_native_storage_404_is_pending_but_auth_and_other_errors_fail(self):
        class Opener:
            def __init__(self, status):
                self.status = status

            def open(self, request, timeout):
                raise HTTPError(request.full_url, self.status, "test", {}, None)

        adapter = relay.PhysicalAdapter(
            "http://192.168.1.10", "192.168.1.10", "v0",
        )
        adapter.opener = Opener(404)
        self.assertEqual({}, adapter.read_native_storage())
        for status in (401, 403):
            adapter.opener = Opener(status)
            with self.subTest(status=status), self.assertRaises(relay.RelayError):
                adapter.read_native_storage()
        adapter.opener = Opener(503)
        with self.assertRaises(relay.TransientRelayError):
            adapter.read_native_storage()

    def test_physical_origin_requires_exact_private_ip_and_no_url_credentials(self):
        for url, host in (
            ("http://printer.local", "printer.local"),
            ("http://user:secret@192.168.1.10", "192.168.1.10"),
            ("https://192.168.1.10", "192.168.1.10"),
            ("http://8.8.8.8", "8.8.8.8"),
            ("http://127.0.0.1", "127.0.0.1"),
            ("http://169.254.1.2", "169.254.1.2"),
            ("http://192.168.1.11", "192.168.1.10"),
        ):
            with self.subTest(url=url), self.assertRaises(relay.RelayError):
                relay.PhysicalAdapter(url, host, "v0")

    def test_existing_display_rpc_allowlist_stays_unchanged(self):
        display = relay._load("test_display_source", ROOT / "scripts/helix-display-request.py")
        self.assertEqual(
            {relay.IDENTIFY_METHOD, relay.SEND_METHOD}, display.RPC_METHODS,
        )
        self.assertEqual("helix_orca_display.available.v1", display.EVENT)

    def test_temperature_websocket_has_exact_rpc_and_event_allowlists(self):
        class Base:
            def __init__(self):
                self.sent = []
                self.replies = []

            def send_frame(self, opcode, body):
                self.sent.append((opcode, json.loads(body)))

            def receive_json(self):
                return self.replies.pop(0)

        class Display:
            WebSocket = Base
            MAX_IGNORED_FRAMES = 2

        websocket = relay.relay_websocket_class(Display)()
        websocket.replies.append({"id": 1, "result": "ok"})
        self.assertEqual(
            "ok",
            websocket.rpc(1, relay.SEND_METHOD, {
                "event": relay.REQUEST_EVENT,
                "data": valid_outbox(int(time.time()))["payload"],
            }),
        )
        for method, params in (
            ("printer.print.start", {}),
            (relay.SEND_METHOD, {"event": "helixcal.result", "data": {}}),
        ):
            with self.subTest(method=method), self.assertRaises(relay.RelayError):
                websocket.rpc(2, method, params)

    def test_spare_adapter_uses_only_fixed_marked_directory_and_allowlisted_files(self):
        class Access:
            def __init__(self):
                self.scripts = []

            def request(self, op, script, timeout):
                self.scripts.append(script)
                return {"exit_code": 0, "stdout": '{"exists":false}'}

        access = Access()
        path = (
            "C:\\Users\\Chris\\AppData\\Local\\HelixOrcaCalibration\\"
            "issue-6-nightly-6a7763f\\orca_plugins\\plugin_data\\"
            "helix_calibration\\communication"
        )
        adapter = relay.SpareAdapter(path, access)
        self.assertIsNone(adapter.read_json("outbox.json"))
        script = access.scripts[0]
        self.assertIn(relay.ISOLATION_MARKER, script)
        self.assertIn(relay.ISOLATED_DATA_RELATIVE, script)
        self.assertIn(relay.COMMUNICATION_RELATIVE, script)
        self.assertNotIn(path, script)
        self.assertLessEqual(len(script), 8192)
        with self.assertRaises(relay.RelayError):
            adapter.read_json("normal-profile.json")
        with self.assertRaises(relay.RelayError):
            relay.SpareAdapter("C:\\Users\\Chris\\..\\normal\\communication", access)

    def test_trusted_lan_ack_is_explicit_and_makes_no_encryption_claim(self):
        self.assertEqual(
            "I_ACKNOWLEDGE_EXISTING_TRUSTED_LAN_HTTP", relay.TRUSTED_LAN_ACK,
        )
        self.assertNotIn("secure", relay.TRUSTED_LAN_ACK.casefold())
        self.assertNotIn("encrypted", relay.TRUSTED_LAN_ACK.casefold())


if __name__ == "__main__":
    unittest.main()
