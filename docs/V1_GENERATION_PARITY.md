# V1 generation and mandatory native G-code parity

Build Program #14 approves these recipes and the grouped engine investigation.
This document records a working foundation, not a V1 qualification or approval
for a new physical test. Completed Temperature implementation, physical proof,
normal profiles and original lab evidence remain unchanged.

The preferred Orca baseline is October 15 nightly
`6a7763f08d1a175a464a00ce13f0b5a815662fc4`. Read-only inspection used `git show`
against that exact object in the local source cache; the cache checkout itself
is Alpha and must not be mistaken for the preferred source. The independent
`orca-calibration-lab` pins the older October 11
`210bc927bc6fb3d3bf390fdf72e4a2767b5de4b3`. Its Linux findings cannot qualify
October 15 Windows output.

| Calibration | Verified native mechanism | Current route and qualification boundary |
| --- | --- | --- |
| Temperature standard tower | `Plater::calib_temp`, native DRC cut/scale; transient `Print::set_calib_params`; native layer-count temperature interpolation | Job-local model + explicit machine/process/filament serialized inputs + explicit bed + stock `--slice`. Recipe attempt supports hash-bound prepared geometry for exact scaled 0.4/0.6 mm single-tool Marlin/Klipper cases. Exact independent native parity remains mandatory. |
| Flow Ratio YOLO Recommended | `calib_flowrate(true,1,ArchimedeanChords)`, `Orca-LinearFlow.3mf`, native eleven labeled objects, absolute additive flow increments and special top-infill order | Job-local copy adds native per-object settings and ratios, stock Orca slices it. Initial recipe envelope is 0.4 mm nozzle / 0.2 mm first layer. Native UI output comparison remains pending. |
| Pressure Advance Pattern | `_calib_pa_pattern`, native `CalibPressureAdvancePattern::generate_custom_gcodes`, handles/arrangement and writer state | Stock CLI has no calibration-state input. Explicit native-generator blocker; a generic STL or PA command schedule cannot reproduce the custom pattern paths/digits. |
| Retraction tower | `calib_retraction`; exporter changes software writer `retraction_length` per height | Explicit native-writer blocker. Firmware retraction commands cannot substitute for generated software retract/unretract moves. |
| Max Volumetric Speed tower | `calib_max_vol_speed`, `Flow::mm3_per_mm`, spiral mode; exporter changes internal `outer_wall_speed` per height | Explicit native-planner blocker. Firmware feed scaling does not reproduce internal extrusion planning and limits. |

The grouped source paths are `src/slic3r/GUI/Plater.cpp`,
`src/libslic3r/GCode.cpp`, `src/libslic3r/calib.cpp`,
`src/slic3r/Utils/CalibUtils.cpp`, and `src/OrcaSlicer.cpp`. The stock CLI at
both pins exposes no `Calib_Params` or calibration selector. No supported
Python generator API is assumed. Native engine integration is researched in
parallel and must preserve upstream reference files.

## Job contract and invocation

`integration.v1_generation.generate(request, snapshot, output_dir, config)`
implements the shared [V1 contract](V1_CONTRACT.md). The snapshot contains native
serialized strings, with saved identity, edited identity and merged effective
values kept separate. Each explicitly resolved preset option uses its effective
value; missing effective information blocks instead of falling back. Native
`ConfigBase::load_from_json` accepts these strings and deserializes vector
options itself. Identity metadata is explicit; original presets are never saved.
Credentials are omitted from the job copies. Real external post-processing is
rejected. Job directories must be new/empty.

The trusted local generator configuration contains:

- `executable`, `executable_sha256`, `source_commit`, `runtime` (exact version/build);
- Temperature: `temperature_model` with `path`, `sha256`, `source_commit`,
  `nozzle_mm`, and exact `parameters`. This is an explicitly prepared native-derived
  asset, not an implicit normal-profile read or a claim that arbitrary geometry
  matches. Missing or mismatched geometry blocks. Alternatively configure
  `temperature_base_model` (`path`, `sha256`, `source_commit`,
  `decoded_from_sha256`) for the full native decoded tower. Its source DRC SHA
  must be `47edfab84d48f3b762cf536fba532a0e4564653d80e20d4f936ddd5c4541796b`.
  Existing optional `trimesh` / `mapbox-earcut` dependencies cut/cap/scale the
  requested standard range, retaining geometry provenance and explicit
  triangulation uncertainty. Missing geometry dependencies block;
- Flow: `flow_asset` with `path`, `sha256`, `source_commit`, pointing to the exact
  native `Orca-LinearFlow.3mf`;
- optional `native_reference`: `manifest` and `gcode`, each `path`/`sha256`;
- optional `timeout_seconds` (capped at 300). A trusted in-process
  `runner(argv, output_dir) -> returncode` may provide OS/container confinement;
  it is never request data or accepted as a wire command.

The stock argv uses `--datadir` beneath the job directory,
`--load-settings machine.json;process.json`, `--load-filaments filament.json`,
`--curr-bed-type` from the effective snapshot, `--arrange 1 --orient 0 --strict`,
`--export-settings`, and `--slice 0 model`. No default bed is allowed: the lab
found a real 35°C versus 60°C difference when this input was omitted. Child XDG
and WebView2 paths are job-local for direct execution. Confinement/resource
limits belong to the local runner; no printer route or network API exists here.
The generator executes outside Orca's audited Python plugin.

The job retains input and profile copies, executable/source/command provenance,
output G-code, slice log, effective settings, parity report and prepared object.
`GenerationBlocked.code` and `.reason` identify the failed gate. Zero exit and
an artifact establish generation only. They never establish Ready or permit
Confirm/Start. Linux `result.json` warnings/failures reject; other platforms
still require actual platform qualification.

## Native reference and parity policy

The reference must be independently prepared through Orca's native Calibration
UI with matching profiles, edited/effective inputs, parameters, nozzle, bed and
exact engine/runtime. Importing the generated candidate or recipe is forbidden.
UI automation is evidence tooling only. Native provenance schema is
`helix-orca-v1-native-reference/v1`:

- `method: native_orca_ui`, `imported_candidate: false`;
- `inputs_sha256`, `source_commit`, exact `runtime`;
- `artifact` (`name`, `size`, `sha256`) for independently exported G-code;
- `evidence`: retained local paths plus exact artifact records for the native
  input/dialog/slice/export capture and action provenance.

`generation_inputs(request,snapshot,source_commit)` supplies the canonical
comparison input. It excludes request ID and timestamps but binds the context
and full saved/edited/effective profile maps, calibration, parameters, nozzle,
source and runtime. Native references require deliberate provenance review;
the manifest's text does not cryptographically prove a human UI action.

`integration.v1_parity.evaluate` rehashes native evidence and compares executable
streams after removing **only** comments and blank lines. It does not drop M73,
E values, final wipes, heating or motion. It separately tracks actual positive-E
model deposition, current heater state, real Z, extrusion mode and native layer
bands. Temperature invariants reject late/early heating, wrong actual Z, missing
sections, premature or missing shutdown and missing initial wait. YOLO checks
all eleven native patch labels and top surfaces. Other calibration invariant
adapters remain blocked rather than accepting generic valid G-code. Persistent
or external executable commands reject.

Any executable difference blocks qualification under the current conservative
`exact-executable-v1` policy; the report retains both executable digests and the
first twenty command differences. This is intentionally stricter than the lab's
bounded Temperature behavioral comparison. The lab found small mesh/toolpath,
adaptive-width and extrusion differences, so its passing temperature/placement
checks do **not** automatically pass this V1 qualification. A broader behavioral
policy would need an independently reviewed explanation of material differences
and calibration-specific acceptance bounds, not thresholds chosen to pass.

`verify_report(report,prepared)` checks the exact prepared artifact/input/engine
bindings, then reruns parity from retained independent files and requires the
same report. Rehashing a forged `qualified: true` does not confer qualification.
The coordinator independently rehashes the deliverable before publishing it.
There is no manual bypass or self-reference route.

## Verification and remaining limitations

Focused dependency-free tests use explicitly synthetic fixture artifacts to
exercise the checker, not to claim native acceptance. They cover context and
asset tampering, unavailable effective bed, original profile preservation,
post-process rejection, slicing warnings, explicit grouped blockers, native
provenance tampering, changed motion/bed, actual-Z and late-heater failures,
self-reference, changed evidence, report revalidation and forged flags.

Actual Windows native reference preparation/parity for all five V1 calibrations,
production edited-profile fidelity, wider nozzle/dialect support, a native-engine
adapter for the three internal-state calibrations, full distribution packaging
and real print quality remain unqualified. No generated file is authorized for a
new physical test.

Managed offline checkpoint `ef219968edda495eb456adfd6a1cf80a` executed both
recipes against the real pinned Linux `210bc927` stock binary, with Docker
network none, 2 CPUs, 4 GiB, read-only lab/runtime mounts and new XDG artifacts.
Both strict slices exited zero with empty warnings. Teardown verified
`runtime_clear: true` with no errors; native UI work then resumed the shared slot.
Temperature 230→220°C / 0.4 mm produced 956,109 bytes, SHA-256
`9fc87ecf425f6b6ae8e943000f4fd691f5888666674f4bc47aaab39c8958ec03`;
actual deposition has all 150 layers and 230/225/220°C sections. YOLO produced
2,848,812 bytes, SHA-256
`d35b6acdc51e78942962ad001b12edecdf98e31e1b166c68ef8633a85f06b369`;
actual deposition includes all eleven labeled patches across ten layers.
These are generation checkpoints, not exact-input native qualification.

The retained genuine lab native Temperature export was inspected without
modification. The new V1 public-profile snapshot has not been established as
matching that GUI run's complete original inputs; the executable comparison
also finds 32,586 differing command positions, starting with M73 estimates and
M201/M203 machine limits. Both files pass the bounded temperature/deposition
checks, but those checks do not erase input or executable differences. The
exploratory report explicitly keeps `qualified: false`. No matching native
YOLO export exists yet. Neither prepared artifact is Ready.

Logs, input snapshots, generated profiles, exact invocation/container commands,
G-code, reports and the checkpoint source are retained beneath
`~/.local/state/100day-dev/runs/ef219968edda495eb456adfd6a1cf80a/artifacts/`.
The earlier rejected size-bound attempt remains separately preserved as
`141c9c965b0345bbaa358c4834bcddad`. The lab and its references were read-only
throughout. No screenshot evidence was promoted from this generator checkpoint.
