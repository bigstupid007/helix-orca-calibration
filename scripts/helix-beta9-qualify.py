#!/usr/bin/env python3
"""Qualify the pinned HelixScreen beta.9 developer artifact without a source build."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import zipfile


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("accepted_helix_dev", ROOT / "scripts/helix_dev.py")
accepted = importlib.util.module_from_spec(spec)
spec.loader.exec_module(accepted)

TAG = "v1.1.0-beta.9"
TAG_OBJECT = "cd9734ccd884784ac7f1aa07e2046b72de2d59e9"
SOURCE_COMMIT = "e5cdc5dc523280bc3ead681a4f229bf84dfa726a"
BUILD_RUN = 38685014257
ARTIFACT_ID = 11955517186
ARTIFACT_NAME = "helix-screen-ubuntu-22.04"
ARTIFACT_BYTES = 66705493
ARTIFACT_ARCHIVE_SHA256 = "494826250f5b38020a8a06673bc58cad3da9370f607523babf4163499b8c1ba1"
ARTIFACT_BINARY_SHA256 = "e21a5a8ce2c3a7dfcc21f56d3c19b2ba31528be00313929f671b66197e3e4704"
RELEASE_NAME = "helixscreen-x86-desktop-v1.1.0-beta.9.tar.gz"
RELEASE_URL = f"https://github.com/prestonbrown/helixscreen/releases/download/{TAG}/{RELEASE_NAME}"
RELEASE_SHA256 = "32303ccbad05bf1073cfafd6280fe08e264d838b28f03ca649425d54d7c59f97"


class QualificationError(RuntimeError):
    pass


def cache_root() -> Path:
    base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "helix-orca-calibration/helixscreen" / TAG


def state_root() -> Path:
    base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
    return base / "helix-orca-calibration/helix-beta9-qualification"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def gh() -> str:
    command = shutil.which(os.environ.get("HELIX_BETA9_GH", "gh-oss"))
    if not command:
        raise QualificationError("gh-oss is required to verify the pinned developer artifact")
    return command


def gh_json(endpoint: str) -> object:
    result = subprocess.run([gh(), "api", endpoint], check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def verify_upstream() -> dict[str, object]:
    ref = gh_json(f"repos/prestonbrown/helixscreen/git/ref/tags/{TAG}")
    obj = ref.get("object", {})
    if obj.get("sha") != TAG_OBJECT or obj.get("type") != "tag":
        raise QualificationError("beta.9 annotated-tag object changed")
    tag = gh_json(f"repos/prestonbrown/helixscreen/git/tags/{TAG_OBJECT}")
    target = tag.get("object", {})
    if target.get("sha") != SOURCE_COMMIT or target.get("type") != "commit":
        raise QualificationError("beta.9 source target changed")
    artifact = gh_json(f"repos/prestonbrown/helixscreen/actions/artifacts/{ARTIFACT_ID}")
    expected = {
        "id": ARTIFACT_ID,
        "name": ARTIFACT_NAME,
        "size_in_bytes": ARTIFACT_BYTES,
        "digest": "sha256:" + ARTIFACT_ARCHIVE_SHA256,
        "expired": False,
    }
    if any(artifact.get(key) != value for key, value in expected.items()):
        raise QualificationError("beta.9 developer artifact metadata changed or expired")
    run = artifact.get("workflow_run", {})
    if run.get("id") != BUILD_RUN or run.get("head_sha") != SOURCE_COMMIT:
        raise QualificationError("beta.9 developer artifact workflow provenance changed")
    return {**expected, "build_run": BUILD_RUN, "source_commit": SOURCE_COMMIT}


def safe_extract_zip(archive: Path, destination: Path) -> None:
    root = destination.resolve()
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            target = (destination / member.filename).resolve()
            if root not in (target, *target.parents):
                raise QualificationError(f"unsafe artifact path: {member.filename}")
        bundle.extractall(destination)


def safe_extract_tar(archive: Path, destination: Path) -> None:
    root = destination.resolve()
    with tarfile.open(archive, "r:gz") as bundle:
        for member in bundle.getmembers():
            target = (destination / member.name).resolve()
            if root not in (target, *target.parents):
                raise QualificationError(f"unsafe release path: {member.name}")
        bundle.extractall(destination)


def verify_cache(root: Path | None = None) -> dict[str, object]:
    root = root or cache_root()
    metadata_path = root / "metadata.json"
    binary = root / "binary/helix-screen"
    runtime = root / "runtime/helixscreen"
    required = (metadata_path, binary, runtime / "ui_xml/globals.xml", runtime / "config/settings.json.template")
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise QualificationError("beta.9 cache is incomplete: " + ", ".join(missing))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    expected = {
        "tag": TAG,
        "tag_object": TAG_OBJECT,
        "source_commit": SOURCE_COMMIT,
        "build_run": BUILD_RUN,
        "artifact_id": ARTIFACT_ID,
        "artifact_name": ARTIFACT_NAME,
        "artifact_archive_sha256": ARTIFACT_ARCHIVE_SHA256,
        "binary_sha256": ARTIFACT_BINARY_SHA256,
        "release_sha256": RELEASE_SHA256,
    }
    if any(metadata.get(key) != value for key, value in expected.items()):
        raise QualificationError("beta.9 cache metadata does not match exact pins")
    if sha256(binary) != ARTIFACT_BINARY_SHA256:
        raise QualificationError("beta.9 developer binary digest mismatch")
    return metadata


def bootstrap(refresh: bool) -> None:
    final = cache_root()
    if final.exists() and not refresh:
        verify_cache(final)
        print(f"Pinned beta.9 developer runtime is ready: {final}")
        return
    provenance = verify_upstream()
    final.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{TAG}-", dir=final.parent))
    try:
        artifact_zip = staging / "artifact.zip"
        with artifact_zip.open("wb") as output:
            subprocess.run(
                [gh(), "api", f"repos/prestonbrown/helixscreen/actions/artifacts/{ARTIFACT_ID}/zip"],
                check=True,
                stdout=output,
            )
        if artifact_zip.stat().st_size != ARTIFACT_BYTES or sha256(artifact_zip) != ARTIFACT_ARCHIVE_SHA256:
            raise QualificationError("downloaded beta.9 artifact archive digest/size mismatch")
        unpacked = staging / "unpacked"
        unpacked.mkdir()
        safe_extract_zip(artifact_zip, unpacked)
        matches = [path for path in unpacked.rglob("helix-screen") if path.is_file()]
        if len(matches) != 1 or sha256(matches[0]) != ARTIFACT_BINARY_SHA256:
            raise QualificationError("downloaded beta.9 developer binary mismatch")
        binary_dir = staging / "binary"
        binary_dir.mkdir()
        shutil.copy2(matches[0], binary_dir / "helix-screen")
        (binary_dir / "helix-screen").chmod(0o755)

        release = staging / RELEASE_NAME
        subprocess.run(["curl", "--fail", "--location", "--output", release, RELEASE_URL], check=True)
        if sha256(release) != RELEASE_SHA256:
            raise QualificationError("downloaded beta.9 release-data digest mismatch")
        runtime = staging / "runtime"
        runtime.mkdir()
        safe_extract_tar(release, runtime)
        metadata = {
            "artifact_archive_sha256": ARTIFACT_ARCHIVE_SHA256,
            "artifact_id": ARTIFACT_ID,
            "artifact_name": ARTIFACT_NAME,
            "binary_sha256": ARTIFACT_BINARY_SHA256,
            "build_run": BUILD_RUN,
            "release_sha256": RELEASE_SHA256,
            "source_commit": SOURCE_COMMIT,
            "tag": TAG,
            "tag_object": TAG_OBJECT,
            "upstream": provenance,
        }
        write_json(staging / "metadata.json", metadata)
        for path in (artifact_zip, release):
            path.unlink()
        shutil.rmtree(unpacked)
        verify_cache(staging)
        backup = None
        if final.exists():
            backup = final.with_name(final.name + ".previous-" + time.strftime("%Y%m%d-%H%M%S"))
            final.rename(backup)
        staging.rename(final)
        if backup:
            print(f"Previous beta.9 cache retained: {backup}")
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    print(f"Bootstrapped exact beta.9 developer runtime: {final}")


def configure_accepted_harness() -> None:
    root = cache_root()
    accepted.binary_path = lambda: root / "binary/helix-screen"
    accepted.runtime_path = lambda: root / "runtime/helixscreen"
    accepted.PLUGIN_ROOT = ROOT / "helix-plugin"
    accepted.PLUGIN_DIR = accepted.PLUGIN_ROOT / "orcacal"


def qualification_source_hashes() -> dict[str, str]:
    paths = (
        ROOT / "scripts/helix-beta9-qualify.py",
        ROOT / "scripts/helix_dev.py",
    )
    return {str(path.relative_to(ROOT)): sha256(path) for path in paths}


def capture_matrix(output: Path | None) -> None:
    metadata = verify_cache()
    image = accepted.image_metadata()
    configure_accepted_harness()
    root = output or state_root() / "captures" / time.strftime("%Y%m%d-%H%M%S")
    if root.exists():
        raise QualificationError(f"capture destination exists: {root}")
    root.mkdir(parents=True)
    before = accepted._plugin_hashes()
    rows = []
    try:
        for entry in accepted.VIEWPORTS:
            row = accepted.run_viewport(entry, root)
            rows.append(row)
            print(f"PASS {row['label']}: {row['viewport']}", flush=True)
    except Exception:
        write_json(root / "report.partial.json", {"results": rows})
        raise
    if accepted._plugin_hashes() != before:
        raise QualificationError("beta.9 capture changed accepted beta.4 plugin files")
    screenshots = {
        str(path.relative_to(root)): sha256(path) for path in sorted(root.rglob("*.png"))
    }
    report = {
        "accepted_plugin_files": before,
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "container_network": "none",
        "dependency_image": accepted.IMAGE,
        "dependency_image_id": image["id"],
        "qualification_sources": qualification_source_hashes(),
        "results": rows,
        "runtime": metadata,
        "screenshots": screenshots,
    }
    write_json(root / "report.json", report)
    verify_capture(root)
    print(f"Beta.9 native matrix retained at {root}")


def verify_capture(root: Path) -> None:
    configure_accepted_harness()
    report_path = root / "report.json"
    if not report_path.is_file():
        raise QualificationError("beta.9 capture report is missing")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("container_network") != "none" or report.get("runtime") != verify_cache():
        raise QualificationError("beta.9 report runtime/isolation mismatch")
    if report.get("qualification_sources") != qualification_source_hashes():
        raise QualificationError("beta.9 report qualification-source mismatch")
    if report.get("accepted_plugin_files") != accepted._plugin_hashes():
        raise QualificationError("beta.9 report accepted-plugin mismatch")
    rows = report.get("results", [])
    if len(rows) != len(accepted.VIEWPORTS):
        raise QualificationError("beta.9 report does not contain the eleven-target matrix")
    for row, entry in zip(rows, accepted.VIEWPORTS, strict=True):
        label, width, height, layout, dpi = entry
        if row != {
            "assertions": list(accepted.EXPECTED_ASSERTIONS),
            "dpi": dpi,
            "label": label,
            "layout": layout,
            "result": "PASS",
            "viewport": f"{width}x{height}",
        }:
            raise QualificationError(f"beta.9 matrix row mismatch: {label}")
    expected_count = len(accepted.VIEWPORTS) * len(accepted.CAPTURE_FRAME_NAMES)
    screenshots = report.get("screenshots", {})
    if len(screenshots) != expected_count:
        raise QualificationError("beta.9 report screenshot count mismatch")
    for relative, digest in screenshots.items():
        path = root / relative
        if not path.is_file() or sha256(path) != digest:
            raise QualificationError(f"beta.9 screenshot digest mismatch: {relative}")
    print("PASS: exact beta.9 developer artifact completed the accepted eleven-target matrix")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    bootstrap_parser = sub.add_parser("bootstrap")
    bootstrap_parser.add_argument("--refresh", action="store_true")
    capture_parser = sub.add_parser("capture")
    capture_parser.add_argument("--output", type=Path)
    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("capture", type=Path)
    args = parser.parse_args()
    if args.command == "bootstrap":
        bootstrap(args.refresh)
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
