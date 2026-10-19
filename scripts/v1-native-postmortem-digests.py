#!/usr/bin/env python3
"""Read retained local PA G-code and emit only fixed scalar/digest postmortem data.

This never constructs a reference, prepares a job, qualifies output, slices,
executes G-code, or prints raw commands, settings, profile names or file paths.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT))
from integration import v1_contract as c
from integration import v1_parity as p


def inspect(path, expected_sha256):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= p.MAX_GCODE_BYTES:
        raise ValueError('bounded_regular_gcode_required')
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != expected_sha256:
        raise ValueError('retained_gcode_digest_differs')
    # Match parity.evaluate's text-mode universal newline decoding.
    text = raw.decode('utf-8').replace('\r\n', '\n').replace('\r', '\n')
    codes, data = p.executable(text), p.analyze(text)
    if len(data['patterns']) != 4 or not data['moves']:
        raise ValueError('native_pa_pattern_required')
    pattern_codes, inside = [], False
    for line in text.splitlines():
        if line == '; start pressure advance pattern for layer':
            inside = True
        if inside:
            pattern_codes.extend(p.executable(line))
        if line == '; end pressure advance pattern for layer':
            inside = False
    return {'schema': 'helix-orca-v1-pa-postmortem-digests/v1',
            'qualified': False, 'prepared': False, 'physical_actions': False,
            'gcode_sha256': sha, 'executable_count': len(codes),
            'executable_sha256': hashlib.sha256('\n'.join(codes).encode()).hexdigest(),
            'pattern_executable_count': len(pattern_codes),
            'pattern_executable_sha256': hashlib.sha256('\n'.join(pattern_codes).encode()).hexdigest(),
            'model_moves': len(data['moves']), 'model_extrusion_mm': sum(move['e'] for move in data['moves']),
            'heater_stream_sha256': c.digest([{key: value for key, value in heater.items() if key != 'line'}
                                               for heater in data['heaters']]),
            'pa_values_sha256': c.digest([value['value'] for value in data['pa_commands']])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gcode', type=Path, required=True)
    parser.add_argument('--sha256', required=True)
    args = parser.parse_args()
    try:
        result = inspect(args.gcode, args.sha256)
    except Exception:
        # Avoid echoing parser/native errors that could contain private paths/text.
        print(json.dumps({'schema': 'helix-orca-v1-pa-postmortem-digests/v1',
                          'qualified': False, 'prepared': False, 'physical_actions': False,
                          'failure': 'retained_pa_inspection_failed'}, sort_keys=True))
        return 2
    print(c.canonical(result).decode())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
