# Issue #14 V1 candidate evidence

`native/` is the complete, source-bound beta.9 native UI matrix: all eleven
pinned targets, all five calibration workflows, 341 frames. Every context,
capability, prepared artifact, parity flag, printer status, completion proof and
receipt in this capture is **synthetic test input**. It proves real native UI
behavior and interaction, not generator parity, Windows operation or printing.
No physical actions occurred. The revised matrix also verifies a separate
request-bound Cancel confirmation: opening the dialog sends no cancel intent,
Keep printing preserves the job, and only the second confirmation persists Cancel.
Human-readable parameter/status copy and the original-context review are included.
The earlier complete 308-frame capture remains retained in private state and Git history.

Verify the portable source/runtime/geometry/frame/lifecycle summary bindings:

```
python3 scripts/v1-native-evidence.py verify docs/evidence/issue-14/native
```

The exact complete private capture and all eleven full ManagedRun records remain
in XDG state. They were independently checked before promotion: each command
exited zero, each exact owned container was removed, runtime_clear is true and
no Docker baseline drift/errors were reported. The portable report retains
sanitized limits/outcomes and full-manifest hashes, excluding private host and
unrelated Docker inventories. Optional `--verify-managed /private/capture` checks
those original records as well.

Actual Windows/native-reference and generator-parity evidence is retained
separately while qualification proceeds. No V1 generator is qualified by these
UI fixture screenshots. Accepted Issue #12 physical and synthetic proof remains
unchanged in its original evidence directories.
