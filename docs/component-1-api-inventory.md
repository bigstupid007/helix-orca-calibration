# Component 1 — read-only Orca API inventory

## Status and boundary

Implementation has executed in the actual fixed Windows runtime on Spare.
The complete Issue #4 qualification passed with retained saved/edited/effective
values and the original printer leaf imported through Orca's supported offline
local bundle namespace. See [the Windows report](evidence/issue-4/windows/qualification.json). Issue #4 supersedes the earlier runtime
target with the fixed Windows x64 OrcaSlicer `2.5.0-dev` nightly at build
`210bc927`, source commit `210bc927bc6fb3d3bf390fdf72e4a2767b5de4b3`.

This is a diagnostic inventory, not a production payload or an architecture
decision. It does not read Orca profile/config files or the baseline G-code at
runtime. It does not use networking, printer access, subprocesses, background
threads, slicing, slicing hooks, preset/project mutation, Helix, or Moonraker.

Current qualification candidate plugin version: `0.3.0`

Install file:

```text
/home/dev/Projects/personal/helix-orca-calibration/plugin/helix_calibration.py
```

SHA-256:

```text
c7b908e8e175088f6f9aeedcbd1a841a996f49c6c315c966b02bd686436ca9d4
```

This hash must be checked again if the plugin file changes.

## Implemented action

**Export Orca Context JSON** is a normal
`orca.script.ScriptPluginCapabilityBase` action. Its `execute()` method:

1. reads the supported host APIs synchronously;
2. builds one in-memory, JSON-compatible snapshot;
3. asks `orca.host.plugin.storage()` for this plugin's storage directory;
4. creates an `exports` child directory; and
5. writes one timestamped UTF-8 JSON file.

No filesystem operation occurs in a WebView callback. `PluginHost.cpp` requires
`plugin.storage()` to run inside a plugin callback. `PluginManager.cpp` maps it
to `{data_dir}/orca_plugins/plugin_data/{plugin_key}`, and
`PluginAuditManager.cpp` explicitly permits reads/writes below the Orca data
tree. A denied or failed write returns a recoverable action failure; it is not
bypassed.

For the installed filename `helix_calibration.py`, the local plugin key is
`helix_calibration`, so the output pattern is:

```text
<Orca data directory>\orca_plugins\plugin_data\helix_calibration\exports\orca-context-YYYYMMDDTHHMMSS.ffffffZ.json
```

Orca uses an executable-adjacent `data_dir` folder when one exists. Otherwise
Windows uses the OrcaSlicer user-data directory under `%APPDATA%`, unless Orca
was launched with a `--datadir` override. The successful action message prints
the exact path used by the running process and is authoritative.

## Snapshot sources

Each configuration source remains separate and has its own namespace,
association, key-enumeration outcome, enumerable-key count, per-status counts,
and entry list. Each entry records the exact Orca key, raw value returned by the
binding, read status, and any failure/redaction reason.

The action attempts:

- printer `selected_preset()` and `edited_preset()` independently;
- process `selected_preset()` and `edited_preset()` independently;
- the filament collection's single selected/edited editor pair;
- every ordered name from `current_filament_preset_names()` paired by index with
  `current_filament_presets()`;
- every key from `PresetBundle.full_config_keys()` via
  `full_config_value()`;
- every object and volume config override through `config_keys()` and
  `config_value()`;
- live model identity/counts/paint flags/current plate index;
- object, instance, volume, and one-based volume-extruder associations without
  exporting mesh arrays;
- Plater project/preset dirty state and snapshot-capture state; and
- the supported application-language accessor.

The raw preset/config binding serializes a present Orca config option with
`opt_serialize()` and returns Python `None` when absent. The exporter does not
parse vectors, percentages, placeholders, or G-code text and does not replace
missing values with defaults or profile-file data. Empty strings, multiline
text, Unicode, zero, false, and null remain distinct in the JSON data model.

Preset filesystem paths and model input paths are omitted explicitly. Known
password, token, secret, API-key, and path-bearing configuration keys remain
enumerated but carry `intentionally_omitted_or_redacted`, a null raw value, and
a reason. Inactive preset collections, mesh arrays, and toolpaths are not bulk
exported.

## Filament association semantics

The pinned host exposes only one filament `PresetCollection` selected/edited
pair. It separately exposes an ordered vector of selected slot names and an
ordered vector of resolved current preset objects. In the C++ implementation,
the latter resolves each name through `PresetCollection.find_preset()`; that
function returns the edited temporary copy when the name is the collection's
active preset.

The export therefore does not label each slot as independently edited or as a
raw saved leaf. It records the positional pairing and classifies the
collection-edited name association as:

- a unique name match;
- ambiguous because the same preset occupies multiple slots; or
- not established for that slot.

Count mismatches and unresolved entries remain visible.

## G-code and template fields

The report explicitly checks these keys across all enumerated sources:

- `machine_start_gcode`
- `machine_end_gcode`
- `filament_start_gcode`
- `filament_end_gcode`
- `before_layer_change_gcode`
- `layer_change_gcode`
- `change_filament_gcode`

It also lists every other discovered key containing `gcode` or `template`.
Returned text remains unchanged in the corresponding raw config entry. A
separate interpretation section reports placeholder/expression markers and
line-leading firmware-macro *candidates*. Those tokens are only candidates:
the action does not read firmware configuration, expand templates, produce
G-code, or prove printer-start behavior.

## Source-verified limitations

The exact pinned bindings establish the following limits:

- `PresetBundle.full_config()` is a current merged configuration, but the
  exporter does not call it the complete final sliced configuration.
- Project settings can contribute to that merged config, but no standalone
  project-config accessor is bound.
- `Model.current_plate_index()` is available. No plate object, plate preset
  collection, or plate-settings config accessor is bound.
- `ModelVolume.extruder_id()` and ordered filament slots are available. No
  broader authoritative tool-association accessor is bound.
- The enum contains `PhysicalPrinter`, but `PresetBundle` exposes no physical
  printer collection or selected physical-printer accessor. Non-secret
  connection-related values can still appear among merged enumerable config
  keys; credentials are redacted.
- No calibration-state accessor is present in the inspected script, app,
  preset, or model bindings.
- `Print`, `PrintObject`, `PrintRegion`, layers, toolpaths, export target/path,
  and export-time config are available only to slicing-pipeline callbacks. This
  action does not register a hook or trigger slicing merely to reach them.
- A script capability's `execute()` gets no `PluginContext`, and `orca.host`
  exposes no app version/build accessor. The snapshot records the target build
  as supplied test configuration and says so explicitly.
- `ModelInstance.is_printable()` is documented as set during slicing, so the
  script records the phase limitation instead of presenting it as live truth.

These are source findings, not Windows runtime acceptance. A missing value in a
particular export is not treated as proof that an API is missing, and an
exception is recorded as a failed read rather than “unsupported.”

## Non-GUI verification

Dependency-free synthetic tests cover:

- enumeration and per-source counts;
- exact raw values, including Unicode and multiline G-code;
- saved-versus-edited separation;
- ordered multi-filament associations;
- absent values and individual key failures;
- valid UTF-8 JSON output and write failures;
- credential/path redaction;
- synchronous host-storage export and capability registration; and
- preservation of the accepted initial HTML and Refresh behavior.

Run:

```sh
python3 -m unittest discover -s tests -v
```

Mocks and source inspection do not establish runtime acceptance.

## Windows installation and export

The Issue #4 launcher verifies the exact nightly executable/DLL hashes, stages
this plugin in a separate `--datadir`, and prints the authoritative paths and
hashes. Follow the complete interactive checklist in
[`ORCA_NIGHTLY_QUALIFICATION.md`](ORCA_NIGHTLY_QUALIFICATION.md). It covers the
original effective value, a real unsaved edit, both JSON exports, the host-owned
panel, lifecycle events, normal Temperature preparation, and manual G-code
export without selecting a physical printer or changing the existing Orca
installation.

## Removal and cleanup

1. Close any Helix Calibration window.
2. In Orca's Plugins dialog, use **Delete** on **Helix Calibration Context**.
   This removes the installed plugin package.
3. Close Orca.
4. If the private diagnostics should also be removed, delete only the exact
   `plugin_data\helix_calibration` directory reported by the export path. Orca's
   package-delete path does not remove this separate storage directory.
5. Keep or delete the original downloaded `.py` file separately. No preset or
   project cleanup is required because the exporter is read-only.
