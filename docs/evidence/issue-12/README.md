# Issue #12 — actual physical milestone and synthetic compact-widget evidence

The controlling calibration remains exactly **225/220/215°C bottom to top**,
normal original nozzle **220°C**, no hard duration/combined-estimate gate and
no additional spool-label verification.

## Actual first physical success

[`physical-first/`](physical-first/README.md) records the successful Founder-started
real print at baseline `c1eee4374fb0286e1a3973d8e29107bfc64ee99f`, independently
completed same-job history, selected 220°C, exact originating Orca receipt and
NOT APPLIED return. Actual elapsed time was 999 seconds (16m39s). Raw operational
proof and generated/rollback components remain hash-preserved privately. This
milestone is separate from all synthetic proof below and authorizes no rerun.

## Current supported compact-widget capture

`native/` is the complete passing source-bound beta.9 eleven-target capture:
**99 frames, eleven tile geometry records and eleven storage snapshots**.
The manifest requests 1×1 cells; the native saved test placement is 2×2 internal
tracks. Geometry proves icon/full identity/status containment without overlap,
and actual native taps prove tile → chooser → Temperature navigation at all sizes.
Lifecycle status, result locking, restart, guarded cancellation, exact context,
late-status/disconnected pending-result preservation, wrong/duplicate receipts
and exact already-emitted ACK acceptance after later printer state are checked.
Coordinator/relay live checks are unchanged; broader replacement-job delivery is
not claimed. The new capture does not install or migrate a physical home entry.

All authorization/job/status/clock/completion inputs are **synthetic**, under
Docker network-none/read-only runtime/plugin isolation, with zero physical
actions. The 1501-second fixture estimate is not the actual G-code estimate;
simulated clock jumps are not elapsed hardware proof. Only report-bound frames,
geometry and native storage are promoted, without private runtime logs/settings.

**Automatic chooser remains BLOCKED and unimplemented.** No automatic cross-page
opening, modal arbitration or dismissal-suppression proof is claimed. See the
[pinned API gate and separate host proposal](../../ISSUE_12_COMPLETION_UX_API_GATE.md).

```sh
python3 scripts/temperature-print-qualify.py verify docs/evidence/issue-12/native
```

Prior c1eee43 native bytes are preserved under
[history](history/candidate-c1eee43/README.md). The ac84114 and earlier
210/205/200°C captures remain separate superseded history. Failed, partial and
source-changed exploratory captures are not promoted.

## Preserved pre-physical qualification

`native-gcode-inspection.json` records the actual corrected native Windows
export: 484,552 bytes, three bands, 75 layers and 720-second informational
estimate. `native-file-safety-review.json` and `read-only-suitability.json`
resolve registered commands, unchanged macro dependencies and geometric bounds.
The suitability refresh is historical GET-only pre-execution evidence, not a
claim that the printer was just rechecked or that another print is authorized.

`windows-native-roundtrip.json` is the earlier actual Windows companion/native
integration with **synthetic** job/history/completion inputs. It binds the exact
original outbox, native 220°C result and committed originating receipt before
ACK. Its accepted 0.5.0 restoration and profile-preservation observations predate
the later separately authorized physical staging. The new UX build changes no
Windows component and performs no physical installation or rollback. Do not
mislabel that original synthetic proof as the later actual physical success.
Raw G-code, Windows frames, target data and payloads remain private.

[Readiness](../../TEMPERATURE_PRINT_READINESS.md) ·
[Engineering review](../../ISSUE_12_ENGINEERING_REVIEW.md) ·
[Product Preflight](../../ISSUE_12_PRODUCT_PREFLIGHT.md).
