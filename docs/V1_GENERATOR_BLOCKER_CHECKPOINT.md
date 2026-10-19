# Generator repair checkpoint

<!-- v1-generator-current -->
Current generation candidate: [`c0fa61d` Windows build 39255585408](https://github.com/bigstupid007/helix-orca-calibration/actions/runs/39255585408)
completed successfully. Actual SPARE execution of the unchanged `exact-executable-v1`
harness qualifies Temperature, PA Pattern, Retraction and Max Volumetric Speed for
the retained explicit unsaved 50°C context and exact parameters. Their executable
streams match native UI references: **106,508 / 2,904 / 16,585 / 35,672 commands**,
with zero mismatches and both invariant sets passing. Both qualified YOLO modes
retain their separate original-context qualification.

Four fresh native 800×480 Helix sessions independently reach actual Windows
Coordinator Prepared with exact request/readback values, real generation and parity;
no Cancel, Confirm or Start is sent. Normal Orca's **1,429-file fingerprint is unchanged**.
All verified controls, ordinary coordination and the accepted physical Temperature
baseline remain intact. [Exact results and limits](V1_GENERATOR_BLOCKER_CHECKPOINT.md#current-r2-generation-and-prepared-candidate),
[parity receipts](evidence/issue-14/generator-blockers/native-four-windows-parity-r2.json),
[native Prepared capture bindings](evidence/issue-14/generator-blockers/native-prepared-ui-r2.json).

Qualification covers these exact contexts/origins/profiles/parameters only. The
original 60°C bed / 55°C filament threshold remains unsupported; the actual PA
negative still reports `native_warning` / `1000C001` before reference selection.
No warning suppression, profile writeback, new physical test, printer deployment
or merge occurred. Hardware, production security and complete corresponding-source
acceptance remain separate limitations; PR #15 stays draft and unmerged.
<!-- /v1-generator-current -->

## Current r2 generation and Prepared candidate

The actual package is built from `c0fa61d2217fb36d1b64c0f515b70beff327399e`,
using the verified October 15 Orca source `6a7763f08d1a175a464a00ce13f0b5a815662fc4`.
Package SHA `5f258c15cf4c4949071491c132e0e643f04e8eeaa52e94ef8b361e1c890d1588`;
PE SHA `c64ef7473c5575d0fc6d35a03b54c607cd160e54b1d5332bad2dd362cf98ff5a`.
The full cold build completed in 5,932.656 seconds, peaked at 9,244,848,128 bytes
of filesystem growth, and exited every stage process. Managed download, actual
SPARE package verification and independent package review pass: 13 owned inputs,
9 tool records, 29 runtime DLLs, 30 AMD64 PE binaries including the executable,
exact import/resource closure and 29 retained source archives / 21,915 members.

| Native calibration | Exact parameters | Executable commands | Result |
| --- | --- | ---: | --- |
| Temperature | 230→190°C, fixed 5°C, scale on | 106,508 | Exact executable stream and both invariant sets pass |
| PA Pattern | 0→0.08, step 0.005; direct drive | 2,904 | Exact executable stream and both invariant sets pass |
| Retraction | 0→2 mm, step 0.1 mm | 16,585 | Exact executable stream and both invariant sets pass |
| Max Volumetric Speed | 5→20 mm³/s, step 0.5 mm³/s | 35,672 | Exact executable stream and both invariant sets pass |

These four use only the retained context digest
`bd62b71f7b082465e61bf1eb193a8fb569a802f075e3828391cfb44166861711`,
its original origin, profile identities, full effective values and independent
native catalog. This context explicitly retained saved bed 60°C and unsaved
edited/effective bed 50°C; no saved profile was changed. The original 60/55 context
is not qualified or substituted: actual PA still fails with warning `1000C001`,
processor error mask 0, before native-reference selection and without Prepared.
Both YOLO modes retain their previously qualified original-context references;
this does not qualify YOLO under the separate 50°C edit.

The underlying corrections align the actual GUI's Clang 22.1.3 / VS2026 / SDK /
Release dynamic-CRT recipe, follow native Windows import-path normalization,
and disable the discovered incidental compiler-cache launcher through supported
`DEP_CMAKE_OPTS=-DUSE_CCACHE:BOOL=OFF`. A real early ON/OFF object/archive probe
proves why: ON produced no objects/archive; OFF with identical compiler/linker/
archiver/configuration produced valid AMD64 object and exact archive member bytes.
The successful full build uses the same guarded path. No geometry, floating-point,
calibration algorithm, slicer-warning or parity-rule relaxation was used.

The unchanged full harness rereads actual native and generated artifacts. All
executable hashes match, including motion, extrusion, acceleration, heaters,
machine limits and object names. Files are **not byte-identical**: comments and
non-executable settings metadata differ. Retained display-only bed asset fields
and inactive Klipper legacy `silent_mode` explain the three footer differences;
no material executable discrepancy is waived. Native invariants pass separately.
Generator qualification does not establish macro internals, accepted hardware ABI
or physical readiness; those flags remain false.

Four fresh native 800×480 review sessions send real UI-selected Generate requests
through the approved bounded metadata relay to real Windows DirectoryEvents and
Coordinator/routing/native `generate`, with `job_adapter=None`. All request copies,
parameters, profile-context digests and native status readbacks match. Each actual
qualified Prepared response is captured after a changed and stable rendered frame,
then the relay exits and its managed review stops cleanly. No native intent is sent.
The private configuration explicitly sets `routes.temperature="native-engine"`;
stock Temperature/YOLO defaults are preserved, and no automatic fallback occurs.
See [four private native Prepared capture bindings](evidence/issue-14/generator-blockers/native-prepared-ui-r2.json).

An initial four-case test sequence was deliberately stopped after its successful
Temperature Prepared capture: it assumed pre-print Cancel, while the current UI
only offers Cancel during printing. That attempt is retained as incomplete test
infrastructure evidence. The corrected proof uses one fresh session per case and
all four complete successfully without Cancel, Confirm or Start. Product UI and
coordination semantics were not changed to accommodate testing. This focused
pointer/request/Prepared proof does not replace the preserved 66bfaf6 all-five
edited-parameter/browser proof or claim another broad UI certification.

Final normal-settings preservation still matches all 1,429 baseline files and
aggregate `41100c88a1cc27e23747ecb9db25a91c621a04b3dc359a5f64e0df5b8d6a9c19`.
Independent combined review covers the package, actual four parity receipts,
extractor, focused single-case helper and native Prepared evidence. Local source
validation passes 583 tests (six host skips), with 109 focused Windows checks
(five skips) and 60 independent compiler/archive checks retained.

Remaining limits: fresh origins/contexts, changed ranges and other profiles lack
matching native references and remain unsupported; non-ASCII Windows paths are
unverified; v2 warm-cache restoration is source-tested but not target-exercised.
Historical vendored GNU build provenance and opaque OpenCV IPP prevent a complete
corresponding-source/production-distribution claim. Existing LAN HTTP remains
unencrypted and is not production-security qualified. The accepted physical
225/220/215°C → 220°C / NOT APPLIED baseline and rollback material are untouched.

The next meaningful Founder Review is this integrated draft PR's generation and
Prepared candidate for the stated supported inputs, including clear unsupported
states. No physical Start, deployment, profile writeback or merge is authorized.

## Historical investigation and earlier blockers

The chronological records below describe earlier source and binary candidates;
the current r2 results above supersede their pending/blocked dispositions. Raw
receipts remain immutable.



The verified native parameter controls and exact request propagation are unchanged.
Both previously qualified YOLO modes retain their exact stock generation sources
and native references. The accepted physical Temperature baseline is untouched.
This checkpoint adds no calibration qualification and is not a new Founder review.

The native import path now follows the pinned GUI's load/volume-center/instance
placement order before Cut. Temperature native preparation is a separate mode
that exits before Print/slicing. Its source-bound Linux build is managed run
`d406f61daa8647ce92fe5defa83f96dc`, executable SHA
`a45d89e73a8eff80d426c89e017eff66fbb77b21fffa7edea1bef0dcdfad9f71`.
The initial geometry run lacked a complete Python execution-closure label.
A fresh run `bd4fad7e9bde4790b804dee73dec62e3` binds/rechecks the Python
closure, interpreter, reviewed lifecycle helper, context/parameter inputs and
native build receipts before/after execution. It independently reproduces exactly
1,361,984 STL bytes, 27,238 finite nondegenerate triangles and SHA
`e7ee12fd387eae6d0ee5f3ca6500fe9376cca8e0dbf229d8394fee2b15b309a6`.
The [reproduction record](evidence/issue-14/generator-blockers/temperature-geometry-reproduction.json)
retains both exact receipts and explicitly identifies nonce/path exclusions.
Each native metadata and request digest is checked separately; normalized
metadata, requests and all remaining receipt fields match exactly. This is
reproducibility evidence, not retroactive provenance or executable parity.

The exact public-source/mesh bundle already proposed for the same SPARE target
is unchanged. Automatic approval review rejected its transfer because the previous
YOLO approval did not authorize this new Temperature payload/destination. The
payload-specific approval was pending at that checkpoint. The Founder subsequently
approved the exact bundle SHA `4859087009be381122f3a877856cfb224367d776831eaf4c30d98ee0b822b222`
for the same SPARE qualification destination. It remains untransferred and unused;
the successful direct native-engine route does not require it.
The existing native Temperature reference is retained. No new reference is
manufactured from candidate geometry. The stock-STL experiment still needs actual Windows slicing and the unchanged
`exact-executable-v1` harness. The separate direct native-engine route below
does not consume or transfer this protected mesh.

The rebuilt PA run `3e5d7650c29346328059b05e81edbb0e` exits 2 and retains
`native-blocker.json` for genuine `1000C001`: original bed 60°C meets/exceeds
filament vitrification 55°C. Its runtime is clear; its lifecycle is honestly
incomplete because preparation failed. No Prepared job is produced. Its 2,904
executable commands match the retained independent Windows native PA reference,
but that scalar diagnostic does not replace mandatory whole-harness qualification
or override the warning. Retraction/MVS share that underlying warning gate.
V1 explicitly rejects this profile/input combination while preserving the request;
this does not claim that native Orca cannot export a warning-bearing file.

The [Windows package build](V1_WINDOWS_NATIVE_PACKAGE.md) has an actual
MSVC/PE/DLL/corresponding-source build workflow, with focused negative checks.
The disposable public-source-only CI build must succeed before actual Windows
execution/parity can be attempted. Source portability and checker tests alone
qualify no Windows route. The SPARE machine has no native compiler toolchain;
none is installed there. Supported warning-free combinations require an honest
matching native UI reference, without changing original profiles silently.

The substantial combined source review through `02b9676` found no remaining
material source defect; target execution/parity remains pending. The next meaningful Founder review
is a candidate with actual Windows package evidence and exact generation/parity
results, or an explicit residual blocker that prevents that product milestone.
No physical action, deployment, profile writeback or merge is authorized.

## Integrated Windows qualification continuation

The first actual Windows CI attempts exposed environment-command quoting,
Windows checkout line endings and CMake cache-path escaping. Causal fixes use
an owned CRLF batch file, LF checkout (preserving explicit upstream batch-file
attributes), and forward-slash CMake cache paths. Strict source hashes are
unchanged. Bounded failure logs and lifecycle records retain each failure.

Package source materials now have a closed hash/size inventory, unique required
archives and a same-stream rehash into an unpromoted ZIP. Unknown, missing,
substituted, duplicated or late-mutated archives make the source gate incomplete;
only explicitly excluded binary build inputs may be ignored. Matching GNU
upstream source versions and original licenses are retained where verified.
Historical vendored compiler/patch provenance and OpenCV's opaque Windows IPP
component remain explicit production source-material limitations; there is no
complete-corresponding-source claim. Upstream compilation behavior is unchanged.

The shared [Windows qualification driver](V1_WINDOWS_NATIVE_QUALIFICATION.md)
uses externally pinned source and input bytes, an actual PE/DLL/resource-bound
package, the existing native engine entry point, and unchanged strict parity.
Its separate registration mode calls the original native invariant harness and
always reports unqualified. Source/resource/input mutations prevent publication;
warnings preserve the requested values and actual blocker without Prepared.
Independent review found no remaining material defect in that driver or the
Temperature stock helper's corrected source binding.

Native UI investigation found that the installed Generic PETG system profile
exposes six saved nozzle temperatures while the active contract requires an
unambiguous single value; its 80°C bed / 70°C threshold would also warn. It was
not silently coerced. The original filament was restored without preset saving.
A separate qualification input deliberately edits both bed fields to 50°C in
isolated native Orca, without saving. Native capture SHA
`bd62b71f7b082465e61bf1eb193a8fb569a802f075e3828391cfb44166861711`
retains the original 60°C saved values. The only differences are those two
filament edited/effective fields; printer/process and every saved configuration
match the original context. Each native calibration setup must independently
match this exact captured context before preparation; the UI's explicit
Transfer action carries these unsaved values into the qualification project.
Between cases, native Discard restores saved settings. Fresh UI exports remain
private and are distinct from every generated candidate. This input qualifies
nothing until real Windows generation and strict parity both pass. It never
qualifies or substitutes for the original 60/55 input combination.

The direct native-engine Temperature case uses genuine native Cut and calibration
state on Windows. It is separate from the still-untransferred STL experiment;
no protected mesh payload is consumed or transferred by that route.

Combined local validation at `32f3a68` passes 522 tests (two Windows-only skips)
and the unchanged-control preservation gate. The subsequent closed-inventory
classifier correction passes all 14 focused Windows guard tests. Actual Windows
build/target/parity evidence remains required; no new generator is yet qualified.


## Grouped actual generation diagnostic

The four independent native UI references for the explicit unsaved 50°C context
are retained separately on Windows. Each registration passed the unchanged
native invariant harness and remains `qualified:false`. Independent review of
the twelve native parameter/sliced/exported frames and four settings/restoration
frames found no reference-readiness blocker. It did not operate the UI or qualify
a generator. The original settings were restored; the 1,429-file normal profile
inventory remains byte-identical.

The [grouped diagnostic receipt](evidence/issue-14/generator-blockers/native-four-linux-diagnostic-r1.json)
binds four completed managed Linux generation runs to the exact native-captured
context, native build, complete Python execution closure and immutable inputs.
All four have zero processor errors/warnings, passing candidate calibration
invariants, exit zero and cleared owned runtimes. A hash-verified Windows probe
calls the unchanged executable parser against the separate native UI exports.
Only fixed counts/digests returned; no new raw G-code or profiles transferred.

| Calibration | Candidate executable commands | Native executable commands | Executable digest |
| --- | ---: | ---: | --- |
| Temperature | 106,517 | 106,508 | Material motion differences; under causal investigation |
| PA Pattern | 2,904 | 2,904 | Exact match |
| Retraction | 16,585 | 16,585 | Exact match |
| Max Volumetric Speed | 35,672 | 35,672 | Exact match |

The Temperature difference is material: a first-layer brim move and later
motion/acceleration streams differ, despite matching extents and passing
calibration invariants. Nine is the net command-count difference, not nine
isolated harmless commands. A second fixed-scalar Windows probe confirms that
the retained original 60°C and new 50°C native motion/acceleration/progress
streams match exactly; the discrepancy belongs to the candidate generation path.

These are diagnostics, **not Windows or whole-harness qualification**. The
source-pinned actual Windows build at `b64656d` is
[run 39206549132](https://github.com/bigstupid007/helix-orca-calibration/actions/runs/39206549132);
its three preservation/policy checks passed independently. The actual Windows
package must run against the retained references through the mandatory complete
parity harness before any newly supported generator is described as qualified.
The original 60/55 warning-bearing combination remains blocked.

The native-only [exact-input catalog](V1_WINDOWS_NATIVE_QUALIFICATION.md#native-only-exact-input-reference-catalog)
selects among independently registered exact input pairs without worker
reconfiguration. Its strict context key includes the capture origin; a fresh
origin remains unsupported until independently registered. No reference
rebinding or profile-only equivalence is claimed. The YOLO route and its
previously qualified modes are unchanged.


At the integrated catalog/provenance candidate `fe9d415`, the required local suite
passes **533 tests** with two Windows-only skips. The unchanged native-control
preservation gate and whitespace check pass. This broad local boundary check
does not replace the pending Windows target checks.


## Windows build repair after actual dependency completion

Run 39206549132 failed at engine configuration after all 25 dependencies passed.
The failure was a duplicate upstream `expat` target following failed system
Expat discovery. The Windows-only module now selects the genuine bundled
headers and later-created target. A separate deferred-target wrapper ensures
the native target inherits the upstream root's final MSVC compiler options.
Four real CMake fixture checks passed in the pinned, network-disabled tool
container (managed run `76598c80a1164d00ad954abd7b67717c`, four passed,
zero skipped). This proves CMake behavior, not MSVC compilation or G-code parity.

An explicit dependency checkpoint retains progress before native configuration;
its provenance, integrity and restore gates are documented in
[V1_WINDOWS_NATIVE_PACKAGE.md](V1_WINDOWS_NATIVE_PACKAGE.md#explicit-dependency-checkpoint).
The measured 8,434,524,160-byte dependency growth justified a declared 16 GiB
peak bound while retaining the 3 GiB reserve, 512 MiB margin and 120-minute
watchdog. No early intermediate deletion, warning suppression, C++ generation
change, profile change or parity relaxation is included. Actual successful
Windows compilation and local full parity against the retained UI references
remain outstanding; no additional generator is qualified by this repair.

The integrated boundary passes **557 tests**, with six host skips (four CMake
checks separately passed in the pinned offline tool container and two Windows-only
checks). Accepted parameter-control preservation and `git diff --check` pass.
The final independent re-review confirms the environment-contract finding is
resolved; twenty affected wiring/Windows guard tests passed independently.


## Empty-inventory checkpoint correction

Actual run 39215986939 completed all 25 dependencies with exit zero, then the
new checkpoint rejected the exact empty recursive submodule inventory. This was
an owned validator assumption, not a slicer failure. No ZIP or native executable
was retained. The correction accepts an exact empty list and moves complete
provenance validation before dependency commands. Malformed/uninitialized rows
still fail. Twenty-four focused local module/wiring tests and fifteen actual
Windows filesystem tests pass; the lead wiring and scoped OCCT-four-job override
passed independent review (eight wiring tests). Accepted control preservation
and whitespace checks pass. The previous integrated 557-test boundary remains
retained; no broad UI recertification was repeated for this narrow repair.
Actual MSVC compilation and full four-route parity remain outstanding.

## Actual MSVC success and packaging classification correction

Run `39224687302` completed all 25 dependencies, native configuration and all
307 compile/link steps. The third attempt retained its full explicit dependency
checkpoint, then failed packaging on `wsock32.dll`, an omitted Windows Sockets
compatibility system library. Official Microsoft documentation and a read-only
actual SPARE system-file/signature probe establish its identity. The correction
adds only this exact name to the system classifier. The focused Windows guard
suite passes fifteen checks, including acceptance without bundling that OS DLL
while still withholding parity qualification and rejecting unknown names.
The frozen `b603ffb` integrated boundary passed 561 tests with six host skips.
No broad UI capture was repeated. Actual Windows package execution and full
four-route native parity remain pending; no new generator is qualified.
See [exact stage and dependency checkpoint evidence](evidence/issue-14/generator-blockers/windows-native-build-r3.json).


## Actual Windows results and shared causal corrections

[Real package/run 39233686041](https://github.com/bigstupid007/helix-orca-calibration/actions/runs/39233686041)
passes source/PE/resource/import checks on SPARE. Package SHA
`d4f250e89867b2e49df0ca179420f6ce6d0880c381987de5805a7d0f72eba07c`,
real executable SHA `6136a1ddd821ea083307073de8682329cdc6e8917adfb69b43a77ed5a7a63dc0`.
Independent package review rechecked all 17 DLLs, 13 owned source inputs,
11 upstream pins, three resources and 29 source-archive entries. Explicit
checkpoint restore preserved its original producer. Complete lifecycle elapsed
2,996.922 seconds, peak growth 5,041,557,504 bytes, all children exited. Historical
GNU vendor builds and opaque static IPP remain production source-acceptance
limits; package completeness is not that acceptance.

The [four actual production-generator/harness results](evidence/issue-14/generator-blockers/native-four-windows-parity-r1.json)
use the retained independent native UI references and exact explicit bed50 context.
PA Pattern qualifies: both streams contain 2,904 commands with SHA
`5e8e5478a1f5b312e7ff3d21a547948f648a4c5c9c65e61745c7fece3f273173`.
Retraction and MVS stay unqualified: 215 of 16,585 / 203 of 35,672 commands differ.
[Full positional diagnosis](evidence/issue-14/generator-blockers/windows-name-differences-r1.json)
proves only `EXCLUDE_OBJECT_* NAME` tokens differ, with every other byte unchanged.
Pinned GUI Plater9026 calls `make_preferred()` on Windows because the DRC loader
splits names only at native separators. The adapter omitted this normalization.
The minimal shared correction follows that exact behavior; Linux path bytes,
geometry, config and warning semantics are unchanged. Diagnostic name masking
never qualifies output; the corrected real binary still needs the full harness.

Temperature remains unqualified: Windows candidate 105,929 / native106,508
commands, material toolpath/acceleration differences, no native warnings and
both calibration invariants pass. [Numeric motion diagnosis](evidence/issue-14/generator-blockers/temperature-windows-numeric-r1.json)
finds the first geometric difference at top-surface layer5, an 8.731mm Y endpoint
choice with equal extrusion, and differences on 381 layers. It is not number
spelling alone. [Geometry-only diagnosis](evidence/issue-14/generator-blockers/temperature-windows-geometry-r1.json)
reproduces exactly the retained Linux STL SHA `e7ee12fd387eae6d0ee5f3ca6500fe9376cca8e0dbf229d8394fee2b15b309a6`
on Windows: 27,238 triangles / 13,585 vertices. Native saved-project XY projections
match; its tiny reconstructed Z discrepancy is limited serialized transform
precision, not proof of a missing Cut step. All private geometry remains on SPARE.

[Actual upstream compiler provenance](evidence/issue-14/generator-blockers/native-gui-compiler-provenance-r1.json)
confirms GUI and dependencies were built with Clang22.1.3 on
`windows-2025-vs2026`, VS18/MSVC14.51, Ninja Multi-Config. The adapter used
MSVC19.44 on Windows2022. This established recipe mismatch is the next shared
correction; no Cut, random seed, TBB or floating-point workaround is justified.
The old dependency checkpoint is retained and is not relabeled for a different
compiler recipe. The corrected build requires fresh strict provenance and parity.

The three absent native footer options are `bed_custom_model`,
`bed_custom_texture` (display assets) and legacy-ignored `silent_mode`. The latter's
executable consumers apply to Marlin stealth estimation, inactive in this retained
Klipper case. These are documented non-executable provenance differences, not a
waiver for the remaining real command differences.

[Actual original-profile negative test](evidence/issue-14/generator-blockers/windows-original-warning-r1.json)
verifies the product throws `native_warning` / `1000C001`, processor mask0,
before native-reference selection; no Prepared job is produced. The normal
1,429-file Orca fingerprint remains unchanged after all actual generation and
geometry probes. Both qualified YOLO modes, functional control proof and accepted
physical Temperature evidence remain untouched. No print, deployment, writeback,
firmware/configuration change or merge occurred. No intermediate Founder review
is requested.


The integrated compiler-aligned source now uses a separate strict v2 receipt,
a guarded actual C/CXX compiler/linker preflight before dependencies, and the
same checks after both real configurations. Native and dependency builds select
Ninja Multi-Config Release. Clang flag inputs are empty; only real MSVC helper
builds append `/MP1`, with all per-target environments recorded. Canonical probe
hashing has a Windows CRLF roundtrip regression and dynamic Release runtime has
positive checks. Independent review passes; the integrated suite passes 568
tests with six host skips, control preservation and whitespace checks pass.
Actual Clang build/package and complete four-route parity remain pending. No
old cache publisher or old generator qualification is relabeled for this recipe.


## Clang dependency-cache correction and early proof

Actual run39244022330 uses the verified VS18 Clang22.1.3/LLD22.1.3 recipe and
passes the real compiler probe. It stops at dependency24of25, OpenVDB;23 prior
stages returned0 and FFMPEG was unattempted. Lifecycle is honestly failed,
3,967.782 seconds with6,835,007,488 bytes peak filesystem growth; all stage
processes exited. No dependency checkpoint, native compilation or package exists.
The bounded metadata-only evidence fetch completed with runtime clear.

Pinned OpenVDB's `USE_CCACHE` option auto-discovers an incidental cache and adds
bare `ccache` as both global compile and link launcher. The archive command then
reports `Grid.cc.obj` missing. Ninja's reported compile steps are not proof that
objects existed: the whole OpenVDB stage took4.547 seconds. Root-cause proof must
check real output files rather than infer them from the log. Orca's pinned
superbuild forwards `DEP_CMAKE_OPTS` to each child; explicitly configuring
`-DUSE_CCACHE:BOOL=OFF` removes that optional wrapper without editing upstream
source, compiler flags, profiles, warnings or parity. Assimp already disables its
own optional cache. The bounded source audit found no further core auto-launcher.

An early ON/OFF static archive preflight will record actual bare-cache resolution,
discovered cache bytes/version and identical compiler/archiver/flags. The OFF
case must produce an AMD64 COFF object and valid archive with no link launcher.
A dispatch-only preflight skips all dependencies and cannot qualify a generator.
Its actual result is required before the next expensive cold build.

Independent combined review also corrected runtime compiler-proof validation:
actual probe/dependency/engine records, compiler/linker/Release identity, flags,
release digest and toolchain/command/source binding are checked before dispatch.
Legitimate dynamic CRT normalization remains supported; static/debug CRT and
fast math remain rejected. Final runtime-only boundary passes573 tests withsix
host skips and preserves the66bfaf6 control/request proof. Historical v1 schema
recognition does not make227b447 dispatchable under current owned-source hashes.

The [actual read-only native-project metadata check](evidence/issue-14/generator-blockers/temperature-native-override-metadata-r1.json)
finds only eight expected Temperature object overrides and extruder1, structural
volume metadata, and three plate mappings matching the retained context. No
unlisted settings or layer overrides occur. The old saved60 project and explicit
bed50 context remain distinct; this is diagnostic evidence, not provenance
rebinding or qualification. It supplies no hidden top-fill configuration cause.
