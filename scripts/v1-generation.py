#!/usr/bin/env python3
"""Offline V1 preparation. Configuration contains explicit pinned local paths."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from integration.v1_generation import generate, GenerationBlocked


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
    raise SystemExit(main())
