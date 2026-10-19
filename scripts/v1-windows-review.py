#!/usr/bin/env python3
"""Drive only the V1 marked datadir in the pinned October 15 Windows runtime."""
import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("v1_oct15_ui", ROOT / "orca-oct15-windows-review.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
original = module.issue6_ui_source


def guarded_source():
    source = original()
    changes = {
        "$Stage=Join-Path $env:LOCALAPPDATA 'HelixOrcaCalibration\\issue-6-oct15-6a7763f'":
            "$Stage=Join-Path $env:LOCALAPPDATA 'HelixOrcaCalibration\\v1-qualification'",
        "$Exe=Join-Path $Stage 'runtime\\orca-slicer.exe'":
            "$Exe=Join-Path (Join-Path $env:LOCALAPPDATA 'HelixOrcaCalibration\\issue-6-oct15-6a7763f') 'runtime\\orca-slicer.exe'",
        "HelixOrcaCalibration\\issue-6-nightly-6a7763f": "HelixOrcaCalibration\\v1-qualification\\data",
        ".helix-orca-issue-6-oct15-qualification": ".helix-orca-v1-qualification",
        "Where-Object {$_.ExecutablePath -eq $Exe}":
            "Where-Object {$_.ExecutablePath -eq $Exe -and $_.CommandLine -like ('*--datadir*'+$Data+'*')}",
    }
    for old, new in changes.items():
        if source.count(old) != 1:
            raise ValueError("Qualified Windows guard anchor changed: " + old)
        source = source.replace(old, new)
    if "--passive-menu" in sys.argv:
        for old, new in (("else{[Issue4Native]::SetWindowPos($H,[IntPtr]::new(-1),0,0,0,0,19)|Out-Null}", "else{}"),
                         ("[Windows.Forms.Cursor]::Position=$Original", "[void]$Original"),
                         ("if(-not $WasTop){[Issue4Native]::SetWindowPos($H,[IntPtr]::new(-2),0,0,0,0,19)|Out-Null}", "[void]$WasTop")):
            if source.count(old) != 1:
                raise ValueError("Passive guard anchor changed")
            source = source.replace(old, new)
    return source


module.issue6_ui_source = guarded_source
if __name__ == "__main__":
    passive = "--passive-menu" in sys.argv
    if passive:
        # The source callback sees the flag until argparse needs the clean argv.
        sys.argv.remove("--passive-menu")
        original_guarded = guarded_source
        def with_passive():
            sys.argv.append("--passive-menu")
            try:
                return original_guarded()
            finally:
                sys.argv.remove("--passive-menu")
        module.issue6_ui_source = with_passive
    module.main()
