#!/usr/bin/env python3
"""Pinned native HelixScreen beta.4 mock-printer development harness."""

from __future__ import annotations

import argparse
import hashlib
import http.server
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
from typing import Any, Iterable
import urllib.error
import urllib.request
import zipfile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = PROJECT_ROOT / "helix-plugin"
PLUGIN_DIR = PLUGIN_ROOT / "orcacal"
DOCKERFILE = PROJECT_ROOT / "scripts" / "helix-dev.Dockerfile"
BUILDER_DOCKERFILE = PROJECT_ROOT / "scripts" / "helix-dev-build.Dockerfile"

HELIX_TAG = "v1.1.0-beta.4"
HELIX_TAG_OBJECT = "daaf181197b82c795721b06bc7db55f6219fc258"
HELIX_SOURCE_COMMIT = "13a77bec42616d5c6f4fa397f1d5e12682fa4376"
HELIX_BUILD_RUN = 37385776288
HELIX_ARTIFACT_ID = 11381944255
HELIX_ARTIFACT_NAME = "helix-screen-ubuntu-22.04"
HELIX_ARTIFACT_EXPIRES_AT = "2026-10-13T00:24:45Z"
HELIX_ARTIFACT_BINARY_SHA256 = (
    "ab819714fd469ff32657dc974585ad3bb05270829247da08eb71161a2d5197d0"
)
HELIX_SOURCE_URL = "https://github.com/prestonbrown/helixscreen.git"
HELIX_SUBMODULE_COUNT = 14
HELIX_RELEASE_URL = (
    "https://github.com/prestonbrown/helixscreen/releases/download/"
    f"{HELIX_TAG}/helixscreen-x86-{HELIX_TAG}.tar.gz"
)
HELIX_RELEASE_SHA256 = "a0a618c2ab233e61324ec1024448571b160a8bd65b22b0387007017f4dc21b94"

IMAGE = f"helix-orca-calibration-beta4:{HELIX_SOURCE_COMMIT[:12]}"
BUILDER_IMAGE = f"helix-orca-calibration-beta4-builder:{HELIX_SOURCE_COMMIT[:12]}"
CONTAINER = "helix-orca-dev"
REVIEW_BIND = "0.0.0.0"
REVIEW_HOST = "192.168.1.114"
REVIEW_PORT = 8540

VIEWPORTS = (
    ("micro_480x272", 480, 272, "standard", 160),
    ("micro_portrait_272x480", 272, 480, "portrait", 160),
    ("tiny_480x320", 480, 320, "standard", 160),
    ("small_480x400", 480, 400, "standard", 160),
    ("medium_800x480", 800, 480, "standard", 160),
    ("portrait_480x800", 480, 800, "portrait", 160),
    ("large_1024x600", 1024, 600, "standard", 160),
    ("xlarge_1280x720", 1280, 720, "standard", 160),
    ("phone_1080x2400_dpi405", 1080, 2400, "portrait", 405),
    ("ultrawide_1920x480", 1920, 480, "ultrawide", 160),
    ("tall_320x1480", 320, 1480, "portrait", 160),
)
CAPTURE_FRAME_NAMES = ("home.png", "chooser.png", "temperature.png", "start-toast.png")
EXPECTED_ASSERTIONS = (
    "plugin-loaded",
    "landing-home",
    "tile-visible",
    "tile-native-tap-opens-chooser",
    "chooser-native-back",
    "chooser-horizontal-fit",
    "chooser-native-tap-opens-temperature",
    "temperature-native-back",
    "temperature-horizontal-fit",
    "start-visible",
    "start-native-tap-toast",
    "back-to-chooser",
    "back-to-home",
    "home-action-keeps-tile-visible",
    "tile-native-tap-reopens",
)
BETA4_DEFAULT_HOME_WIDGETS = (
    "printer_image",
    "print_status",
    "led",
    "fan_stack",
    "temperature",
    "bed_temperature",
    "filament",
    "tips",
    "notifications",
)
BETA4_MOCK_ACKNOWLEDGED_HARDWARE = (
    "neopixel chamber_light",
    "fan_generic nevermore",
    "controller_fan controller_fan",
    "filament_switch_sensor runout_sensor",
)


class HarnessError(RuntimeError):
    """An actionable harness failure."""


def cache_root() -> Path:
    base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "helix-orca-calibration" / "helixscreen" / HELIX_TAG


def state_root() -> Path:
    base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return base / "helix-orca-calibration" / "helix-dev"


def binary_path() -> Path:
    return cache_root() / "binary" / "helix-screen"


def runtime_path() -> Path:
    return cache_root() / "runtime" / "helixscreen"


def run(
    argv: Iterable[str | os.PathLike[str]],
    *,
    check: bool = True,
    capture: bool = False,
    stdout: Any = None,
    timeout: float | None = None,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    args = [os.fspath(item) for item in argv]
    kwargs: dict[str, Any] = {
        "check": check,
        "text": True,
        "timeout": timeout,
        "cwd": cwd,
        "env": env,
    }
    if capture:
        kwargs.update(stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    elif stdout is not None:
        kwargs["stdout"] = stdout
        kwargs["text"] = False
    return subprocess.run(args, **kwargs)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _safe_extract_tar(archive: Path, destination: Path) -> None:
    destination_resolved = destination.resolve()
    with tarfile.open(archive, "r:gz") as bundle:
        for member in bundle.getmembers():
            target = (destination / member.name).resolve()
            if destination_resolved not in (target, *target.parents):
                raise HarnessError(f"release archive contains unsafe path: {member.name}")
        bundle.extractall(destination)


def _safe_extract_zip(archive: Path, destination: Path) -> None:
    destination_resolved = destination.resolve()
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            target = (destination / member.filename).resolve()
            if destination_resolved not in (target, *target.parents):
                raise HarnessError(f"artifact archive contains unsafe path: {member.filename}")
        bundle.extractall(destination)


def _gh_command() -> str:
    requested = os.environ.get("HELIX_DEV_GH")
    if requested:
        resolved = shutil.which(requested)
        if not resolved:
            raise HarnessError(f"HELIX_DEV_GH command not found: {requested}")
        return resolved
    for candidate in ("gh-oss", "gh"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise HarnessError("GitHub CLI is required to verify the pinned source tag (gh-oss or gh)")


def _gh_json(endpoint: str) -> Any:
    result = run([_gh_command(), "api", endpoint], capture=True)
    return json.loads(result.stdout)


def verify_source_pin() -> None:
    ref = _gh_json(f"repos/prestonbrown/helixscreen/git/ref/tags/{HELIX_TAG}")
    obj = ref.get("object", {})
    if obj.get("type") != "tag" or obj.get("sha") != HELIX_TAG_OBJECT:
        raise HarnessError(
            f"upstream tag object mismatch: expected {HELIX_TAG_OBJECT}, got {obj.get('sha')}"
        )
    tag = _gh_json(f"repos/prestonbrown/helixscreen/git/tags/{HELIX_TAG_OBJECT}")
    target = tag.get("object", {})
    if target.get("type") != "commit" or target.get("sha") != HELIX_SOURCE_COMMIT:
        raise HarnessError(
            f"upstream source mismatch: expected {HELIX_SOURCE_COMMIT}, got {target.get('sha')}"
        )


def verify_assets(root: Path | None = None) -> dict[str, Any]:
    root = root or cache_root()
    binary = root / "binary" / "helix-screen"
    runtime = root / "runtime" / "helixscreen"
    required = (
        binary,
        runtime / "ui_xml" / "globals.xml",
        runtime / "config" / "settings.json.template",
        runtime / "assets" / "filaments.json",
        root / "metadata.json",
    )
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise HarnessError("pinned runtime is incomplete; run bootstrap:\n  " + "\n  ".join(missing))
    metadata = json.loads((root / "metadata.json").read_text(encoding="utf-8"))
    if (
        metadata.get("tag") != HELIX_TAG
        or metadata.get("tag_object") != HELIX_TAG_OBJECT
        or metadata.get("source_commit") != HELIX_SOURCE_COMMIT
    ):
        raise HarnessError("cached source pin does not match this harness; run bootstrap --refresh")
    if metadata.get("release_archive_sha256") != HELIX_RELEASE_SHA256:
        raise HarnessError("cached release-data pin does not match this harness; run bootstrap --refresh")
    expected_binary = metadata.get("binary_sha256")
    actual = sha256(binary)
    if not isinstance(expected_binary, str) or len(expected_binary) != 64 or actual != expected_binary:
        raise HarnessError(
            f"developer binary SHA-256 mismatch: expected {expected_binary}, got {actual}"
        )
    origin = metadata.get("binary_origin", {})
    kind = origin.get("kind") if isinstance(origin, dict) else None
    if kind == "actions-artifact":
        expected_origin = {
            "artifact_id": HELIX_ARTIFACT_ID,
            "artifact_name": HELIX_ARTIFACT_NAME,
            "build_run": HELIX_BUILD_RUN,
            "expires_at": HELIX_ARTIFACT_EXPIRES_AT,
            "kind": "actions-artifact",
        }
        if origin != expected_origin or expected_binary != HELIX_ARTIFACT_BINARY_SHA256:
            raise HarnessError("cached Actions binary does not match the pinned artifact SHA-256")
    elif kind == "source-build":
        expected_recipe = sha256(BUILDER_DOCKERFILE)
        if (
            origin.get("builder_dockerfile_sha256") != expected_recipe
            or origin.get("builder_image") != BUILDER_IMAGE
            or origin.get("source_url") != HELIX_SOURCE_URL
        ):
            raise HarnessError("source-build recipe changed; run bootstrap --refresh --from-source")
        submodules = origin.get("submodules")
        if not isinstance(submodules, list) or len(submodules) != HELIX_SUBMODULE_COUNT:
            raise HarnessError("source-build metadata is missing pinned submodule revisions")
    else:
        raise HarnessError("cached binary origin is unknown; run bootstrap --refresh")
    return metadata


def image_metadata() -> dict[str, str]:
    result = run(["docker", "image", "inspect", IMAGE], capture=True, check=False)
    if result.returncode:
        raise HarnessError(f"runtime image {IMAGE} is missing; run bootstrap")
    inspected = json.loads(result.stdout)[0]
    labels = inspected.get("Config", {}).get("Labels", {}) or {}
    if labels.get("org.helixscreen.source.commit") != HELIX_SOURCE_COMMIT:
        raise HarnessError("runtime image source label mismatch; run bootstrap --refresh")
    if labels.get("org.helixscreen.runtime.recipe.sha256") != sha256(DOCKERFILE):
        raise HarnessError("runtime image recipe mismatch; run bootstrap")
    return {"id": inspected["Id"], "repo_digest": next(iter(inspected.get("RepoDigests") or []), "")}


def build_image() -> None:
    run(
        [
            "docker",
            "build",
            "--pull=false",
            "--label",
            f"org.helixscreen.runtime.recipe.sha256={sha256(DOCKERFILE)}",
            "-f",
            DOCKERFILE,
            "-t",
            IMAGE,
            DOCKERFILE.parent,
        ]
    )
    image_metadata()


def _builder_image_metadata() -> dict[str, str]:
    result = run(["docker", "image", "inspect", BUILDER_IMAGE], capture=True, check=False)
    if result.returncode:
        raise HarnessError(f"builder image {BUILDER_IMAGE} is missing")
    inspected = json.loads(result.stdout)[0]
    labels = inspected.get("Config", {}).get("Labels", {}) or {}
    if labels.get("org.helixscreen.source.commit") != HELIX_SOURCE_COMMIT:
        raise HarnessError("builder image source label mismatch")
    if labels.get("org.helixscreen.builder.recipe.sha256") != sha256(BUILDER_DOCKERFILE):
        raise HarnessError("builder image recipe mismatch")
    return {"id": inspected["Id"]}


def verify_source_builder(metadata: dict[str, Any]) -> None:
    origin = metadata.get("binary_origin", {})
    if not isinstance(origin, dict) or origin.get("kind") != "source-build":
        return
    builder = _builder_image_metadata()
    if origin.get("builder_image_id") != builder["id"]:
        raise HarnessError(
            "source-build cache does not match the retained builder image; "
            "run bootstrap --refresh --from-source"
        )


def _build_builder_image() -> dict[str, str]:
    run(
        [
            "docker",
            "build",
            "--pull=false",
            "--label",
            f"org.helixscreen.builder.recipe.sha256={sha256(BUILDER_DOCKERFILE)}",
            "-f",
            BUILDER_DOCKERFILE,
            "-t",
            BUILDER_IMAGE,
            BUILDER_DOCKERFILE.parent,
        ]
    )
    return _builder_image_metadata()


def _install_artifact_binary(staging: Path) -> dict[str, Any]:
    artifact_zip = staging / "developer-artifact.zip"
    with artifact_zip.open("wb") as output:
        run(
            [
                _gh_command(),
                "api",
                f"repos/prestonbrown/helixscreen/actions/artifacts/{HELIX_ARTIFACT_ID}/zip",
            ],
            stdout=output,
        )
    artifact_dir = staging / "artifact-unpacked"
    artifact_dir.mkdir()
    _safe_extract_zip(artifact_zip, artifact_dir)
    matches = [path for path in artifact_dir.rglob("helix-screen") if path.is_file()]
    if len(matches) != 1:
        raise HarnessError(f"expected one helix-screen in developer artifact, found {len(matches)}")
    if sha256(matches[0]) != HELIX_ARTIFACT_BINARY_SHA256:
        raise HarnessError("downloaded developer binary does not match the pinned SHA-256")
    binary_dir = staging / "binary"
    binary_dir.mkdir()
    shutil.copy2(matches[0], binary_dir / "helix-screen")
    (binary_dir / "helix-screen").chmod(0o755)
    artifact_zip.unlink()
    shutil.rmtree(artifact_dir)
    return {
        "artifact_id": HELIX_ARTIFACT_ID,
        "artifact_name": HELIX_ARTIFACT_NAME,
        "build_run": HELIX_BUILD_RUN,
        "expires_at": HELIX_ARTIFACT_EXPIRES_AT,
        "kind": "actions-artifact",
    }


def _source_build_binary(staging: Path) -> dict[str, Any]:
    # Always issue the build command: Docker reuses cached layers when the
    # recipe is unchanged, while a recipe edit can never silently reuse an old
    # image that happens to carry the same source tag.
    builder = _build_builder_image()
    source = staging / "source"
    run(["git", "init", source])
    run(["git", "-C", source, "remote", "add", "origin", HELIX_SOURCE_URL])
    run(["git", "-C", source, "fetch", "--depth", "1", "origin", HELIX_SOURCE_COMMIT])
    run(["git", "-C", source, "checkout", "--detach", HELIX_SOURCE_COMMIT])
    run(
        [
            "git",
            "-C",
            source,
            "submodule",
            "update",
            "--init",
            "--recursive",
            "--jobs",
            "4",
            "--depth",
            "1",
        ]
    )
    head = run(["git", "-C", source, "rev-parse", "HEAD"], capture=True).stdout.strip()
    if head != HELIX_SOURCE_COMMIT:
        raise HarnessError(f"source checkout mismatch: expected {HELIX_SOURCE_COMMIT}, got {head}")
    submodules = [
        line.strip()
        for line in run(
            ["git", "-C", source, "submodule", "status", "--recursive"], capture=True
        ).stdout.splitlines()
        if line.strip()
    ]
    if not submodules or any(line[0] in "-+U" for line in submodules):
        raise HarnessError("source checkout has an uninitialized or mismatched submodule")
    jobs = max(1, int(os.environ.get("HELIX_DEV_BUILD_JOBS", min(os.cpu_count() or 2, 8))))
    run(
        [
            "docker",
            "run",
            "--rm",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "-e",
            "HOME=/source/.helix-build-home",
            "-e",
            "CC=clang",
            "-e",
            "CXX=clang++",
            "-e",
            "DBGLEVEL=0",
            "-e",
            f"HELIX_BUILD_JOBS={jobs}",
            "-v",
            f"{source}:/source",
            BUILDER_IMAGE,
            "bash",
            "-lc",
            "mkdir -p \"$HOME\" && npm install --no-audit --no-fund "
            "&& make venv-setup && make -j\"$HELIX_BUILD_JOBS\"",
        ]
    )
    built = source / "build" / "bin" / "helix-screen"
    if not built.is_file():
        raise HarnessError("pinned source build did not produce build/bin/helix-screen")
    binary_dir = staging / "binary"
    binary_dir.mkdir()
    shutil.copy2(built, binary_dir / "helix-screen")
    (binary_dir / "helix-screen").chmod(0o755)
    shutil.rmtree(source)
    return {
        "builder_dockerfile_sha256": sha256(BUILDER_DOCKERFILE),
        "builder_image": BUILDER_IMAGE,
        "builder_image_id": builder["id"],
        "build_jobs": jobs,
        "kind": "source-build",
        "source_url": HELIX_SOURCE_URL,
        "submodules": submodules,
    }


def _install_release_data(staging: Path) -> None:
    release_archive = staging / f"helixscreen-x86-{HELIX_TAG}.tar.gz"
    run(["curl", "--fail", "--location", "--output", release_archive, HELIX_RELEASE_URL])
    if sha256(release_archive) != HELIX_RELEASE_SHA256:
        raise HarnessError("downloaded release data does not match the pinned SHA-256")
    runtime_dir = staging / "runtime"
    runtime_dir.mkdir()
    _safe_extract_tar(release_archive, runtime_dir)
    release_archive.unlink()


def bootstrap(refresh: bool, from_source: bool = False) -> None:
    final = cache_root()
    if from_source and not refresh and final.exists():
        raise HarnessError("--from-source requires --refresh when a cache already exists")
    if final.exists() and not refresh:
        try:
            metadata = verify_assets(final)
            try:
                image = image_metadata()
            except HarnessError:
                build_image()
                image = image_metadata()
            print(f"Pinned Helix runtime is ready: {final}")
            print(f"source {metadata['source_commit']} | image {image['id']}")
            return
        except HarnessError as exc:
            raise HarnessError(f"existing cache failed verification ({exc}); use bootstrap --refresh")

    verify_source_pin()
    parent = final.parent
    parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{HELIX_TAG}-", dir=parent))
    try:
        if from_source:
            origin = _source_build_binary(staging)
        else:
            try:
                origin = _install_artifact_binary(staging)
            except (HarnessError, subprocess.CalledProcessError, zipfile.BadZipFile) as exc:
                print(
                    f"Pinned Actions accelerator unavailable ({exc}); building exact source instead.",
                    file=sys.stderr,
                )
                for transient in (staging / "developer-artifact.zip", staging / "artifact-unpacked"):
                    if transient.is_dir():
                        shutil.rmtree(transient)
                    elif transient.exists():
                        transient.unlink()
                origin = _source_build_binary(staging)
        _install_release_data(staging)

        metadata = {
            "binary_sha256": sha256(staging / "binary" / "helix-screen"),
            "binary_origin": origin,
            "release_archive_sha256": HELIX_RELEASE_SHA256,
            "release_url": HELIX_RELEASE_URL,
            "source_commit": HELIX_SOURCE_COMMIT,
            "tag": HELIX_TAG,
            "tag_object": HELIX_TAG_OBJECT,
        }
        json_write(staging / "metadata.json", metadata)
        verify_assets(staging)

        backup = None
        if final.exists():
            backup = final.with_name(f"{final.name}.previous-{time.strftime('%Y%m%d-%H%M%S')}")
            final.rename(backup)
        staging.rename(final)
        if backup:
            print(f"Previous verified cache retained at {backup}")
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise

    build_image()
    print(f"Bootstrapped {HELIX_TAG} at {final}")


def _template_path() -> Path:
    return runtime_path() / "config" / "settings.json.template"


def seed_settings(config_dir: Path) -> Path:
    config_dir.mkdir(parents=True, exist_ok=True)
    target = config_dir / "settings-test.json"
    if target.is_file():
        try:
            settings = json.loads(target.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise HarnessError(f"refusing to overwrite malformed retained config {target}: {exc}")
    else:
        settings = json.loads(_template_path().read_text(encoding="utf-8"))

    settings["dark_mode"] = True
    settings["disable_sound"] = True
    settings["sounds_enabled"] = False
    settings["wizard_completed"] = True
    settings["tour"] = {"completed": True, "last_seen_version": 1}
    settings["active_printer_id"] = "default"
    settings.setdefault("plugins", {})["enabled"] = {
        "orcacal": {"permissions": [], "version": "0.2.0"}
    }
    printer = settings.setdefault("printers", {}).setdefault("default", {})
    printer["name"] = "Helix native mock printer"
    # These devices are built into Helix's beta.4 mock printer. Acknowledge
    # them so the stock eight-second discovery toast cannot cover the review
    # tile on compact landing screens.
    printer.setdefault("hardware", {})["expected"] = list(
        BETA4_MOCK_ACKNOWLEDGED_HARDWARE
    )
    printer["panel_widgets"] = {
        "home": {
            "grid": "12x8",
            # Beta.4's normal Home action always selects physical page zero,
            # even when main_page_index names another page. Keep the review
            # tile on page zero so startup, retained state, and Home agree.
            "main_page_index": 0,
            "next_page_id": 1,
            "pages": [
                {
                    "id": "main",
                    "widgets": [
                        {
                            "col": 0,
                            "colspan": 3,
                            "enabled": True,
                            "id": "orcacal__tile",
                            "row": 0,
                            "rowspan": 2,
                        },
                        *(
                            {
                                "col": -1,
                                "colspan": 1,
                                "enabled": False,
                                "id": widget_id,
                                "row": -1,
                                "rowspan": 1,
                            }
                            for widget_id in BETA4_DEFAULT_HOME_WIDGETS
                        ),
                    ],
                },
            ],
        }
    }
    json_write(target, settings)
    return target


def _docker_running(name: str) -> bool:
    result = run(
        ["docker", "inspect", "--format", "{{.State.Running}}", name],
        capture=True,
        check=False,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def _remove_container(name: str) -> None:
    result = run(["docker", "inspect", name], capture=True, check=False)
    if result.returncode == 0:
        run(["docker", "rm", "--force", name], capture=True)


def _container_args(
    name: str,
    work: Path,
    width: int,
    height: int,
    layout: str,
    dpi: int,
) -> list[str]:
    uid = os.getuid()
    gid = os.getgid()
    return [
        "docker",
        "run",
        "--detach",
        "--name",
        name,
        "--network",
        "none",
        "--read-only",
        "--user",
        f"{uid}:{gid}",
        "--tmpfs",
        "/tmp:rw,nosuid,nodev",
        "-e",
        "HOME=/state/home",
        "-e",
        "HELIX_DATA_DIR=/helix",
        "-e",
        "HELIX_CONFIG_DIR=/state/config",
        "-e",
        "HELIX_PLUGIN_DIR=/plugin",
        "-e",
        "HELIX_HOT_RELOAD=1",
        "-e",
        "SDL_VIDEODRIVER=dummy",
        "-e",
        "SDL_AUDIODRIVER=dummy",
        "-v",
        f"{binary_path().parent}:/binary:ro",
        "-v",
        f"{runtime_path()}:/helix:ro",
        "-v",
        f"{PLUGIN_ROOT}:/plugin:ro",
        "-v",
        f"{work}:/state",
        IMAGE,
        "/binary/helix-screen",
        "--test",
        "--skip-wizard",
        "--skip-splash",
        "--remote-socket",
        "/state/control.sock",
        "--size",
        f"{width}x{height}",
        "--layout",
        layout,
        "--dpi",
        str(dpi),
        "--dark",
        "--no-sound",
        "--log-dest",
        "console",
        "-vv",
    ]


def ctl(name: str, *args: str, check: bool = True) -> Any:
    result = run(
        [
            "docker",
            "exec",
            name,
            "/binary/helix-screen",
            "ctl",
            "--json",
            "-s",
            "/state/control.sock",
            *args,
        ],
        capture=True,
        check=check,
        timeout=20,
    )
    if not check and result.returncode:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise HarnessError(f"invalid helixctl response for {' '.join(args)}: {result.stdout!r}") from exc


def wait_ready(name: str, timeout: float = 20.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _docker_running(name):
            logs = run(["docker", "logs", name], capture=True, check=False)
            raise HarnessError(f"Helix runtime exited during startup:\n{logs.stdout}\n{logs.stderr}")
        if ctl(name, "ping", check=False) == "pong":
            logs = run(["docker", "logs", name], capture=True, check=False)
            combined = logs.stdout + logs.stderr
            if "[PluginHost] orcacal: loaded" not in combined:
                time.sleep(0.2)
                continue
            return
        time.sleep(0.2)
    raise HarnessError(f"timed out waiting for native Helix control socket in {name}")


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def _viewer_process_alive(pid: int) -> bool:
    if not _pid_alive(pid):
        return False
    try:
        command = (Path("/proc") / str(pid) / "cmdline").read_bytes().split(b"\0")
    except OSError:
        return False
    return any(part.endswith(b"helix_dev.py") for part in command) and b"_serve" in command


def _viewer_pid() -> int | None:
    path = state_root() / "viewer.pid"
    if not path.is_file():
        return None
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def _http_health() -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{REVIEW_PORT}/health", timeout=1) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


def _runtime_healthy() -> bool:
    try:
        return _docker_running(CONTAINER) and ctl(CONTAINER, "ping", check=False) == "pong"
    except (HarnessError, subprocess.SubprocessError):
        return False


def _port_available() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((REVIEW_BIND, REVIEW_PORT))
        except OSError:
            return False
    return True


def start_viewer() -> int:
    root = state_root()
    log = (root / "viewer.log").open("ab")
    process = subprocess.Popen(
        [sys.executable, __file__, "_serve"],
        cwd=PROJECT_ROOT,
        stdin=subprocess.DEVNULL,
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    (root / "viewer.pid").write_text(f"{process.pid}\n", encoding="utf-8")
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise HarnessError(f"review viewer exited; inspect {root / 'viewer.log'}")
        if _http_health():
            return process.pid
        time.sleep(0.1)
    process.terminate()
    raise HarnessError(f"review viewer did not become healthy; inspect {root / 'viewer.log'}")


def up() -> None:
    metadata = verify_assets()
    image = image_metadata()
    root = state_root()
    root.mkdir(parents=True, exist_ok=True)
    (root / "home").mkdir(exist_ok=True)
    seed_settings(root / "config")

    old_pid = _viewer_pid()
    if old_pid and _viewer_process_alive(old_pid):
        os.kill(old_pid, signal.SIGTERM)
        time.sleep(0.2)
    _remove_container(CONTAINER)
    if not _port_available():
        raise HarnessError(
            f"reserved port {REVIEW_PORT} is occupied by another process; run status and inspect the devbox registry"
        )

    run(_container_args(CONTAINER, root, 800, 480, "standard", 160), capture=True)
    try:
        wait_ready(CONTAINER)
        _wait_visible_landing(CONTAINER, 800, 480)
        viewer_pid = start_viewer()
    except Exception:
        _remove_container(CONTAINER)
        raise
    json_write(
        root / "session.json",
        {
            "binary_sha256": metadata["binary_sha256"],
            "container": CONTAINER,
            "image": IMAGE,
            "image_id": image["id"],
            "network": "none",
            "plugin_dir": str(PLUGIN_ROOT),
            "source_commit": HELIX_SOURCE_COMMIT,
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "viewer_pid": viewer_pid,
            "viewport": "800x480",
        },
    )
    print("Native Helix beta.4 mock runtime is ready.")
    print(f"Trusted-LAN review: http://{REVIEW_HOST}:{REVIEW_PORT}/")
    tailscale_ip = _tailscale_ip()
    if tailscale_ip:
        print(f"Tailscale review:   http://{tailscale_ip}:{REVIEW_PORT}/")
    print("Plugin edits under helix-plugin/orcacal hot-reload in about one second.")


def _tailscale_ip() -> str | None:
    command = shutil.which("tailscale")
    if not command:
        return None
    result = run([command, "ip", "-4"], capture=True, check=False)
    return result.stdout.strip().splitlines()[0] if result.returncode == 0 and result.stdout.strip() else None


def status() -> None:
    running = _docker_running(CONTAINER)
    pid = _viewer_pid()
    viewer = bool(pid and _viewer_process_alive(pid) and _http_health())
    ping = ctl(CONTAINER, "ping", check=False) if running else None
    payload = {
        "assets": "ready" if _assets_ready() else "missing-or-invalid",
        "container": CONTAINER,
        "container_running": running,
        "control": ping,
        "network": "none" if running else None,
        "review_url": f"http://{REVIEW_HOST}:{REVIEW_PORT}/",
        "viewer_healthy": viewer,
        "viewer_pid": pid,
    }
    print(json.dumps(payload, indent=2))
    if not (running and viewer and ping == "pong"):
        raise HarnessError("native review harness is not fully healthy")


def _assets_ready() -> bool:
    try:
        verify_assets()
        image_metadata()
        return True
    except HarnessError:
        return False


def down() -> None:
    pid = _viewer_pid()
    if pid and _viewer_process_alive(pid):
        os.kill(pid, signal.SIGTERM)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and _viewer_process_alive(pid):
            time.sleep(0.05)
    _remove_container(CONTAINER)
    for path in (state_root() / "viewer.pid", state_root() / "control.sock"):
        path.unlink(missing_ok=True)
    print("Helix mock runtime and review listener are stopped; retained state and captures were not deleted.")


def prove_reload() -> None:
    if not _docker_running(CONTAINER):
        raise HarnessError("run up before reload")
    before_logs = run(["docker", "logs", CONTAINER], capture=True, check=False)
    before = (before_logs.stdout + before_logs.stderr).count("[PluginHost] orcacal: loaded")
    marker = PLUGIN_DIR / ".helix-dev-reload"
    marker.write_text(f"reload proof {time.time_ns()}\n", encoding="utf-8")
    try:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            logs = run(["docker", "logs", CONTAINER], capture=True, check=False)
            combined = logs.stdout + logs.stderr
            if (
                combined.count("[PluginHost] orcacal: loaded") > before
                and "[PluginDirWatcher]" in combined
            ):
                print("PASS: beta.4 PluginDirWatcher reloaded orcacal without restarting the runtime.")
                return
            time.sleep(0.2)
        raise HarnessError("no beta.4 hot-reload event observed within five seconds")
    finally:
        marker.unlink(missing_ok=True)


def _screenshot(container: str, output: Path, name: str) -> Path:
    ctl(container, "screenshot", f"/state/{name}", "--stable")
    path = output / name
    if not path.is_file() or path.stat().st_size == 0:
        raise HarnessError(f"native screenshot was not created: {path}")
    return path


def _widgets(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, dict) or not isinstance(value.get("widgets"), list):
        raise HarnessError(f"unexpected helixctl widget response: {value!r}")
    return value["widgets"]


def _assert_widget(value: Any, name: str) -> None:
    if not any(item.get("name") == name for item in _widgets(value)):
        raise HarnessError(f"native widget not found: {name}")


def _assert_horizontal_fit(value: Any, width: int) -> None:
    widgets = _widgets(value)
    if not widgets:
        raise HarnessError("geometry result contains no widgets")
    for widget in widgets:
        x = int(widget.get("x", -1))
        w = int(widget.get("w", 0))
        h = int(widget.get("h", 0))
        scroll = widget.get("scroll", {}) or {}
        if w <= 0 or h <= 0 or x < 0 or x + w > width:
            raise HarnessError(f"horizontal viewport overflow at {width}px: {widget}")
        if int(scroll.get("left", 0)) != 0 or int(scroll.get("right", 0)) > 0:
            raise HarnessError(f"positive horizontal scroll extent at {width}px: {widget}")


def _visible_widget_geometry(value: Any, name: str, width: int, height: int) -> dict[str, Any]:
    widgets = _widgets(value)
    widget = next((item for item in widgets if item.get("name") == name), None)
    if widget is None:
        raise HarnessError(f"native widget geometry not found: {name}")
    x = int(widget.get("x", -1))
    y = int(widget.get("y", -1))
    w = int(widget.get("w", 0))
    h = int(widget.get("h", 0))
    if (
        widget.get("hidden") is True
        or w <= 0
        or h <= 0
        or x < 0
        or y < 0
        or x + w > width
        or y + h > height
    ):
        raise HarnessError(f"native widget is not visible in {width}x{height}: {widget}")
    return widget


def _assert_visible_landing(container: str, width: int, height: int) -> dict[str, Any]:
    current = ctl(container, "current")
    if not isinstance(current, dict) or current.get("panel") != "home" or current.get(
        "overlays"
    ) != []:
        raise HarnessError(f"native landing screen is not unobstructed Home: {current!r}")
    return _visible_widget_geometry(
        ctl(container, "geom", "orcacal__tile", "0"),
        "orcacal__tile",
        width,
        height,
    )


def _wait_visible_landing(
    container: str, width: int, height: int, timeout: float = 10.0
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            return _assert_visible_landing(container, width, height)
        except (HarnessError, subprocess.CalledProcessError) as exc:
            last_error = exc
            time.sleep(0.1)
    raise HarnessError(f"tile never became visible on native Home: {last_error}")


def _tap_visible_widget(container: str, name: str, width: int, height: int) -> None:
    widget = _visible_widget_geometry(ctl(container, "geom", name, "0"), name, width, height)
    x = int(widget["x"]) + int(widget["w"]) // 2
    y = int(widget["y"]) + int(widget["h"]) // 2
    ctl(container, "press", str(x), str(y))
    ctl(container, "release", str(x), str(y))
    ctl(container, "wait_idle")


def _assert_overlay(value: Any, expected: list[str]) -> None:
    if not isinstance(value, dict) or value.get("overlays") != expected:
        raise HarnessError(f"expected overlay stack {expected!r}, got {value!r}")


def _plugin_hashes() -> dict[str, str]:
    return {
        str(path.relative_to(PROJECT_ROOT)): sha256(path)
        for path in sorted(PLUGIN_DIR.rglob("*"))
        if path.is_file()
    }


def _candidate_paths() -> tuple[Path, ...]:
    return (
        PROJECT_ROOT / ".github" / "workflows" / "ci.yml",
        PROJECT_ROOT / "scripts" / "helix-dev",
        BUILDER_DOCKERFILE,
        DOCKERFILE,
        PROJECT_ROOT / "scripts" / "helix_dev.py",
        PROJECT_ROOT / "tests" / "test_helix_dev.py",
    )


def _candidate_hashes() -> dict[str, str]:
    missing = [str(path) for path in _candidate_paths() if not path.is_file()]
    if missing:
        raise HarnessError("candidate is missing evidence-bound files:\n  " + "\n  ".join(missing))
    return {str(path.relative_to(PROJECT_ROOT)): sha256(path) for path in _candidate_paths()}


def _matrix_text(rows: list[dict[str, Any]]) -> str:
    lines = ["label\tviewport\tlayout\tdpi\tresult"]
    lines.extend(
        f"{row['label']}\t{row['viewport']}\t{row['layout']}\t{row['dpi']}\t{row['result']}"
        for row in rows
    )
    return "\n".join(lines) + "\n"


def _expected_rows() -> list[dict[str, Any]]:
    return [
        {
            "dpi": dpi,
            "label": label,
            "layout": layout,
            "result": "PASS",
            "viewport": f"{width}x{height}",
        }
        for label, width, height, layout, dpi in VIEWPORTS
    ]


def _validate_report_structure(report: dict[str, Any], matrix_text: str) -> None:
    results = report.get("results")
    if not isinstance(results, list) or len(results) != len(VIEWPORTS):
        raise HarnessError("capture report does not contain the exact eleven-target matrix")
    for observed, expected in zip(results, _expected_rows(), strict=True):
        identity = {key: observed.get(key) for key in expected}
        if identity != expected or observed.get("assertions") != list(EXPECTED_ASSERTIONS):
            raise HarnessError(f"capture row does not match the verified matrix: {observed}")
    if matrix_text != _matrix_text(results):
        raise HarnessError("matrix.tsv does not exactly match report.json")
    runtime = report.get("runtime", {})
    if (
        runtime.get("tag") != HELIX_TAG
        or runtime.get("tag_object") != HELIX_TAG_OBJECT
        or runtime.get("source_commit") != HELIX_SOURCE_COMMIT
        or runtime.get("release_archive_sha256") != HELIX_RELEASE_SHA256
        or runtime.get("binary_origin", {}).get("kind")
        not in {"actions-artifact", "source-build"}
    ):
        raise HarnessError("capture report runtime pins do not match this harness")
    if report.get("container_network") != "none" or report.get("image") != IMAGE:
        raise HarnessError("capture report does not prove the isolated pinned runtime")
    if report.get("candidate_files") != _candidate_hashes():
        raise HarnessError("capture-time candidate hashes do not match the current candidate")
    if report.get("plugin_files_before_and_after") != _plugin_hashes():
        raise HarnessError("capture product hashes do not match the accepted Issue #1 plugin")
    expected_screenshots = {
        f"{label}/{filename}"
        for label, _width, _height, _layout, _dpi in VIEWPORTS
        for filename in CAPTURE_FRAME_NAMES
    }
    screenshots = report.get("screenshots", {})
    if set(screenshots) != expected_screenshots or any(
        not isinstance(value, str) or len(value) != 64 for value in screenshots.values()
    ):
        raise HarnessError("capture report does not contain exactly 44 screenshot hashes")


def _validate_capture(source: Path, *, require_runtime: bool) -> dict[str, Any]:
    report_path = source / "report.json"
    matrix_path = source / "matrix.tsv"
    if not report_path.is_file() or not matrix_path.is_file():
        raise HarnessError(f"not a completed helix-dev capture: {source}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    _validate_report_structure(report, matrix_path.read_text(encoding="utf-8"))
    for relative, expected in report["screenshots"].items():
        path = source / relative
        if not path.is_file() or sha256(path) != expected:
            raise HarnessError(f"capture screenshot does not match its recorded hash: {relative}")
    if require_runtime:
        metadata = verify_assets()
        if report.get("runtime") != metadata:
            raise HarnessError("capture runtime metadata does not match the current verified cache")
        verify_source_builder(metadata)
        if report.get("image_id") != image_metadata()["id"]:
            raise HarnessError("capture runtime image does not match the current verified image")
    return report


def verify_promoted_evidence(root: Path) -> None:
    report_path = root / "report.json"
    matrix_path = root / "matrix.tsv"
    promotion_path = root / "promotion.json"
    if not all(path.is_file() for path in (report_path, matrix_path, promotion_path)):
        raise HarnessError(f"promoted evidence is incomplete: {root}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    promotion = json.loads(promotion_path.read_text(encoding="utf-8"))
    _validate_report_structure(report, matrix_path.read_text(encoding="utf-8"))
    if promotion.get("full_capture_report_sha256") != sha256(report_path):
        raise HarnessError("promoted report hash does not match report.json")
    if promotion.get("candidate_files") != report.get("candidate_files"):
        raise HarnessError("promotion candidate hashes do not match capture-time hashes")
    selected = promotion.get("selected_screenshots", {})
    expected_selected = {}
    for label, _width, _height, _layout, _dpi in VIEWPORTS:
        expected_selected[f"screenshots/landing/{label}.png"] = report["screenshots"][
            f"{label}/home.png"
        ]
        expected_selected[f"screenshots/start-toast/{label}.png"] = report["screenshots"][
            f"{label}/start-toast.png"
        ]
    if selected != expected_selected:
        raise HarnessError("promotion does not select the exact landing and Start-toast frames")
    for relative, expected in selected.items():
        path = root / relative
        if not path.is_file() or sha256(path) != expected:
            raise HarnessError(f"promoted screenshot does not match its recorded hash: {relative}")
    print(f"PASS: evidence is bound to the current candidate and all {len(VIEWPORTS)} targets")


def run_viewport(entry: tuple[str, int, int, str, int], root: Path) -> dict[str, Any]:
    label, width, height, layout, dpi = entry
    output = root / label
    output.mkdir(parents=True)
    (output / "home").mkdir()
    seed_settings(output / "config")
    name = f"orcacal-i2-{os.getpid()}-{label.replace('_', '-')}"
    _remove_container(name)
    run(_container_args(name, output, width, height, layout, dpi), capture=True)
    assertions: list[str] = []
    try:
        wait_ready(name)
        assertions.append("plugin-loaded")

        _wait_visible_landing(name, width, height)
        assertions.extend(("landing-home", "tile-visible"))
        _screenshot(name, output, "home.png")

        _tap_visible_widget(name, "orcacal__tile", width, height)
        _assert_overlay(ctl(name, "current"), ["orcacal__wizard"])
        chooser = ctl(name, "ls", "orcacal__wizard")
        _assert_widget(chooser, "back_button")
        _assert_widget(chooser, "orcacal__temperature_choice")
        _assert_horizontal_fit(ctl(name, "geom", "orcacal__chooser_content", "8"), width)
        assertions.extend(
            ("tile-native-tap-opens-chooser", "chooser-native-back", "chooser-horizontal-fit")
        )
        _screenshot(name, output, "chooser.png")

        ctl(name, "scroll", "orcacal__temperature_choice")
        ctl(name, "wait_idle")
        _tap_visible_widget(name, "orcacal__temperature_choice", width, height)
        _assert_overlay(
            ctl(name, "current"), ["orcacal__wizard", "orcacal__temperature"]
        )
        temperature = ctl(name, "ls", "orcacal__temperature")
        _assert_widget(temperature, "back_button")
        _assert_widget(temperature, "orcacal__start_button")
        _assert_horizontal_fit(ctl(name, "geom", "orcacal__temperature_content", "8"), width)
        assertions.extend(
            (
                "chooser-native-tap-opens-temperature",
                "temperature-native-back",
                "temperature-horizontal-fit",
            )
        )
        _screenshot(name, output, "temperature.png")

        ctl(name, "scroll", "orcacal__start_button")
        ctl(name, "wait_idle")
        start_geom = _widgets(ctl(name, "geom", "orcacal__start_button"))[0]
        if int(start_geom.get("y", -1)) < 0 or int(start_geom.get("y", -1)) + int(
            start_geom.get("h", 0)
        ) > height:
            raise HarnessError(f"Start is not visible after native scroll: {start_geom}")
        _tap_visible_widget(name, "orcacal__start_button", width, height)
        deadline = time.monotonic() + 3
        combined = ""
        while time.monotonic() < deadline:
            logs = run(["docker", "logs", name], capture=True, check=False)
            combined = logs.stdout + logs.stderr
            if "Toast shown: [info] Calibration request test" in combined:
                break
            time.sleep(0.1)
        else:
            raise HarnessError("Start callback did not produce the expected native toast")
        assertions.extend(("start-visible", "start-native-tap-toast"))
        _screenshot(name, output, "start-toast.png")

        # The proof toast intentionally covers compact content for four
        # seconds. Let that real user-visible feedback finish before proving
        # the later Home interaction, so the follow-up tap is not intercepted.
        time.sleep(4.1)

        ctl(name, "go_back")
        ctl(name, "wait_idle")
        _assert_overlay(ctl(name, "current"), ["orcacal__wizard"])
        ctl(name, "go_back")
        ctl(name, "wait_idle")
        _assert_overlay(ctl(name, "current"), [])
        _assert_visible_landing(name, width, height)
        ctl(name, "navigate", "home")
        ctl(name, "wait_idle")
        _assert_visible_landing(name, width, height)
        _tap_visible_widget(name, "orcacal__tile", width, height)
        _assert_overlay(ctl(name, "current"), ["orcacal__wizard"])
        assertions.extend(
            (
                "back-to-chooser",
                "back-to-home",
                "home-action-keeps-tile-visible",
                "tile-native-tap-reopens",
            )
        )

        (output / "runtime.log").write_text(combined, encoding="utf-8")
        return {
            "assertions": assertions,
            "dpi": dpi,
            "label": label,
            "layout": layout,
            "result": "PASS",
            "viewport": f"{width}x{height}",
        }
    finally:
        logs = run(["docker", "logs", name], capture=True, check=False)
        if logs.stdout or logs.stderr:
            (output / "runtime.log").write_text(logs.stdout + logs.stderr, encoding="utf-8")
        _remove_container(name)


def capture(output: Path | None) -> None:
    metadata = verify_assets()
    verify_source_builder(metadata)
    image = image_metadata()
    root = output or state_root() / "captures" / time.strftime("%Y%m%d-%H%M%S")
    if root.exists():
        raise HarnessError(f"capture destination already exists: {root}")
    root.mkdir(parents=True)
    before = _plugin_hashes()
    candidate_files = _candidate_hashes()
    rows: list[dict[str, Any]] = []
    try:
        for entry in VIEWPORTS:
            row = run_viewport(entry, root)
            rows.append(row)
            print(
                f"PASS {row['label']}: {row['viewport']} {row['layout']} {row['dpi']} DPI",
                flush=True,
            )
    except Exception:
        json_write(root / "report.partial.json", {"results": rows})
        raise
    after = _plugin_hashes()
    if before != after:
        raise HarnessError("capture changed an accepted Issue #1 product file")

    artifact_hashes = {
        str(path.relative_to(root)): sha256(path)
        for path in sorted(root.rglob("*.png"))
    }
    report = {
        "candidate_files": candidate_files,
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "container_network": "none",
        "image": IMAGE,
        "image_id": image["id"],
        "plugin_files_before_and_after": before,
        "repository_head_at_capture": _git_head(),
        "runtime": metadata,
        "results": rows,
        "screenshots": artifact_hashes,
    }
    json_write(root / "report.json", report)
    (root / "matrix.tsv").write_text(_matrix_text(rows), encoding="utf-8", newline="")
    _validate_capture(root, require_runtime=True)
    print(f"Native evidence retained at {root}")


def promote(source: Path, output: Path) -> None:
    report = _validate_capture(source, require_runtime=True)
    report_path = source / "report.json"
    matrix_path = source / "matrix.tsv"
    results = report["results"]
    if output.exists():
        raise HarnessError(f"evidence destination already exists: {output}")
    source_images = {}
    for row in results:
        label = row["label"]
        source_images[f"screenshots/landing/{label}.png"] = source / label / "home.png"
        source_images[f"screenshots/start-toast/{label}.png"] = (
            source / label / "start-toast.png"
        )
    missing = [str(path) for path in source_images.values() if not path.is_file()]
    if missing:
        raise HarnessError("capture is missing final-flow screenshots:\n  " + "\n  ".join(missing))
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}-", dir=output.parent))
    try:
        (staging / "screenshots" / "landing").mkdir(parents=True)
        (staging / "screenshots" / "start-toast").mkdir(parents=True)
        shutil.copy2(report_path, staging / "report.json")
        shutil.copy2(matrix_path, staging / "matrix.tsv")
        selected: dict[str, str] = {}
        for relative, source_image in source_images.items():
            target = staging / relative
            shutil.copy2(source_image, target)
            selected[str(target.relative_to(staging))] = sha256(target)
        promotion = {
            "candidate_files": report["candidate_files"],
            "full_capture_report_sha256": sha256(report_path),
            "promoted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "selected_screenshots": selected,
            "source_capture_id": source.name,
        }
        json_write(staging / "promotion.json", promotion)
        verify_promoted_evidence(staging)
        staging.rename(output)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    print(f"Promoted matrix, report, and 22 landing/final-flow screenshots to {output}")


def _git_head() -> str:
    result = run(["git", "rev-parse", "HEAD"], capture=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def doctor(static: bool) -> None:
    errors: list[str] = []
    if not PLUGIN_DIR.is_dir():
        errors.append(f"missing plugin directory: {PLUGIN_DIR}")
    if not DOCKERFILE.is_file():
        errors.append(f"missing Dockerfile: {DOCKERFILE}")
    if not BUILDER_DOCKERFILE.is_file():
        errors.append(f"missing source-builder Dockerfile: {BUILDER_DOCKERFILE}")
    if len(VIEWPORTS) != 11 or len({entry[0] for entry in VIEWPORTS}) != 11:
        errors.append("viewport matrix must contain eleven unique named targets")
    manifest = json.loads((PLUGIN_DIR / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("id") != "orcacal" or manifest.get("permissions") != []:
        errors.append("accepted orcacal identity/permission boundary changed")
    if not static:
        for command in ("docker", "curl"):
            if not shutil.which(command):
                errors.append(f"required command not found: {command}")
        try:
            metadata = verify_assets()
            verify_source_builder(metadata)
            image_metadata()
        except HarnessError as exc:
            errors.append(str(exc))
        if not _port_available() and not _http_health():
            errors.append(f"reserved review port {REVIEW_PORT} is occupied by an unknown listener")
    if errors:
        raise HarnessError("doctor failed:\n- " + "\n- ".join(errors))
    print("PASS: static harness contract" if static else "PASS: native harness prerequisites")


VIEWER_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Helix native mock review</title>
  <style>
    :root { color-scheme: dark; font-family: system-ui, sans-serif; }
    body { margin: 0; background: #11151a; color: #e8edf2; }
    header { display: flex; gap: .75rem; align-items: center; padding: .65rem .9rem;
      background: #1b222a; border-bottom: 1px solid #34404b; }
    header strong { flex: 1; } button { color: #e8edf2; background: #27313b;
      border: 1px solid #465462; border-radius: .35rem; padding: .45rem .75rem; }
    button:hover { background: #34414d; } main { padding: 1rem; text-align: center; }
    #frame { max-width: 100%; height: auto; image-rendering: auto; cursor: pointer;
      box-shadow: 0 0 0 1px #38434d; background: #000; touch-action: none; }
    #state { margin-top: .6rem; color: #9eabb6; font-size: .85rem; }
  </style>
</head>
<body>
  <header><strong>Real HelixScreen beta.4 mock · 800×480</strong>
    <button data-action="home">Home</button><button data-action="back">Back</button>
    <button data-action="capture">Save capture</button></header>
  <main><img id="frame" src="/frame.png" width="800" height="480"
    alt="Live pixels rendered by the native HelixScreen mock runtime">
    <div id="state">Inputs are sent through Helix's native synthetic pointer.</div></main>
  <script>
    const frame = document.querySelector('#frame'); const state = document.querySelector('#state');
    let busy = false;
    async function post(path, body={}) { busy=true; try {
      const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
      const value=await response.json(); if(!response.ok) throw new Error(value.error || response.statusText);
      state.textContent=value.message || 'Ready'; refresh();
    } catch(error) { state.textContent=error.message; } finally { busy=false; } }
    function refresh(){ frame.src='/frame.png?t='+Date.now(); }
    frame.addEventListener('click', event => { if(busy) return; const rect=frame.getBoundingClientRect();
      const x=Math.round((event.clientX-rect.left)*frame.naturalWidth/rect.width);
      const y=Math.round((event.clientY-rect.top)*frame.naturalHeight/rect.height);
      post('/api/tap',{x,y}); });
    document.querySelectorAll('button').forEach(button => button.addEventListener('click',()=>post('/api/'+button.dataset.action)));
    setInterval(()=>{if(!busy)refresh()},1000);
  </script>
</body></html>
"""


class ViewerHandler(http.server.BaseHTTPRequestHandler):
    server_version = "HelixOrcaDev/1"
    capture_lock = threading.Lock()

    def log_message(self, format_string: str, *args: Any) -> None:
        sys.stdout.write(f"{self.log_date_time_string()} {format_string % args}\n")
        sys.stdout.flush()

    def _headers(self, status: int, content_type: str, length: int) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src 'self'")
        self.end_headers()

    def _send(self, body: bytes, content_type: str, status: int = 200) -> None:
        self._headers(status, content_type, len(body))
        self.wfile.write(body)

    def _json(self, value: Any, status: int = 200) -> None:
        self._send(json.dumps(value).encode("utf-8"), "application/json", status)

    def do_GET(self) -> None:  # noqa: N802
        route = self.path.split("?", 1)[0]
        if route == "/":
            self._send(VIEWER_HTML.encode("utf-8"), "text/html; charset=utf-8")
            return
        if route == "/health":
            healthy = _runtime_healthy()
            self._json(
                {"status": "ok" if healthy else "unavailable", "container": CONTAINER},
                200 if healthy else 503,
            )
            return
        if route == "/api/status":
            self._json(ctl(CONTAINER, "current"))
            return
        if route == "/frame.png":
            try:
                with self.capture_lock:
                    ctl(CONTAINER, "screenshot", "/state/viewer-frame.png")
                    body = (state_root() / "viewer-frame.png").read_bytes()
                self._send(body, "image/png")
            except Exception as exc:
                self._json({"error": str(exc)}, 503)
            return
        self._json({"error": "not found"}, 404)

    def do_POST(self) -> None:  # noqa: N802
        route = self.path.split("?", 1)[0]
        length = int(self.headers.get("Content-Length", "0"))
        if length > 4096:
            self._json({"error": "request too large"}, 413)
            return
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
            if route == "/api/tap":
                x, y = int(body["x"]), int(body["y"])
                if not (0 <= x < 800 and 0 <= y < 480):
                    raise HarnessError("tap is outside the 800x480 native viewport")
                ctl(CONTAINER, "press", str(x), str(y))
                ctl(CONTAINER, "release", str(x), str(y))
                ctl(CONTAINER, "wait_idle")
                self._json({"message": f"Native tap {x},{y}"})
                return
            if route == "/api/back":
                ctl(CONTAINER, "go_back")
                ctl(CONTAINER, "wait_idle")
                self._json({"message": "Native Back"})
                return
            if route == "/api/home":
                ctl(CONTAINER, "navigate", "home")
                ctl(CONTAINER, "wait_idle")
                self._json({"message": "Native Home"})
                return
            if route == "/api/capture":
                destination = state_root() / "manual-captures"
                destination.mkdir(parents=True, exist_ok=True)
                filename = f"manual-{time.strftime('%Y%m%d-%H%M%S')}.png"
                ctl(CONTAINER, "screenshot", f"/state/manual-captures/{filename}", "--stable")
                self._json({"message": f"Saved {destination / filename}"})
                return
            self._json({"error": "not found"}, 404)
        except Exception as exc:
            self._json({"error": str(exc)}, 400)


def serve() -> None:
    server = http.server.ThreadingHTTPServer((REVIEW_BIND, REVIEW_PORT), ViewerHandler)

    def stop_server(_signum: int, _frame: Any) -> None:
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop_server)
    print(f"helix-orca-dev-viewer listening on {REVIEW_BIND}:{REVIEW_PORT}", flush=True)
    server.serve_forever(poll_interval=0.2)
    server.server_close()


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        description="Pinned native HelixScreen beta.4 mock-printer development harness"
    )
    sub = root.add_subparsers(dest="command", required=True)
    bootstrap_parser = sub.add_parser("bootstrap", help="fetch and verify pinned native assets")
    bootstrap_parser.add_argument(
        "--refresh", action="store_true", help="stage a fresh verified cache and retain the old cache"
    )
    bootstrap_parser.add_argument(
        "--from-source",
        action="store_true",
        help="force the durable exact-source build instead of the short-lived artifact accelerator",
    )
    sub.add_parser("up", help="start 800x480 native mock runtime and trusted-LAN viewer")
    sub.add_parser("status", help="verify runtime, control socket, and review listener")
    sub.add_parser("down", help="stop runtime and viewer while retaining state")
    sub.add_parser("reload", help="prove beta.4 plugin hot reload without a restart")
    capture_parser = sub.add_parser("capture", help="exercise and capture all eleven target sizes")
    capture_parser.add_argument(
        "--output", type=Path, help="explicit evidence destination (default: retained XDG state)"
    )
    promote_parser = sub.add_parser(
        "promote", help="promote a complete retained capture into a bounded evidence directory"
    )
    promote_parser.add_argument("source", type=Path)
    promote_parser.add_argument("--output", type=Path, required=True)
    evidence_parser = sub.add_parser(
        "verify-evidence", help="verify promoted native evidence against the current candidate"
    )
    evidence_parser.add_argument("path", type=Path)
    doctor_parser = sub.add_parser("doctor", help="validate harness prerequisites")
    doctor_parser.add_argument("--static", action="store_true", help="skip Docker/cache/port checks")
    sub.add_parser("_serve", help=argparse.SUPPRESS)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "bootstrap":
            bootstrap(args.refresh, args.from_source)
        elif args.command == "up":
            up()
        elif args.command == "status":
            status()
        elif args.command == "down":
            down()
        elif args.command == "reload":
            prove_reload()
        elif args.command == "capture":
            capture(args.output.resolve() if args.output else None)
        elif args.command == "promote":
            promote(args.source.resolve(), args.output.resolve())
        elif args.command == "verify-evidence":
            verify_promoted_evidence(args.path.resolve())
        elif args.command == "doctor":
            doctor(args.static)
        elif args.command == "_serve":
            serve()
        else:
            raise HarnessError(f"unknown command: {args.command}")
        return 0
    except (HarnessError, subprocess.CalledProcessError) as exc:
        print(f"helix-dev: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
