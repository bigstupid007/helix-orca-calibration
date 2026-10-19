# Bounded Windows native package qualification

<!-- v1-generator-current -->
Current generation candidate: [`c0fa61d` Windows build 39255585408](https://github.com/bigstupid007/helix-orca-calibration/actions/runs/39255585408)
completed successfully. Actual SPARE execution of the unchanged `exact-executable-v1`
harness qualifies Temperature, PA Pattern, Retraction and Max Volumetric Speed for
the retained explicit unsaved 50°C context and exact parameters. Their executable
streams match native UI references: **106,508 / 2,904 / 16,585 / 35,672 commands**,
with zero mismatches and both invariant sets passing. Both qualified YOLO modes
retain their separate original-context qualification.

Four fresh native 800×480 Helix sessions independently reach actual Windows
Coordinator Prepared with exact request/readback values, real generation and parity;
no Cancel, Confirm or Start is sent. Normal Orca's **1,429-file fingerprint is unchanged**.
All verified controls, ordinary coordination and the accepted physical Temperature
baseline remain intact. [Exact results and limits](V1_GENERATOR_BLOCKER_CHECKPOINT.md#current-r2-generation-and-prepared-candidate),
[parity receipts](evidence/issue-14/generator-blockers/native-four-windows-parity-r2.json),
[native Prepared evidence](evidence/issue-14/generator-blockers/native-prepared-ui-r2.json).

Qualification covers these exact contexts/origins/profiles/parameters only. The
original 60°C bed / 55°C filament threshold remains unsupported; the actual PA
negative still reports `native_warning` / `1000C001` before reference selection.
No warning suppression, profile writeback, new physical test, printer deployment
or merge occurred. Hardware, production security and complete corresponding-source
acceptance remain separate limitations; PR #15 stays draft and unmerged.
<!-- /v1-generator-current -->


The historical MSVC `227b447` package and its PA-only pass remain retained
alongside the failed Temperature motion and Retraction/MVS object-name comparisons.
The current Clang package independently passes all four complete harnesses; no old
qualification flag carries forward. [Causal history and exact current scope](V1_GENERATOR_BLOCKER_CHECKPOINT.md#current-r2-generation-and-prepared-candidate).

The validator recognizes historical MSVC v1 and compiler-aligned Clang v2
receipt schemas. Actual dispatch also requires every owned build input to match
the current source. The retained MSVC package `227b447` therefore remains historical
evidence and is not dispatchable under the current source; its PA qualification
does not carry forward. A v2 package requires actual Windows PE/DLL execution,
consistent probe/dependency/engine compiler evidence and its own unchanged
whole-harness comparison for every exact input. Changing schema or compiler
never inherits an old qualification flag.


`scripts/v1-windows-native-qualify.py` is a separate acceptance driver for PA
Pattern, Retraction, Max Volumetric Speed and native Temperature. It invokes the
actual `integration.v1_engine._backend` and `generate` paths. It does not alter
profiles, ignore warnings, produce simulated G-code, print or deploy anything.
The existing YOLO and Temperature stock helpers and protected mesh bundle are
unchanged. Native Temperature uses the adapter's real Cut and transient mode;
it does not consume the separate STL experiment.

Use a fresh source-only tree, an existing isolated Windows native package, the
independently captured complete context and genuine native GUI exports/evidence.
The original saved profiles stay unchanged. An explicitly prepared unsaved
context is a different supported-input candidate and must retain its own hash,
UI evidence and native exports. In particular, the original 60°C bed / 55°C
vitrification context remains blocked by native warning `1000C001`; using an
independently captured deliberate 50°C edit does not qualify or rewrite that
original context.

## Reviewed source closure

The externally reviewed manifest has exactly these 18 entries:

- `integration/v1-native-engine/windows-target.cmake`
- `integration/v1-native-engine/windows-cmake/FindEXPAT.cmake`
- `integration/v1_windows_dependencies.py`
- `integration/v1_contract.py`
- `integration/v1_parity.py`
- `integration/v1_engine.py`
- `integration/v1_pe.py`
- `integration/v1-native-dependencies.json`
- `integration/v1-native-engine/main.cpp`
- `integration/v1-native-engine/add-target.cmake`
- `integration/v1-native-engine/temperature_prepare.hpp`
- `integration/v1-native-build-tools.py`
- `scripts/v1-engine-native.py`
- `integration/v1-native-windows-dependencies.json`
- `scripts/v1-engine-windows.py`
- `.github/workflows/v1-windows-engine.yml`
- `scripts/v1-windows-native-qualify.py`
- `scripts/v1-windows-parity.py`

Use the existing manifest shape:
`{"schema":"helix-orca-v1-reviewed-python-source/v1","files":{"relative/path":"expected_sha256",...}}`.
Its exact byte SHA-256 comes from the lead's reviewed public-source bundle and
must be passed separately. Expected pins are never replaced with observations
from the Windows target. Native source/build files above are required because
`_backend` checks them causally against the audited package's owned-input
receipt. Runtime Python executes only contract, parity, engine, PE inspection,
this driver and the existing sanitized parity reporter.

The standard-library bootstrap runs before any owned import, rejects extra
files/directories, symlinks/reparse components and bytecode, and compiles only
captured verified source bytes. Native package files, profiles, context,
evidence and output all stay outside the source tree. Both source and complete
input closure are rechecked after generation and sanitization and before any
published scalar result. The receipt-bound DLL import closure and all native
resource hashes are revalidated as well.

## Register genuine native references

`--register-native-only` needs no executable or package. It calls the original
`v1_parity.create_native_reference` and `invariants`, using the explicitly
hash-pinned context, selected parameters, native G-code and at least two
distinct pinned native UI PNGs. The context becomes a separate third evidence
item. It writes a private `native-reference.json`, full inspection and scalar
summary. Registration always reports `qualified:false` and `prepared:false`;
it cannot qualify a generated candidate.

```text
python.exe -I -S -B SOURCE/scripts/v1-windows-native-qualify.py
  --register-native-only --calibration pressure_advance_pattern
  --source-manifest REVIEWED_JSON --source-manifest-sha256 REVIEWED_SHA256
  --context NATIVE_CONTEXT_JSON --context-sha256 EXACT_CONTEXT_FILE_SHA256
  --parameters SELECTED_PARAMETERS_JSON --parameters-sha256 PARAMETERS_FILE_SHA256
  --native NATIVE_GUI_GCODE --native-sha256 NATIVE_GCODE_SHA256
  --native-evidence DIALOG_PNG --native-evidence-sha256 DIALOG_SHA256
  --native-evidence EXPORT_PNG --native-evidence-sha256 EXPORT_SHA256
  --output-dir NEW_PRIVATE_REGISTRATION_DIRECTORY
```

The same command supports `retraction`, `max_volumetric_speed` and `temperature`
with their own exact parameters and independent GUI exports. No parameter,
profile, nozzle or context fallback is performed.

## Generate and compare the real Windows package

Use the shared context/parameter/native pins above, replace registration mode
with the package and registered native-manifest arguments, and choose a fresh
private output directory:

```text
python.exe -I -S -B SOURCE/scripts/v1-windows-native-qualify.py
  --calibration retraction
  --source-manifest REVIEWED_JSON --source-manifest-sha256 REVIEWED_SHA256
  --context NATIVE_CONTEXT_JSON --context-sha256 EXACT_CONTEXT_FILE_SHA256
  --parameters SELECTED_PARAMETERS_JSON --parameters-sha256 PARAMETERS_FILE_SHA256
  --native NATIVE_GUI_GCODE --native-sha256 NATIVE_GCODE_SHA256
  --native-manifest REGISTERED_REFERENCE_JSON --native-manifest-sha256 REFERENCE_FILE_SHA256
  --native-executable NATIVE_PACKAGE_EXE --native-executable-sha256 EXE_SHA256
  --build-receipt PACKAGE_RECEIPT_JSON --build-receipt-sha256 RECEIPT_FILE_SHA256
  --build-inputs PACKAGE_INPUTS_JSON --build-inputs-sha256 INPUTS_FILE_SHA256
  --resources EXACT_PACKAGE_RESOURCES --application-commit EXPECTED_PACKAGE_COMMIT
  --timeout-seconds 120 --output-dir NEW_PRIVATE_GENERATION_DIRECTORY
```

The executable must pass the real Windows AMD64 PE/import-closure, source,
builder, toolchain and resource receipt checks. There is no runner argument or
path guessing. The native generation deadline is bounded to 1–120 seconds.

Actual warnings remain fatal. A warning or native execution blocker retains the
exact request, complete local diagnostic, any generated artifact and the native
false parity disposition. Only fixed codes, validated warning information,
digests and selected parameters appear in `blocked-summary.json` and stdout.
No Prepared job or qualification is claimed for that rejection.

A successful native generation still needs the unchanged independent
`exact-executable-v1` parity harness. The driver rechecks actual artifact bytes,
prepared request/parameters, report digest and `verify_report` before reporting
qualification. Executable differences produce a false summary and exit 2;
actual strict qualification exits 0. Full profiles, G-code, evidence images,
processing data and reports remain local. Sanitized summaries never establish
printer hardware, macro internals or physical readiness.

## Native-only exact-input reference catalog

One trusted native configuration can now hold up to 64 independent reference
pairs under `native_references`. Each dictionary key must be the full lowercase
SHA-256 of the unchanged `v1_parity.generation_inputs(request, context,
source_commit)` object. Each value has exactly the existing pinned `manifest`
and `gcode` records, with only `path` and `sha256` in each file record. A private
catalog file contains that dictionary directly; the runtime configuration stores
the same dictionary inside `native_engine.native_references`.

The generator selects only an exact key after real native execution and
processor validation. It does not select by calibration name alone, choose a
nearby parameter range, fall back to another profile/reference, rewrite a
manifest or substitute values. Catalog lookup never establishes qualification:
the same executable comparison and mandatory native invariant checks remain.
Actual slicer warnings, including `1000C001`, remain the first blocker even when
the catalog lacks a matching key. Missing references retain the actual generated
artifact and a false parity report with a specific missing-reference message.

The legacy `native_reference` single-pair configuration remains supported.
Supplying both `native_reference` and `native_references` is rejected. Empty
catalogs are valid and qualify nothing. Malformed keys, extra entry fields,
unpinned file records and catalogs larger than 64 entries are rejected.

For actual Windows qualification, add both flags to the generation command:

```text
--native-catalog PRIVATE_CATALOG_JSON
--native-catalog-sha256 EXPECTED_CATALOG_FILE_SHA256
```

The current case's explicit `--native-manifest`, `--native` and their expected
hashes remain required for independent checking. A matching catalog entry must
be exactly that checked pair. A missing catalog key is allowed to reach actual
generation so it cannot mask native warnings; it then reports unqualified with
`native_reference_missing`. The driver pins every catalog file and referenced
manifest/G-code pair, including unselected entries, and rechecks them after
generation and sanitization. It writes the catalog's expected digest into scalar
provenance. Registration mode does not accept catalog flags.

This supports automatic selection among the four retained exact native cases
without test-worker reconfiguration. It does **not** qualify ordinary newly
captured contexts. The current context digest includes `origin_id`; restoring
identical profiles after changing selection or settings creates a fresh origin
and therefore a different exact key. Saved/edited names, every serialized
configuration value, effective settings, runtime, nozzle, selected parameters
and source pin also remain exact. Neither origin equivalence nor profile-only
reference reuse is implemented. A fresh origin remains explicitly unsupported
until its own independent matching native evidence is registered under the
unchanged policy. The accepted physical Temperature evidence, YOLO routes,
contracts, UI and correlation behavior are unchanged.


## Target path limitation

Current retained Windows qualification paths are ASCII. The small adapter uses
narrow `main` arguments and has not reproduced the GUI entry point's explicit
wide-argument/Nowide filesystem initialization. Non-ASCII Windows job/resource
paths therefore remain unsupported pending implementation and independent target
proof; success on the retained paths does not establish Unicode path support.
This limitation does not change or waive any exact context/parameter parity gate.
