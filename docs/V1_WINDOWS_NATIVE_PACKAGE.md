# Bounded Windows native-engine package

The Windows engine package is a separate build target for the approved October
15 Orca commit `6a7763f08d1a175a464a00ce13f0b5a815662fc4`. A successful
package provides an actual PE32+ AMD64 executable, its complete non-system DLL
closure, native calibration resources, source/build receipts and corresponding
source. Building or running `--capabilities` qualifies no calibration. Native
warnings, independent executable parity and exact matching input provenance
remain mandatory before a prepared job can become Ready.

The existing SPARE Windows target has no native compiler/CMake toolchain. The
public-source-only `V1 Windows native engine` workflow uses a disposable
`windows-2022` runner with preinstalled MSVC, CMake, Ninja and Perl. It sends no
profile, retained context, reference G-code or printer information to GitHub.
No software is installed on SPARE by the builder.

The workflow checks out the exact upstream commit with recursive submodules
and LF source bytes. The existing eleven-file source audit must pass. It builds
the same 25 headless dependency targets and the adapter, without GUI/CAD. The
Windows dependency lock records upstream's SHA-bound prebuilt FFmpeg download
and exact in-tree Windows GMP/MPFR files rather than pretending the Linux
archives are Windows build inputs. Upstream sources and recipes are unchanged.

Top-level dependency execution is serial. CMake/Ninja child builds use two jobs.
The unchanged CPython recipe invokes MSBuild `/m`; that switch uses the machine's
processor count, so this builder rejects runners with more than four processors.
`CL_MPCount=1` and the compiler's appended `_CL_=/MP1` prevent each compiler from
multiplying that concurrency. The explicit upper bound is four compiler jobs
on the four-CPU runner, with two for ordinary CMake builds. Microsoft documents
[MSBuild processor behavior](https://learn.microsoft.com/visualstudio/msbuild/building-multiple-projects-in-parallel-with-msbuild)
and [the appended compiler environment option](https://learn.microsoft.com/cpp/build/reference/cl-environment-variables).

The builder has a 120-minute watchdog, a 3 GiB disk reserve, an 8 GiB peak growth
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

The build artifacts include the AGPL license, source notice and a separate
corresponding-source archive containing exact recursive Orca sources, dependency
archives and the owned build sources. They contain no saved user profiles or
private evidence. Package acceptance still requires an actual successful CI
build, local Windows capability execution and calibration-specific parity.
Synthetic PE/receipt guard tests are checker evidence only.
