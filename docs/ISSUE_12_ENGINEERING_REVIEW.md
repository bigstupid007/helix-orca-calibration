# Issue #12 corrected candidate — engineering review

Authority: the direct Founder correction of 2026-10-17, the updated
[Build Program](BUILD_PROGRAM_TEMPERATURE_PRINT.md), application AGENTS.md and
published shared Development System main `2328bc55709d6dd1705fdec339d4a3982a81ffe2`.
Continue existing Issue #12 / PR #13, unmerged. Application main remains
`89165d15993ccfcd065b299e1980bb19749fdcaf`.

## Independent authority and code review

A fresh-context read-only reviewer first compared the raw Founder correction,
workflow playback and proposed specification. **PASS:** no material mismatch;
no extra human task, combined-time gate or filament checkpoint was introduced.
The shared independent-review profile is used with High reasoning because the
changed duration logic participates in a future physical-control lifecycle.

Frozen corrected runtime/protocol/driver boundary: `baf08d5`. Independent
focused validation passes **42 tests**, with no material executable finding.
Exactly 225/220/215 is enforced across actual-file inspection, qualification,
request/protocol, native UI, stored-result restoration and result validation.
Old 210/205/200 descriptors are rejected rather than retargeted.

The correction removes the 20-minute maximum, 10-minute minimum, startup/end
allowance inputs, combined-time qualification and estimate-plus-five-minute
monitoring timeout. The native estimate remains finite, positive information.
Regression proof accepts above-20-minute estimates and observes a healthy job
past its estimate without failing it. The native fixture uses 1501 seconds to
prove that Ready is not blocked at 20 minutes.

Request lifetime/start freshness, connection freshness, reviewed machine/config/
version, exact G-code bytes, macro arguments, geometry, preconfirmed material
suitability, durable one-shot dispatch, same-job monitoring, guarded cancellation,
recovery and independent-success selection remain fail-closed. The existing
one-hour request expiry is separate stale-request protection, not a duration
qualification threshold or request for another Founder decision.

## Pending final reconciliation

The full corrected beta.9 capture passes all eleven sizes. Its 88 native frames,
eleven storage snapshots, generated fixture and report verify against this
candidate source. Actual Windows export/current companion proof, affected
Product Preflight, final integrated-head review and exact-head CI remain
separate dispositions below. The independent affected-surface native Product
Preflight passes with no material native UX defect; overall preflight remains
pending the corrected Windows companion capture. Earlier review at `68d1029` and its evidence
remain history and do not substitute for this correction's actual export.

The full repository suite passes **231 tests**. Retained beta.4 and Issue #8
evidence verification and `git diff --check` pass. Accepted CI/source, normal profiles, old evidence,
the canonical dirty checkout and existing security boundaries stay preserved.
No physical print, heating, motion, macro, upload/queue, firmware/configuration
change, profile writeback, physical derivative install, merge or Alpha adoption
is authorized or performed.
