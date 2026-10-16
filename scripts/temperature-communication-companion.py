#!/usr/bin/env python3
"""Generate the self-contained October 15 Temperature communication companion."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
OCT15_GENERATOR = ROOT / "scripts/orca-oct15-plugin.py"
PROTOCOL = ROOT / "integration/temperature-communication/protocol.py"
EXTENSION = ROOT / "integration/temperature-communication/orca_extension.py"
BASE_SHA256 = "8f0269e6510ca11848144c14fc2c42a33ea288e8dd1bfa7bd1e5789636bf3d52"
OCT15_GENERATOR_SHA256 = "6cec86e359815345cf4477289951f671e40ab93d274dade1b5a9456489be5106"


class CompanionGenerationError(RuntimeError):
    pass


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _oct15_source() -> str:
    if sha256_bytes((ROOT / "plugin/helix_calibration.py").read_bytes()) != BASE_SHA256:
        raise CompanionGenerationError("accepted plugin source changed")
    if sha256_bytes(OCT15_GENERATOR.read_bytes()) != OCT15_GENERATOR_SHA256:
        raise CompanionGenerationError("accepted October 15 generator changed")
    spec = importlib.util.spec_from_file_location("accepted_oct15_generator", OCT15_GENERATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.generate()


def generate() -> str:
    source = _oct15_source()
    for old, new in (
        ('# version = "0.4.1"', '# version = "0.5.0"'),
        ('EXPORTER_VERSION = "0.4.1"', 'EXPORTER_VERSION = "0.5.0"'),
    ):
        if source.count(old) != 1:
            raise CompanionGenerationError(f"qualified source anchor changed: {old}")
        source = source.replace(old, new)
    registration = "        orca.register_capability(TemperatureRoundTripPanel)"
    if source.count(registration) != 1:
        raise CompanionGenerationError("capability registration anchor changed")
    source = source.replace(registration, registration + "\n        orca.register_capability(TemperatureCommunicationPanel)")
    class_anchor = "@orca.plugin\nclass HelixCalibrationPlugin"
    if source.count(class_anchor) != 1:
        raise CompanionGenerationError("plugin class anchor changed")
    protocol = PROTOCOL.read_text(encoding="utf-8").rstrip() + "\n\n"
    extension = EXTENSION.read_text(encoding="utf-8").rstrip() + "\n\n"
    embedded = "\n# BEGIN GENERATED TEMPERATURE COMMUNICATION\n" + protocol + "\n" + extension + "\n# END GENERATED TEMPERATURE COMMUNICATION\n\n"
    return source.replace(class_anchor, embedded + class_anchor)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    source = generate()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(source, encoding="utf-8")
    temporary.replace(args.output)
    print(f"Generated Temperature communication companion: {args.output}")
    print(f"SHA-256: {sha256_bytes(source.encode())}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, CompanionGenerationError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
