# Issue #12 Build Program — physical milestone and bounded UX follow-up

Continue [Issue #12](https://github.com/bigstupid007/helix-orca-calibration/issues/12)
and [PR #13](https://github.com/bigstupid007/helix-orca-calibration/pull/13),
open and unmerged. Current shared Development System main is
`4a42a944b344427c8f925241191595eb57c6949c`, verified against GitHub;
application main remains `89165d15993ccfcd065b299e1980bb19749fdcaf`.
Direct Founder instructions and application AGENTS.md govern this continuation.

## Completed physical milestone

The corrected readiness baseline is exactly
`c1eee4374fb0286e1a3973d8e29107bfc64ee99f`. It uses the qualified native October 15
Orca export with **225/220/215°C bottom to top**, normal nozzle **220°C**,
confirmed filament, no hard duration/combined-estimate gate and no additional
spool-label checkpoint. Its 484,552 bytes, 75 layers, 12m00s informational estimate
and `PRINT_START BED_TEMP=60 EXTRUDER_TEMP=225` are preserved.

The Founder separately authorized exactly one physical test, initiated only by
his deliberate physical HelixScreen Start. It succeeded. Read-only follow-up
matches the retained completed journal and owned job to independently completed
printer history, the native returned **220°C** result, the exact originating
Orca receipt and delivered status. The Founder also confirms the actual chooser
unlocked and Orca displayed **NOT APPLIED**. No settings were written back.
[Actual physical evidence](evidence/issue-12/physical-first/README.md) remains
separate from all synthetic validation. Private operational files and rollback
product trees are retained with a hash manifest; `c1eee43` remains recoverable.

## Founder-approved subsequent workflow

The Founder requests two UX changes. After the existing independent same-job
completion checks succeed, the native Temperature result chooser should open
over Print Status, Home or another native page,
allow dismissal without losing the result, offer easy reopening and avoid
repeated presentation for the same dismissed completion, including recovery.
Unrelated, failed, cancelled, uncertain or unverified jobs must not activate it.
Result selection/delivery and original Orca context remain immutable.

The Orca Calibration home widget should request **1×1** instead of 3×2, retain
its icon, readable identity/status and tap-to-open behavior, and fit the native
800×480 target plus the supported matrix. The chooser/dashboard are otherwise
unchanged. Exact documented beta.9 API support must be verified before building.
No upstream patch or unsupported navigation API is authorized.

## Technical disposition

The earlier modal-coordination blocker was correct under the prior constraint.
The subsequent direct Founder instruction **supersedes it for this controlled
personal-printer test**: use documented beta.9 `helix.ui.overlay()` immediately
and accept temporary overlap with an existing native dialog. No fixed-delay
workaround, notification preference change or upstream patch is authorized.
[The API/presentation record](ISSUE_12_COMPLETION_UX_API_GATE.md) retains the source
findings and exact accepted limitation. Future queued-overlay support remains
an adapter replacement, not an invented API in this implementation.

Keep presentation separate from exact completion verification. An accepted fresh
same-job lifecycle arms one automatic attempt. Validated completion records its
request/job/proof claim before storage acceptance and opens Temperature directly
above the current native page. Closing only dismisses the view. Duplicate events,
manual reopening, waiting/returned state and restart never authorize another
attempt. The normal Home → tile → Temperature path retains the pending selection.
Beta.9 defers disk writes; conservative boot disarming prevents duplicate
presentation if the last claim write was lost. A restarted session can rearm only
after fresh matching live printing; a completion recovered without that edge
stays manual after fresh verification. This is at-most-once automatic attempting,
not a promise that a crash cannot lose an unseen popup. Result handling remains
exactly-once and NOT APPLIED, with all existing live/recovery checks unchanged.

Retain the validated generated 1×1 widget, accepted beta.4/Issue #8 sources and
physical c1eee43 installation. No saved home placement is migrated. Preserve
committed waiting/returned result immutability and exact originating receipt.
The coordinator, relay and companion remain unchanged; no broader replacement-job
delivery is claimed. Idempotent artifact retries cannot create a second selection
or dispatch.

Validate actual automatic overlays from Home, native Print Status and Controls;
dismiss/reopen, restart/lost deferred writes, duplicates, failed/cancelled/uncertain
and unrelated/unverified completion, result return and all eleven viewports.
Run relevant repository checks, fresh independent review, affected-surface Product
Preflight and exact-head CI. Archive prior capture bytes before complete passing
promotion. Preserve real physical success separately from all synthetic proof.

## Consequence and preservation boundary

This follow-up authorizes **no new print, heating, motion, printer configuration,
profile writeback, upstream change, physical deployment, merge or release**.
The one-shot physical grant/journal is historical proof, never reusable authority.
The candidate native plugin remains storage-only and the companion local-I/O
only. Existing guards, original profiles, private payloads, accepted evidence,
canonical dirty work and successful physical baseline remain preserved.

The storage incident remains resolved. Check available bytes/inodes around native
capture and promotion, serialize disk-intensive work through the existing shared
lock, reuse the verified runtime/image, and retain owned output in XDG state.
Do not reopen the completed storage investigation or perform broad cleanup.
