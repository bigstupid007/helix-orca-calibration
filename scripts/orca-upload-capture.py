#!/usr/bin/env python3
"""Bounded Moonraker-shaped receiver for native Orca upload-only qualification."""

import argparse
import hashlib
import json
from email.parser import BytesParser
from email.policy import default
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import sys
import time
from urllib.parse import urlsplit


MAX_OVERHEAD = 256 * 1024
ALLOWED_GETS = {"/server/info", "/server/files/roots"}
UPLOAD_PATH = "/server/files/upload"
FORBIDDEN_PREFIXES = ("/printer/",)


class UploadIdentityMismatch(ValueError):
    def __init__(self, proof, payload):
        super().__init__("Uploaded file identity mismatch")
        self.proof = proof
        self.payload = payload


def parse_multipart(content_type, body):
    message = BytesParser(policy=default).parsebytes(
        b"Content-Type: " + content_type.encode("ascii") + b"\r\nMIME-Version: 1.0\r\n\r\n" + body
    )
    if not message.is_multipart():
        raise ValueError("Expected multipart upload")
    fields = {}
    files = []
    for part in message.iter_parts():
        name = part.get_param("name", header="content-disposition")
        if not name or name in fields:
            raise ValueError("Missing or duplicate multipart field")
        payload = part.get_payload(decode=True)
        filename = part.get_filename()
        if filename is None:
            fields[name] = payload.decode("utf-8")
        else:
            files.append((name, filename, payload))
    return fields, files


def validate_upload(content_type, body, expected_name, expected_bytes):
    fields, files = parse_multipart(content_type, body)
    if fields != {"root": "gcodes", "print": "false"}:
        raise ValueError("Upload must contain only root=gcodes and print=false")
    if len(files) != 1 or files[0][0] != "file":
        raise ValueError("Upload must contain exactly one file field")
    _, filename, payload = files[0]
    proof = {
        "root": fields["root"],
        "print": fields["print"],
        "filename": filename,
        "file_bytes": len(payload),
        "file_sha256": hashlib.sha256(payload).hexdigest(),
    }
    if filename != expected_name or payload != expected_bytes:
        raise UploadIdentityMismatch(proof, payload)
    return proof


def response_for_get(path):
    if path == "/server/info":
        return {"result": {"klippy_state": "ready", "software_version": "issue6-upload-capture/v1"}}
    if path == "/server/files/roots":
        return {"result": [{"name": "gcodes", "path": "gcodes", "permissions": "rw"}]}
    raise ValueError("GET route not allowed")


def append_record(path, value):
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, sort_keys=True) + "\n")


def make_handler(expected_path, record_path, mismatch_path=None):
    expected_bytes = expected_path.read_bytes()
    expected_name = expected_path.name
    expected_sha256 = hashlib.sha256(expected_bytes).hexdigest()

    class Handler(BaseHTTPRequestHandler):
        server_version = "Issue6UploadCapture/1"
        protocol_version = "HTTP/1.1"

        def log_message(self, _format, *_args):
            return

        def write_json(self, status, value):
            payload = json.dumps(value, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(payload)
            self.close_connection = True

        def record(self, result, **extra):
            append_record(record_path, {
                "time_unix": int(time.time()),
                "client": self.client_address[0],
                "method": self.command,
                "path": urlsplit(self.path).path,
                "result": result,
                **extra,
            })

        def do_GET(self):
            path = urlsplit(self.path).path
            try:
                value = response_for_get(path)
            except ValueError as exc:
                self.record("rejected", reason=str(exc))
                self.write_json(404, {"error": "route not allowed"})
                return
            self.record("served")
            self.write_json(200, value)

        def do_POST(self):
            path = urlsplit(self.path).path
            if path.startswith(FORBIDDEN_PREFIXES) or path != UPLOAD_PATH:
                self.record("rejected", reason="POST route not allowed")
                self.write_json(405, {"error": "POST route not allowed"})
                return
            try:
                length = int(self.headers.get("Content-Length", ""))
                if not 0 < length <= len(expected_bytes) + MAX_OVERHEAD:
                    raise ValueError("Invalid upload length")
                content_type = self.headers.get("Content-Type", "")
                if not content_type.startswith("multipart/form-data;"):
                    raise ValueError("Expected multipart/form-data")
                body = self.rfile.read(length)
                if len(body) != length:
                    raise ValueError("Incomplete upload body")
                proof = validate_upload(content_type, body, expected_name, expected_bytes)
            except UploadIdentityMismatch as exc:
                if mismatch_path is not None:
                    if mismatch_path.exists():
                        self.record("rejected", reason="Mismatch capture already exists", **exc.proof)
                        self.write_json(409, {"error": "Mismatch capture already exists"})
                        return
                    mismatch_path.parent.mkdir(parents=True, exist_ok=True)
                    mismatch_path.write_bytes(exc.payload)
                    mismatch_path.chmod(0o600)
                self.record("rejected", reason=str(exc), **exc.proof)
                self.write_json(400, {"error": str(exc)})
                return
            except (UnicodeError, ValueError) as exc:
                self.record("rejected", reason=str(exc))
                self.write_json(400, {"error": str(exc)})
                return
            self.record("accepted", **proof)
            self.write_json(201, {
                "item": {"path": expected_name, "root": "gcodes", "size": len(expected_bytes)},
                "print_started": False,
                "print_queued": False,
            })

    Handler.expected = {"filename": expected_name, "file_bytes": len(expected_bytes), "file_sha256": expected_sha256}
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bind", required=True)
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("--expected-file", required=True, type=Path)
    parser.add_argument("--record", required=True, type=Path)
    parser.add_argument("--mismatch-file", required=True, type=Path)
    args = parser.parse_args()
    if args.bind != "192.168.1.114" or args.port != 8540:
        raise ValueError("Receiver is restricted to the allocated devbox harness endpoint")
    if not args.expected_file.is_file() or args.expected_file.suffix.lower() != ".gcode":
        raise ValueError("Expected file must be an existing G-code")
    args.record.parent.mkdir(parents=True, exist_ok=True)
    if args.record.exists():
        raise ValueError("Refusing to overwrite an existing capture record")
    if args.mismatch_file.exists():
        raise ValueError("Refusing to overwrite an existing mismatch capture")
    handler = make_handler(args.expected_file, args.record, args.mismatch_file)
    print(json.dumps(handler.expected, sort_keys=True), flush=True)
    HTTPServer((args.bind, args.port), handler).serve_forever()


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
