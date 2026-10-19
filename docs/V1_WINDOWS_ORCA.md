# V1 isolated Windows Orca observations

These are actual Windows UI/CLI observations for Issue #14, separate from the
synthetic native Helix matrix and Linux lab. The target is the October 15
`6a7763f08d1a175a464a00ce13f0b5a815662fc4` nightly, executable SHA-256
`e2b6da4c20e7080eade97379f326dcfcaa90f1ecb9991f1db9eb61e3065a9759`.
A dedicated marked `v1-qualification` data directory and separate WebView storage
reuse only copied test profiles. Accepted/normal installations, printer config,
physical grants and rollback material are not runtime inputs for this candidate.

## Historical companion observations

R5 generated self-contained source SHA-256
`9d02d75abe03d0614e2e5313caa489c838cedc1778a2109b8b2d5a15137dc61e`
was installed, replaced and activated through the real native plugin manager.
The native action launcher opens the V1 dock. Selected profile/nozzle fields,
preparation status, explicit review-only physical execution notice and provenance
expander render in the actual Windows WebView. No preset setter is used.
The retained screenshot `v1-r5-companion-open.png` SHA-256 is
`26daba62e5b32f85369770acc3d8b8259f6da486bdef4e6d3b47789877aa29c6`.
Full screenshots remain private because they show the owner's profile identities.

The real callback captures saved, edited and effective configuration separately.
Complete R4 and fresh pre-calibration R5 snapshots are byte-identical SHA-256
`3bf24bab6c2ac71cf7c0017d8889d4430006d3cd489a512ff656990f41324b3c`,
with 775 effective serialized keys, 0.4 mm nozzle and explicit empty post-processing.
The original incomplete context omitted that key and is retained as failed
provenance; it was never silently repaired into a complete native reference.

## Independent Temperature reference and actual generation

The native calibration dialog independently prepared the default PLA standard
tower 230→190°C, 5°C step, auto-scaling enabled, from the original context. The
reference model was not imported from the programmatic recipe. Native slicing
and local G-code/project Save As actions produced the retained Windows reference.
The final native G-code is 3028201 bytes, SHA-256
`512eb13a80788bd22f928b1b073382070a7c43b5c667efd08ffcc05e550e29b7`.
Its Windows-local 3MF is 341982 bytes, SHA-256
`f6ac5e0a1bf46f7caeb826c0059dd0044a451be253a707fa81a51689fc6fbdbd`.

The bounded stock CLI helper then executed the same pinned Windows executable
with matching exact input context, separate job data/browser directories and
explicit High Temp Plate. The verified run returned exit 0 in 1.593 seconds;
G-code 2965977 bytes SHA-256
`7bcb855addd5747b4c8a2d8eb2c606b7d4415ff8b82ebe9543f7e3a840e9e544`.
A preceding run whose PowerShell exit-code capture was unavailable remains a
failed qualification attempt; output existence was not treated as exit 0.

Both actual files pass the 450-layer/nine-temperature-section deposition
invariants. Their executable streams differ. Exact metrics and measured
geometry/brim diagnostics are in [generation/parity](V1_GENERATION_PARITY.md).
Qualification remains false; no command, mesh or flow difference is waived.
The private reports retain exact commands, inputs, screenshots, helper/ZIP hashes,
stdout/stderr and artifact bytes. Public documentation exports only bounded
metrics and digests.

## Native references and historical first YOLO comparison

Native YOLO Recommended/Archimedean surface was independently prepared and sliced
through the native Flow Ratio dialog, with local G-code and 3MF references retained.
The actual stock Windows CLI run completed with exit 0 in 2.457 seconds using
approved exact bundle SHA-256
`d2296b855fbc2ace4d61817bf91454572ecd534da3341ee5dcc3155d42072996`.
Candidate G-code 1559700 bytes SHA-256
`ce05e8bd2acc16ceea51781745357bc90b87cb72800634eff60bc99061f358cb`;
native G-code 1576258 bytes SHA-256
`0fb149a6a1624cdf64cb03a8c0dcb0fc6a21d9d3f43a4fb0f3389e4e48485daa`.
Both pass the ten-layer YOLO invariants, with identical 4854.673 mm extrusion
and 43241 deposition moves. Executable commands differ (55268 versus 55273),
as do the dynamic acceleration stream, motion stream and printed XY bounds.
There are five classified emitted-setting differences and no unclassified
setting differences. That historical R6 candidate had strict parity **false**, report SHA-256
`5c5fb10764918deba29573a1ac5465b108ffdf659ad92418ed79152e287b27d3`.
No numerical or geometry difference has been waived.

Native direct-drive PA Pattern was independently prepared at 0→0.08 by 0.005,
numbering enabled, and exported locally. Its genuine native inspection passes:
4 custom layers, 17 values, 3 walls per sample, 789 deposition moves and 2904 executable
commands at 220°C. Native G-code 92568 bytes SHA-256
`53fcd2d926eac9dbe9979450a4b0d4ba30ed9025c2f9bcc3eead155b7300eab5`;
manifest SHA-256
`4583a44a32f8611f201b60ad89f8b2345384a40ca42a4b5dd69f3157c87e5452`.
This registers actual native evidence, not candidate qualification.

Native Retraction independently prepared 0→2 mm by 0.1 mm. Its 107-layer,
21.4 mm tower was sliced and locally exported: G-code 539980 bytes SHA-256
`0f5dec36bf301cf94c2c9824d940d725083ae5b8b873435a493887533a2de678`;
3MF 127420 bytes SHA-256
`de12eb4abd834235a58bacc4f4b8ffc13a55873f9f91c754670c4b14ebd8baa7`.
The initial native invariant inspection failed `retraction_episode_length` and is
retained unchanged. A bounded local diagnostic found seven transition episodes
among 204 software retractions: recorded motion Z still belongs to the previous
layer while the next deposition belongs to the next nominal layer. The corrected source-derived checker associates the final negative-extrusion
command with that layer's independently measured deposition Z. Its fresh,
separately retained inspection passes 202 checked episodes across 107 layers;
report SHA-256 `5e0d0a19ee77809f30e1195c667ed32dd9f2ec77e36de4033f9525ba936f23f5`.
Tolerances remain unchanged and forged wrong-length top-ups still fail.

Native MVS independently prepared 5→20 mm³/s by 0.5. G-code 1296372 bytes,
SHA-256 `3e204ce2d2cd1ede29e68ae4e375160dea966d9877ece05c9ce3be7e14c30a97`;
3MF 104748 bytes SHA-256
`28fd4295f90628ad9f748b54a43a5143142c6500a9afa4822535d6e1a4bae35c`.
The native inspection passes 101 layers and 99 checked outer-wall ramp layers;
report SHA-256 `2a9b765e2047f2352f3e0ac85dfcc658e3c509099088760fba86a3986f0874ac`.
These three native-engine-family references do not qualify programmatic output.
No programmatic artifact may serve as its own native reference.

The source-only metrics/parity utilities execute locally on Windows with the
existing Python in isolated/no-site mode. Complete native projects stay there;
whitelisted scalar geometry/settings summaries can be retained separately. No
profile/configuration/model payload is published with these observations.
The Spare bridge is testing infrastructure, not an ordinary runtime dependency.
Actual detached coordinator lifecycle and Win32 ACL evidence are recorded in
[V1 Windows runtime](V1_WINDOWS_RUNTIME.md), without physical activation.

A read-only Windows toolchain probe found no existing `cmake`, `ninja`, `cl` or
`msbuild` command and no Visual Studio Installer/VC toolchain registration. No
build tools were installed. The current native-engine build is Linux x86_64 only;
its executable/receipt cannot qualify Windows generation or packaging.

After all five native preparations and local exports, the pre-V1 normal-profile
fingerprint remains unchanged: 1429 `.json/.conf/.ini` settings/profile files,
aggregate SHA-256 `41100c88a1cc27e23747ecb9db25a91c621a04b3dc359a5f64e0df5b8d6a9c19`.
Only isolated native test edits were discarded; the baseline was not rewritten.
The [public-safe reference inventory](evidence/issue-14/windows-reference-inventory.json)
retains all five native checks, exact source/report digests, the historical
Retraction failure, historical R6 YOLO parity failure, later R8 production pass
and preservation proof.

At this pre-R7/R8 checkpoint, runtime refresh and review corrections remained
open; the later sections record their completed outcomes. Other generator
comparisons and Founder acceptance remain open. No
new physical print, upload/queue, heat/motion, firmware/configuration change,
writeback or printer deployment is validation evidence for this program.

## R7 companion and R8 production YOLO correction

The corrected self-contained companion source SHA-256
`3c03e972706431469700d801ba3177d588d3e0e094bde73f8d04ed10f6bcda6a`
was installed and activated through the marked isolated GUI's native plugin
manager. Its actual waiting screenshot SHA-256 is
`49970c962adbfa06186f52eacbaed4827a106a854d0c9b931d6e36a5d31ff2af`:
heading and attention badge consistently say Waiting for Helix, the control says
Refresh selection, and physical execution is explicitly disabled. The isolated
GUI was gracefully restarted using the validated explicit NUL handle-list
launcher; both normal Orca instances remained running. An update notice was
dismissed without accepting any update. An occluded capture was rejected by
the existing guard and retained; no guard was weakened.

Actual R8 YOLO production generation now passes strict native-reference parity,
report `f2fbe79592c354b61bf5051295c0d3f2a2d2bae8e2657e3026dd8dbe10227a92`.
See [the exact run and hashes](V1_GENERATION_PARITY.md#corrected-actual-windows-yolo-production-parity--r8).
This supersedes the failed R6 candidate and unsupported-option R7 attempt only
for this new exact combination. It does not qualify Temperature, other routes,
physical hardware or deployment. The waiting screenshot does not prove active
job/result/profile-switch behavior; those target observations remain separate.

## Integrated native companion workflow — R8

The current complete runtime source was staged as public code only. Its actual
offline coordinator read the originating companion's unchanged original context,
issued a fresh request and invoked the production stock generator. It reached
Review with exact native-reference parity qualified: report
`2f8cdcf6d64746411739c5775d2739c89e51940f8ed3c97e6b72cf612f75d320`,
prepared job `f18fdf1c33c5997278a373c37e5e442d3b13d3ea2659ae74672427dbdec90421`.
This distinct fresh generation retained G-code
`d16f991f4d92eef7d500840bff487c0843ee5686988f0ba7d87b2f9a9ea951d1`.
The actual dock displayed Ready to review on Helix, the qualified calibration
and original profiles. No job adapter, Confirm or Start was supplied.

Selecting another existing copied Process through the isolated native selector
changed the current captured context to `15c19222…`; the dock updated Current
Orca selection while keeping Original calibration context and the prepared job
unchanged. A misplaced click had first opened a delete-preset confirmation;
**No** dismissed it, and no preset was deleted. The original copied Process
selection was restored after the test. A final private comparison confirmed all
saved, edited and effective values exactly equal the initial snapshot (excluding
the deliberately fresh origin ID).

A separate, explicitly labeled **synthetic completion UI fixture** then exercised
the real companion's result inbox, durable original-context commit and receipt.
This was not a print or independent physical completion. The actual dock showed
Result returned, the original-context value and NOT APPLIED, while the changed
current selection remained separate. Readback verified the exact returned result
and receipt SHA-256 `e26b10496ebe5d6042d7f7f518c7432f367aaa2f76039e67839e28cf2b14b78d`,
and original context `3bf24bab…`. The review message states that no printer was
contacted. The coordinator's actual job journal remains at Review; the synthetic
result fixture does not manufacture a real completed job.

[The bounded workflow inventory](evidence/issue-14/windows-companion-workflow.json)
retains source, preparation, screenshot and result digests without profile names,
G-code or screenshots. Independent cold visual review found these three states
healthy and coherent. Changed rows could benefit from an explicit difference
notice; current users compare the separately named profile lists. The synthetic
message sits lower in the result view, so complete un-cropped evidence must be
used. Runtime accessibility remains unqualified.

The final post-R8 normal-settings fingerprint again passed: **1429 files**,
SHA-256 `41100c88a1cc27e23747ecb9db25a91c621a04b3dc359a5f64e0df5b8d6a9c19`,
matching the immutable pre-V1 baseline. Accepted printer behavior/configuration,
physical Temperature evidence, normal profiles and rollback were untouched.

The original R8 qualification driver (SHA-256
`ceb422fd0b9d273698f030982605084e95a35bbeef76bd852211bde70a9ee621`)
is retained with the private run. Its actual invocation used isolated Python
without optimization; its then-current checks executed. Independent review later
found those test-only checks used `assert`, so optimization could remove them.
The committed `scripts/v1-windows-companion-qualify.py` now uses explicit
`require` gates, exact isolation-marker identity, local-root/checkout/storage
ancestry and reparse/symlink refusal, pre-import source hashing, bounded local
reads/writes, no-reuse and exact result/receipt validation.

The hardened source SHA-256 is
`8d829f66990701a503e575f041b35ba1701abe1a5a773558d1efdc7da2c4736b`.
Actual Windows `-I -S -O` readback passed against the existing native commit and
receipt, and an optimized wrong-root invocation was refused before payload writes.
No new synthetic completion was written. Two dependency-free `python -O`
negative tests separately prove wrong-marker and linked-ancestor rejection
without modifying an unrelated view/inbox. The independent reviewer rechecked
and resolved this finding.

This helper is **testing infrastructure**, not the product runtime. `prepare`
requires the exact original context, fresh workflow directory and no existing
job/result, then calls the real offline CLI twice. `result-simulation` requires
a changed current context and no existing result before writing only a labeled
synthetic fixture below the marker-verified isolated host storage. `readback`
checks the native plugin's exact original-context commit and receipt. It cannot
contact a printer and supplies no job adapter or physical intent. Retain the
existing run rather than replaying preparation in populated review storage.


## Functional parameter correction: separate Perfectionist reference

The lead independently selected YOLO Perfectionist in the actual isolated native
Flow Ratio dialog, kept Archimedean Chords, sliced/exported locally, and ran the
production generator. The [scalar evidence](evidence/issue-14/parameter-windows/README.md)
retains exact source/provenance/parity digests:82,060 executable commands and63,357
model moves match, with all invariants passing. Both mode-specific references are
separate; Recommended R8 is unchanged. Before preparation, saved/edited/effective
profiles, runtime and nozzle matched the preserved original; origin IDs remained
distinct. Full profiles/projects/G-code/Windows screenshots stay private/local.
The post-correction normal fingerprint again matches all1429 files and
`41100c88a1cc27e23747ecb9db25a91c621a04b3dc359a5f64e0df5b8d6a9c19`.
Native-selected identity propagation to the Windows coordinator has separate
focused relay/operator evidence; standalone generation does not prove that step.
No physical execution or deployment follows from parity.

Final native-selected request propagation is now independently verified in the
[focused proof](evidence/issue-14/parameters/README.md): all five exact requests
match real Windows DirectoryEvents and journal readback. Perfectionist actually
generates and reaches qualified Review with request-bound strict parity report
`ffe947043c42596beea42d2e376aa6e0dceba8599c119626668326164a494013`.
Four blocked Windows routes preserve their changed values and report real
capability reasons, without dispatch or artifacts. Final normal-profile readback
again matches1429 files and the original aggregate fingerprint. Current companion
label changes have source/focused callback coverage; they were not deployed to an
operational installation during this correction.
