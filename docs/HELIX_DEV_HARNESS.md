# Native Helix mock-printer harness

Issue #2 turns the accepted Issue #1 plugin proof into a repeatable developer
loop against the real HelixScreen runtime. It does not emulate Helix UI and it
does not add product behavior. The browser review page displays PNG frames
rendered by Helix itself and sends taps through Helix's synthetic pointer API.

## Pinned authority

- HelixScreen tag: `v1.1.0-beta.4`
- Source commit: `13a77bec42616d5c6f4fa397f1d5e12682fa4376`
- Annotated tag object: `daaf181197b82c795721b06bc7db55f6219fc258`
- Optional Ubuntu developer-artifact accelerator:
  `helix-screen-ubuntu-22.04`, artifact `11381944255`, from successful Build
  run `37385776288`; GitHub reports that it expires at
  `2026-10-13T00:24:45Z`
- Accelerator binary SHA-256:
  `ab819714fd469ff32657dc974585ad3bb05270829247da08eb71161a2d5197d0`
- x86 release-data SHA-256:
  `a0a618c2ab233e61324ec1024448571b160a8bd65b22b0387007017f4dc21b94`

`bootstrap` dereferences the upstream annotated tag, checks the exact source
commit, and verifies the release-data payload. While the short-lived Actions
artifact remains available it is a SHA-verified accelerator. If it is absent or
expired, the harness initializes every public submodule at the superproject's
pinned revisions and builds `build/bin/helix-screen` with the repository-owned,
pinned Ubuntu builder recipe. `bootstrap --refresh --from-source` forces that
durable path. The resulting binary SHA, builder recipe/image, and complete
recursive submodule lock are retained in `metadata.json`.

Both runtime and builder Docker builds use only the small `scripts/` directory
as context; no repository or reference-checkout contents are sent to Docker.
All cache replacement is staged, and `--refresh` retains the old verified cache
as a timestamped backup. Once the cache and runtime image exist, ordinary `up`,
`status`, `reload`, `down`, and `capture` runs need no network.

## First setup

From the canonical checkout:

```sh
cd /home/dev/Projects/personal/helix-orca-calibration
./scripts/helix-dev bootstrap
./scripts/helix-dev doctor
```

The bootstrap requires Docker, Git, `curl`, and a GitHub CLI to verify the
annotated source tag and, while available, retrieve the optional accelerator.
On the canonical devbox it uses `gh-oss`; another contributor may set
`HELIX_DEV_GH=gh`. A forced source build also needs network access for public
submodules, Ubuntu packages used when building the pinned builder image, and
the upstream Node/Python build dependencies. Override its conservative
eight-job maximum with `HELIX_DEV_BUILD_JOBS=<n>` when appropriate.

Assets are retained beneath
`$XDG_CACHE_HOME/helix-orca-calibration/helixscreen/v1.1.0-beta.4` (or
`~/.cache/...`). Runtime state, logs, and default captures are retained beneath
`$XDG_STATE_HOME/helix-orca-calibration/helix-dev` (or `~/.local/state/...`).
Nothing depends on an Issue-specific `/tmp` directory.

## Interactive loop

```sh
./scripts/helix-dev up
./scripts/helix-dev status
./scripts/helix-dev reload
./scripts/helix-dev down
```

`up` starts the real beta.4 Ubuntu developer binary in `--test` mode at the
default 800x480 dark viewport. It pre-enables only `orcacal` and places the
accepted tile on its own native Home page. Open:

- trusted LAN: `http://192.168.1.114:8540/`
- Tailscale on the current devbox: `http://100.120.150.65:8540/`
- health: `http://192.168.1.114:8540/health`

Port `8540` is reserved to this on-demand harness in the shared devbox
application registry. The viewer is intentionally a development control
surface, not product chrome: its image is a native Helix screenshot, a click is
translated to Helix `press`/`release`, and Home/Back call Helix navigation.

The plugin directory is mounted read-only into a container with
`HELIX_PLUGIN_DIR=/plugin` and `HELIX_HOT_RELOAD=1`. Beta.4's native
`PluginDirWatcher` reloads a saved plugin file in about one second. `reload`
proves that path with a temporary signature marker that is always removed; it
does not restart Helix or alter a product file.

`down` stops only the exact `helix-orca-dev` container and viewer PID. It keeps
the verified cache, config, logs, and captures.

## Capture and retained evidence

```sh
./scripts/helix-dev capture
```

The command starts an isolated native instance for each verified beta.4 target:

`480x272`, `272x480`, `480x320`, `480x400`, `800x480`, `480x800`,
`1024x600`, `1280x720`, `1080x2400` at 405 DPI, `1920x480`, and
`320x1480`.

At every size it proves plugin load, tile render, tile-to-chooser navigation,
native Back, chooser-to-Temperature navigation, horizontal fit, Start
visibility, the exact `Calibration request test` toast, return to Home, and
reopen. It captures Home, chooser, Temperature, and toast frames plus the
runtime log. The report records runtime pins, image identity, exact
capture-time hashes for the harness/CI candidate, unchanged product hashes, the
ordered matrix, assertions, and every screenshot hash. Default output is
timestamped durable XDG state, outside Git.

Only a complete passing run can be explicitly promoted:

```sh
./scripts/helix-dev promote \
  ~/.local/state/helix-orca-calibration/helix-dev/captures/<timestamp> \
  --output docs/evidence/issue-2/native
```

Promotion keeps the matrix, full report, and one final-flow native screenshot
per viewport. It rejects a changed harness, changed product, reordered or
partial matrix, runtime/cache mismatch, or altered frame. Verify the committed
bounded set independently with:

```sh
./scripts/helix-dev verify-evidence docs/evidence/issue-2/native
```

This provides versioned evidence bound to the exact candidate without
committing generated config, caches, full logs, or all 44 transient frames.

## Isolation and scope

Every Helix container uses Docker `--network none`, `--read-only`, SDL dummy
video/audio, `--test`, no `--real-moonraker`, a private config directory, and a
private Unix control socket. Release data and the plugin are read-only mounts.
Only the host viewer binds `0.0.0.0:8540`; it can control only the isolated mock
container. It exposes no shell or general control command.

This harness never installs to a printer and is not physical-device
acceptance. Real installation remains copying `helix-plugin/orcacal/` beneath
`printer_data/config/helixscreen/plugins/` and enabling it in Helix. Moonraker,
G-code generation/execution, print control, results, and Orca writeback remain
deferred.

## Automated coverage

GitHub CI runs the dependency-free unit/policy suite, wrapper syntax check,
static harness contract, promoted-evidence integrity check, and commit
whitespace check. It deliberately does not perform a large native source build.
Native interactive and eleven-target capture remains the reproducible devbox
gate above; CI proves that its bounded promoted result is still tied to the
checked-out candidate.
