# Miniature Temperature calibration — corrected readiness candidate

[Issue #12](https://github.com/bigstupid007/helix-orca-calibration/issues/12) /
[PR #13](https://github.com/bigstupid007/helix-orca-calibration/pull/13).
The [direct Founder correction](BUILD_PROGRAM_TEMPERATURE_PRINT.md) controls:
**225 / 220 / 215°C bottom to top**, normal nozzle **220°C**, confirmed filament.
There is **no hard 20-minute ceiling, combined-estimate qualification requirement
or spool-label checkpoint**.

## Current disposition

The remaining runtime qualification is on the actual Windows surface. The
reviewed source passes **243 repository tests**, including **54 affected tests
independently rerun**. The independent source review is PASS. Accepted beta.4
and Issue #8 native evidence verifies. The renewed eleven-target beta.9 capture passes, with **88 frames and eleven
storage snapshots**, promoted and verified against current source. It covers
post-expiry monitoring, cancellation, return and context gating; see [current evidence](evidence/issue-12/README.md).

Actual Windows regeneration/export and the current companion UI proof await
restart of the existing owner-launched test worker. The devbox storage incident
is resolved: resume checks show 358.6 GiB available and healthy inode headroom;
proportionate checks continue around export and capture. Windows Product
Preflight remains due; PR #13 current checks own the exact-head CI disposition. No hardware action is authorized
or needed for these software checks. This report does not claim a completed
physical-test candidate before those gates pass.

## Actual export and estimate

The Windows worker uses the preferred October 15 nightly
`6a7763f08d1a175a464a00ce13f0b5a815662fc4`: native Calibration → Temperature,
225°C start, 215°C end, 5°C step; uniform native Scale 70%, unsaved 0.28 mm
layers, normal Slice and Export. The in-memory machine-start field must emit
`PRINT_START BED_TEMP=60 EXTRUDER_TEMP=225`, matching the existing printer macro.
Temporary changes are discarded; presets and original context stay unchanged.

The corrected export's actual byte count, SHA-256, geometry, transitions and
native estimate will be recorded from its new bytes in
[Windows qualification](ISSUE_12_WINDOWS_NATIVE_QUALIFICATION.md) and the new
inspection JSON. Earlier 210/205/200°C files are preserved as
[superseded history](evidence/issue-12/history/README.md); they do not prove this
correction. No custom G-code generator or exported-file edit is used.

The native estimate is useful information, not an elapsed-time promise or
readiness gate. Printer-side heating, homing, QGL, saved-mesh loading, purge and
normal end behavior can add wall time; qualifying a combined estimate is not
required. A healthy same-job print is not failed for exceeding its estimate.

## Lifecycle retained

Sending creates only a correlated request. After separate physical-test
authorization, only explicit Start on HelixScreen supplies the native intent.
The coordinator requires the same private authorization, reviewed machine,
configuration, Moonraker version and qualification. After Start it checks the
exact uploaded bytes and a second fresh idle/queue snapshot before journaling
and one dispatch. Ambiguous Start or cancel is never retried.

Real same-job state, ID and start time confirm starting and monitoring. Initial
metadata/history lag remains pending only inside the persisted 30-second
confirmation deadline; ownership is never inferred or dispatch repeated.
After Start, request TTL is not a print-duration or result-return cutoff. A
durable local lifecycle marker preserves the original companion slot while
active/uncertain, and only exact retained job/proof results may return later. Fresh
`print_stats=complete` plus the same independently completed history job unlock
the three-choice result picker. History lag stays locked. Failure, cancellation,
disconnection, replacement, stale request or unexpected state cannot yield a
result. Native Cancel confirms exact-file intent; ordinary Helix Print remains
the monitoring route. Recovery observes rather than redispatches.

The selected result returns to the original saved/edited/effective Orca context
as **NOT APPLIED**, with no profile writeback. Its effective original nozzle
must be 220°C; saved and edited values are preserved independently. The companion is local-I/O only;
Helix remains storage-only. The physical adapter defaults to actions disabled;
no live permit, physical upload/queue, install or activation occurs here.

## Safety and preservation

A bounded GET-only refresh confirms unchanged reviewed physical identity,
configuration and accepted Moonraker version, standby state and empty queue.
The 0.4 mm nozzle, X/Y 0–300 and Z −5–290 mm envelope, supported exclude-object
commands, QGL and saved 60°C mesh are retained. Confirmed material and requested
temperatures remain the Founder facts; no additional label decision is needed.
Raw identities/configuration, Windows frames, payloads and G-code stay private.

Accepted Issue #8 source/communication, Issue #10 preferred-nightly policy,
normal Orca profiles, the dirty canonical checkout, previous evidence and the
beta.4 harness remain preserved. Alpha has no physical adoption. No print,
heating, motion, macro execution, firmware/configuration/security change,
profile writeback, merge or deployment is authorized by this workstream.

## Review and validation

The pinned beta.9 matrix uses `--test`, Docker `--network none`, read-only mounts
and the existing private control socket. Its clock, authorization, jobs and
completion proofs are synthetic. A 1501-second ready estimate deliberately
exercises acceptance above the removed 20-minute boundary; it is not the actual
export estimate. The current actual Windows request/result is tested separately.

```sh
python3 -m unittest discover -s tests -v
./scripts/helix-dev verify-evidence docs/evidence/issue-2/native
python3 scripts/temperature-communication-evidence.py verify docs/evidence/issue-8/native
python3 scripts/temperature-print-qualify.py verify docs/evidence/issue-12/native
git diff --check
```

[Engineering review](ISSUE_12_ENGINEERING_REVIEW.md) and
[affected-surface Product Preflight](ISSUE_12_PRODUCT_PREFLIGHT.md) will record the
completed corrected candidate. Founder Review is personal review, not AI
acceptance. Physical execution remains a separate authorization.
