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

`native-gcode-inspection.json` records the actual corrected native Windows export:
484,552 bytes, three bands, 75 layers and a 720-second informational estimate.
Its standalone `physical_ready: false` is not a failed offline suitability gate:
`native-file-safety-review.json` and `read-only-suitability.json` resolve registered
commands, unchanged macro dependencies and geometric bounds without authorization.

`windows-native-roundtrip.json` binds the real originating Windows outbox,
reviewed installed 0.6.1 source, exact native persisted 220°C result and committed
receipt before ACK. Job/history/authorization/completion inputs are synthetic;
zero hardware completion or physical action is claimed. The accepted 0.5.0
companion is restored, all five communication artifacts, 12 user profile JSONs
and 1,429 normal files are unchanged. Raw G-code, Windows frames, target data and
payloads remain private. Earlier evidence stays superseded history.

See the [readiness report](../../TEMPERATURE_PRINT_READINESS.md),
[engineering review](../../ISSUE_12_ENGINEERING_REVIEW.md) and
[Product Preflight](../../ISSUE_12_PRODUCT_PREFLIGHT.md).
