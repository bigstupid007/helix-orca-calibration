#!/usr/bin/env python3
"""Build and verify the current V2 generator qualification matrix.

The public evidence is sanitized: exact contexts, configured paths, G-code and
native diagnostics remain below ``private/`` or at their operator-owned source
paths.  Qualification is Windows-only and always invokes
``integration.v1_routing.generate``.  A Python caller may inject a case runner
only with ``test_only=True``; that path is permanently ineligible to emit the
final ``helix-orca-v1-build-qualification/v2`` record.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import sys
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integration import v1_contract as contract
from integration import v1_routing as routing

CONFIG_SCHEMA = "helix-orca-v1-build-qualification-config/v2"
EVIDENCE_SCHEMA = "helix-orca-v1-build-qualification-evidence/v2"
CASE_SCHEMA = "helix-orca-v1-build-qualification-case/v2"
PROVENANCE_SCHEMA = "helix-orca-v1-build-qualification-private-provenance/v2"
PLATFORM_LABEL = ("Windows x86_64 official nightly b5e9cb3c; upstream run "
                  "40220020944 has mixed conclusion (sole unrelated macOS arm64 cache failure)")
ROUTE_IDS = {"stock-cli": "stock-cli-recipe-v2", "native-engine": "native-engine-v2"}
ADAPTER_SOURCES = (
    "integration/v1_contract.py",
    "integration/v1_routing.py",
    "integration/v1_generation.py",
    "integration/v1_engine.py",
    "integration/v1_qualification.py",
    "integration/v1-native-engine/main.cpp",
    "scripts/v1-build-qualify.py",
)
REQUIRED_CELLS = {(context_name, calibration, parameter_case)
                  for context_name in contract.V2_QUALIFICATION_CONTEXTS
                  for calibration in contract.CALIBRATIONS
                  for parameter_case in contract.V2_QUALIFICATION_PARAMETER_CASES}


class QualificationError(ValueError):
    pass


def _canonical(value):
    return contract.canonical(value)


def _digest(value):
    return contract.digest(value)


def _sha_file(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise QualificationError("Qualification input must be a regular non-link file: " + str(path))
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def _nonlink_path(path_value, label, *, must_exist=True) -> Path:
    raw = Path(path_value).absolute()
    for candidate in (raw, *raw.parents):
        if candidate.is_symlink():
            raise QualificationError(label + " must not use a symlink path")
    try:
        return raw.resolve(strict=must_exist)
    except (OSError, RuntimeError) as exc:
        raise QualificationError(label + " path cannot be resolved safely") from exc


def _write(path: Path, value) -> None:
    path = Path(path).absolute()
    for candidate in (path, *path.parents):
        if candidate.is_symlink():
            raise QualificationError("Qualification output must not use a symlink path")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    for candidate in (path, *path.parents):
        if candidate.is_symlink():
            raise QualificationError("Qualification output must not use a symlink path")
    if path.exists():
        raise QualificationError("Refusing to replace qualification evidence: " + str(path))
    path.write_bytes(_canonical(value))


def _read(path: Path):
    path = _nonlink_path(path, "JSON evidence")
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 16 * 1024 * 1024:
        raise QualificationError("Missing, linked or oversized JSON evidence: " + str(path))
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError) as exc:
        raise QualificationError("Malformed JSON evidence: " + str(path)) from exc
    return value


def _exact(value, fields, label):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise QualificationError("Malformed " + label)


def _not_fixture_digest(value: str, label: str) -> str:
    try:
        contract.hex_value(value)
    except contract.ContractError as exc:
        raise QualificationError("Invalid " + label + " digest") from exc
    if len(set(value)) == 1:
        raise QualificationError("Synthetic fixture digest is forbidden for " + label)
    return value


def _record(label: str, path_value, expected=None) -> dict:
    if not isinstance(label, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,255}", label):
        raise QualificationError("Invalid inventory label")
    path = _nonlink_path(path_value, "Inventory file " + label)
    sha = _sha_file(path)
    if expected is not None and sha != expected:
        raise QualificationError("Pinned file digest differs: " + label)
    if path.stat().st_size <= 0 or path.stat().st_size > 2 * 1024**3:
        raise QualificationError("Inventory file size is outside qualification bounds: " + label)
    return {"label": label, "path": str(path), "sha256": sha, "size": path.stat().st_size}


def _public_inventory(records: list[dict]) -> list[dict]:
    # Operator labels and paths stay private.  Stable ordinal IDs are safe
    # because callers sort the private inventory by label before projection.
    return [{"id": "file-%03d" % index, "sha256": item["sha256"], "size": item["size"]}
            for index, item in enumerate(records, 1)]


def _validate_pe_x64(path: Path) -> None:
    if path.suffix.lower() != ".exe":
        raise QualificationError("Official Orca executable must be a Windows .exe")
    try:
        with path.open("rb") as stream:
            header = stream.read(64)
            if len(header) != 64 or header[:2] != b"MZ":
                raise QualificationError("Official Orca executable is not PE")
            offset = int.from_bytes(header[60:64], "little")
            if offset < 64 or offset > 16 * 1024 * 1024:
                raise QualificationError("Official Orca PE header offset is invalid")
            stream.seek(offset)
            pe = stream.read(6)
        if pe[:4] != b"PE\0\0" or int.from_bytes(pe[4:6], "little") != 0x8664:
            raise QualificationError("Official Orca executable is not Windows x86_64 PE")
    except OSError as exc:
        raise QualificationError("Could not inspect official Orca executable") from exc


def _windows_x64() -> bool:
    return platform.system() == "Windows" and platform.machine().lower() in ("amd64", "x86_64")


def _deep_merge(base, overlay):
    if not isinstance(overlay, dict):
        return copy.deepcopy(overlay)
    result = copy.deepcopy(base) if isinstance(base, dict) else {}
    for key, value in overlay.items():
        result[key] = _deep_merge(result.get(key), value) if isinstance(value, dict) else copy.deepcopy(value)
    return result


def parameters_for(context, calibration: str, parameter_case: str) -> dict:
    defaults = contract.default_parameters_v2(context)[calibration]
    if parameter_case == "default":
        value = defaults
    elif calibration == "temperature":
        value = ({"start": 245, "end": 205, "step": 5, "scale": True}
                 if parameter_case == "non_default_range" else
                 {"start": 230, "end": 190, "step": 5, "scale": False}
                 if parameter_case == "non_default_step" else
                 {"start": 160, "end": 155, "step": 5, "scale": True}
                 if parameter_case == "lower_boundary" else
                 {"start": 500, "end": 495, "step": 5, "scale": True})
    elif calibration == "flow_ratio_yolo":
        # Four native combinations are exhaustive.  Five semantic cells are
        # retained by explicitly repeating the minimum combination at the
        # lower boundary; the cell itself, request and receipt remain unique.
        value = ({"pass": 2, "pattern": "archimedean_chords"}
                 if parameter_case == "non_default_range" else
                 {"pass": 1, "pattern": "monotonic"}
                 if parameter_case == "non_default_step" else
                 {"pass": 1, "pattern": "archimedean_chords"}
                 if parameter_case == "lower_boundary" else
                 {"pass": 2, "pattern": "monotonic"})
    elif calibration == "pressure_advance_pattern":
        value = ({"start": .01, "end": .12, "step": .005, "accelerations": [], "speeds": []}
                 if parameter_case == "non_default_range" else
                 {"start": defaults["start"], "end": defaults["end"], "step": defaults["step"] * 2,
                  "accelerations": [1000, 2000], "speeds": [40, 80]}
                 if parameter_case == "non_default_step" else
                 {"start": 0, "end": .001, "step": .001, "accelerations": [], "speeds": []}
                 if parameter_case == "lower_boundary" else
                 {"start": 1.9, "end": 2, "step": .1, "accelerations": [], "speeds": []})
    elif calibration == "retraction":
        # Pinned Orca exposes no finite product maximum for Retraction or MVS.
        # Their "upper_boundary" cells are the high edge of this program's
        # deliberately bounded qualification domain, not a claim about Orca's
        # absolute accepted maximum.
        value = ({"start": .5, "end": 3, "step": .1}
                 if parameter_case == "non_default_range" else
                 {"start": 0, "end": 2, "step": .2}
                 if parameter_case == "non_default_step" else
                 {"start": 0, "end": .001, "step": .001}
                 if parameter_case == "lower_boundary" else
                 {"start": 19, "end": 20, "step": 1})
    else:
        value = ({"start": 10, "end": 30, "step": .5}
                 if parameter_case == "non_default_range" else
                 {"start": 5, "end": 20, "step": 1}
                 if parameter_case == "non_default_step" else
                 {"start": .01, "end": .011, "step": .001}
                 if parameter_case == "lower_boundary" else
                 {"start": 199, "end": 200, "step": 1})
    return contract.validate_parameters_v2(calibration, value)


class OneShotAuthorizer:
    def __init__(self, intent):
        self.intent = json.loads(_canonical(intent))
        self.consumed = False

    def __call__(self, intent):
        if self.consumed:
            raise QualificationError("Qualification intent was already consumed")
        if _canonical(intent) != _canonical(self.intent):
            raise QualificationError("Qualification authorizer received a different case")
        self.consumed = True
        return {
            "schema": contract.V2_QUALIFICATION_AUTHORIZATION_SCHEMA,
            "intent_sha256": _digest(intent),
            "case_id": intent["case_id"],
            "request_sha256": intent["request_sha256"],
            "context_sha256": intent["context_sha256"],
            "machine_sha256": intent["machine_sha256"],
            "route_id": intent["route_id"],
            "output_sha256": intent["output_sha256"],
            "adapter_sha256": intent["adapter_sha256"],
            "resources_sha256": intent["resources_sha256"],
            "consumed": True,
            "generation_only": True,
        }


def _upstream():
    return {
        "run_id": contract.ORCA_UPSTREAM_RUN_V2,
        "overall_conclusion": "failure",
        "sole_failed_job": "build_macos_arch (arm64) / Check Cache",
        "exact_jobs": {name: {"job_id": job_id, "conclusion": "success"}
                       for name, job_id in contract.ORCA_UPSTREAM_JOBS_V2.items()},
    }


def _load_config(path: Path, test_only: bool):
    value = _read(path)
    _exact(value, {"schema", "generator", "case_overrides", "official_archive",
                   "adapter_files", "resource_files"}, "qualification configuration")
    if value["schema"] != CONFIG_SCHEMA or not isinstance(value["generator"], dict):
        raise QualificationError("Unknown qualification configuration")
    if not isinstance(value["case_overrides"], dict):
        raise QualificationError("Case overrides must be an object")
    for key in ("adapter_files", "resource_files"):
        if not isinstance(value[key], list):
            raise QualificationError(key + " must be a list")
    _exact(value["official_archive"], {"path", "sha256"}, "official archive record")
    if not test_only and value["official_archive"]["sha256"] != contract.ORCA_ARCHIVE_SHA256_V2:
        raise QualificationError("Official Orca archive digest pin differs")
    return value


def _configured_records(values, category):
    records = []
    for index, item in enumerate(values):
        _exact(item, {"label", "path", "sha256"}, category + " record")
        if not isinstance(item["sha256"], str):
            raise QualificationError("Invalid configured digest")
        records.append(_record(item["label"], item["path"], item["sha256"]))
    if len({item["label"] for item in records}) != len(records):
        raise QualificationError("Duplicate " + category + " inventory label")
    return records


def _inventories(config, test_only):
    adapter = []
    for relative in ADAPTER_SOURCES:
        adapter.append(_record(relative, ROOT / relative))
    adapter.extend(_configured_records(config["adapter_files"], "adapter"))
    resources = _configured_records(config["resource_files"], "resource")
    adapter.sort(key=lambda item: item["label"])
    resources.sort(key=lambda item: item["label"])
    if not test_only and not resources:
        raise QualificationError("Exact generator resources must be explicitly inventoried")
    for category, records in (("adapter", adapter), ("resource", resources)):
        if len({item["label"] for item in records}) != len(records):
            raise QualificationError("Duplicate " + category + " inventory label")
        for item in records:
            if not test_only:
                _not_fixture_digest(item["sha256"], item["label"])
    public_adapter = _public_inventory(adapter)
    public_resources = _public_inventory(resources)
    return (adapter, resources, _digest(public_adapter), _digest(public_resources))


def _configured_path_records(value):
    result = []
    if isinstance(value, dict):
        if (set(("path", "sha256")).issubset(value) and isinstance(value["path"], str)
                and isinstance(value["sha256"], str)):
            result.append((str(Path(value["path"]).resolve()), value["sha256"]))
        for child in value.values():
            result.extend(_configured_path_records(child))
    elif isinstance(value, list):
        for child in value:
            result.extend(_configured_path_records(child))
    return result


def _assert_generator_files_inventoried(config, adapter, resources, archive, executable):
    allowed = {(item["path"], item["sha256"]) for item in adapter + resources + [archive, executable]}
    for item in _configured_path_records({"generator": config["generator"],
                                          "case_overrides": config["case_overrides"]}):
        if item not in allowed:
            raise QualificationError("Configured generator file is absent from adapter/resource inventory")
    resource_roots = []
    def find_roots(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "native_resources" and isinstance(child, str):
                    resource_roots.append(Path(child).resolve())
                else:
                    find_roots(child)
        elif isinstance(value, list):
            for child in value:
                find_roots(child)
    find_roots({"generator": config["generator"], "case_overrides": config["case_overrides"]})
    resource_files = {(item["path"], item["sha256"]) for item in resources}
    for root in resource_roots:
        if root.is_symlink() or not root.is_dir():
            raise QualificationError("Native resource root must be a non-link directory")
        files = sorted(path for path in root.rglob("*") if path.is_file())
        if not files or len(files) > 512:
            raise QualificationError("Native resource root inventory is empty or oversized")
        for path in files:
            if path.is_symlink() or (str(path.resolve()), _sha_file(path)) not in resource_files:
                raise QualificationError("Native resource file is absent from exact resource inventory")


def _context(path: Path):
    try:
        return contract.validate_context_v2(_read(path))
    except contract.ContractError as exc:
        raise QualificationError("Invalid exact V2 context: " + str(path)) from exc


def _override(config, context_name, calibration, parameter_case):
    current = config["case_overrides"]
    for key in (context_name, calibration, parameter_case):
        if not isinstance(current, dict):
            return {}
        current = current.get(key, {})
    if not isinstance(current, dict):
        raise QualificationError("Case override must be an object")
    return current


def _retained_record(case_dir: Path, labels: list[str]):
    records = []
    for label in labels:
        path = case_dir / label
        record = _record(label, path)
        records.append({key: record[key] for key in ("label", "sha256", "size")})
    return records


def _case_receipt(context_name, parameter_case, request, context, intent, prepared,
                  case_dir, adapter_sha, resources_sha, epoch, acknowledged_codes):
    if prepared["processing"]["status"] != "ready" or prepared["processing"]["error_code"] != 0:
        raise QualificationError("Only processor-ready case receipts can qualify")
    warnings = prepared["processing"]["warnings"]
    codes = sorted(item["error_code"] for item in warnings)
    if any(item["known"] is not True or item["requires_ack"] is not True for item in warnings):
        raise QualificationError("Unknown or non-acknowledgeable warning cannot qualify")
    if set(codes) - acknowledged_codes:
        raise QualificationError("Known warning was not explicitly acknowledged: " + ",".join(codes))
    ack_sha = None
    labels = ["qualification-request.json", "qualification-context.json",
              "qualification-intent.json", "qualification-authorization.json",
              "prepared.json", "invocation.json", "inputs.json", prepared["artifact"]["name"]]
    if codes:
        acknowledgement = contract.validate_warning_acknowledgement_v2({
            "schema": "helix-orca-v1-warning-ack/v2", "request_id": request["request_id"],
            "prepared_sha256": _digest(prepared), "warning_codes": codes,
            "acknowledged_at": epoch,
        }, prepared)
        _write(case_dir / "qualification-warning-ack.json", acknowledgement)
        labels.append("qualification-warning-ack.json")
        ack_sha = _digest(acknowledgement)
    if prepared["generator"]["route"] == "native-engine-v2":
        labels.extend(["native-processing.json", "native-generation.json",
                       "native-validation-warnings.json", "native-slicing-warnings.json"])
    result_path = case_dir / "result.json"
    if result_path.is_file():
        labels.append("result.json")
    retained = _retained_record(case_dir, labels)
    authorization = _read(case_dir / "qualification-authorization.json")
    return {
        "schema": CASE_SCHEMA,
        "case_id": intent["case_id"],
        "context": context_name,
        "parameter_case": parameter_case,
        "calibration": request["calibration"],
        "context_sha256": _digest(context),
        "machine_sha256": contract.machine_sha256_v2(context),
        "parameters_sha256": _digest(request["parameters"]),
        "request_sha256": _digest(request),
        "intent_sha256": _digest(intent),
        "authorization_sha256": _digest(authorization),
        "prepared_sha256": _digest(prepared),
        "artifact": {key: prepared["artifact"][key] for key in ("size", "sha256")},
        "processing_sha256": _digest(prepared["processing"]),
        "warning_codes": codes,
        "warning_ack_sha256": ack_sha,
        "route_id": prepared["generator"]["route"],
        "source_commit": prepared["generator"]["source_commit"],
        "executable_sha256": prepared["generator"]["executable_sha256"],
        "adapter_sha256": adapter_sha,
        "resources_sha256": resources_sha,
        "final_slice_path": contract.V2_FINAL_SLICE_PATH,
        "retained_files": retained,
    }


def _build_record(manifest):
    routes = {}
    for calibration in contract.CALIBRATIONS:
        selected = [item for item in manifest["cases"] if item["calibration"] == calibration]
        route_ids = {item["route_id"] for item in selected}
        if len(route_ids) != 1:
            raise QualificationError("One exact route is required per calibration")
        coverage = [{"context": item["context"], "parameter_case": item["parameter_case"],
                     "case_sha256": _digest(item)} for item in selected]
        coverage.sort(key=lambda item: (contract.V2_QUALIFICATION_CONTEXTS.index(item["context"]),
                                        contract.V2_QUALIFICATION_PARAMETER_CASES.index(item["parameter_case"])))
        routes[calibration] = {
            "qualified": True, "route_id": next(iter(route_ids)), "case_count": len(coverage),
            "cases_sha256": _digest(coverage), "coverage": coverage,
            "final_slice_path": contract.V2_FINAL_SLICE_PATH,
        }
    value = {
        "schema": "helix-orca-v1-build-qualification/v2",
        "source_commit": contract.ORCA_SOURCE_V2,
        "runtime": contract.ORCA_RUNTIME_V2,
        "platform": PLATFORM_LABEL,
        "distribution": {"archive_sha256": contract.ORCA_ARCHIVE_SHA256_V2,
                         "executable_sha256": contract.ORCA_EXECUTABLE_SHA256_V2},
        "upstream": _upstream(),
        "adapter": {"sha256": manifest["adapter"]["sha256"]},
        "resources_sha256": manifest["resources"]["sha256"],
        "routes": routes,
        "evidence_sha256": _digest(manifest),
        "qualified": True,
    }
    return contract.validate_build_qualification_v2(value)


def qualify(voron_context: Path, ad5x_context: Path, config_path: Path, output: Path,
            *, epoch: int, acknowledged_codes=frozenset(), case_runner: Callable | None = None,
            test_only: bool = False):
    """Run the matrix. Injected runners are structurally unable to emit final qualification."""
    if case_runner is not None and not test_only:
        raise QualificationError("Injected case runners are test-only")
    if not test_only and not _windows_x64():
        raise QualificationError("Actual build qualification requires native Windows x86_64")
    if type(epoch) is not int or epoch < 0:
        raise QualificationError("A non-negative deterministic qualification epoch is required")
    output = _nonlink_path(output, "Qualification output", must_exist=False)
    if output.exists() and any(output.iterdir()):
        raise QualificationError("Qualification output must be a new empty directory")
    output.mkdir(mode=0o700, parents=True, exist_ok=True)
    private = output / "private"
    private.mkdir(mode=0o700)
    config = _load_config(config_path, test_only)
    contexts = {"voron": _context(voron_context), "ad5x": _context(ad5x_context)}
    if (_digest(contexts["voron"]) == _digest(contexts["ad5x"])
            or contract.machine_sha256_v2(contexts["voron"]) == contract.machine_sha256_v2(contexts["ad5x"])):
        raise QualificationError("Voron and AD5X contexts/machines must be independently supplied and distinct")
    for name, value in contexts.items():
        _write(private / "contexts" / (name + ".json"), value)
    adapter, resources, adapter_sha, resources_sha = _inventories(config, test_only)
    archive = _record("official-orca-archive", config["official_archive"]["path"],
                      None if test_only else contract.ORCA_ARCHIVE_SHA256_V2)
    generator = copy.deepcopy(config["generator"])
    executable_expected = None if test_only else contract.ORCA_EXECUTABLE_SHA256_V2
    executable_record = _record("official-orca-executable", generator.get("executable", ""),
                                executable_expected)
    _assert_generator_files_inventoried(config, adapter, resources, archive, executable_record)
    if not test_only:
        _validate_pe_x64(Path(executable_record["path"]))
        if generator.get("executable_sha256") != contract.ORCA_EXECUTABLE_SHA256_V2:
            raise QualificationError("Production generator is not pinned to the official executable")
        for value, label in ((adapter_sha, "adapter"), (resources_sha, "resources")):
            _not_fixture_digest(value, label)
    runner = case_runner or routing.generate
    receipts = []
    plan = []
    for context_name in contract.V2_QUALIFICATION_CONTEXTS:
        context_value = contexts[context_name]
        for calibration in contract.CALIBRATIONS:
            for parameter_case in contract.V2_QUALIFICATION_PARAMETER_CASES:
                parameters = parameters_for(context_value, calibration, parameter_case)
                case_seed = {"context": context_name, "context_sha256": _digest(context_value),
                             "calibration": calibration, "parameter_case": parameter_case,
                             "parameters_sha256": _digest(parameters), "adapter_sha256": adapter_sha,
                             "resources_sha256": resources_sha}
                case_id = _digest(case_seed)
                request = contract.validate_request_v2({
                    "schema": "helix-orca-v1-request/v2", "request_id": case_id[:32],
                    "origin_id": context_value["origin_id"], "context_sha256": _digest(context_value),
                    "calibration": calibration, "parameters": parameters,
                    "created_at": epoch, "expires_at": epoch + 3600,
                }, now=epoch)
                case_dir = private / "jobs" / context_name / calibration / parameter_case
                case_config = _deep_merge(generator, _override(config, context_name, calibration, parameter_case))
                selected = routing.routes(case_config)[calibration]
                route_id = ROUTE_IDS[selected]
                intent = {
                    "schema": contract.V2_QUALIFICATION_INTENT_SCHEMA, "case_id": case_id,
                    "source_commit": contract.ORCA_SOURCE_V2, "runtime": contract.ORCA_RUNTIME_V2,
                    "executable_sha256": contract.ORCA_EXECUTABLE_SHA256_V2,
                    "adapter_sha256": adapter_sha, "resources_sha256": resources_sha,
                    "context_sha256": _digest(context_value),
                    "machine_sha256": contract.machine_sha256_v2(context_value),
                    "request_sha256": _digest(request), "calibration": calibration,
                    "parameters_sha256": _digest(parameters), "route_id": route_id,
                    "output_sha256": contract._output_sha256_v2(case_dir),
                    "final_slice_path": contract.V2_FINAL_SLICE_PATH,
                    "generation_only": True, "one_shot": True,
                }
                intent = contract.validate_qualification_intent_v2(
                    intent, request, context_value, route_id, case_dir)
                gate = OneShotAuthorizer(intent)
                case_config.update(now=epoch, qualification_intent=intent,
                                   qualification_authorizer=gate)
                plan.append({"case_id": case_id, "context": context_name,
                             "calibration": calibration, "parameter_case": parameter_case,
                             "intent_sha256": _digest(intent)})
                try:
                    prepared = runner(request, context_value, case_dir, case_config)
                except Exception as exc:
                    raise QualificationError("Generation failed for " + "/".join(
                        (context_name, calibration, parameter_case)) + ": " + str(exc)) from exc
                if not gate.consumed:
                    raise QualificationError("Production route did not consume its one-shot intent")
                try:
                    prepared = contract.validate_prepared_v2(prepared, request)
                except contract.ContractError as exc:
                    raise QualificationError("Production route returned an invalid prepared receipt") from exc
                if (prepared["generator"]["route"] != route_id
                        or prepared["generator"]["source_commit"] != contract.ORCA_SOURCE_V2
                        or prepared["generator"]["executable_sha256"] != contract.ORCA_EXECUTABLE_SHA256_V2
                        or prepared["generator"]["qualification_sha256"] != _digest(intent)
                        or prepared["generator"]["machine_sha256"] != contract.machine_sha256_v2(context_value)):
                    raise QualificationError("Prepared receipt differs from exact qualification intent")
                if _read(case_dir / "prepared.json") != prepared:
                    raise QualificationError("Returned and retained prepared receipts differ")
                _write(case_dir / "qualification-request.json", request)
                _write(case_dir / "qualification-context.json", context_value)
                _write(case_dir / "qualification-intent.json", intent)
                receipt = _case_receipt(context_name, parameter_case, request, context_value,
                                        intent, prepared, case_dir, adapter_sha, resources_sha,
                                        epoch, set(acknowledged_codes))
                receipts.append(receipt)
    receipts.sort(key=lambda item: (contract.CALIBRATIONS.index(item["calibration"]),
                                    contract.V2_QUALIFICATION_CONTEXTS.index(item["context"]),
                                    contract.V2_QUALIFICATION_PARAMETER_CASES.index(item["parameter_case"])))
    actual_distribution = {"archive_sha256": archive["sha256"],
                           "executable_sha256": executable_record["sha256"]}
    manifest = {
        "schema": EVIDENCE_SCHEMA, "source_commit": contract.ORCA_SOURCE_V2,
        "runtime": contract.ORCA_RUNTIME_V2,
        "platform": PLATFORM_LABEL if not test_only else "TEST-ONLY injected runner; not qualification",
        "distribution": actual_distribution, "upstream": _upstream(),
        "execution": {"runner": "production-v1-routing.generate" if not test_only else "injected-test-runner",
                      "actual_windows_x86_64": not test_only, "test_only": test_only},
        "adapter": {"sha256": adapter_sha, "files": _public_inventory(adapter)},
        "resources": {"sha256": resources_sha, "files": _public_inventory(resources)},
        "contexts": [{"context": name, "context_sha256": _digest(contexts[name]),
                      "machine_sha256": contract.machine_sha256_v2(contexts[name])}
                     for name in contract.V2_QUALIFICATION_CONTEXTS],
        "case_plan_sha256": _digest(plan), "cases": receipts,
        "final_slice_path": contract.V2_FINAL_SLICE_PATH,
        "qualified": not test_only,
    }
    provenance = {
        "schema": PROVENANCE_SCHEMA, "epoch": epoch,
        "acknowledged_warning_codes": sorted(set(acknowledged_codes)),
        "official_archive": archive, "official_executable": executable_record,
        "adapter_files": adapter, "resource_files": resources,
        "config_path": str(config_path.resolve()), "test_only": test_only,
    }
    _write(private / "provenance.json", provenance)
    _write(output / ("test-evidence.json" if test_only else "evidence.json"), manifest)
    if test_only:
        verify_evidence(output, allow_test=True)
        return manifest, None
    record = _build_record(manifest)
    if record["evidence_sha256"] != _digest(manifest):
        raise QualificationError("Final record is not bound to evidence")
    _write(output / "build-qualification.json", record)
    verify_evidence(output)
    return manifest, record


def _verify_inventory(public, private, label, allow_test):
    if _public_inventory(private) != public["files"] or _digest(public["files"]) != public["sha256"]:
        raise QualificationError(label + " public/private inventory differs")
    for item in private:
        current = _record(item["label"], item["path"], item["sha256"])
        if current != item:
            raise QualificationError(label + " inventory file changed")
        if not allow_test:
            _not_fixture_digest(item["sha256"], label + "/" + item["label"])


def verify_evidence(output: Path, *, allow_test=False):
    output = _nonlink_path(output, "Qualification output")
    evidence_path = output / ("test-evidence.json" if allow_test else "evidence.json")
    manifest = _read(evidence_path)
    provenance = _read(output / "private/provenance.json")
    _exact(manifest, {"schema", "source_commit", "runtime", "platform", "distribution", "upstream",
                      "execution", "adapter", "resources", "contexts", "case_plan_sha256", "cases",
                      "final_slice_path", "qualified"}, "qualification evidence")
    _exact(provenance, {"schema", "epoch", "acknowledged_warning_codes", "official_archive",
                        "official_executable", "adapter_files", "resource_files", "config_path",
                        "test_only"}, "private provenance")
    is_test = manifest["execution"] == {"runner": "injected-test-runner",
                                        "actual_windows_x86_64": False, "test_only": True}
    if allow_test:
        if not is_test or manifest["qualified"] is not False or provenance["test_only"] is not True:
            raise QualificationError("Only explicitly ineligible injected-runner evidence is test-verifiable")
        if (output / "build-qualification.json").exists():
            raise QualificationError("Test-only evidence must never emit a final qualification record")
    else:
        if (manifest["execution"] != {"runner": "production-v1-routing.generate",
                                      "actual_windows_x86_64": True, "test_only": False}
                or manifest["qualified"] is not True or provenance["test_only"] is not False
                or not _windows_x64()):
            raise QualificationError("Final qualification verification requires actual Windows production execution")
    if (manifest["schema"] != EVIDENCE_SCHEMA or provenance["schema"] != PROVENANCE_SCHEMA
            or manifest["source_commit"] != contract.ORCA_SOURCE_V2
            or manifest["runtime"] != contract.ORCA_RUNTIME_V2
            or manifest["upstream"] != _upstream()
            or manifest["final_slice_path"] != contract.V2_FINAL_SLICE_PATH):
        raise QualificationError("Qualification pin, upstream conclusion or final slice path differs")
    _verify_inventory(manifest["adapter"], provenance["adapter_files"], "adapter", allow_test)
    _verify_inventory(manifest["resources"], provenance["resource_files"], "resources", allow_test)
    archive = provenance["official_archive"]
    executable = provenance["official_executable"]
    if _record(archive["label"], archive["path"], archive["sha256"]) != archive:
        raise QualificationError("Official archive changed")
    if _record(executable["label"], executable["path"], executable["sha256"]) != executable:
        raise QualificationError("Official executable changed")
    if manifest["distribution"] != {"archive_sha256": archive["sha256"],
                                     "executable_sha256": executable["sha256"]}:
        raise QualificationError("Distribution evidence differs from retained files")
    if not allow_test:
        if (archive["sha256"] != contract.ORCA_ARCHIVE_SHA256_V2
                or executable["sha256"] != contract.ORCA_EXECUTABLE_SHA256_V2):
            raise QualificationError("Official Orca distribution digest differs")
        _validate_pe_x64(Path(executable["path"]))
    contexts = {}
    if [item.get("context") for item in manifest["contexts"]] != list(contract.V2_QUALIFICATION_CONTEXTS):
        raise QualificationError("Context summaries are not in deterministic matrix order")
    for item in manifest["contexts"]:
        _exact(item, {"context", "context_sha256", "machine_sha256"}, "context summary")
        if item["context"] in contexts or item["context"] not in contract.V2_QUALIFICATION_CONTEXTS:
            raise QualificationError("Duplicate or unknown context summary")
        value = _context(output / "private/contexts" / (item["context"] + ".json"))
        if item["context_sha256"] != _digest(value) or item["machine_sha256"] != contract.machine_sha256_v2(value):
            raise QualificationError("Private context or machine hash changed")
        contexts[item["context"]] = value
    if set(contexts) != set(contract.V2_QUALIFICATION_CONTEXTS):
        raise QualificationError("Both exact contexts are required")
    if contract.machine_sha256_v2(contexts["voron"]) == contract.machine_sha256_v2(contexts["ad5x"]):
        raise QualificationError("Voron and AD5X machine contexts are not independent")
    cells, case_ids, case_hashes = set(), set(), set()
    verified_plan = {}
    by_calibration = {name: [] for name in contract.CALIBRATIONS}
    for receipt in manifest["cases"]:
        _exact(receipt, {"schema", "case_id", "context", "parameter_case", "calibration",
                         "context_sha256", "machine_sha256", "parameters_sha256", "request_sha256",
                         "intent_sha256", "authorization_sha256", "prepared_sha256", "artifact",
                         "processing_sha256", "warning_codes", "warning_ack_sha256", "route_id",
                         "source_commit", "executable_sha256", "adapter_sha256", "resources_sha256",
                         "final_slice_path", "retained_files"}, "case receipt")
        cell = (receipt["context"], receipt["calibration"], receipt["parameter_case"])
        receipt_sha = _digest(receipt)
        if (receipt["schema"] != CASE_SCHEMA or cell in cells or receipt["case_id"] in case_ids
                or receipt_sha in case_hashes):
            raise QualificationError("Duplicate or malformed qualification cell")
        cells.add(cell); case_ids.add(receipt["case_id"]); case_hashes.add(receipt_sha)
        if cell not in REQUIRED_CELLS:
            raise QualificationError("Unknown qualification cell")
        context_value = contexts[receipt["context"]]
        case_dir = output / "private/jobs" / receipt["context"] / receipt["calibration"] / receipt["parameter_case"]
        request = contract.validate_request_v2(_read(case_dir / "qualification-request.json"),
                                               now=provenance["epoch"])
        expected_parameters = parameters_for(context_value, receipt["calibration"], receipt["parameter_case"])
        expected_case_id = _digest({
            "context": receipt["context"], "context_sha256": _digest(context_value),
            "calibration": receipt["calibration"], "parameter_case": receipt["parameter_case"],
            "parameters_sha256": _digest(expected_parameters),
            "adapter_sha256": manifest["adapter"]["sha256"],
            "resources_sha256": manifest["resources"]["sha256"],
        })
        if (request["parameters"] != expected_parameters or receipt["parameters_sha256"] != _digest(expected_parameters)
                or receipt["request_sha256"] != _digest(request)
                or receipt["case_id"] != expected_case_id or request["request_id"] != expected_case_id[:32]
                or request["context_sha256"] != _digest(context_value)
                or receipt["context_sha256"] != _digest(context_value)
                or receipt["machine_sha256"] != contract.machine_sha256_v2(context_value)):
            raise QualificationError("Qualification case input/context binding changed")
        intent = contract.validate_qualification_intent_v2(
            _read(case_dir / "qualification-intent.json"), request, context_value,
            receipt["route_id"], case_dir)
        if (intent["adapter_sha256"] != manifest["adapter"]["sha256"]
                or intent["resources_sha256"] != manifest["resources"]["sha256"]):
            raise QualificationError("Qualification intent adapter/resources binding changed")
        verified_plan[cell] = {"case_id": expected_case_id, "context": receipt["context"],
                               "calibration": receipt["calibration"],
                               "parameter_case": receipt["parameter_case"],
                               "intent_sha256": _digest(intent)}
        authorization = _read(case_dir / "qualification-authorization.json")
        gate = OneShotAuthorizer(intent)
        expected_authorization = gate(intent)
        if (authorization != expected_authorization or receipt["intent_sha256"] != _digest(intent)
                or receipt["authorization_sha256"] != _digest(authorization)):
            raise QualificationError("One-shot qualification authorization receipt changed")
        prepared = contract.validate_prepared_v2(_read(case_dir / "prepared.json"), request)
        artifact = case_dir / prepared["artifact"]["name"]
        artifact_record = _record(prepared["artifact"]["name"], artifact, prepared["artifact"]["sha256"])
        if (prepared["artifact"]["size"] != artifact_record["size"]
                or receipt["artifact"] != {"size": artifact_record["size"], "sha256": artifact_record["sha256"]}
                or receipt["prepared_sha256"] != _digest(prepared)
                or receipt["processing_sha256"] != _digest(prepared["processing"])
                or prepared["generator"]["qualification_sha256"] != _digest(intent)
                or prepared["generator"]["route"] != receipt["route_id"]
                or prepared["generator"]["machine_sha256"] != receipt["machine_sha256"]
                or prepared["generator"]["source_commit"] != contract.ORCA_SOURCE_V2
                or prepared["generator"]["executable_sha256"] != contract.ORCA_EXECUTABLE_SHA256_V2
                or receipt["source_commit"] != prepared["generator"]["source_commit"]
                or receipt["executable_sha256"] != prepared["generator"]["executable_sha256"]):
            raise QualificationError("Prepared/artifact/route/machine binding changed")
        if (receipt["adapter_sha256"] != manifest["adapter"]["sha256"]
                or receipt["resources_sha256"] != manifest["resources"]["sha256"]
                or receipt["final_slice_path"] != contract.V2_FINAL_SLICE_PATH):
            raise QualificationError("Case adapter/resources/final path differs")
        warnings = prepared["processing"]["warnings"]
        codes = sorted(item["error_code"] for item in warnings)
        if (prepared["processing"]["status"] != "ready" or prepared["processing"]["error_code"] != 0
                or any(item["known"] is not True or item["requires_ack"] is not True for item in warnings)
                or codes != receipt["warning_codes"]
                or set(codes) - set(provenance["acknowledged_warning_codes"])):
            raise QualificationError("Warning disposition is not explicitly known and acknowledged")
        ack_path = case_dir / "qualification-warning-ack.json"
        if codes:
            ack = contract.validate_warning_acknowledgement_v2(_read(ack_path), prepared)
            if receipt["warning_ack_sha256"] != _digest(ack):
                raise QualificationError("Warning acknowledgement changed")
        elif receipt["warning_ack_sha256"] is not None or ack_path.exists():
            raise QualificationError("Unexpected warning acknowledgement")
        retained = []
        for item in receipt["retained_files"]:
            _exact(item, {"label", "sha256", "size"}, "retained file")
            if "/" in item["label"] or "\\" in item["label"] or item["label"] in (".", ".."):
                raise QualificationError("Unsafe retained file label")
            current = _record(item["label"], case_dir / item["label"], item["sha256"])
            retained.append({key: current[key] for key in ("label", "sha256", "size")})
        if retained != receipt["retained_files"] or len({item["label"] for item in retained}) != len(retained):
            raise QualificationError("Retained case files changed or duplicate")
        by_calibration[receipt["calibration"]].append(receipt)
    if cells != REQUIRED_CELLS or len(manifest["cases"]) != len(REQUIRED_CELLS):
        raise QualificationError("Qualification matrix is partial")
    expected_receipt_order = [(calibration, context_name, parameter_case)
                              for calibration in contract.CALIBRATIONS
                              for context_name in contract.V2_QUALIFICATION_CONTEXTS
                              for parameter_case in contract.V2_QUALIFICATION_PARAMETER_CASES]
    actual_receipt_order = [(item["calibration"], item["context"], item["parameter_case"])
                            for item in manifest["cases"]]
    if actual_receipt_order != expected_receipt_order:
        raise QualificationError("Case receipts are not in deterministic matrix order")
    plan = [verified_plan[(context_name, calibration, parameter_case)]
            for context_name in contract.V2_QUALIFICATION_CONTEXTS
            for calibration in contract.CALIBRATIONS
            for parameter_case in contract.V2_QUALIFICATION_PARAMETER_CASES]
    if manifest["case_plan_sha256"] != _digest(plan):
        raise QualificationError("Qualification case plan changed")
    if not allow_test:
        record = contract.validate_build_qualification_v2(_read(output / "build-qualification.json"))
        expected_record = _build_record(manifest)
        if record != expected_record or record["evidence_sha256"] != _digest(manifest):
            raise QualificationError("Final build qualification differs from actual case receipts")
        # A provisional prepared receipt is deliberately ineligible at runtime.
        final_sha = _digest(record)
        if any(item["intent_sha256"] == final_sha for item in manifest["cases"]):
            raise QualificationError("Qualification intent was confused with final runtime qualification")
    return manifest


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("qualify")
    run.add_argument("--voron-context", type=Path, required=True)
    run.add_argument("--ad5x-context", type=Path, required=True)
    run.add_argument("--config", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--epoch", type=int, required=True)
    run.add_argument("--ack-known-warning", action="append", default=[])
    verify = sub.add_parser("verify-only")
    verify.add_argument("--output", type=Path, required=True)
    return parser


def main(argv=None):
    args = _parser().parse_args(argv)
    try:
        if args.command == "qualify":
            unknown = set(args.ack_known_warning) - set(contract.KNOWN_WARNINGS_V2)
            if unknown:
                raise QualificationError("Cannot pre-acknowledge unknown warning codes: " + ",".join(sorted(unknown)))
            qualify(args.voron_context, args.ad5x_context, args.config, args.output,
                    epoch=args.epoch, acknowledged_codes=frozenset(args.ack_known_warning))
            print("PASS: exact Windows V2 build qualification verified at " + str(args.output))
        else:
            verify_evidence(args.output)
            print("PASS: retained exact Windows V2 build qualification verified")
        return 0
    except (QualificationError, contract.ContractError, OSError, ValueError, KeyError, TypeError) as exc:
        print("FAIL: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
