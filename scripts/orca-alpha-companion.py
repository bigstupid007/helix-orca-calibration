#!/usr/bin/env python3
"""Generate the identity-only Orca 2.5.0-alpha communication companion."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
COMPANION_GENERATOR = ROOT / "scripts/temperature-communication-companion.py"
COMPANION_GENERATOR_SHA256 = "a70db750354e427c0b433fa1534dd1bd9c9e497a4bba6574de6b728b2e766064"
ACCEPTED_COMPANION_SHA256 = "bc3d35eb260a1360e1095bd97d8e7d31e3ab96e8b3cafde1f145e3adf5b4d71f"
ALPHA_VERSION = "2.5.0-alpha"
ALPHA_BUILD = "3880f2c5"


class AlphaCompanionGenerationError(RuntimeError):
    pass


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _accepted_source() -> str:
    if sha256_bytes(COMPANION_GENERATOR.read_bytes()) != COMPANION_GENERATOR_SHA256:
        raise AlphaCompanionGenerationError("accepted communication companion generator changed")
    spec = importlib.util.spec_from_file_location("accepted_communication_companion", COMPANION_GENERATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = module.generate()
    if sha256_bytes(source.encode("utf-8")) != ACCEPTED_COMPANION_SHA256:
        raise AlphaCompanionGenerationError("accepted 0.5.0 communication companion bytes changed")
    return source


def _replace_once(source: str, old: str, new: str) -> str:
    if source.count(old) != 1:
        raise AlphaCompanionGenerationError(f"qualified source anchor changed: {old}")
    return source.replace(old, new)


def generate() -> str:
    source = _accepted_source()
    old_target = '''TARGET_BUILD = {
    "platform": "Windows x64",
    "version": "OrcaSlicer 2.5.0-dev",
    "build": "210bc927",
    "source_commit": "210bc927bc6fb3d3bf390fdf72e4a2767b5de4b3",
    "workflow_run": 38106132250,
    "artifact_id": 11690627983,
    "artifact_name": "OrcaSlicer_Windows_V2.5.0-dev_x64_portable",
    "artifact_digest": "sha256:080b00bc001256fd521a663e2939004d09a14f9bdef08c351167580e0d505d13",
    "orca_slicer_exe_sha256": "8d9db0bec8b8a8e0ad0a70485daaf7ee9fa1c88d5f1395f92eabf0430ce0339b",
    "orca_slicer_dll_sha256": "5b71e5dbf2f6b3319d6d69f597e3aa3dbf9403f9ea63f93c3c72dc294efba0a4",
    "metadata_source": "verified upstream scheduled run, artifact API digest, and downloaded payload hashes",
}'''
    alpha_target = '''TARGET_BUILD = {
    "platform": "Windows x64",
    "version": "OrcaSlicer 2.5.0-alpha",
    "build": "3880f2c5",
    "source_commit": "3880f2c58ec392ed2bd5938ab31c9c7c496c0eb2",
    "release_id": 410256856,
    "asset_id": 647273931,
    "asset_name": "OrcaSlicer_Windows_V2.5.0-alpha_x64_portable.zip",
    "asset_bytes": 221507287,
    "asset_sha256": "9b4593697c9ec0f8e7c0dcbebd7f8ea08a5cd01c2bd68d2a5d48b45b4c18ff8c",
    "orca_slicer_exe_sha256": "a37d149ea315a0a2125c11625b7dc24e456dbd3bc309dd56519d90dcdcd77985",
    "orca_slicer_dll_sha256": "92bdf7493425b949934479164d0745ce5e28fe24c7a556af300792b788e94c8b",
    "metadata_source": "verified official upstream release, asset metadata, and downloaded payload hashes",
}'''
    replacements = (
        ('# version = "0.5.0"', '# version = "0.5.1"'),
        ('EXPORTER_VERSION = "0.5.0"', 'EXPORTER_VERSION = "0.5.1"'),
        (old_target, alpha_target),
        ('matches = version == TARGET_BUILD["version"].removeprefix("OrcaSlicer ") and build.startswith(TARGET_BUILD["build"])',
         'matches = (version, build) == (TARGET_BUILD["version"].removeprefix("OrcaSlicer "), TARGET_BUILD["build"])'),
        ('"reason": None if matches else "Running Orca version/build does not match the pinned October 11 target."',
         '"reason": None if matches else "Running Orca version/build does not match the pinned official 2.5.0-alpha target."'),
        ('qualified = {("2.5.0-dev", TARGET_BUILD["build"]), ("2.5.0-dev", "6a7763f0")}\n    if (info.get("version"), info.get("build")) not in qualified:',
         'if (info.get("version"), info.get("build")) != ("2.5.0-alpha", "3880f2c5"):'),
        ('raise ValueError("This proof requires the qualified Windows nightly.")',
         'raise ValueError("This proof requires the exact qualified Windows 2.5.0-alpha runtime.")'),
        ('if runtime != {"version": "2.5.0-dev", "build": "6a7763f0"}:',
         'if runtime != {"version": "2.5.0-alpha", "build": "3880f2c5"}:'),
        ('raise CommunicationProtocolError("Outbox target is not the qualified October 15 runtime.")',
         'raise CommunicationProtocolError("Outbox target is not the exact qualified 2.5.0-alpha runtime.")'),
        ('"runtime": {"version": "2.5.0-dev", "build": "6a7763f0"},',
         '"runtime": {"version": "2.5.0-alpha", "build": "3880f2c5"},'),
        ('Read-only OrcaSlicer context inspector and nightly qualification probe.',
         'Read-only OrcaSlicer context inspector and official alpha qualification probe.'),
        ('Helix Calibration Nightly Qualification', 'Helix Calibration Alpha Qualification'),
        ('The nightly\'s GCodeExportStarted/GCodeExportFinished', 'The alpha build\'s GCodeExportStarted/GCodeExportFinished'),
        ('The qualified nightly exposes orca.host.app_info()', 'The qualified alpha exposes orca.host.app_info()'),
        ('October 11 nightly qualification · read-only · never starts a print',
         'Official 2.5.0-alpha qualification · read-only · never starts a print'),
    )
    for old, new in replacements:
        source = _replace_once(source, old, new)
    return source


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    source = generate()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(source, encoding="utf-8")
    temporary.replace(args.output)
    print(f"Generated Orca 2.5.0-alpha communication companion: {args.output}")
    print(f"SHA-256: {sha256_bytes(source.encode('utf-8'))}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, AlphaCompanionGenerationError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
