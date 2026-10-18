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
over Print Status, Home or another native page, respect built-in modal priority,
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

The independent API review proves a hard blocker for automatic presentation.
Beta.9 offers plugin overlays but no native-modal visibility/close signal or
modal-aware deferred-presentation contract. A plugin overlay can cover a
built-in completion dialog. Fixed delays cannot satisfy that requirement.
[The API gate](ISSUE_12_COMPLETION_UX_API_GATE.md) records pinned primary source
and a concrete host-support proposal; no automatic-popup workaround is shipped.
This part remains BLOCKED under the current no-upstream-change constraint.

Complete the independent supported compact-widget candidate in the generated
`temperature-print` derivative only. Preserve the accepted beta.4/Issue #8
sources and the physical installation. The fresh native test layout requests
1×1; it does not migrate a retained physical saved placement. Mirror short
lifecycle status and retain the existing tile → chooser → Temperature navigation.
Protect an already committed waiting/returned result from late statuses and
clock/disconnect changes; native acceptance of an already-emitted exact ACK acknowledges the committed
result rather than the printer's later live job. Coordinator/relay live checks
remain unchanged; broader replacement-job delivery is not claimed. Idempotent artifact retries are still allowed;
no second selection or dispatch is introduced.

Run repository checks, the full pinned native matrix, fresh independent review,
affected-surface Product Preflight and exact-head CI. Preserve earlier evidence
before promoting a complete passing capture. Do not describe a partial candidate
as implementing both UX corrections or ask the Founder to accept unsupported
modal behavior.

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
