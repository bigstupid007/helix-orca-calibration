# Issue #12 readiness evidence

`native/` is the complete passing pinned beta.9 eleven-target capture: 88
native PNGs, eleven persisted storage snapshots and a source/fixture/runtime
bound report. It uses `--test`, Docker `--network none`, read-only runtime/plugin
mounts and the existing private control socket. Authorization, printer clock,
status, jobs and completion proof are synthetic; physical actions are zero.

```sh
python3 scripts/temperature-print-qualify.py verify docs/evidence/issue-12/native
```

`native-gcode-inspection.json` records read-only inspection of the actual
October 15 native export. `read-only-suitability.json` sanitizes the existing
physical target's bounded GET-only review. `windows-mock-roundtrip.json` binds
the fresh actual Windows request, exact native mock result and actual Windows
NOT APPLIED receipt through private artifact hashes. Raw Windows frames,
G-code, target addresses, identifiers, configuration and payloads remain in
private XDG state.

These artifacts do not prove physical execution. The combined estimate for
native printing plus all opaque printer-macro overhead remains unqualified;
no live qualification, Founder grant or physical test was issued. See
[the readiness report](../../TEMPERATURE_PRINT_READINESS.md),
[engineering review](../../ISSUE_12_ENGINEERING_REVIEW.md) and
[Product Preflight](../../ISSUE_12_PRODUCT_PREFLIGHT.md).
