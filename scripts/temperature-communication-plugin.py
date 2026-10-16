#!/usr/bin/env python3
"""Generate the beta.9 OrcaCal communication candidate from its accepted shell."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "helix-plugin/orcacal"
INTEGRATION = ROOT / "integration/temperature-communication"
BASELINE_HASHES = {
    "main.lua": "9e9617f8b90d0ed795f63de43fd266813a02aebfa1c47c1635c164bfd099ea56",
    "manifest.json": "6de01177e6289dbd0faf155d9abe57d9e1c41a3392dda55db097e1ff1d7a9b0d",
    "ui/orcacal__temperature.xml": "b221855d6defcf42914e2663a8ec3b30199a287b4abacf44c07330761caf00c0",
    "ui/orcacal__tile.xml": "fdbdb78c0b1db680ca19dc2619abfe3eed5858749162abc55bf9b95bdea26eff",
    "ui/orcacal__wizard.xml": "cc02d31b63f804c0aa34c54f8ba134c7e51817db8ba9417f672e502bffd34f81",
}


class GenerationError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_baseline() -> dict[str, str]:
    observed = {relative: sha256(BASE / relative) for relative in BASELINE_HASHES}
    if observed != BASELINE_HASHES:
        raise GenerationError("accepted OrcaCal baseline changed; refusing to generate derivative")
    return observed


def default_output() -> Path:
    cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return cache / "helix-orca-calibration/temperature-communication/orcacal"


def generate(output: Path, *, replace: bool = False) -> dict[str, object]:
    baseline = verify_baseline()
    output = output.resolve()
    if output == BASE.resolve() or ROOT.resolve() in output.parents:
        raise GenerationError("generated runtime must stay outside the repository")
    if output.exists():
        if not replace:
            raise GenerationError(f"destination exists: {output}")
        shutil.rmtree(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(BASE, output)

    accepted_main = (BASE / "main.lua").read_bytes()
    extension = (INTEGRATION / "native-extension.lua").read_bytes()
    (output / "main.lua").write_bytes(accepted_main + b"\n" + extension)
    for name in ("orcacal__wizard.xml", "orcacal__temperature.xml"):
        shutil.copyfile(INTEGRATION / "ui" / name, output / "ui" / name)

    manifest = json.loads((BASE / "manifest.json").read_text(encoding="utf-8"))
    manifest.update({
        "version": "0.3.0-issue8-native",
        "description": "Native Orca Calibration shell with bounded simulated Temperature return.",
        "helix_version": ">=1.1.0-beta.9",
        "permissions": ["storage"],
    })
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    generated = {
        str(path.relative_to(output)): sha256(path)
        for path in sorted(output.rglob("*")) if path.is_file()
    }
    return {"output": str(output), "accepted_baseline": baseline, "generated": generated}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=default_output())
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    report = generate(args.output, replace=args.replace)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (GenerationError, OSError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
