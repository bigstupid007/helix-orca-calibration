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
| Flow Ratio YOLO Recommended | `calib_flowrate(true,1,ArchimedeanChords)`, `Orca-LinearFlow.3mf`, native eleven labeled objects, absolute additive flow increments and special top-infill order | Job-local copy adds native per-object settings and ratios, stock Orca slices it. Initial recipe envelope is 0.4 mm nozzle / 0.2 mm first layer. Actual matching Windows native/CLI comparison passes YOLO invariants but fails strict executable parity; retained measurements below. |
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
all eleven native patch labels and top surfaces. Source-backed October 15
Retraction, MVS and PA Pattern invariant adapters are implemented as detailed
below; implementing an invariant does not establish generator availability or
an independently passing native comparison. Persistent or external executable
commands reject.

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

All five genuine October 15 Windows native references now pass their calibration
invariants; candidate/native parity remains unqualified for every generator.
Production edited-profile fidelity, wider nozzle/dialect support, a native-engine
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
exploratory report explicitly keeps `qualified: false`. That October 11 lab
checkpoint had no matching native YOLO export. The later October 15 Windows
YOLO reference/comparison below exists and fails strict parity. Neither prepared
artifact is Ready.

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


## Bounded Klipper invocation semantics

The lead explicitly approved an engineering refinement of the initial visible
M109/shutdown rule. Exact October 15 `GCodeWriter::set_temperature` emits M104 S
for both Klipper and Marlin. The retained accepted Issue12 Windows qualification
and completed Temperature milestone document the target macro ABI:
`PRINT_START BED_TEMP=… EXTRUDER_TEMP=…`, then `PRINT_END` after deposition.
This is a source/evidence-bound command-comparison policy, not new hardware
qualification or permission to execute either macro.

For the accepted-ABI Klipper variant, the immutable effective start
hook must contain exactly one
`PRINT_START BED_TEMP=[bed_temperature_initial_layer_single] EXTRUDER_TEMP=[nozzle_temperature_initial_layer]`
invocation and the end hook exactly one `PRINT_END`. The separate original-ABI
variant with mandatory visible waits is specified below. The actual G-code must invoke them once, on the correct
sides of all model deposition; arguments must equal the original effective
selected-plate initial bed temperature and initial nozzle target. Temperature
uses the requested starting calibration temperature; the other four routes use
the immutable effective `nozzle_temperature_initial_layer`, without a fallback.
All plate temperature option names come from native PrintConfig. Subsequent bed
commands must match the original normal/initial plate values. The explicit
coordinate and extrusion modes must match immutable effective inputs. Every
per-layer nozzle command and actual deposition temperature must match its
calibration section; a later corrected command cannot excuse an intervening
wrong target. The other routes check visible nozzle commands against effective
initial/normal targets; native normal-temperature zero retains the initial
target. Coordinate/extrusion modes are also checked on every measured deposition
move, so a later M82 or G91 cannot hide behind a correct prefix. The complete executable stream, including every start/end command,
macro argument, limit and mode command, still has to match the independently
prepared native reference exactly.

Reports bind effective start/end hook and declared machine-limit digests and
record the exact start/end invocations, mode and target values. They explicitly
state `macro_internals: unobserved` and `physical_readiness: false`. A corrected
in-memory macro template used by the earlier accepted physical preparation is
not silently substituted for a different original profile hook. An original ABI outside the two explicitly supported variants, missing
effective information, stale inputs or actual native mismatch still blocks. Real printer configuration and accepted behavior remain
unchanged. Independent candidate review must assess this comparison policy.

Synthetic tests verify exact accepted invocations, wrong macro arguments,
unsupported original ABI without matching wait hooks, duplicate/misplaced end,
wrong extrusion mode, wrong
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

## Corrected native lab comparison and Windows input staging

The managed follow-up `06424308883348218503dc12c9bb18bc` preserved all native
exported options, including the dynamically registered machine-limit axes.
Its strict real Linux stock slice exited zero with no warnings and produced
956,379 bytes, SHA-256
`0bc421d8ec347bd10d3dbbc15852e6d23e9cb1002c93adcf9b95d09224243cf8`.
Against the unchanged genuine native lab file, complete heater, machine-limit
and M73 estimate streams now match exactly. Printed XY bounds are identical at
emitted precision: X102.975–147.024 and Y100.164–109.775 mm. Both independently
pass all 150 fixed-Z temperature/deposition checks.

The remaining measured motion/extrusion difference matches the lab's retained
external-cut triangulation finding: native/recipe model extrusion is
1915.31196/1915.90865 mm, and positive-E model move counts are 19,064/19,151.
The first differing G1 commands change E0.05034 to E0.05032 and split/order a
nearby brim contour differently. This is a measured toolpath difference, not
another machine-limit or thermal mismatch. The lab's separately retained
mesh/contour analysis bounds the sampled boundary difference at 0.000262 mm
for this case; it does not prove identical full topology or print quality.
The strict V1 executable gate remains blocked, and the legacy native run still
lacks the complete independently captured pre-calibration V1 context. No known
M73 or triangle difference is silently labeled equal or waived.

Managed geometry run `57fb5247065947549a132a7cc06304f0` prepared the native-derived
standard 230→190°C / scaled 0.4 mm model for actual October15 Windows comparison.
The unchanged full decoded native source asset has SHA-256
`17e387d8e5a19ca06daa574f97c1f981bf634c8d5af5c2349663519e23ea0a39`.
Cuts at 629.9999 and 540.0001 mm produce a watertight 27,280-face model with
extents 44.499069 × 10.000015 × 89.9998 mm. The prepared STL is 1,364,084 bytes,
SHA-256 `d7508da7e33682bee239873d56695363e9217954a860444733f7697137c9dcde`.
This is geometry provenance only; native triangulation/toolpath parity remains
mandatory. Both managed runs completed with `runtime_clear: true`, no errors,
and no lab/reference writes. The engine worker then received the exclusive
heavy-resource slot.

The lead's separately captured private R4 Windows context retains 775 effective
keys including explicit empty post-processing. `prepare_inputs` successfully
staged the default standard tower against that exact October15 context. A
private ZIP includes original immutable snapshot/request, exact input digest,
job-local profile/model copies, merged native configuration, structured Windows
argv and source/runtime/executable/geometry provenance. It instructs the lead
to use the exact hash-pinned Windows executable and separate V1 datadir/output,
with explicit bed selection and strict mode. The original native macro hook is
preserved. Staging is not Windows slicing, native parity or physical readiness;
the lead owns actual Windows execution and the independent native reference.
No private snapshot, profile name or operational path is promoted here.

## Actual October15 Windows Temperature comparison

The actual preferred Windows executable (SHA-256
`e2b6da4c20e7080eade97379f326dcfcaa90f1ecb9991f1db9eb61e3065a9759`)
prepared the stock CLI candidate from the complete independently captured R4
context. The lead independently used the native Calibration menu with
230→190°C, fixed 5°C step and nozzle auto-scale enabled. Retained native
parameter/slice/export screenshots, the pre-calibration context and actual
export bind the native reference. Candidate helper code, transferred bundle,
invocation and all resulting artifact hashes are verified. CLI exit was zero.
No UI automation or test worker is claimed as a shipping generation API.

| Actual artifact | Native UI | Programmatic stock CLI |
| --- | --- | --- |
| G-code bytes | 3,028,201 | 2,965,977 |
| G-code SHA-256 | `512eb13a80788bd22f928b1b073382070a7c43b5c667efd08ffcc05e550e29b7` | `7bcb855addd5747b4c8a2d8eb2c606b7d4415ff8b82ebe9543f7e3a840e9e544` |
| Fixed 0.2 mm layers | 450 | 450 |
| Actual deposited temperature sections | 230→190°C, nine sections | Exact same nine sections |
| Model positive-E XY moves | 59,562 | 59,464 |
| Model emitted E, mm | 5558.07546 | 5558.38590 |
| Geometry triangles / vertices | 27,238 / 13,585 | 27,280 / 13,606 |
| Exact degenerate triangles | 0 | 4 |
| Signed mesh volume, mm³ | 20517.682389683 | 20517.590425722 |

**Qualification remains blocked under `exact-executable-v1`.** Both files pass
all actual-deposition temperature/Z checks, complete nozzle/bed streams and
original visible-wait macro semantics. Printed XY bounds, G90/M83 modes,
PRINT_START/PRINT_END invocations and the pressure-advance command match.
This is command comparison only: the preserved original EXTRUDER/BED macro ABI
is not newly certified for the actual printer; macro internals remain unobserved
and `physical_readiness` is false.

The exact differences remain retained and classified:

- Model extrusion differs by +0.0055854%; toolpaths have 98 fewer positive-E
  model moves. This is a measured difference, not an assertion of print-quality
  equivalence.
- Dynamic Klipper acceleration streams contain 11,749 native versus 11,740 CLI
  commands. Their exact allowed values match (1500, 2000, 3000, 3500, 6000,
  7000 and 8000 mm/s²), but their sequences differ. Static Marlin-style limit
  streams are absent in these Klipper files; an empty equal stream is not proof
  of identical dynamic acceleration.
- Both files contain 175 M73 commands, with differing estimates/sequence values.
- Exclusion-object identifiers differ with the model names. Their derived
  exclusion polygons also differ: the symmetric maximum polygon-vertex to
  opposite-edge distance is 0.00931385 mm. This is a polygon measurement,
  not a full mesh-surface bound.
- Eight global emitted-setting differences are retained. The brim type/gap
  difference is resolved by independently inspected native **object** overrides:
  native object and candidate effective settings both use outer-only 5 mm brim
  with zero gap. Native global no-brim/0.1 mm values do not describe that object.
  The remaining differences are the stock layer template replacing native
  transient calibration state and retained preset identity/bookkeeping columns.
  None waives an executable difference.

The native full project remains in its isolated Windows evidence directory.
The standard-library whitelist utility inspected both projects **on Windows**
with Python `-I -S` and returned only bounded settings/scalar geometry metrics;
no full native project, profile text, hooks or vertex arrays were transferred.
Its executed source SHA-256 is
`a11979d38e87073576c495e743028252e0de8b9ea10d33b4ba2287b5f2080bcb`.
The native retained project is 341,982 bytes with SHA-256
`f6ac5e0a1bf46f7caeb826c0059dd0044a451be253a707fa81a51689fc6fbdbd`.
Its existence/hash is established by the Windows-local sanitized report, not
by a fabricated local copy. Both meshes have finite coordinates, valid indices
and zero indexed boundary/nonmanifold edges. Candidate-minus-native extent
changes are −0.0000076, −0.00001526 and −0.0001984 mm in XYZ. These scalar
measurements establish neither full-surface equivalence nor physical quality.

The native provenance manifest and raw comparison remain private. They bind
exact inputs, actual G-code bytes, UI evidence and the Windows-local metrics
report. No real printer action, settings/profile write or new physical test
occurred. The reusable report now distinguishes global emitted settings,
per-object evidence, static limit opcodes and dynamic acceleration streams.

A matching YOLO Recommended pass1 Windows bundle has also been staged from the
same complete original R4 context and exact native `Orca-LinearFlow.3mf` asset.
It preserves all eleven objects and native per-object ratios in a 3MF input;
flattening it to STL would lose the calibration. Recipe arithmetic mirrors the
source's float32 nozzle/width/label-modifier operations before native double
configuration values. Actual Windows slicing and independently prepared native
YOLO comparison are still required; staging alone is not qualification.

The source-only Windows parity runner executes the shared contract/evaluator
locally using the existing isolated Python. It verifies the exact generation
bundle, retained input members, executable/helper/archive fingerprints and CLI
output binding, then creates the native manifest from independently retained UI
evidence. Full reports, inputs, manifests and prepared descriptors remain in a
new Windows-only report directory. A qualified result is recomputed from its
retained bytes before any summary is returned.

Its stdout contains only fixed-key hashes, scalar counts, invariant flags,
bounded temperatures and classified comparison disposition. It emits no raw
executable lines, paths, profile names, effective configurations, hook strings
or raw exception messages. Historical request inspection uses its original
creation time because this is evidence evaluation, not a live dispatch gate;
`physical_actions`, `physical_readiness` and `hardware_abi_qualified` stay false.
The runner and two shared modules can be transferred as curated source without
moving the native G-code or full native project off Windows. Tests verify
privacy, provenance tampering and changed candidate rejection with explicitly
synthetic evidence; those tests do not represent a native qualification.

## October 15 native calibration invariant adapters

These adapters inspect executable behavior from the source at immutable commit
`6a7763f08d1a175a464a00ce13f0b5a815662fc4`. They do not generate G-code, assume
a Python generator API, or waive the independent native-reference requirement.
All three require an explicit non-belt context; arcs and firmware retraction
remain unsupported rather than partially analyzed. Input parameters pass the
shared validator before calibration math. Missing effective inputs are errors.

| Calibration | Source-verified behavior measured by the adapter | Explicit bounds |
| --- | --- | --- |
| Retraction | Native `start + floor(max(0, print_z − 0.4)) * step`; actual negative-E episodes are summed across wipe/retract splits and compared with the final negative command's nominal layer target. That layer's Z is measured from real deposited fixed-schedule moves; an episode's old or lifted starting Z is not the calibration Z. Real deposited Z follows native 0.05/0.1/0.2 mm layers for nozzle ≤0.1/≤0.2/>0.2 mm. Required positive-length sections and cut-height coverage must be present. | Declared `z_offset` is removed from deposited coordinates. A ±0.0002 mm boundary ambiguity accounts for serialized Z versus native float/double thresholds; retraction sum tolerance is 0.00003 mm. Native height cutting/layer quantization may reach a section above `end`; there is no invented end clamp. |
| Max Volumetric Speed | Native width is nozzle×1.75, height nozzle×0.8; `Flow` receives float32 values and returns float32 rounded-rectangle area, multiplied by immutable filament flow ratio. Native per-layer wall speed is `round((start + max(0, print_z) * step) / flow)`. Actual mature outer-wall maximum feed must attain that speed, with no move above it; at least three distinct speeds and native cut-height coverage are required. | First/slowdown layers follow native first-layer rules and are excluded from ramp assertions. Spiral-vase segments use their layer's measured top Z rather than each segment's interpolated Z. Serialized-Z ambiguity is ±0.0006 mm; feed tolerance is 0.02 mm/s. An additional speed cap causes a specific failure requiring investigation; it is not silently accepted. |
| Pressure Advance Pattern | Exactly four native custom sections, sample count `ceil((end−start)/step + 1)`, four-significant-digit Klipper PA commands, native per-section prefix/final resets, actual fixed-Z deposition, and three alternating 90° chevron walls per commanded sample. Mature side lengths are 30 mm. | Retained single-case Klipper route only. First-layer frame/tab/glyphs are separated from the six measured chevron sides by executable PA command boundaries. The first layer shrinks natively; mature side/coordinate tolerance is 0.003 mm. Non-divisible ranges can legitimately emit a last sample above `end`. |

The source anchors are `Plater.cpp` 17604–17745 (MVS/Retraction preparation),
`GCode.cpp` 6580–6640 (non-belt calibration Z and layer overrides),
`GCode.cpp` 9250–9338 (first-layer/slowdown and volumetric caps), `Flow.cpp`
225–232 (`mm3_per_mm`), `calib.hpp` 300–382 (PA configuration, count and four
layers), `calib.cpp` 644–811 (PA native custom commands and actual chevrons), and
`GCodeWriter.cpp` 594–612 (Klipper command formatting). Source blob SHA-256s:

| Source | SHA-256 |
| --- | --- |
| `src/libslic3r/GCode.cpp` | `4fc8b474911a30cded21cb4ad856f771ceba0c0f1d85b2aab9f93ef568aa37d7` |
| `src/libslic3r/calib.cpp` | `ac5e19c8d8d5bd27fd13b576f28312ed91d39c0190b6d1f170a21bcea96d3aa4` |
| `src/libslic3r/calib.hpp` | `3d993e153497669808075bcdc935e1666b18b840510da518fb6371cc7d064fd2` |
| `src/libslic3r/Flow.cpp` | `0e65189f2f3df44ad115d010dad47f49ebb0e4f01e53d773f7579aa26274daa0` |
| `src/libslic3r/GCodeWriter.cpp` | `7e74ae503a981bdd57bdad8536bf56f5e4fb20fdb4f1987e74b03e5afe0e1db0` |
| `src/slic3r/GUI/Plater.cpp` | `8290003e06b12b06a5c239e4d66269dfbc081895c5deb304f3a9b6dbddc8621a` |

All five Klipper invariant results now expose
`candidate_invariants.macro_semantics.accepted_abi_signature` (and the same field
for the native result). It is true only for the retained
`BED_TEMP`/`EXTRUDER_TEMP` signature. The separately approved original
`EXTRUDER`/`BED` signature with matching visible waits remains false for that
field. Neither value observes macro internals or certifies hardware readiness;
`hardware_abi_qualified` and `physical_readiness` stay false. The Windows summary
exposes only these fixed-key boolean facts, never invocation strings or hooks.

Synthetic tests reject changed PA values, missing sections/reset, malformed
chevrons/Z, wrong Retraction episode length/Z/firmware commands, flattened MVS
feeds or missing height, unsupported source/belt context, absent required
effective values, invalid step, and changed start/bed/extrusion/coordinate modes.
Actual native references for these routes are still required. Every executable
difference still blocks `exact-executable-v1`; no geometry, motion, extrusion,
estimate or calibration-section difference is waived by these adapters.

## Windows-local native reference inspection before generation

`scripts/v1-native-reference.py` registers actual native UI evidence and runs
the same invariant adapter before any candidate exists. Its CLI accepts only a
local native G-code path, the unchanged original context, a typed calibration
ID, optional local parameter JSON, actual distinct PNG screenshot paths and a
new output directory. There is no candidate option. It calls
`create_native_reference` and retains `native-reference.json`,
`native-inspection.json` and a sanitized `summary.json` locally on Windows.
An invariant failure also retains the native manifest and full local diagnostic
detail, exposing only a fixed public failure code. Registration always reports
`qualified: false`; no comparison or physical readiness can be established by
inspecting one native artifact.

This bounded inspector pins the source/runtime above and canonical original
context SHA-256
`3bf24bab6c2ac71cf7c0017d8889d4430006d3cd489a512ff656990f41324b3c`.
Its known defaults match the independently prepared dialogs: Temperature
230→190/5°C scaled, YOLO Recommended pass1, PA Pattern 0→0.08/0.005,
Retraction 0→2/0.1 mm and MVS 5→20/0.5 mm³/s. A local JSON file may specify a
different bounded parameter set explicitly; nothing is inferred from filenames,
comments or a programmatic candidate. UI provenance still requires review of
the retained actual screenshots; file fingerprints alone cannot prove a GUI
action.

Invoke using an existing Python with `-I -S`; the utility explicitly adds only
its curated source root for the shared standard-library modules. For example,
`python.exe -I -S scripts/v1-native-reference.py --calibration retraction
--native <local-native.gcode> --context <original-context-r5.json>
--native-evidence <actual-parameters.png> --native-evidence <actual-export.png>
--output-dir <new-private-report-directory>` (one command). Its ≤64 KiB stdout
contains only fixed-key hashes, calibration/default parameter numbers, counts,
bounded measured calibration values and flags. Source fingerprints bind the
inspector, shared contract and parity implementation. No executable text,
profile/object names, paths, hooks, full configuration, vertices or raw exception
messages are returned. Argument errors use a fixed code too.

The transferred package consists only of this utility, the curated contract and
parity source, an empty package initializer and an exact source-file manifest.
No model, profile/configuration payload, generation input bundle or G-code is
included. Earlier R4 transfer archives are preserved unchanged. Tests cover
local retained provenance, source/context binding, invariant-failure retention,
unknown-field privacy, screenshot validation, refusal to overwrite reports,
explicit/default parameter validation and rejection of any candidate argument.

Actual Windows PA Pattern reference inspection passed the native invariants at
the documented defaults: four layers, seventeen values from 0 to 0.08, three
walls per sample, 789 measured model moves and 2,904 executable commands. The
92,568-byte native G-code SHA-256 is
`53fcd2d926eac9dbe9979450a4b0d4ba30ed9025c2f9bcc3eead155b7300eab5`.
This native-reference-only observation still has `qualified: false`, unobserved
macro internals and no physical readiness; no programmatic PA candidate is
qualified by it.

The first actual Windows Retraction inspection retained a checker failure:
204 episodes over 107 layers with seven transition-only mismatches for the
0→2/0.1 mm tower. Native G-code SHA-256 is
`0f5dec36bf301cf94c2c9824d940d725083ae5b8b873435a493887533a2de678`;
the historical failed report SHA-256 is
`f689d94e8bfb760843fbcf483de7cbc426373d745ab71d21de2191a759c8f142`.
Bounded Windows-local scalar diagnostics showed, for example, an aggregate
0.2 mm retract beginning at physical Z2.2 before deposition at nominal Z2.4.
Its previous native state tag was still 0.1 mm at nominal Z2.2. The seven
examples show transition top-ups; they do not show wrong native lengths.

The source explains the ordering: `GCode::change_layer` 8257–8289 may retract
before the calibration override at 6633; lazy Z travel and later wiping/retract
can extend the same outstanding episode after the override. `Extruder::retract`
76–101 adds only `max(0, target − already_retracted)`; `GCode::retract`
10418–10437 finishes any remaining amount after wipe. The checker now tracks
the last negative-E command's layer and validates the aggregate against that
layer's independently measured deposition Z. Native length comments are not
an oracle. Length/Z tolerances and exact executable equality are unchanged.
Synthetic cross-layer/lifted-Z tests verify both incomplete and excessive
top-ups still fail even with forged native-looking comments. The historical
failed inspection and source archive remain unchanged. A fresh corrected Windows
inspection now passes 202 checked episodes across 107 layers, in the separately
fingerprinted report `5e0d0a19ee77809f30e1195c667ed32dd9f2ec77e36de4033f9525ba936f23f5`.
This native invariant result does not qualify programmatic output.


## Actual Windows YOLO comparison and complete native references

The approved exact original-context bundle was transferred back to the same
isolated Windows stage and sliced by the pinned October 15 executable. Exit 0,
2.457 seconds; candidate G-code SHA-256
`ce05e8bd2acc16ceea51781745357bc90b87cb72800634eff60bc99061f358cb`.
The independently prepared native UI G-code SHA-256 is
`0fb149a6a1624cdf64cb03a8c0dcb0fc6a21d9d3f43a4fb0f3389e4e48485daa`.
Both ten-layer YOLO invariant checks pass with identical 4854.673 mm extrusion
and 43241 deposition moves. Executable commands differ (55268 vs 55273), along
with dynamic acceleration stream, motion stream and printed XY bounds. Five
emitted-setting differences are classified, none waived. Exact parity is false;
report SHA-256 `5c5fb10764918deba29573a1ac5465b108ffdf659ad92418ed79152e287b27d3`.

Native PA Pattern, Retraction and MVS references also pass their source-derived
invariants after Retraction's measured layer-transition checker correction. Their
references do not qualify an unbuilt native adapter. All exact native/report/tool
hashes and the historical failed Retraction inspection are retained in the
[public-safe Windows inventory](evidence/issue-14/windows-reference-inventory.json).
[Windows observations](V1_WINDOWS_ORCA.md) distinguish actual native references,
actual CLI outputs, parity failures, normal-profile preservation and packaging
limits. Full private G-code/projects/configuration stay separate from that export.

## Actual Windows YOLO layout diagnosis and corrected stock recipe

The historical fixed input archive `d2296b…` produced a genuine Windows CLI
candidate with SHA-256
`ce05e8bd2acc16ceea51781745357bc90b87cb72800634eff60bc99061f358cb`
(1,559,700 bytes), compared against independently prepared native G-code
`0fb149a6a1624cdf64cb03a8c0dcb0fc6a21d9d3f43a4fb0f3389e4e48485daa`
(1,576,258 bytes). Both pass the calibration invariants: ten layers, 43,241
model moves and 4,854.673 mm model E. This does **not** qualify the candidate:
executable counts are 55,268 versus 55,273, motion/extrusion sequences and
dynamic acceleration order differ, and XY bounds differ. The strict gate
remains closed; identical totals are not path equivalence.

Bounded Windows-local per-label diagnostics establish eleven identical patch
move counts, E totals and XY extents, but differing patch translations and layer
order. Candidate-minus-native patch translations range from −63.5 to +94.5 mm
in X and −64 to +64 mm in Y. Seven of eleven diagnostic relative-path hashes
match after per-object translation and decimal normalization; four differ.
Those diagnostic hashes neither compare the complete executable stream nor
waive the four remaining relative-path differences.

The source identifies the recipe error. `Plater::calib_flowrate` 17273–17299
imports the public native 3MF and changes object settings without arranging it.
`Plater::add_model` 16608–16610 uses `LoadModel`; the non-project 3MF import at
10004–10006 centers the entire model around the bed center.
`Model::center_instances_around_point` 846–864 applies one uniform translation
to all existing instances. `BuildVolume.hpp` 87 defines that bed center as the
printable-area bounding-box center. The original public YOLO model bounds are
X[−37,86], Y[34,128] mm; its fixed relative patch layout is intentional.

The old stock route instead forced `--arrange 1`, repacking individual patches.
The corrected YOLO route uses `--center <effective printable-area bbox center>
--arrange 0`; pinned `OrcaSlicer.cpp` 4919–4937 invokes the **same** native Model
centering helper and 4945–4950 disables subsequent arrangement. Temperature's
single-model route is unchanged. Missing/malformed/degenerate effective bed
geometry blocks preparation rather than using a CLI/profile default.
`prepare_inputs` now exposes its exact `layout_arguments` so another caller
does not recreate stale shared CLI arguments. Tests verify those arguments,
asymmetric/triangular bed-center math, unchanged model/build transforms and
unavailable-layout failure before execution. No tolerance or parity policy was
changed to address the layout error.

`scripts/v1-windows-stock-yolo.py` calls the real production
`integration.v1_generation.generate` locally with no injected runner. It reads
the existing immutable original context and independent native reference
manifest/G-code on Windows, the exact pinned executable and original public
asset `c998359c…`, and creates a fresh request nonce with current time and a
one-hour deadline. Native comparison inputs intentionally exclude nonce/time,
so the historical independent reference still matches identical immutable
profiles, parameters, source and runtime. The generation subprocess has a fixed
45-second timeout and isolated job paths; all request/configuration, prepared
inputs, invocation, G-code, full parity report and source-fingerprinted
provenance stay in a new Windows-only directory.

Its source-only transfer contains the driver, production generation/parity/
contract code, approved sanitized-summary helper and an exact code manifest.
It contains no private context, profile, model or generation-input bundle. The
already approved historical archive remains unchanged. Existing local original
public calibration assets are preferred; a separately verified public asset
copy can be used if needed. The driver accepts only fixed bounded path arguments
and returns ≤64 KiB fixed-key hashes, scalar observations and flags, with no raw
commands, full coordinates, names, hooks or profile payload. A successful slice
still needs exact executable parity; physical/hardware readiness remains false.
The corrected actual Windows run is pending and must receive its own artifact,
request, source and report fingerprints rather than replacing historical proof.
