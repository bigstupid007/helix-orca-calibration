# Helix beta.4 capability and viewport preflight

Date: 2026-10-10

This is the implementation authority for Issue #1's Helix UI. It was completed
before changing the H1 candidate and does not infer behavior from screenshots.

## Pinned material

- HelixScreen tag: `v1.1.0-beta.4`
- Source commit: `13a77bec42616d5c6f4fa397f1d5e12682fa4376`
- Source inspected at:
  `/tmp/helix-h1-preflight-20261010/source-beta4`
- Native runtime: official `helix-screen-ubuntu-22.04` artifact from successful
  upstream Build run `37385776288`
- Runtime SHA-256:
  `ab819714fd469ff32657dc974585ad3bb05270829247da08eb71161a2d5197d0`

Primary sources were `docs/devel/PLUGIN_DEVELOPMENT.md`,
`docs/devel/UI_CONTRIBUTOR_GUIDE.md`, `include/ui_breakpoint.h`,
`src/plugin/plugin_xml_policy.cpp`, `src/plugin/lua_bind_ui.cpp`,
`src/plugin/plugin_overlay_host.cpp`, `include/ui_nav.h`,
`include/overlay_class.h`, `ui_xml/overlay_panel.xml`,
`ui_xml/header_bar.xml`, the `temp-spark` and `led-effects` examples, and the
plugin/navigation/layout tests.

The repository's `references/helixscreen` checkout is useful general reference
material but is not beta.4 and is not the authority for this implementation.

## Verified plugin UI capabilities

### XML primitives

Beta.4's closed plugin XML policy permits:

- LVGL `lv_*` widgets;
- `component`, `view`, `api`, and `prop` structure;
- `style`, `remove_style*`, `play_timeline_event`, `bind_*`, and `event_cb`;
- the Helix components `overlay_panel`, `ui_card`, `icon`, `text_heading`,
  `text_body`, `text_muted`, `text_small`, `text_xs`, and `text_tiny`;
- `plugin_canvas`; and
- components owned by the same plugin.

The only plugin XML event callback is `plugin_event`. Its `user_data` selects a
Lua handler using `<plugin-id>__<event>[:argument]`. `ui_button` is not in the
allowlist, so a plugin action uses an allowed `lv_button` styled with Helix
tokens. Screen-load/create callbacks, application panels, nav-bar panels, and
raw LVGL object access from Lua are not plugin capabilities.

### Home tile

A tile is declared by `manifest.json.widgets`, appears in the native home
widget catalog under **Plugins**, is never enabled or placed automatically, and
has one instance. The user enables the plugin and adds the tile. Saved placement
survives plugin disable/absence. Widget spans are manifest grid-cell requests;
the home grid remains owned by Helix and may normalize/resize the tile. H1's
3x2 request rendered as 4x2 in the accepted 800x480 runtime and avoided the
clipping seen with the first 1x1 request.

### Plugin surface and navigation

`helix.ui.overlay(component[, attrs])` creates only a component owned by the
plugin, registers it with the native navigation manager, and returns a handle
whose `close()` method closes that overlay. Opening the same component while it
is already present is a no-op. Closing it removes the instance; it can then be
opened again. Plugin unload closes all of its overlays.

`overlay_panel` owns a full-height native header and content slot. Its inherited
Back control calls Helix's `on_header_back_clicked`, so a plugin must leave that
default intact. A second plugin overlay pushed from the first is a native stack
entry; Back pops it and reveals the first.

“Full-screen plugin surface” means the Helix-owned overlay behavior, not a
plugin-created screen or application shell. From Home, beta.4 classifies the
first plugin overlay as a transient layer: it is 100% high and Helix sizes its
width to `screen - native navigation - #space_lg`. The global Helix navigation
remains visible. The plugin cannot replace that navigation or register its own
application-level navigation.

### Native visual conventions

Plugin XML can use responsive Helix tokens including `#screen_bg`, `#card_bg`,
`#primary`, `#text`, `#text_muted`, `#text_on_primary`, `#space_*`,
`#button_height`, `#border_radius`, and the base `#font_*` tokens. Semantic text
and card components are preferred. Size-suffixed font tokens are rejected for
plugins; base font tokens resolve to the linked face for the active breakpoint.

The plugin therefore uses Helix-owned overlay/header chrome, `ui_card`, semantic
text, built-in icons, responsive spacing, and a token-styled `lv_button`. It
does not draw an independent sidebar, toolbar, stage navigation, or dashboard.

## Viewports, breakpoints, and scaling

Breakpoints use `min(width, height)` for fonts, spacing, widths, and neutral
tokens. Height tokens use the actual vertical dimension. The exact source
breakpoints are Micro <=272, Tiny 273-390, Small 391-460, Medium 461-550, Large
551-700, XLarge 701-1000, and XXLarge >1000 pixels.

The required Issue #1 runtime matrix is the union of beta.4's shipping geometry
sweep and its documented common contributor targets:

| Viewport | Runtime mode | Why it is in the matrix |
| --- | --- | --- |
| 480x272 | standard | Shipping Micro; documented smallest supported size |
| 272x480 | portrait | Shipping rotated Micro |
| 480x320 | standard | Shipping Tiny |
| 480x400 | standard | Shipping Small |
| 800x480 | standard | Shipping/default Medium |
| 480x800 | portrait | Shipping/documented portrait |
| 1024x600 | standard | Shipping Large |
| 1280x720 | standard | Shipping/documented XLarge |
| 1080x2400 at 405 DPI | portrait | Shipping phone-class geometry and scale check |
| 1920x480 | ultrawide | Documented ultrawide target |
| 320x1480 | portrait | Documented tall-portrait narrow-axis target |

Shipping printer panels measure at or below the 225-DPI scaling deadband, so
their UI scale is 1.0. Above 225 DPI beta.4 applies
`1 + (dpi - 225) * 0.0032118`, capped at 2.0; the 405-DPI check resolves to
about 1.578. The scale enlarges tokens/fonts and can reduce home-grid track
count. Plugin layouts must therefore use responsive tokens and flexible width,
not fixed desktop dimensions.

## Scrolling and overflow contract

`overlay_panel` itself is non-scrollable. A plugin that may exceed the content
slot must provide a `width="100%"`, `flex_grow="1"`, vertically scrollable child.
That child owns vertical overflow and touch scrolling. Nested cards/rows remain
content-height and non-scrollable. Horizontal overflow is not an accepted
fallback: content uses the available width, responsive padding, and stacked
rows so it fits the narrow axis.

The final candidate must be loaded in the native beta.4 runtime at every matrix
viewport above. At each size the test must prove discovery/enablement, tile
rendering and opening, chooser rendering, Temperature navigation, native Back,
Start toast, close/reopen, and absence of horizontal clipping. Vertical content
may scroll only inside the declared overlay content container.

## Issue #1 implementation boundary

The supported product path is:

`native Helix home tile -> calibration chooser overlay -> Temperature overlay`

Visible functionality is limited to the fixed development context, the real
Temperature module and range, and the existing Start callback toast. There are
no visible Generate/Run/Result stages, Apply-to-Orca control, custom sidebar,
Moonraker action, G-code action, storage, networking, print control, or future
calibration placeholders.

The accepted baseline presents the same four context values in a compact
two-line card above the dominant calibration list. Future modules extend the
local registry and add plugin-owned native detail components inside this shell;
they do not redefine navigation or application chrome.
