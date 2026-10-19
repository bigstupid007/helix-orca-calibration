#!/usr/bin/env python3
"""Prepare exact native Temperature geometry, without slicing or qualification."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from integration.v1_temperature_geometry import prepare, TemperatureGeometryBlocked


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('request', 'context', 'config', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    try:
        result = prepare(json.loads(args.request.read_text()), json.loads(args.context.read_text()),
                         args.output, json.loads(args.config.read_text()))
    except (TemperatureGeometryBlocked, RuntimeError, ValueError, OSError, KeyError) as exc:
        print(json.dumps({'generated': False, 'qualified': False, 'reason': str(exc)}))
        return 2
    print(json.dumps({'generated': True, 'qualified': False, 'gcode_generated': False,
                     'source_commit': result['source_commit'],
                     'request_sha256': result['request_sha256'],
                     'context_sha256': result['context_sha256'],
                     'model_sha256': result['model']['sha256'], 'metrics': result['metrics']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
