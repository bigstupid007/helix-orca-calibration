#!/usr/bin/env python3
"""Pinned native-engine inventory. Source evidence never enables generation.

The C++ surfaces below exist in Orca; they are not Python or stock CLI APIs.
The audit command reads immutable git objects, never checks out or edits Orca.
"""
from __future__ import annotations

import argparse
import hashlib
import json
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
    """No built/qualified native executable exists for the requested operation."""


class NativeSourceError(ValueError):
    """Immutable native source could not be bound to the approved baseline."""


def capabilities():
    """Return fresh capability data, never a source-derived permission to execute."""
    return [dict(id=name, available=False, source_commit=ORCA_SOURCE,
                 route="native-engine", family=route[1], native_mode=route[0],
                 source=route[2], reason="Native adapter is not built or qualified. " + route[3])
            for name, route in _ROUTES.items()]


def require_native_generation(calibration):
    """Fail closed until a real native backend is integrated through qualification."""
    if type(calibration) is not str or calibration not in _ROUTES:
        raise NativeEngineBlocked("Unsupported calibration")
    capability = next(item for item in capabilities() if item["id"] == calibration)
    raise NativeEngineBlocked(capability["reason"])


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
