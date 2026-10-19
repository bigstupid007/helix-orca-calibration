# Temperature native geometry parity investigation

The October 15 Windows native reference remains the independent authority:
230→190°C, fixed 5°C step, resize enabled, retained original context
`3bf24bab6c2ac71cf7c0017d8889d4430006d3cd489a512ff656990f41324b3c`.
Its G-code is `512eb13a80788bd22f928b1b073382070a7c43b5c667efd08ffcc05e550e29b7`.
The native project and executable output remain private and unchanged.

The former stock candidate cut the decoded native asset with Python trimesh
and Earcut. Native Orca instead uses `Slic3r::Cut::perform_with_plane()` via
`Plater::cut_horizontal()` (pinned `Plater.cpp:17047`). Its upper and lower
planes are exactly `((500-end)/5+1)*10-EPSILON` and
`((500-start)/5)*10+EPSILON`, with native `EPSILON=1e-4`. The Python candidate
had 27,280 triangles including four exact degenerates; the genuine native
project has 27,238 and zero. Their extrusion, path and acceleration differences
remain material under the unchanged `exact-executable-v1` policy.

The stock CLI does not provide an equivalent cut operation. At pinned
`src/OrcaSlicer.cpp:5056–5103`, the recognized cut/cut_x/cut_y branch has its
implementation commented out. Selecting that option is not native preparation.

The bounded repair experiment uses the existing source-pinned grouped native
adapter solely to prepare its native Cut/scale geometry, then supplies that
independently generated mesh to the actual Windows stock CLI. It reuses the
same native GUI G-code reference, not a native export reused as both candidate
and reference. The separate `--prepare-temperature` mode exits before `Print`
construction, slicing, post-processing or G-code export. No native warning is
suppressed; the ordinary stock slicing and mandatory independent parity gates
still decide whether an executable output qualifies.

`integration/v1-native-engine/temperature_prepare.hpp` writes a new binary STL
and a scalar preparation report. Final instance X/Y bed placement is excluded
from the STL to avoid unnecessary bed-coordinate float rounding; the normal
stock CLI arranges the model. Native plane cuts, volume transformations,
nozzle scale and instance Z placement remain. Flattened STL can itself cause
rounding differences: actual native comparison is required, and a failing STL
experiment must not be labeled qualified. A transform-preserving native 3MF
would be the next source-backed investigation if necessary.

`integration/v1_temperature_geometry.py` verifies the real source-bound native
build receipt, exact request/context identity, authoritative single nozzle,
explicit non-belt state, successful process exit, absence of G-code/Prepared,
exact returned parameters, and independently inspected finite nondegenerate
STL bytes. It writes `geometry-receipt.json` with model and build digests and
`temperature-model.json` with the existing stock recipe's exact model pin.
Original context, saved/edited profiles and custom hooks remain private and
unchanged. The descriptor does not qualify slicing or authorize printing.

Development invocation, inside the lead's existing bounded resource lifecycle:

```sh
python3 scripts/v1-temperature-geometry.py \
  --request /private/new-temperature-request.json \
  --context /private/original-context.json \
  --config /private/native-build-config.json \
  --output /private/new-temperature-preparation
```

The native build configuration is the existing trusted `native_engine` object,
not UI-supplied paths or commands. A production coordinator may use the same
preparation module; no test worker or GUI automation is required by the module.
Only public-source geometry and scalar provenance may cross the approved
qualification boundary. Full profiles/configuration remain on their original
private host. The existing stock recipe accepts the returned exact
`temperature_model` descriptor; its parity remains mandatory for that exact
source/runtime/context/nozzle/range/scale combination.

Focused preparation tests use a plainly synthetic tetrahedron to test rejection
and provenance handling; those bytes are never native calibration evidence.
Actual preparation/slicing/parity results will be recorded by the lead after
one serialized native rebuild and the retained Windows reference comparison.
The accepted physical Temperature baseline remains untouched.

## Bounded Windows production comparison

The separate `scripts/v1-windows-temperature-native-geometry.py` helper runs
only the real existing `integration.v1_generation.generate` stock path. It
accepts the exact native-prepared STL and its hash-bound geometry receipt,
checks the retained original context and October 15 executable, and rechecks
all distinct native-UI reference evidence. Initially it supports only the
retained 230→190°C / 5°C / resize-enabled / 0.4 mm combination. A different
range, context, nozzle, model digest or reference is rejected explicitly.

The source-only Windows staging closure is exactly:

- `integration/v1_contract.py`
- `integration/v1_generation.py`
- `integration/v1_parity.py`
- `integration/v1_engine.py`
- `integration/v1_temperature_geometry.py`
- `scripts/v1-windows-temperature-native-geometry.py`
- `scripts/v1-windows-parity.py`

In addition to these public sources, stage only the newly native-prepared public
tower geometry and its scalar geometry receipt. The original complete context,
native G-code, native manifest and UI evidence remain on Windows. For example,
with every path beneath the existing isolated qualification root:

```text
python.exe -I -S scripts/v1-windows-temperature-native-geometry.py
  --context ORIGINAL_CONTEXT --executable OCT15_EXECUTABLE
  --model NATIVE_PREPARED_STL --model-sha256 EXACT_MODEL_SHA256
  --geometry-receipt GEOMETRY_RECEIPT
  --geometry-receipt-sha256 EXACT_RECEIPT_SHA256
  --native RETAINED_NATIVE_GCODE
  --native-sha256 512eb13a80788bd22f928b1b073382070a7c43b5c667efd08ffcc05e550e29b7
  --native-manifest RETAINED_NATIVE_MANIFEST
  --native-manifest-sha256 EXACT_NATIVE_MANIFEST_FILE_SHA256
  --output-dir NEW_LOCAL_JOB
```

The slicing deadline is 45 seconds. There is no runner argument, network route,
GUI automation, profile writeback or physical action. Actual stock slicer
warnings remain fatal under the existing generator's checks. An unqualified
comparison retains its full false report and preparation locally, writes a
controlled scalar summary through the existing Windows parity sanitizer, and
exits 2. Zero means strict parity qualified that exact retained combination;
neither disposition claims printer hardware or macro-internal readiness.
