#!/usr/bin/env python3
"""Package unchanged qualification JSON in Orca's supported offline namespace."""
import hashlib
import json
import os
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
METADATA = {
    'id': 'helix-issue-4-original-context',
    'name': 'Helix Issue 4 original fixtures',
    'version': '2.4.0.2',
    'description': 'Offline qualification bundle; supplied profile JSON preserved byte-for-byte.',
}


def main():
    profiles = ROOT / 'testdata/orca-profiles'
    files = sorted(profiles.glob('*.json'), key=lambda p: (bool(json.loads(p.read_text()).get('inherits')), p.name))
    if len(files) != 6:
        raise ValueError('Expected the six original qualification profiles')
    directory = Path(os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache')) / 'helix-orca-calibration/orca-nightly'
    directory.mkdir(parents=True, exist_ok=True)
    output = directory / 'issue-4-original-profiles-reproducible.orca_bundle'
    entries = {'bundle_structure.json': json.dumps(METADATA).encode()}
    for path in files:
        raw = path.read_bytes()
        value = json.loads(raw)
        kind = next(k for k, field in [('printer', 'printer_settings_id'), ('process', 'print_settings_id'), ('filament', 'filament_settings_id')] if field in value)
        entries[kind + '/' + path.name] = raw
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, raw in entries.items():
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, raw)
    with zipfile.ZipFile(output) as archive:
        for name, raw in entries.items():
            if archive.read(name) != raw:
                raise ValueError('Bundle did not preserve fixture bytes')
    print(json.dumps({'path': str(output), 'sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
                      'entries': {name: hashlib.sha256(raw).hexdigest() for name, raw in entries.items()}}, indent=2))


if __name__ == '__main__':
    main()
