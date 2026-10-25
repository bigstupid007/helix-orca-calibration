"""Bind a V2 build qualification to the generator bytes used at runtime."""
from __future__ import annotations

import hashlib
from pathlib import Path

from integration.v1_contract import (
    ContractError, digest, exact, hex_value, validate_build_qualification_v2,
)


SCHEMA = "helix-orca-v1-runtime-qualification-closure/v2"
REQUIRED_ADAPTER_LABELS = frozenset({
    "integration/v1_contract.py",
    "integration/v1_routing.py",
    "integration/v1_generation.py",
    "integration/v1_engine.py",
    "integration/v1_qualification.py",
    "integration/v1-native-engine/main.cpp",
    "scripts/v1-build-qualify.py",
})
PACKAGE_BINDING_KEY = "_runtime_qualification_package"


def _sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def _closure_items(values, label):
    if not isinstance(values, list):
        raise ContractError(label + " runtime closure must be a list")
    result = []
    seen = set()
    for item in values:
        exact(item, "label path size sha256", label + " runtime closure file")
        name = item["label"]
        if (not isinstance(name, str) or not name or len(name.encode("utf-8")) > 256
                or name in seen):
            raise ContractError("Duplicate or invalid " + label + " runtime closure label")
        seen.add(name)
        if type(item["size"]) is not int or not 0 < item["size"] <= 2 * 1024**3:
            raise ContractError(label + " runtime closure file size is invalid")
        expected = hex_value(item["sha256"])
        raw = Path(item["path"])
        if not raw.is_absolute():
            raise ContractError(label + " runtime closure path must be absolute")
        result.append({"label": name, "path": str(raw), "size": item["size"], "sha256": expected})
    result.sort(key=lambda item: item["label"])
    return result


def _verified_external_records(values, label):
    result = _closure_items(values, label)
    for item in result:
        raw = Path(item["path"])
        for candidate in (raw, *raw.parents):
            if candidate.is_symlink():
                raise ContractError(label + " runtime closure path must not use links")
        try:
            path = raw.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise ContractError(label + " runtime closure file is unavailable") from exc
        if (not path.is_file() or path.stat().st_size != item["size"]
                or _sha256(path) != item["sha256"]):
            raise ContractError(label + " runtime closure file differs: " + item["label"])
        item["path"] = str(path)
    return result


def _aggregate(result):
    public = [{"id": "file-%03d" % index, "sha256": item["sha256"], "size": item["size"]}
              for index, item in enumerate(result, 1)]
    return digest(public)


def _installed_adapter_records(values, package_root, package_manifest):
    records = _closure_items(values, "adapter")
    root = Path(package_root)
    try:
        root = root.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ContractError("Installed runtime package root is unavailable") from exc
    if not root.is_dir() or root.is_symlink():
        raise ContractError("Installed runtime package root is unsafe")
    exact(package_manifest, "schema candidate_sha256 files", "installed runtime manifest")
    if package_manifest["schema"] != "helix-orca-v1-runtime-manifest/v1":
        raise ContractError("Unknown installed runtime manifest schema")
    hex_value(package_manifest["candidate_sha256"])
    files = package_manifest["files"]
    if not isinstance(files, list):
        raise ContractError("Installed runtime manifest files must be a list")
    inventory = {}
    for item in files:
        exact(item, "path size sha256", "installed runtime file")
        relative = item["path"]
        if (not isinstance(relative, str) or not relative or "\\" in relative
                or relative.startswith("/") or any(part in ("", ".", "..") for part in relative.split("/"))
                or relative in inventory or type(item["size"]) is not int or item["size"] < 0):
            raise ContractError("Malformed installed runtime file inventory")
        inventory[relative] = {"size": item["size"], "sha256": hex_value(item["sha256"])}
    for record in records:
        entry = inventory.get(record["label"])
        if entry is None or entry != {"size": record["size"], "sha256": record["sha256"]}:
            raise ContractError("Installed package differs from qualified adapter: " + record["label"])
        target = root.joinpath(*record["label"].split("/"))
        try:
            target = target.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise ContractError("Installed qualified adapter is unavailable: " + record["label"]) from exc
        if (target.parent == root or root not in target.parents or target.is_symlink()
                or not target.is_file() or target.stat().st_size != record["size"]
                or _sha256(target) != record["sha256"]):
            raise ContractError("Installed qualified adapter differs: " + record["label"])
        record["path"] = str(target)
    return records


def runtime_build_qualification(config, package_root=None, package_manifest=None):
    """Rehash the configured executing closure and return its exact record.

    Absolute paths remain owner-private configuration. The public build record
    contains only the same deterministic size/hash projection produced by the
    Windows qualifier.
    """
    if not isinstance(config, dict):
        raise ContractError("Private generator configuration must be an object")
    qualification = validate_build_qualification_v2(config.get("build_qualification"))
    closure = config.get("qualification_closure")
    exact(closure, "schema adapter_files resource_files package_manifest_sha256",
          "runtime qualification closure")
    if closure["schema"] != SCHEMA:
        raise ContractError("Unknown runtime qualification closure schema")
    manifest = closure["package_manifest_sha256"]
    if manifest is not None:
        hex_value(manifest)
    binding = config.get(PACKAGE_BINDING_KEY)
    if package_root is None and package_manifest is None and isinstance(binding, dict):
        package_root, package_manifest = binding.get("root"), binding.get("manifest")
    if manifest is None:
        if package_root is not None or package_manifest is not None:
            raise ContractError("Source qualification closure cannot claim an installed package")
        adapter = _verified_external_records(closure["adapter_files"], "adapter")
    else:
        if package_root is None or package_manifest is None or digest(package_manifest) != manifest:
            raise ContractError("Runtime qualification closure differs from the installed package manifest")
        adapter = _installed_adapter_records(closure["adapter_files"], package_root, package_manifest)
    resources = _verified_external_records(closure["resource_files"], "resource")
    adapter_sha, resources_sha = _aggregate(adapter), _aggregate(resources)
    if not REQUIRED_ADAPTER_LABELS.issubset({item["label"] for item in adapter}):
        raise ContractError("Runtime qualification closure omits executing generator sources")
    if (adapter_sha != qualification["adapter"]["sha256"]
            or resources_sha != qualification["resources_sha256"]):
        raise ContractError("Runtime generator closure differs from build qualification")
    return qualification
