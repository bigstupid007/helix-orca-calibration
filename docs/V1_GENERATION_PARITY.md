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

The first checkpoint's machine-limit mismatch is now traced: its experimental
snapshot builder found option definitions by regular expression over literal
`PrintConfig::add` calls. Orca registers per-axis acceleration/speed/jerk options
in a C++ loop, so the builder silently excluded those existing exported values.
Stock defaults then supplied M201/M203. This is a reproducible fixture capture
bug, not evidence of native vector deserialization failure or a reason to ignore
machine limits. Follow-up snapshot capture must preserve all exported native
options, including dynamically registered axes; original checkpoint artifacts
remain preserved. Actual host snapshots use Orca's resolved keys directly.

`prepare_inputs(request,snapshot,output_dir,config)` exposes the common stock
staging boundary to the native-engine worker: it returns validated request and
snapshot, the job/model paths, profile maps, merged native serialized effective
configuration and exact comparison inputs. It does not invoke slicing. The
bundle also retains `native-effective.json`. A native Temperature adapter using
`Calib_Params` must retain the original effective layer hook rather than append
both its native ramp and the stock recipe ramp. Other families still need their
own source-verified native preparation; this helper does not claim to prepare
Retraction, MVS or PA Pattern.

To register a newly captured genuine native reference, use:

```sh
python3 scripts/v1-generation.py native-reference \
  --native-gcode /absolute/native.gcode \
  --native-context /absolute/pre-calibration-native-context.json \
  --calibration temperature --parameters /absolute/parameters.json \
  --source-commit 6a7763f08d1a175a464a00ce13f0b5a815662fc4 \
  --evidence /absolute/native-inputs-and-dialog-capture.png \
  --evidence /absolute/native-slice-export-action-record.json \
  --output /absolute/new-native-reference.json
```

The context must be independently captured from that native run before preparing
its calibration; substituting a candidate's context does not establish this
provenance. Registration rehashes all evidence, checks exact runtime/source,
validates native inputs and refuses to overwrite an existing manifest. It does
not declare qualification. The old lab has genuine native G-code, screenshots
and a provenance-bound original resolved-profile export, but it did not capture
the complete pre-calibration V1 saved/edited/effective context object. Its native
files therefore remain valuable independent behavioral evidence; registration
must not manufacture the missing exact V1 snapshot.

Parity reports now explicitly measure complete heater streams, machine-limit
streams, M73 estimate streams, motion/extrusion streams, actual model extrusion,
printed XY bounds and model-move counts separately. These observations explain
which differences remain. They never waive any executable difference. Native
The reviewed Klipper variant compares the exact accepted macro ABI below;
macro internals remain explicitly unobserved. An unsupported macro ABI still
blocks, and identical invocation text does not prove physical macro execution.

Effective-only/project options absent from all three preset-local key maps are
also explicitly carried in the job's machine DynamicPrintConfig. The stock CLI
applies those serialized keys through its native `update_full_config` path;
they must not disappear merely because a preset-local enumeration lacks them.
Regression coverage preserves dynamically registered per-axis machine limits.
The actual host's `bundle.full_config_keys()` and `full_config_value(key)` are
the supported capture route. Exact October 15 source
`PluginHostPresets.cpp:202` binds those to `bundle.full_config()` and
`PluginBindingUtils.hpp:79` returns `opt_serialize(key)` (or unavailable).
`PresetBundle::full_config` dispatches `full_fff_config` at line 5489; that
function explicitly applies `project_config`, including `curr_bed_type`.
No app-settings fallback or guessed bed default is required or permitted.


## Bounded Klipper Temperature invocation semantics

The lead explicitly approved an engineering refinement of the initial visible
M109/shutdown rule. Exact October 15 `GCodeWriter::set_temperature` emits M104 S
for both Klipper and Marlin. The retained accepted Issue12 Windows qualification
and completed Temperature milestone document the target macro ABI:
`PRINT_START BED_TEMP=… EXTRUDER_TEMP=…`, then `PRINT_END` after deposition.
This is a source/evidence-bound command-comparison policy, not new hardware
qualification or permission to execute either macro.

For Klipper Temperature, the immutable effective start hook must contain exactly
one `PRINT_START BED_TEMP=[bed_temperature_initial_layer_single]
EXTRUDER_TEMP=[nozzle_temperature_initial_layer]` invocation and the end hook
exactly one `PRINT_END`. The actual G-code must invoke them once, on the correct
sides of all model deposition; arguments must equal the original effective
selected-plate initial bed temperature and requested starting nozzle temperature.
All plate temperature option names come from native PrintConfig. Subsequent bed
commands must match the original normal/initial plate values. The explicit
coordinate and extrusion modes must match immutable effective inputs. Every
per-layer nozzle command and actual deposition temperature must match its
calibration section; a later corrected command cannot excuse an intervening
wrong target. The complete executable stream, including every start/end command,
macro argument, limit and mode command, still has to match the independently
prepared native reference exactly.

Reports bind effective start/end hook and declared machine-limit digests and
record the exact start/end invocations, mode and target values. They explicitly
state `macro_internals: unobserved` and `physical_readiness: false`. A corrected
in-memory macro template used by the earlier accepted physical preparation is
not silently substituted for a different original profile hook. Unsupported
original ABI, missing effective information, stale inputs or actual native
mismatch still block. Real printer configuration and accepted behavior remain
unchanged. Independent candidate review must assess this comparison policy.

Synthetic tests verify exact accepted invocations, wrong macro arguments,
unsupported original ABI, duplicate/misplaced end, wrong extrusion mode, wrong
bed commands even when both files share them, and M73-only differences. M73
estimate differences are measured separately and still do not pass the current
strict executable gate. These tests do not qualify any actual Windows or
physical macro execution.

The first actual October15 Windows context exposed source-intentional merged
metadata erasures: `inherits`, `compatible_printers`,
`compatible_printers_condition`, `compatible_prints`,
`compatible_prints_condition` and `different_settings_to_system` are explicitly
removed by `PresetBundle::full_fff_config`. Job copies omit only these verified
composition-only fields rather than substituting their saved/edited values for
missing effective values. Other missing settings still block. In particular,
legacy public-diagnostic redaction treated `post_process` as a personal path;
the new private V1 snapshot must retain that serialized value to distinguish
empty post-processing from scripts. The incomplete earlier context/reference
must remain history rather than having unknown fields retrofitted.

A second lead-approved **command comparison only** variant preserves the exact
immutable original native `PRINT_START EXTRUDER=… BED=…` hook when both the
serialized original hook and the exported file contain independently matching
explicit M190/M109 waits before PRINT_START. It requires the original exact
placeholder signature, the requested nozzle target and selected-plate bed value,
all subsequent section checks, the correct original modes and one PRINT_END
after deposition. No replacement with the accepted target ABI occurs.
`native-original-visible-waits-v1` reports `hardware_abi_qualified: false`,
`macro_internals: unobserved` and `physical_readiness: false`. This can compare
the unchanged original native file's commanded behavior; it cannot certify that
the printer's actual macro accepts those original arguments or authorize a print.
The earlier accepted-ABI variant also retains `hardware_abi_qualified: false`
for this new candidate: matching a retained signature does not observe execution.
Unsupported original hooks, missing waits or wrong arguments still block.
