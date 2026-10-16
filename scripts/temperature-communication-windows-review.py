#!/usr/bin/env python3
"""Guarded Issue #8 Windows evidence, including Orca's transient native menus."""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--passive-menu', action='store_true')
    parser.add_argument('--region', nargs=4, type=int, metavar=('LEFT','TOP','WIDTH','HEIGHT'))
    options, remaining = parser.parse_known_args()
    if options.region and (min(options.region[:2]) < 0 or min(options.region[2:]) <= 0):
        raise ValueError('Invalid bounded native capture region')
    source_path = Path(__file__).with_name('orca-oct15-windows-review.py')
    spec = importlib.util.spec_from_file_location('communication_oct15_review', source_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = module.issue6_ui_source

    def guarded_source():
        source = original()
        # Keep all executable, datadir, WebView, PID, point ownership and bounds
        # checks. Topmost/cursor restoration dismisses native transient menus;
        # passive mode leaves focus and the cursor at the approved native point.
        replacements = []
        if options.passive_menu:
            replacements = [
                ('else{[Issue4Native]::SetWindowPos($H,[IntPtr]::new(-1),0,0,0,0,19)|Out-Null}', 'else{}'),
                ('[Windows.Forms.Cursor]::Position=$Original', '[void]$Original'),
                ('if(-not $WasTop){[Issue4Native]::SetWindowPos($H,[IntPtr]::new(-2),0,0,0,0,19)|Out-Null}', '[void]$WasTop'),
            ]
        # Wait for queued keyboard input before capture changes window ordering.
        replacements.append(('[Windows.Forms.SendKeys]::SendWait($Keys)',
                             '[Windows.Forms.SendKeys]::SendWait($Keys); Start-Sleep -Milliseconds 350'))
        for before, after in replacements:
            if source.count(before) != 1:
                raise ValueError('Accepted Windows evidence guard anchor changed')
            source = source.replace(before, after)
        if options.region:
            if not remaining or remaining[0] != 'capture':
                raise ValueError('A native region is valid only for capture')
            tree_start = source.index("if($Op -eq 'tree') {")
            tree_end = source.index('$WasTop=', tree_start)
            source = source[:tree_start] + source[tree_end:]
            left, top, width, height = options.region
            needle = "  $Dir=Join-Path $Stage 'screenshots';"
            region = f"if({left}+{width} -gt $Width -or {top}+{height} -gt $Height){{throw 'Region outside target'}};$r.left+={left};$r.top+={top};$Width={width};$Height={height};"
            region += "$p.x=$r.left+[int]($Width/2);$p.y=$r.top+[int]($Height/2);if($Allowed -notcontains [Issue4Native]::Owner([Issue4Native]::GetAncestor([Issue4Native]::WindowFromPoint($p),2))){throw 'Region occluded'};"
            if source.count(needle) != 1:
                raise ValueError('Accepted capture anchor changed')
            source = source.replace(needle, region + needle)
        return '\n'.join(line.strip() for line in source.splitlines() if line.strip())

    module.issue6_ui_source = guarded_source
    sys.argv = [sys.argv[0], *remaining]
    module.main()


if __name__ == '__main__':
    main()
