#!/usr/bin/env python3
"""Offline V1 preparation. Configuration contains explicit pinned local paths."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from integration.v1_generation import GenerationBlocked
from integration.v1_routing import generate


def native_reference():
    from integration.v1_parity import create_native_reference
    parser = argparse.ArgumentParser(description='Register a genuine independent native UI export. Never import a generated candidate as native evidence.')
    parser.add_argument('--native-gcode', required=True, type=Path)
    parser.add_argument('--native-context', required=True, type=Path, help='Complete pre-calibration context independently captured from this native run')
    parser.add_argument('--calibration', required=True)
    parser.add_argument('--parameters', required=True, type=Path)
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--evidence', required=True, action='append', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(sys.argv[2:])
    manifest = create_native_reference(args.native_gcode, json.loads(args.native_context.read_text()),
                                       args.calibration, json.loads(args.parameters.read_text()),
                                       args.source_commit, [args.native_context, *args.evidence])
    # Creation is provenance registration, never a qualified disposition.
    with args.output.open('x') as stream:
        json.dump(manifest, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'manifest': str(args.output), 'qualified': False,
                      'reason': 'Provenance registered; candidate comparison is still required.'}))
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--request', required=True, type=Path)
    p.add_argument('--snapshot', required=True, type=Path)
    p.add_argument('--config', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    try:
        result = generate(json.loads(a.request.read_text()), json.loads(a.snapshot.read_text()),
                          a.output, json.loads(a.config.read_text()))
        print(json.dumps(result, indent=2))
        return 0 if result['parity']['qualified'] else 2
    except GenerationBlocked as exc:
        print(json.dumps({'phase': 'blocked', 'code': exc.code, 'reason': exc.reason}))
        return 2


if __name__ == '__main__':
    raise SystemExit(native_reference() if len(sys.argv) > 1 and sys.argv[1] == 'native-reference' else main())
