#!/usr/bin/env python3
"""Build a separate storage-only V1 derivative; never deploy or overwrite a plugin."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'integration/v1-native'
ORDER = ('temperature','flow_ratio_yolo','pressure_advance_pattern','retraction','max_volumetric_speed')
CATALOG = json.loads((SOURCE / 'catalog.json').read_text())

def hash_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load_base():
    spec = importlib.util.spec_from_file_location('v1_accepted_shell', ROOT/'scripts/temperature-communication-plugin.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def generate(output: Path):
    base = load_base()
    baseline = base.verify_baseline()
    output = output.expanduser().absolute()
    if output.is_symlink() or output.exists() or ROOT.resolve() in output.resolve().parents:
        raise ValueError('V1 output must be a new directory outside the repository')
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(base.BASE, output)
    main = (base.BASE/'main.lua').read_text()
    # Values are JSON scalar literals, also valid Lua after false/true conversion.
    catalog = []
    for ident in ORDER:
        entry = CATALOG[ident]
        params = []
        for key, values in entry['parameters'].items():
            params.append('[%s]={%s}' % (json.dumps(key), ','.join(json.dumps(v) for v in values)))
        catalog.append('[%s]={name=%s,parameters={%s}}' % (json.dumps(ident), json.dumps(entry['name']), ','.join(params)))
    main += '\nlocal V1_CATALOG = {' + ','.join(catalog) + '}\n'
    main += (SOURCE/'main.lua').read_text()
    (output/'main.lua').write_text(main)
    for path in (SOURCE/'ui').glob('*.xml'):
        shutil.copyfile(path, output/'ui'/path.name)
    manifest = json.loads((base.BASE/'manifest.json').read_text())
    manifest.update(version='1.0.0-v1-candidate', helix_version='>=1.1.0-beta.9', permissions=['storage'],
                    description='Native V1 calibration workflow; no physical action adapter enabled.')
    manifest['widgets'][0].update(colspan=1, rowspan=1)
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (output/'.helix-orca-v1-generated.json').write_text(json.dumps({'schema':'helix-orca-v1-native-generated/v1','accepted_baseline':baseline,'physical_adapter_enabled':False},indent=2)+'\n')
    return {str(p.relative_to(output)):hash_file(p) for p in sorted(output.rglob('*')) if p.is_file()}

def default_output():
    return Path(os.environ.get('XDG_CACHE_HOME',Path.home()/'.cache'))/'helix-orca-calibration/v1/native/orcacal'

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=default_output())
    print(json.dumps(generate(parser.parse_args().output),indent=2))
