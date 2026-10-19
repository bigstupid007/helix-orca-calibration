# V1 grouped native-engine reuse

Build Program #14 owns this investigation. Baseline:
`6a7763f08d1a175a464a00ce13f0b5a815662fc4`, the accepted October 15 Orca nightly.
The real Linux x86_64 native adapter and its capability command now build.
The native enum-default startup repair passes actual retained-configuration
loading and Temperature model preparation. The subsequent wait is now localized
to Orca's thread-name/locale initialization barrier; the downstream two-worker
task-arena repair awaits its targeted runtime check.
No native calibration is qualified by this document. All five independent
native Windows references are retained separately; they do not change the
adapter's generation status. The accepted physical Temperature milestone and
lab remain unchanged. Historical checkpoints below retain the actual failures
rather than implying that a successful build alone is a working or qualified
generator.

## Common engine and three preparation families

All five can ultimately use the same Orca engine. The genuine C++ surfaces are
`Print::apply`, `Print::process`, `Print::export_gcode` and
`Print::set_calib_params` ([Print.hpp, lines 1080–1085 and 1343](https://github.com/OrcaSlicer/OrcaSlicer/blob/6a7763f08d1a175a464a00ce13f0b5a815662fc4/src/libslic3r/Print.hpp#L1080)).
They are internal, version-bound C++ interfaces. Orca builds `libslic3r` as a
**static** target ([CMakeLists.txt, line 605](https://github.com/OrcaSlicer/OrcaSlicer/blob/6a7763f08d1a175a464a00ce13f0b5a815662fc4/src/libslic3r/CMakeLists.txt#L605)).
An ordinary portable Orca executable is not a supplied engine SDK.

| Calibration | Common family | Additional native requirement |
| --- | --- | --- |
| Temperature standard tower | Cut/scale model, configuration, transient calibration mode | Native cut planes and nozzle scaling; layer-count interpolation of the commanded temperature, fixed 5°C step. |
| Flow Ratio YOLO | Asset plus per-object settings | Recommended means `is_linear=true`, `pass=1`, Archimedean Chords top surface. Preserve labels, flow modifiers, ten-layer geometry, special top-surface ordering, and speed overrides. |
| Pressure Advance Pattern | Native custom paths plus sliced handle geometry | `CalibPressureAdvancePattern` produces four layers of custom G-code. Preserve profile-derived speed/acceleration, writer/dialect state, handle placement, numbers, and per-plate merging. An ordinary PA tower is a different calibration. |
| Retraction tower | Cut model, configuration, transient calibration mode | Native software retract writer length varies by height. Firmware retraction is explicitly disabled. A firmware-command template is insufficient. |
| Max Volumetric Speed tower | Cut model, configuration, transient calibration mode | Native wall speed changes inside extrusion planning. Convert requested mm³/s using native `Flow::mm3_per_mm()` and retained filament flow; disable slowdown and set native width/height/spiral settings. Firmware feed-rate scaling is insufficient. |

Exact setup locations are [Plater.cpp](https://github.com/OrcaSlicer/OrcaSlicer/blob/6a7763f08d1a175a464a00ce13f0b5a815662fc4/src/slic3r/GUI/Plater.cpp):
Temperature 17311–17500, Flow 17136–17300, PA Pattern 16808–17050,
MVS 17604–17682, Retraction 17685–17745.
The decisive exporter logic is [GCode.cpp, lines 6602–6640](https://github.com/OrcaSlicer/OrcaSlicer/blob/6a7763f08d1a175a464a00ce13f0b5a815662fc4/src/libslic3r/GCode.cpp#L6602).
PA's reusable generator is [calib.hpp, lines 311–331](https://github.com/OrcaSlicer/OrcaSlicer/blob/6a7763f08d1a175a464a00ce13f0b5a815662fc4/src/libslic3r/calib.hpp#L311).

The existing Python `Print` binding exposes objects, model, config reads and
cancellation; it does not expose constructing a calibration or invoking these
four engine operations ([PluginHostSlicing.cpp, lines 345–368](https://github.com/OrcaSlicer/OrcaSlicer/blob/6a7763f08d1a175a464a00ce13f0b5a815662fc4/src/slic3r/plugin/host/PluginHostSlicing.cpp#L345)).
Native command dispatch opens a modal calibration dialog; it is not a supported
parameterized generation API. Product UI automation is not a fallback.

## Shared parameter semantics

The V1 shared contract is `docs/V1_CONTRACT.md`; the lead owns its validator.
These are native behavior, not a promise that every native numeric input is
supported by a V1 generator:

- Temperature defaults 230→190°C, fixed 5°C step, resize enabled. Native checks
  start ≤500, end ≥155, start ≥end+5. Dialog focus normalizes temperatures to
  multiples of five; parity inputs must preserve the normalized values.
- Flow `{pass:1}` fixes YOLO Recommended and the native default Archimedean
  Chords pattern. Classic Pass 1 and YOLO Perfectionist are separate choices.
- PA Pattern defaults 0→0.08 by 0.005 for direct drive, or 0→1 by 0.05 for
  Bowden. Native checks start ≥0, step ≥0.001 and end ≥start+step. The bounded
  V1 contract uses direct-drive defaults. Numbering is enabled; empty optional
  speed/acceleration lists select native profile-derived defaults, not zero.
- Retraction defaults 0→2 by 0.1 mm; native checks start ≥0, step >0 and
  end ≥start+step.
- MVS defaults 5→20 by 0.5 mm³/s; native checks start >0, step >0 and
  end ≥start+step.

See [calib_dlg.cpp](https://github.com/OrcaSlicer/OrcaSlicer/blob/6a7763f08d1a175a464a00ce13f0b5a815662fc4/src/slic3r/GUI/calib_dlg.cpp):
PA defaults/validation 289–383; Temperature 480–520 and 581–598;
MVS 695–720 and 753–766; Retraction 1070–1095 and 1130–1143;
Flow 1790–1830 and 1872–1883. V1 resource caps must be labeled as V1 bounds,
not invented upstream limits. Belt/multitool arrangements require separate
qualification; PA Pattern is explicitly blocked for belt printers by native Orca.

## Smallest credible grouped adapter

Use a separately owned C++ executable linked against the exact static native
target, with upstream sources unchanged. Keep one native request envelope,
profile snapshot decoder, asset/cut/transform layer, full-config construction,
`Print` pipeline and output manifest. Branch only preparation and transient
mode/custom-path setup among the three families. Do not call `Plater::calib_*`
as though they are pure helpers: they depend on wx application, tabs, selection,
plate manager and edited-preset state. Extract/reproduce their minimum setup in
the adapter, and compare its effects against independently prepared native UI
jobs. PA Pattern additionally needs the native custom-G-code insertion and
plate placement path; setting `Calib_PA_Pattern` alone does not create it.

Require the same mandatory parity harness as stock recipes. Native reuse does
not itself qualify profile flattening, object placement, bed type, custom hooks,
cutting, range boundaries, heater behavior, speed or retraction. Keep immutable
explicit job inputs; the lab demonstrated that project-only reslicing can lose
recipe edits through Orca preset reconciliation. The lab's Temperature proof
uses October 11 Linux runtime/public profiles and cannot qualify October 15
Windows, production profiles, or a different calibration.

## Build feasibility and real blockers

Read-only metadata inspected on October 18, 2026:

- The exact baseline [official Build all run 38659661741](https://github.com/OrcaSlicer/OrcaSlicer/actions/runs/38659661741)
  has application, profile-validator, PDB and system-cache artifacts. There is
  no native SDK, static engine archive or dependency bundle in its artifact set.
  The Linux x64 application artifact is ID `11939596177`, 216,769,632 bytes,
  digest `2e55b438d706109031dd75046e370ea11bc8988822c147b4d232385489237579`.
- The upstream dependency workflow builds a dependency archive, but its upload
  steps are commented out ([build_deps.yml, lines 151–179](https://github.com/OrcaSlicer/OrcaSlicer/blob/6a7763f08d1a175a464a00ce13f0b5a815662fc4/.github/workflows/build_deps.yml#L151)).
  Public release metadata likewise offers applications/debug symbols, not an SDK.
- Official Actions cache metadata includes Linux main dependency cache
  `9012570506`, key
  `linux-clang-cache-orcaslicer_deps-build-3b9f0c459d3ed62cb1ce08e1e8e8590173d2ef600946ee5ef7dd55e87d755142`,
  167,045,642 compressed bytes. Metadata availability is not a supported local
  cache download. Standard Actions restoration uses an authorized job context;
  no upstream workflow dispatch or token workaround was attempted.
- A reusable local builder exists: image ID
  `sha256:f67960f55aa1b7cfa8af41bd89943b13730b791ce55e1925bc575d5eef89f6d9`,
  CMake 3.22.1/Clang 14. It provides tools but no Orca development prefix.
  Missing host CMake is therefore not the blocker. No host packages were installed.
  An offline 2-CPU/2-GiB/60-second configure probe with GUI/CAD disabled reached
  the actual missing Boost ≥1.83 dependency. A separate configure of the exact
  upstream dependency project succeeded and generated its dependency graph;
  no downloads or compiles ran in that probe. Logs remain in XDG state under
  `helix-orca-calibration/v1-engine/`.
- The exact static target requires CGAL 6.2, Eigen 5.0.1, Boost 1.83, TBB,
  OpenCV, Assimp, OCCT, Draco and transitive dependencies; root configuration
  also includes other required packages even with GUI disabled. No existing
  compatible native dependency prefix or static build cache was found locally.
- The upstream warm-dependency Linux app build took 29m56s. This is not a
  measured cold-dependency or thin-adapter build estimate. Local host snapshot:
  16 CPUs, 22 GiB RAM (~19 GiB available), 352 GiB free disk. A bounded future
  build should isolate/cache dependencies, limit concurrent compilers and memory,
  retain timings/peak memory, and stop at its explicit watchdog. The cold build
  was allocated only after this source-size/resource audit. The lead subsequently
  allocated a capped 2-GiB exact URL/SHA download phase and, after the native
  matrix/stock slices release the heavy slot, a network-none dependency build
  with 6 CPUs/12 GiB RAM, ≤4 compilers per dependency, serial top-level
  dependencies and a 120-minute watchdog. Its disk preflight uses 16 GiB
  additional peak, 10 GiB reserve and 2 GiB reaction margin. These are execution
  limits, not measured build predictions. Shared managed-run ownership, lock,
  retained logs and exact owned-container teardown are required.

The isolated dependency prefix, headless static target and shared adapter now
build; runtime configuration and native-UI parity are the next gates. Missing
APIs in stock Python and transient native calibration state are verified
interface constraints; missing host tools were recoverable infrastructure.
Default capability responses remain unavailable without a real matching build
receipt, and a capability inventory alone does not prove usable generation.

## Reusable exact-source audit

`integration/v1_engine.py` records SHA-256 for eleven exact baseline files and
returns unavailable native capabilities unless an actual compatible build
receipt is configured. `audit-source --repository
/PATH/TO/ORCA` reads fixed git objects with replacement objects disabled; it never
changes a checkout or trusts the current branch. It rejects missing, altered or
unknown source inventory entries. Its report distinguishes source verification,
executable build and qualification. Neither a source report nor a caller-edited
capability object can enable generation.

The audit passed against the locally retained exact October 15 objects. Five
focused adversarial tests cover substituted/incomplete source, git failures,
fixed-commit reads, unknown dispatch and forged capability availability. Native
UI, Windows and print evidence remain absent from this engine investigation.

## Isolated native bootstrap progress

The approved download phase completed under shared managed run
`4145418419964f7b999f07ac575f0181`: 21 source archives, 497,005,093 bytes, every
archive matched the exact upstream SHA-256. `integration/v1-native-dependencies.json`
records the resolved Linux/CMake-3.22 choices; no archive is executed by the
downloader. Its managed manifest records exit 0, complete lifecycle and cleared
runtime. The report/log remain in that run's artifacts. Verified archives remain
in the V1 engine user cache, and may be reused offline.

`scripts/v1-engine-deps.py` enforces HTTPS, a cumulative 2 GiB archive/cache cap,
checksum verification before atomic promotion, retained failure reports and the
shared managed writer. Tests reject substituted and oversized archives.
`scripts/v1-engine-native.py` prepares the separately allocated offline build,
using an immutable existing builder, read-only source/app/archive mounts, owned
build/evidence mounts, exact container teardown and capped per-stage first/tail
logs. CPU, memory, PID, time and disk-headroom bounds are explicit. The native
static library was not yet built at that initial checkpoint; source downloads
or dependency configure never enabled generation.

Upstream GMP/MPFR invoke unbounded `make -j`, and OpenSSL/Python derive jobs from
`ProcessorCount`; setting only `CMAKE_BUILD_PARALLEL_LEVEL=4` would misstate the
resource bound. The app-owned `v1-native-build-tools.py` clamps explicit make job
counts and gates compiler entry through four shared locks inside the owned
container build directory. Upstream source remains unchanged. Dependency and
static-engine compilation wait until native captures and stock slices explicitly
release their scheduled shared resource slot.

## First native dependency build checkpoint

The first managed compile attempt passed dependency configure and installed
Boost, Cereal, Qhull, GLFW and TBB. GMP configure then rejected the reused
builder because it has no `m4`; an additional `file` absence was a warning.
Run `27997b867ef64a8fbde693de4ead029e` retained the exact failure and all cached
progress, removed its owned container, and recorded `runtime_clear: true`.
Peak memory was 1,816,973,312 bytes; peak PID count 23; no OOM occurred. This is
real native compilation progress, not a built or qualified generator.

The minimal repair is an owned-prefix GNU m4 bootstrap, without host installs
or a new image. Its source URL and SHA-256 are locked separately from Orca's
21 native dependencies, using the [GNU release announcement's published checksum](https://lists.gnu.org/archive/html/info-gnu/2025-05/msg00001.html).
All dependency archive headers total 1,527,267,848 expanded bytes (1.422 GiB),
providing a measured source-expansion component of the 16 GiB peak bound.

Separate experimental C++ adapter sources now live in
`integration/v1-native-engine/`. They reproduce three native tower setup
paths and the PA Pattern generator/arrangement/custom-G-code path using actual `Model`/`Cut`/`Flow`/`Print` interfaces and an app-owned
CMake target injection. They were uncompiled at this initial checkpoint; actual
build and runtime results are recorded below. Product Ready always requires
independent native parity and integration.

GMP subsequently built successfully. The next MPFR step invokes
`autoreconf -f -i` in the unchanged upstream dependency recipe; that tool was
also absent from the reused builder. Run `283d6acab97c430b9717e8eab14cf76c`
retained this exact environment gate and cleared its runtime. The owned-prefix
bootstrap now also locks Autoconf, Automake and Libtool to checksums published
in their GNU release announcements. This is standard build tooling inside the
owned cache; there is no host installation, new image or upstream source edit.

The next retained run `8cc9f4c55cd24f999c65bf2f9dd7fddb` built the real
Autotools prerequisites and reached MPFR compilation. MPFR's documentation
regeneration requires `makeinfo`, another declared Orca Linux prerequisite.
The exact owned container was removed, `runtime_clear` is true, and no OOM
occurred. GNU Texinfo 7.1.1 is now source/checksum locked using the primary
Debian source-control file's SHA-256 for its unmodified upstream tarball; the
archive still comes directly from GNU. No documentation generator is stubbed.

PA Pattern now has a downstream source implementation of Plater.cpp
16808–17050, using `CalibPressureAdvance::find_optimal_PA_speed`,
`CalibPressureAdvancePattern`, native arrangement and the actual per-plate
`generate_custom_gcodes` result. It retains the default speed/acceleration
selection and printed numbers. It requires Klipper flavor because V1's
retained context lacks the native vendor object needed to prove Bambu writer
selection for other firmware. The one pattern is arranged before generation;
its anchor must not subsequently be recentered independently of custom paths.
Its actual compilation now passes; runtime behavior and parity remain gates.

The retained complete Windows R4 context was inventoried against all active
`FullPrintConfig` class declarations and literal native definitions. The only
missing current full-config keys are the deliberately redacted
`bed_custom_model` and `bed_custom_texture` (PrintConfig.cpp 1037/1043). These
are display asset paths; the adapter excludes them explicitly and reports
the exclusion. All executable slicing values remain mandatory. Obsolete static
class members have no active definition and do not become required values.
Native `plugins`, `post_process` and `slicing_pipeline_plugin` must all be empty.
No preset source file is read to fill a missing effective value.

The exact root CMake configuration also requires bundled CPython 3.12.13 and
OpenGL/GLFW even with `SLIC3R_GUI=OFF`; the stock dependency list therefore
retains those upstream targets rather than inventing unsupported bypasses.
The source-pinned optional uv download may report unavailable inside the
network-none container; no substitute executable is supplied. Each build now
retains `native-inputs.json` with the eleven-file source audit, exact owned
adapter/build-wrapper/lock hashes, immutable builder identity and execution
bounds before any compile stage runs.

## Guarded product adapter interface

`integration.v1_engine.generate(request, snapshot, output_dir, config)` now uses
the same prepared-job contract and mandatory `v1_parity` evaluator as the stock
route. The lead may dispatch `pressure_advance_pattern`, `retraction` and
`max_volumetric_speed` here, and optionally native Temperature. Flow YOLO remains
the stock route. The Linux native executable is built; default capabilities
remain unavailable without its exact compatible receipt. Successful process
exit alone never makes a job Ready.

Trusted runtime configuration supplies:

```python
{
  "build_receipt": {"path": ".../native-build.json", "sha256": "..."},
  "build_inputs": {"path": ".../native-inputs.json", "sha256": "..."},
  "native_executable": {"path": ".../helix_orca_native", "sha256": "..."},
  "native_resources": ".../exact-source/resources",
  "native_reference": {
    "manifest": {"path": ".../native-reference.json", "sha256": "..."},
    "gcode": {"path": ".../independent-native.gcode", "sha256": "..."}
  }
}
```

These fields never come from request/context JSON. Optional `runner(argv,
output_directory)` is an in-process trusted runtime adapter; otherwise the
configured executable runs directly with a bounded deadline and job-local XDG
directories. `timeout_seconds` is capped at 300; `now` is only a deterministic
clock injection. No Codex-operated worker is necessary for ordinary dispatch.

The build must actually compile the adapter, execute its `--capabilities`
command, and retain the native required effective-key inventory in its receipt.
The Python adapter validates source/build receipt and executable hashes, current
owned C++/CMake/build-wrapper hashes, immutable builder identity, native resource
hashes and every required effective key before execution. It preserves the
original complete snapshot without saved/edited fallback or stock temperature
hook insertion. It rejects active slicing plugins/post-processing and stale
result identities. Every actual artifact gets a shared parity report: absent
native reference stays unqualified; a retained independent native reference is
evaluated for exact inputs, executable commands and calibration invariants.

Eleven adversarial transport tests use conspicuously synthetic build receipts,
resources, executable runners and UI evidence to test the checker only. They
prove substituted executable/source/assets, incomplete context, active hooks
and forged result qualification cannot bypass the gate. Their synthetic
checker success is not a native build, native UI capture or V1 qualification.

## Actual offline dependency checkpoint

Managed run `6eac3c294ff24ca8a1323196d4123f9b` successfully built the first
21 locked native dependency targets, including OCCT (1,224.753 seconds), OpenCV
(113.008 seconds), Assimp (33.032 seconds) and CPython 3.12.13. Root configuration
then failed at the exact source's unconditional OpenVDB requirement
(`CMakeLists.txt:1034–1041`): OpenVDB and IlmBase were missing. This is a real
failed build checkpoint, not a built or available generator. Its retained
`engine-configure.log` and stage JSON files record the failure. Cgroup peak was
3,341,504,512 bytes and 31 PIDs, with zero OOM events. The exact container was
removed and lifecycle verification records `runtime_clear=true`.

The dependency lock now also includes the exact upstream `dep_Blosc`,
`dep_OpenEXR` and `dep_OpenVDB` URLs and SHA-256 values from `deps/Blosc/Blosc.cmake`,
`deps/OpenEXR/OpenEXR.cmake` and `deps/OpenVDB/OpenVDB.cmake`. OpenVDB depends on
Blosc, OpenEXR, TBB and Boost. These targets will use the retained owned prefix
under the same bounded network-none build; no host installation or upstream
patch is implied. Downloads and compilation remain serialized with native UI
capture through the shared lifecycle lock.

The registered build target is explicitly Linux x86_64 ELF64 little-endian.
Its receipt and actual capability response must agree on target, the host must
match, and the executable must contain an actual ELF64 `EM_X86_64` header.
Copying the Linux binary or receipt to Windows cannot enable generation.
A compatible Windows build remains unavailable: the read-only target probe
found no CMake, Ninja, MSVC, MSBuild or Visual Studio installer toolchain.
The C++ source also refuses an unregistered platform at compile time.

A persistent `tbb::global_control` limits native generation to two workers.
Export retains `native-processing.json` and rejects native processor errors or
warnings, including executable build-volume failures; successful slicing alone
cannot bypass Orca's post-export checks. Missing, malformed or substituted local
reference material retains an unqualified parity report for the generated
artifact. Remote qualification flags are never accepted.

Incremental run `56f3cf91fab64d53a02dc9ed114dc40d` built Blosc, OpenEXR and
OpenVDB successfully and reused the earlier 21 targets. Root configuration now
finds OpenVDB, then stops because `src/CMakeLists.txt:320` unconditionally calls
the Linux shared-library packaging helper, whose `CMakeLists.txt:1151` copy
requires the bundled FFmpeg shared libraries even with GUI disabled. The lock
therefore also retains the exact upstream `deps/FFMPEG/FFMPEG.cmake` n7.0.3
source URL and SHA-256. No placeholder shared libraries or configure bypass
are used. The failed configure run retained its logs, peaked at 1,257,209,856
bytes/31 PIDs with no OOM, and removed its exact container with runtime clear.

The exact FFmpeg configure additionally needs executable compiler probes and
defaults to the driver name `gcc` instead of honoring `CC`. The owned wrapper
keeps `/tmp` noexec, uses `/build/configure-tmp` for probes, and supplies local
`gcc`/`g++` driver aliases to the real pinned Clang-backed compilers through the
same four-slot gate. FFmpeg still sees the actual compiler version and selects
Clang semantics. Its real NASM assembler is bootstrapped into the owned prefix
from the [official 2.16.03 source release](https://www.nasm.us/pub/nasm/releasebuilds/2.16.03/),
with SHA-256 independently retained by the
[FreeBSD ports update](https://cgit.freebsd.org/ports/commit/?id=264dd71e3875a9c9dfdc3c25231cc0829cb8c8b2).
No compiler or assembler is installed on the host, and no assembly is replaced
with placeholders or disabled to manufacture a passing native build.

## Actual adapter build and shared runtime gate

Run `17384310035646fdb83974208145503b` built the real static `libslic3r` target
in 844.965 seconds and compiled the adapter on its first pass. Linking required
NanoSVG's header implementations, exactly as the upstream headless profile
validator does (`src/dev-utils/OrcaSlicer_profile_validator.cpp:1–9`), rather
than the GUI-owned implementation. Run `ce3fc31f304342d8b18c50956ae31a44` then
completed the native build and actual `--capabilities` command: executable
71,627,768 bytes, four native routes, 721 required effective keys, Linux x86_64
ELF64 and two-worker scheduler bound. Run `eba06ccacdf44c25b604ef003c9d6d65`
subsequently built optional bounded diagnostics. Both successful build runs
record runtime clear; no Windows execution capability is inferred.

The grouped smoke tool `scripts/v1-engine-smoke.py` uses one private, offline,
2-CPU/4-GiB/128-PID managed container per calibration, exact teardown,
immutable retained context, and the same guarded product adapter/parity path.
Its first four actual native jobs all exited 139 before generating G-code:
`67342532791f44c58ee67c59dbed8d84` (Temperature),
`e133c59aba8b4551a65de869d4515fba` (PA),
`a28fd2e999834d9a8d695bac5a5dfa3a` (Retraction), and
`27ce6e502cf04429b1518b4ee59c188f` (MVS). All failures are retained with runtime
clear and qualification false. No process exit or fixture is presented as a
working calibration. Real native-UI Windows references remain separate evidence.

Diagnostic run `03078f9ecdd34c8bbd7fb4a7284fa0ce` localized the shared crash
to strict parsing of `extruder_type`; it logs only phase/key names, never
configuration values. `full_print_config()` (`PrintConfig.cpp:10183`) clones
static options (`Config.cpp:1689`), including enum-list defaults with null
lookup maps. `ConfigOptionEnumsGeneric::deserialize` dereferences that map
(`Config.hpp:2249`). The genuine dynamic option factory explicitly attaches
the correct native map (`Config.cpp:322–338`, `1721–1741`). The downstream repair
uses full defaults only to inventory mandatory keys and fills a fresh dynamic
configuration from every retained serialized effective value. It changes no
upstream source or profile value, and introduces no missing-value fallback.
Run `90612e0187fd46dca9ea5eb5d7f51c06` built that repair. Actual retained-context
job `dca51e5594b44f1fbfcf7a9cdee9b356` passed every effective key and native
Temperature model preparation, then waited in native code after `model-ready`
(two futex-waiting threads, no G-code). The exact owned grouped driver received
a validated pidfd/SIGINT; its existing lifecycle handler stopped the foreground
and exact container, preserving all evidence with runtime clear. Remaining
cases were not launched to repeat this shared gate. The smoke now stops after
its first failed generation, and more precise bed/volume/Print/apply/process
phase diagnostics are prepared. No calibration artifact or parity success is
claimed from this intermediate progress.

The development smoke watchdog now defaults to 60 seconds and accepts an
explicit bounded `--timeout-seconds 10..300`; production generator deadlines
are unchanged. The next shared-wait check uses one PA case with at most
45 seconds. Diagnostic jobs explicitly enable native phase/key-name logging
and an optional `SIGUSR1` stack dump for their exact owned process; no debugger
attachment, elevated container capability or network endpoint is required.
Ordinary native execution installs no diagnostic signal handler.

The final diagnostic build `3aa200694be341e5b5af4d4ffa02755f` passed. A single
45-second PA job `b85b5160dd8b4fb6813c76beef6d899b` passed native apply and
validation, then waited at `Print::process`. One signal to its exact registered
container retained a stack in `diagnostic-stack.log`; the matching executable
symbolizes it as `name_tbb_thread_pool_threads_set_locale()` (`Thread.cpp:225–286`),
called at `Print.cpp:3146`. The native barrier counts
`tbb::this_task_arena::max_concurrency()` while `global_control(2)` only limits
worker availability. A larger host arena therefore waits for unavailable
workers. The owned adapter now executes process/export in `tbb::task_arena(2)`
while retaining the persistent global two-worker cap. This changes no upstream
source or calibration behavior; its targeted runtime check is pending.
The failed job reached its 45-second watchdog, retained all inputs/diagnostics,
and cleared its exact process/container with runtime clear.

If native execution returns a failed status after leaving G-code (including a
post-export processor rejection), the transport still retains a mandatory
unqualified harness disposition for those exact bytes and never creates a
Prepared job. A successful exit seeds the same false disposition before its
result identity/processor validation, so a malformed or warning-bearing result
cannot leave an undisposed candidate. An ineligible artifact instead retains
an explicit parity blocker; it cannot qualify.
