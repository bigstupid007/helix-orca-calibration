#!/usr/bin/env python3
"""Private, serialized LAN SSH test bridge. No TCP listener or product transport."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import select
import socket
import sys
import uuid

PROTOCOL = 'helix-orca-spare-access/v1'
MAX_BYTES = 1048576


def state_dir():
    base = Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local/state'))
    return base / 'helix-orca-calibration/windows-access'


def read_message(stream):
    line = stream.readline(MAX_BYTES + 1)
    if not line or len(line) > MAX_BYTES or not line.endswith(b'\n'):
        raise ValueError('Disconnected or oversized/incomplete protocol message')
    value = json.loads(line)
    if not isinstance(value, dict):
        raise ValueError('Expected a JSON object')
    return value


def encode_message(value):
    data = (json.dumps(value, ensure_ascii=True) + '\n').encode()
    if len(data) > MAX_BYTES:
        raise ValueError('Protocol message exceeds limit')
    return data


def validate_hello(hello, connection):
    fields = connection.split()
    if len(fields) != 4 or fields[0] != '192.168.1.155' or fields[2:] != ['192.168.1.114', '22']:
        raise ValueError('Worker must arrive over Spare-to-devbox LAN SSH')
    if hello.get('protocol') != PROTOCOL or hello.get('hostname', '').casefold() != 'spare':
        raise ValueError('Unexpected worker protocol or Windows host')
    if type(hello.get('session_id')) is not int or hello['session_id'] <= 0:
        raise ValueError('Worker requires a signed-in interactive Windows session')
    if hello.get('is_admin') is not False or not hello.get('identity'):
        raise ValueError('Worker must run unelevated with an identified user')


def validate_request(request):
    if request.get('op') not in ('probe', 'exec', 'stop'):
        raise ValueError('Unsupported testing operation')
    timeout = request.get('timeout_seconds', 60)
    if type(timeout) is not int or not 1 <= timeout <= 60:
        raise ValueError('Testing command timeout must be 1..60 seconds')
    if request['op'] == 'exec':
        script = request.get('script')
        if not isinstance(script, str) or not script.strip() or len(script) > 8192:
            raise ValueError('Testing script must contain 1..8192 characters')
    return request


def serve():
    directory = state_dir()
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(directory, 0o700)
    path = directory / 'bridge.sock'
    if path.exists():
        raise ValueError('Bridge socket already exists; inspect the current session before replacing it')
    incoming = sys.stdin.buffer
    if not select.select([incoming], [], [], 20)[0]:
        raise TimeoutError('Windows worker handshake timed out')
    hello = read_message(incoming)
    validate_hello(hello, os.environ.get('SSH_CONNECTION', ''))
    hello.update({'bridge_pid': os.getpid(), 'ssh_connection': os.environ['SSH_CONNECTION']})
    session_path = directory / 'session.json'
    session_path.write_text(json.dumps(hello, indent=2) + '\n')
    os.chmod(session_path, 0o600)
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
        listener.bind(str(path))
        os.chmod(path, 0o600)
        listener.listen(1)
        listener.settimeout(1)
        try:
            while True:
                if select.select([incoming], [], [], 0)[0]:
                    raise ConnectionError('Unexpected worker message or disconnected SSH session')
                try:
                    client, _ = listener.accept()
                except socket.timeout:
                    continue
                with client:
                    client.settimeout(70)
                    stream = client.makefile('rb')
                    try:
                        request = validate_request(read_message(stream))
                    except (ValueError, OSError) as exc:
                        client.sendall(encode_message({'error': str(exc)}))
                        continue
                    request['request_id'] = str(uuid.uuid4())
                    metadata = {k: request[k] for k in ('request_id', 'op')}
                    metadata['script_sha256'] = hashlib.sha256(request.get('script', '').encode()).hexdigest()
                    with (directory / 'requests.jsonl').open('a') as log:
                        log.write(json.dumps(metadata) + '\n')
                    os.chmod(directory / 'requests.jsonl', 0o600)
                    sys.stdout.buffer.write(encode_message(request))
                    sys.stdout.buffer.flush()
                    if not select.select([incoming], [], [], request.get('timeout_seconds', 60) + 10)[0]:
                        raise TimeoutError('Windows worker did not complete within its bound')
                    response = read_message(incoming)
                    if response.get('request_id') != request['request_id']:
                        raise ValueError('Mismatched Windows response; ending access session')
                    client.sendall(encode_message(response))
                    if request['op'] == 'stop':
                        return
        finally:
            path.unlink(missing_ok=True)
            session_path.unlink(missing_ok=True)


def request(op, script=None, timeout=60):
    value = {'op': op, 'timeout_seconds': timeout}
    if script is not None:
        value['script'] = script
    validate_request(value)
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(timeout + 15)
        client.connect(str(state_dir() / 'bridge.sock'))
        client.sendall(encode_message(value))
        return read_message(client.makefile('rb'))


def prepare():
    source = Path(__file__).resolve().parent
    names = ('spare-access.py', 'spare-access.ps1', 'spare-gui-smoke.ps1')
    payloads = {name: (source / name).read_bytes() for name in names}
    digest = hashlib.sha256()
    for name, data in payloads.items():
        digest.update(name.encode() + b'\0' + data)
    # Fixed canonical devbox cache location; never an Issue-specific /tmp runtime.
    destination = Path.home() / '.cache/helix-orca-calibration/windows-access' / digest.hexdigest()
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(destination, 0o700)
    payloads['spare-access.ps1'] = payloads['spare-access.ps1'].replace(
        b'__BRIDGE_PATH__', str(destination / 'spare-access.py').encode())
    manifest = {}
    for name, data in payloads.items():
        target = destination / name
        if target.exists() and target.read_bytes() != data:
            raise ValueError('Frozen access bundle differs from source: ' + name)
        if not target.exists():
            target.write_bytes(data)
        os.chmod(target, 0o400)
        manifest[name] = hashlib.sha256(data).hexdigest()
    manifest_path = destination / 'manifest.json'
    manifest_data = json.dumps(manifest, indent=2) + '\n'
    if manifest_path.exists():
        if manifest_path.read_text() != manifest_data:
            raise ValueError('Frozen bundle manifest differs from source')
    else:
        manifest_path.write_text(manifest_data)
    os.chmod(manifest_path, 0o400)
    print(json.dumps({'bundle_dir': str(destination), 'sha256': manifest,
                     'windows_launch': 'ssh -o BatchMode=yes -o StrictHostKeyChecking=yes dev@192.168.1.114 "cat ' +
                     str(destination / 'spare-access.ps1') + '"'}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('serve')
    sub.add_parser('prepare')
    sub.add_parser('status')
    sub.add_parser('probe')
    sub.add_parser('stop')
    execute = sub.add_parser('exec')
    execute.add_argument('--script-file', type=Path, required=True)
    execute.add_argument('--timeout', type=int, default=60)
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare()
    elif args.command == 'serve':
        serve()
    elif args.command == 'status':
        path = state_dir() / 'session.json'
        print(path.read_text() if path.exists() else json.dumps({'connected': False}))
    else:
        script = args.script_file.read_text(encoding='utf-8') if args.command == 'exec' else None
        result = request(args.command, script, getattr(args, 'timeout', 60))
        print(json.dumps(result, indent=2))
        if result.get('error') or result.get('exit_code', 0) != 0:
            raise SystemExit(1)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
