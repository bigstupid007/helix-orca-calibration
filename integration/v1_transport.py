"""V1 event/storage transport: no printer command, upload or test-worker route.

Uses the previously verified trusted-LAN origin and exact single-file bridge.
Activation is intentionally separate from building this module.
"""
import importlib.util
import ipaddress
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, ProxyHandler, HTTPRedirectHandler, build_opener

from integration.v1_contract import ContractError, canonical


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_):
        return None


class MoonrakerEvents:
    EVENTS = frozenset(("helix_orca_v1.context.v1", "helix_orca_v1.status.v1", "helix_orca_v1.ack.v1",
                        "helix_orca_v1.context.v2", "helix_orca_v1.status.v2", "helix_orca_v1.ack.v2",
                        "helix_orca_v1.warning.v2", "helix_orca_v1.application.v2",
                        "helix_orca_v1.retired.v1", "helix_orca_v1.retired.v2"))
    STORAGE = "/server/files/config/helixscreen/plugin-data/orcacal.json"

    def __init__(self, origin, expected_host, expected_version, api_key=None, *, trusted_lan=False):
        parsed = urlparse(origin)
        address = ipaddress.ip_address(expected_host)
        private = any(address in ipaddress.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"))
        if not trusted_lan or not private or parsed.scheme != "http" or parsed.hostname != expected_host or parsed.path not in ("", "/") or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ContractError("Only explicitly acknowledged existing private-LAN HTTP origin is supported")
        self.origin = origin.rstrip("/")
        self.host, self.port = expected_host, parsed.port or 80
        self.version, self.api_key = expected_version, api_key
        self.opener = build_opener(ProxyHandler({}), NoRedirect())
        # Reuse bounded wire framing, never its print/display command utilities.
        path = Path(__file__).resolve().parents[1] / "scripts/helix-display-request.py"
        spec = importlib.util.spec_from_file_location("v1_ws_framing", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.websocket = module.WebSocket

    def _get(self, path):
        if path not in (self.STORAGE, "/server/info"):
            raise ContractError("GET path outside allowlist")
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["X-Api-Key"] = self.api_key
        try:
            with self.opener.open(Request(self.origin + path, headers=headers), timeout=5) as response:
                data = response.read(1048577)
        except HTTPError as exc:
            # Helix creates the per-plugin storage file only after the first
            # persisted native session.  Before then, its exact Moonraker file
            # URL is a normal 404 and means "no native request yet".  Auth and
            # every other HTTP error remain failures.
            if path == self.STORAGE and exc.code == 404:
                return {}
            raise
        if len(data) > 1048576:
            raise ContractError("Native storage exceeds bound")
        value = json.loads(data)
        canonical(value)
        return value

    def assert_identity(self):
        info = self._get("/server/info").get("result", {})
        if info.get("moonraker_version") != self.version or info.get("klippy_state") != "ready":
            raise ContractError("Pinned Moonraker identity/readiness differs")

    def read(self):
        self.assert_identity()
        return self._get(self.STORAGE).get("v1_session", {})

    def send(self, event, value):
        if event not in self.EVENTS:
            raise ContractError("Event outside V1 namespace")
        self.assert_identity()
        connection = self.websocket(self.host, self.port, "/websocket")
        try:
            identify = dict(client_name="helix-orca-v1", version="1.0.0-candidate", type="agent",
                            url="https://github.com/bigstupid007/helix-orca-calibration/issues/14")
            if self.api_key:
                identify["api_key"] = self.api_key
            for request_id, method, params in ((1, "server.connection.identify", identify),
                    (2, "connection.send_event", dict(event=event, data=value))):
                connection.send_frame(1, canonical(dict(jsonrpc="2.0", id=request_id, method=method, params=params)))
                for _ in range(17):
                    reply = connection.receive_json()
                    if isinstance(reply, dict) and reply.get("id") == request_id:
                        if "error" in reply or (request_id == 2 and reply.get("result") != "ok"):
                            raise ContractError("V1 event rejected")
                        break
                else:
                    raise ContractError("V1 response exceeded bounded frame count")
        finally:
            connection.close()


class DirectoryEvents:
    """Explicit offline adapter; it cannot send a network or printer command."""
    def __init__(self, directory):
        self.directory = Path(directory)

    def read(self):
        from integration.v1_runtime import read_json
        path = self.directory / "native.json"
        return read_json(path) if path.exists() else {}

    def send(self, event, value):
        from integration.v1_runtime import atomic_json
        if event not in MoonrakerEvents.EVENTS:
            raise ContractError("Event outside V1 namespace")
        atomic_json(self.directory / (event.split(".")[1] + ".json"), value)
