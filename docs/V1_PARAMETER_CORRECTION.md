# V1 functional parameter correction — Program #14 / PR #15

Status: functional acceptance passes. Independent actual800×480 native pointer,
drag and keypad input changed all five requests, which matched actual Windows
DirectoryEvents and coordinator-journal readback exactly. All14 fresh captures,
source bindings and full managed cleanup pass. Flow Perfectionist reaches genuine
parity-qualified Review; four unavailable generators retain their values and actual
blockers. The [focused evidence](evidence/issue-14/parameters/README.md) supersedes
earlier fixture-driven control qualification claims.
Shared Development System main remains `4a42a94`; application main `523bc5d`,
starting candidate `15e2e26`. Scope remains one program and one unmerged PR.

## Controlling Founder source

The 2026-10-18 correction requires “Fix the functionality, not the visual design”
and “Independently exercise each calibration's parameter controls through the actual
native UI, change values from their defaults, and verify the exact changes propagate
through the request contract to the Orca coordinator.” Broader Product Design work
is deferred. No physical printing, deployment, profile writeback or merge is allowed.

Here is what the printer owner does: choose a calibration on Helix, edit its required
parameters (or choose a fixed YOLO mode), request preparation, then see the exact
selected values and either the genuine preparation/blocker or a parity-qualified job.
Existing separate Confirm and deliberate Start, exact-job monitoring, evaluation and
NOT APPLIED return remain. Blocked generation must retain the request and its values;
receiving the request cannot start a printer. This is the already approved workflow,
with missing configuration functionality restored, not a new workflow approval gate.

## Frozen common parameter contract

| Kind | Request parameters and defaults |
| --- | --- |
| Temperature | `{start:230,end:190,step:5,scale:true}`. Start/End editable whole 5°C increments. Step fixed at 5, shown read-only. Scale tower remains editable; the operator trial changes true to false. |
| Flow Ratio YOLO | `{pass:1}` Recommended or `{pass:2}` Perfectionist. Fixed additive offsets from original flow: Recommended −.05…+.05 by .01 (11); Perfectionist −.04…+.035 by .005 (16, asymmetric). Archimedean Chords remains fixed. |
| PA Pattern | Editable `{start,end,step}`. Direct Drive 0/.08/.005; Bowden 0/1/.05. Extruder type selects defaults only, not a generation parameter or profile change. |
| Retraction | Editable `{start:0,end:2,step:.1}` in mm. |
| MVS | Editable `{start:5,end:20,step:.5}` in mm³/s. |

Request schema/identity fields are unchanged. Existing Recommended parameters/input
digests remain unchanged. Perfectionist cannot borrow Recommended qualification.
The offer optionally adds `extruder_type: direct_drive|bowden|unavailable`; it is
derived only from the current effective serialized `extruder_type`. Unknown/missing
must be labeled unavailable; generic Orca Direct Drive defaults are explicitly
identified, with a deliberate action to use Bowden defaults. No saved-value fallback.

Retain existing V1 resource bounds: Temperature Start 160..500, End 155..495, descending
at least 5°C; PA 0..5 and Step 0.001..5; Retraction 0..20 and Step 0.001..20; MVS 0.01..200 and
Step 0.001..200. Ranges need End≥Start+Step and at most 1000 increments. These maxima
are V1 resource envelopes, not claims about native Orca physical limits. Existing
128-result-choice evaluation limit must report an understandable actual blocker.
No typed value is rounded, clamped or silently replaced. Local field validation and
Generate/restore validation match the Python contract. Request/prepared/result
validation retains exact values. A backend receives a defensive copy of the request.

## Verified source basis

Exact Orca `6a7763f0`, `src/slic3r/GUI/calib_dlg.cpp`: Temperature defaults at lines
480/488, fixed step496, floor-to5 UI behavior544–560 and predicates581–598; PA Pattern
reset defaults289–333 and validation337–344; Retraction defaults1070–1095 and
predicates1130–1143; MVS defaults695–720 and predicates753–766; YOLO choices1790–1791
and dispatch1872–1883. Plater17260–17283 selects separate linear/fine assets.
CalibUtils184–220 uses .05/.035 positive additive speed envelopes. Pinned beta.9
allows owned overlays, buttons, labels and subjects; its app text-input API is not
plugin-accessible. A bounded native numeric keypad restores free numeric entry using
supported APIs; no upstream patch or speculative host API is needed.

## Independent acceptance and proof boundaries

The required acceptance uses one healthy focused 800×480 native managed run,
with browser pointer/drag/keypad input. Change all required numeric fields from
defaults, toggle Temperature Scale true→false, and choose YOLO Perfectionist.
Read-only native geometry is allowed; `ctl.set_value`, subject assignments and seeded
requests do not prove operator selection. Retain exact native request, unchanged offline
transport input, real Coordinator journal/dispatch and preparation/status/result bindings.
Use real routing/generation, with genuine blockers; no manufactured qualified prepared
objects. Returned transport into the network-none native container is explicitly test
transport emulation. It is not a Moonraker or physical-print qualification.

Qualified generation needs independently prepared matching Orca-native reference and
actual executable/invariant parity. Changed YOLO must affect actual output; missing
matching reference blocks qualification. Existing references/profile payloads stay on
SPARE, with public source/assets and bounded request metadata using existing approved
test access. No normal profiles/settings change. A source-only test can protect
immutability, but cannot replace the native operator proof.

Run focused affected checks, review the integrated delta independently, and let required
candidate CI run its existing regression. Do not repeat the eleven-size 396-frame matrix
or broad certification unless a concrete material shared invariant changes. Preserve
that historical complete capture; do not label it qualification of changed controls.


## Evidence checkpoint and final proof

The owned numeric keypad, fixed Temperature step, editable Scale, both YOLO modes,
Direct Drive/Bowden default actions and exact draft/request copies are implemented.
A separate native operability smoke passed with an explicitly unavailable local
generator configuration; it proved control operation and real Coordinator blocker
retention, not production generation. Later actual Windows observations include
all five unchanged selected requests and a genuine qualified Flow review. Both
Recommended and Perfectionist have separate matching native-reference parity;
see [Windows generation evidence](evidence/issue-14/parameter-windows/README.md).

The final complete14-frame operator capture now passes its health, current-source
and resource-lifecycle gates. Partial captures and earlier HTTP/resource-guard/
baseline-drift failures remain private and unpromoted. The completed record below
binds all exact requests/events/journals/statuses and owned cleanup. Independent
delta review and required candidate CI remain separately recorded. No additional
Founder feature launch is required.

## Completed focused acceptance

Managed run `b04728721c2741bd8d05b3001a343cdf` passes full operator, source and
lifecycle verification. The promoted report SHA is
`a0386c8cb0edb96976e8e3ec411980ed9dd506052103a66de46730ee5775ece2`;
operator report SHA is
`f39b272a459bc309fb3cb34cab9e5cd1aa6bf2fa2b7efce1e80e59182ba85449`.
All14 fresh frames pass, with101 native operator actions and no browser errors or
retries. The exact values, genuine blockers and native-selected Windows parity
are in the [focused record](evidence/issue-14/parameters/README.md). Separate
Confirm/Start and completion-dependent evaluation remain intact; this focused
run stops at Review and makes no execution/completion claim. Seven deliberate
record tamper cases are rejected, including changed selected/transport values,
false blocked qualification, failed parity, incomplete lifecycle, historical
relabeling and wrong run identity. No broad certification repeat was needed.
