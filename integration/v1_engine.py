#!/usr/bin/env python3
"""Pinned native-engine inventory. Source evidence never enables generation.

The C++ surfaces below exist in Orca; they are not Python or stock CLI APIs.
The audit command reads immutable git objects, never checks out or edits Orca.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
from pathlib import Path
from types import MappingProxyType

ORCA_SOURCE = "6a7763f08d1a175a464a00ce13f0b5a815662fc4"
SOURCE_HASHES = MappingProxyType({
    "src/libslic3r/Print.hpp": "45b1cef48808d496c7f75a78b23b39ad5cd29dca9259aa3b1920492cee5b118a",
    "src/libslic3r/calib.hpp": "3d993e153497669808075bcdc935e1666b18b840510da518fb6371cc7d064fd2",
    "src/libslic3r/calib.cpp": "ac5e19c8d8d5bd27fd13b576f28312ed91d39c0190b6d1f170a21bcea96d3aa4",
    "src/libslic3r/GCode.cpp": "4fc8b474911a30cded21cb4ad856f771ceba0c0f1d85b2aab9f93ef568aa37d7",
    "src/libslic3r/CMakeLists.txt": "02daa32753ad79d5ac98a13d237e74d0a71a8e2cc856427292bae4f1008a183f",
    "src/slic3r/GUI/Plater.cpp": "8290003e06b12b06a5c239e4d66269dfbc081895c5deb304f3a9b6dbddc8621a",
    "src/slic3r/GUI/calib_dlg.cpp": "cc845019c60fb763c61ba56d2edb09125b02a023350646394c6149106b497b0a",
    "src/slic3r/plugin/host/PluginHostSlicing.cpp": "ad415673ba92bce737bc398c663ff4b8fcd280cef4453a7dc6c5feb74d0a47bb",
    "src/slic3r/plugin/host/PluginHostApp.cpp": "cf3ca5345f7000a1160a79ec27665c7597694888601556da71c80a48a3af9ff6",
    "src/OrcaSlicer.cpp": "e0b238e7c29006d382cf88790277c3e508bb6dc6753313c0b252a71843ae3282",
    "CMakeLists.txt": "614005222dc2db9e1d221c9f14ca3a26ef76c31206a326d5fa6e3b922510b762",
})
# Mode numbers are deliberately omitted: only the pinned C++ enum may define them.
_ROUTES = MappingProxyType({
    "temperature": ("Calib_Temp_Tower", "model+transient-mode", "Plater.cpp:17311-17500",
                    "Native mesh cutting and set_calib_params; a separate qualified stock recipe may be used."),
    "flow_ratio_yolo": (None, "model+object-config", "Plater.cpp:17136-17300",
                        "Native YOLO asset and per-object configuration must be reproduced and compared."),
    "pressure_advance_pattern": ("Calib_PA_Pattern", "custom-path+model", "Plater.cpp:16808-17050",
                                   "Native CalibPressureAdvancePattern and per-plate custom G-code are required."),
    "retraction": ("Calib_Retraction_tower", "model+transient-mode", "GCode.cpp:6632-6640",
                   "Native software retract writer changes by height; a firmware command is insufficient."),
    "max_volumetric_speed": ("Calib_Vol_speed_Tower", "model+transient-mode", "GCode.cpp:6627-6631",
                             "Native outer-wall speed changes within extrusion planning; firmware scaling is insufficient."),
})


class NativeEngineBlocked(RuntimeError):
    """Native source/build/input/parity requirements are not satisfied."""
    def __init__(self, reason, code="native_engine"):
        self.code, self.reason = code, reason
        super().__init__(reason)


class NativeSourceError(ValueError):
    """Immutable native source could not be bound to the approved baseline."""


def capabilities(config=None):
    """Return fresh capability data, never a source-derived permission to execute."""
    backend, failure = None, "Native adapter is not built or qualified; a compatible audited build is required. "
    if not _compatible_host():
        failure = "Native x86_64 target is unavailable on this host; a compatible audited build is required. "
    if config:
        try:
            backend = _backend(config)
        except (NativeEngineBlocked, OSError, ValueError, KeyError, TypeError) as exc:
            failure = "Native build unavailable: " + str(exc) + ". "
    return [dict(id=name, available=bool(backend and name in backend["receipt"]["capabilities"]["routes"]),
                 source_commit=ORCA_SOURCE, route="native-engine", family=route[1], native_mode=route[0],
                 source=route[2], reason=("Built native route; independent parity is mandatory before Ready. "
                    if backend and name in backend["receipt"]["capabilities"]["routes"] else failure) + route[3])
            for name, route in _ROUTES.items()]


def require_native_generation(calibration, config=None):
    """Fail closed until a real native backend is integrated through qualification."""
    if type(calibration) is not str or calibration not in _ROUTES:
        raise NativeEngineBlocked("Unsupported calibration")
    if config:
        try:
            backend = _backend(config)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise NativeEngineBlocked("Complete native build configuration required: " + str(exc), "native_receipt") from exc
        if calibration in backend["receipt"]["capabilities"]["routes"]:
            return backend
    capability = next(item for item in capabilities() if item["id"] == calibration)
    raise NativeEngineBlocked(capability["reason"])


_OWNED_INPUTS = ("integration/v1-native-dependencies.json", "integration/v1-native-engine/main.cpp",
                 "integration/v1-native-engine/add-target.cmake", "integration/v1-native-engine/temperature_prepare.hpp",
                 "integration/v1-native-build-tools.py",
                 "scripts/v1-engine-native.py")
_NATIVE_ROUTES = {"temperature", "pressure_advance_pattern", "retraction", "max_volumetric_speed"}
_NATIVE_ASSETS = {"calib/temperature_tower/temperature_tower.drc", "calib/retraction/retraction_tower.drc",
                  "calib/volumetric_speed/SpeedTestStructure.drc"}
_ROOT = Path(__file__).resolve().parents[1]
_TARGET = {"system": "Linux", "architecture": "x86_64", "format": "ELF64-LE-EM_X86_64"}
_WINDOWS_TARGET = {"system": "Windows", "architecture": "x86_64", "format": "PE32+-LE-AMD64"}
_WINDOWS_OWNED_INPUTS = _OWNED_INPUTS + (
    "integration/v1-native-engine/windows-target.cmake",
    "integration/v1-native-engine/windows-cmake/FindEXPAT.cmake",
    "integration/v1_pe.py", "integration/v1-native-windows-dependencies.json",
    "scripts/v1-engine-windows.py", ".github/workflows/v1-windows-engine.yml")


def _host_target():
    if platform.machine().lower() in ("x86_64", "amd64"):
        return {"Linux": _TARGET, "Windows": _WINDOWS_TARGET}.get(platform.system())
    return None


def _compatible_host():
    return _host_target() is not None


def _windows_builder_valid(builder, receipt):
    if not isinstance(builder, dict):
        return False
    run_id, attempt = builder.get("run_id"), builder.get("run_attempt")
    commit, tools = builder.get("application_commit"), builder.get("toolchain")
    return (builder.get("schema") == "helix-orca-v1-windows-builder/v1"
        and builder.get("repository") == "bigstupid007/helix-orca-calibration"
        and builder.get("workflow") == ".github/workflows/v1-windows-engine.yml"
        and builder.get("runner_image") == "windows-2022"
        and isinstance(builder.get("image_version"), str) and 0 < len(builder["image_version"]) <= 128
        and isinstance(run_id, str) and run_id.isdecimal() and int(run_id) > 0
        and isinstance(attempt, str) and attempt.isdecimal() and int(attempt) > 0
        and builder.get("run_url") == "https://github.com/bigstupid007/helix-orca-calibration/actions/runs/" + run_id
        and isinstance(commit, str) and re.fullmatch(r"[0-9a-f]{40}", commit) is not None
        and receipt.get("application_commit") == commit and isinstance(tools, dict)
        and set(tools) == {"cl", "link", "cmake", "ninja", "perl", "msbuild"}
        and all(isinstance(row, dict) and type(row.get("size")) is int and row["size"] > 0
                and isinstance(row.get("sha256"), str) and re.fullmatch(r"[0-9a-f]{64}", row["sha256"])
                for row in tools.values()))


def _windows_closure(executable, receipt):
    from integration import v1_pe as pe
    files, closure = receipt.get("runtime_dlls"), receipt.get("import_closure")
    if (executable.suffix.lower() != ".exe" or not isinstance(files, dict) or len(files) > 128 or not isinstance(closure, dict)
            or set(closure) != {executable.name.lower(), *files}
            or any(not isinstance(name, str) or not pe.DLL_NAME.fullmatch(name) or pe.system_dll(name)
                   for name in files)
            or {path.name.lower() for path in executable.parent.iterdir() if path.suffix.lower() == ".dll"} != set(files)):
        raise NativeEngineBlocked("Exact isolated Windows DLL inventory required", "native_runtime")
    actual_system = set()
    try:
        for name in closure:
            path = executable if name == executable.name.lower() else _checked(
                {"path": str(executable.parent/name), "sha256": files[name]["sha256"]}, 256*1024**2)
            if name in files and path.stat().st_size != files[name].get("size"):
                raise ValueError("Runtime DLL size differs")
            actual = pe.inspect(path, dll=name in files)
            if actual != closure[name]:
                raise ValueError("Runtime PE imports differ")
            for imported in actual:
                if pe.system_dll(imported):
                    actual_system.add(imported)
                elif imported not in files:
                    raise ValueError("Unresolved non-system runtime DLL")
        reachable, pending = set(), [executable.name.lower()]
        while pending:
            name = pending.pop()
            if name not in reachable:
                reachable.add(name)
                pending.extend(item for item in closure[name] if item in files)
        if reachable != set(closure) or sorted(actual_system) != receipt.get("system_imports"):
            raise ValueError("Runtime/system import inventory differs")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise NativeEngineBlocked("Windows runtime import closure differs", "native_runtime") from exc


def _sha_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _checked(record, maximum):
    if not isinstance(record, dict) or set(record) != {"path", "sha256"}:
        raise NativeEngineBlocked("Exact path/SHA-256 record required", "native_pin")
    path = Path(record["path"])
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum:
        raise NativeEngineBlocked("Native input is missing, linked or oversized", "native_file")
    if _sha_file(path) != record["sha256"]:
        raise NativeEngineBlocked("Native pinned file digest differs", "native_digest")
    return path.resolve()


def _backend(config):
    """Trusted process configuration, never fields accepted from a UI request."""
    if not _compatible_host():
        raise NativeEngineBlocked("Native x86_64 target is unavailable on this host; a compatible audited build is required", "native_platform")
    receipt_path = _checked(config["build_receipt"], 1048576)
    inputs_path = _checked(config["build_inputs"], 1048576)
    receipt = json.loads(receipt_path.read_text())
    inputs = json.loads(inputs_path.read_text())
    if (receipt.get("schema") != "helix-orca-v1-native-build/v1" or receipt.get("built") is not True
            or receipt.get("qualified") is not False or receipt.get("source_commit") != ORCA_SOURCE
            or receipt.get("native_inputs_sha256") != _sha_file(inputs_path)):
        raise NativeEngineBlocked("Exact successful native build receipt required", "native_receipt")
    caps = receipt["capabilities"]
    target = _host_target()
    if receipt.get("target") != target or caps.get("target") != target:
        raise NativeEngineBlocked("Native backend requires an actual compatible audited build for this host", "native_platform")
    windows = target == _WINDOWS_TARGET
    source = inputs["source"]
    if (source.get("source_commit") != ORCA_SOURCE or source.get("source_verified") is not True
            or set(source.get("files", {})) != set(SOURCE_HASHES)
            or any(source["files"][name].get("sha256") != sha for name, sha in SOURCE_HASHES.items())
            or (not windows and inputs.get("builder_image") != "sha256:f67960f55aa1b7cfa8af41bd89943b13730b791ce55e1925bc575d5eef89f6d9")
            or (windows and not _windows_builder_valid(inputs.get("builder"), receipt))):
        raise NativeEngineBlocked("Native source/build provenance differs", "native_source")
    owned = _WINDOWS_OWNED_INPUTS if windows else _OWNED_INPUTS
    if set(inputs.get("owned_inputs", {})) != set(owned) or any(
            inputs["owned_inputs"][name] != _sha_file(_ROOT / name) for name in owned):
        raise NativeEngineBlocked("Native adapter source differs from its build", "native_adapter_source")
    executable = _checked(config["native_executable"], 2 * 1024**3)
    if (receipt["adapter"]["sha256"] != _sha_file(executable)
            or receipt["adapter"]["size"] != executable.stat().st_size or not os.access(executable, os.X_OK)):
        raise NativeEngineBlocked("Actual built executable differs", "native_executable")
    if windows:
        _windows_closure(executable, receipt)
    else:
        with executable.open("rb") as stream:
            header = stream.read(64)
        if (len(header) != 64 or header[:7] != b"\x7fELF\x02\x01\x01"
                or int.from_bytes(header[18:20], "little") != 62):
            raise NativeEngineBlocked("Native executable is not the recorded Linux x86_64 ELF64 target", "native_format")
    if caps.get("max_parallelism") != 2:
        raise NativeEngineBlocked("Native scheduler bound is unavailable", "native_scheduler")
    required = caps.get("required_effective_keys")
    if (caps.get("schema") != "helix-orca-v1-native-capabilities/v1" or caps.get("source_commit") != ORCA_SOURCE
            or set(caps.get("routes", [])) != _NATIVE_ROUTES or not isinstance(required, list)
            or len(required) < 100 or len(required) > 5000 or len(set(required)) != len(required)
            or any(not isinstance(key, str) or not key or len(key) > 128 for key in required)
            or not {"plugins", "post_process", "slicing_pipeline_plugin", "curr_bed_type", "nozzle_diameter"}.issubset(required)):
        raise NativeEngineBlocked("Actual native capability inventory is unavailable", "native_capabilities")
    resources = Path(config["native_resources"]).resolve()
    if set(receipt.get("resources", {})) != _NATIVE_ASSETS:
        raise NativeEngineBlocked("Native resource inventory differs", "native_resources")
    for name, sha in receipt["resources"].items():
        _checked({"path": str(resources / name), "sha256": sha}, 32 * 1024**2)
    return {"receipt": receipt, "executable": executable, "resources": resources,
            "receipt_sha256": _sha_file(receipt_path), "inputs_sha256": _sha_file(inputs_path)}



def _processing_failure(value):
    """Describe actual native rejection without trusting arbitrary diagnostic text.

    This cannot grant qualification: every warning and nonzero processor mask is
    fatal. Unknown codes remain fatal and retain their private native diagnostic.
    """
    if (not isinstance(value, dict) or type(value.get("error_code")) is not int
            or value["error_code"] < 0 or not isinstance(value.get("warnings"), list)
            or len(value["warnings"]) > 64):
        return None
    warnings = value["warnings"]
    for warning in warnings:
        if (not isinstance(warning, dict) or type(warning.get("level")) is not int
                or warning["level"] < 0 or not isinstance(warning.get("message"), str)
                or len(warning["message"]) > 512 or not isinstance(warning.get("error_code"), str)
                or not 1 <= len(warning["error_code"]) <= 32
                or any(char not in "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_-"
                       for char in warning["error_code"])):
            return None
    if value["error_code"]:
        return ("Orca rejected generated G-code with processor error mask "
                + str(value["error_code"]) + "; see retained native-processing.json.", "native_processing")
    if warnings:
        codes = ", ".join(dict.fromkeys(warning["error_code"] for warning in warnings))
        reason = "V1 preparation blocked by Orca warning " + codes + ". "
        if any(warning["error_code"] == "1000C001" for warning in warnings):
            reason += ("The commanded bed temperature meets or exceeds the retained filament's "
                       "vitrification temperature. This profile/input combination is unsupported by V1; "
                       "the original profile has not been changed.")
        else:
            reason += "This profile/input combination is unsupported by V1; see retained native-processing.json."
        return reason, "native_warning"
    return None


def _retained_processing_failure(destination):
    path = destination / "native-processing.json"
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 65536:
            return None
        return _processing_failure(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, UnicodeError):
        return None


def select_native_reference(config, inputs_sha256):
    """Select only an exact full-input key; never normalize or rebind context.

    This validates trusted catalog structure, not native evidence. The ordinary
    parity evaluator still verifies the selected manifest and native bytes.
    Call it after native processor validation so a missing catalog entry cannot
    hide an actual slicer warning.
    """
    if "native_references" not in config:
        return config.get("native_reference")  # Existing single-reference policy.
    if "native_reference" in config:
        raise NativeEngineBlocked("Choose either a native reference catalog or a single native reference, not both",
                                  "native_reference_catalog")
    catalog = config["native_references"]
    if not isinstance(catalog, dict) or len(catalog) > 64:
        raise NativeEngineBlocked("Native reference catalog must contain at most 64 exact-input entries",
                                  "native_reference_catalog")
    for key, reference in catalog.items():
        if not isinstance(key, str) or re.fullmatch(r"[0-9a-f]{64}", key) is None:
            raise NativeEngineBlocked("Native reference catalog requires full lowercase SHA-256 input keys",
                                      "native_reference_catalog")
        if not isinstance(reference, dict) or set(reference) != {"manifest", "gcode"}:
            raise NativeEngineBlocked("Native catalog entries require exactly pinned manifest and G-code records",
                                      "native_reference_catalog")
        for record in reference.values():
            if (not isinstance(record, dict) or set(record) != {"path", "sha256"}
                    or not isinstance(record["path"], str) or not 1 <= len(record["path"]) <= 4096
                    or not isinstance(record["sha256"], str)
                    or re.fullmatch(r"[0-9a-f]{64}", record["sha256"]) is None):
                raise NativeEngineBlocked("Native catalog files require exact bounded path/SHA-256 records",
                                          "native_reference_catalog")
    # Never choose the nearest parameter range, a different calibration, a
    # profile-only match, or a reference with a different origin/context hash.
    selected = catalog.get(inputs_sha256)
    return json.loads(json.dumps(selected)) if selected is not None else None


def generate(request, snapshot, output_dir, config):
    """Invoke our built C++ CLI and shared parity gate; never an Orca Python API."""
    from integration import v1_contract as contract
    from integration import v1_parity as parity
    request = contract.validate_request(request, now=config.get("now"))
    snapshot = contract.validate_context(snapshot)
    if request["context_sha256"] != contract.digest(snapshot) or request["origin_id"] != snapshot["origin_id"]:
        raise NativeEngineBlocked("Native request differs from immutable context", "context_mismatch")
    backend = require_native_generation(request["calibration"], config)
    if snapshot["runtime"] != {"version": "2.5.0-dev", "build": "6a7763f0"}:
        raise NativeEngineBlocked("Exact October 15 runtime context required", "runtime_pin")
    effective = snapshot["effective"]
    missing = set(backend["receipt"]["capabilities"]["required_effective_keys"]) - set(effective)
    if missing:
        raise NativeEngineBlocked("Effective native values unavailable: " + ", ".join(sorted(missing)[:10]), "effective_unavailable")
    for key in ("plugins", "post_process", "slicing_pipeline_plugin"):
        if effective[key] not in ("", '""'):
            raise NativeEngineBlocked("Native external processing unsupported: " + key, "external_processing")
    if effective.get("belt_printer") not in ("0", "false") or not effective.get("curr_bed_type"):
        raise NativeEngineBlocked("Explicit non-belt configuration and bed type required", "native_envelope")
    try:
        nozzle = float(effective["nozzle_diameter"])
    except (KeyError, ValueError, TypeError) as exc:
        raise NativeEngineBlocked("Effective single nozzle unavailable", "native_envelope") from exc
    if nozzle != snapshot["nozzle_mm"]:
        raise NativeEngineBlocked("Effective nozzle differs from context", "native_envelope")
    if request["calibration"] == "pressure_advance_pattern" and effective.get("gcode_flavor") != "klipper":
        raise NativeEngineBlocked("Native PA requires retained Klipper flavor", "native_vendor_unavailable")
    destination = Path(output_dir)
    if destination.is_symlink() or (destination.exists() and any(destination.iterdir())):
        raise NativeEngineBlocked("Native generation requires a new empty job directory", "output_exists")
    destination.mkdir(mode=0o700, parents=True, exist_ok=True)
    destination = destination.resolve()
    (destination / "request.json").write_bytes(contract.canonical(request))
    (destination / "context.json").write_bytes(contract.canonical(snapshot))
    inputs = parity.generation_inputs(request, snapshot, ORCA_SOURCE)
    (destination / "inputs.json").write_bytes(contract.canonical(inputs))
    argv = [str(backend["executable"]), str(destination / "request.json"),
            str(destination / "context.json"), str(backend["resources"]), str(destination)]
    (destination / "invocation.json").write_bytes(contract.canonical({"argv": argv,
        "source_commit": ORCA_SOURCE, "executable_sha256": backend["receipt"]["adapter"]["sha256"],
        "build_receipt_sha256": backend["receipt_sha256"], "build_inputs_sha256": backend["inputs_sha256"]}))
    artifact = destination / "native-calibration.gcode"
    def retain_unqualified(reason):
        if artifact.is_file() and not artifact.is_symlink():
            try:
                disposition = parity.unqualified(artifact, inputs, reason)
                (destination / "parity.json").write_bytes(contract.canonical(disposition))
            except (OSError, ValueError) as exc:
                (destination / "native-parity-blocker.json").write_bytes(contract.canonical({
                    "qualified": False, "reason": str(exc), "native_failure": reason,
                    "request_sha256": contract.digest(request), "source_commit": ORCA_SOURCE}))
    runner = config.get("runner")
    if runner:
        code = runner(argv, destination)
    else:
        environment = os.environ.copy()
        environment.update({key: str(destination / key.lower()) for key in
                            ("XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME")})
        environment.update(OMP_NUM_THREADS="2", TBB_NUM_THREADS="2")
        with (destination / "native.log").open("wb") as log:
            try:
                result = subprocess.run(argv, cwd=destination, stdin=subprocess.DEVNULL,
                    stdout=log, stderr=subprocess.STDOUT, timeout=min(config.get("timeout_seconds", 180), 300),
                    env=environment, check=False)
            except subprocess.TimeoutExpired as exc:
                retain_unqualified("Native generation exceeded its deadline; any retained G-code is incomplete and unqualified.")
                raise NativeEngineBlocked("Native generation exceeded its deadline", "native_timeout") from exc
        code = result.returncode
    if code != 0:
        retain_unqualified("Native generation or post-export validation failed; retained artifact is unqualified.")
        failure = _retained_processing_failure(destination)
        if failure:
            reason, code = failure
            (destination / "native-blocker.json").write_bytes(contract.canonical({
                "schema": "helix-orca-v1-native-blocker/v1", "request_sha256": contract.digest(request),
                "code": code, "reason": reason, "qualified": False, "not_applied": True}))
            raise NativeEngineBlocked(reason, code)
        raise NativeEngineBlocked("Native generation failed; retained native.log has diagnostics", "native_failed")
    if artifact.is_symlink() or list(destination.glob("*.gcode")) != [artifact]:
        raise NativeEngineBlocked("Expected exactly one native artifact", "native_artifact")
    record = parity.file_record(artifact)
    retain_unqualified("Native artifact exists but its exact request/result/processor validation has not passed.")
    native_path = destination / "native-generation.json"
    if native_path.is_symlink() or native_path.stat().st_size > 1048576:
        raise NativeEngineBlocked("Bounded native result required", "native_result")
    native = json.loads(native_path.read_text())
    if (native.get("source_commit") != ORCA_SOURCE or native.get("calibration") != request["calibration"]
            or native.get("parameters") != request["parameters"] or native.get("request_id") != request["request_id"]
            or native.get("origin_id") != request["origin_id"] or native.get("context_sha256") != request["context_sha256"]
            or native.get("artifact") != artifact.name or native.get("size") != record["size"]
            or native.get("qualified") is not False or native.get("not_applied") is not True
            or native.get("processing") != {"error_code": 0, "warnings": []} or native.get("max_parallelism") != 2):
        raise NativeEngineBlocked("Native result does not bind exact request and artifact", "native_result")
    reference = select_native_reference(config, contract.digest(inputs))
    if "native_references" in config:
        (destination / "native-reference-selection.json").write_bytes(contract.canonical({
            "schema": "helix-orca-v1-native-reference-selection/v1",
            "method": "exact-full-input-sha256", "inputs_sha256": contract.digest(inputs),
            "catalog_entries": len(config["native_references"]), "matched": reference is not None,
            "reference": reference, "qualified": False}))
    if reference:
        try:
            manifest = json.loads(_checked(reference["manifest"], 1048576).read_text())
            report = parity.evaluate(artifact, _checked(reference["gcode"], parity.MAX_GCODE_BYTES), manifest, inputs)
        except (NativeEngineBlocked, OSError, ValueError, KeyError, TypeError) as exc:
            report = parity.unqualified(artifact, inputs, "Independent native reference unavailable: " + str(exc))
    else:
        reason = ("No native catalog entry matches the exact context and selected parameters; "
                  "the original values were preserved. A fresh origin is a different exact context."
                  if "native_references" in config else
                  "No independent native UI reference with matching exact inputs has been retained.")
        report = parity.unqualified(artifact, inputs, reason)
    (destination / "parity.json").write_bytes(contract.canonical(report))
    prepared = {key: request[key] for key in ("request_id", "origin_id", "context_sha256", "calibration", "parameters")}
    prepared.update(schema="helix-orca-v1-prepared/v1", request_sha256=contract.digest(request),
        artifact=record, generator={"build": ORCA_SOURCE, "route": "native-engine-v1"},
        parity={"qualified": report["qualified"], "report_sha256": contract.digest(report), "reason": report["reason"]},
        not_applied=True)
    prepared = contract.validate_prepared(prepared, request)
    (destination / "prepared.json").write_bytes(contract.canonical(prepared))
    return prepared


def verify_source_bytes(sources):
    """Check complete exact bytes, including non-interface native setup logic."""
    if set(sources) != set(SOURCE_HASHES):
        raise NativeSourceError("Native source inventory is incomplete or has unknown files")
    files = {}
    for name, expected in SOURCE_HASHES.items():
        value = sources[name]
        if not isinstance(value, bytes):
            raise NativeSourceError("Native source must be exact bytes: " + name)
        actual = hashlib.sha256(value).hexdigest()
        if actual != expected:
            raise NativeSourceError("Approved October 15 source mismatch: " + name)
        files[name] = {"size": len(value), "sha256": actual}
    return dict(schema="helix-orca-v1-native-source/v1", source_commit=ORCA_SOURCE,
                source_verified=True, executable_built=False, qualified=False, files=files,
                capabilities=capabilities())


def audit_git_source(repository):
    """Developer audit only; bounded immutable reads, no branch/index mutation."""
    sources = {}
    for name in SOURCE_HASHES:
        try:
            result = subprocess.run(
                ["git", "--no-replace-objects", "-C", str(Path(repository).resolve()),
                 "show", ORCA_SOURCE + ":" + name],
                check=True, capture_output=True, timeout=20,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise NativeSourceError("Cannot read approved native source: " + name) from exc
        sources[name] = result.stdout
    return verify_source_bytes(sources)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("capabilities")
    audit = sub.add_parser("audit-source")
    audit.add_argument("--repository", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "audit-source":
        try:
            value = audit_git_source(args.repository)
        except NativeSourceError as exc:
            parser.exit(2, str(exc) + "\n")
    else:
        value = capabilities()
    print(json.dumps(value, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
