# Experimental downstream native adapter

This source uses exact October 15 internal C++ `Model`, `Cut`, `Flow`, `Print`
and calibration state; it does not modify Orca. It is **uncompiled and
unqualified**. Do not advertise generator availability from the source file.
The separate native static dependency build must pass before target injection
and an incremental adapter build are attempted.

The intended CLI reads an immutable V1 request and complete effective context,
explicit pinned native resources and an existing empty output directory. It
contains Temperature standard tower, Retraction and Max Volumetric Speed setup
for one non-belt nozzle. It rejects unavailable effective values, unsupported
external processing, out-of-volume geometry and overwritten artifacts. PA
Pattern remains an explicit missing route, and stock Flow YOLO preparation is
owned by the stock generation module. All artifacts remain unqualified until
mandatory independent native-UI parity; this file grants no physical action.

Use `-DCMAKE_PROJECT_OrcaSlicer_INCLUDE=/absolute/path/add-target.cmake` on a
pinned Orca source root to add target `helix_orca_native` without editing that
root. This injection/build procedure still needs actual qualification.
