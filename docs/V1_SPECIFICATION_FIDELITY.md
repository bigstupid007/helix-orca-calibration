# V1 amendment specification-fidelity trace

This trace maps the controlling 2026-10-25 Founder playback to the frozen
candidate `2f1ffe1041b9f591d2c621e821975f53414efd65`. It distinguishes implemented
behavior, qualified external behavior, and the incomplete physical playback.
Passing source or synthetic evidence is never substituted for a physical step.

| Founder playback requirement | Implemented/qualified evidence | Final disposition |
| --- | --- | --- |
| Open Orca with the intended printer, process, filament, nozzle, bed, and machine G-code context | V2 companion captures saved/edited/effective context and an explicit 1-based originating slot on pinned Orca; the 50-case Windows matrix final-slices through `Print.process` / `Print.export_gcode` | **PASS through preparation** |
| Choose any of the five calibrations and current-Orca-valid parameters on beta.12 | Five native configuration surfaces, validation, defaults, precise input path, and build-level routes are covered by current tests and focused beta.12 evidence | **PASS** |
| Do not require an exact reference for each future request | Runtime accepts native-valid requests through an exact build/route qualification; qualification SHA `66c8616c…9ee` covers five calibrations × five representative cases × Voron/AD5X | **PASS** |
| Present real Orca warnings and allow only its known continue path | Unknown/fatal findings block; known `1000C001` acknowledgements are request/prepared-bound in the Windows matrix and were visibly continued on beta.12 without starting a print | **PASS through prepared review** |
| Review, Confirm, then deliberately press Start; generation must never start a printer | Native Confirm and Start are distinct. The only Founder Start produced an intent, then failed closed before upload. Independent Moonraker readback proves no upload or print | **PASS safety; execution incomplete** |
| Upload/start only the exact owned file, monitor the exact job, and recover conservatively | Printer-neutral adapter binds target, file bytes, fit, idle/queue, no-overwrite upload, history, cancellation, and one-shot recovery. Actual target checks passed through pre-dispatch | **PASS implementation; physical completion blocked** |
| Select the printed result after exact completion | The chooser is completion-gated and validated in native/source fixtures | **NOT REACHED physically** |
| Apply to the immutable originating filament slot/preset using Orca's official transaction; leave modified/unsaved; never Save | All five source-current mappings, PA atomic two-key commit, failure/retry, and uncertain/no-replay pass 637-test regression. The pinned companion captured the actual origin, but no amended physical result reached the real transaction | **PASS implementation; actual physical transaction not reached** |
| No manual file relay, hand-edited G-code, result re-entry, Codex worker, or qualification-fixture choice in ordinary use | The installed per-user coordinator runs independently of the test worker; all technical work remained behind the product surfaces | **PASS design/runtime** |
| Comparable AD5X compatibility without a Voron-only macro contract | Twenty-five AD5X matrix cases final-sliced with no physical adapter and no universal Voron macro requirement | **PASS** |
| Installation/status/stop/restart/rollback/uninstall without service, listener, firewall, account, or credential changes | Actual SPARE stop → rollback → install → start → status and final freeze stop passed with rollback retained and `test_worker_required:false`; restart/uninstall remain implementation/test-reviewed only | **PARTIAL** |
| Five controlled Voron calibrations | The continuation remained trapped in the retired uncertain beta.12 session while the coordinator held no request. No new upload or print occurred. Per Founder direction no further navigation/timing repair loop was started and the product was frozen | **BLOCKED — specific diagnostic preserved** |

The intended architecture maps the requested workflow without adding Founder
relay or automatic Save, but the actual end-to-end navigation did not complete.
The five new physical chains remain incomplete because the frozen
beta.12/native-session path could not leave its retired uncertain request. See the
[acceptance ledger](V1_COMPLETION_ACCEPTANCE.md) and
[diagnostic](evidence/issue-14/amendment/physical-stale-session-navigation-diagnostic.json).
