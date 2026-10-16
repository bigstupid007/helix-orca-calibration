import importlib.util
import json
from pathlib import Path
import base64
import hashlib
import socket
import struct
import tempfile
import threading
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/helix-display-request.py"
spec = importlib.util.spec_from_file_location("display_request", SCRIPT)
request = importlib.util.module_from_spec(spec)
spec.loader.exec_module(request)


def valid_payload():
    return {
        "schema": request.SCHEMA,
        "display_only": True,
        "request_id": "1" * 32,
        "file_sha256": "a" * 64,
        "file": "temperature-230-190-step5-oct15.gcode",
        "file_bytes": 3028194,
        "printer": "Voron 2.4 300 0.4 nozzle",
        "filament": "Generic PLA - Voron Rapido - Initial",
        "process": "Voron 0.20 Standard - Fast Quality",
        "nozzle_mm": 0.4,
        "current_temperature_c": 220,
        "temperatures": [230, 225, 220, 215, 210, 205, 200, 195, 190],
    }


def retained_request(source):
    target = {
        "runtime": dict(request.QUALIFIED_RUNTIME),
        "printer": {"selected_saved": {"name": "Voron 2.4 300 0.4 nozzle"}},
        "filament": {"selected_saved": {"name": "Generic PLA - Voron Rapido - Initial"}},
        "process": {"selected_saved": {"name": "Voron 0.20 Standard - Fast Quality"}},
        "nozzle_mm": 0.4,
        "effective_temperature": 217,
    }
    file_info = {"name": source.name, "size": source.stat().st_size,
                 "sha256": request.sha256(source), "bands": list(request.TEMPERATURES)}
    created = "2026-10-16T02:00:00+00:00"
    context_hash = request.canonical(target)
    identifier = request.canonical({"context": context_hash, "file": file_info, "created_at": created})[:32]
    return {"schema": "helix-orca-temperature-request/v1", "mock_only": True,
            "request_id": identifier, "created_at_utc": created, "context_sha256": context_hash,
            "wizard": "temp_tower", "target": target, "file": file_info,
            "choices": list(request.TEMPERATURES), "bridge_file": "helix-temp-" + identifier + ".gcode"}


class DisplayRequestTests(unittest.TestCase):
    def test_exact_payload_contract_passes(self):
        payload = valid_payload()
        self.assertIs(request.validate(payload), payload)

    def test_wrong_schema_extra_key_and_unsafe_file_fail(self):
        cases = []
        wrong = valid_payload()
        wrong["schema"] = "helixcal.available"
        cases.append(wrong)
        extra = valid_payload()
        extra["start"] = True
        cases.append(extra)
        unsafe = valid_payload()
        unsafe["file"] = "../tower.gcode"
        cases.append(unsafe)
        for payload in cases:
            with self.subTest(payload=payload):
                with self.assertRaises(request.DisplayRequestError):
                    request.validate(payload)

    def test_numeric_and_context_bounds_fail_closed(self):
        for key, value in (
            ("file_bytes", 0),
            ("file_bytes", request.MAX_FILE_BYTES + 1),
            ("nozzle_mm", float("nan")),
            ("nozzle_mm", 2.1),
            ("current_temperature_c", 501),
            ("printer", "x" * 129),
        ):
            payload = valid_payload()
            payload[key] = value
            with self.subTest(key=key, value=value):
                with self.assertRaises(request.DisplayRequestError):
                    request.validate(payload)

    def test_python_and_lua_share_filename_case_and_utf8_byte_bounds(self):
        # Lua's # operator measures bytes. Keep the producer's contract byte-for-byte
        # equivalent so every client-valid payload can produce a receipt.
        cases = (
            ("file", "tower.GCODE"),
            ("file", ("é" * 125) + ".gcode"),
            ("printer", "é" * 65),
            ("filament", "\x7fPLA"),
            ("process", "\nFast Quality"),
        )
        for key, value in cases:
            payload = valid_payload()
            payload[key] = value
            with self.subTest(key=key, value=value):
                with self.assertRaises(request.DisplayRequestError):
                    request.validate(payload)

        lua = (ROOT / "integration/helix-orca-display/main.lua").read_text(encoding="utf-8")
        self.assertIn('#value <= MAX_CONTEXT_TEXT', lua)
        self.assertIn('#value <= 255', lua)
        self.assertIn('value:match("%.gcode$") ~= nil', lua)
        self.assertNotIn(':lower()', lua)

    def test_prepare_binds_exact_file_bytes_and_digest(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "qualified.gcode"
            source.write_text("".join(f"M104 S{value}\n" for value in request.TEMPERATURES))
            context_path = Path(temporary) / "retained-request.json"
            context_path.write_text(json.dumps(retained_request(source)))
            args = type("Args", (), {
                "gcode": source,
                "context_request": context_path,
                "output": Path(temporary) / "request.json",
            })()
            payload = request.prepare(args)
            self.assertEqual(payload["file_bytes"], source.stat().st_size)
            self.assertEqual(payload["file_sha256"], request.sha256(source))
            self.assertEqual(payload["current_temperature_c"], 217)
            self.assertEqual(json.loads(args.output.read_text()), payload)

    def test_prepare_rejects_file_without_all_retained_bands(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "qualified.gcode"
            source.write_text("M104 S230\nM104 S225\n")
            context = retained_request(source)
            context["file"]["bands"] = list(request.TEMPERATURES)
            context["request_id"] = request.canonical({
                "context": context["context_sha256"], "file": context["file"],
                "created_at": context["created_at_utc"],
            })[:32]
            path = Path(temporary) / "retained.json"
            path.write_text(json.dumps(context))
            args = type("Args", (), {"gcode": source, "context_request": path, "output": None})()
            with self.assertRaises(request.DisplayRequestError):
                request.prepare(args)

    def test_transport_surface_is_two_allowlisted_rpcs(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertEqual(request.IDENTIFY_METHOD, "server.connection.identify")
        self.assertEqual(request.SEND_METHOD, "connection.send_event")
        self.assertEqual(request.EVENT, "helix_orca_display.available.v1")
        self.assertNotIn("helixcal.available", source)
        self.assertNotIn("printer.print", source)
        self.assertNotIn("gcode.script", source)
        self.assertIn('args.confirm_display_only != EVENT', source)
        self.assertIn('state not in IDLE_STATES', source)
        self.assertIn('method not in RPC_METHODS', source)
        self.assertIn('verify_remote_file(', source)
        self.assertIn('signal.setitimer(signal.ITIMER_REAL, SEND_LIFETIME_SECONDS)', source)
        self.assertNotIn('MOONRAKER_API_KEY', source)

    def test_handshake_and_rpc_reads_share_one_deadline(self):
        source = SCRIPT.read_text(encoding="utf-8")
        handshake = source[source.index("    def _read_until"):source.index("    def _read_exact")]
        exact = source[source.index("    def _read_exact"):source.index("    def send_frame")]
        for body in (handshake, exact):
            self.assertIn("self.deadline - time.monotonic()", body)
            self.assertIn("self.sock.settimeout(min(5, remaining))", body)

    def test_socketpair_proves_masked_two_rpc_exchange_and_close(self):
        client, server = socket.socketpair()
        seen = []

        def read_exact(count):
            value = b""
            while len(value) < count:
                value += server.recv(count - len(value))
            return value

        def read_client_frame():
            head = read_exact(2)
            self.assertTrue(head[1] & 0x80)
            length = head[1] & 0x7F
            if length == 126:
                length = struct.unpack("!H", read_exact(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", read_exact(8))[0]
            mask_key = read_exact(4)
            body = read_exact(length)
            return head[0] & 0x0F, bytes(value ^ mask_key[i % 4] for i, value in enumerate(body))

        def send_json(value):
            body = json.dumps(value).encode()
            server.sendall(bytes([0x81, len(body)]) + body)

        def peer():
            handshake = b""
            while b"\r\n\r\n" not in handshake:
                handshake += server.recv(4096)
            key = next(line.split(b":", 1)[1].strip() for line in handshake.split(b"\r\n")
                       if line.lower().startswith(b"sec-websocket-key:"))
            accept = base64.b64encode(hashlib.sha1(key + b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11").digest())
            server.sendall(b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: " + accept + b"\r\n\r\n")
            for expected_id in (1, 2):
                opcode, body = read_client_frame()
                self.assertEqual(opcode, 1)
                message = json.loads(body)
                seen.append(message)
                send_json({"jsonrpc": "2.0", "method": "notify_agent_event", "params": []})
                send_json({"jsonrpc": "2.0", "id": expected_id,
                           "result": {"connection_id": 7} if expected_id == 1 else "ok"})
            opcode, _ = read_client_frame()
            self.assertEqual(opcode, 8)
            server.close()

        thread = threading.Thread(target=peer)
        thread.start()
        with mock.patch.object(socket, "create_connection", return_value=client):
            ws = request.WebSocket("example.invalid", 80, "/websocket")
            self.assertEqual(ws.rpc(1, request.IDENTIFY_METHOD, {
                "client_name": request.CLIENT_NAME, "version": request.CLIENT_VERSION,
                "type": "agent", "url": request.CLIENT_URL,
            }), {"connection_id": 7})
            self.assertEqual(ws.rpc(2, request.SEND_METHOD, {
                "event": request.EVENT, "data": valid_payload(),
            }), "ok")
            ws.close()
        thread.join(timeout=2)
        self.assertFalse(thread.is_alive())
        self.assertEqual([item["method"] for item in seen], [request.IDENTIFY_METHOD, request.SEND_METHOD])


if __name__ == "__main__":
    unittest.main()
