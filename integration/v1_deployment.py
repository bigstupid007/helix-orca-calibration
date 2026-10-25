"""Explicit local deployment gate; the review program never creates a grant.

Only the local launcher can supply this path. Native events and profile data
cannot name it or enable actions. The owner-private launcher/storage envelope
is required; this record is not a cryptographic authorization service.
"""
from pathlib import Path
import hashlib
import re

from integration.v1_contract import ContractError, digest, exact, hex_value, text
from integration.v1_runtime import read_json
from integration.v1_private_file import private_file


MANIFEST_SCHEMA = "helix-orca-v1-runtime-manifest/v1"
SAFE_PART = re.compile(r"[A-Za-z0-9_.-]+")


def _file_sha256(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def runtime_manifest(entry):
    """Verify an immutable installed package manifest and every listed byte.

    Source-checkout review remains supported when no manifest exists. Installed
    candidates place ``runtime-manifest.json`` at the package root, two levels
    above ``scripts/v1-runtime.py``.
    """
    entry = Path(entry)
    root = entry.parent.parent
    path = root / "runtime-manifest.json"
    if not path.is_file():
        return None
    if path.is_symlink() or root.is_symlink() or path.stat().st_size > 1_048_576:
        raise ContractError("Installed runtime manifest path is unsafe")
    value = read_json(path)
    exact(value, "schema candidate_sha256 files", "installed runtime manifest")
    if value["schema"] != MANIFEST_SCHEMA:
        raise ContractError("Unknown installed runtime manifest schema")
    hex_value(value["candidate_sha256"])
    files = value["files"]
    if not isinstance(files, list) or not 1 <= len(files) <= 4096:
        raise ContractError("Installed runtime manifest file inventory unavailable")
    seen, hashes = set(), {}
    for item in files:
        exact(item, "path size sha256", "installed runtime file")
        relative = item["path"]
        if (not isinstance(relative, str) or not relative or "\\" in relative
                or relative.startswith("/") or any(not SAFE_PART.fullmatch(part)
                for part in relative.split("/")) or ".." in relative.split("/")):
            raise ContractError("Unsafe installed runtime relative path")
        if relative in seen or type(item["size"]) is not int or not 0 <= item["size"] <= 500_000_000:
            raise ContractError("Malformed installed runtime file inventory")
        seen.add(relative)
        expected = hex_value(item["sha256"])
        target = root.joinpath(*relative.split("/"))
        if target.is_symlink() or not target.is_file() or target.stat().st_size != item["size"]:
            raise ContractError("Installed runtime file is missing or changed")
        actual = _file_sha256(target)
        if actual != expected:
            raise ContractError("Installed runtime file hash differs")
        hashes[relative] = actual
    actual_files = set()
    for target in root.rglob("*"):
        if target.is_symlink():
            raise ContractError("Installed runtime contains a symlink")
        if target.is_file() and target != path:
            actual_files.add(target.relative_to(root).as_posix())
    if actual_files != seen:
        raise ContractError("Installed runtime contains unlisted or missing files")
    entry_relative = entry.relative_to(root).as_posix()
    if entry_relative not in seen:
        raise ContractError("Installed runtime manifest omits its entry point")
    return value


def runtime_manifest_fingerprint(entry):
    value = runtime_manifest(entry)
    return digest(value) if value is not None else None


def authorized(path, config, entry):
    if path is None:
        return False
    path = private_file(path)
    if not 0 < path.stat().st_size <= 65536:
        raise ContractError("Local deployment authorization must contain 1..65536 bytes")
    value = read_json(path)
    schema = value.get("schema") if isinstance(value, dict) else None
    fields = ("schema approved native_start_only approval_reference config_sha256 runtime_sha256 "
              "package_manifest_sha256" if schema == "helix-orca-v1-local-deployment/v2" else
              "schema approved native_start_only approval_reference config_sha256 runtime_sha256")
    exact(value, fields, "local deployment authorization")
    if schema not in ("helix-orca-v1-local-deployment/v1", "helix-orca-v1-local-deployment/v2") or value["approved"] is not True or value["native_start_only"] is not True:
        raise ContractError("Explicit separately approved native-Start-only deployment required")
    text(value["approval_reference"], "deployment approval reference", 512)
    if hex_value(value["config_sha256"]) != digest(config) or hex_value(value["runtime_sha256"]) != runtime_fingerprint(entry):
        raise ContractError("Deployment authorization does not bind this exact configuration and runtime")
    manifest = runtime_manifest_fingerprint(entry)
    if schema == "helix-orca-v1-local-deployment/v2":
        if manifest is None or hex_value(value["package_manifest_sha256"]) != manifest:
            raise ContractError("Deployment authorization does not bind the installed package manifest")
    elif manifest is not None:
        raise ContractError("Installed runtime requires package-bound deployment authorization v2")
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
    """Bind source closure, or the complete immutable installed manifest."""
    entry = Path(entry)
    manifest = runtime_manifest(entry)
    if manifest is not None:
        return digest(dict(candidate_sha256=manifest["candidate_sha256"],
                           manifest_sha256=digest(manifest)))
    root = entry.parent.parent
    paths = {entry}
    paths.update((root / "integration").glob("v1_*.py"))
    websocket = root / "scripts" / "helix-display-request.py"
    if websocket.is_file():
        paths.add(websocket)
    return digest({str(path.relative_to(root).as_posix()): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(paths)})
