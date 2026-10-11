# Findings

## Issue #1 verified HelixScreen baseline

- Authority: HelixScreen `v1.1.0-beta.4`, commit
  `13a77bec42616d5c6f4fa397f1d5e12682fa4376`.
- The local `references/helixscreen` checkout predates the Lua framework and is
  not the Issue #1 runtime authority.
- Plugin XML has a closed allowlist. `overlay_panel`, `ui_card`, semantic text,
  built-in icons, `lv_*` widgets, and base responsive design tokens are valid;
  plugin events route only through `plugin_event`.
- “Full-screen” is a Helix-owned full-height overlay. Global Helix navigation
  remains visible, and inherited Back behavior owns the native overlay stack.
- `orcacal` requests no permissions. Its only Lua actions open the chooser,
  select a registered native detail component, and show the local Start toast.
- Temperature is the only registered module and exposes only the fixed
  `230°C -> 190°C` range plus **Start**.
- The final context card preserves all four values in two responsive lines. Its
  measured height fell from 150 to 90 px at 800x480 and from 98 to 59 px at the
  smallest/narrow targets. Temperature renders remained pixel-identical at
  800x480 and 272x480.
- Network-disconnected native beta.4 tests passed discovery, enablement, tile,
  chooser/detail navigation, inherited Back, Start toast, close/reopen, and
  horizontal-fit checks at all eleven supported target geometries.
- The accepted chooser/detail shell is the baseline for future modules. They
  extend the registry and add native detail components without replacing
  navigation, application chrome, or visual language.

Detailed capability findings and runtime evidence are in
[`../helix-plugin/CAPABILITY_PREFLIGHT.md`](../helix-plugin/CAPABILITY_PREFLIGHT.md)
and [`../helix-plugin/PREFLIGHT.md`](../helix-plugin/PREFLIGHT.md).

## Issue #2 native development harness

- Beta.4's documented fastest plugin loop is real: when
  `HELIX_PLUGIN_DIR` is set and hot reload is enabled, `PluginDirWatcher`
  rescans changed plugin directories and `PluginHost` reloads the enabled
  plugin without restarting the process.
- The optional Ubuntu developer artifact from Build run `37385776288` contains
  the remote-control subsystem, but it expires. Durable bootstrap builds exact
  public commit `13a77bec42616d5c6f4fa397f1d5e12682fa4376` and its 14 recorded
  recursive submodule revisions with the repository-owned pinned builder.
- `--test` supplies the mock printer and enables the private control server;
  no `--real-moonraker` flag is used. Docker `--network none` provides an
  independent enforcement boundary beyond the CLI selection.
- SDL dummy rendering still uses the real LVGL widget lifecycle and native
  snapshot implementation. Browser review can therefore show the captured
  native framebuffer and forward Helix synthetic pointer events without a
  hand-built product emulator.
- The first deterministic mock run exposed beta.4's separate first-run tour.
  Source inspection identified `/tour/completed=true` and
  `/tour/last_seen_version=1`; the harness now seeds those alongside
  `wizard_completed` so the accepted tile is unobstructed.
- Port `8540` is reserved to the on-demand harness in the canonical shared
  devbox registry. The authorized Mac mini independently received HTTP 200
  from the exact UI, health, and native-frame URLs.
- All eleven target runs passed discovery, tile render, chooser, Temperature,
  Start toast, native Back, reopen, and horizontal-fit assertions. The report
  binds the exact harness/CI candidate, product files, ordered matrix, assertion
  set, and all 44 generated frames; the promoted evidence retains one final
  native toast frame per viewport and is reverified in CI.
- Issue #1's recorded 25-test result combined seven committed Helix tests with
  18 unrelated uncommitted Orca tests already present in the canonical dirty
  checkout. Issue #2 adds fifteen committed harness tests, so its candidate CI
  suite contains 22 while the current working tree runs 40.

## Issue #4 Windows access checkpoint — 2026-10-11

- Current Issue #4 authority and shared Development System GitHub main
  `de8d7a66e58aca81fc9b44cda6a6463ffcea47ff` were checked. The shared local
  checkout has the same tree; its working tree was not changed.
- The owner identifies Spare as the intended interactive Windows target with
  Orca installed. This session's shell runs on devbox/Linux; it has not executed
  Windows commands or inspected the installed Orca build.
- Spare resolves to `192.168.1.155`. An established TCP connection from that
  address to devbox's SSH listener proves the client-to-devbox direction.
- A batch-mode SSH attempt to Spare with strict host-key checking and an
  eight-second connection bound timed out before authentication. Separate
  five-second TCP checks of ports 22, 3389, and 5985 also timed out. No host key,
  credential, firewall, service, or access configuration was changed. These
  observations do not distinguish filtering from an unavailable service.
- Existing Tailscale discovery lists LAPTOP-EC83OFDE separately and no Spare
  peer. The laptop was not used as a substitute. This session exposes no
  Windows-local execution or desktop-control tool.
- Windows qualification remains blocked on existing authorized execution and
  desktop access. No Windows installation/settings were touched, no runtime
  pass is claimed, and round-trip implementation has not begun. The detailed
  continuation condition is in
  [`ORCA_NIGHTLY_QUALIFICATION.md`](ORCA_NIGHTLY_QUALIFICATION.md).

## Issue #4 LAN-only access approval and prepared worker

- The founder explicitly approved minimum LAN-only command and interactive GUI
  testing access on October 11. The exception is now in GitHub Issue #4; no
  Tailscale, public exposure, or unnecessary security change is approved.
- The existing devbox authorized-key inventory includes Spare's client key.
  The prepared worker therefore reuses existing SSH authentication and pins
  devbox's public host identity. No credential, account, inbound Windows
  service, firewall rule, or elevation is introduced.
- Local bridge tests exercise a real private Unix-socket/stdio round trip,
  permissions, wrong-host/route/session rejection, stale-response termination,
  duplicate-worker exclusion, request bounds, and frozen-bundle integrity.
- The native Windows GUI smoke test is prepared but has not run. Windows
  execution and GUI access remain unproven until the owner starts the worker
  in the visible desktop and the agent validates the resulting access. This
  checkpoint is not a qualification pass or round-trip implementation.

## Issue #4 actual Windows access and launch checkpoint

- The worker identified `SPARE`, `AzureAD\ChrisDeMichael`, session 1,
  unelevated execution, and direct LAN SSH from `192.168.1.155` to
  `192.168.1.114:22`. Commands executed in the visible desktop.
- The initial foreground-only smoke test correctly refused input. Using a
  topmost test window and native point ownership allowed an actual button
  click without changing foreground-lock policy. The cropped native screenshot
  was returned, hash-verified, and visually inspected; private evidence is in
  XDG state. This proves access only.
- The fixed nightly and test inputs were transferred to separately marked
  Windows directories, with archive and executable/DLL hashes checked. A
  private normal-profile/settings fingerprint baseline was retained.
- The first nightly launch used an unsupported CLI flag. Although the exact
  source contains an internal `--no-single-instance` parser, the CLI option
  registration is commented out. Windows recorded a startup crash; the flag
  was removed rather than patching Orca or replacing the fixed target.
- The original-argument/portable-working-directory retry then exposed the
  testing worker's unbounded asynchronous pipe-EOF wait. The bridge timed out.
  Capture waits are now bounded; actual Windows regression requires one
  owner-only restart. Retry process/UI state remains unobserved.
- Normal Orca was not closed or selected for input; product code and accepted
  Helix behavior remain unchanged. Qualification and round-trip work remain
  gated until actual context/panel/lifecycle/export proof is complete.
