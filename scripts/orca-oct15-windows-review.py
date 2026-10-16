#!/usr/bin/env python3
"""Drive only the hash-pinned isolated October 15 Orca runtime on Spare."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("review", ROOT / "orca-windows-review.py")
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)

EXE_SHA256 = "e2b6da4c20e7080eade97379f326dcfcaa90f1ecb9991f1db9eb61e3065a9759"


def issue6_ui_source():
    source = (ROOT / "orca-windows-ui.ps1").read_text()
    replacements = {
        "HelixOrcaCalibration\\issue-4-windows": "HelixOrcaCalibration\\issue-6-oct15-6a7763f",
        "nightly\\orca-slicer.exe": "runtime\\orca-slicer.exe",
        "HelixOrcaCalibration\\issue-4-nightly-210bc927": "HelixOrcaCalibration\\issue-6-nightly-6a7763f",
        ".helix-orca-issue-4-qualification": ".helix-orca-issue-6-oct15-qualification",
    }
    for old, new in replacements.items():
        if old not in source:
            raise ValueError("Accepted UI guard changed; missing replacement anchor")
        source = source.replace(old, new)
    anchor = "$Candidates=@(Get-CimInstance Win32_Process"
    if anchor not in source:
        raise ValueError("Accepted UI process guard changed; missing hash insertion anchor")
    guard = (
        "$Actual=(Get-FileHash -LiteralPath $Exe -Algorithm SHA256).Hash.ToLowerInvariant()\n"
        f"if($Actual-ne'{EXE_SHA256}'){{throw 'October 15 executable digest mismatch.'}}\n"
    )
    source = source.replace(anchor, guard + anchor)
    return "\n".join(line for line in source.splitlines() if not line.lstrip().startswith("#"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("op", choices=["windows", "capture", "click", "keys", "tree", "resize"])
    parser.add_argument("--handle", type=int, default=0)
    parser.add_argument("--x", type=int, default=0)
    parser.add_argument("--y", type=int, default=0)
    parser.add_argument("--keys", default="")
    parser.add_argument("--name", default="issue6-frame")
    args = parser.parse_args()
    if not args.name.replace("-", "").replace("_", "").isalnum():
        raise ValueError("Invalid evidence name")
    command = "& {\n" + issue6_ui_source() + "\n} -Op " + review.quote(args.op)
    command += " -Handle " + str(args.handle) + " -X " + str(args.x) + " -Y " + str(args.y)
    command += " -Keys " + review.quote(args.keys) + " -Name " + review.quote(args.name)
    if len(command) > 8192:
        raise ValueError("Issue #6 UI command exceeds worker bound")
    result = review.invoke(command, "issue6-" + args.op)
    if args.op == "capture":
        destination = review.access.state_dir() / "evidence" / (args.name + ".png")
        script = "$K=Join-Path $env:LOCALAPPDATA 'HelixOrcaCalibration\\windows-access\\devbox_known_hosts'; "
        script += "& scp.exe -o BatchMode=yes -o StrictHostKeyChecking=yes -o ClearAllForwardings=yes -o ('UserKnownHostsFile='+$K) "
        script += review.quote(result["file"]) + " " + review.quote("dev@192.168.1.114:" + str(destination))
        script += "; if($LASTEXITCODE-ne0){throw 'Private screenshot transfer failed.'}; @{transferred=$true}|ConvertTo-Json -Compress"
        review.invoke(script, "issue6-screenshot-transfer")
        if review.hashlib.sha256(destination.read_bytes()).hexdigest() != result["sha256"]:
            raise ValueError("Screenshot digest mismatch")
        result["local_file"] = str(destination)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
