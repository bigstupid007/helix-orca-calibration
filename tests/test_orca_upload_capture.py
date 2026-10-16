import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("upload_capture", ROOT / "scripts" / "orca-upload-capture.py")
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)


def multipart(fields, filename, payload, boundary="issue6-boundary"):
    pieces = []
    for name, value in fields.items():
        pieces.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode())
    pieces.append(
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n"
        "Content-Type: application/octet-stream\r\n\r\n".encode() + payload + b"\r\n"
    )
    pieces.append(f"--{boundary}--\r\n".encode())
    return f"multipart/form-data; boundary={boundary}", b"".join(pieces)


class UploadCaptureTests(unittest.TestCase):
    def test_accepts_only_exact_nonprinting_gcode(self):
        payload = b"G90\nM104 S0\n"
        content_type, body = multipart({"root": "gcodes", "print": "false"}, "issue6.gcode", payload)
        proof = capture.validate_upload(content_type, body, "issue6.gcode", payload)
        self.assertEqual(proof["print"], "false")
        self.assertEqual(proof["file_sha256"], hashlib.sha256(payload).hexdigest())

    def test_rejects_start_queue_extras_and_wrong_bytes(self):
        good = b"G90\n"
        cases = [
            ({"root": "gcodes", "print": "true"}, good),
            ({"root": "gcodes", "print": "false", "queue": "true"}, good),
            ({"root": "config", "print": "false"}, good),
            ({"root": "gcodes", "print": "false"}, b"M112\n"),
        ]
        for fields, payload in cases:
            with self.subTest(fields=fields, payload=payload):
                content_type, body = multipart(fields, "issue6.gcode", payload)
                with self.assertRaises(ValueError):
                    capture.validate_upload(content_type, body, "issue6.gcode", good)

    def test_identity_mismatch_exposes_only_bounded_file_proof(self):
        payload = b"G90\nM104 S0\n"
        content_type, body = multipart({"root": "gcodes", "print": "false"}, "issue6.gcode", payload)
        with self.assertRaises(capture.UploadIdentityMismatch) as raised:
            capture.validate_upload(content_type, body, "issue6.gcode", b"G90\n")
        self.assertEqual(raised.exception.payload, payload)
        self.assertEqual(raised.exception.proof, {
            "root": "gcodes",
            "print": "false",
            "filename": "issue6.gcode",
            "file_bytes": len(payload),
            "file_sha256": hashlib.sha256(payload).hexdigest(),
        })

    def test_only_required_read_routes_are_served(self):
        self.assertEqual(capture.response_for_get("/server/info")["result"]["klippy_state"], "ready")
        self.assertEqual(capture.response_for_get("/server/files/roots")["result"][0]["name"], "gcodes")
        with self.assertRaises(ValueError):
            capture.response_for_get("/printer/objects/query")

    def test_handler_binds_expected_identity_without_listening(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "issue6.gcode"
            path.write_bytes(b"G90\n")
            handler = capture.make_handler(path, Path(directory) / "record.jsonl")
            self.assertEqual(handler.expected, {
                "filename": "issue6.gcode",
                "file_bytes": 4,
                "file_sha256": hashlib.sha256(b"G90\n").hexdigest(),
            })


if __name__ == "__main__":
    unittest.main()
