import contextlib
import io
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/spare-access.py'
spec = importlib.util.spec_from_file_location('spare_access', SCRIPT)
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)

HELLO = {'protocol': bridge.PROTOCOL, 'hostname': 'Spare', 'identity': 'test-user',
         'session_id': 1, 'is_admin': False}
LAN = '192.168.1.155 50000 192.168.1.114 22'


class SpareAccessTests(unittest.TestCase):
    def start_server(self, root, hello=HELLO, connection=LAN):
        env = dict(os.environ, XDG_STATE_HOME=str(root), SSH_CONNECTION=connection)
        process = subprocess.Popen([sys.executable, str(SCRIPT), 'serve'], env=env,
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        self.addCleanup(self.close_server, process)
        process.stdin.write(bridge.encode_message(hello))
        process.stdin.flush()
        return process

    @staticmethod
    def close_server(process):
        if process.poll() is None:
            process.terminate()
        process.wait(timeout=3)
        for stream in (process.stdin, process.stdout, process.stderr):
            stream.close()

    def wait_socket(self, root, process):
        path = root / 'helix-orca-calibration/windows-access/bridge.sock'
        deadline = time.monotonic() + 3
        while not path.exists() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertTrue(path.exists(), 'Bridge did not become ready')
        return path

    def test_rejects_other_host_elevated_or_noninteractive_session_and_nonlan_route(self):
        variants = [dict(HELLO, hostname='LAPTOP-EC83OFDE'), dict(HELLO, is_admin=True),
                    dict(HELLO, session_id=0), dict(HELLO, session_id=True)]
        for hello in variants:
            with self.subTest(hello=hello), tempfile.TemporaryDirectory() as temp:
                process = self.start_server(Path(temp), hello)
                self.assertEqual(1, process.wait(timeout=3))
                self.assertFalse((Path(temp) / 'helix-orca-calibration/windows-access/bridge.sock').exists())
        with tempfile.TemporaryDirectory() as temp:
            process = self.start_server(Path(temp), connection='100.1.2.3 50000 192.168.1.114 22')
            self.assertEqual(1, process.wait(timeout=3))

    def test_real_private_socket_round_trip_preserves_identity_and_cleans_up(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, XDG_STATE_HOME=temp):
            root = Path(temp)
            process = self.start_server(root)
            path = self.wait_socket(root, process)
            self.assertEqual(0o600, path.stat().st_mode & 0o777)
            self.assertEqual(0o700, path.parent.stat().st_mode & 0o777)
            self.assertEqual(0o600, (path.parent / 'session.json').stat().st_mode & 0o777)
            def windows_peer():
                for op in ('exec', 'stop'):
                    request = bridge.read_message(process.stdout)
                    self.assertEqual(op, request['op'])
                    response = {'request_id': request['request_id'], 'exit_code': 0, 'stdout': 'visible-session'}
                    process.stdin.write(bridge.encode_message(response))
                    process.stdin.flush()
            peer = threading.Thread(target=windows_peer)
            peer.start()
            self.assertEqual('visible-session', bridge.request('exec', 'Write-Output "visible-session"')['stdout'])
            self.assertEqual(0, bridge.request('stop')['exit_code'])
            peer.join(timeout=3)
            self.assertFalse(peer.is_alive())
            self.assertEqual(0, process.wait(timeout=3))
            self.assertFalse(path.exists())
            self.assertFalse((path.parent / 'session.json').exists())
            audit = (path.parent / 'requests.jsonl').read_text()
            self.assertNotIn('Write-Output', audit)
            self.assertNotIn('visible-session', audit)

    def test_mismatched_response_terminates_session_instead_of_reusing_stale_result(self):
        with tempfile.TemporaryDirectory() as temp:
            process = self.start_server(Path(temp))
            path = self.wait_socket(Path(temp), process)
            with socket.socket(socket.AF_UNIX) as client:
                client.connect(str(path))
                client.sendall(bridge.encode_message({'op': 'probe'}))
                bridge.read_message(process.stdout)
                process.stdin.write(bridge.encode_message({'request_id': 'stale', 'exit_code': 0}))
                process.stdin.flush()
                self.assertEqual(1, process.wait(timeout=3))
                self.assertFalse(path.exists())

    def test_existing_worker_is_not_overwritten_by_second_connection(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = self.start_server(root)
            path = self.wait_socket(root, first)
            second = self.start_server(root)
            self.assertEqual(1, second.wait(timeout=3))
            self.assertTrue(path.exists())
            self.assertEqual(first.pid, json.loads((path.parent / 'session.json').read_text())['bridge_pid'])
            first.stdin.close()
            first.stdin = open(os.devnull, 'wb')
            self.assertEqual(1, first.wait(timeout=3))
            self.assertFalse(path.exists())

    def test_malformed_request_cannot_invoke_windows_command(self):
        with tempfile.TemporaryDirectory() as temp:
            process = self.start_server(Path(temp))
            path = self.wait_socket(Path(temp), process)
            with socket.socket(socket.AF_UNIX) as client:
                client.connect(str(path))
                client.sendall(bridge.encode_message({'op': 'unbounded-shell'}))
                result = bridge.read_message(client.makefile('rb'))
                self.assertIn('error', result)
            self.assertIsNone(process.poll())

    def test_prepare_is_idempotent_and_refuses_modified_frozen_payload(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(Path, 'home', return_value=Path(temp)):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                bridge.prepare()
            bundle = json.loads(output.getvalue())
            directory = Path(bundle['bundle_dir'])
            self.assertNotIn('__BRIDGE_PATH__', (directory / 'spare-access.ps1').read_text())
            with contextlib.redirect_stdout(io.StringIO()):
                bridge.prepare()
            target = directory / 'spare-access.ps1'
            target.chmod(0o600)
            target.write_text('altered')
            with self.assertRaisesRegex(ValueError, 'Frozen access bundle differs'):
                bridge.prepare()

    def test_bounds_reject_empty_script_oversized_input_and_invalid_timeout(self):
        for request in ({'op': 'exec', 'script': ''}, {'op': 'exec', 'script': 'x'*8193},
                        {'op': 'probe', 'timeout_seconds': 61}, {'op': 'probe', 'timeout_seconds': True}):
            with self.assertRaises(ValueError):
                bridge.validate_request(request)
        import io
        with self.assertRaises(ValueError):
            bridge.read_message(io.BytesIO(b'{"op":"probe"}'))
        with self.assertRaises(ValueError):
            bridge.encode_message({'script': 'x' * bridge.MAX_BYTES})


if __name__ == '__main__':
    unittest.main()
