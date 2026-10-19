# Bounded Windows native package qualification

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

The externally reviewed manifest has exactly these 15 entries:

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
