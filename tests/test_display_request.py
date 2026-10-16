import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


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

    def test_prepare_binds_exact_file_bytes_and_digest(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "qualified.gcode"
            source.write_bytes(b"M104 S230\nM104 S225\n")
            args = type("Args", (), {
                "gcode": source,
                "printer": "Voron 2.4 300 0.4 nozzle",
                "filament": "Generic PLA - Voron Rapido - Initial",
                "process": "Voron 0.20 Standard - Fast Quality",
                "nozzle": 0.4,
                "current_temperature": 217,
                "output": Path(temporary) / "request.json",
            })()
            payload = request.prepare(args)
            self.assertEqual(payload["file_bytes"], source.stat().st_size)
            self.assertEqual(payload["file_sha256"], request.sha256(source))
            self.assertEqual(payload["current_temperature_c"], 217)
            self.assertEqual(json.loads(args.output.read_text()), payload)

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


if __name__ == "__main__":
    unittest.main()
