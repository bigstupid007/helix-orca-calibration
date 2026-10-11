#!/usr/bin/env python3
"""Drive only the isolated qualification nightly over the private testing bridge."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('spare_access', ROOT / 'spare-access.py')
access = importlib.util.module_from_spec(spec)
spec.loader.exec_module(access)


def quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def invoke(script, name):
    response = access.request('exec', script)
    directory = access.state_dir() / 'evidence'
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    (directory / (name + '-' + str(uuid.uuid4()) + '.json')).write_text(json.dumps(response, indent=2))
    if response.get('exit_code') != 0 or response.get('error') or response.get('output_truncated'):
        raise RuntimeError(json.dumps(response))
    return json.loads(response['stdout'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('op', choices=['windows', 'capture', 'click', 'keys', 'tree', 'resize'])
    parser.add_argument('--handle', type=int, default=0)
    parser.add_argument('--x', type=int, default=0)
    parser.add_argument('--y', type=int, default=0)
    parser.add_argument('--keys', default='')
    parser.add_argument('--name', default='frame')
    args = parser.parse_args()
    if not args.name.replace('-', '').replace('_', '').isalnum():
        raise ValueError('Invalid evidence name')
    source = (ROOT / 'orca-windows-ui.ps1').read_text()
    command = '& {\n' + source + '\n} -Op ' + quote(args.op) + ' -Handle ' + str(args.handle)
    command += ' -X ' + str(args.x) + ' -Y ' + str(args.y) + ' -Keys ' + quote(args.keys) + ' -Name ' + quote(args.name)
    result = invoke(command, args.op)
    if args.op == 'capture':
        destination = access.state_dir() / 'evidence' / (args.name + '.png')
        script = "$Known=Join-Path $env:LOCALAPPDATA 'HelixOrcaCalibration\\windows-access\\devbox_known_hosts'; "
        script += '& scp.exe -o BatchMode=yes -o StrictHostKeyChecking=yes -o ClearAllForwardings=yes '
        script += "-o ('UserKnownHostsFile='+$Known) " + quote(result['file']) + ' ' + quote('dev@192.168.1.114:' + str(destination))
        script += "; if($LASTEXITCODE -ne 0){throw 'Private screenshot transfer failed.'}; @{transferred=$true}|ConvertTo-Json -Compress"
        invoke(script, 'screenshot-transfer')
        if hashlib.sha256(destination.read_bytes()).hexdigest() != result['sha256']:
            raise ValueError('Screenshot digest mismatch')
        result['local_file'] = str(destination)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
