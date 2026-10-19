# Experimental downstream native adapter

This source uses exact October 15 internal C++ `Model`, `Cut`, `Flow`, `Print`
and calibration state; it does not modify Orca. Its Linux x86_64 executable and
actual capability command now build, but it remains **unqualified and blocked
on runtime configuration**. Do not infer working generation from compilation.

The intended CLI reads an immutable V1 request and complete effective context,
explicit pinned native resources and an existing empty output directory. It
contains Temperature standard tower, Retraction, Max Volumetric Speed and PA Pattern setup
for one non-belt nozzle. It rejects unavailable effective values, unsupported
external processing, out-of-volume geometry and overwritten artifacts. PA
Pattern uses the actual native pattern generator and per-plate custom G-code;
it currently requires Klipper because the context has no native vendor object.
Stock Flow YOLO preparation is
owned by the stock generation module. All artifacts remain unqualified until
mandatory independent native-UI parity; this file grants no physical action.

The registered executable target is Linux x86_64 ELF64. Its receipt is
unavailable on Windows; Windows needs its own real compatible audited build.
All 25 native dependencies and the real static engine/adapter now build. Actual
grouped generation exposed a shared enum-default deserialization crash before
G-code. Its source-backed fresh dynamic-config repair now passes full config
and model preparation. A subsequent native wait after model prep is being
localized with bounded phase diagnostics; no G-code has been generated yet.
Native export
also retains and checks processor errors/warnings, and a persistent TBB control
limits generation to two workers. Exact source/build receipts and actual failed
jobs are retained in the managed run evidence; no generated native calibration
or qualification is claimed yet.

Use `-DCMAKE_PROJECT_OrcaSlicer_INCLUDE=/absolute/path/add-target.cmake` on a
pinned Orca source root to add target `helix_orca_native` without editing that
root. This injection/build procedure still needs actual qualification.
