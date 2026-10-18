# V1 grouped native-engine reuse

Build Program #14 owns this investigation. Baseline:
`6a7763f08d1a175a464a00ce13f0b5a815662fc4`, the accepted October 15 Orca nightly.
This is source and build-feasibility evidence. No native adapter has been built,
no new native reference job has been exported, and none of the five V1
calibrations is qualified by this document. The accepted physical Temperature
milestone and lab remain unchanged.

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
  retain timings/peak memory, and stop at its explicit watchdog. No cold build
  has been started under an invented resource estimate. The lead subsequently
  allocated a capped 2-GiB exact URL/SHA download phase and, after the native
  matrix/stock slices release the heavy slot, a network-none dependency build
  with 6 CPUs/12 GiB RAM, ≤4 compilers per dependency, serial top-level
  dependencies and a 120-minute watchdog. Its disk preflight uses 16 GiB
  additional peak, 10 GiB reserve and 2 GiB reaction margin. These are execution
  limits, not measured build predictions. Shared managed-run ownership, lock,
  retained logs and exact owned-container teardown are required.

The next native implementation dependency is a **compatible isolated dependency
prefix and successful headless static-target build**, followed by the shared
adapter and native-UI parity corpus. Missing APIs in stock Python and transient
native calibration state are verified interface blockers; missing host tools
are recoverable infrastructure. Current capability responses remain unavailable.
A capability inventory is progress, not a usable generator.

## Reusable exact-source audit

`integration/v1_engine.py` records SHA-256 for eleven exact baseline files and
returns explicit unavailable native capabilities. `audit-source --repository
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
static library is not yet built; no available-generator claim follows from a
successful source download or dependency configure.

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
CMake target injection. They remain explicitly uncompiled/unqualified. The next managed build attempts that
actual executable only after the dependency/static-engine gates pass. It must
not be advertised to the product before native parity and integration.

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
This remains uncompiled source until the native target build passes.
