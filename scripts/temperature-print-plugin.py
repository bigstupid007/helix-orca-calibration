#!/usr/bin/env python3
"""Generate the storage-only beta.9 miniature Temperature readiness derivative."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def generate(output):
    spec = importlib.util.spec_from_file_location('accepted_print_shell_generator', ROOT/'scripts/temperature-communication-plugin.py')
    base = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(base)
    base.generate(output)  # verifies unchanged accepted sources; refuses overwrite
    root = ROOT/'integration/temperature-print'
    (output/'main.lua').write_bytes((base.BASE/'main.lua').read_bytes()+b'\n'+(root/'native.lua').read_bytes())
    for name in ('orcacal__wizard.xml','orcacal__temperature.xml'):
        (output/'ui'/name).write_bytes((root/'ui'/name).read_bytes())
    manifest=json.loads((output/'manifest.json').read_text())
    manifest.update(version='0.4.0-issue12-readiness',description='Three-band Temperature readiness; storage intents only; physical authorization required.')
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (output/base.MARKER_NAME).unlink()
    (output/'.helix-orca-print-generated.json').write_text(json.dumps({'schema':'helix-orca-temperature-print-generated/v1','physical_activation':False})+'\n')
    return {str(p.relative_to(output)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.rglob('*')) if p.is_file()}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    print(json.dumps(generate(args.output),indent=2))
