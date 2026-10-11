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
