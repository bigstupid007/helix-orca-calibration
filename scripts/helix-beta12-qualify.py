#!/usr/bin/env python3
"""Exact beta.12 runtime adapter with a durable source-build fallback.

The official desktop release supplies runtime data and installation evidence.
The native control-socket harness separately uses the exact short-lived Actions
binary or an exact-source build locked to all recursive submodule revisions.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile


ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "helix_beta12_qualification_base", ROOT / "scripts/helix-beta9-qualify.py"
)
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)

TAG = "v1.1.0-beta.12"
TAG_OBJECT = "ef1d5bb7bc9769d1abff11b39dcecd218fce2956"
SOURCE_COMMIT = "00a9fe6030c37d56748b2122b41fd36de1fdf831"
SOURCE_URL = "https://github.com/prestonbrown/helixscreen.git"
BUILD_RUN = 40062592022
ARTIFACT_ID = 12550514687
ARTIFACT_NAME = "helix-screen-ubuntu-22.04"
ARTIFACT_BYTES = 79546965
ARTIFACT_EXPIRES_AT = "2026-10-31T06:25:44Z"
ACTIONS_ARCHIVE_SHA256 = "c37ca065282a24de7b5f596a8f9d1fb64e133fea25a0b4472f56860b40785ae8"
ACTIONS_BINARY_SHA256 = "1ae6d052ec14d0148a300caaa049cb4b5ca8a5048390b9426814f48227adb04a"
RELEASE_ASSET_ID = 671432139
RELEASE_BYTES = 78801574
RELEASE_NAME = "helixscreen-x86-desktop-v1.1.0-beta.12.tar.gz"
RELEASE_URL = f"https://github.com/prestonbrown/helixscreen/releases/download/{TAG}/{RELEASE_NAME}"
RELEASE_SHA256 = "c87b12c8c6e884ac788fc28de326d9c4e1e19329531e758ac2ca65f12bbabee3"
RELEASE_BINARY_SHA256 = "3811d962d76d1d652602c5cc465fd7487db76bd1f00fceb343d10c52111a93db"

SUBMODULES = {
    "lib/cpp-terminal": "48ae2f284084850901c45b6c10a9d68949c1b272",
    "lib/glm": "a583c59e1616a628b18195869767ea4d6faca5f4",
    "lib/helix-xml": "f9720d27d0ba3b718a0b5f325bfbb829e913b167",
    "lib/libhv": "71770e04becaa149e0ef8ffc4d3900c5466ddddb",
    "lib/libjpeg-turbo": "c85e6b905bf237038faa936dab160ebfc5da0344",
    "lib/libnl": "bdf83151326e365f137fe0e36dc9b1b7aeb1cf33",
    "lib/linenoise": "452e3793858a15cc006bb3aa3ea06378eb98c5b5",
    "lib/lua": "312b9efaa1061c2c4cad08554dbc1351c3270eef",
    "lib/lv_i18n": "f6ac92ee2c31b57032fc6addc9aa15de2fee4568",
    "lib/lv_markdown": "77ec2c0c91614a50575a44c39d8db52c057ae681",
    "lib/lvgl": "85aa60d18b3d5e5588d7b247abf90198f07c8a63",
    "lib/sdl2": "5d249570393f7a37e037abf22cd6012a4cc56a71",
    "lib/spdlog": "14ab43ec0b9df6cf793c75785ec5f70b65f2f965",
    "lib/wpa_supplicant": "b5e326d24298ac52fba3c4e5ba5ae79780c78dc9",
}
RUNTIME_DOCKERFILE = ROOT / "scripts/helix-beta12-runtime.Dockerfile"
BUILDER_DOCKERFILE = ROOT / "scripts/helix-beta12-build.Dockerfile"
RUNTIME_IMAGE = f"helix-orca-calibration-beta12:{SOURCE_COMMIT[:12]}"
BUILDER_IMAGE = f"helix-orca-calibration-beta12-builder:{SOURCE_COMMIT[:12]}"
BUILDER_BASE = "ubuntu@sha256:5ec03bb3441e8b0bf3b4f9cd4629a1ae763010dc3035bb8da3ae6cf026486401"

QualificationError = _base.QualificationError
accepted = _base.accepted
sha256 = _base.sha256


def cache_root() -> Path:
    base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "helix-orca-calibration/helixscreen" / TAG


def state_root() -> Path:
    base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
    return base / "helix-orca-calibration/helix-beta12-qualification"


def gh() -> str:
    command = shutil.which(os.environ.get("HELIX_BETA12_GH", "gh-oss"))
    if not command:
        raise QualificationError("gh-oss is required to verify the pinned beta.12 artifact")
    return command


def qualification_source_hashes() -> dict[str, str]:
    paths = (
        ROOT / "scripts/helix-beta12-qualify.py",
        RUNTIME_DOCKERFILE,
        BUILDER_DOCKERFILE,
        ROOT / "scripts/helix-beta9-qualify.py",
        ROOT / "scripts/helix_dev.py",
    )
    return {str(path.relative_to(ROOT)): sha256(path) for path in paths}


def _configure_base() -> None:
    for name, value in {
        "TAG": TAG, "TAG_OBJECT": TAG_OBJECT, "SOURCE_COMMIT": SOURCE_COMMIT,
        "BUILD_RUN": BUILD_RUN, "ARTIFACT_ID": ARTIFACT_ID,
        "ARTIFACT_NAME": ARTIFACT_NAME, "ARTIFACT_BYTES": ARTIFACT_BYTES,
        "ARTIFACT_ARCHIVE_SHA256": ACTIONS_ARCHIVE_SHA256,
        "ARTIFACT_BINARY_SHA256": ACTIONS_BINARY_SHA256,
        "RELEASE_NAME": RELEASE_NAME, "RELEASE_URL": RELEASE_URL,
        "RELEASE_SHA256": RELEASE_SHA256,
    }.items():
        setattr(_base, name, value)
    _base.cache_root = cache_root
    _base.state_root = state_root
    _base.gh = gh
    _base.qualification_source_hashes = qualification_source_hashes
    _base.verify_cache = verify_cache
    _base.accepted.HELIX_SOURCE_COMMIT = SOURCE_COMMIT
    _base.accepted.DOCKERFILE = RUNTIME_DOCKERFILE
    _base.accepted.IMAGE = RUNTIME_IMAGE


def _run(argv: list[object], **kwargs: object) -> subprocess.CompletedProcess:
    return subprocess.run([os.fspath(item) for item in argv], check=True, text=True, **kwargs)


def _gh_json(endpoint: str) -> dict[str, object]:
    return json.loads(_run([gh(), "api", endpoint], capture_output=True).stdout)


def _verify_source_and_release() -> dict[str, object]:
    ref = _gh_json(f"repos/prestonbrown/helixscreen/git/ref/tags/{TAG}")
    if ref.get("object", {}).get("sha") != TAG_OBJECT or ref.get("object", {}).get("type") != "tag":
        raise QualificationError("beta.12 annotated-tag object changed")
    tag = _gh_json(f"repos/prestonbrown/helixscreen/git/tags/{TAG_OBJECT}")
    if tag.get("object", {}).get("sha") != SOURCE_COMMIT or tag.get("object", {}).get("type") != "commit":
        raise QualificationError("beta.12 source target changed")
    asset = _gh_json(f"repos/prestonbrown/helixscreen/releases/assets/{RELEASE_ASSET_ID}")
    expected = {"id": RELEASE_ASSET_ID, "name": RELEASE_NAME, "size": RELEASE_BYTES,
                "digest": "sha256:" + RELEASE_SHA256}
    if any(asset.get(key) != value for key, value in expected.items()):
        raise QualificationError("beta.12 desktop release asset metadata changed")
    return {**expected, "source_commit": SOURCE_COMMIT, "tag_object": TAG_OBJECT}


def _verify_actions() -> dict[str, object]:
    artifact = _gh_json(f"repos/prestonbrown/helixscreen/actions/artifacts/{ARTIFACT_ID}")
    expected = {
        "id": ARTIFACT_ID, "name": ARTIFACT_NAME,
        "size_in_bytes": ARTIFACT_BYTES, "digest": "sha256:" + ACTIONS_ARCHIVE_SHA256,
        "expired": False, "expires_at": ARTIFACT_EXPIRES_AT,
    }
    if any(artifact.get(key) != value for key, value in expected.items()):
        raise QualificationError("beta.12 developer artifact metadata changed or expired")
    run = artifact.get("workflow_run", {})
    if run.get("id") != BUILD_RUN or run.get("head_sha") != SOURCE_COMMIT:
        raise QualificationError("beta.12 developer artifact workflow provenance changed")
    return {**expected, "build_run": BUILD_RUN, "source_commit": SOURCE_COMMIT}


def verify_upstream() -> dict[str, object]:
    _configure_base()
    return {"stable": _verify_source_and_release(), "actions": _verify_actions()}


def _parse_submodules(source: Path) -> dict[str, str]:
    output = _run(["git", "-C", source, "submodule", "status", "--recursive"],
                  capture_output=True).stdout
    parsed: dict[str, str] = {}
    for line in output.splitlines():
        if not line or line[0] in "-+U":
            raise QualificationError("source has an uninitialized or mismatched submodule")
        fields = line[1:].split()
        if len(fields) < 2:
            raise QualificationError("malformed recursive submodule status")
        parsed[fields[1]] = fields[0]
    if parsed != SUBMODULES:
        raise QualificationError("beta.12 recursive submodule lock differs")
    return parsed


def _image_metadata(image: str, recipe: Path, label: str) -> dict[str, str]:
    result = subprocess.run(["docker", "image", "inspect", image],
                            capture_output=True, text=True)
    if result.returncode:
        raise QualificationError(f"Docker image {image} is missing")
    inspected = json.loads(result.stdout)[0]
    labels = inspected.get("Config", {}).get("Labels", {}) or {}
    if labels.get("org.helixscreen.source.commit") != SOURCE_COMMIT:
        raise QualificationError(f"{label} image source label mismatch")
    if labels.get(f"org.helixscreen.{label}.recipe.sha256") != sha256(recipe):
        raise QualificationError(f"{label} image recipe label mismatch")
    return {"id": inspected["Id"], "image": image}


def _build_image(image: str, recipe: Path, label: str) -> dict[str, str]:
    _run(["docker", "build", "--pull=false", "--label",
          f"org.helixscreen.{label}.recipe.sha256={sha256(recipe)}",
          "-f", recipe, "-t", image, recipe.parent])
    return _image_metadata(image, recipe, label)


def _ensure_runtime_image() -> dict[str, str]:
    try:
        return _image_metadata(RUNTIME_IMAGE, RUNTIME_DOCKERFILE, "runtime")
    except QualificationError:
        return _build_image(RUNTIME_IMAGE, RUNTIME_DOCKERFILE, "runtime")


def _install_actions_binary(staging: Path) -> dict[str, object]:
    upstream = _verify_actions()
    archive = staging / "developer-artifact.zip"
    with archive.open("wb") as output:
        subprocess.run([gh(), "api", f"repos/prestonbrown/helixscreen/actions/artifacts/{ARTIFACT_ID}/zip"],
                       check=True, stdout=output)
    if archive.stat().st_size != ARTIFACT_BYTES or sha256(archive) != ACTIONS_ARCHIVE_SHA256:
        raise QualificationError("downloaded beta.12 Actions archive differs")
    unpacked = staging / "artifact-unpacked"; unpacked.mkdir()
    _base.safe_extract_zip(archive, unpacked)
    matches = [path for path in unpacked.rglob("helix-screen") if path.is_file()]
    if len(matches) != 1 or sha256(matches[0]) != ACTIONS_BINARY_SHA256:
        raise QualificationError("downloaded beta.12 Actions binary differs")
    binary = staging / "binary"; binary.mkdir()
    shutil.copy2(matches[0], binary / "helix-screen"); (binary / "helix-screen").chmod(0o755)
    archive.unlink(); shutil.rmtree(unpacked)
    return {"kind": "actions-artifact", "artifact_id": ARTIFACT_ID,
            "artifact_name": ARTIFACT_NAME, "archive_sha256": ACTIONS_ARCHIVE_SHA256,
            "binary_sha256": ACTIONS_BINARY_SHA256, "build_run": BUILD_RUN,
            "expires_at": ARTIFACT_EXPIRES_AT, "upstream": upstream}


def _source_build_binary(staging: Path) -> dict[str, object]:
    builder = _build_image(BUILDER_IMAGE, BUILDER_DOCKERFILE, "builder")
    source = staging / "source"
    _run(["git", "init", source]); _run(["git", "-C", source, "remote", "add", "origin", SOURCE_URL])
    _run(["git", "-C", source, "fetch", "--depth", "1", "origin", SOURCE_COMMIT])
    _run(["git", "-C", source, "checkout", "--detach", SOURCE_COMMIT])
    _run(["git", "-C", source, "submodule", "update", "--init", "--recursive",
          "--jobs", "4", "--depth", "1"])
    head = _run(["git", "-C", source, "rev-parse", "HEAD"], capture_output=True).stdout.strip()
    if head != SOURCE_COMMIT:
        raise QualificationError("source checkout differs from beta.12 pin")
    submodules = _parse_submodules(source)
    jobs = max(1, int(os.environ.get("HELIX_BETA12_BUILD_JOBS", min(os.cpu_count() or 2, 8))))
    _run(["docker", "run", "--rm", "--user", f"{os.getuid()}:{os.getgid()}",
          "-e", "HOME=/source/.helix-build-home", "-e", "CC=clang", "-e", "CXX=clang++",
          "-e", "DBGLEVEL=0", "-e", "HELIX_PATCHES_FROM_CLEAN=1",
          "-e", f"HELIX_BUILD_JOBS={jobs}", "-v", f"{source}:/source", BUILDER_IMAGE,
          "bash", "-lc", 'mkdir -p "$HOME" && npm install --no-audit --no-fund '
          '&& make venv-setup && make -j"$HELIX_BUILD_JOBS"'])
    built = source / "build/bin/helix-screen"
    if not built.is_file():
        raise QualificationError("pinned beta.12 source build produced no helix-screen")
    binary = staging / "binary"; binary.mkdir()
    shutil.copy2(built, binary / "helix-screen"); (binary / "helix-screen").chmod(0o755)
    binary_hash = sha256(binary / "helix-screen"); shutil.rmtree(source)
    return {"kind": "source-build", "binary_sha256": binary_hash,
            "builder_base": BUILDER_BASE, "builder_dockerfile_sha256": sha256(BUILDER_DOCKERFILE),
            "builder_image": BUILDER_IMAGE, "builder_image_id": builder["id"],
            "build_jobs": jobs, "source_url": SOURCE_URL, "submodules": submodules}


def _install_release(staging: Path) -> None:
    archive = staging / RELEASE_NAME
    _run(["curl", "--fail", "--location", "--output", archive, RELEASE_URL])
    if archive.stat().st_size != RELEASE_BYTES or sha256(archive) != RELEASE_SHA256:
        raise QualificationError("downloaded beta.12 desktop archive differs")
    runtime = staging / "runtime"; runtime.mkdir(); _base.safe_extract_tar(archive, runtime)
    shipped = runtime / "helixscreen/bin/helix-screen"
    if not shipped.is_file() or sha256(shipped) != RELEASE_BINARY_SHA256:
        raise QualificationError("downloaded beta.12 release binary differs")
    archive.unlink()


def validate_metadata(metadata: object) -> dict[str, object]:
    if not isinstance(metadata, dict):
        raise QualificationError("beta.12 metadata is not an object")
    exact = {"tag": TAG, "tag_object": TAG_OBJECT, "source_commit": SOURCE_COMMIT,
             "release_asset_id": RELEASE_ASSET_ID, "release_name": RELEASE_NAME,
             "release_sha256": RELEASE_SHA256, "release_binary_sha256": RELEASE_BINARY_SHA256}
    if any(metadata.get(key) != value for key, value in exact.items()):
        raise QualificationError("beta.12 metadata differs from stable pins")
    binary_hash = metadata.get("binary_sha256"); origin = metadata.get("binary_origin")
    if not isinstance(binary_hash, str) or len(binary_hash) != 64 or not isinstance(origin, dict):
        raise QualificationError("beta.12 harness binary provenance is malformed")
    if origin.get("binary_sha256") != binary_hash:
        raise QualificationError("beta.12 harness binary/origin digests differ")
    if origin.get("kind") == "actions-artifact":
        values = {"artifact_id": ARTIFACT_ID, "artifact_name": ARTIFACT_NAME,
                  "archive_sha256": ACTIONS_ARCHIVE_SHA256, "binary_sha256": ACTIONS_BINARY_SHA256,
                  "build_run": BUILD_RUN, "expires_at": ARTIFACT_EXPIRES_AT}
        if binary_hash != ACTIONS_BINARY_SHA256 or any(origin.get(k) != v for k, v in values.items()):
            raise QualificationError("beta.12 Actions harness provenance differs")
    elif origin.get("kind") == "source-build":
        values = {"builder_base": BUILDER_BASE,
                  "builder_dockerfile_sha256": sha256(BUILDER_DOCKERFILE),
                  "builder_image": BUILDER_IMAGE, "source_url": SOURCE_URL,
                  "submodules": SUBMODULES}
        if any(origin.get(k) != v for k, v in values.items()):
            raise QualificationError("beta.12 source-build provenance differs")
        if binary_hash in (ACTIONS_BINARY_SHA256, RELEASE_BINARY_SHA256):
            raise QualificationError("source-build origin claims a prebuilt digest")
    else:
        raise QualificationError("unknown beta.12 harness binary origin")
    return metadata


def verify_cache(root: Path | None = None) -> dict[str, object]:
    _configure_base(); root = root or cache_root()
    metadata_path = root / "metadata.json"; binary = root / "binary/helix-screen"
    runtime = root / "runtime/helixscreen"
    required = (metadata_path, binary, runtime / "bin/helix-screen",
                runtime / "ui_xml/globals.xml", runtime / "config/settings.json.template")
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise QualificationError("beta.12 cache is incomplete: " + ", ".join(missing))
    metadata = validate_metadata(json.loads(metadata_path.read_text(encoding="utf-8")))
    if sha256(binary) != metadata["binary_sha256"]:
        raise QualificationError("beta.12 harness binary digest mismatch")
    if sha256(runtime / "bin/helix-screen") != RELEASE_BINARY_SHA256:
        raise QualificationError("beta.12 official release binary digest mismatch")
    return metadata


def bootstrap(refresh: bool = False, from_source: bool = False) -> None:
    _configure_base(); final = cache_root()
    if from_source and final.exists() and not refresh:
        raise QualificationError("--from-source requires --refresh for an existing cache")
    if final.exists() and not refresh:
        metadata = verify_cache(final); _ensure_runtime_image()
        print(f"Pinned beta.12 runtime is ready: {final} ({metadata['binary_origin']['kind']})")
        return
    stable = _verify_source_and_release()
    final.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{TAG}-", dir=final.parent))
    try:
        if from_source:
            origin = _source_build_binary(staging)
        else:
            try:
                origin = _install_actions_binary(staging)
            except (QualificationError, subprocess.SubprocessError, zipfile.BadZipFile) as exc:
                print(f"Pinned Actions accelerator unavailable ({exc}); building exact source.", file=sys.stderr)
                for transient in (staging / "developer-artifact.zip", staging / "artifact-unpacked"):
                    if transient.is_dir(): shutil.rmtree(transient)
                    elif transient.exists(): transient.unlink()
                origin = _source_build_binary(staging)
        _install_release(staging)
        metadata = {"tag": TAG, "tag_object": TAG_OBJECT, "source_commit": SOURCE_COMMIT,
                    "release_asset_id": RELEASE_ASSET_ID, "release_name": RELEASE_NAME,
                    "release_sha256": RELEASE_SHA256,
                    "release_binary_sha256": RELEASE_BINARY_SHA256,
                    "binary_sha256": sha256(staging / "binary/helix-screen"),
                    "binary_origin": origin, "upstream": stable}
        _base.write_json(staging / "metadata.json", metadata)
        verify_cache(staging)
        backup = None
        if final.exists():
            backup = final.with_name(final.name + ".previous-" + time.strftime("%Y%m%d-%H%M%S"))
            final.rename(backup)
        staging.rename(final)
        if backup: print(f"Previous beta.12 cache retained: {backup}")
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    _ensure_runtime_image()
    print(f"Bootstrapped exact beta.12 runtime: {final} ({origin['kind']})")


def configure_accepted_harness() -> None:
    _configure_base()
    _base.configure_accepted_harness()


def capture_matrix(output: Path | None = None) -> None:
    _configure_base()
    _base.capture_matrix(output)


def verify_capture(root: Path) -> None:
    _configure_base()
    _base.verify_capture(root)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    bootstrap_parser = sub.add_parser("bootstrap")
    bootstrap_parser.add_argument("--refresh", action="store_true")
    bootstrap_parser.add_argument("--from-source", action="store_true")
    capture_parser = sub.add_parser("capture")
    capture_parser.add_argument("--output", type=Path)
    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("capture", type=Path)
    args = parser.parse_args()
    if args.command == "bootstrap":
        bootstrap(args.refresh, args.from_source)
    elif args.command == "capture":
        capture_matrix(args.output)
    else:
        verify_capture(args.capture)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (QualificationError, OSError, subprocess.SubprocessError, zipfile.BadZipFile) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
