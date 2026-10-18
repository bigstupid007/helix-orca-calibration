"""Explicit local deployment gate; the review program never creates a grant.

Only the local launcher can supply this path. Native events and profile data
cannot name it or enable actions. The owner-private launcher/storage envelope
is required; this record is not a cryptographic authorization service.
"""
from pathlib import Path
import hashlib

from integration.v1_contract import ContractError, digest, exact, hex_value, text
from integration.v1_runtime import read_json
from integration.v1_private_file import private_file


def authorized(path, config, entry):
    if path is None:
        return False
    path = private_file(path)
    if not 0 < path.stat().st_size <= 65536:
        raise ContractError("Local deployment authorization must contain 1..65536 bytes")
    value = read_json(path)
    exact(value, "schema approved native_start_only approval_reference config_sha256 runtime_sha256", "local deployment authorization")
    if value["schema"] != "helix-orca-v1-local-deployment/v1" or value["approved"] is not True or value["native_start_only"] is not True:
        raise ContractError("Explicit separately approved native-Start-only deployment required")
    text(value["approval_reference"], "deployment approval reference", 512)
    if hex_value(value["config_sha256"]) != digest(config) or hex_value(value["runtime_sha256"]) != runtime_fingerprint(entry):
        raise ContractError("Deployment authorization does not bind this exact configuration and runtime")
    return True


def require_native_channel(config, enabled):
    """An active job target must be the same pinned native Helix event target."""
    if enabled is not True:
        raise ContractError("Owned jobs require the explicit native event channel")
    event = config.get("moonraker", {})
    job = config.get("owned_jobs", {})
    if any(event.get(k) != job.get(k) for k in ("expected_host", "expected_version")) or not isinstance(event.get("origin"), str) or event["origin"].rstrip("/") != str(job.get("origin", "")).rstrip("/"):
        raise ContractError("Native event and owned-job printer targets differ")


def runtime_fingerprint(entry):
    """Bind the CLI and its local V1 Python code, not only its thin entry point."""
    entry = Path(entry)
    root = entry.parent.parent
    paths = {entry}
    paths.update((root / "integration").glob("v1_*.py"))
    websocket = root / "scripts" / "helix-display-request.py"
    if websocket.is_file():
        paths.add(websocket)
    return digest({str(path.relative_to(root).as_posix()): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(paths)})
