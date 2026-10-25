"""Shared bounded V1 objects. No host, network, execution or printer APIs."""
import hashlib
import json
import math
import re
import time
from decimal import Decimal, InvalidOperation

CALIBRATIONS = ("temperature", "flow_ratio_yolo", "pressure_advance_pattern", "retraction", "max_volumetric_speed")
ORCA_SOURCE_V2 = "b5e9cb3c5e7a925adf8379366ae580e4dabb1d03"
ORCA_RUNTIME_V2 = {"version": "2.5.0-dev", "build": "b5e9cb3c"}
ORCA_ARCHIVE_SHA256_V2 = "e38b26af21e17e5aa8785a3d6041a7dae9cb934060571ce947b33b7ce10346c0"
ORCA_EXECUTABLE_SHA256_V2 = "aab75b0bf66bba057e695ffd8425d723f881b7d409a496c486caad0983fe6761"
ORCA_UPSTREAM_RUN_V2 = "40220020944"
ORCA_UPSTREAM_JOBS_V2 = {
    "windows_x64_build": "121250255545",
    "windows_build_script_tests": "121249364052",
    "windows_x64_unit_tests": "121261641595",
}
KNOWN_WARNINGS_V2 = {"1000C001": "bed_temperature_too_high_than_filament"}
V2_QUALIFICATION_CONTEXTS = ("voron", "ad5x")
V2_QUALIFICATION_PARAMETER_CASES = (
    "default", "non_default_range", "non_default_step", "lower_boundary", "upper_boundary",
)
V2_GENERATOR_ROUTES = frozenset(("stock-cli-recipe-v2", "native-engine-v2"))
DEFAULTS = {
    "temperature": {"start": 230, "end": 190, "step": 5, "scale": True},
    "flow_ratio_yolo": {"pass": 1},
    "pressure_advance_pattern": {"start": 0, "end": 0.08, "step": 0.005},
    "retraction": {"start": 0, "end": 2, "step": 0.1},
    "max_volumetric_speed": {"start": 5, "end": 20, "step": 0.5},
}
PA_DEFAULTS = {
    "direct_drive": {"start": 0, "end": 0.08, "step": 0.005},
    "bowden": {"start": 0, "end": 1, "step": 0.05},
}
# These are existing V1 resource envelopes, not Orca's physical printer limits.
PARAMETER_LIMITS = {
    "temperature": {"start": [160, 500], "end": [155, 495]},
    "pressure_advance_pattern": {"start": [0, 5], "end": [0, 5], "step": [0.001, 5]},
    "retraction": {"start": [0, 20], "end": [0, 20], "step": [0.001, 20]},
    "max_volumetric_speed": {"start": [0.01, 200], "end": [0.01, 200], "step": [0.001, 200]},
}


def context_extruder_type(context):
    """Only the effective native serialized value may select PA defaults."""
    value = context.get("effective", {}).get("extruder_type") if context else None
    return {"Direct Drive": "direct_drive", "Bowden": "bowden"}.get(value, "unavailable")


def default_parameters(context=None):
    result = json.loads(json.dumps(DEFAULTS))
    kind = context_extruder_type(context)
    # The offer explicitly reports unavailable; the UI labels this generic DD
    # preset and offers the deliberate Bowden-default action. It is not a
    # claimed effective printer value or a saved-preset fallback.
    if kind in PA_DEFAULTS:
        result["pressure_advance_pattern"] = dict(PA_DEFAULTS[kind])
    return result


def flow_ratio_choices(original, flow_pass):
    """Native YOLO additive samples, including asymmetric Perfectionist ends."""
    if type(flow_pass) is not int or flow_pass not in (1, 2):
        raise ContractError("Choose YOLO Recommended or Perfectionist.")
    try:
        current = Decimal(str(original))
        if not current.is_finite():
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        raise ContractError("The original effective flow ratio is unavailable.") from None
    divisor, first, last = (100, -5, 5) if flow_pass == 1 else (200, -8, 7)
    return [float(current + Decimal(i) / divisor) for i in range(first, last + 1)]
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


def number(value, minimum, maximum, label="Parameter"):
    if type(value) not in (int, float) or not math.isfinite(value) or not minimum <= value <= maximum:
        raise ContractError(f"{label} must be a finite number from {minimum} to {maximum}.")
    return value


def validate_parameters(calibration, value):
    if calibration not in CALIBRATIONS:
        raise ContractError("Unknown calibration")
    exact(value, " ".join(DEFAULTS[calibration]), "parameters")
    if calibration == "flow_ratio_yolo":
        if type(value["pass"]) is not int or value["pass"] not in (1, 2):
            raise ContractError("Choose YOLO Recommended (1) or Perfectionist (2).")
    elif calibration == "temperature":
        if any(type(value[k]) is not int for k in ("start", "end", "step")):
            raise ContractError("Temperature bands must be integers")
        number(value["start"], 160, 500, "Starting temperature (°C)")
        number(value["end"], 155, 495, "Ending temperature (°C)")
        if value["step"] != 5 or value["start"] < value["end"] + 5 or value["start"] % 5 or value["end"] % 5:
            raise ContractError("Use 5°C increments, with Start at least 5°C above End. Temperature step is fixed at 5°C.")
        if type(value["scale"]) is not bool:
            raise ContractError("Temperature scale must be boolean")
    else:
        for key, bounds in PARAMETER_LIMITS[calibration].items():
            number(value[key], *bounds, label=key.capitalize())
        if value["end"] < value["start"] + value["step"]:
            raise ContractError("End must be at least Start + Step. Increase End or reduce Start/Step.")
        if (value["end"] - value["start"]) / value["step"] > 1000:
            raise ContractError("V1 supports at most 1001 samples. Increase Step or reduce the range.")
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


# V2 is intentionally parallel to V1. The original validators above continue to
# validate already-retained Issue #6/PR #15 evidence byte-for-byte; current
# jobs must opt in with a V2 schema and cannot be silently upgraded.
V2_DEFAULTS = {
    "temperature": {"start": 230, "end": 190, "step": 5, "scale": True},
    "flow_ratio_yolo": {"pass": 1, "pattern": "archimedean_chords"},
    "pressure_advance_pattern": {"start": 0, "end": 0.08, "step": 0.005,
                                 "accelerations": [], "speeds": []},
    "retraction": {"start": 0, "end": 2, "step": 0.1},
    "max_volumetric_speed": {"start": 5, "end": 20, "step": 0.5},
}


def default_parameters_v2(context=None):
    result = json.loads(json.dumps(V2_DEFAULTS))
    kind = context_extruder_type(context)
    if kind in PA_DEFAULTS:
        result["pressure_advance_pattern"].update(PA_DEFAULTS[kind])
    return result


def _positive_int_list(value, label):
    if not isinstance(value, list) or len(value) > 64:
        raise ContractError(label + " must contain at most 64 values")
    if any(type(item) is not int or item <= 0 for item in value):
        raise ContractError(label + " must contain positive integers")
    return value


def validate_parameters_v2(calibration, value):
    if calibration not in CALIBRATIONS:
        raise ContractError("Unknown calibration")
    exact(value, " ".join(V2_DEFAULTS[calibration]), "V2 parameters")
    if calibration == "flow_ratio_yolo":
        if type(value["pass"]) is not int or value["pass"] not in (1, 2):
            raise ContractError("Choose YOLO Recommended (1) or Perfectionist (2).")
        if value["pattern"] not in ("archimedean_chords", "monotonic"):
            raise ContractError("Choose an Orca native Flow Ratio pattern")
    elif calibration == "temperature":
        if any(type(value[key]) is not int for key in ("start", "end", "step")):
            raise ContractError("Temperature bands must be integers")
        number(value["start"], 160, 500, "Starting temperature (°C)")
        number(value["end"], 155, 495, "Ending temperature (°C)")
        if value["step"] != 5 or value["start"] < value["end"] + 5 or value["start"] % 5 or value["end"] % 5:
            raise ContractError("Use Orca's fixed 5°C increments, with Start at least 5°C above End.")
        if type(value["scale"]) is not bool:
            raise ContractError("Temperature scale must be boolean")
    else:
        for key in ("start", "end", "step"):
            if type(value[key]) not in (int, float) or not math.isfinite(value[key]):
                raise ContractError(key.capitalize() + " must be finite")
        if value["start"] < 0 or value["step"] <= 0 or value["end"] < value["start"] + value["step"]:
            raise ContractError("End must be at least Start + positive Step")
        if calibration == "max_volumetric_speed" and value["start"] <= 0:
            raise ContractError("Maximum volumetric speed Start must be positive")
        if calibration == "pressure_advance_pattern":
            accelerations = _positive_int_list(value["accelerations"], "Accelerations")
            speeds = _positive_int_list(value["speeds"], "Speeds")
            if accelerations and speeds and min(accelerations) <= max(speeds):
                raise ContractError("Orca PA Pattern requires every acceleration to exceed every speed")
    return json.loads(canonical(value))


def validate_context_v2(value):
    exact(value, "schema origin_id runtime printer process filament effective nozzle_mm filament_slots origin_filament", "V2 context")
    if value["schema"] != "helix-orca-v1-context/v2":
        raise ContractError("Unknown V2 context schema")
    hex_value(value["origin_id"], 32)
    exact(value["runtime"], "version build source_commit executable_sha256", "V2 runtime")
    if ({key: value["runtime"][key] for key in ("version", "build")} != ORCA_RUNTIME_V2
            or value["runtime"]["source_commit"] != ORCA_SOURCE_V2
            or value["runtime"]["executable_sha256"] != ORCA_EXECUTABLE_SHA256_V2):
        raise ContractError("Exact pinned Orca nightly runtime required")
    number(value["nozzle_mm"], 0.05, 2)
    for role in ("printer", "process", "filament"):
        exact(value[role], "saved edited", role)
        for kind in ("saved", "edited"):
            exact(value[role][kind], "name config", role + " " + kind)
            text(value[role][kind]["name"], "preset name")
            _config(value[role][kind]["config"])
    _config(value["effective"])
    slots = value["filament_slots"]
    if not isinstance(slots, list) or not slots or len(slots) > 64:
        raise ContractError("One to 64 explicit filament slots required")
    seen = set()
    for slot in slots:
        exact(slot, "slot_number preset_name", "filament slot")
        if type(slot["slot_number"]) is not int or slot["slot_number"] < 1 or slot["slot_number"] in seen:
            raise ContractError("Filament slot numbers must be unique positive integers")
        seen.add(slot["slot_number"])
        text(slot["preset_name"], "filament slot preset name")
    if seen != set(range(1, len(slots) + 1)):
        raise ContractError("Filament slots must cover the complete contiguous active vector")
    exact(value["origin_filament"], "slot_number preset_name shared_slots", "origin filament")
    origin = value["origin_filament"]
    if origin["slot_number"] not in seen or type(origin["shared_slots"]) is not list:
        raise ContractError("Originating filament slot is unavailable")
    selected = next(slot for slot in slots if slot["slot_number"] == origin["slot_number"])
    if selected["preset_name"] != origin["preset_name"]:
        raise ContractError("Originating filament preset differs from its slot")
    expected_shared = sorted(slot["slot_number"] for slot in slots if slot["preset_name"] == origin["preset_name"])
    if origin["shared_slots"] != expected_shared:
        raise ContractError("Shared filament slots must exactly identify the originating preset")
    if value["filament"]["saved"]["name"] != origin["preset_name"]:
        raise ContractError("Captured filament preset is not the explicit originating preset")
    return json.loads(canonical(value))


def machine_sha256_v2(value):
    """Bind the immutable Orca printer context used for physical review."""
    value = validate_context_v2(value)
    return digest({"printer": value["printer"], "nozzle_mm": value["nozzle_mm"]})


def validate_request_v2(value, now=None):
    exact(value, "schema request_id origin_id context_sha256 calibration parameters created_at expires_at", "V2 request")
    if value["schema"] != "helix-orca-v1-request/v2":
        raise ContractError("Unknown V2 request schema")
    hex_value(value["request_id"], 32)
    hex_value(value["origin_id"], 32)
    hex_value(value["context_sha256"])
    validate_parameters_v2(value["calibration"], value["parameters"])
    if type(value["created_at"]) is not int or type(value["expires_at"]) is not int:
        raise ContractError("Integer request timestamps required")
    current = time.time() if now is None else now
    if not value["created_at"] <= current < value["expires_at"] or not 1 <= value["expires_at"] - value["created_at"] <= 3600:
        raise ContractError("Stale or future V2 request")
    return json.loads(canonical(value))


def _artifact_v2(value):
    exact(value, "name size sha256", "V2 artifact")
    text(value["name"], "artifact name", 255)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*\.gcode", value["name"]) or ".." in value["name"]:
        raise ContractError("Unsafe artifact name")
    if type(value["size"]) is not int or not 0 < value["size"] <= 100_000_000:
        raise ContractError("Artifact size outside bounds")
    hex_value(value["sha256"])


def validate_warning_v2(value):
    exact(value, "level message error_code params known requires_ack", "V2 processor warning")
    if type(value["level"]) is not int or value["level"] < 0:
        raise ContractError("Warning level must be non-negative")
    text(value["message"], "warning message", 512)
    text(value["error_code"], "warning error code", 32)
    if not isinstance(value["params"], list) or len(value["params"]) > 32 or any(not isinstance(item, str) or len(item) > 512 for item in value["params"]):
        raise ContractError("Malformed warning parameters")
    known = KNOWN_WARNINGS_V2.get(value["error_code"]) == value["message"]
    if value["known"] is not known or type(value["requires_ack"]) is not bool or value["requires_ack"] is not known:
        raise ContractError("Warning classification does not match pinned Orca semantics")
    return json.loads(canonical(value))


def validate_build_qualification_v2(value):
    exact(value, "schema source_commit runtime platform distribution upstream adapter resources_sha256 routes evidence_sha256 qualified", "V2 build qualification")
    if value["schema"] != "helix-orca-v1-build-qualification/v2" or value["qualified"] is not True:
        raise ContractError("A qualified V2 build record is required")
    if value["source_commit"] != ORCA_SOURCE_V2 or value["runtime"] != ORCA_RUNTIME_V2:
        raise ContractError("Build qualification source/runtime differs")
    text(value["platform"], "qualified platform", 128)
    exact(value["distribution"], "archive_sha256 executable_sha256", "qualified distribution")
    if (value["distribution"]["archive_sha256"] != ORCA_ARCHIVE_SHA256_V2
            or value["distribution"]["executable_sha256"] != ORCA_EXECUTABLE_SHA256_V2):
        raise ContractError("Official Orca distribution digest differs")
    exact(value["upstream"], "run_id overall_conclusion sole_failed_job exact_jobs", "upstream build provenance")
    if (value["upstream"]["run_id"] != ORCA_UPSTREAM_RUN_V2
            or value["upstream"]["overall_conclusion"] != "failure"
            or value["upstream"]["sole_failed_job"] != "build_macos_arch (arm64) / Check Cache"
            or not isinstance(value["upstream"]["exact_jobs"], dict)
            or set(value["upstream"]["exact_jobs"]) != set(ORCA_UPSTREAM_JOBS_V2)):
        raise ContractError("Upstream run must retain its mixed conclusion and sole unrelated failure")
    for name, job in value["upstream"]["exact_jobs"].items():
        exact(job, "job_id conclusion", "upstream exact job")
        if job["job_id"] != ORCA_UPSTREAM_JOBS_V2[name] or job["conclusion"] != "success":
            raise ContractError("Required upstream exact job did not succeed: " + name)
    exact(value["adapter"], "sha256", "qualified adapter")
    for digest_value in (value["adapter"]["sha256"], value["resources_sha256"], value["evidence_sha256"]):
        hex_value(digest_value)
    if not isinstance(value["routes"], dict) or set(value["routes"]) != set(CALIBRATIONS):
        raise ContractError("Every calibration route needs build-level qualification")
    for calibration, route in value["routes"].items():
        exact(route, "qualified route_id case_count cases_sha256 coverage final_slice_path", "qualified route")
        if route["route_id"] not in V2_GENERATOR_ROUTES:
            raise ContractError("Unknown qualified generator route: " + calibration)
        coverage = route["coverage"]
        if not isinstance(coverage, list):
            raise ContractError("Route qualification coverage must be an explicit matrix")
        cells = []
        for case in coverage:
            exact(case, "context parameter_case case_sha256", "qualification matrix case")
            if (case["context"] not in V2_QUALIFICATION_CONTEXTS
                    or case["parameter_case"] not in V2_QUALIFICATION_PARAMETER_CASES):
                raise ContractError("Unknown route qualification coverage cell")
            hex_value(case["case_sha256"])
            cells.append((case["context"], case["parameter_case"]))
        required = {(context, parameter_case) for context in V2_QUALIFICATION_CONTEXTS
                    for parameter_case in V2_QUALIFICATION_PARAMETER_CASES}
        if len(cells) != len(required) or set(cells) != required:
            raise ContractError("Route qualification must cover Voron and AD5X default, non-default, and boundary cases")
        if (route["qualified"] is not True or type(route["case_count"]) is not int
                or route["case_count"] != len(coverage)):
            raise ContractError("Route is not build-qualified: " + calibration)
        hex_value(route["cases_sha256"])
        if route["cases_sha256"] != digest(coverage):
            raise ContractError("Route qualification case digest differs: " + calibration)
        if route["final_slice_path"] != ["Print.process", "Print.export_gcode"]:
            raise ContractError("Route does not use Orca's ordinary final slicing path")
    return json.loads(canonical(value))


def validate_prepared_v2(value, request):
    exact(value, "schema request_id origin_id context_sha256 request_sha256 calibration parameters artifact generator processing", "V2 prepared job")
    if value["schema"] != "helix-orca-v1-prepared/v2":
        raise ContractError("Unknown V2 prepared schema")
    request = validate_request_v2(request, now=request["created_at"])
    for key in ("request_id", "origin_id", "context_sha256", "calibration", "parameters"):
        if canonical(value[key]) != canonical(request[key]):
            raise ContractError("Prepared V2 job differs from request: " + key)
    if value["request_sha256"] != digest(request):
        raise ContractError("Prepared V2 request digest differs")
    _artifact_v2(value["artifact"])
    exact(value["generator"], "source_commit route executable_sha256 qualification_sha256 machine_sha256", "V2 generator")
    if value["generator"]["source_commit"] != ORCA_SOURCE_V2 or value["generator"]["executable_sha256"] != ORCA_EXECUTABLE_SHA256_V2:
        raise ContractError("Prepared V2 generator pin differs")
    if value["generator"]["route"] not in V2_GENERATOR_ROUTES:
        raise ContractError("Prepared V2 generator route is not qualified by this contract")
    hex_value(value["generator"]["qualification_sha256"])
    hex_value(value["generator"]["machine_sha256"])
    exact(value["processing"], "error_code warnings status", "V2 processing")
    if type(value["processing"]["error_code"]) is not int or value["processing"]["error_code"] < 0:
        raise ContractError("Invalid processor error mask")
    warnings = value["processing"]["warnings"]
    if not isinstance(warnings, list) or len(warnings) > 64:
        raise ContractError("Invalid processor warnings")
    warnings = [validate_warning_v2(item) for item in warnings]
    expected_status = "ready" if value["processing"]["error_code"] == 0 and all(item["known"] for item in warnings) else "blocked"
    if value["processing"]["status"] != expected_status:
        raise ContractError("Processor disposition differs from warnings/error mask")
    return json.loads(canonical(value))


def validate_warning_acknowledgement_v2(value, prepared):
    exact(value, "schema request_id prepared_sha256 warning_codes acknowledged_at", "V2 warning acknowledgement")
    if value["schema"] != "helix-orca-v1-warning-ack/v2" or value["request_id"] != prepared["request_id"] or value["prepared_sha256"] != digest(prepared):
        raise ContractError("Warning acknowledgement is unrelated to the prepared job")
    if type(value["acknowledged_at"]) is not int or value["acknowledged_at"] < 0:
        raise ContractError("Warning acknowledgement timestamp is invalid")
    expected = sorted(item["error_code"] for item in prepared["processing"]["warnings"] if item["requires_ack"])
    if value["warning_codes"] != expected:
        raise ContractError("Every structured warning must be acknowledged exactly once")
    return json.loads(canonical(value))


def validate_result_v2(value, request, prepared):
    exact(value, "schema request_id origin_id context_sha256 prepared_sha256 job_id completion_sha256 setting value", "V2 result")
    if value["schema"] != "helix-orca-v1-result/v2":
        raise ContractError("Unknown V2 result schema")
    for key in ("request_id", "origin_id", "context_sha256"):
        if value[key] != request[key]:
            raise ContractError("V2 result differs from request: " + key)
    if value["prepared_sha256"] != digest(prepared):
        raise ContractError("V2 result differs from prepared job")
    text(value["job_id"], "job identity")
    hex_value(value["completion_sha256"])
    if value["setting"] != SETTINGS[request["calibration"]] or type(value["value"]) not in (int, float) or not math.isfinite(value["value"]):
        raise ContractError("V2 result setting/value is invalid")
    return json.loads(canonical(value))
