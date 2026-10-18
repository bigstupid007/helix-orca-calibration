# Issue #12 automatic completion chooser — beta.9 API gate

**BLOCKED under the current no-upstream-change constraint.** This conclusion
was independently verified at exact beta.9 source
`e5cdc5dc523280bc3ead681a4f229bf84dfa726a`; no unsupported navigation API,
fixed-delay popup, upstream patch or physical deployment is included.

The Founder approved automatically opening the Temperature result chooser over
Print Status, Home or another page only after independently verified same-job
success, with modal priority, dismiss/reopen, durable suppression for that
completion, recovery and immutable result/context handling. This is distinct
from the compact home widget and from the successful first physical calibration.

## Verified capability and blocker

The documented [plugin UI API](https://github.com/prestonbrown/helixscreen/blob/e5cdc5dc523280bc3ead681a4f229bf84dfa726a/docs/devel/PLUGIN_DEVELOPMENT.md#helixui-srcpluginlua_bind_uicpp)
provides `on`, `toast`, `confirm`, `overlay` and `text_width`. `on` handles the
plugin's own XML/action callbacks. The printer API exposes connection, print
state, filename, progress and temperatures. Neither API exposes native modal
visibility, navigation state, a modal-close event or an idle-presentation queue.

[PluginOverlayHost::open](https://github.com/prestonbrown/helixscreen/blob/e5cdc5dc523280bc3ead681a4f229bf84dfa726a/src/plugin/plugin_overlay_host.cpp#L25)
creates a plugin component under `lv_screen_active()` and queues a native
navigation push. [NavigationManager](https://github.com/prestonbrown/helixscreen/blob/e5cdc5dc523280bc3ead681a4f229bf84dfa726a/src/ui/ui_nav_manager.cpp#L1817)
then brings that overlay to the foreground. The
[built-in modal](https://github.com/prestonbrown/helixscreen/blob/e5cdc5dc523280bc3ead681a4f229bf84dfa726a/src/ui/ui_modal.cpp#L671)
is a sibling backdrop under the same screen.
[`bring_to_front`](https://github.com/prestonbrown/helixscreen/blob/e5cdc5dc523280bc3ead681a4f229bf84dfa726a/src/ui/ui_effects.cpp#L217)
only re-raises registered screen chrome, without preserving ModalStack priority.
Opening a plugin overlay after a completion modal can cover that modal.

The [built-in completion observer](https://github.com/prestonbrown/helixscreen/blob/e5cdc5dc523280bc3ead681a4f229bf84dfa726a/src/print/print_completion.cpp#L397)
skips its notification on Print Status, but off that page may show a modal,
a toast or nothing according to the existing alert preference. It emits no
plugin callback when the modal closes. Neither changing that preference nor
assuming it is off is authorized. A fixed timer cannot prove dismissal; a
plugin confirmation could itself cover the built-in dialog.

The current candidate therefore retains manual reopening through the native
Orca Calibration tile and Temperature entry. It does not claim automatic opening
from Print Status, Home or another page, dismissal suppression, or safe modal
arbitration. Synthetic lifecycle tests do not qualify an unimplemented feature.
The first real returned 220°C result must not reopen from stale completion data.

## Concrete host-support proposal — not an implemented API

A separately reviewed host change could offer modal-aware queued presentation
of a plugin-owned overlay. The host must serialize it with native modal creation
and navigation, preserve all app/safety modal priority, and report actual
presentation/closure or cancellation to the plugin. It must cancel queued work
on plugin unload and avoid resurrecting a closing overlay. Merely exposing a
busy boolean leaves a race between checking it and the deferred navigation push.

Once such support exists, the plugin can persist a completion-bound presentation
record, present only a fresh independently verified owned success, mark the
actual presentation durably, suppress repeat presentation after dismissal and
restart, and retain manual tile reopening without changing the pending result.
Qualification must exercise modal arrival before and during queued presentation,
Print Status/Home/other pages, dismissal, reopen, restart, duplicates, unrelated
jobs, failure, cancellation, uncertainty and the exact original-context return.

That host work or a deliberately weaker UX policy requires a changed Founder
scope decision. The current instruction explicitly excludes upstream patches;
this proposal does not authorize one.

## Compact tile boundary

The documented manifest span supports a fresh **1×1** placement and native
XML supports its icon, full Orca Calibration identity, short lifecycle status
and tap-to-open handler. Existing saved placements override a new manifest's
default; the permissionless plugin cannot migrate a saved 3×2 dashboard entry.
The test fixture requests a fresh logical 1×1 placement (2×2 internal tracks;
`plugin_manifest.cpp` converts each declared cell to two tracks). It does not prove migration or
change the real home dashboard. Any later authorized installation uses native
Home editing/removal and re-addition if its old placement is retained.
