#!/usr/bin/env python3
"""Relay one bounded, non-printing Temperature selection between Orca and Helix."""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import signal
import sys
import time
from typing import Any
from urllib.error import HTTPError
from urllib.parse import quote, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


ROOT = Path(__file__).resolve().parent
DISPLAY_PATH = ROOT / "helix-display-request.py"
SPARE_PATH = ROOT / "spare-access.py"

REQUEST_EVENT = "helix_orca_temperature.request.v1"
ACK_EVENT = "helix_orca_temperature.ack.v1"
SESSION_SCHEMA = "helix-orca-temperature-session/v1"
SELECTION_SCHEMA = "helix-orca-temperature-selection/v1"
ACK_SCHEMA = "helix-orca-temperature-ack/v1"
OUTBOX_SCHEMA = "helix-orca-temperature-outbox/v1"
DELIVERY_SCHEMA = "helix-orca-temperature-delivery/v1"
CHOICES = [230, 225, 220, 215, 210, 205, 200, 195, 190]
SETTING = "nozzle_temperature"

IDENTIFY_METHOD = "server.connection.identify"
SEND_METHOD = "connection.send_event"
RPC_METHODS = frozenset((IDENTIFY_METHOD, SEND_METHOD))
EVENTS = frozenset((REQUEST_EVENT, ACK_EVENT))
IDLE_STATES = frozenset(("standby", "complete", "cancelled"))
PRIVATE_LAN_NETWORKS = tuple(
    ipaddress.ip_network(value) for value in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
)
TRUSTED_LAN_ACK = "I_ACKNOWLEDGE_EXISTING_TRUSTED_LAN_HTTP"
STORAGE_PATH = "/server/files/config/helixscreen/plugin-data/orcacal.json"
COMMUNICATION_RELATIVE = (
    "orca_plugins\\plugin_data\\helix_calibration\\communication"
)
ISOLATED_DATA_RELATIVE = "HelixOrcaCalibration\\issue-6-nightly-6a7763f"
ISOLATION_MARKER = ".helix-orca-issue-6-oct15-qualification"

MAX_REQUEST_BYTES = 64 * 1024
MAX_STORAGE_BYTES = 256 * 1024
MAX_FILE_BYTES = 20_000_000
MAX_SESSION_SECONDS = 900
MAX_CALL_SECONDS = 60
MAX_TRANSPORT_ATTEMPTS = 5
MAX_TEXT_BYTES = 128
POLL_SECONDS = 1.0
MIN_LEASE_REMAINING_SECONDS = 2.0
REQUEST_RECEIPT_GRACE_SECONDS = 1.75
DELIVERY_PHASES = frozenset((
    "delivering", "waiting_selection", "waiting_companion", "delivered",
    "retrying", "failed",
))


class RelayError(RuntimeError):
    pass


class TransientRelayError(RelayError):
    """A bounded transport failure that may be retried with identical data."""


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RelayError(f"cannot load required source: {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise RelayError("value is not bounded canonical JSON") from exc


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _exact_hex(value: Any, size: int, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != size
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise RelayError(f"{name} must be exact lowercase hexadecimal")
    return value


def _bounded_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RelayError(f"{name} must be nonblank text")
    try:
        size = len(value.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise RelayError(f"{name} must be valid UTF-8") from exc
    if size > MAX_TEXT_BYTES or any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise RelayError(f"{name} exceeds its UTF-8/control-character bound")
    return value


def _finite(value: Any, low: float, high: float, name: str) -> int | float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not low <= value <= high
    ):
        raise RelayError(f"{name} is outside its finite bound")
    return value


def valid_filename(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        size = len(value.encode("utf-8"))
    except UnicodeEncodeError:
        return False
    return (
        6 < size <= 255
        and value.endswith(".gcode")
        and "/" not in value
        and "\\" not in value
        and ".." not in value
        and not any(ord(char) < 32 or ord(char) == 127 for char in value)
    )


def validate_forward_payload(value: Any, now: int | None = None) -> dict[str, Any]:
    required = {
        "schema", "simulation_only", "not_applied", "request_id", "origin_id",
        "context_sha256", "file_sha256", "file", "file_bytes", "printer",
        "filament", "process", "nozzle_mm", "saved_current", "edited_current",
        "current", "setting", "choices", "expires_at", "ttl_seconds",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise RelayError("request keys do not match the exact v1 contract")
    if (
        value["schema"] != SESSION_SCHEMA
        or value["simulation_only"] is not True
        or value["not_applied"] is not True
    ):
        raise RelayError("request simulation/not-applied markers are invalid")
    _exact_hex(value["request_id"], 32, "request_id")
    _exact_hex(value["origin_id"], 32, "origin_id")
    _exact_hex(value["context_sha256"], 64, "context_sha256")
    _exact_hex(value["file_sha256"], 64, "file_sha256")
    if not valid_filename(value["file"]):
        raise RelayError("file must be a safe case-sensitive .gcode basename")
    if (
        isinstance(value["file_bytes"], bool)
        or not isinstance(value["file_bytes"], int)
        or not 1 <= value["file_bytes"] <= MAX_FILE_BYTES
    ):
        raise RelayError("file_bytes is outside 1..20 MiB")
    for name in ("printer", "filament", "process"):
        _bounded_text(value[name], name)
    _finite(value["nozzle_mm"], 0.05, 2, "nozzle_mm")
    for name in ("saved_current", "edited_current", "current"):
        _finite(value[name], 0, 500, name)
    if value["setting"] != SETTING or value["choices"] != CHOICES:
        raise RelayError("setting or prepared choices differ from the Temperature contract")
    if (
        isinstance(value["ttl_seconds"], bool)
        or not isinstance(value["ttl_seconds"], int)
        or not 1 <= value["ttl_seconds"] <= MAX_SESSION_SECONDS
    ):
        raise RelayError("ttl_seconds is outside 1..900")
    current_time = int(time.time()) if now is None else now
    if (
        isinstance(value["expires_at"], bool)
        or not isinstance(value["expires_at"], int)
        or value["expires_at"] > 4_102_444_800
        or value["expires_at"] <= current_time
        or value["expires_at"] - current_time > value["ttl_seconds"]
    ):
        raise RelayError("request is expired or its expiry exceeds ttl_seconds")
    return value


def validate_outbox(value: Any, now: int | None = None) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"schema", "target", "payload"}:
        raise RelayError("outbox keys do not match the exact v1 wrapper")
    if value["schema"] != OUTBOX_SCHEMA or not isinstance(value["target"], dict):
        raise RelayError("outbox schema or retained target is invalid")
    payload = validate_forward_payload(value["payload"], now)
    target = value["target"]
    if canonical_sha256(target) != payload["context_sha256"]:
        raise RelayError("retained target differs from context_sha256")
    if target.get("runtime") != {"version": "2.5.0-dev", "build": "6a7763f0"}:
        raise RelayError("retained target is not the qualified October 15 runtime")
    try:
        flattened = {
            "printer": target["printer"]["selected_saved"]["name"],
            "filament": target["filament"]["selected_saved"]["name"],
            "process": target["process"]["selected_saved"]["name"],
            "nozzle_mm": target["nozzle_mm"],
            "saved_current": target["saved_temperature"],
            "edited_current": target["edited_temperature"],
            "current": target["effective_temperature"],
        }
    except (KeyError, TypeError) as exc:
        raise RelayError("retained target is missing required original context") from exc
    for name, retained in flattened.items():
        if type(payload[name]) is not type(retained) or payload[name] != retained:
            raise RelayError(f"request {name} differs from the retained target")
    if len(canonical_bytes(value)) > MAX_REQUEST_BYTES:
        raise RelayError("outbox exceeds 64 KiB")
    return value


def _result_keys() -> set[str]:
    return {
        "schema", "simulation_only", "not_applied", "request_id", "origin_id",
        "context_sha256", "file_sha256", "file", "file_bytes", "setting", "value",
    }


def validate_selection_result(
    request: dict[str, Any], value: Any, now: int | None = None,
) -> dict[str, Any]:
    validate_forward_payload(request, now)
    if not isinstance(value, dict) or set(value) != _result_keys():
        raise RelayError("selection keys do not match the exact v1 contract")
    if (
        value["schema"] != SELECTION_SCHEMA
        or value["simulation_only"] is not True
        or value["not_applied"] is not True
    ):
        raise RelayError("selection simulation/not-applied markers are invalid")
    for name in (
        "request_id", "origin_id", "context_sha256", "file_sha256", "file",
        "file_bytes", "setting",
    ):
        if type(value[name]) is not type(request[name]) or value[name] != request[name]:
            raise RelayError(f"selection {name} does not match the current request")
    if isinstance(value["value"], bool) or type(value["value"]) is not int:
        raise RelayError("selection value must be a prepared integer")
    if value["value"] not in request["choices"]:
        raise RelayError("selection value is outside the prepared choices")
    return value


def make_ack(result: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(result, dict) or set(result) != _result_keys():
        raise RelayError("cannot acknowledge a non-v1 selection")
    return {**result, "schema": ACK_SCHEMA}


def validate_ack(
    request: dict[str, Any], value: Any, now: int | None = None,
) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != _result_keys() or value.get("schema") != ACK_SCHEMA:
        raise RelayError("receipt keys do not match the exact v1 ACK contract")
    result = {**value, "schema": SELECTION_SCHEMA}
    validate_selection_result(request, result, now)
    return value


def make_delivery(request: dict[str, Any], phase: str) -> dict[str, Any]:
    validate_forward_payload(request, request["expires_at"] - request["ttl_seconds"])
    if phase not in DELIVERY_PHASES:
        raise RelayError("delivery phase is outside the exact v1 contract")
    return {
        "schema": DELIVERY_SCHEMA,
        "request_id": request["request_id"],
        "origin_id": request["origin_id"],
        "context_sha256": request["context_sha256"],
        "phase": phase,
    }


def validate_delivery(request: dict[str, Any], value: Any) -> dict[str, Any]:
    expected_keys = {"schema", "request_id", "origin_id", "context_sha256", "phase"}
    if not isinstance(value, dict) or set(value) != expected_keys:
        raise RelayError("delivery keys do not match the exact v1 contract")
    expected = make_delivery(request, value.get("phase"))
    if value != expected:
        raise RelayError("delivery identity differs from the current request")
    return value


def validate_lease(request: dict[str, Any], value: Any) -> dict[str, int | float]:
    if not isinstance(value, dict) or set(value) != {"issued_eventtime", "expires_eventtime"}:
        raise RelayError("lease keys do not match the exact v1 contract")
    issued = value["issued_eventtime"]
    expires = value["expires_eventtime"]
    for name, number in (("issued_eventtime", issued), ("expires_eventtime", expires)):
        if isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(number) or number < 0:
            raise RelayError(f"{name} is outside the finite lease bound")
    duration = expires - issued
    if not MIN_LEASE_REMAINING_SECONDS < duration <= request["ttl_seconds"]:
        raise RelayError("lease duration is outside the current request bound")
    return value


def make_wire_envelope(
    request: dict[str, Any], eventtime: Any, walltime_after_response: Any,
    previous_lease: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validate_forward_payload(request, int(walltime_after_response))
    if (
        isinstance(eventtime, bool) or not isinstance(eventtime, (int, float))
        or not math.isfinite(eventtime) or eventtime < 0
        or isinstance(walltime_after_response, bool)
        or not isinstance(walltime_after_response, (int, float))
        or not math.isfinite(walltime_after_response)
    ):
        raise RelayError("Moonraker eventtime or relay wall time is invalid")
    remaining = max(0.0, request["expires_at"] - walltime_after_response)
    expires_eventtime = eventtime + remaining
    if previous_lease is not None:
        validate_lease(request, previous_lease)
        expires_eventtime = min(expires_eventtime, previous_lease["expires_eventtime"])
    lease = {
        "issued_eventtime": eventtime,
        "expires_eventtime": expires_eventtime,
    }
    validate_lease(request, lease)
    return {"session": request, "lease": lease}


def validate_wire_envelope(value: Any, now: int | None = None) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"session", "lease"}:
        raise RelayError("wire request keys do not match the exact lease envelope")
    session = value["session"]
    validate_forward_payload(session, now)
    validate_lease(session, value["lease"])
    return value


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        return None


def relay_websocket_class(display: Any) -> type:
    class TemperatureWebSocket(display.WebSocket):
        def rpc(self, request_id: int, method: str, params: dict[str, Any]) -> Any:
            if method not in RPC_METHODS:
                raise RelayError("RPC method is outside the Temperature relay allowlist")
            if method == IDENTIFY_METHOD:
                required = {"client_name", "version", "type", "url"}
                if set(params) not in (required, required | {"api_key"}) or params.get("type") != "agent":
                    raise RelayError("identify request is outside the Temperature relay contract")
            else:
                if not isinstance(params, dict) or set(params) != {"event", "data"}:
                    raise RelayError("send-event parameters are outside the Temperature relay contract")
                event = params.get("event")
                if event == REQUEST_EVENT:
                    validate_wire_envelope(params.get("data"))
                elif event == ACK_EVENT:
                    data = params.get("data")
                    if not isinstance(data, dict) or set(data) != _result_keys() or data.get("schema") != ACK_SCHEMA:
                        raise RelayError("ACK event is outside the Temperature relay contract")
                else:
                    raise RelayError("event is outside the Temperature relay namespace")
            body = json.dumps(
                {"jsonrpc": "2.0", "method": method, "params": params, "id": request_id},
                separators=(",", ":"), allow_nan=False,
            ).encode("utf-8")
            self.send_frame(0x1, body)
            for _ in range(display.MAX_IGNORED_FRAMES + 1):
                reply = self.receive_json()
                if not isinstance(reply, dict) or reply.get("id") != request_id:
                    continue
                if "error" in reply:
                    raise RelayError(f"Moonraker rejected {method}")
                return reply.get("result")
            raise RelayError("Moonraker exceeded the ignored-frame bound")

    return TemperatureWebSocket


class PhysicalAdapter:
    def __init__(
        self, base_url: str, expected_host: str, expected_version: str,
        api_key: str | None = None,
    ):
        parsed = urlparse(base_url)
        try:
            address = ipaddress.ip_address(expected_host)
        except ValueError as exc:
            raise RelayError("expected host must be an exact private IP literal") from exc
        if (
            parsed.scheme != "http" or parsed.username or parsed.password
            or parsed.path not in ("", "/") or parsed.query or parsed.fragment
            or parsed.hostname != expected_host
            or not isinstance(address, ipaddress.IPv4Address)
            or not any(address in network for network in PRIVATE_LAN_NETWORKS)
        ):
            raise RelayError("Moonraker must be the exact credential-free private-LAN HTTP origin")
        self.base_url = base_url.rstrip("/")
        self.expected_host = expected_host
        self.expected_version = expected_version
        self.api_key = api_key
        self.display = _load("temperature_relay_display_source", DISPLAY_PATH)
        self.ws_type = relay_websocket_class(self.display)
        self.opener = build_opener(_NoRedirect())

    def _headers(self, accept: str) -> dict[str, str]:
        headers = {"Accept": accept}
        if self.api_key:
            headers["X-Api-Key"] = self.api_key
        return headers

    def _json_get(
        self, path: str, limit: int = MAX_STORAGE_BYTES, allow_not_found: bool = False,
    ) -> Any:
        request = Request(self.base_url + path, headers=self._headers("application/json"))
        try:
            with self.opener.open(request, timeout=5) as response:
                data = response.read(limit + 1)
        except HTTPError as exc:
            if allow_not_found and exc.code == 404:
                return None
            if 500 <= exc.code <= 599:
                raise TransientRelayError("bounded HTTP GET encountered a transient server failure") from exc
            raise RelayError(f"bounded HTTP GET failed with status {exc.code}") from exc
        if len(data) > limit:
            raise RelayError("bounded HTTP response exceeds its limit")
        try:
            return json.loads(data)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise RelayError("bounded HTTP response is not JSON") from exc

    def assert_ready(self) -> dict[str, Any]:
        info = self._json_get("/server/info").get("result", {})
        if info.get("moonraker_version") != self.expected_version or info.get("klippy_state") != "ready":
            raise RelayError("Moonraker identity/readiness preflight failed")
        query = self._json_get("/printer/objects/query?print_stats").get("result", {})
        state = query.get("status", {}).get("print_stats", {}).get("state")
        eventtime = query.get("eventtime")
        if state not in IDLE_STATES:
            raise RelayError("printer is not in an allowed non-active state")
        if (
            isinstance(eventtime, bool) or not isinstance(eventtime, (int, float))
            or not math.isfinite(eventtime) or eventtime < 0
        ):
            raise RelayError("Moonraker readiness response omitted finite eventtime")
        return {
            "moonraker_version": self.expected_version,
            "klippy_state": "ready",
            "print_state": state,
            "eventtime": eventtime,
        }

    def verify_file(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = Request(
            self.base_url + "/server/files/gcodes/" + quote(payload["file"], safe=""),
            headers=self._headers("application/octet-stream"),
        )
        digest = hashlib.sha256()
        size = 0
        try:
            with self.opener.open(request, timeout=5) as response:
                while True:
                    chunk = response.read(min(1024 * 1024, payload["file_bytes"] - size + 1))
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > payload["file_bytes"] or size > MAX_FILE_BYTES:
                        raise RelayError("target G-code exceeds the retained size")
                    digest.update(chunk)
        except HTTPError as exc:
            if 500 <= exc.code <= 599:
                raise TransientRelayError("G-code readback encountered a transient server failure") from exc
            raise RelayError(f"bounded G-code readback failed with status {exc.code}") from exc
        if size != payload["file_bytes"] or digest.hexdigest() != payload["file_sha256"]:
            raise RelayError("target G-code bytes differ from the retained request")
        return {"bytes": size, "sha256": digest.hexdigest()}

    def read_native_storage(self) -> Any:
        value = self._json_get(STORAGE_PATH, MAX_STORAGE_BYTES, allow_not_found=True)
        return {} if value is None else value

    def send_event(self, event: str, data: dict[str, Any]) -> None:
        if event not in EVENTS:
            raise RelayError("event is outside the Temperature relay namespace")
        parsed = urlparse(self.base_url)
        try:
            connection = self.ws_type(parsed.hostname, parsed.port or 80, "/websocket")
            identify = {
                "client_name": "helix-orca-temperature-relay",
                "version": "0.1.0",
                "type": "agent",
                "url": "https://github.com/bigstupid007/helix-orca-calibration/issues/8",
            }
            if self.api_key:
                identify["api_key"] = self.api_key
            connection.rpc(1, IDENTIFY_METHOD, identify)
            if connection.rpc(2, SEND_METHOD, {"event": event, "data": data}) != "ok":
                raise RelayError("Moonraker did not acknowledge the Temperature event")
        except self.display.DisplayRequestError as exc:
            message = str(exc).casefold()
            if any(marker in message for marker in (
                "deadline", "closed", "read failed", "before reply", "handshake failed",
            )):
                raise TransientRelayError("transient WebSocket transport failure") from exc
            raise RelayError("Moonraker rejected the Temperature WebSocket exchange") from exc
        finally:
            if "connection" in locals():
                connection.close()


class SpareAdapter:
    FILES = frozenset(("outbox.json", "inbox.json", "receipt.json", "delivery.json"))
    WINDOWS_ABSOLUTE = re.compile(r"^[A-Za-z]:\\[^\r\n'\"]{1,500}$")

    def __init__(self, communication_dir: str, access: Any | None = None):
        segments = communication_dir[3:].split("\\") if len(communication_dir) >= 3 else []
        if (
            not self.WINDOWS_ABSOLUTE.fullmatch(communication_dir)
            or any(segment in ("", ".", "..") for segment in segments)
        ):
            raise RelayError("communication directory must be an exact bounded Windows absolute path")
        self.communication_dir = communication_dir
        self.access = access if access is not None else _load("temperature_relay_spare_access", SPARE_PATH)
        self.script_hashes: list[str] = []

    def _invoke(self, operation: str, name: str, data: bytes | None = None, limit: int = MAX_REQUEST_BYTES) -> Any:
        if name not in self.FILES or operation not in ("read", "write"):
            raise RelayError("Windows communication operation is outside the file allowlist")
        if not 1 <= limit <= MAX_REQUEST_BYTES:
            raise RelayError("Windows communication limit is invalid")
        encoded_dir = base64.b64encode(self.communication_dir.encode("utf-8")).decode("ascii")
        encoded_data = base64.b64encode(data or b"").decode("ascii")
        script = f"""$ErrorActionPreference='Stop'
$D=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{encoded_dir}'))
$Root=Join-Path $env:LOCALAPPDATA '{ISOLATED_DATA_RELATIVE}'
$Expected=Join-Path $Root '{COMMUNICATION_RELATIVE}'
$Marker=Join-Path $Root '{ISOLATION_MARKER}'
$A=[IO.Path]::GetFullPath($D).TrimEnd('\\')
$B=[IO.Path]::GetFullPath($Expected).TrimEnd('\\')
if($A-ne$B -or !(Test-Path -LiteralPath $Marker -PathType Leaf)){{throw 'Isolated October 15 data marker/path mismatch.'}}
$N='{name}'
if(@('outbox.json','inbox.json','receipt.json','delivery.json')-notcontains$N){{throw 'Communication file denied.'}}
$P=Join-Path $B $N
if('{operation}'-eq'read'){{
 if(!(Test-Path -LiteralPath $P -PathType Leaf)){{@{{exists=$false}}|ConvertTo-Json -Compress;exit}}
 $X=[IO.File]::ReadAllBytes($P);if($X.Length-gt{limit}){{throw 'Communication file exceeds bound.'}}
 @{{exists=$true;bytes=$X.Length;sha256=([BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash($X))).Replace('-','').ToLowerInvariant();content_base64=[Convert]::ToBase64String($X)}}|ConvertTo-Json -Compress
}}else{{
 $X=[Convert]::FromBase64String('{encoded_data}');if($X.Length-gt{limit}){{throw 'Communication write exceeds bound.'}}
 [IO.Directory]::CreateDirectory($B)|Out-Null;$T=$P+'.relay-tmp';try{{[IO.File]::WriteAllBytes($T,$X);Move-Item -LiteralPath $T -Destination $P -Force}}finally{{Remove-Item -LiteralPath $T -Force -ErrorAction SilentlyContinue}}
 @{{written=$true;bytes=$X.Length;sha256=([BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash($X))).Replace('-','').ToLowerInvariant()}}|ConvertTo-Json -Compress
}}"""
        if len(script) > 8192:
            raise RelayError("bounded Windows communication script exceeds worker limit")
        self.script_hashes.append(hashlib.sha256(script.encode("utf-8")).hexdigest())
        response = self.access.request("exec", script, timeout=MAX_CALL_SECONDS)
        if response.get("error") or response.get("exit_code") != 0 or response.get("output_truncated"):
            raise RelayError("bounded Windows communication operation failed")
        try:
            return json.loads(response["stdout"])
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise RelayError("Windows communication response is invalid") from exc

    def read_json(self, name: str, limit: int = MAX_REQUEST_BYTES) -> Any | None:
        envelope = self._invoke("read", name, limit=limit)
        if envelope.get("exists") is False:
            return None
        try:
            data = base64.b64decode(envelope["content_base64"], validate=True)
        except (KeyError, ValueError, TypeError) as exc:
            raise RelayError("Windows communication content encoding is invalid") from exc
        if len(data) > limit or hashlib.sha256(data).hexdigest() != envelope.get("sha256"):
            raise RelayError("Windows communication content digest/size mismatch")
        try:
            return json.loads(data)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise RelayError("Windows communication file is not JSON") from exc

    def write_json(self, name: str, value: Any) -> None:
        data = canonical_bytes(value) + b"\n"
        if len(data) > MAX_REQUEST_BYTES:
            raise RelayError("Windows communication write exceeds 64 KiB")
        envelope = self._invoke("write", name, data=data)
        if envelope.get("written") is not True or envelope.get("sha256") != hashlib.sha256(data).hexdigest():
            raise RelayError("Windows communication write was not verified")


class Journal:
    def __init__(self, root: Path, request_id: str):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.root, 0o700)
        self.path = self.root / (request_id + ".json")

    def read(self) -> dict[str, Any] | None:
        if not self.path.exists():
            return None
        if self.path.stat().st_size > MAX_REQUEST_BYTES:
            raise RelayError("relay journal exceeds its bound")
        value = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise RelayError("relay journal is invalid")
        return value

    def write(self, value: dict[str, Any]) -> None:
        data = canonical_bytes(value) + b"\n"
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(data)
        os.chmod(temporary, 0o600)
        temporary.replace(self.path)
        os.chmod(self.path, 0o600)


class SessionRelay:
    PHASES = (
        "created", "request_sent", "result_received", "inbox_written",
        "receipt_received", "ack_sent", "complete",
    )

    def __init__(
        self, physical: Any, spare: Any, journal_root: Path,
        wall_time: Any = time.time, monotonic: Any = time.monotonic,
        sleep: Any = time.sleep, poll_seconds: float = POLL_SECONDS,
    ):
        self.physical = physical
        self.spare = spare
        self.journal_root = journal_root
        self.wall_time = wall_time
        self.monotonic = monotonic
        self.sleep = sleep
        self.poll_seconds = poll_seconds

    def _deadline_check(self, deadline: float, request: dict[str, Any]) -> None:
        if self.monotonic() >= deadline:
            raise RelayError("relay session exceeded its 900-second total deadline")
        if int(self.wall_time()) >= request["expires_at"]:
            raise RelayError("relay request expired before delivery completed")

    def _session_deadline_check(self, deadline: float) -> None:
        if self.monotonic() >= deadline:
            raise RelayError("relay session exceeded its 900-second total deadline")

    def _status(self, request: dict[str, Any], phase: str) -> None:
        self.spare.write_json("delivery.json", make_delivery(request, phase))

    def _physical_call(
        self, operation: Any, deadline: float, request: dict[str, Any],
        active_phase: str,
    ) -> Any:
        for attempt in range(1, MAX_TRANSPORT_ATTEMPTS + 1):
            self._deadline_check(deadline, request)
            try:
                return operation()
            except (TransientRelayError, OSError, TimeoutError) as exc:
                if attempt == MAX_TRANSPORT_ATTEMPTS:
                    raise RelayError("physical transport failed after five bounded attempts") from exc
                self._status(request, "retrying")
                self.sleep(min(self.poll_seconds, max(0.0, deadline - self.monotonic())))
                self._deadline_check(deadline, request)
                self._status(request, active_phase)
        raise AssertionError("unreachable bounded retry loop")

    @staticmethod
    def _storage_session(
        storage: Any, request: dict[str, Any], lease: dict[str, Any],
    ) -> dict[str, Any] | None:
        validate_lease(request, lease)
        if not isinstance(storage, dict):
            raise RelayError("native storage root is invalid")
        session = storage.get("session")
        if session is None:
            return None
        if not isinstance(session, dict):
            raise RelayError("native storage session is invalid")
        required = {"request", "lease", "acknowledged", "recovery_required", "state"}
        if not required.issubset(session):
            raise RelayError("native storage session is incomplete")
        if session["request"] != request:
            raise RelayError("native storage contains a conflicting request")
        # A deferred duplicate write can still expose an earlier valid lease for
        # this exact immutable request. Native owns the minimum-deadline merge;
        # treat the exact request as received without accepting other identities.
        validate_lease(request, session["lease"])
        if type(session["acknowledged"]) is not bool or type(session["recovery_required"]) is not bool:
            raise RelayError("native storage acknowledgement flags are invalid")
        if session["state"] not in ("received", "queued", "waiting", "returned"):
            raise RelayError("native storage state is invalid")
        if "result" not in session:
            # Lua serializes nil by omitting the key. Only the native pending
            # state may omit a result; selected/acknowledged states must retain it.
            if session["state"] != "received" or session["acknowledged"]:
                raise RelayError("native selected session is missing its result")
            session = dict(session, result=None)
        return session

    def _journal_value(
        self, outbox: dict[str, Any], phase: str, lease: dict[str, Any],
        result: dict[str, Any] | None = None, request_attempts: int = 0,
    ) -> dict[str, Any]:
        if type(request_attempts) is not int or not 0 <= request_attempts <= MAX_TRANSPORT_ATTEMPTS:
            raise RelayError("relay request-attempt journal bound is invalid")
        value = {
            "schema": "helix-orca-temperature-relay-journal/v1",
            "phase": phase,
            "outbox_sha256": canonical_sha256(outbox),
            "request_id": outbox["payload"]["request_id"],
            "origin_id": outbox["payload"]["origin_id"],
            "context_sha256": outbox["payload"]["context_sha256"],
            "file_sha256": outbox["payload"]["file_sha256"],
            "lease": validate_lease(outbox["payload"], lease),
            "request_attempts": request_attempts,
            "script_sha256": list(dict.fromkeys(getattr(self.spare, "script_hashes", [])))[-16:],
        }
        if result is not None:
            value["result"] = result
        return value

    def _wait_for_outbox(self, deadline: float) -> dict[str, Any]:
        transient_attempts = 0
        while True:
            self._session_deadline_check(deadline)
            try:
                outbox = self.spare.read_json("outbox.json", MAX_REQUEST_BYTES)
                transient_attempts = 0
            except (OSError, TimeoutError) as exc:
                transient_attempts += 1
                if transient_attempts >= MAX_TRANSPORT_ATTEMPTS:
                    raise RelayError("originating companion transport failed after five bounded attempts") from exc
                outbox = None
            if outbox is not None:
                return validate_outbox(outbox, int(self.wall_time()))
            self.sleep(min(self.poll_seconds, max(0.0, deadline - self.monotonic())))

    def _run_validated(
        self, outbox: dict[str, Any], deadline: float,
    ) -> dict[str, Any]:
        request = outbox["payload"]
        journal = Journal(self.journal_root, request["request_id"])
        prior = journal.read()
        digest = canonical_sha256(outbox)
        if prior is not None and prior.get("outbox_sha256") != digest:
            raise RelayError("recovery outbox conflicts with the retained relay session")
        phase = prior.get("phase", "created") if prior else "created"
        if phase not in self.PHASES:
            raise RelayError("relay journal phase is invalid")
        result = prior.get("result") if prior else None
        lease = prior.get("lease") if prior else None
        request_attempts = prior.get("request_attempts", 0) if prior else 0
        if type(request_attempts) is not int or not 0 <= request_attempts <= MAX_TRANSPORT_ATTEMPTS:
            raise RelayError("relay journal request-attempt count is invalid")
        if lease is not None:
            lease = validate_lease(request, lease)
        if result is not None:
            result = validate_selection_result(request, result, int(self.wall_time()))
        if phase == "complete":
            self._status(request, "delivered")
            return {"request_id": request["request_id"], "state": "complete", "recovered": True}
        if phase in ("result_received", "inbox_written", "receipt_received", "ack_sent"):
            self._status(request, "waiting_companion")

        self._deadline_check(deadline, request)

        def prepare_envelope() -> dict[str, Any]:
            self.physical.assert_ready()
            self.physical.verify_file(request)
            self._deadline_check(deadline, request)
            ready = self.physical.assert_ready()
            return make_wire_envelope(
                request, ready.get("eventtime"), self.wall_time(), lease,
            )

        receipt_session = None
        if phase in ("created", "request_sent"):
            phase = "request_sent"
            request_status = None
            while receipt_session is None:
                if request_attempts >= MAX_TRANSPORT_ATTEMPTS:
                    # A relay crash can occur after the fifth send but before its
                    # receipt read. Allow that exact persisted receipt to finish,
                    # while never emitting an unbudgeted sixth request.
                    self.sleep(min(
                        REQUEST_RECEIPT_GRACE_SECONDS,
                        max(0.0, deadline - self.monotonic()),
                    ))
                    self._deadline_check(deadline, request)
                    storage = self._physical_call(
                        self.physical.read_native_storage, deadline, request,
                        "waiting_selection",
                    )
                    observed = self._storage_session(storage, request, lease)
                    if observed is not None and observed["recovery_required"] is False:
                        receipt_session = observed
                        break
                    raise RelayError("native request receipt missing after five bounded deliveries")
                if request_attempts and request_status != "retrying":
                    self._status(request, "retrying")
                    request_status = "retrying"
                # Every non-complete invocation sends one fresh bounded envelope.
                # This re-establishes native state after a device restart. Further
                # sends happen only when the exact native receipt remains absent.
                envelope = self._physical_call(
                    prepare_envelope, deadline, request, "delivering",
                )
                lease = envelope["lease"]
                request_attempts += 1
                journal.write(self._journal_value(
                    outbox, phase, lease, result, request_attempts,
                ))
                try:
                    self.physical.send_event(REQUEST_EVENT, envelope)
                    self._status(request, "waiting_selection")
                    request_status = "waiting_selection"
                except (TransientRelayError, OSError, TimeoutError):
                    # Delivery is unknown, not absent. The next loop first waits
                    # for and checks the exact native receipt before redelivery.
                    self._status(request, "retrying")
                    request_status = "retrying"
                self.sleep(min(
                    REQUEST_RECEIPT_GRACE_SECONDS,
                    max(0.0, deadline - self.monotonic()),
                ))
                self._deadline_check(deadline, request)
                storage = self._physical_call(
                    self.physical.read_native_storage, deadline, request,
                    "waiting_selection",
                )
                observed = self._storage_session(storage, request, lease)
                if observed is not None and observed["recovery_required"] is False:
                    receipt_session = observed
            assert lease is not None
            if request_status != "waiting_selection":
                self._status(request, "waiting_selection")
        else:
            # Preserve the single fresh recovery envelope on a later-phase relay
            # restart, but do not enter receipt-driven redelivery after selection.
            envelope = self._physical_call(
                prepare_envelope, deadline, request, "waiting_companion",
            )
            lease = envelope["lease"]
            journal.write(self._journal_value(
                outbox, phase, lease, result, request_attempts,
            ))
            self._physical_call(
                lambda: self.physical.send_event(REQUEST_EVENT, envelope),
                deadline, request, "waiting_companion",
            )
            self._status(request, "waiting_companion")

        if phase == "request_sent":
            session = receipt_session
            while session is None or session["result"] is None:
                self._deadline_check(deadline, request)
                storage = self._physical_call(
                    self.physical.read_native_storage, deadline, request, "waiting_selection",
                )
                session = self._storage_session(storage, request, lease)
                if session is None or session["result"] is None:
                    self.sleep(min(self.poll_seconds, max(0.0, deadline - self.monotonic())))
            result = validate_selection_result(request, session["result"], int(self.wall_time()))
            phase = "result_received"
            journal.write(self._journal_value(
                outbox, phase, lease, result, request_attempts,
            ))

        if phase in ("result_received", "inbox_written"):
            assert result is not None
            self.spare.write_json("inbox.json", result)
            phase = "inbox_written"
            journal.write(self._journal_value(
                outbox, phase, lease, result, request_attempts,
            ))
            self._status(request, "waiting_companion")

        if phase == "inbox_written":
            while True:
                self._deadline_check(deadline, request)
                receipt = self.spare.read_json("receipt.json", MAX_REQUEST_BYTES)
                if receipt is not None:
                    validate_ack(request, receipt, int(self.wall_time()))
                    if receipt != make_ack(result):
                        raise RelayError("originating companion receipt conflicts with the selected result")
                    break
                self.sleep(min(self.poll_seconds, max(0.0, deadline - self.monotonic())))
            phase = "receipt_received"
            journal.write(self._journal_value(
                outbox, phase, lease, result, request_attempts,
            ))

        if phase in ("receipt_received", "ack_sent"):
            assert result is not None
            ack = make_ack(result)
            self._deadline_check(deadline, request)

            def send_ack() -> None:
                self.physical.assert_ready()
                self.physical.send_event(ACK_EVENT, ack)

            self._physical_call(send_ack, deadline, request, "waiting_companion")
            phase = "ack_sent"
            journal.write(self._journal_value(
                outbox, phase, lease, result, request_attempts,
            ))

        while True:
            self._deadline_check(deadline, request)
            storage = self._physical_call(
                self.physical.read_native_storage, deadline, request, "waiting_companion",
            )
            session = self._storage_session(storage, request, lease)
            if session is not None and session["result"] == result and session["acknowledged"] is True:
                break
            self.sleep(min(self.poll_seconds, max(0.0, deadline - self.monotonic())))
        journal.write(self._journal_value(
            outbox, "complete", lease, result, request_attempts,
        ))
        self._status(request, "delivered")
        return {
            "request_id": request["request_id"],
            "origin_id": request["origin_id"],
            "state": "complete",
            "value": result["value"],
            "not_applied": True,
        }

    def run(self) -> dict[str, Any]:
        deadline = self.monotonic() + MAX_SESSION_SECONDS
        outbox = self._wait_for_outbox(deadline)
        request = outbox["payload"]
        self._status(request, "delivering")
        try:
            return self._run_validated(outbox, deadline)
        except (RelayError, OSError, ValueError, json.JSONDecodeError):
            try:
                self._status(request, "failed")
            except (RelayError, OSError, ValueError, json.JSONDecodeError):
                pass
            raise


def default_journal_root() -> Path:
    base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
    return base / "helix-orca-calibration" / "temperature-relay"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--communication-dir", required=True)
    parser.add_argument("--moonraker", required=True)
    parser.add_argument("--expected-host", required=True)
    parser.add_argument("--expected-moonraker-version", required=True)
    parser.add_argument("--api-key-env")
    parser.add_argument("--acknowledge-trusted-lan-http", required=True)
    parser.add_argument("--journal-root", type=Path, default=default_journal_root())
    args = parser.parse_args()
    if args.acknowledge_trusted_lan_http != TRUSTED_LAN_ACK:
        raise RelayError("explicit acknowledgement of the existing trusted-LAN HTTP boundary is required")
    api_key = os.environ.get(args.api_key_env) if args.api_key_env else None
    if args.api_key_env and not api_key:
        raise RelayError("explicit approved API-key environment variable is unavailable")
    physical = PhysicalAdapter(
        args.moonraker, args.expected_host, args.expected_moonraker_version, api_key,
    )
    spare = SpareAdapter(args.communication_dir)

    def expired(_signum: int, _frame: Any) -> None:
        raise RelayError("relay session exceeded its 900-second total deadline")

    previous = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, MAX_SESSION_SECONDS)
    try:
        result = SessionRelay(physical, spare, args.journal_root).run()
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RelayError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
