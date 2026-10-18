# Issue #12 — actual physical success and synthetic automatic-chooser proof

The calibration remains exactly **225/220/215°C bottom to top**, normal original
nozzle **220°C**, no duration/combined-estimate gate or extra spool-label check.

## Actual physical milestone preserved

[`physical-first/`](physical-first/README.md) records actual Founder-started
c1eee43 success, independent completed same-job history, selected 220°C, exact
originating Orca receipt and **NOT APPLIED**. Actual elapsed time is 999 seconds
(16m39s); the 720-second estimate is informational. Its raw private evidence,
generated components and rollback files remain hash-preserved. This milestone
authorizes no rerun and is separate from the new synthetic proof below. The
physical-first record is preserved verbatim: its reference to the then-blocked
popup describes the earlier 7cc0b4d stage, superseded by the authorization below.

## Current automatic chooser and compact-widget capture

`native/` is the complete source-bound pinned beta.9 capture:
**eleven viewports, 133 frames, eleven geometry records, eleven presentation
records and eleven storage snapshots**. Only these 167 report-bound files are
promoted; runtime logs/private settings remain outside Git.

Every size exercises actual Temperature overlay presentation from **Home**,
native **Print Status** (with manual Temperature buried underneath) and
**Controls**, then native dismissal with restoration
of the underlying page, no repeated popup on duplicate events, normal manual
reopening and exact original-context selection/receipt. Native Print Status is
opened using the runtime's production `demo print-status` route; this is test
infrastructure, absent from the product plugin. `presentation.json` binds actual
before/after native panel/overlay stacks and recovery/rejection outcomes.

A complete request/job/proof claim precedes the immediate overlay attempt.
Restart never opens a retained completion by itself. The capture restores an
earlier persisted **synthetic** printing snapshot to simulate loss of a deferred
claim write, restarts, re-verifies completion and proves no popup plus manually
reachable result. Other checks cover waiting/returned restart, unrelated request/
job/file, missing proof, failed/cancelled/uncertain states, original context,
post-expiry monitoring/cancel/result and exactly-once NOT APPLIED handling.

The retained 1×1 tile (2×2 internal tracks) contains its icon, full identity and
status without overlap/clipping; actual native taps reach chooser/Temperature.
No saved physical dashboard placement is migrated. Existing live return/recovery
and coordinator/relay checks remain unchanged; broader replacement-job delivery
is not claimed.

All authorization/job/status/clock/completion inputs are **synthetic** in Docker
network-none/read-only runtime/plugin isolation, with zero physical actions. The
1501-second fixture estimate is not the actual G-code estimate. A simulated lost
host write is not a new disk-space incident. No current proof claims a physical
installation or another real print.

The Founder explicitly accepts temporary native-dialog overlap for this test;
no modal priority/deferral is claimed. The product uses existing `helix.ui.overlay`
without a timer workaround, preference change or upstream patch. A crash may
conservatively suppress an unseen popup because the host defers disk writes;
manual recovery follows fresh verification. See the [API/presentation record](../../ISSUE_12_COMPLETION_UX_API_GATE.md).

```sh
python3 scripts/temperature-print-qualify.py verify docs/evidence/issue-12/native
```

## Preserved earlier evidence

The prior 122-file compact capture is preserved byte-for-byte under
[7cc0b4d history](history/candidate-7cc0b4d/README.md); prior 100-file c1eee43 capture
under [c1eee43 history](history/candidate-c1eee43/README.md). Earlier ac84114 and
210/205/200°C proof remain superseded history. Partial/failed trials are private,
unpromoted, and never described as complete matrix proof.

`native-gcode-inspection.json` records the actual native Windows export:
484,552 bytes, 75 layers, 720-second informational estimate. Preserved
`native-file-safety-review.json` and `read-only-suitability.json` qualified
registered commands, unchanged macro dependencies and geometric bounds before
the physical test. They are historical GET-only observations, not fresh printer
checks or permission for another print.

`windows-native-roundtrip.json` is earlier actual Windows integration with
**synthetic** completion inputs; it is not the later actual physical success.
Its accepted 0.5.0 restoration/profile-preservation observations predate separately
authorized physical staging. This UX build changes no Windows component and
performs no physical installation/rollback. Raw G-code, Windows frames, target
data and operational payloads remain private.

[Readiness](../../TEMPERATURE_PRINT_READINESS.md) ·
[Engineering review](../../ISSUE_12_ENGINEERING_REVIEW.md) ·
[Product Preflight](../../ISSUE_12_PRODUCT_PREFLIGHT.md).
