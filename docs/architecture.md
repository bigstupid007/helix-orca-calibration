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
