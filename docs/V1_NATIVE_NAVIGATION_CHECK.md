# Native navigation correction and bounded smoke

The V1 native smoke exposed a qualifier error after automatic Temperature result
dismissal on a native page. The shared `back_to_home()` helper closes overlays;
it does not select the Home panel. Consequently the correctly preserved Controls
panel had no home tile to reopen. The accepted Temperature qualifier explicitly
navigates Home before reopening its pending result. V1 now performs that same
deliberate native navigation. Product Lua and accepted sources are unchanged.

The qualifier additionally requires the real Print Status overlay or Controls
panel before completion, compares exact native navigation before presentation
and after dismissal, rejects duplicate presentation, and records native page
transitions before explicitly navigating Home and manually reopening. This
preserves the native-page assertions rather than bypassing them.

The repaired source passed one bounded native beta.9 `800x480` smoke on
2026-10-19 UTC: all five workflows, 31 screenshots, 19 assertions, logical 1×1
tile bounds, real Coordinator-derived Review/Confirmed/Complete restart recovery,
Temperature automatic presentation/dismissal/manual reopening on Home, Print
Status and Controls, cancellation confirmation, and fresh request after blocked
work. Review advanced sequence 2→3, Confirmed 3→4 and Complete 7→8 through the
actual coordinator reconciler; unchanged and replayed statuses stayed locked.
Lost and retained presentation claims remained manual-only after restart.

Managed run `1c72ae330a0b4c7e977e62ce35ce4b7e` completed with workload exit 0,
`runtime_clear: true`, no verification or teardown errors, and the exact owned
container was absent afterward. It used the shared writer lock, network-none
runtime, 2 CPUs, 512 MiB memory, 128 PIDs, a 240-second deadline, 5 GiB reserve,
512 MiB expected additional peak and 512 MiB margin. Private source-bound smoke
artifacts remain in the XDG-state V1-native `fidelity-navigation-smoke-20261019`
directory. No accepted evidence, original profiles or physical configuration was
changed. No printer, Windows bridge, physical Start or deployment was exercised.

All inputs and parity/job boundaries are explicitly synthetic UI fixtures. This
one-viewport smoke does not qualify generators, hardware or the entire display
matrix. The lead must run the complete eleven-size matrix against the final
integrated source before promoting evidence. Dependency-free validation passed
384 tests, with two Windows-specific checks skipped on Linux; `git diff --check`
passed.
