# Issue #14 V1 candidate evidence

`native/` is the complete, source-bound corrected beta.9 native UI matrix:
all eleven pinned targets, all five calibration workflows, **396 frames**
(36 per target). It includes separate Confirmed/Start views, same-job nullable
progress, terminal evaluation visibility, explicit Return/receipt/Done,
confirmed cancellation, logical 1×1 tile child bounds/nonoverlap and conservative
restart recovery using actual Coordinator-derived fixtures. Native Home, Print
Status and Controls navigation remain owned by Helix.

Every context, generator capability, prepared artifact, parity flag, printer
status, completion proof and receipt is **synthetic test input**. These captures
prove actual pinned native UI behavior and interaction; they do not qualify
generator parity, Windows operation or a physical print. Docker used network
none, read-only runtime/plugin mounts and no physical action route. Historical
308- and 341-frame captures remain retained in private state and Git history;
failed/interrupted later captures were never promoted.

Verify current portable source/runtime/geometry/frame/lifecycle bindings:

```sh
python3 scripts/v1-native-evidence.py verify docs/evidence/issue-14/native
```

The frozen native source digest is
`e5dc3aff82501ed6f507d00e3bb34b692187c971b37a4173a13a0afdad81820a`.
The complete private capture is retained in XDG state at
`helix-orca-calibration/v1-native/f6198a7-full-audited-20261019`.
All eleven ManagedRuns exited zero, removed only their exact owned container,
reported runtime clear and had no verification errors/baseline drift. These
full records were independently verified before promotion. The portable report
retains sanitized limits/outcomes and full-manifest hashes; host inventories
remain private. Optional `--verify-managed /absolute/current-private-capture`
rechecks those same matching final private records, without bypassing source
or frame validation.

Actual Windows/native-reference, generator-parity and interactive browser
lifecycle evidence are separate inventories. No generator is qualified by UI
fixture screenshots. Accepted Issue #12 physical and synthetic proof remains
unchanged in its original evidence directories. See the
[integrated review guide](../../V1_FOUNDER_REVIEW.md) for proof levels and limits.
