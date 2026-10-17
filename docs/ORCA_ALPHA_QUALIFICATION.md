# OrcaSlicer 2.5.0 Alpha compatibility qualification

Status: **passed isolated compatibility qualification, independent review and affected-surface AI Product Preflight; unmerged candidate** under [Issue #10](https://github.com/bigstupid007/helix-orca-calibration/issues/10).
The accepted physical baseline remains the October 15 nightly. This work does
not adopt Alpha, merge a candidate or authorize physical communication.

## Baselines and approved boundary

Accepted main is `9c8d159221ff132a7be2516bb7a50b1ef26bbeca`, following Founder
acceptance and closeout of Issue #8 / PR #9. That milestone proved the actual
physical 205°C selection return and original-profile 220°C / NOT APPLIED
instructions. Its implementation and public/private evidence remain unchanged.
Canonical dirty work is preserved through a separate qualification worktree.

This qualification compares official Alpha source
`3880f2c58ec392ed2bd5938ab31c9c7c496c0eb2` against the qualified nightly source
`6a7763f08d1a175a464a00ce13f0b5a815662fc4`. Spare runs Alpha from a new marked
portable directory, separate `--datadir` and child-only WebView2 storage.
Only profile copies and minimal local settings are seeded; printer connections,
prior communication state, credentials and normal settings are excluded.
Before/after fingerprints protect normal Orca and the accepted nightly.

No print, queue, heating, motion, homing, macro, profile writeback, new access,
security change, production deployment or unrelated UX is authorized. Normal
Temperature preparation/slicing/export and unsaved edits are isolated test
inputs, never hardware actions or writes to original profile sources.

## Source and release comparison

The Alpha is a direct descendant of the nightly by 39 commits. The host app-info,
preset-context, owned-UI, storage, lifecycle and normal Calibration/Plater
surfaces used by the companion are byte-identical. Relevant changes add a
ResourceTexture capability, improve plugin-page tab overflow and long-path ZIP
extraction; the Script companion does not use those added surfaces. The G-code
change concerns multi-tool standby heaters, so Alpha must generate and hash its
own normal Temperature export rather than reuse the nightly file identity.

The official tag resolves directly to the specified Alpha commit. Release ID
`410256856`, Windows x64 portable asset `647273931`:

| Artifact | SHA-256 |
| --- | --- |
| `OrcaSlicer_Windows_V2.5.0-alpha_x64_portable.zip` (221,507,287 bytes) | `9b4593697c9ec0f8e7c0dcbebd7f8ea08a5cd01c2bd68d2a5d48b45b4c18ff8c` |
| `orca-slicer.exe` | `a37d149ea315a0a2125c11625b7dc24e456dbd3bc309dd56519d90dcdcd77985` |
| `OrcaSlicer.dll` | `92bdf7493425b949934479164d0745ce5e28fe24c7a556af300792b788e94c8b` |

These hashes were independently checked on devbox and after extraction on Spare.
The ZIP is extracted only into its owned runtime directory; no system installer
is used. [Official release](https://github.com/OrcaSlicer/OrcaSlicer/releases/tag/v2.5.0-alpha),
[exact source comparison](https://github.com/OrcaSlicer/OrcaSlicer/compare/6a7763f08d1a175a464a00ce13f0b5a815662fc4...3880f2c58ec392ed2bd5938ab31c9c7c496c0eb2).

## Runtime admission and retained evidence

The accepted `0.5.0` companion deliberately admits the qualified nightly only
for its communication outbox. It cannot be relabeled as Alpha compatible merely
because plugin loading succeeds. A separate generated derivative must retain
truthful exact Alpha runtime provenance in both context and embedded protocol,
without broad version prefixes or pretending that Alpha is the nightly.
Accepted generators, source, protocol, physical relay and evidence stay intact.

The accepted physical relay also has an exact nightly runtime gate and remains
unchanged. An isolated Alpha companion/native-harness pass does not enable
Alpha on that physical route. No physical retest is planned: the native code,
flat request/result schemas, selection/receipt guards and retained viewport
proof can be reused where their hashes and contracts remain valid.

## Completed Windows qualification

The generated Alpha-only `0.5.1` companion has SHA-256
`9b79d6150b4f0102a8e5ed8b43491005ddfb3834f4e099d9eb470c870a4c41b7`.
The owner unlocked Spare, and the native Plugins dialog installed, activated and
subsequently reloaded this separate single-file package. Actual `app_info()`
reports `2.5.0-alpha / 3880f2c5`, matching the official pinned binaries.
The guarded Windows tool checks both executable and DLL before process admission.

| Surface | Actual result |
| --- | --- |
| Context and Orca-owned UI | Qualification and communication docks open; original printer, filament, process and 0.4 mm nozzle are correct. |
| Saved/edited/effective | An unsaved edit shows 220/217/217°C separately; native reset restores 220/220/220°C without saving. |
| Normal preparation/export | Built-in PLA Temperature 230→190°C, step 5, prepared and sliced locally; new export is 3,028,203 bytes with all nine expected bands. |
| Exact file association | Native chooser descriptor matches independently read file size, SHA-256 and bands. Export lifecycle still names only the temporary slice file, so manual association remains necessary. |
| Request and retry | Actual Alpha outbox validates with truthful Alpha context; Retry preserves its exact bytes, IDs and expiry. |
| Native return | The unchanged beta.9 native driver consumes that outbox in Docker with network `none`, selects 205°C and verifies exact native persisted result. |
| Originating Alpha result | Alpha automatically commits that exact fixture result and exact ACK-shaped receipt; original profile, setting, 220/220/220°C and 205°C remain visibly NOT APPLIED. |
| Stale and duplicate results | A stale ID leaves pending state unchanged with no receipt. Conflicting and exact duplicates preserve the committed state and receipt bytes. |
| Profile switching | Switching to the copied alternate filament changes current-context information and warning, never the original target/instructions; switching back restores the matching-context message. |
| Persistence | Normal close discards the temporary tower project; a fresh Alpha process reloads 0.5.1 and recovers byte-identical request, result and receipt. |

This is a new **isolated** Alpha-to-native-to-Alpha fixture run. Its clock is
explicitly synthetic (`eventtime` 1000→1900). The fixture result is delivered
through the existing approved worker only to the marked Alpha inbox; no physical
relay runs. The fresh native driver stops awaiting acknowledgement. Alpha's exact
receipt is verified, but no fresh native ACK or terminal physical delivery is
claimed. The unchanged Issue #8 eleven-viewport/33-frame selection/ACK/recovery
proof and accepted physical evidence remain valid retained evidence, not new
Alpha physical qualification. Both native and Issue #2 evidence verifiers pass.

An inadvertent unsaved bed-temperature edit during reversion was caught by
Orca's safety warning and discarded through native reset. All 12 seeded profile
JSON files still match their preserved source. Normal Orca's 1,429 relevant
files, 61 sampled nightly files and both nightly binaries match their immutable
before-run fingerprints. Canonical pre-existing HEAD, full dirty status and file
bytes are unchanged. Accepted product, CI and earlier evidence are unchanged.
The worker bounded an inherited-output-pipe capture during launch/restart;
target state was inspected before any retry, confirming one exact isolated
process each time. No duplicate launch or access workaround was used.

[Sanitized qualification report](evidence/issue-10/qualification.json) binds the
private evidence manifest. Request IDs, target paths, payloads and operational
file hashes remain private. [Initial staging snapshot](evidence/issue-10/windows-staging.json)
is historical; its former desktop-lock gate was resolved by the owner.
The [actual recovered result card](evidence/issue-10/orca-not-applied.png)
contains only the already public original profile/context and instructions.

## Validation and review

Eight focused Alpha tests and the full 189-test suite pass. They cover truthful
provenance, exact-runtime admission, unchanged 0.5.0 rejection of Alpha, digest
binding, result/recovery guards and the pinned Windows process boundary.
Independent static review corrected DLL binding and Alpha-specific evidence
schema/filenames. Final independent GPT-5.6 Sol / High review found no material
issue: all 121 private-manifest entries, runtime/state/file invariants and the
clean public capture matched. Exact-head CI is reported by PR #11. No Founder
acceptance is implied.

The affected-surface AI Product Preflight passes the same actual Prepare →
Plugins → communication → recovered result path below, including the original
profile/setting, three labeled values, simulated selection, current-context
warning and NOT APPLIED/manual instructions. Existing navigation/discoverability
polish remains deferred; this qualification adds no new product workflow.
Screenshot review does not newly qualify keyboard/focus or assistive-technology
behavior; inherited text density and discoverability remain deferred polish.

## Recommendation

**Retain the October 15 nightly as the preferred program and physical baseline.**
Official Alpha passes the bounded isolated companion qualification with the
separate 0.5.1 derivative and is suitable as a secondary development/test target.
It is not a drop-in replacement for accepted 0.5.0: the unchanged physical relay
intentionally rejects Alpha context. A program-wide switch would need separately
authorized relay compatibility work and acceptance. This qualification performs
no adoption, merge, deployment or physical rerun.

## Founder Review

The isolated Alpha is left open on Spare with an empty Prepare workspace,
original copied profiles and the recovered completed result. Use this window,
not a normal Orca shortcut. Its owned runtime is beneath
`%LOCALAPPDATA%\HelixOrcaCalibration\issue-10-alpha-3880f2c\runtime`.

1. Inspect **Returned selection**: original Generic PLA – Voron Rapido – Initial,
   **Filament > Print temperature > Nozzle > Other layers**, original
   saved/edited/effective 220°C, simulated 205°C and **NOT APPLIED**.
2. Confirm **Current effective value** remains 220°C and the original profile is
   still selected. The optional instructions refer to that original profile.
3. If the panel has been closed, choose **Prepare > application menu beside
   File > Plugins > expand Helix Calibration Context > Play Helix Temperature
   Communication (no printing)**, then close the Plugins dialog. The same
   completed result returns without a transport command. Prepare also enters
   the workspace from startup Home.

No new Send, Keep original profile, manual save or printer action is needed for
this review. Judge whether this bounded compatibility evidence and the proposed
baseline policy are acceptable. Deferred UX polish remains outside this PR.
