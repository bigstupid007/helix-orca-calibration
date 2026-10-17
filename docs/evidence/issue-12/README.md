# Issue #12 corrected-candidate evidence

The controlling correction is exactly **225/220/215°C bottom to top**, normal
nozzle **220°C**, confirmed filament, and no hard duration/combined-estimate gate
or additional spool-label checkpoint.

`read-only-suitability.json` is the sanitized current GET-only refresh. It
confirms the unchanged reviewed machine/configuration/version and idle queue;
raw identities, configuration and endpoints remain private.

`native/` is the renewed complete passing, source-bound beta.9 eleven-target
matrix: **88 frames and eleven storage snapshots**. It verifies effective-220
context gating, no receipt-triggered Start, guarded one-shot intent, restart,
independent-success selection, post-request-expiry monitoring/result/ACK, refusal
to replace an expired active session and fresh post-expiry cancellation.
All authorization/job/status/clock/completion inputs are synthetic; the
1501-second estimate is a fixture, not the actual G-code estimate. Native
clock jumps beyond request expiry are simulated, not elapsed hardware proof.
The reused dependency image, candidate hashes and all matrix inputs are in the
report; the run used network-none/read-only isolation and zero physical actions.

```sh
python3 scripts/temperature-print-qualify.py verify docs/evidence/issue-12/native
```

The superseded `ac84114` native bytes are preserved under
[history](history/candidate-ac84114/README.md); earlier 210/205/200°C proof remains
separate history. No partial capture was promoted.

Corrected actual Windows native-export inspection and current companion
round-trip proof remain pending reconnection of the existing test worker.
Earlier files and screenshots are [superseded history](history/README.md),
never evidence of the corrected export. Raw G-code, Windows frames and payloads
remain private. No physical action is authorized or performed.

See the [readiness report](../../TEMPERATURE_PRINT_READINESS.md),
[engineering review](../../ISSUE_12_ENGINEERING_REVIEW.md) and
[Product Preflight](../../ISSUE_12_PRODUCT_PREFLIGHT.md).
