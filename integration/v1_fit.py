"""Printer-neutral, fail-closed beta.12 file-fit validation.

The pure limit and finding rules intentionally track HelixScreen
``v1.1.0-beta.12`` / HelixPrint ``1.4.0`` (feature ``file_analysis`` v1).
Unlike HelixPrint's optional slicer-upload hold, this module never fails open:
an owned physical Start needs a current analysis record and complete limits.

Source reference:
``moonraker-plugin/helix_fitcheck.py`` at
``00a9fe6030c37d56748b2122b41fd36de1fdf831``.
"""
from __future__ import annotations

import math
import re
from typing import Any

from integration.v1_contract import ContractError, digest, exact, hex_value, text


HELIXSCREEN_COMMIT = "00a9fe6030c37d56748b2122b41fd36de1fdf831"
HELIXPRINT_VERSION = "1.4.0"
FILE_ANALYSIS_SCHEMA = 1
FIT_CHECK_VERSION = 1
LIMIT_EPSILON = 1e-4
NOZZLE_TOLERANCE = 0.005
AXES = ("x", "y", "z")
_EXTRUDER = re.compile(r"^extruder(\d*)$")
_TOOL_MACRO = re.compile(r"^gcode_macro t(\d+)$")


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def _section(settings: dict[str, Any], name: str) -> dict[str, Any] | None:
    value = settings.get(name)
    return value if isinstance(value, dict) else None


def _option(section: dict[str, Any] | None, key: str,
            default: float | None = None) -> float | None:
    if section is None:
        return None
    return default if key not in section else _number(section[key])


def machine_limits(settings: Any) -> dict[str, Any]:
    """Read the same generic Klipper limits as beta.12's fit checker."""
    settings = settings if isinstance(settings, dict) else {}
    printer = _section(settings, "printer") or {}
    kinematics = printer.get("kinematics")
    kinematics = kinematics.lower() if isinstance(kinematics, str) else ""
    axis_min: list[float | None] = [None, None, None]
    axis_max: list[float | None] = [None, None, None]
    radius = None
    if kinematics == "delta":
        radius = _number(printer.get("print_radius"))
        if radius is None:
            radius = _number(printer.get("delta_radius"))
        axis_min[2] = _option(printer, "minimum_z_position", 0.0)
        stops = [_option(_section(settings, "stepper_" + name), "position_endstop")
                 for name in ("a", "b", "c")]
        known = [value for value in stops if value is not None]
        axis_max[2] = min(known) if known else None
    else:
        for index, axis in enumerate(AXES):
            stepper = _section(settings, "stepper_" + axis)
            axis_min[index] = _option(stepper, "position_min", 0.0)
            axis_max[index] = _option(stepper, "position_max")
        carriage = _section(settings, "dual_carriage")
        if carriage is not None:
            axis = carriage.get("axis", "x")
            index = AXES.index(axis) if axis in ("x", "y") else None
            low = _option(carriage, "position_min", 0.0)
            high = _option(carriage, "position_max")
            if index is not None:
                if low is not None and axis_min[index] is not None:
                    axis_min[index] = min(axis_min[index], low)
                if high is not None and axis_max[index] is not None:
                    axis_max[index] = max(axis_max[index], high)

    extruders: list[tuple[int, dict[str, Any]]] = []
    tool_macros: list[int] = []
    for name, section in settings.items():
        match = _EXTRUDER.match(name)
        if match and isinstance(section, dict):
            extruders.append((int(match.group(1) or 0), section))
            continue
        match = _TOOL_MACRO.match(name)
        if match:
            tool_macros.append(int(match.group(1)))
    extruders.sort(key=lambda item: item[0])
    maximums = [value for value in (_number(section.get("max_temp"))
                for _index, section in extruders) if value is not None]
    nozzles = [value for value in (_number(section.get("nozzle_diameter"))
               for _index, section in extruders) if value is not None]
    tool_count = max(len(extruders), max(tool_macros) + 1 if tool_macros else 0)
    return {
        "kinematics": kinematics,
        "axis_min": axis_min,
        "axis_max": axis_max,
        "print_radius": radius,
        "max_extruder_temp": max(maximums) if maximums else None,
        "max_bed_temp": _option(_section(settings, "heater_bed"), "max_temp"),
        "tool_count": tool_count or None,
        "tool_count_confirmed": bool(extruders) and len(extruders) >= tool_count,
        "nozzle_diameters": nozzles,
        "model": "",
    }


def require_machine_limits(machine: dict[str, Any]) -> dict[str, Any]:
    """Require enough live limits to authorize a physical calibration."""
    if machine.get("kinematics") == "delta":
        complete_motion = (machine.get("print_radius") is not None
                           and machine.get("axis_min", [None] * 3)[2] is not None
                           and machine.get("axis_max", [None] * 3)[2] is not None)
    else:
        complete_motion = (all(value is not None for value in machine.get("axis_min", []))
                           and all(value is not None for value in machine.get("axis_max", []))
                           and len(machine.get("axis_min", [])) == 3
                           and len(machine.get("axis_max", [])) == 3)
    if (not complete_motion or machine.get("max_extruder_temp") is None
            or not machine.get("nozzle_diameters") or machine.get("tool_count") is None):
        raise ContractError("Complete live printer fit limits are unavailable")
    return machine


def validate_helix_status(value: Any, qualification: dict[str, Any]) -> None:
    """Pin the live beta.12 HelixPrint analysis contract, not its fail-open hold."""
    if not isinstance(value, dict) or value.get("enabled") is not True or value.get("api") != 2:
        raise ContractError("HelixPrint status/API is unavailable")
    if value.get("version") != qualification["helixprint_version"]:
        raise ContractError("HelixPrint version differs from target qualification")
    feature = value.get("features", {}).get("file_analysis")
    if (not isinstance(feature, dict) or feature.get("version") != qualification["file_analysis_schema"]
            or feature.get("available") is not True or feature.get("enabled") is not True
            or feature.get("reason") is not None):
        raise ContractError("HelixPrint file_analysis v1 is not ready")


def analysis_record(reply: Any, filename: str, metadata: Any) -> dict[str, Any]:
    """Return a current exact-file record or fail closed.

    HelixPrint records bind filename/size/mtime, not content. The caller must
    bracket this check with exact remote SHA-256 byte readbacks.
    """
    if not isinstance(reply, dict):
        raise ContractError("HelixPrint analysis reply is unavailable")
    if reply.get("filename") != filename:
        raise ContractError("HelixPrint analysis reply names a different file")
    status = reply.get("status")
    if status != "ready":
        if status in ("pending", "failed", "disabled"):
            raise ContractError("HelixPrint analysis is " + status)
        raise ContractError("HelixPrint analysis status is invalid")
    record = reply.get("analysis")
    if not isinstance(record, dict) or record.get("schema") != FILE_ANALYSIS_SCHEMA:
        raise ContractError("HelixPrint analysis schema differs")
    if record.get("filename") != filename:
        raise ContractError("HelixPrint analysis names a different file")
    size = record.get("file_size")
    modified = _number(record.get("file_mtime"))
    if (type(size) is not int or not 0 < size <= 100_000_000 or modified is None
            or not isinstance(metadata, dict) or metadata.get("size") != size
            or _number(metadata.get("modified")) != modified):
        raise ContractError("HelixPrint analysis is not current for exact remote metadata")
    return record


def fit_file(record: Any) -> dict[str, Any]:
    record = record if isinstance(record, dict) else {}
    bounds = record.get("bounds") if isinstance(record.get("bounds"), dict) else {}
    header = record.get("header") if isinstance(record.get("header"), dict) else {}
    tools = [item.get("tool") for item in record.get("tools") or [] if isinstance(item, dict)]
    return {
        "print": bounds.get("print"),
        "travel": bounds.get("travel"),
        "max_hotend_temp": bounds.get("max_hotend_temp"),
        "max_bed_temp": bounds.get("max_bed_temp"),
        "tools": sorted(tool for tool in tools if isinstance(tool, int) and not isinstance(tool, bool)),
        "nozzle_diameters": list(header.get("nozzle_diameters") or []),
        "printer_model": header.get("printer_model"),
    }


def _box_axis(box: Any, end: str, index: int) -> float | None:
    if not isinstance(box, dict):
        return None
    values = box.get(end)
    return _number(values[index]) if isinstance(values, list) and len(values) > index else None


def _usable_box(box: Any) -> bool:
    return (isinstance(box, dict) and isinstance(box.get("min"), list)
            and isinstance(box.get("max"), list))


def _model_key(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return "".join(character for character in value.lower()
                   if character.isascii() and character.isalnum())


def _finding(kind: str, severity: str, **detail: Any) -> dict[str, Any]:
    return {"kind": kind, "severity": severity, "detail": detail}


def check_fit(machine: dict[str, Any], facts: dict[str, Any]) -> list[dict[str, Any]]:
    """Beta.12-compatible generic findings, in its deterministic order."""
    findings: list[dict[str, Any]] = []
    box = facts.get("travel") if _usable_box(facts.get("travel")) else facts.get("print")
    if not _usable_box(box):
        raise ContractError("Full analyzed file motion bounds are unavailable")
    axis_min = machine.get("axis_min") or [None, None, None]
    axis_max = machine.get("axis_max") or [None, None, None]
    for index, axis in enumerate(AXES):
        low, lower = _box_axis(box, "min", index), _number(axis_min[index])
        if low is not None and lower is not None and low < lower - LIMIT_EPSILON:
            findings.append(_finding("out_of_bounds", "block", axis=axis, side="min", value=low, limit=lower))
        high, upper = _box_axis(box, "max", index), _number(axis_max[index])
        if high is not None and upper is not None and high > upper + LIMIT_EPSILON:
            findings.append(_finding("out_of_bounds", "block", axis=axis, side="max", value=high, limit=upper))
    radius = _number(machine.get("print_radius"))
    if radius is not None:
        edges = [abs(value) for value in (_box_axis(box, end, index)
                 for end in ("min", "max") for index in (0, 1)) if value is not None]
        reach = max(edges) if edges else None
        if reach is not None and reach > radius + LIMIT_EPSILON:
            findings.append(_finding("out_of_bounds", "block", axis="radius", side="max", value=reach, limit=radius))
    for heater, file_key, machine_key in (("extruder", "max_hotend_temp", "max_extruder_temp"),
                                           ("heater_bed", "max_bed_temp", "max_bed_temp")):
        value, limit = _number(facts.get(file_key)), _number(machine.get(machine_key))
        if value is not None and limit is None and value > 0:
            raise ContractError("Live " + heater + " maximum is unavailable")
        if value is not None and limit is not None and value > limit + LIMIT_EPSILON:
            findings.append(_finding("temp_over_max", "block", heater=heater, value=value, limit=limit))
    count = machine.get("tool_count")
    tools = [tool for tool in facts.get("tools") or [] if isinstance(tool, int) and not isinstance(tool, bool)]
    if isinstance(count, int) and not isinstance(count, bool) and tools and max(tools) >= count:
        findings.append(_finding("too_many_tools", "block" if machine.get("tool_count_confirmed") is True else "warn",
                                 tool=max(tools), limit=count))
    file_nozzles = facts.get("nozzle_diameters") or []
    machine_nozzles = machine.get("nozzle_diameters") or []
    for tool in range(min(len(file_nozzles), len(machine_nozzles))):
        want, have = _number(file_nozzles[tool]), _number(machine_nozzles[tool])
        if want is not None and have is not None and abs(want - have) > NOZZLE_TOLERANCE:
            findings.append(_finding("nozzle_mismatch", "warn", tool=tool, file=want, printer=have))
    file_model, machine_model = facts.get("printer_model"), machine.get("model")
    left, right = _model_key(file_model), _model_key(machine_model)
    if left and right and left not in right and right not in left:
        findings.append(_finding("printer_model_mismatch", "note", file=file_model, printer=machine_model))
    return findings


def warning_binding(findings: Any, *, target_id: str, request_id: str,
                    prepared_sha256: str, file_sha256: str) -> dict[str, Any]:
    """Bind the exact warning decision to this target, job and candidate."""
    if not isinstance(findings, list):
        raise ContractError("File-fit findings are unavailable")
    kinds = sorted({item.get("kind") for item in findings
                    if isinstance(item, dict) and item.get("severity") == "warn"
                    and isinstance(item.get("kind"), str)})
    return {
        "target_id": text(target_id, "printer target ID", 128),
        "request_id": hex_value(request_id, 32),
        "prepared_sha256": hex_value(prepared_sha256),
        "file_sha256": hex_value(file_sha256),
        "findings_sha256": digest(findings),
        "warning_kinds": kinds,
    }


def authorize_findings(findings: Any, acknowledgement: Any = None, *,
                       binding: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Blocks always fail; warnings need an exact versioned acknowledgement.

    Existing v1 intents cannot carry this record, so their no-ack path remains
    fail-closed. A newer native-contract adapter may supply the exact record
    without changing target or fit-check semantics.
    """
    if not isinstance(findings, list):
        raise ContractError("File-fit findings are unavailable")
    blocks = [item for item in findings if item.get("severity") == "block"]
    if blocks:
        raise ContractError("Printer-neutral fit check refused Start: "
                            + ", ".join(item.get("kind", "unknown") for item in blocks))
    warnings = [item for item in findings if item.get("severity") == "warn"]
    if not warnings:
        if acknowledgement is not None:
            raise ContractError("Fit-warning acknowledgement supplied without warnings")
        return findings
    if not isinstance(binding, dict):
        raise ContractError("Printer-neutral fit warnings require exact acknowledgement")
    exact(binding, "target_id request_id prepared_sha256 file_sha256 findings_sha256 warning_kinds",
          "fit-warning binding")
    expected = dict(binding, schema="helix-orca-v1-fit-warning-ack/v1",
                    action="acknowledge-fit-warnings")
    if acknowledgement != expected:
        raise ContractError("Printer-neutral fit warnings require exact acknowledgement")
    return findings
