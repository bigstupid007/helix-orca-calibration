#!/usr/bin/env python3
"""Build a separate storage-only V1 derivative; never deploy or overwrite a plugin."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path
import shutil
import sys
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from integration.v1_contract import DEFAULTS, PARAMETER_LIMITS, PA_DEFAULTS, validate_parameters
SOURCE = ROOT / 'integration/v1-native'
ORDER = ('temperature','flow_ratio_yolo','pressure_advance_pattern','retraction','max_volumetric_speed')
CATALOG = json.loads((SOURCE / 'catalog.json').read_text())
ACCEPTED_TILE = ROOT/'integration/temperature-print/ui/orcacal__tile.xml'
ACCEPTED_TILE_SHA256 = '821b112f6ba3e3fe334caf8bbe83ac41a76c731b1f4f19fa8e07f510a9c10b61'

def hash_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load_base():
    spec = importlib.util.spec_from_file_location('v1_accepted_shell', ROOT/'scripts/temperature-communication-plugin.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def generate(output: Path):
    # Fail the build rather than silently publishing controls with different limits.
    for ident,bounds in PARAMETER_LIMITS.items():
        for key,(minimum,maximum) in bounds.items():
            rule=CATALOG[ident]['parameters'][key]
            if rule.get('kind')!='number' or (rule.get('min'),rule.get('max'))!=(minimum,maximum):
                raise ValueError('Native control limits differ from shared contract')
    for ident,defaults in DEFAULTS.items():validate_parameters(ident,defaults)
    base = load_base()
    baseline = base.verify_baseline()
    if hash_file(ACCEPTED_TILE) != ACCEPTED_TILE_SHA256:
        raise ValueError('Accepted compact tile source changed')
    compact = ACCEPTED_TILE.read_text().replace('orcacal__tp_tile_status','orcacal__v1_tile')
    if (SOURCE/'ui/orcacal__tile.xml').read_text() != compact:
        raise ValueError('V1 compact tile must preserve accepted layout and identity')
    output = output.expanduser().absolute()
    if output.is_symlink() or output.exists() or ROOT.resolve() in output.resolve().parents:
        raise ValueError('V1 output must be a new directory outside the repository')
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(base.BASE, output)
    main = (base.BASE/'main.lua').read_text()
    def lua(value):
        if isinstance(value,dict):return '{'+','.join('['+json.dumps(key)+']='+lua(item) for key,item in value.items())+'}'
        if isinstance(value,list):return '{'+','.join(lua(item) for item in value)+'}'
        return json.dumps(value,ensure_ascii=False)
    main += '\nlocal V1_CATALOG = '+lua(CATALOG)+'\nlocal V1_DEFAULTS = '+lua(DEFAULTS)+'\nlocal V1_PA_DEFAULTS = '+lua(PA_DEFAULTS)+'\n'
    main += (SOURCE/'presentation.lua').read_text() + '\n'
    native=(SOURCE/'main.lua').read_text().replace('-- V1_PARAMETER_CONTROLS',(SOURCE/'controls.lua').read_text())
    main += native
    (output/'main.lua').write_text(main)
    for path in (SOURCE/'ui').glob('*.xml'):
        shutil.copyfile(path, output/'ui'/path.name)
    # The accepted beta.9 pattern uses a distinct overlay identity: a buried
    # manual view must not turn automatic presentation into the host's no-op.
    automatic = re.sub(r'name="orcacal__v1_', 'name="orcacal__v1_auto_',
                       (SOURCE/'ui/orcacal__v1_job.xml').read_text())
    automatic = automatic.replace('name="orcacal__v1_auto_job"', 'name="orcacal__v1_auto_result"')
    (output/'ui/orcacal__v1_auto_result.xml').write_text(automatic)
    manifest = json.loads((base.BASE/'manifest.json').read_text())
    manifest.update(version='1.0.0-v1-candidate', helix_version='>=1.1.0-beta.9', permissions=['storage'],
                    description='Native V1 calibration workflow; no physical action adapter enabled.')
    manifest['widgets'][0].update(colspan=1, rowspan=1)
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (output/'.helix-orca-v1-generated.json').write_text(json.dumps({'schema':'helix-orca-v1-native-generated/v1','accepted_baseline':baseline,'accepted_compact_tile_sha256':ACCEPTED_TILE_SHA256,'physical_adapter_enabled':False},indent=2)+'\n')
    return {str(p.relative_to(output)):hash_file(p) for p in sorted(output.rglob('*')) if p.is_file()}

def default_output():
    return Path(os.environ.get('XDG_CACHE_HOME',Path.home()/'.cache'))/'helix-orca-calibration/v1/native/orcacal'

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=default_output())
    print(json.dumps(generate(parser.parse_args().output),indent=2))
