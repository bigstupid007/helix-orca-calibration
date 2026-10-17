# Issue #12 Windows native miniature qualification

Status: **Founder correction in progress; corrected native export and companion round trip pending the existing Spare worker restart**.

No printer request, upload, heating, motion, queue operation, or other printer
action was performed during this review. The raw G-code and screenshots remain
private evidence; this document contains only the bounded findings needed for
review.

## Current Founder correction

The Founder superseded the earlier illustrative range and duration policy. The
current native Temperature calibration must contain exactly three bands,
ordered bottom to top as `225 C`, `220 C`, and `215 C`. The normal filament
temperature is confirmed as `220 C`. There is no hard 20-minute limit, no
combined slicer-plus-printer-macro duration qualification, and no spool-label
checkpoint in this corrected scope.

The corrected investigation retains Orca's native Temperature calibration,
fixed `5 C` step, bundled `temperature_tower.drc`, normal slice/export path,
`0.28 mm` layers, and native uniform `70%` scale. The selected printer's start
G-code remains changed only in memory to:

```gcode
PRINT_START BED_TEMP=[bed_temperature_initial_layer_single] EXTRUDER_TEMP=[nozzle_temperature_initial_layer]
```

Before the access interruption, actual October 15 Orca showed the corrected
`225 C` start and `215 C` end in its native dialog, transferred the unsaved
machine-start value into a newly generated native calibration project, and
accepted the retained layer-height input. The scale input was issued, but the
devbox evidence volume then filled and ended the one-shot approved Spare worker
before Scale Done, Slice, or Export could be independently confirmed. Space was
later recovered losslessly by replacing a temporary duplicate with a link to
its identical retained cache file. The storage incident is now resolved, with 358.6 GiB available on resume;
[bounded headroom checks](BUILD_PROGRAM_TEMPERATURE_PRINT.md#resumed-validation--2026-10-17)
continue around export/capture. The documented existing worker still requires
its owner-only unelevated restart. The isolated Orca session remains
the intended recovery point. No alternate access route will be created.

Consequently, this document does not yet claim a corrected G-code identity,
hash, estimate, geometry, temperature-command distribution, or completed
`0.6.1` companion round trip. Those values will be recorded only from the
fresh native export after the same approved worker reconnects. The planned
companion proof keeps the original saved/edited/effective `220 C` context,
selects the corrected file, sends only a local readiness request, and returns
an explicitly synthetic native-mock `220 C` selection to Orca as **NOT
APPLIED**. It authorizes no physical action.

The pre-correction profile baseline is private evidence under the Windows
access state. It records `1429` normal profile/configuration files with
aggregate SHA-256
`41100c88a1cc27e23747ecb9db25a91c621a04b3dc359a5f64e0df5b8d6a9c19`,
and `38` isolated-datadir files with aggregate SHA-256
`4f91294290543807185c0460e2ce8e153cb351014dce8f1317d8f8e25107fafa`.
The accepted companion and communication artifacts will be rechecked after
the corrected export and round trip.

## Superseded historical qualification

The earlier 210/205/200°C investigation, 0.6.0/205°C mock result, old timing
gates and former label assumption are preserved verbatim in
[the historical qualification record](evidence/issue-12/history/candidate-68d1029/ORIGINAL_WINDOWS_NATIVE_QUALIFICATION.txt)
and original Git commit `68d1029`. They do not govern or qualify this corrected
candidate. [Historical provenance](evidence/issue-12/history/candidate-68d1029/windows-mock-roundtrip.json)
continues to bind that earlier mock proof without relabeling it as current.
