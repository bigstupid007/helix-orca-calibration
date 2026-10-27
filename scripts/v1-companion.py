#!/usr/bin/env python3
"""Generate a separate self-contained October 15 V1 Orca companion."""
import argparse
import hashlib
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def generate():
    spec = importlib.util.spec_from_file_location("v1_qualified_orca", ROOT / "scripts/orca-oct15-plugin.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = module.generate()
    # The accepted physical Temperature plugin remains byte-for-byte pinned,
    # while the current-Orca V2 companion accepts ConfigOption numeric vectors
    # serialized with native comma delimiters (and legacy semicolons).
    old = '    for index, token in enumerate(text.split(";")):'
    new = '    for index, token in enumerate(re.split(r"[;,]", text)):'
    if source.count(old) != 1:
        raise ValueError("Qualified numeric-vector parser anchor changed")
    source = source.replace(old, new)
    anchor = "@orca.plugin\nclass HelixCalibrationPlugin"
    if source.count(anchor) != 1:
        raise ValueError("Qualified companion class anchor changed")
    contract = (ROOT / "integration/v1_contract.py").read_text()
    extension = (ROOT / "integration/v1_orca_extension.py").read_text()
    source = source.replace(anchor, contract + "\n\n" + extension + "\n\n" + anchor)
    anchor = "        orca.register_capability(TemperatureRoundTripPanel)"
    if source.count(anchor) != 1:
        raise ValueError("Qualified capability anchor changed")
    source = source.replace(anchor, anchor + "\n        orca.register_capability(V2CalibrationPanel)")
    for old, new in (("# version = \"0.4.1\"", "# version = \"2.0.0-v2-candidate\""),
                     ("EXPORTER_VERSION = \"0.4.1\"", "EXPORTER_VERSION = \"2.0.0-v2-candidate\"")):
        if source.count(old) != 1:
            raise ValueError("Qualified version anchor changed")
        source = source.replace(old, new)
    return source


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Refusing to replace an existing plugin artifact")
    source = generate()
    compile(source, "helix_calibration.py", "exec")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(source, encoding="utf-8", newline="\n")
    print(hashlib.sha256(source.encode()).hexdigest())
