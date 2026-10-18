# Temperature calibration — physical success and current UX candidate

[Issue #12](https://github.com/bigstupid007/helix-orca-calibration/issues/12) /
[PR #13](https://github.com/bigstupid007/helix-orca-calibration/pull/13) remain
open and unmerged under the [current Build Program](BUILD_PROGRAM_TEMPERATURE_PRINT.md).

## Current disposition

The first controlled physical calibration **SUCCEEDED** at baseline `c1eee43`:
225/220/215°C bottom to top, normal original nozzle 220°C, selected 220°C returned
to the original Orca context as **NOT APPLIED**. Retained real-job completion and
originating receipt evidence verifies that milestone; see
[the actual physical record](evidence/issue-12/physical-first/README.md).
The tested physical product and its rollback files remain recoverable.

The subsequent Founder instruction authorizes **automatic native Temperature
presentation** using the existing beta.9 overlay API, explicitly accepting
temporary overlap with a native dialog for this personal-printer test. The earlier
modal blocker is superseded by that risk decision, not by a host API change.
The new isolated adapter opens immediately only after the unchanged independent
exact-job completion checks. Dismiss/manual reopen, duplicate/restart suppression
and the retained **1×1** home tile pass renewed source-bound qualification.
[API semantics and accepted limitation](ISSUE_12_COMPLETION_UX_API_GATE.md) include
the conservative crash-recovery/manual fallback. No delay, notification preference
change or upstream patch is used. No candidate is deployed to the printer.

## Preserved physical baseline and qualified file

Preferred October 15 Orca nightly
`6a7763f08d1a175a464a00ce13f0b5a815662fc4` prepared, sliced and exported the native
Temperature calibration at 70% uniform scale and 0.28 mm layers. Exact output:
**484,552 bytes**, SHA-256
`83fd38e22aca7237c1b8c9fa8a8971657f72b47d344a06f42120c78d05503074`,
75 layers, extrusion top Z20.92 mm and **12m00s** informational native estimate.
The three extrusion bands span Z0.20–6.92, 7.20–13.92 and 14.20–20.92 mm.
Native macro arguments resolve to `PRINT_START BED_TEMP=60 EXTRUDER_TEMP=225`.
No custom generator or exported-file edit was used.

Read-only identity/configuration/version review, all registered commands,
original motor/homing/QGL/probe/mesh/temperature/purge/end safeguards and
motion/purge/park/acceleration bounds were qualified before the separately
authorized physical Start. The actual completed job and exact result/receipt
are preserved privately. The normal estimate excludes macro overhead and is
never a print-duration ceiling. Material remains Founder-confirmed; no extra
spool check or combined-estimate gate exists.

The earlier [Windows native qualification](ISSUE_12_WINDOWS_NATIVE_QUALIFICATION.md)
records preparation and the original synthetic return test. That synthetic
proof is not the later actual physical success. The old pre-physical accepted
companion restoration occurred before the Founder-authorized physical staging;
this UX build performs no installation or rollback on the real target.

## Supported UX change and result preservation

Only the separate generated `temperature-print` plugin changes. Its manifest
requests 1×1. The tile retains the tune icon, full two-line **Orca Calibration**
identity, short lifecycle status (Ready, Print, Pick, Send, Done and locked/error
states), and the native tile → chooser → Temperature interaction. The compact
layout uses allowed XML primitives and native type/icon tokens. The fresh test
placement is 1×1; existing saved placement overrides a new manifest default,
so migration of a previously placed 3×2 tile is not claimed or performed.

After a selection is committed, `waiting` and `returned` are immutable to later
status events and the liveness timer. At the native UI boundary, an already-emitted exact acknowledgement can finish
return after a disconnect, standby or a different later job, because it acknowledges
the already verified committed result. This does not change the coordinator or
relay: their live correlation/recovery checks still apply before they emit an ACK,
and end-to-end delivery after a replacement job is not newly claimed. Selection itself still requires the
original success/job/proof checks. Wrong receipts, duplicates, cancellation,
failure and unrelated jobs cannot create a result or second dispatch. The
coordinator, physical adapter, companion and original context contract are
unchanged. Repeated identical inbox writes remain idempotent crash-safe delivery
retries, not repeated selections or profile writes.

## Validation and limits

The full repository suite passes **243 tests**; the fresh independent reviewer
reran all **54 affected tests**, passing. Static/whitespace and accepted beta.4/
Issue #8 evidence checks pass. The promoted complete source-bound beta.9 matrix
passes **all eleven supported viewports** with **133 frames, eleven geometry
records, eleven presentation records and eleven storage snapshots**. Every size
proves actual overlays from Home/native Print Status/Controls, dismissal and
underlying-page restoration, native manual reopening, duplicate/restart/lost-write
suppression, terminal/unrelated/unverified rejection and exact result/receipt.
The retained 1×1 tile fits without clipping/overlap and native taps still work.

Independent engineering and final promoted-artifact/privacy/visual/document
Product Preflight review PASS with no material findings. PR #13 owns exact-head
CI. Prior 7cc0b4d (122 files) and c1eee43 (100 files) native captures
remain byte-preserved and separate from actual physical proof.

The actual popup is attempted at most once per session completion. A request/job/
proof claim and runtime latch prevent dismissal/duplicate/restart repetition.
Beta.9 disk writes are deferred; a crash can conservatively suppress a popup
before it was seen. A recovered already-complete job stays manual after fresh
independent verification. Existing disconnection, filename and live return gates
remain unchanged. No exactly-once visual delivery across process crashes or
modal arbitration is claimed. Result handling remains exactly-once, NOT APPLIED.

All native authorization/job/clock/completion inputs in the new UI validation
are synthetic, with Docker network disabled and runtime/plugin mounts read-only.
They do not prove actual physical deployment or automatic modal arbitration.
Actual first-print proof stays separately labeled. Native screenshots prove
pixel fit, not hardware touch accuracy. No new print, heat, motion, configuration,
profile writeback, upstream patch, deployment, merge or release occurs here.

```sh
python3 -m unittest discover -s tests -v
./scripts/helix-dev verify-evidence docs/evidence/issue-2/native
python3 scripts/temperature-communication-evidence.py verify docs/evidence/issue-8/native
python3 scripts/temperature-print-qualify.py verify docs/evidence/issue-12/native
git diff --check
```

[Engineering review](ISSUE_12_ENGINEERING_REVIEW.md) ·
[Product Preflight](ISSUE_12_PRODUCT_PREFLIGHT.md) ·
[API gate](ISSUE_12_COMPLETION_UX_API_GATE.md).
