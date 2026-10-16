"""Bounded, transport-neutral Temperature communication protocol.

This module is embedded verbatim in the generated Orca plugin.  It has no
transport and only reads or writes fixed artifact names below a caller-owned
storage directory.
"""

import json
import math
import os
import pathlib
import re
import secrets
import time


OUTBOX_SCHEMA = "helix-orca-temperature-outbox/v1"
SESSION_SCHEMA = "helix-orca-temperature-session/v1"
RESULT_SCHEMA = "helix-orca-temperature-selection/v1"
ACK_SCHEMA = "helix-orca-temperature-ack/v1"
DELIVERY_SCHEMA = "helix-orca-temperature-delivery/v1"
STATE_SCHEMA = "helix-orca-temperature-local-state/v1"
SETTING = "nozzle_temperature"
CHOICES = [230, 225, 220, 215, 210, 205, 200, 195, 190]
TTL_SECONDS = 900
MAX_FILE_BYTES = 20_000_000
MAX_ARTIFACT_BYTES = 262_144
HEX32 = re.compile(r"[a-f0-9]{32}")
HEX64 = re.compile(r"[a-f0-9]{64}")
SAFE_FILE = re.compile(r"[^/\\]+\.gcode")
ARTIFACT_NAMES = frozenset({"outbox.json", "inbox.json", "receipt.json", "state.json", "delivery.json"})
DELIVERY_PHASES = frozenset({
    "delivering", "waiting_selection", "waiting_companion", "delivered", "retrying", "failed",
})
DELIVERY_MESSAGES = {
    "delivering": "Delivering the retained request.",
    "waiting_selection": "Request delivered; waiting for a simulated HelixScreen selection.",
    "waiting_companion": "Selection returned; waiting for this originating Orca companion.",
    "delivered": "Communication acknowledged by the originating companion.",
    "retrying": "Delivery is delayed; the relay is retrying automatically.",
    "failed": "Delivery failed after bounded retries. Retry republishes the same request and IDs.",
}


class CommunicationProtocolError(ValueError):
    pass


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def json_digest(value):
    import hashlib
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _exact_keys(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise CommunicationProtocolError(f"Malformed {label} fields.")


def _text(value, label, limit=128):
    try:
        encoded = value.encode("utf-8") if isinstance(value, str) else b""
    except UnicodeError:
        encoded = b""
    if (not isinstance(value, str) or not value.strip() or not encoded or len(encoded) > limit
            or any(ord(character) < 32 or ord(character) == 127 for character in value)):
        raise CommunicationProtocolError(f"Invalid {label}.")
    return value


def _hex(value, pattern, label):
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise CommunicationProtocolError(f"Invalid {label}.")
    return value


def _number(value, label, minimum, maximum):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise CommunicationProtocolError(f"Invalid {label}.")
    if not minimum <= value <= maximum:
        raise CommunicationProtocolError(f"Invalid {label}.")
    return value


def _integer(value, label, minimum, maximum):
    if type(value) is not int or not minimum <= value <= maximum:
        raise CommunicationProtocolError(f"Invalid {label}.")
    return value


PAYLOAD_KEYS = (
    "schema", "simulation_only", "not_applied", "request_id", "origin_id",
    "context_sha256", "file_sha256", "file", "file_bytes", "printer",
    "filament", "process", "nozzle_mm", "saved_current", "edited_current",
    "current", "setting", "choices", "expires_at", "ttl_seconds",
)
RESULT_KEYS = (
    "schema", "simulation_only", "not_applied", "request_id", "origin_id",
    "context_sha256", "file_sha256", "file", "file_bytes", "setting", "value",
)


def validate_forward_payload(value, now=None):
    _exact_keys(value, PAYLOAD_KEYS, "Temperature session")
    if value["schema"] != SESSION_SCHEMA or value["simulation_only"] is not True or value["not_applied"] is not True:
        raise CommunicationProtocolError("Invalid Temperature session safety markers.")
    _hex(value["request_id"], HEX32, "request ID")
    _hex(value["origin_id"], HEX32, "origin ID")
    _hex(value["context_sha256"], HEX64, "context digest")
    _hex(value["file_sha256"], HEX64, "file digest")
    try:
        file_name_bytes = value["file"].encode("utf-8") if isinstance(value["file"], str) else b""
    except UnicodeError:
        file_name_bytes = b""
    if (not isinstance(value["file"], str) or SAFE_FILE.fullmatch(value["file"]) is None
            or ".." in value["file"] or not file_name_bytes or len(file_name_bytes) > 255
            or any(ord(c) < 32 or ord(c) == 127 for c in value["file"])):
        raise CommunicationProtocolError("Invalid G-code basename.")
    _integer(value["file_bytes"], "file byte count", 1, MAX_FILE_BYTES)
    for key in ("printer", "filament", "process"):
        _text(value[key], key)
    _number(value["nozzle_mm"], "nozzle diameter", 0.05, 2.0)
    for key in ("saved_current", "edited_current", "current"):
        _number(value[key], key, 0, 500)
    if value["setting"] != SETTING or value["choices"] != CHOICES or any(type(item) is not int for item in value["choices"]):
        raise CommunicationProtocolError("Invalid Temperature setting or choices.")
    _integer(value["ttl_seconds"], "TTL", 1, TTL_SECONDS)
    _integer(value["expires_at"], "expiry", 1, 4_102_444_800)
    current_time = int(time.time() if now is None else now)
    if value["expires_at"] <= current_time:
        raise CommunicationProtocolError("Temperature request expired.")
    if value["expires_at"] > current_time + value["ttl_seconds"]:
        raise CommunicationProtocolError("Temperature request expiry exceeds its TTL.")
    return json.loads(canonical_json(value))


def validate_outbox(value, now=None):
    _exact_keys(value, ("schema", "target", "payload"), "outbox")
    if value["schema"] != OUTBOX_SCHEMA or not isinstance(value["target"], dict):
        raise CommunicationProtocolError("Invalid outbox.")
    if len(canonical_json(value["target"]).encode("utf-8")) > 65_536:
        raise CommunicationProtocolError("Outbox target is too large.")
    payload = validate_forward_payload(value["payload"], now=now)
    if json_digest(value["target"]) != payload["context_sha256"]:
        raise CommunicationProtocolError("Outbox target digest mismatch.")
    target = value["target"]
    runtime = target.get("runtime") if isinstance(target, dict) else None
    if runtime != {"version": "2.5.0-dev", "build": "6a7763f0"}:
        raise CommunicationProtocolError("Outbox target is not the qualified October 15 runtime.")
    bindings = {
        "printer": _identity(target, "printer"), "filament": _identity(target, "filament"),
        "process": _identity(target, "process"), "nozzle_mm": target.get("nozzle_mm"),
        "saved_current": target.get("saved_temperature"), "edited_current": target.get("edited_temperature"),
        "current": target.get("effective_temperature"),
    }
    for key, expected in bindings.items():
        if type(payload[key]) is not type(expected) or payload[key] != expected:
            raise CommunicationProtocolError(f"Outbox target binding mismatch: {key}.")
    return {"schema": OUTBOX_SCHEMA, "target": json.loads(canonical_json(value["target"])), "payload": payload}


def validate_selection_result(payload, value, now=None):
    payload = validate_forward_payload(payload, now=now)
    _exact_keys(value, RESULT_KEYS, "Temperature selection")
    if value["schema"] != RESULT_SCHEMA or value["simulation_only"] is not True or value["not_applied"] is not True:
        raise CommunicationProtocolError("Invalid Temperature selection safety markers.")
    for key in ("request_id", "origin_id", "context_sha256", "file_sha256", "file", "file_bytes", "setting"):
        if type(value[key]) is not type(payload[key]) or value[key] != payload[key]:
            raise CommunicationProtocolError(f"Stale or mismatched result: {key}.")
    if type(value["value"]) is not int or value["value"] not in payload["choices"]:
        raise CommunicationProtocolError("Selected value was not prepared for this request.")
    return json.loads(canonical_json(value))


def make_ack(result):
    _exact_keys(result, RESULT_KEYS, "Temperature selection")
    ack = dict(result)
    ack["schema"] = ACK_SCHEMA
    return ack


def validate_ack(payload, value, now=None):
    expected_result = dict(value) if isinstance(value, dict) else value
    _exact_keys(expected_result, RESULT_KEYS, "Temperature acknowledgement")
    if expected_result["schema"] != ACK_SCHEMA:
        raise CommunicationProtocolError("Invalid acknowledgement schema.")
    selection = dict(expected_result)
    selection["schema"] = RESULT_SCHEMA
    validate_selection_result(payload, selection, now=now)
    return json.loads(canonical_json(expected_result))


def validate_delivery(payload, value):
    # Delivery remains useful at and after expiry, so validate the immutable
    # session structurally at its creation instant rather than against now.
    structural_now = payload["expires_at"] - payload["ttl_seconds"]
    payload = validate_forward_payload(payload, now=structural_now)
    _exact_keys(value, ("schema", "request_id", "origin_id", "context_sha256", "phase"), "delivery status")
    if value["schema"] != DELIVERY_SCHEMA:
        raise CommunicationProtocolError("Invalid delivery status schema.")
    for key in ("request_id", "origin_id", "context_sha256"):
        if type(value[key]) is not type(payload[key]) or value[key] != payload[key]:
            raise CommunicationProtocolError(f"Stale or mismatched delivery status: {key}.")
    if type(value["phase"]) is not str or value["phase"] not in DELIVERY_PHASES:
        raise CommunicationProtocolError("Invalid delivery phase.")
    return json.loads(canonical_json(value))


def bounded_read_json(path, max_bytes=MAX_ARTIFACT_BYTES):
    path = pathlib.Path(path)
    if path.name not in ARTIFACT_NAMES:
        raise CommunicationProtocolError("Artifact path is not permitted.")
    size = path.stat().st_size
    if size <= 0 or size > max_bytes:
        raise CommunicationProtocolError("Artifact size is invalid.")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CommunicationProtocolError(f"Artifact JSON is invalid: {exc}") from exc
    return value


def atomic_write_json(path, value):
    path = pathlib.Path(path)
    if path.name not in ARTIFACT_NAMES:
        raise CommunicationProtocolError("Artifact path is not permitted.")
    encoded = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
    if len(encoded) > MAX_ARTIFACT_BYTES:
        raise CommunicationProtocolError("Artifact is too large.")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name("." + path.name + "." + secrets.token_hex(8) + ".tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
        try:
            directory_fd = os.open(str(path.parent), os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            # Windows does not support opening directories this way; the file
            # itself was still flushed before the atomic replacement.
            pass
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return str(path)


def _identity(target, role):
    try:
        value = target[role]["selected_saved"]["name"]
    except (KeyError, TypeError):
        raise CommunicationProtocolError(f"Original {role} identity is unavailable.")
    return _text(value, role)


def make_forward_payload(target, file_value, origin_id, now=None, request_id=None):
    if not isinstance(target, dict):
        raise CommunicationProtocolError("Original target is unavailable.")
    if not isinstance(file_value, dict):
        raise CommunicationProtocolError("Temperature file is unavailable.")
    current_time = int(time.time() if now is None else now)
    payload = {
        "schema": SESSION_SCHEMA,
        "simulation_only": True,
        "not_applied": True,
        "request_id": request_id or secrets.token_hex(16),
        "origin_id": origin_id,
        "context_sha256": json_digest(target),
        "file_sha256": file_value.get("sha256"),
        "file": file_value.get("name"),
        "file_bytes": file_value.get("size"),
        "printer": _identity(target, "printer"),
        "filament": _identity(target, "filament"),
        "process": _identity(target, "process"),
        "nozzle_mm": target.get("nozzle_mm"),
        "saved_current": target.get("saved_temperature"),
        "edited_current": target.get("edited_temperature"),
        "current": target.get("effective_temperature"),
        "setting": SETTING,
        "choices": list(CHOICES),
        "expires_at": current_time + TTL_SECONDS,
        "ttl_seconds": TTL_SECONDS,
    }
    return validate_forward_payload(payload, now=current_time)


def instructions_for(payload, result):
    return {
        "profile": payload["filament"],
        "setting": SETTING,
        "setting_label": "Filament > Print temperature > Nozzle > Other layers",
        "original_saved_value": payload["saved_current"],
        "original_edited_value": payload["edited_current"],
        "original_effective_value": payload["current"],
        "selected_value": result["value"],
        "status": "NOT APPLIED",
        "simulation_only": True,
    }


class TemperatureCommunicationState:
    def __init__(self, storage_root, now=None):
        self.directory = pathlib.Path(storage_root) / "communication"
        self.now = now or time.time
        self.target = None
        self.file = None
        self.origin_id = None
        self.payload = None
        self.result = None
        self.instructions = None
        self.delivery_phase = None
        self.recovery_error = None
        self._recover()

    def _path(self, name):
        if name not in ARTIFACT_NAMES:
            raise CommunicationProtocolError("Artifact name is not permitted.")
        return self.directory / name

    def _snapshot(self):
        return {
            "schema": STATE_SCHEMA,
            "target": self.target,
            "file": self.file,
            "origin_id": self.origin_id,
            "payload": self.payload,
            "result": self.result,
            "instructions": self.instructions,
        }

    def _validate_snapshot(self, value):
        _exact_keys(value, ("schema", "target", "file", "origin_id", "payload", "result", "instructions"), "local state")
        if value["schema"] != STATE_SCHEMA or not isinstance(value["target"], dict):
            raise CommunicationProtocolError("Invalid local state.")
        _hex(value["origin_id"], HEX32, "origin ID")
        if value["file"] is not None:
            self._validate_file_descriptor(value["file"])
        if value["payload"] is not None:
            # Recovery preserves an expired request so it can reject late returns
            # against the original identity rather than losing correlation.
            structural_now = value["payload"]["expires_at"] - value["payload"]["ttl_seconds"]
            validate_outbox({"schema": OUTBOX_SCHEMA, "target": value["target"], "payload": value["payload"]}, now=structural_now)
            if value["origin_id"] != value["payload"]["origin_id"]:
                raise CommunicationProtocolError("Local origin mismatch.")
            if value["file"] is None:
                raise CommunicationProtocolError("Local request has no file descriptor.")
            for file_key, payload_key in (("name", "file"), ("size", "file_bytes"), ("sha256", "file_sha256")):
                if value["file"][file_key] != value["payload"][payload_key]:
                    raise CommunicationProtocolError("Local file identity mismatch.")
        if value["result"] is not None:
            if value["payload"] is None:
                raise CommunicationProtocolError("Result has no local request.")
            # A committed result remains recoverable after expiry; identity and choice stay strict.
            relaxed_now = value["payload"]["expires_at"] - value["payload"]["ttl_seconds"]
            validate_selection_result(value["payload"], value["result"], now=relaxed_now)
            if value["instructions"] != instructions_for(value["payload"], value["result"]):
                raise CommunicationProtocolError("Local instructions mismatch.")
        elif value["instructions"] is not None:
            raise CommunicationProtocolError("Instructions have no committed result.")
        return value

    @staticmethod
    def _validate_file_descriptor(value):
        _exact_keys(value, ("name", "size", "sha256", "bands"), "local file")
        probe_target = {
            "runtime": {"version": "2.5.0-dev", "build": "6a7763f0"},
            "printer": {"selected_saved": {"name": "probe"}},
            "filament": {"selected_saved": {"name": "probe"}},
            "process": {"selected_saved": {"name": "probe"}},
            "nozzle_mm": 0.4, "saved_temperature": 1, "edited_temperature": 1,
            "effective_temperature": 1,
        }
        make_forward_payload(probe_target, value, "0" * 32, now=1, request_id="0" * 32)
        if value["bands"] != CHOICES:
            raise CommunicationProtocolError("Local file choices mismatch.")
        return value

    def _recover(self):
        path = self._path("state.json")
        if not path.exists():
            return
        try:
            value = self._validate_snapshot(bounded_read_json(path))
            for key in ("target", "file", "origin_id", "payload", "result", "instructions"):
                setattr(self, key, value[key])
            if self.result is not None:
                atomic_write_json(self._path("receipt.json"), make_ack(self.result))
        except Exception as exc:
            self.recovery_error = str(exc)

    def _persist(self):
        atomic_write_json(self._path("state.json"), self._snapshot())

    def start_new(self, target):
        # This explicit user action is the only operation that abandons a pending request.
        if (self.payload is not None and self.result is None
                and self.payload["expires_at"] > int(self.now())):
            raise CommunicationProtocolError(
                "The current request is still pending. Retry it or wait for its result/expiry before starting a new calibration."
            )
        copied = json.loads(canonical_json(target))
        origin_id = secrets.token_hex(16)
        self.target, self.file, self.origin_id = copied, None, origin_id
        self.payload = self.result = self.instructions = None
        self.delivery_phase = None
        self.recovery_error = None
        self.directory.mkdir(parents=True, exist_ok=True)
        for name in ("outbox.json", "inbox.json", "receipt.json", "delivery.json"):
            try:
                self._path(name).unlink()
            except FileNotFoundError:
                pass
        self._persist()

    def select_file(self, value, validator):
        if self.target is None:
            raise CommunicationProtocolError("Keep the original profile first.")
        if self.payload is not None:
            raise CommunicationProtocolError("Start a new calibration before replacing a pending file.")
        try:
            candidate = validator(value)
            self._validate_file_descriptor(candidate)
        except Exception:
            self.file = None
            self._persist()
            raise
        self.file = candidate
        self._persist()

    def send(self):
        if self.payload is not None:
            outbox = validate_outbox({"schema": OUTBOX_SCHEMA, "target": self.target, "payload": self.payload}, now=int(self.now()))
            atomic_write_json(self._path("outbox.json"), outbox)
            return "Request retry reused the existing request."
        if self.target is None or self.file is None or self.origin_id is None:
            raise CommunicationProtocolError("Keep the original profile and select its exact Temperature file.")
        payload = make_forward_payload(self.target, self.file, self.origin_id, now=int(self.now()))
        outbox = validate_outbox({"schema": OUTBOX_SCHEMA, "target": self.target, "payload": payload}, now=int(self.now()))
        self.payload = payload
        try:
            self._persist()
        except Exception:
            self.payload = None
            raise
        atomic_write_json(self._path("outbox.json"), outbox)
        return "Request ready for delivery; no print started and no profile changed."

    def poll_inbox(self):
        if self.payload is None:
            return None
        path = self._path("inbox.json")
        if not path.exists():
            return None
        candidate = bounded_read_json(path)
        if self.result is not None:
            if candidate != self.result:
                raise CommunicationProtocolError("Conflicting duplicate result rejected.")
            atomic_write_json(self._path("receipt.json"), make_ack(self.result))
            return "Duplicate result ignored; receipt preserved."
        result = validate_selection_result(self.payload, candidate, now=int(self.now()))
        instructions = instructions_for(self.payload, result)
        previous_result, previous_instructions = self.result, self.instructions
        self.result, self.instructions = result, instructions
        try:
            self._persist()  # Commit locally before acknowledging transport.
        except Exception:
            self.result, self.instructions = previous_result, previous_instructions
            raise
        atomic_write_json(self._path("receipt.json"), make_ack(result))
        return "Selection received; NOT APPLIED."

    def poll_delivery(self):
        if self.payload is None:
            return None
        path = self._path("delivery.json")
        if not path.exists():
            return None
        delivery = validate_delivery(self.payload, bounded_read_json(path))
        self.delivery_phase = delivery["phase"]
        return DELIVERY_MESSAGES[self.delivery_phase]

    def is_expired(self):
        return (self.payload is not None and self.result is None
                and self.payload["expires_at"] <= int(self.now()))
