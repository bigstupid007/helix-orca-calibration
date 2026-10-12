# Architecture

## Issue #1 HelixScreen foundation

`helix-plugin/orcacal/` is an independent permissionless Lua plugin for the
stock framework introduced in HelixScreen `v1.1.0-beta.4`.

The runtime flow is:

1. Helix owns and renders the `orcacal__tile` home widget.
2. The tile's `open` event pushes `orcacal__wizard` through
   `helix.ui.overlay()`.
3. The chooser reads the local `CALIBRATIONS` registry and its Temperature row
   pushes `orcacal__temperature` as a second native overlay.
4. Helix's inherited Back control pops Temperature to the chooser and the
   chooser to Home.
5. **Start** calls only `helix.ui.toast("Calibration request test")`.

The registry maps a calibration ID to a plugin-owned detail component.
Temperature is the only current entry. The chooser's shared context is a
compact, non-interactive two-line card above the dominant calibration list.
Future modules add registry entries and native detail components to this same
shell; they do not introduce alternate navigation, application chrome, or
speculative workflow UI.

The XML uses only beta.4's plugin allowlist: native `overlay_panel`, `ui_card`,
semantic text, built-in icons, `lv_*` objects, and Helix design tokens.
`overlay_panel` owns the header, Back behavior, full-height surface, and native
navigation integration. Each plugin overlay owns one flexible vertical
scroller; horizontal overflow is not used.

The fixed development context is presentation data only. The plugin requests
no permissions and has no Moonraker, G-code, HTTP, storage, slicing, print,
monitoring, result, or Orca communication path.

The exact capability/viewport contract is in
[`../helix-plugin/CAPABILITY_PREFLIGHT.md`](../helix-plugin/CAPABILITY_PREFLIGHT.md),
and native runtime evidence is in
[`../helix-plugin/PREFLIGHT.md`](../helix-plugin/PREFLIGHT.md).

## Issue #2 native development boundary

`scripts/helix-dev` is development infrastructure around the accepted plugin;
it is not another product surface. Its bootstrap verifies a pinned beta.4
source tag/commit, developer binary, release-data archive, and image labels,
then retains them in the user cache.

Interactive mode has two processes:

1. The official beta.4 developer binary runs in an immutable Ubuntu container
   with Helix `--test`, SDL dummy rendering, a private Unix control socket, the
   current plugin mounted read-only through `HELIX_PLUGIN_DIR`, and Docker
   networking disabled.
2. A dependency-free host viewer on reserved trusted-LAN port `8540` requests
   native Helix screenshots and forwards only bounded tap/Home/Back/capture
   actions to that private control socket.

The viewer draws no imitation Orca or Helix interface. Product pixels,
navigation, callbacks, layout, and input dispatch all remain owned by the real
runtime. The host listener cannot connect the container to Moonraker and does
not expose a shell or arbitrary helixctl command.

Capture mode gives every target size its own config and control socket, drives
the complete accepted flow, and records capture-time candidate, product, and
frame hashes to prove exactly what ran and that the product plugin was not
changed. Generated artifacts stay in durable XDG state by default; explicit
promotion retains only the report, matrix, and one final native frame per target
under `docs/evidence/issue-2/`.

GitHub CI covers deterministic Python/XML/manifest/harness policy and verifies
the bounded promoted evidence against the checked-out candidate. Native runtime
capture remains a devbox gate because an exact source build and eleven native
viewport runs are intentionally too heavy for proportionate per-commit CI.

## Issue #4 qualification and host boundary

The canonical implementation checkout remains
`/home/dev/Projects/personal/helix-orca-calibration` on devbox. The existing
`codex/issue-4-temperature-round-trip` worktree isolates Issue #4 from unrelated
canonical changes. Spare is the intended Windows runtime-validation target;
LAPTOP-EC83OFDE is outside this workstream.

Windows setup, isolated runtime execution, and capture use the founder-approved
LAN-only access envelope. A prepared unelevated Windows worker carries command
requests through the existing outbound SSH connection to a private devbox Unix
socket. It needs no Windows listener, service, firewall change, or Tailscale.
The worker executes inside the visible desktop. Commands and a native GUI click
were proven there. The restarted worker passed an actual inherited-pipe capture
regression in 2.11 seconds and remained connected. Transport details
and operational boundaries are in [`SPARE_TEST_ACCESS.md`](SPARE_TEST_ACCESS.md). Source/tests and
devbox execution cannot satisfy the Windows gate. The fixed nightly must use
its own portable directory and marked `--datadir`, preserving the normal Orca
installation and profiles. `WEBVIEW2_USER_DATA_FOLDER` is set only in the
nightly child environment: `--datadir` alone reused normal Orca browser data.
Separate browser process ancestry and data storage were verified after relaunch.
The qualification gate passed after the supported offline local bundle importer
resolved the System-name collision with unchanged fixture JSON. Runtime context
records the original printer's bundle identity and `is_system=false`, while
saved 220, edited 217 and merged 217 remain separate. Normal Temperature
preparation used a separately retained temporary context. Manual selection of
the actual export is required because the lifecycle path is temporary slicing
output. All 1,429 normal settings/profile files remained unchanged after close.

Prefer the Orca-owned dock panel and lifecycle file association. If necessary,
qualify a host-owned modeless window and explicit manual file selection under
the approved Issue #4 fallback authority. UI driving belongs only to isolated
evidence tooling. The mock-only Temperature round trip now proceeds from the completed
actual Windows observations in
[`ORCA_NIGHTLY_QUALIFICATION.md`](ORCA_NIGHTLY_QUALIFICATION.md).

## Issue #4 bounded round-trip implementation

The self-contained Orca `0.4.0` companion freezes the original supported-API
context separately from live selection/settings, verifies a manually selected
file in its host-owned browser, and explicitly writes one immutable request
under plugin storage. Returned JSON must match request, context, file, printer,
filament, current/saved values and setting; duplicates are idempotent, conflicts
and stale results are rejected. Instructions state **not applied**. There is no
network, process/thread, slice hook, UI automation or preset-write path in the
Orca plugin. Lifecycle callbacks notify the page; host reads run through its
supported UI message callback. Modeless fallback remains available.

The separately mounted development bridge uses pinned native overlays,
subjects, plugin storage and mock print APIs. Beta.4 forbids HTTP to local
printer-host addresses, so the proof preserves that protection and transports
real artifacts through existing SSH and supported native storage. Native
request receipt never starts printing. Docker `--network none` and `--test`
prevent any physical route. The accepted product and ordinary harness are
unchanged. All eleven sizes and actual Spare result reception pass; see
[TEMPERATURE_ROUND_TRIP.md](TEMPERATURE_ROUND_TRIP.md).

The separate proof viewer adds bounded native drag input and a single guarded
mock-completion action. Completion requires an already started request in the
owned `--test`, network-none container; it cannot start printing. Native context
labels identify effective values explicitly. Evidence binds the executed
source-built binary and provenance, per-viewport binary hashes, and the imported
ordinary harness in addition to the round-trip sources.


The consolidated Founder Review repair supplies a proof-only native Home resume
tile and restores the stock print-status card, while preserving normal native
Home/Back semantics. Native Finish writes a correlated storage action; the
owned mock driver validates and consumes it. The viewer makes the same existing
completion action prominent and responsive. This changes only mock integration
and review infrastructure, never the accepted shell or upstream navigation.

The proof parks beta.4's synthetic clock before the remote pointer is created,
after a stable entry frame. This keeps completion from being overwritten by
later simulator snapshots. Navigation/update/render queues and the later-created
remote input sampler stay live; pre-existing periodic timers and animations are
paused only in this test runtime. Fresh browser proof verifies both Finish
surfaces and native Home/Back/task return through the terminal 205°C result.
