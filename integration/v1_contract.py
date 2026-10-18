"""Shared bounded V1 objects. No host, network, execution or printer APIs."""
import hashlib
import json
import math
import re
import time

CALIBRATIONS = ("temperature", "flow_ratio_yolo", "pressure_advance_pattern", "retraction", "max_volumetric_speed")
DEFAULTS = {
    "temperature": {"start": 230, "end": 190, "step": 5, "scale": True},
    "flow_ratio_yolo": {"pass": 1},
    "pressure_advance_pattern": {"start": 0, "end": 0.08, "step": 0.005},
    "retraction": {"start": 0, "end": 2, "step": 0.1},
    "max_volumetric_speed": {"start": 5, "end": 20, "step": 0.5},
}
SETTINGS = {"temperature": "nozzle_temperature", "flow_ratio_yolo": "filament_flow_ratio",
            "pressure_advance_pattern": "pressure_advance", "retraction": "filament_retraction_length",
            "max_volumetric_speed": "filament_max_volumetric_speed"}
MAX_MESSAGE = 1048576


class ContractError(ValueError):
    pass


def canonical(value):
    try:
        data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, UnicodeError) as exc:
        raise ContractError("Non-finite or unserializable JSON") from exc
    if len(data) > MAX_MESSAGE:
        raise ContractError("V1 message exceeds 1 MiB")
    return data


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def exact(value, fields, label):
    if not isinstance(value, dict) or set(value) != set(fields.split()):
        raise ContractError("Malformed " + label + " fields")


def text(value, label, maximum=512):
    if not isinstance(value, str) or not value.strip() or len(value.encode("utf-8")) > maximum or any(ord(c) < 32 for c in value):
        raise ContractError("Invalid " + label)
    return value


def hex_value(value, size=64):
    if not isinstance(value, str) or re.fullmatch("[a-f0-9]{%d}" % size, value) is None:
        raise ContractError("Invalid identity digest")
    return value


def number(value, minimum, maximum):
    if type(value) not in (int, float) or not math.isfinite(value) or not minimum <= value <= maximum:
        raise ContractError("Parameter outside supported native range")
    return value


def validate_parameters(calibration, value):
    if calibration not in CALIBRATIONS:
        raise ContractError("Unknown calibration")
    exact(value, " ".join(DEFAULTS[calibration]), "parameters")
    if calibration == "flow_ratio_yolo":
        if type(value["pass"]) is not int or value["pass"] != 1:
            raise ContractError("V1 supports native YOLO Recommended pass 1")
    elif calibration == "temperature":
        if any(type(value[k]) is not int for k in ("start", "end", "step")):
            raise ContractError("Temperature bands must be integers")
        number(value["start"], 160, 500)
        number(value["end"], 155, 495)
        if value["step"] != 5 or value["start"] < value["end"] + 5 or (value["start"] - value["end"]) % 5:
            raise ContractError("Native Temperature uses descending 5 degree bands")
        if type(value["scale"]) is not bool:
            raise ContractError("Temperature scale must be boolean")
    else:
        limits = {"pressure_advance_pattern": (0, 5, 0.001), "retraction": (0, 20, 0.001),
                  "max_volumetric_speed": (0.01, 200, 0.001)}
        low, high, step = limits[calibration]
        number(value["start"], low, high)
        number(value["end"], low, high)
        number(value["step"], step, high)
        if value["end"] < value["start"] + value["step"] or (value["end"] - value["start"]) / value["step"] > 1000:
            raise ContractError("Native range needs at least two and at most 1001 samples")
    return json.loads(canonical(value))


def validate_context(value):
    exact(value, "schema origin_id runtime printer process filament effective nozzle_mm", "context")
    if value["schema"] != "helix-orca-v1-context/v1":
        raise ContractError("Unknown context schema")
    hex_value(value["origin_id"], 32)
    exact(value["runtime"], "version build", "runtime")
    text(value["runtime"]["version"], "runtime version")
    text(value["runtime"]["build"], "runtime build")
    number(value["nozzle_mm"], 0.05, 2)
    for role in ("printer", "process", "filament"):
        exact(value[role], "saved edited", role)
        for kind in ("saved", "edited"):
            exact(value[role][kind], "name config", role + " " + kind)
            text(value[role][kind]["name"], "preset name")
            _config(value[role][kind]["config"])
    _config(value["effective"])
    return json.loads(canonical(value))


def _config(value):
    if not isinstance(value, dict) or not value or len(value) > 5000:
        raise ContractError("Configuration unavailable")
    for k, v in value.items():
        text(k, "configuration key", 128)
        if not isinstance(v, str):
            raise ContractError("Configuration must preserve Orca serialized values")


def validate_request(value, now=None):
    exact(value, "schema request_id origin_id context_sha256 calibration parameters created_at expires_at not_applied", "request")
    if value["schema"] != "helix-orca-v1-request/v1" or value["not_applied"] is not True:
        raise ContractError("Invalid request safety/schema")
    hex_value(value["request_id"], 32)
    hex_value(value["origin_id"], 32)
    hex_value(value["context_sha256"])
    validate_parameters(value["calibration"], value["parameters"])
    if type(value["created_at"]) is not int or type(value["expires_at"]) is not int:
        raise ContractError("Integer request timestamps required")
    current = time.time() if now is None else now
    if not value["created_at"] <= current < value["expires_at"] or not 1 <= value["expires_at"] - value["created_at"] <= 3600:
        raise ContractError("Stale or future request")
    return json.loads(canonical(value))


def validate_prepared(value, request):
    exact(value, "schema request_id origin_id context_sha256 request_sha256 calibration parameters artifact generator parity not_applied", "prepared job")
    if value["schema"] != "helix-orca-v1-prepared/v1" or value["not_applied"] is not True:
        raise ContractError("Invalid prepared schema/safety")
    for key in ("request_id", "origin_id", "context_sha256", "calibration", "parameters"):
        if canonical(value[key]) != canonical(request[key]):
            raise ContractError("Prepared job differs from request: " + key)
    if value["request_sha256"] != digest(request):
        raise ContractError("Prepared request digest differs")
    exact(value["generator"], "build route", "generator")
    for k in ("build", "route"):
        text(value["generator"][k], "generator " + k)
    exact(value["parity"], "qualified report_sha256 reason", "parity")
    if type(value["parity"]["qualified"]) is not bool:
        raise ContractError("Explicit parity disposition required")
    text(value["parity"]["reason"], "parity reason", 1024)
    if value["parity"]["report_sha256"] is not None:
        hex_value(value["parity"]["report_sha256"])
    if value["artifact"] is not None:
        artifact = value["artifact"]
        exact(artifact, "name size sha256", "artifact")
        text(artifact["name"], "artifact name", 255)
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*\.gcode", artifact["name"]) or ".." in artifact["name"]:
            raise ContractError("Unsafe artifact name")
        if type(artifact["size"]) is not int or not 0 < artifact["size"] <= 100_000_000:
            raise ContractError("Artifact size outside bounds")
        hex_value(artifact["sha256"])
    if value["parity"]["qualified"] and (value["artifact"] is None or value["parity"]["report_sha256"] is None):
        raise ContractError("Qualification needs artifact and parity evidence")
    return json.loads(canonical(value))
