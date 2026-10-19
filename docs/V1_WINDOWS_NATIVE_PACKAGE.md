# Bounded Windows native-engine package

<!-- v1-generator-current -->
Current generator checkpoint: [Clang build39244022330](https://github.com/bigstupid007/helix-orca-calibration/actions/runs/39244022330)
failed before native compilation. Of25 declared dependency targets,23 returned
success, OpenVDB failed at24, and FFMPEG was not attempted. OpenVDB's optional
bare `ccache` launcher reported compilation steps without retained object proof;
`llvm-lib` then found `Grid.cc.obj` missing. No checkpoint or package was produced.
A source-supported `USE_CCACHE=OFF` correction and an early real object/archive
preflight are integrated for actual preflight before another cold build; warning and parity
requirements remain unchanged.

Both YOLO modes retain qualification. All four current native routes still need
a successful corrected package and their own full strict target harness. The
retained227b447 PA pass is historical evidence, not dispatchable by current
owned-input checks and not inherited by the next package. The consolidated compiler/archive correction passes583 tests (six documented
host skips),109 focused Windows checks (five skips), and60 independent review
checks. Actual Windows preflight/build/parity remain pending. All parameter controls, coordination and the accepted physical baseline
remain preserved. [Actual failed-build evidence](evidence/issue-14/generator-blockers/windows-clang-build-r1.json).
<!-- /v1-generator-current -->


Actual Windows package `227b447` is verified on SPARE, including all 17 DLLs.
PA Pattern passes the complete strict harness for the exact retained explicit
50°C context and 0→0.08 / 0.005 parameters. Temperature remains blocked by real
motion differences. Retraction and MVS have respectively 215 and 203 executable
object-name differences; every other executable byte matches. The shared
Windows import now follows Orca's native path normalization, but a new build
and unchanged full parity are still required. The actual GUI and dependencies
used Clang 22.1.3 / VS2026; the retained adapter used MSVC 19.44. The next
candidate aligns that verified recipe rather than changing geometry or parity.
[Exact results and causal evidence](V1_GENERATOR_BLOCKER_CHECKPOINT.md#actual-windows-results-and-shared-causal-corrections).


## Compiler-aligned build contract (v2)

The new workflow selects GitHub's documented [`windows-2025-vs2026` label](https://docs.github.com/en/actions/reference/runners/github-hosted-runners), matching the
retained GUI's actual image family. The builder requires preinstalled VS18
clang-cl 22.1.3, MSVC headers 14.51.36231 and Windows SDK 10.0.26100.0. There is no
compiler/version fallback or toolchain installation on SPARE. Both dependencies
and engine use absolute compiler paths, Ninja Multi-Config and `--config Release`.
A tiny owned C/CXX CMake probe has a 90-second deadline and runs before expensive
dependencies. It discovers the actual compiler/linker selection, verifies exact
identity and positive `/O2`, `/DNDEBUG` and dynamic Release runtime evidence,
and records actual tool hashes. Both real configure boundaries repeat these
checks. Upstream floating-point settings remain unchanged; static/debug CRT or
added fast-math flags are rejected.

The strict `helix-orca-v1-windows-builder/v2` receipt records compiler recipe and
nine actual tool identities: clang-cl, CMake-selected linker, LLVM static
archiver, separately named MSVC cl/link, CMake, Ninja, Perl and MSBuild. The selected linker may be the actual
VS18 LLD 22.1.3 or MSVC 14.51 linker; its path/version/hash must agree with the real
CMake probe and configure results. The probe digest uses shared canonical JSON,
independent of CRLF file encoding. Runtime validation rebinds that probe and
all nine identities and the bound successful uncached archive proof. Legacy MSVC v1 evidence is validated separately and never
relabeled as the Clang recipe.

A separate early archive preflight reproduces OpenVDB's optional bare-cache
launchers ON and OFF under the same actual compiler, archiver and Release flags.
It checks the configured cache value and both global launchers, real AMD64 COFF
object production and a byte-matched object member inside the archive. The OFF
case must succeed before dependency work. Its proof is bound into native inputs
and revalidated by the runtime; the tiny public-source object/archive are retained
for independent inspection. Ambient compiler launchers are rejected or cleared
explicitly, and configured launcher emptiness is recorded at each boundary.

The pinned superbuild forwards `DEP_CMAKE_OPTS=-DUSE_CCACHE:BOOL=OFF` to child
projects. This disables any child honoring that optional cache setting; no
compiler, floating-point or warning policy changes. Preflight-only workflow input
`toolchain_preflight_only: true` runs compiler/archive diagnostics and publishes
evidence without dependencies or a package. It can never qualify a generator.
A restored dependency bundle still receives a bounded local configure/verification
so actual probe/deps/engine records all exist before dispatch.

Clang's global `CL`/`_CL_` inputs are explicitly empty. Only the upstream
MSVC-based CPython/OpenSSL tasks append `/MP1`; the per-target environments,
OCCT-four-job override and all other two-job scheduling are recorded in the
exact dependency contract. New builder/workflow/module bytes invalidate the old
MSVC checkpoint, so this compiler change starts a fresh dependency build. The
same disk/deadline guards apply. A successful Clang package and parity remain pending until
complete receipts and retained-reference comparisons pass.

Focused source review corrected a Windows CRLF probe-digest mismatch and required
positive runtime evidence before launch. The meaningful CRLF roundtrip preserves
valid dispatch and rejects a modified probe. Independent final review passed
29 compiler/backend/cache checks. The integrated boundary passes 568 tests with
six host skips; accepted control preservation and whitespace checks pass. This
is source/checker evidence, not Windows generator qualification.

The consolidated archive/compiler correction subsequently passes583 integrated
tests (six host skips),109 focused Windows checks (five skips) and60 independent
checks. Actual preflight and the corrected full build remain mandatory; source
readiness is not package or generator qualification. V2 warm checkpoint restore
has source/test coverage but is not yet verified on the actual target.

## Retained MSVC v1 packaging and repairs

The clean Windows runner exposed an upstream Expat discovery conflict after all
25 dependencies built: failed system discovery created an `expat` fallback in
the root, then `deps_src/expat` created the same target again. The Windows-only
owned find module now selects the real `deps_src/expat` headers and later-created
static target. It creates no target or binary location itself. Both the Windows
build receipt and reviewed qualification source closure pin this module. Linux
discovery and its existing six owned input hashes remain unchanged. Focused
host CMake tests reproduce the duplicate and build/link one actual target with
the fix; these are not Windows package or calibration qualification evidence.

The Windows target injection also waits until the root directory finishes
configuration. CMake copies directory compile options when a target is created;
the original early project hook missed later upstream MSVC options, including
`/Zc:lambda`, `/bigobj`, `/utf-8` and warning options. The Windows-only wrapper
requires CMake 3.19 or newer and captures its owned include path before deferral.
It preserves the upstream options without duplicating or changing individual
flags. A focused CMake property check compares early and deferred creation;
Windows compilation and exact calibration parity remain separate gates.

The Windows engine package is a separate build target for the approved October
15 Orca commit `6a7763f08d1a175a464a00ce13f0b5a815662fc4`. A successful
package provides an actual PE32+ AMD64 executable, its complete non-system DLL
closure, native calibration resources, source/build receipts and declared source
materials. Building or running `--capabilities` qualifies no calibration. Native
warnings, independent executable parity and exact matching input provenance
remain mandatory before a prepared job can become Ready.

The existing SPARE Windows target has no native compiler/CMake toolchain. The
public-source-only `V1 Windows native engine` workflow uses a disposable
`windows-2022` runner with preinstalled MSVC, CMake, Ninja and Perl. It sends no
profile, retained context, reference G-code or printer information to GitHub.
No software is installed on SPARE by the builder.

The workflow checks out the exact upstream commit with recursive submodules
and LF source bytes. Its disposable Git configuration sets both
`core.autocrlf=false` and `core.eol=lf` before checkout, while explicit upstream
`.gitattributes` rules still apply. A public size/hash/newline-count inventory is
retained before the unchanged strict eleven-file source audit must pass. It builds
the same 25 headless dependency targets and the adapter, without GUI/CAD. The
Windows dependency lock records upstream's SHA-bound prebuilt FFmpeg download
and exact in-tree Windows GMP/MPFR files rather than pretending the Linux
archives are Windows build inputs. Upstream sources and recipes are unchanged.

Top-level dependency execution is serial. CMake/Ninja child builds use two jobs.
The unchanged CPython recipe invokes MSBuild `/m`; that switch uses the machine's
processor count, so this builder rejects runners with more than four processors.
`CL_MPCount=1` and the compiler's appended `_CL_=/MP1` prevent each compiler from
multiplying that concurrency. The explicit upper bound is four compiler jobs
on the four-CPU runner, with two for ordinary CMake builds and four for OCCT alone. The OCCT override
is copied per target, retains the serial outer build and `/MP1`, and is bound in
the dependency recipe/contract and the `occt_jobs` build receipt. Microsoft documents
[MSBuild processor behavior](https://learn.microsoft.com/visualstudio/msbuild/building-multiple-projects-in-parallel-with-msbuild)
and [the appended compiler environment option](https://learn.microsoft.com/cpp/build/reference/cl-environment-variables).

The builder has a 120-minute watchdog, a 3 GiB disk reserve, a 16 GiB peak growth
limit and a 512 MiB reaction margin. It checks headroom during each running
stage and source packaging. Stage logs retain at most 1 MiB plus a 64 KiB tail.
Failure stops only the current owned child process tree. The disposable CI job
owns its fresh build directory and VM; the workflow neither prunes shared caches
nor changes existing Windows/printer configuration.

Packaging recursively reads the actual PE normal and delay imports. Every
non-system DLL must resolve uniquely from the built prefix or the preinstalled
MSVC redistributable and is copied beside the executable. The clean-package
capability probe has only that package and Windows system directories in PATH.
Receipts retain binary/DLL/resource hashes, exact import closure, static library
hashes, the actual compiler/tool hashes, runner image version, application commit
and GitHub run URL. The Python runtime independently rechecks PE architecture,
all DLL hashes/imports, the isolated directory inventory and source/build
identity. A Linux executable, foreign target, missing/substituted DLL or changed
owned input never enables Windows generation.

The build artifacts include the AGPL license, preserved GNU notices, source
notice and a separate source-material archive containing exact recursive Orca
sources, compiled dependency source archives and owned build sources. Bounded
SHA-pinned supplements retain official GMP 5.0.1 and MPFR 3.0.0 upstream sources:
these match the vendored Windows headers and DLL version evidence. GMP's version
was read from its public PE-exported `__gmp_version` data without execution;
MPFR's DLL and header both identify 3.0.0. Linux's newer sources are not substituted.

The unlinked binary-only FFmpeg and CPython external build inputs are excluded
from the source archive. Unused executable/import-library blobs in the recursive
source snapshot are omitted except the exact Windows GMP/MPFR inputs. If the
actual native import closure reaches FFmpeg, Python or those unprovided binary
external components, `source-materials.json` records the unresolved component as
a production source-acceptance blocker. A failed supplemental source download
also remains explicit; it does not erase a built code-only candidate or pretend
its source materials are complete. Resource guards still stop the whole build.

The original vendor compiler, flags and patch history for the pinned GNU DLLs
remain unverified. Matching version sources do not prove that historical build
was reproduced, and complete corresponding source is not claimed. The package
retains this limitation in `source-materials.json`; production source acceptance
remains a separate gate. No saved user profiles or private evidence are present.
Package acceptance also requires an actual successful CI build, local Windows
capability execution and calibration-specific parity. Synthetic guard tests are
checker evidence only.

Every nonexcluded direct and transitive source archive, including the GNU
supplements, must be retained with its locked SHA exactly once. A size/SHA
inventory is written before packaging and its digest binds the source-material
status, native build receipt and package summary. Only inventoried archive
entries enter the source ZIP; the copied stream is rehashed, and a changed,
missing or duplicated archive prevents atomic promotion of the partial ZIP.
Excluded binary-only basenames and unrecognized downloads never enter it.

The unchanged Windows OpenCV recipe enables Intel IPP-ICV, an additional opaque
static component whose vendor build/source provenance remains unverified. This
is an explicit production source-acceptance limitation, alongside the historic
GMP/MPFR vendor-build limits; matching source archives do not erase it. Native
compilation and G-code parity can progress while this gate remains explicit.


## Explicit dependency checkpoint

Actual Windows run [39206549132](https://github.com/bigstupid007/helix-orca-calibration/actions/runs/39206549132)
built all 25 dependencies in about 65 minutes, then failed during engine CMake
configuration at the duplicate Expat target. Its measured dependency growth was
8,434,524,160 bytes, almost the former 8 GiB limit. The new 16 GiB bound includes
retained intermediates, the native build and archive packaging; initial free
space and the rationale are recorded in `disk-budget.json`. Insufficient actual
headroom still stops the build.

After complete dependencies, an optional bounded ZIP preserves the installed
prefix and exact downloaded inputs before native configuration. Intermediates
remain until disposable VM teardown. A normal native failure uploads the
checkpoint with `always()`; cancellation or job timeout can prevent upload.
Count/size capacity failures record an unavailable checkpoint without relaxing
any native build or package gate. Resource, provenance and other failures remain
fatal.

Reuse requires an explicitly selected owned workflow run, producer commit,
attempt and externally pinned inner ZIP SHA. The workflow checks the producer's
repository, head repository, workflow and completed state. The builder verifies
exact source/submodules, recipe, module, builder/workflow bytes, six tool hashes,
fixed paths and named compiler flags, include/library/PATH and SDK environment
inputs. Environment names use Windows case-insensitive semantics and reject
collisions. Changed flags or paths reject restore before dependency commands;
there is no automatic cache selection or fallback. ZIP entries, closed file and
empty-directory inventories, byte hashes, bounds and atomic destination ownership
are checked independently. Restored receipts retain the original publisher and
remain `qualified:false`; a checkpoint never qualifies a generator.


The second actual run [39215986939](https://github.com/bigstupid007/helix-orca-calibration/actions/runs/39215986939)
again completed all 25 dependencies, then exposed an owned checkpoint defect:
it required at least one submodule although this exact source's recursive
inventory is empty. No dependency ZIP or native engine was produced. The
validator now accepts the exact empty list, keeps malformed/duplicate/
uninitialized inventories fatal, and runs before any dependency command.
[Actual Windows checkpoint preflight](evidence/issue-14/generator-blockers/windows-checkpoint-preflight-r1.json)
passes fifteen selected filesystem unit tests, including empty-inventory
create/restore, hardlink publication, flush, Windows no-replace rename, tampering,
rollback and producer checks. The case-sensitive/symlink creation test remains
separate Linux coverage because it requires filesystem/privilege support.
These synthetic file tests qualify no engine or calibration.

OCCT's actual dependency stage took 2,541 seconds at two child jobs. The next
build uses four child jobs only for OCCT, within the existing four-compiler
upper bound, while native and other dependency builds remain at two. Speed or
memory improvement is not claimed before measurement. Disk/deadline guards and
all source, warning, package and parity requirements are unchanged.

Actual [run 39224687302](https://github.com/bigstupid007/helix-orca-calibration/actions/runs/39224687302)
completed all dependencies, CMake configuration and all 307 native compile/link
steps. OCCT took 1,379.5 seconds and native compilation 1,547.485 seconds;
the complete run's peak measured growth was 12,768,280,576 bytes. Packaging then
rejected `wsock32.dll` as an unresolved non-system DLL. Microsoft documents this
[Windows Sockets compatibility library](https://learn.microsoft.com/en-us/windows/win32/winsock/windows-sockets-compatibility-issues-2),
and the actual SPARE system-directory copy has a valid Microsoft Windows
signature. Only that exact library name is added to the OS classification;
unknown/changed private DLLs still fail. No DLL is copied from the system or
substituted, and no slicer warning or parity rule changes.

The [actual build checkpoint](evidence/issue-14/generator-blockers/windows-native-build-r3.json)
retains successful stage receipts, the OS probe and the complete 29,616-file
dependency ZIP's external SHA. This classifier-only correction preserves the
dependency recipe contract, allowing explicitly pinned reuse while the new
native package binds the corrected owned source and new application commit.
Compile/link success is not a completed package or calibration qualification.
