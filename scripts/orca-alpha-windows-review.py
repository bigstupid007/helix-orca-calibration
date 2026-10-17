#!/usr/bin/env python3
"""Guarded Issue #10 review of the hash-pinned official Orca alpha on Spare."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
OCT15_REVIEW = ROOT / "orca-oct15-windows-review.py"
COMMUNICATION_REVIEW = ROOT / "temperature-communication-windows-review.py"
OCT15_REVIEW_SHA256 = "27f3cf38188e8dd2598de402a76c073d8a0d67a785c350105e2dd26dbb36fd6c"
COMMUNICATION_REVIEW_SHA256 = "d5acdfad02772830c86fc72519a97b7bb4d19f91be36e21c8af83352abc7ece4"
EXE_SHA256 = "a37d149ea315a0a2125c11625b7dc24e456dbd3bc309dd56519d90dcdcd77985"
DLL_SHA256 = "92bdf7493425b949934479164d0745ce5e28fe24c7a556af300792b788e94c8b"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_review():
    if _sha256(OCT15_REVIEW) != OCT15_REVIEW_SHA256:
        raise ValueError("Accepted October 15 Windows review source changed")
    if _sha256(COMMUNICATION_REVIEW) != COMMUNICATION_REVIEW_SHA256:
        raise ValueError("Accepted communication Windows review source changed")
    spec = importlib.util.spec_from_file_location("alpha_oct15_review", OCT15_REVIEW)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _replace_once(source: str, before: str, after: str) -> str:
    if source.count(before) != 1:
        raise ValueError("Accepted Windows evidence guard anchor changed")
    return source.replace(before, after)


def alpha_ui_source(review, *, passive_menu=False, region=None, op="windows"):
    source = review.issue6_ui_source()
    replacements = (
        ("HelixOrcaCalibration\\issue-6-oct15-6a7763f", "HelixOrcaCalibration\\issue-10-alpha-3880f2c"),
        ("HelixOrcaCalibration\\issue-6-nightly-6a7763f", "HelixOrcaCalibration\\issue-10-alpha-3880f2c\\data"),
        (".helix-orca-issue-6-oct15-qualification", ".helix-orca-issue-10-alpha-data"),
        (review.EXE_SHA256, EXE_SHA256),
        ("October 15 executable digest mismatch.", "Official 2.5.0-alpha executable digest mismatch."),
    )
    for before, after in replacements:
        source = _replace_once(source, before, after)
    process_admission = "$Candidates=@(Get-CimInstance Win32_Process"
    dll_guard = (
        "$Dll=Join-Path $Stage 'runtime\\OrcaSlicer.dll'\n"
        "$ActualDll=(Get-FileHash -LiteralPath $Dll -Algorithm SHA256).Hash.ToLowerInvariant()\n"
        f"if($ActualDll-ne'{DLL_SHA256}'){{throw 'Official 2.5.0-alpha DLL digest mismatch.'}}\n"
    )
    source = _replace_once(source, process_admission, dll_guard + process_admission)
    if passive_menu:
        for before, after in (
            ("else{[Issue4Native]::SetWindowPos($H,[IntPtr]::new(-1),0,0,0,0,19)|Out-Null}", "else{}"),
            ("[Windows.Forms.Cursor]::Position=$Original", "[void]$Original"),
            ("if(-not $WasTop){[Issue4Native]::SetWindowPos($H,[IntPtr]::new(-2),0,0,0,0,19)|Out-Null}", "[void]$WasTop"),
        ):
            source = _replace_once(source, before, after)
    source = _replace_once(
        source, "[Windows.Forms.SendKeys]::SendWait($Keys)",
        "[Windows.Forms.SendKeys]::SendWait($Keys); Start-Sleep -Milliseconds 350")
    if region:
        if op != "capture":
            raise ValueError("A native region is valid only for capture")
        tree_start = source.index("if($Op -eq 'tree') {")
        tree_end = source.index("$WasTop=", tree_start)
        source = source[:tree_start] + source[tree_end:]
        left, top, width, height = region
        needle = "  $Dir=Join-Path $Stage 'screenshots';"
        bounded = f"if({left}+{width} -gt $Width -or {top}+{height} -gt $Height){{throw 'Region outside target'}};$r.left+={left};$r.top+={top};$Width={width};$Height={height};"
        bounded += "$p.x=$r.left+[int]($Width/2);$p.y=$r.top+[int]($Height/2);if($Allowed -notcontains [Issue4Native]::Owner([Issue4Native]::GetAncestor([Issue4Native]::WindowFromPoint($p),2))){throw 'Region occluded'};"
        source = _replace_once(source, needle, bounded + needle)
    return "\n".join(line.strip() for line in source.splitlines() if line.strip())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("op", choices=["windows", "capture", "click", "keys", "tree", "resize"])
    parser.add_argument("--handle", type=int, default=0)
    parser.add_argument("--x", type=int, default=0)
    parser.add_argument("--y", type=int, default=0)
    parser.add_argument("--keys", default="")
    parser.add_argument("--name", default="issue10-alpha-frame")
    parser.add_argument("--passive-menu", action="store_true")
    parser.add_argument("--region", nargs=4, type=int, metavar=("LEFT", "TOP", "WIDTH", "HEIGHT"))
    args = parser.parse_args()
    if not args.name.replace("-", "").replace("_", "").isalnum():
        raise ValueError("Invalid evidence name")
    if args.region and (min(args.region[:2]) < 0 or min(args.region[2:]) <= 0):
        raise ValueError("Invalid bounded native capture region")
    review = _load_review()
    source = alpha_ui_source(review, passive_menu=args.passive_menu, region=args.region, op=args.op)
    command = "& {\n" + source + "\n} -Op " + review.review.quote(args.op)
    command += " -Handle " + str(args.handle) + " -X " + str(args.x) + " -Y " + str(args.y)
    command += " -Keys " + review.review.quote(args.keys) + " -Name " + review.review.quote(args.name)
    if len(command) > 8192:
        raise ValueError("Issue #10 Alpha UI command exceeds worker bound")
    result = review.review.invoke(command, "issue10-alpha-" + args.op)
    if args.op == "capture":
        destination = review.review.access.state_dir() / "evidence" / (args.name + ".png")
        script = "$K=Join-Path $env:LOCALAPPDATA 'HelixOrcaCalibration\\windows-access\\devbox_known_hosts'; "
        script += "& scp.exe -o BatchMode=yes -o StrictHostKeyChecking=yes -o ClearAllForwardings=yes -o ('UserKnownHostsFile='+$K) "
        script += review.review.quote(result["file"]) + " " + review.review.quote("dev@192.168.1.114:" + str(destination))
        script += "; if($LASTEXITCODE-ne0){throw 'Private screenshot transfer failed.'}; @{transferred=$true}|ConvertTo-Json -Compress"
        review.review.invoke(script, "issue10-alpha-screenshot-transfer")
        if hashlib.sha256(destination.read_bytes()).hexdigest() != result["sha256"]:
            raise ValueError("Screenshot digest mismatch")
        result["local_file"] = str(destination)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
