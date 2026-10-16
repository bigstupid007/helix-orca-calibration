#!/usr/bin/env python3
"""Owner-run proposal only. Inspect by default; --apply links one result file.

Requires a separate explicit Founder authorization. No remote execution,
credentials, permission changes, service changes, or directory-wide links.
"""
import argparse
import json
import os
import re
from pathlib import Path


def plan(install, shared, request_id, apply=False):
    if not re.fullmatch(r"[0-9a-f]{32}", request_id):
        raise ValueError("Expected exact original request ID")
    install = Path(install).resolve(strict=True)
    shared = Path(shared).resolve(strict=True)
    if not (install / 'config/settings.json').samefile(shared / 'settings.json'):
        raise ValueError('These are not the installation/shared settings locations')
    manifest = json.loads((shared / 'plugins/orcacal/manifest.json').read_text())
    if (manifest.get('id'), manifest.get('version'), manifest.get('permissions')) != (
            'orcacal', '0.3.0-issue8-native', ['storage']):
        raise ValueError('Reviewed storage-only OrcaCal installation is absent')
    source = install / 'config/plugin-data/orcacal.json'
    if source.is_symlink() or not source.is_file() or not 0 < source.stat().st_size <= 262144:
        raise ValueError('Expected bounded regular native storage file is absent')
    state = json.loads(source.read_text())
    request = state.get('session', {}).get('request', {})
    if (request.get('schema') != 'helix-orca-temperature-session/v1'
            or request.get('request_id') != request_id
            or request.get('simulation_only') is not True
            or request.get('not_applied') is not True):
        raise ValueError('Native file does not belong to the retained proof request')
    parent = shared / 'plugin-data'
    if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
        raise ValueError('Shared sidecar parent must be a real directory')
    destination = parent / 'orcacal.json'
    if os.path.lexists(destination):
        if not destination.is_symlink() or destination.resolve() != source.resolve():
            raise ValueError('Refusing to replace an existing destination')
        return {'changed': False, 'already_linked': True}
    if source.resolve() == destination.resolve():
        raise ValueError('Storage already resolves here; no link change is justified')
    if apply:
        parent.mkdir(exist_ok=True)
        destination.symlink_to(source)
    return {'changed': apply, 'source': str(source), 'single_file_link': str(destination),
            'readability_by_moonraker': 'must be checked using existing authenticated GET',
            'rollback': 'remove only this exact link after checking its target; never remove native data'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--install', required=True)
    p.add_argument('--shared', required=True)
    p.add_argument('--request-id', required=True)
    p.add_argument('--apply', action='store_true')
    a = p.parse_args()
    print(json.dumps(plan(a.install, a.shared, a.request_id, a.apply), indent=2))


if __name__ == '__main__':
    main()
