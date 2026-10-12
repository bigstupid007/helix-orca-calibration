# Baseline temperature-tower slice

This is a bounded reconstruction of one baseline temperature-tower slice. It
does not approve transport, printer-side implementation, G-code generation,
slicing automation, preset mutation, or another milestone.

## Exact input artifacts

The authoritative selected context was:

- printer: `Voron 2.4 300 0.4 nozzle`;
- process: `Voron 0.20 Standard - Fast Quality`;
- filament: `Generic PLA - Voron Rapido - Initial`;
- nozzle: `0.4 mm Brass`.

The supplied G-code is:

```text
/Users/dev/.codex/attachments/57505dc0-5323-45c9-935b-70e3fafe654f/temperature_tower_PLA_1h10m.gcode
SHA-256 7042c5c9e6ef123e756b65bb370c2247db4afa2808ded2f20cc9a9baa556d8b9
```

It identifies OrcaSlicer `2.5.0-dev`, generated 2026-09-22 at 10:48:23,
and embeds the exact three selected profile names above. The matching reference
source revision is `824b216f18232a0e25644e225c286746ee07cb5f`.

Exact profile inputs:

| Role | File | SHA-256 |
| --- | --- | --- |
| Printer leaf | `testdata/orca-profiles/Voron 2.4 300 0.4 nozzle.json` | `568cbc65fa0ccf2838845f478317050e7c64e69136ca0a243fdcd23325bc4614` |
| Printer parent | `testdata/orca-profiles/Voron Voron 2.4 300 0.4 nozzle.json` | `1f9bed2b1cdc578bafc2fdd95a7a44b5ba607f3fcfda5b2d357d83229fcb6567` |
| Process leaf | `testdata/orca-profiles/Voron 0.20 Standard - Fast Quality.json` | `a62c25f380d54e567e54d701d6387df853cdf35a167dde7f9c2657f9709c2aee` |
| Process parent | `testdata/orca-profiles/process template @Voron Voron 2.4 300 0.4 nozzle.json` | `4d9726ae721e8fad7f6e08787cb54d28d42ecef04c5d721fb7648b61d993d214` |
| Filament leaf | `testdata/orca-profiles/Generic PLA - Voron Rapido - Initial.json` | `eb4aaf99dbc806199aa0f18b25648e8fe6c206740d6b4c175024e05fdc5a3188` |
| Filament parent | `testdata/orca-profiles/Generic PLA template @Voron Voron 2.4 300 0.4 nozzle.json` | `7dfc6d314ccb5000d2e326623aea5929cb3e28c63595b8163ddf2d98dbf82239` |

No similarly named bundled preset is used in this analysis.

## Exact inheritance chains

All six JSON names and `inherits` values agree with the G-code's selected IDs
and `inherits_group` fields. Each supplied direct parent has `inherits: ""`, so
the relevant chains terminate without a deeper unresolved JSON parent.

```text
Voron 2.4 300 0.4 nozzle
  -> Voron Voron 2.4 300 0.4 nozzle
  -> end

Voron 0.20 Standard - Fast Quality
  -> process template @Voron Voron 2.4 300 0.4 nozzle
  -> end

Generic PLA - Voron Rapido - Initial
  -> Generic PLA template @Voron Voron 2.4 300 0.4 nozzle
  -> end
```

Resolution is ordinary leaf-over-parent replacement: a key in the leaf wins;
otherwise the direct parent's value is inherited. Orca then adds defaults,
project/object configuration, calibration edits, and slice-time normalization
to form the effective configuration.

### Printer leaf over parent

Relevant inherited parent values include the 0.4 mm nozzle, FFF technology,
Klipper flavor, relative extrusion, 300 x 300 mm printable area, 30 mm/s
retraction speed, wipe, layer-change snippets, and `PRINT_END`.

The leaf changes the nozzle material to brass, printable height to 290 mm,
retraction to 0.5 mm, Z-hop to zero, machine acceleration/Z limits, and the
start macro to:

```text
PRINT_START BED_TEMP=[bed_temperature_initial_layer_single] EXTRUDER_TEMP=[nozzle_temperature_initial_layer]
```

This removes the parent's explicit `M190`/`M109` waits. Heating, homing, mesh,
and readiness before the first move therefore depend on the printer-local
`PRINT_START` implementation.

### Process leaf over parent

The parent supplies 0.2 mm normal/first-layer height, all 0.4 mm line widths,
15% crosshatch infill, three bottom layers, 50 mm/s bridge speed, 200 mm/s
outer walls, classic wall generation, aligned seams, and the remaining base
geometry rules.

The leaf materially changes three walls, three top layers, inner wall speed to
280 mm/s, sparse infill to 300 mm/s, top surface to 100 mm/s, travel to
400 mm/s, role accelerations, two skirt loops, global `brim_type` to
`no_brim`, overhang speed control off, and object exclusion on.

### Filament leaf over parent

The parent supplies Generic PLA, 1.75 mm filament, flow ratio 1.0, density
1.24 g/cm³, saved nozzle temperatures of 220 °C, a 190-240 °C range,
100% maximum fan, bridge/overhang cooling, and other material defaults.

The leaf changes the High Temp Plate target from 55 to 60 °C, maximum
volumetric speed from 12 to 24 mm³/s, pressure advance from disabled/0.02 to
enabled/0.035, fan ramp values, slowdown thresholds, and filament start/end
snippets. It does not save either nozzle-temperature key, so both inherit
220 °C before Orca's calibration edit.

## Effective context summary

The effective slice is a single-extruder, Klipper-flavor PLA print using a
0.4 mm brass nozzle and 1.75 mm filament. It is 90.0 mm tall, contains 450
layers at 0.2 mm, and reports 0.4 mm extrusion widths for first layer,
perimeters, infill, solid infill, and top infill.

It uses three walls, three top and bottom layers, 15% crosshatch infill,
0.5 mm retraction at 30 mm/s, wipe with no Z-hop, 0.035 pressure advance,
60 °C bed, staged cooling, and a 24 mm³/s volumetric cap. That cap was
binding: nominal flow reconstructed from emitted XY/E/F moves peaks at about
24.0001 mm³/s, within G-code rounding of 24 mm³/s.

The file calls `PRINT_START BED_TEMP=60 EXTRUDER_TEMP=230`, uses `M83`, emits
`SET_PRESSURE_ADVANCE ADVANCE=0.035`, `SET_VELOCITY_LIMIT`, `M104`, `M106`,
and `EXCLUDE_OBJECT_*`, then ends with `PRINT_END`.

## Classification method

Every row below has one primary bucket. Precedence is:

1. **A — MUST TRANSMIT:** per-request semantics that must be supplied directly
   or resolved unambiguously from an immutable artifact manifest;
2. **B — TEMPLATE COMPATIBILITY:** a mismatch can make the artifact unsafe or
   unrepresentative, even when the setting's mechanical effect is baked in;
3. **C — BAKED INTO G-CODE:** fully encoded output that needs no separate
   runtime control after the correct artifact is selected;
4. **D — PRINTER-SIDE LOCAL:** physical truth or behavior owned and validated
   by the printer/firmware side;
5. **E — IRRELEVANT:** inactive or non-material for this workflow.

“Different artifact” means select or generate a separately validated slice;
it does not authorize generation in this project.

## Setting-by-setting causality

| Orca key or behavior | Source and saved resolution | Effective value | G-code influence/evidence | Change rule | Bucket | Confidence |
| --- | --- | --- | --- | --- | --- | --- |
| Calibration `start`, `end`, fixed `step` | Neither JSON; Orca calibration parameters | 230, 190, -5 °C | Defines nine bands and every `M104` target | Transmit directly or bind immutably to artifact ID; do not patch this baseline | A | verified from source + G-code |
| `nozzle_temperature` | Filament leaf absent; parent 220 °C | 230 °C calibration edit | Startup target and first band | Same semantic value as calibration start; not a second independent field | A | verified from source + JSON + G-code |
| `nozzle_temperature_initial_layer` | Filament leaf absent; parent 220 °C | 230 °C calibration edit | `PRINT_START ... EXTRUDER_TEMP=230` | Same semantic value as calibration start | A | verified from source + JSON + G-code |
| `nozzle_temperature_range_low/high` | Filament parent 190/240 °C | 190/240 °C | Validates the requested 230-190 range; not a motion command | Different artifact or reject range mismatch | B | verified from JSON + G-code |
| `nozzle_diameter` | Printer leaf absent; parent 0.4 mm | 0.4 mm | Extrusion widths, path spacing, layer/model scale assumptions | Different artifact | B | verified from source + JSON + G-code |
| `nozzle_type` | Printer parent `undefine`; leaf `brass` | Brass | Thermal/material compatibility; metadata rather than a command | Different artifact/fingerprint | B | verified from JSON + G-code |
| `filament_type`, `filament_vendor` | Filament parent PLA/Generic | PLA/Generic | Material/range identity and metadata | Different artifact/fingerprint | B | verified from JSON + G-code |
| `filament_diameter` | Filament parent 1.75 mm | 1.75 mm | Directly determines E amounts | Different artifact | B | verified from JSON + G-code |
| `filament_flow_ratio` | Filament parent 1.0 | 1.0 | Directly determines E amounts | Different artifact | B | verified from JSON + G-code |
| `layer_height` | Process parent 0.2 mm | 0.2 mm | 450 layers and all Z/toolpaths | Different artifact | B | verified from source + JSON + G-code |
| `initial_layer_print_height` | Process parent 0.2 mm | 0.2 mm | First Z/toolpaths; calibration resize would also set nozzle/2 | Different artifact | B | verified from source + JSON + G-code |
| `line_width`, initial/outer/inner/sparse/top/internal widths | Process parent 0.4 mm for each | 0.4 mm for each | Path placement and E amounts; reported in header | Different artifact | B | verified from JSON + G-code |
| `wall_loops` | Process parent 2; leaf 3 | 3 | Three perimeter paths | Different artifact/fingerprint | B | verified from JSON + G-code |
| `bottom_shell_layers`, `top_shell_layers`, shell thickness | Parent bottom 3/top 5/0.6 mm; leaf top 3 | Bottom 3, top 3, top 0.6 mm | Solid geometry and layer timing | Different artifact/fingerprint | B | verified from JSON + G-code |
| `sparse_infill_pattern`, `sparse_infill_density` | Process parent crosshatch/15% | Crosshatch/15% | Infill path geometry and cooling/layer time | Different artifact/fingerprint | B | verified from JSON + G-code |
| `wall_generator`, `wall_sequence`, `seam_position` | Process parent classic, inner/outer, aligned | Same | Path topology and seam behavior | Different artifact/fingerprint | B | verified from JSON + G-code |
| `initial_layer_speed`, `initial_layer_infill_speed`, `initial_layer_travel_speed` | Parent 50/105/100%; leaf overrides latter two to 80/120 mm/s | 50/80/120 mm/s | Feed rates and first-layer timing | Different artifact/fingerprint | B | verified from JSON + G-code |
| `outer_wall_speed`, `inner_wall_speed` | Parent 200/300; leaf inner 280 mm/s | 200/280 mm/s | Wall feed rates and thermal exposure | Different artifact/fingerprint | B | verified from JSON + G-code |
| `sparse_infill_speed`, `internal_solid_infill_speed`, `top_surface_speed`, `gap_infill_speed` | Parent 270/250/200/250; leaf 300/260/100/160 mm/s | 300/260/100/160 mm/s | Feed rates, layer time, and flow demand | Different artifact/fingerprint | B | verified from JSON + G-code |
| `bridge_speed`, `internal_bridge_speed`, bridge flow | Process parent 50 mm/s, 150%, flow 1.0 | Same | 18 `TYPE:Bridge` sections, two per band | Different artifact/fingerprint | B | verified from JSON + G-code |
| `travel_speed` | Process parent 500; leaf 400 mm/s | 400 mm/s | `F24000` travel moves | Different artifact/fingerprint | B | verified from JSON + G-code |
| Default and role accelerations | Process parent values; leaf sets default 2000, initial 1500, initial travel 3000, outer 3500, inner 7000, sparse 8000, top 3000, internal solid 6000, bridge 3000 mm/s² | Leaf values | Repeated `SET_VELOCITY_LIMIT ACCEL=...` | Different artifact/fingerprint | B | verified from JSON + G-code |
| `filament_max_volumetric_speed` | Filament parent 12; leaf 24 mm³/s | 24 mm³/s | Caps feed rates; reconstructed peak reaches cap | Different artifact/fingerprint | B | verified from JSON + G-code |
| `close_fan_the_first_x_layers`, `full_fan_speed_layer` | Filament parent 1/0; leaf 2/4 | 2/4 | Initial fan-off/ramp timing | Different artifact/fingerprint | B | verified from JSON + G-code |
| `fan_min_speed`, `fan_max_speed`, layer cooling thresholds | Parent max 100%, 100 s; leaf min 30%, slowdown 8 s/min 0 | 30-100%, 100 s threshold, 8 s slowdown | `M106` schedule and feed-rate cooling decisions | Different artifact/fingerprint | B | verified from JSON + G-code |
| `enable_overhang_bridge_fan`, `overhang_fan_speed` | Filament parent enabled/100% | Enabled/100% | Near-full fan changes around bridge/overhang paths | Different artifact/fingerprint | B | verified from JSON + G-code |
| `hot_plate_temp`, `hot_plate_temp_initial_layer` | Filament parent 55; leaf 60 °C | 60 °C | `PRINT_START BED_TEMP=60`; later `M140 S60` | Different artifact/fingerprint | B | verified from JSON + G-code |
| `curr_bed_type`, `bed_temperature_formula` | Bed type is neither leaf nor parent; printer parent supplies `by_highest_temp` | Project/plate merged value `High Temp Plate`; one filament resolves to 60 °C | Selects the hot-plate temperature keys used by startup and `M140` | Different artifact/fingerprint | B | verified from source + JSON + G-code |
| `retraction_length`, `retraction_speed` | Printer parent 0.8/30; leaf length 0.5 mm | 0.5 mm at 30 mm/s | Relative-E retract/unretract moves | Different artifact/fingerprint | B | verified from JSON + G-code |
| `retract_before_wipe`, `retract_when_changing_layer`, `wipe`, `z_hop` | Parent 70%, enabled, wipe enabled, 0.4 mm Z-hop; leaf Z-hop 0 | 70%, enabled, wipe, no Z-hop | Retraction/wipe moves and absence of lift | Different artifact/fingerprint | B | verified from JSON + G-code |
| `enable_pressure_advance`, `pressure_advance` | Filament parent disabled/0.02; leaf enabled/0.035 | Enabled/0.035 | Explicit `SET_PRESSURE_ADVANCE ADVANCE=0.035` | Different artifact/fingerprint | B | verified from JSON + G-code |
| `gcode_flavor` | Printer parent `klipper` | Klipper | Command dialect, `M104`, Klipper-native commands | Different artifact | B | verified from source + JSON + G-code |
| `use_relative_e_distances` | Printer parent 1 | Relative E (`M83`) | Interpretation of every E move | Different artifact | B | verified from JSON + G-code |
| `machine_start_gcode` call contract | Printer parent has waits and different args; leaf replaces it | `PRINT_START BED_TEMP=... EXTRUDER_TEMP=...` | Exact first executable macro call | Different artifact unless ABI identical | B | verified from JSON + G-code |
| `machine_end_gcode` call contract | Printer parent `PRINT_END`; leaf absent | `PRINT_END` | Exact end macro call | Different artifact unless ABI identical | B | verified from JSON + G-code |
| `printable_area`, `printable_height` | Printer parent 300 x 300 x 300; leaf height 290 mm | 300 x 300 x 290 mm; actual moves X 127.950-177.255, Y 136.408-163.584, Z 0.2-90.0 | Coordinate envelope | Different artifact or separately proven transform | B | verified from JSON + G-code |
| Tool topology | Parent one physical/direct-drive variant; leaf selects extruder 1 | One used filament/extruder, no tool change | One E stream; no `T` change | Different artifact | B | verified from JSON + G-code |
| Machine motion limits | Parent up to 500 mm/s XY/20,000 mm/s²; leaf caps primary mode to 8,000 mm/s² and Z values | Slice requests up to 400 mm/s and 8,000 mm/s² | Caps and emitted velocity-limit commands | Template records demands; printer validates physical capability locally | B | verified from JSON + G-code |
| `exclude_object` and local command support | Process parent 0; leaf 1 | Enabled | `EXCLUDE_OBJECT_DEFINE/START/END` | Different artifact or proven command support | B | verified from JSON + G-code |
| Actual `PRINT_START`/`PRINT_END` implementation | Not in Orca JSON or G-code | Unknown | Must home, heat/wait, mesh, and end safely; no explicit `M109`/`M190` remains before first moves | Keep printer-side; validate macro ABI/behavior | D | unresolved |
| Actual heater dynamics and measured temperature | Not in Orca artifacts | Unknown | `M104` changes are non-waiting; achieved temperature may lag a band boundary | Keep printer-side; capture telemetry for result trust | D | inferred |
| Physical nozzle, loaded filament, firmware limits, fan mapping | Orca records claims, not physical truth | Unknown until printer validates | Determines whether compatibility claims are true | Keep printer-side | D | inferred |
| Layer-change snippets | Printer parent `G92 E0` before and comments after each layer | Emitted each layer | Fully encoded reset/comments | No runtime field | C | verified from JSON + G-code |
| Calibration object brim override | Global leaf says `no_brim`; calibration source applies outer-only, width 5 mm, gap 0 | Outer brim present | Executable `TYPE:Brim` geometry | Different artifact; do not patch | C | verified from source + JSON + G-code |
| Skirt behavior | Process parent 0 loops/2 mm/50 mm/s; leaf 2 loops/3 mm/35 mm/s | Leaf values | First-layer `TYPE:Skirt` paths | No runtime field | C | verified from JSON + G-code |
| Other calibration safeguards | Source sets alternate wall off, seam slope none, overhang reverse off, precise Z off, resonance avoidance off, wrapping detection off | Values already agree with resolved profiles in this case | Affects or stabilizes slice behavior; no separate runtime command needed | No runtime field | C | verified from source + JSON + G-code |
| `filament_start_gcode`, `filament_end_gcode` | Leaf replaces parent's auxiliary-fan snippets with comments | Comments only | No material start/end filament command | No runtime field | C | verified from JSON + G-code |
| Support, raft, ironing | Process parent disabled; leaf does not enable | Disabled | No support/raft/ironing paths | No change | E | verified from JSON + G-code |
| `enable_prime_tower` | Process parent 1; leaf absent | Normalized to 0 for one used filament | No prime tower path | No change | E | verified from source + JSON + G-code |
| Support speeds/interfaces and tree-support options | In parent/leaf and merged config | Inactive | No support paths | No change | E | verified from JSON + G-code |
| `filament_density`, cost | Filament parent 1.24 g/cm³ and cost metadata | 1.24 g/cm³; 16.73 g estimate | Estimate/metadata only, not E geometry | No change | E | verified from JSON + G-code |
| Print host, thumbnails, color, notes, timelapse, air filtration, drying | Various saved/default/merged values | Non-material here | Metadata or inactive | No change | E | verified from JSON + G-code |

## Temperature-tower behavior

### 1. How Orca varies temperature

`Plater::calib_temp` cuts the stock tower to the requested start/end range,
sets both edited filament nozzle-temperature keys to the start value, and
stores calibration parameters on the print. During G-code generation,
`GCode::interpolate_value_across_layers` divides the inclusive range into nine
equal layer bands. `GCodeWriter::set_temperature` emits non-waiting `M104` for
the Klipper flavor.

The file contains exactly 450 `M104` commands: one per layer. Most repeat the
current target; the target changes at these boundaries:

| Layers (one-based) | Z range | Target | First command line |
| --- | --- | ---: | ---: |
| 1-50 | 0.2-10.0 mm | 230 °C | 243 |
| 51-100 | 10.2-20.0 mm | 225 °C | 14,824 |
| 101-150 | 20.2-30.0 mm | 220 °C | 28,293 |
| 151-200 | 30.2-40.0 mm | 215 °C | 41,820 |
| 201-250 | 40.2-50.0 mm | 210 °C | 55,466 |
| 251-300 | 50.2-60.0 mm | 205 °C | 69,340 |
| 301-350 | 60.2-70.0 mm | 200 °C | 83,426 |
| 351-400 | 70.2-80.0 mm | 195 °C | 96,874 |
| 401-450 | 80.2-90.0 mm | 190 °C | 110,482 |

These are commanded targets, not proof of the actual measured nozzle
temperature at the start of each band. Because transitions do not wait, heater
dynamics remain printer-local experimental context.

### 2. What makes this tower representative

For this exact fast process, the high-risk representativeness settings are
nozzle material/diameter, filament type/diameter/flow, 0.2/0.4 mm geometry,
wall and bridge speeds, accelerations, the binding 24 mm³/s flow cap,
cooling/slowdown behavior, retraction, pressure advance, bed temperature, and
the Klipper start/motion command contract. Changing any of these is not proven
equivalent and remains a template-fingerprint change.

### 3. What is completely baked

The exact XYZ/E toolpaths, band boundaries, all 450 `M104` commands, fan
commands, feed rates, acceleration commands, retraction/wipe, pressure advance,
brim/skirt, object-exclusion regions, relative extrusion, start/end calls, and
estimated material are already encoded. A printer does not need the original
profile JSONs to execute them.

### 4. What forces a different artifact

Until equivalence is experimentally proven, any mismatch in a bucket-B row
forces a different validated artifact or rejection. Geometry/extrusion keys,
flow cap, speeds, accelerations, cooling, retraction, pressure advance, nozzle
or filament dimensions, command dialect/macro ABI, tool topology, and printable
envelope must not be treated as runtime substitutions.

### 5. What can be patched safely

Only non-executable metadata is unconditionally safe to change in this exact
artifact. The bed target is mechanically replaceable only if both the
`PRINT_START` argument and later `M140` agree and the changed condition is
recorded, but that is not proven equivalent calibration context.

The nozzle schedule is mechanically editable but not safely patchable here:

- it is repeated in all 450 layer commands;
- Orca selected/cut the calibration geometry for the 230-190 range;
- any baked visual range markings may cease to match;
- a different range changes heater-lag behavior at the same boundaries.

Fan, speed, acceleration, pressure advance, retraction, flow, layer height,
line width, nozzle/filament diameter, and path topology must not be patched.
They affect geometry, extrusion, timing, cooling, or the controlled conditions.

### Explicit answers to the eleven baseline questions

1. Orca writes the requested start temperature into the edited filament copy,
   cuts the stock tower to the requested range, divides the 450 layers into
   nine equal bands, and emits the corresponding target once per layer.
2. The exact boundaries are the 50-layer/10 mm ranges in the table above;
   target changes begin at Z 10.2, 20.2, 30.2, 40.2, 50.2, 60.2, 70.2, and
   80.2 mm.
3. `PRINT_START ... EXTRUDER_TEMP=230` supplies the initial macro argument and
   450 non-waiting `M104` commands implement the layer schedule.
4. The bucket-B rows identify the settings that make this a representative
   print: dimensions/flow, geometry, speeds, accelerations, cooling,
   retraction, pressure advance, bed condition, and command contract.
5. The complete paths and emitted commands listed under **Baked into G-code**
   are already encoded.
6. Any unproven mismatch in a bucket-B row requires a different validated
   artifact or rejection.
7. Only metadata is unconditionally safe to patch. Bed temperature is
   mechanically editable but not proven calibration-equivalent.
8. Temperature range, geometry, extrusion, timing, cooling, retraction,
   pressure advance, and motion parameters should not be patched.
9. Yes. The effective temperatures, normalized prime-tower state, and
   object-level brim differ from simple saved global-profile resolution.
10. The 220-to-230 °C temperature changes are proven calibration-created
    edited state; prime-tower disablement is normalization; the brim is an
    object override. No other material unsaved filament edit is evidenced.
11. The evidence supports a small runtime request plus strict artifact
    selection and a canonical effective-context fingerprint, not a large
    profile payload and not printer-side reproduction of Orca slicing.

## Saved versus effective differences

### Unsaved-edit evidence

1. **Nozzle temperatures:** both saved resolved values are 220 °C from the
   filament parent; the effective slice contains 230 °C. Orca source proves
   that temperature calibration writes the chosen start value into the edited
   filament copy and calls the dirty-state update before slicing. This is
   calibration-created unsaved edited state, not a saved leaf value.

Every other materially relevant filament row matches saved leaf-over-parent
resolution. The artifact does not prove another material unsaved filament
edit. It also cannot prove whether some unrelated UI value was momentarily
dirty but equal to the saved/effective result.

### Other material differences

1. **Prime tower:** the saved process resolves to enabled, while the effective
   config is disabled. `normalize_fdm_2` disables it for a normal print with
   one used, non-mixed filament. This is deterministic slice-time
   normalization, not an unsaved edit.
2. **Brim:** the saved process leaf and global effective config both say
   `no_brim`, but the calibration object has an outer-only 5 mm/zero-gap
   override. The executable `TYPE:Brim` path confirms the object-level value.

### Relevant values from neither saved file

- The 230/190/5 °C calibration parameters are transient calibration state,
  not preset keys saved in the six JSON files.
- `curr_bed_type = High Temp Plate` is plate/project merged state. It selects
  the leaf's 60 °C hot-plate values.
- The outer-only, 5 mm, zero-gap brim and the other calibration safeguards are
  object/calibration overrides rather than global preset values.
- Actual startup waits, heater response, and physical hardware identity are
  printer-side state and remain absent from Orca's artifacts.

### Non-material differences

- `extruder_colour` resolves to the parent's yellow but the merged config is
  black. The project/slot source is not recoverable here; color did not affect
  this single-filament toolpath.
- Scalar/vector expansion and serialized newline/list formatting explain
  differences in junction-deviation, layer-change snippets, and thumbnails;
  they do not indicate edited behavior.
- The printer leaf contains a private print-host URL. Orca omits it from the
  embedded G-code config, and it has no slicing effect.

## Must transmit: smallest defensible runtime payload

For this exact workflow, the evidence favors a small request plus strict
artifact selection, not a large profile payload and not printer-side
reproduction of Orca slicing.

The minimum logical payload is:

1. immutable artifact ID and G-code SHA-256;
2. canonical effective-context fingerprint matching the artifact manifest;
3. originating Orca build and exact printer/process/filament display names for
   audit provenance;
4. calibration kind and result semantics: temperature tower and the exact
   layer/Z-to-commanded-temperature map, either inline or immutably referenced
   by the artifact manifest;
5. a schema/manifest version so both sides hash and interpret the same fields.

The raw process, printer, and filament JSONs do not need to travel at runtime.
Names alone are also insufficient because they are mutable and the current
plugin API exposes no durable preset ID. The trustworthy selector is a
canonical hash of effective values, backed by a human-readable manifest.

## Template compatibility and fingerprint

For now, the canonical compatibility projection should include:

- Orca/calibration generator revision and artifact hash;
- G-code flavor, required commands, start/end macro ABI, extrusion mode, and
  single-tool topology;
- nozzle diameter/material, filament diameter/type, allowed temperature range,
  and selected bed type/temperature;
- printable XYZ envelope and the artifact's actual move bounds;
- layer heights, line widths, flow ratio, wall/shell/infill topology;
- all material wall/solid/infill/bridge/travel speeds and accelerations;
- maximum volumetric speed;
- cooling ramp, bridge/overhang fan, and layer-time slowdown settings;
- retraction/wipe/Z-hop and pressure advance;
- the calibration object's fixed geometry, brim/skirt, and band map in the
  artifact manifest.

This is deliberately conservative. The list can shrink only after controlled
evidence shows a dimension does not alter executable output or calibration
validity.

## Baked into G-code

- complete XYZ/E paths and object placement;
- layer count/heights and extrusion widths;
- wall, shell, infill, bridge, brim, and skirt geometry;
- extrusion amounts after filament diameter and flow ratio;
- role feed rates and acceleration changes;
- volumetric-cap consequences;
- retraction, wipe, and absence of Z-hop;
- pressure-advance command;
- fan/cooling commands;
- complete temperature target schedule;
- relative extrusion and Klipper command syntax;
- start/end macro invocations and exclusion-object commands.

These values remain in the manifest for audit and compatibility, but are not
runtime controls once the exact artifact is chosen.

## Printer-side local

- physical printer/nozzle/tool and actually loaded filament identity;
- actual heater, bed, fan, motion, and volumetric capabilities;
- `PRINT_START`/`PRINT_END` definitions and whether startup waits for targets;
- homing, bed mesh, safety limits, shutdown behavior, and firmware clamps;
- support for Klipper-native pressure advance, velocity limit, and object
  exclusion commands;
- actual temperature telemetry and heater lag across non-waiting band changes;
- final authorization to run the artifact on the attached printer.

Orca's context is a claim about slicing intent; it is not physical attestation.

## Irrelevant to this workflow

- support/tree-support settings and their speeds;
- raft settings;
- prime/wipe-tower and multi-material purge settings;
- ironing;
- chamber control for this zero-chamber-temperature slice;
- timelapse, air filtration, drying, color, thumbnails, cost, notes, and
  print-host fields;
- unused plate-temperature presets;
- filament density except for mass/cost reporting.

## Open questions

1. What does the target printer's `PRINT_START` macro actually do, and does it
   wait for both 60/230 °C before returning?
2. How much does measured nozzle temperature lag the commanded `M104` target
   at each 10 mm boundary on this printer?
3. Which conservative fingerprint dimensions can be relaxed without changing
   executable G-code or measured calibration outcome?
4. Can a canonical effective-context projection be obtained reliably from the
   stock read-only plugin API for every required row, especially object-level
   calibration overrides?
5. Are physical range markings embedded in the tower, and can any future
   artifact vary its schedule without making those markings false?

## Recommended next experiment

Run one controlled, one-factor-at-a-time **reslice equivalence matrix** in the
same Orca build using these exact six profile JSONs and the same 230-190 °C
request. Capture the effective configuration and dirty state immediately before
and after invoking temperature calibration. Change one bucket-B dimension per
variant, then compare normalized executable G-code—not comments or metadata—by
category: geometry/E, feed rate, acceleration, fan, retraction, startup, and
temperature commands.

That single experiment gives the highest-value evidence for shrinking the
fingerprint: a dimension may be removed only if its controlled variant leaves
the relevant executable behavior and physical calibration interpretation
equivalent. No such new slices are generated as part of this research update.

## Issue #4 Windows qualification reconciliation

The fixed October 11 nightly qualified on Spare after the supported offline
bundle importer resolved the original printer's System-name collision. The six
supplied profile JSON files above remain unchanged. Original target context,
including saved 220 / unsaved edited 217 / merged 217, is retained separately
from temporary System context used for built-in Temperature preparation.

The normally prepared/manual export `temperature-qualified-230-190-step5.gcode`
is 3,619,569 bytes, SHA-256
`24594869ed17ec6d26c920ff684329c087487d20cbffddaf849c1afd4cdf271b`, with the
same nine 230–190 degree choices accepted by Helix. This newer qualification
artifact does not replace or reinterpret the September baseline above.
See [the complete Windows report](evidence/issue-4/windows/qualification.json).
