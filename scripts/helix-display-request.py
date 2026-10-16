#!/usr/bin/env python3
"""Prepare and send one strictly display-only Helix receipt through Moonraker."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import os
from pathlib import Path
import secrets
import socket
import struct
import sys
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen


EVENT = "helix_orca_display.available.v1"
SCHEMA = "helix-orca-display/v1"
TEMPERATURES = [230, 225, 220, 215, 210, 205, 200, 195, 190]
MAX_FILE_BYTES = 64 * 1024 * 1024
IDENTIFY_METHOD = "server.connection.identify"
SEND_METHOD = "connection.send_event"
CLIENT_NAME = "helix-orca-display"
CLIENT_VERSION = "0.1.0"
CLIENT_URL = "https://github.com/bigstupid007/helix-orca-calibration/issues/6"
IDLE_STATES = {"standby", "complete", "cancelled"}


class DisplayRequestError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def valid_filename(value: Any) -> bool:
    return (
        isinstance(value, str)
        and 6 < len(value) <= 255
        and value.lower().endswith(".gcode")
        and "/" not in value
        and "\\" not in value
        and ".." not in value
        and not any(ord(char) < 32 or ord(char) == 127 for char in value)
    )


def validate(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise DisplayRequestError("display payload must be an object")
    required = {
        "schema", "display_only", "request_id", "file_sha256", "file", "file_bytes",
        "printer", "filament", "process", "nozzle_mm", "current_temperature_c", "temperatures",
    }
    if set(payload) != required:
        raise DisplayRequestError("display payload keys do not match the exact v1 contract")
    if payload["schema"] != SCHEMA or payload["display_only"] is not True:
        raise DisplayRequestError("display-only schema marker mismatch")
    for key, length in (("request_id", 32), ("file_sha256", 64)):
        value = payload[key]
        if not isinstance(value, str) or len(value) != length or any(c not in "0123456789abcdef" for c in value):
            raise DisplayRequestError(f"{key} must be exact lowercase hexadecimal")
    if not valid_filename(payload["file"]):
        raise DisplayRequestError("file must be a safe .gcode basename")
    size = payload["file_bytes"]
    if isinstance(size, bool) or not isinstance(size, int) or not 1 <= size <= MAX_FILE_BYTES:
        raise DisplayRequestError("file_bytes is outside the display-only bound")
    for key in ("printer", "filament", "process"):
        value = payload[key]
        if not isinstance(value, str) or not value.strip() or len(value) > 128:
            raise DisplayRequestError(f"{key} must be 1-128 nonblank characters")
        if any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise DisplayRequestError(f"{key} contains a control character")
    for key, low, high in (("nozzle_mm", 0.05, 2), ("current_temperature_c", 0, 500)):
        value = payload[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
            raise DisplayRequestError(f"{key} is outside the display-only bound")
    if payload["temperatures"] != TEMPERATURES:
        raise DisplayRequestError("temperatures do not match the qualified tower")
    return payload


def prepare(args: argparse.Namespace) -> dict[str, Any]:
    source = args.gcode.resolve(strict=True)
    if not valid_filename(source.name):
        raise DisplayRequestError("source must have a safe .gcode basename")
    size = source.stat().st_size
    payload = validate({
        "schema": SCHEMA,
        "display_only": True,
        "request_id": secrets.token_hex(16),
        "file_sha256": sha256(source),
        "file": source.name,
        "file_bytes": size,
        "printer": args.printer,
        "filament": args.filament,
        "process": args.process,
        "nozzle_mm": args.nozzle,
        "current_temperature_c": args.current_temperature,
        "temperatures": TEMPERATURES,
    })
    encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        temporary.write_text(encoded, encoding="utf-8")
        temporary.replace(args.output)
    return payload


def api_get(base_url: str, path: str, api_key: str | None) -> Any:
    headers = {"Accept": "application/json"}
    if api_key:
        headers["X-Api-Key"] = api_key
    with urlopen(Request(base_url.rstrip("/") + path, headers=headers), timeout=5) as response:
        return json.loads(response.read())


def preflight(base_url: str, api_key: str | None, expected_version: str) -> dict[str, str]:
    info = api_get(base_url, "/server/info", api_key).get("result", {})
    version = info.get("moonraker_version")
    if version != expected_version or info.get("klippy_state") != "ready":
        raise DisplayRequestError("Moonraker identity/readiness preflight failed")
    query = api_get(base_url, "/printer/objects/query?print_stats", api_key).get("result", {})
    state = query.get("status", {}).get("print_stats", {}).get("state")
    if state not in IDLE_STATES:
        raise DisplayRequestError(f"printer is not in an allowed non-active state: {state!r}")
    return {"klippy_state": "ready", "moonraker_version": version, "print_state": state}


class WebSocket:
    def __init__(self, host: str, port: int, path: str):
        self.sock = socket.create_connection((host, port), timeout=5)
        self.buffer = bytearray()
        key = base64.b64encode(secrets.token_bytes(16)).decode("ascii")
        request = (
            f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\nUpgrade: websocket\r\n"
            f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(request.encode("ascii"))
        response = self._read_until(b"\r\n\r\n", 16384)
        status, *headers = response.decode("latin1").split("\r\n")
        values = {k.strip().lower(): v.strip() for k, v in (line.split(":", 1) for line in headers if ":" in line)}
        accept = base64.b64encode(hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")).digest()).decode("ascii")
        if " 101 " not in f" {status} " or values.get("sec-websocket-accept") != accept:
            self.close()
            raise DisplayRequestError("Moonraker WebSocket handshake failed")

    def _read_until(self, marker: bytes, limit: int) -> bytes:
        value = self.buffer
        while marker not in value:
            chunk = self.sock.recv(4096)
            if not chunk or len(value) + len(chunk) > limit:
                raise DisplayRequestError("bounded WebSocket read failed")
            value.extend(chunk)
        end = value.index(marker) + len(marker)
        result = bytes(value[:end])
        self.buffer = value[end:]
        return result

    def _read_exact(self, size: int) -> bytes:
        value = self.buffer
        self.buffer = bytearray()
        while len(value) < size:
            chunk = self.sock.recv(size - len(value))
            if not chunk:
                raise DisplayRequestError("WebSocket closed before reply")
            value.extend(chunk)
        result = bytes(value[:size])
        self.buffer.extend(value[size:])
        return result

    def send_frame(self, opcode: int, payload: bytes) -> None:
        if len(payload) > 1024 * 1024:
            raise DisplayRequestError("WebSocket payload exceeds client bound")
        mask = secrets.token_bytes(4)
        length = len(payload)
        prefix = bytes([0x80 | opcode])
        if length < 126:
            prefix += bytes([0x80 | length])
        elif length <= 65535:
            prefix += bytes([0x80 | 126]) + struct.pack("!H", length)
        else:
            prefix += bytes([0x80 | 127]) + struct.pack("!Q", length)
        masked = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
        self.sock.sendall(prefix + mask + masked)

    def receive_json(self) -> Any:
        while True:
            head = self._read_exact(2)
            opcode, length = head[0] & 0x0F, head[1] & 0x7F
            if head[1] & 0x80:
                raise DisplayRequestError("server sent an invalid masked frame")
            if length == 126:
                length = struct.unpack("!H", self._read_exact(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self._read_exact(8))[0]
            if length > 1024 * 1024:
                raise DisplayRequestError("WebSocket reply exceeds client bound")
            payload = self._read_exact(length)
            if opcode == 0x9:
                self.send_frame(0xA, payload)
                continue
            if opcode == 0x8:
                raise DisplayRequestError("Moonraker closed before RPC reply")
            if opcode != 0x1:
                raise DisplayRequestError("unexpected WebSocket frame type")
            return json.loads(payload)

    def rpc(self, request_id: int, method: str, params: dict[str, Any]) -> Any:
        body = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": request_id}, separators=(",", ":")).encode()
        self.send_frame(0x1, body)
        while True:
            reply = self.receive_json()
            if reply.get("id") != request_id:
                continue
            if "error" in reply:
                raise DisplayRequestError(f"Moonraker rejected {method}: {reply['error']}")
            return reply.get("result")

    def close(self) -> None:
        if getattr(self, "sock", None):
            try:
                self.send_frame(0x8, struct.pack("!H", 1000))
            except OSError:
                pass
            self.sock.close()
            self.sock = None


def send(args: argparse.Namespace) -> dict[str, Any]:
    payload = validate(json.loads(args.payload.read_text(encoding="utf-8")))
    parsed = urlparse(args.moonraker)
    if parsed.scheme != "http" or not parsed.hostname or parsed.path not in ("", "/"):
        raise DisplayRequestError("Moonraker URL must be an explicit http origin")
    if parsed.hostname != args.expected_host or args.confirm_display_only != EVENT:
        raise DisplayRequestError("exact host/event confirmation failed")
    api_key = os.environ.get(args.api_key_env) if args.api_key_env else None
    check = preflight(args.moonraker, api_key, args.expected_moonraker_version)
    connection = WebSocket(parsed.hostname, parsed.port or 80, "/websocket")
    try:
        identified = connection.rpc(1, IDENTIFY_METHOD, {
            "client_name": CLIENT_NAME,
            "version": CLIENT_VERSION,
            "type": "agent",
            "url": CLIENT_URL,
            **({"api_key": api_key} if api_key else {}),
        })
        result = connection.rpc(2, SEND_METHOD, {"event": EVENT, "data": payload})
        if result != "ok":
            raise DisplayRequestError("Moonraker did not acknowledge the display event")
    finally:
        connection.close()
    return {"event": EVENT, "identify": identified, "preflight": check, "request_id": payload["request_id"], "result": "ok"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("prepare")
    build.add_argument("gcode", type=Path)
    build.add_argument("--printer", required=True)
    build.add_argument("--filament", required=True)
    build.add_argument("--process", required=True)
    build.add_argument("--nozzle", type=float, required=True)
    build.add_argument("--current-temperature", type=float, required=True)
    build.add_argument("--output", type=Path)
    emit = sub.add_parser("send")
    emit.add_argument("payload", type=Path)
    emit.add_argument("--moonraker", required=True)
    emit.add_argument("--expected-host", required=True)
    emit.add_argument("--expected-moonraker-version", required=True)
    emit.add_argument("--confirm-display-only", required=True)
    emit.add_argument("--api-key-env", default="MOONRAKER_API_KEY")
    args = parser.parse_args()
    value = prepare(args) if args.command == "prepare" else send(args)
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (DisplayRequestError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
