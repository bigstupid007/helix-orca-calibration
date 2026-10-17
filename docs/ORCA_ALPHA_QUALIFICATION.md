# OrcaSlicer 2.5.0 Alpha compatibility qualification

Status: **blocked on owner desktop unlock; static candidate reviewed** under [Issue #10](https://github.com/bigstupid007/helix-orca-calibration/issues/10).
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

## Windows qualification and recommendation

The generated Alpha-only `0.5.1` companion has SHA-256
`9b79d6150b4f0102a8e5ed8b43491005ddfb3834f4e099d9eb470c870a4c41b7`.
Eight focused Alpha tests and the full 189-test suite pass. Source-bound Issue
#8 native evidence and accepted Issue #2 harness evidence still verify, with
accepted implementation/evidence bytes unchanged. Independent static review
found no remaining material issue after correcting DLL binding and Alpha-specific
saved-report schema/filenames. The guarded Windows tool pins both executable
and DLL before process admission. This supports a reviewed draft candidate,
not a completed qualification or a merge-ready PR.

Actual native UI proof, normal preparation/export, exact file association,
simulated return, persistence, profile switching, stale/duplicate rejection and
preservation checks remain to be completed. Startup is observed as a separate
Alpha process with the pinned path/datadir and isolated WebView2 child; a locked
Spare desktop correctly prevents capture/input until the owner unlocks it.
Source comparison and launch inspection do not substitute for these GUI gates.

**Provisional recommendation: retain the October 15 nightly as the preferred
baseline.** Alpha is source-compatible for the used APIs and has a bounded
exact-runtime derivative, but actual Windows UI/behavior gates remain open.
The after-staging fingerprint matches all 1,429 normal settings/profile files,
61 sampled nightly configuration/plugin files and both accepted nightly binaries.
No normal installation or accepted nightly artifact was overwritten.
The final recommendation requires the actual Windows run and its evidence review.
The October 15 nightly remains preferred for the already accepted physical workflow.
Any final recommendation will distinguish isolated Alpha development use from
adoption of a new physical baseline, which is outside this qualification.
