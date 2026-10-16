#!/usr/bin/env python3
"""Generate the bounded October 15 Orca plugin without changing Issue #4 bytes."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "plugin/helix_calibration.py"
BASE_SHA256 = "8f0269e6510ca11848144c14fc2c42a33ea288e8dd1bfa7bd1e5789636bf3d52"
ISSUE6_BUILD = "6a7763f0"
ISSUE6_SOURCE = "6a7763f08d1a175a464a00ce13f0b5a815662fc4"


class PluginGenerationError(RuntimeError):
    pass


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def generate() -> str:
    source = BASE.read_text(encoding="utf-8")
    actual = sha256_bytes(source.encode())
    if BASE_SHA256 and actual != BASE_SHA256:
        raise PluginGenerationError("accepted Issue #4 plugin source changed")
    replacements = {
        '# version = "0.4.0"': '# version = "0.4.1"',
        'EXPORTER_VERSION = "0.4.0"': 'EXPORTER_VERSION = "0.4.1"',
        'if info.get("build") != TARGET_BUILD["build"] or info.get("version") != "2.5.0-dev":': (
            'qualified = {("2.5.0-dev", TARGET_BUILD["build"]), '
            f'("2.5.0-dev", "{ISSUE6_BUILD}")' + '}\n'
            '    if (info.get("version"), info.get("build")) not in qualified:'
        ),
    }
    for old, new in replacements.items():
        if source.count(old) != 1:
            raise PluginGenerationError(f"accepted plugin anchor changed: {old}")
        source = source.replace(old, new)
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
    print(f"Generated October 15 plugin: {args.output}")
    print(f"SHA-256: {sha256_bytes(source.encode())}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, PluginGenerationError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
