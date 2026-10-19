# Bounded Windows native-engine package

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
