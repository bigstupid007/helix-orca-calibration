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
