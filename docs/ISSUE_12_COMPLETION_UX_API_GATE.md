# Issue #12 — immediate Temperature presentation and accepted beta.9 limit

The Founder explicitly authorizes `helix.ui.overlay()` for the controlled
personal-printer test and **accepts temporary overlap with an existing native
HelixScreen dialog**. This supersedes the earlier modal-coordination blocker
recorded at 7cc0b4d. The missing modal-aware API is still a real host limitation;
it is an accepted test risk, not a technical claim of modal safety.
No printer deployment, physical print, notification preference change, timed
modal workaround or upstream patch is authorized.

## Verified supported API

Exact beta.9 source is `e5cdc5dc523280bc3ead681a4f229bf84dfa726a`.
The documented [plugin UI API](https://github.com/prestonbrown/helixscreen/blob/e5cdc5dc523280bc3ead681a4f229bf84dfa726a/docs/devel/PLUGIN_DEVELOPMENT.md#helixui-srcpluginlua_bind_uicpp)
provides `helix.ui.overlay(component, {on_close=...})`. It opens an owned native
component over the current screen; an already-open component is a no-op returning
its existing handle, preserving its original attributes/close callback. Native
Back closes it; unload closes all owned overlays. No product navigation API is
invented. Automatic presentation uses a distinct owned `orcacal__auto_temperature`
component generated from the unchanged Temperature XML by renaming only owned
widget names. Layout, subject bindings, event actions and visible text remain
identical. This is necessary because the host's duplicate-component no-op does
not raise a manual Temperature component buried beneath Print Status. Native Back
closes the automatic view and restores the native page. The generated derivative
tracks its own wizard/manual Temperature/cancel-confirmation handles using
supported handler replacement and close callbacks. After the unique automatic
push is accepted, it retires only those owned preparation views. Thus dismissing
the chooser and later backing out of Print Status cannot resurface an old plugin
chooser. Native Print Status and unrelated dialogs remain. Guarded callbacks and
nil-first retirement avoid a stale close clearing a newer handle; failed opening
leaves manual views intact.

[PluginOverlayHost::open](https://github.com/prestonbrown/helixscreen/blob/e5cdc5dc523280bc3ead681a4f229bf84dfa726a/src/plugin/plugin_overlay_host.cpp#L25)
creates the owned component under `lv_screen_active()` and queues native navigation.
[NavigationManager](https://github.com/prestonbrown/helixscreen/blob/e5cdc5dc523280bc3ead681a4f229bf84dfa726a/src/ui/ui_nav_manager.cpp#L1817)
raises it; a [native modal backdrop](https://github.com/prestonbrown/helixscreen/blob/e5cdc5dc523280bc3ead681a4f229bf84dfa726a/src/ui/ui_modal.cpp#L671)
is a sibling. [`bring_to_front`](https://github.com/prestonbrown/helixscreen/blob/e5cdc5dc523280bc3ead681a4f229bf84dfa726a/src/ui/ui_effects.cpp#L217)
re-raises chrome without ModalStack arbitration. Thus the chooser can cover a
built-in completion dialog. The [completion observer](https://github.com/prestonbrown/helixscreen/blob/e5cdc5dc523280bc3ead681a4f229bf84dfa726a/src/print/print_completion.cpp#L397)
skips its notice on Print Status, but elsewhere may show a modal/toast/nothing
according to existing preferences. The plugin neither observes nor changes that
preference. No priority, deferral or built-in-modal-close detection is claimed.

## Isolated presentation and suppression

`integration/temperature-print/presentation.lua` is appended only to the separate
generated derivative. It owns runtime arming, a session-scoped claim and the
single immediate overlay call. Replace its `open()` adapter when Preston's
queued-overlay API becomes available, with new qualification at that time.
The native verifier still owns identity, freshness, Start/cancel intent, observed
running, live exact filename/job and independent completion digest checks.
Only their accepted `complete` transition may claim/present. The claim binds
request/origin/job/digest and is written in the same storage snapshot as success.
The automatic latch clears before persistence/open. No second popup follows a
repeat event or a changed later digest for the same session. Overlay failure
leaves manual reopening available and is not automatically retried.

[Storage semantics](https://github.com/prestonbrown/helixscreen/blob/e5cdc5dc523280bc3ead681a4f229bf84dfa726a/docs/devel/PLUGIN_DEVELOPMENT.md#helixstorage-srcpluginlua_bind_iocpp)
explicitly defer disk writes about 0.5 seconds; no flush/commit callback exists.
Immediate presentation and crash-durable claiming cannot be atomic. Every load
starts disarmed. A retained completion gains a recovery-suppression marker and
enters normal unverified recovery; no overlay opens merely on load. A restored
unclaimed running session may rearm only on fresh verified same-job live printing.
If a crash lost a completion claim while older printing bytes remained on disk,
a live already-complete job cannot rearm it. Fresh reverified success remains
manually reachable without repeating the popup. A crash before the actual queued
presentation can therefore suppress an unseen popup. This deliberate at-most-once
policy favors no repetition; it does not claim exactly-once visual delivery.

Dismissal does not consume proof, context or the selection. Normal manual
reopening remains Home → Orca Calibration (Pick) → Temperature. Existing
fail-closed live return/recovery gates still apply if the printer disconnects,
changes job or becomes uncertain; this build does not weaken those checks.
Committed waiting/returned results and exact originating ACK behavior remain
unchanged, exactly-once and NOT APPLIED. No new end-to-end replacement-job delivery
is claimed.

## Native proof and preserved compact tile

The qualification uses actual pinned beta.9 native overlays and private test-only
subject inputs, Docker network-none and read-only runtime/plugin mounts. Native
Print Status is opened through the runtime's own demo route, Controls through its
native navigation route; neither route exists in shipping plugin code. Product
presentation uses only the documented overlay API. The renewed complete matrix
records Home/Print Status/Controls before/after navigation (including manual
Temperature buried beneath Print Status), dismissal, duplicate,
restart and lost-write recovery proof, plus lifecycle rejection and result return.
Its final status/counts belong in readiness and Product Preflight, separate from
the actual c1eee43 physical success.

The 1×1 manifest cells / 2×2 internal tracks and allowed XML tile are unchanged.
Existing physical saved placements are not migrated. No fixture result is a claim
of physical installation or another real print.
