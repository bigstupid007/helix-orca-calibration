# Native parameter controls — functional correction

> **Current parameter authority:** the beta.12 V2 path retains these native
> controls while mirroring pinned current-Orca domains, adding the explicit YOLO
> pattern and optional PA acceleration/speed lists, and representing large valid
> ranges without eager allocation. Historical `NOT APPLIED` statements below
> describe the earlier V1 candidate only. See the
> [amendment record](V1_CURRENT_UPSTREAM_REBASE.md).

Current source replaces finite numeric dropdowns with editable native value
buttons and a bounded owned numeric keypad. It does not redesign the accepted
shell, compact home tile, job/result navigation, Confirm/Start, monitoring,
completion or original-context NOT APPLIED return.

Temperature accepts editable Start/End in whole5°C increments; Step5 is read-only.
Scale remains an explicit boolean toggle. Flow selects Recommended or Perfectionist
fixed additive sample sets, without editable offsets. PA, Retraction and MVS
expose numeric Start/End/Step. PA's deliberate Direct Drive/Bowden-default buttons
populate the shared defaults only; no extruder/profile setting is changed.
Unavailable effective extruder type is explicitly identified, with generic Direct
Drive initial defaults. Every bound is a V1 resource envelope, not a printer limit.

The builder checks catalog bounds against `PARAMETER_LIMITS`, validates common
`DEFAULTS`, and embeds common `PA_DEFAULTS`. Native input validates field bounds,
Temperature integer/multiple5 and boolean types, exact parameter shapes and the
cross-field range/sample envelope. Set commits the keypad buffer; Back dismisses
it. Draft fields are retained independently through close/reopen and offer updates;
a new offer never silently resets edited values. A submitted request copies the
scalars, and active request controls refuse further editing. Stored drafts are
accepted only after field/shape checks; submitted/recovered requests also require
full range validation.

A known blocked capability does not discard the operator's request. Valid numbers
are persisted as `requested` for the actual coordinator to accept and report its
specific real blocker. Only missing context or invalid parameters block locally.
No request or parameter action starts printing or applies a profile value.

The exact beta.9 source is `e5cdc5dc523280bc3ead681a4f229bf84dfa726a`.
Its [plugin XML policy](https://github.com/prestonbrown/helixscreen/blob/e5cdc5dc523280bc3ead681a4f229bf84dfa726a/src/plugin/plugin_xml_policy.cpp)
allows generic `lv_*`, owned subjects, `plugin_event` and native overlays. It excludes
the app's `text_input` widget, so this implementation does not assume the built-in
numeric-keypad API is available to plugins. The pinned helix-xml gitlink
`04eb969355d6368097cbc04d251e7487154d92d3` has no usable keyboard-to-textarea XML
hookup; owned buttons/labels therefore implement numeric input using the documented
[plugin UI API](https://github.com/prestonbrown/helixscreen/blob/e5cdc5dc523280bc3ead681a4f229bf84dfa726a/docs/devel/PLUGIN_DEVELOPMENT.md#helixui-srcpluginlua_bind_uicpp).
Dropdown `bind_value` is documented and implemented as two-way; the previous
operator selection failure is not relabeled as a proven host binding defect.

Focused builder/wiring checks are source/unit evidence only. The controlling
acceptance is independent actual800×480 pointer/drag/keypad input through the LAN
viewer, preserving unchanged requests through the offline transport into the real
coordinator. No `ctl.set_value`, direct subject assignments or seeded requests count
as operator proof. Generation/parity remains real or reports a genuine blocker.
The independent LAN/real-generation acceptance remains pending. A separate bounded
800×480 operability smoke passed using actual private pointer/keypad input and
transport-only fragmented offer/status delivery into an actual Coordinator. All
five edited requests remained exact after reopen: Temperature240/200/5/true,
Perfectionist2, PA.1/.5/.02, Retraction.2/1.4/.2 and MVS3/18/1. Direct Drive/Bowden
default actions and the keypad's bottom Set control also worked. The coordinator
truthfully blocked because this smoke supplied no generator configuration; it
created no prepared or qualified object. Confirm/Start remained locked.

ManagedRun`c9b2471c36394e24ba406e4921d6951a` completed exit0 with runtime-clear and
empty error lists, after exact owned-container/process teardown. The private smoke
report SHA-256 is
`ac49ba686c7246b8e3a0a8c029c43fd7edaf0dc4ceac762c130cee70ffca8021`.
Earlier failed probe records remain preserved: they exposed a1023-byte test-subject
transport limit and stale geometry before native deferred layout settled. Bounded
fragment transport and a fresh native frame before geometry corrected the probe;
no product source change was needed after7344f04. This is not the independent
browser/real-generation acceptance or a physical/runtime deployment claim.

The complete historical396-frame fixture capture remains bound to its earlier
sources and does not qualify these changed controls.
