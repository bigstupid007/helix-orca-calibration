# Issue #12 Windows native miniature qualification

Status: **qualified as an offline native Orca artifact; physical start remains blocked**.

No printer request, upload, heating, motion, queue operation, or other printer
action was performed during this review. The raw G-code and screenshots remain
private evidence; this document contains only the bounded findings needed for
review.

## Runtime and method

- OrcaSlicer: preferred October 15 nightly, isolated runtime label `6a7763f`,
  executable SHA-256
  `e2b6da4c20e7080eade97379f326dcfcaa90f1ecb9991f1db9eb61e3065a9759`.
- Native path: **Calibration > Temperature**, PLA, start `210 C`, end `200 C`,
  step `5 C`; Orca's bundled `temperature_tower.drc`; normal Slice plate and
  Export G-code file actions. No custom generator or exported-file edit was
  used.
- Original context retained: printer parent
  `Voron Voron 2.4 300 0.4 nozzle`, process
  `Voron 0.20 Standard - Fast Quality`, filament
  `Generic PLA - Voron Rapido - Initial`, nozzle `0.4 mm`.
- Temporary project-only changes: layer height `0.28 mm`, initial layer
  `0.20 mm`, and Orca's native uniform Scale tool at `70%`.
- The selected printer parent's stock start G-code has an incompatible
  `PRINT_START EXTRUDER=... BED=...` call. For this investigation only, its
  native Machine start G-code field was changed in memory to
  `PRINT_START BED_TEMP=[bed_temperature_initial_layer_single]
  EXTRUDER_TEMP=[nozzle_temperature_initial_layer]`. Orca transferred that
  unsaved value into the generated calibration project. It was never saved to
  a preset.

The reviewed source path fixes Temperature calibration at 5-degree steps,
crops the bundled model from the selected start and end values, and emits a
temperature command from the calibration parameters on each layer. Runtime
G-code inspection independently confirmed the result below.

## Candidate result

| Property | Qualified value |
| --- | --- |
| Private artifact identity | `temperature-miniature-210-200-step5-xy70-native-abi-12m00s.gcode` |
| Bytes | `482357` |
| SHA-256 | `b576aa0aeb2236927899d60ed5bcb3d126a4cc6ed90ce8920bf6ac2c9054b0d8` |
| Orca estimate | `12m 0s` |
| Filament estimate | `2.48 g` |
| Model geometry | `31.1494 x 7.00002 x 21 mm`, uniform 70% scale |
| Declared build volume | `300 x 300 x 290 mm` |
| Parsed motion bounds | X `131.866..172.149`, Y `137.432..162.558`, Z through `21.32` |
| Layers | `75`; first `0.20 mm`, remaining nominally `0.28 mm`, last model layer Z `20.92` |
| Band 1 | layers 1-25, `M104 S210`, starts Z `0.20` |
| Band 2 | layers 26-50, `M104 S205`, starts Z `7.20` |
| Band 3 | layers 51-75, `M104 S200`, starts Z `14.20` |

The executable start is:

```gcode
EXCLUDE_OBJECT_DEFINE ...
M73 P0 R12
PRINT_START BED_TEMP=60 EXTRUDER_TEMP=210
```

There is no `M190` or `M109` before `PRINT_START`. The executable end contains
one `PRINT_END`. Other nonstandard commands are `EXCLUDE_OBJECT_START`,
`EXCLUDE_OBJECT_END`, `SET_PRESSURE_ADVANCE`, and `SET_VELOCITY_LIMIT`; the
physical configuration review must continue to bind all of them to the target
before authorization.

The embedded filament type is PLA and its profile range is `190..240 C`, so
all three illustrative values are inside the profile's declared range and are
ordered hot-to-cool from bottom to top. The Founder identified the loaded
material as Elegoo Rapid PLA White, normally used at `200 C` nozzle and `60 C`
bed. A separate product-family review found official Rapid PLA+ guidance of
`200..230 C` nozzle and `40..60 C` bed. The proposed `210/205/200 C` tower and
`60 C` bed fit that guidance; exact-spool confirmation remains part of the
physical pre-start check because the family guidance is not a captured spool
SKU label.

## Rejections and remaining gate

The unscaled native tower at the original `0.20 mm` layer height estimated
`25m 17s` and is rejected by the 20-minute limit. A prior uniformly scaled
12-minute export is also rejected because it retained the incompatible
`PRINT_START EXTRUDER=210 BED=60` call after explicit `M190` and `M109`
commands. Only the candidate hash above has the corrected native macro call.

The `12m 0s` value is Orca's model-print estimate. It does not establish the
physical cold-start wall time for homing, bed heating, gantry leveling, mesh
loading, nozzle heating, or the printer-side purge. The candidate must remain
fail-closed until the physical review either bounds that macro overhead such
that total estimated duration is at most 20 minutes or provides a qualified
total estimate by another accepted method. A real print must not start when
the qualified total exceeds 20 minutes.

Before any physical authorization, also verify the loaded spool, exact file
bytes and SHA-256, target printer/nozzle/build volume, accepted macro command
surface, ready/standby state, empty queue, and the separately reviewed Helix
explicit-start lifecycle. Any mismatch disqualifies the file.

## Preservation

After export, Orca's native prompts were used to discard the project and every
temporary layer-height, filament-temperature, and machine-start-G-code edit.
The session returned to an empty `Untitled` project showing saved `0.20 mm`
and `220 C` values.

The normal Orca profile fingerprint was identical before and after: `1429`
configuration files with aggregate SHA-256
`41100c88a1cc27e23747ecb9db25a91c621a04b3dc359a5f64e0df5b8d6a9c19`.
The final isolated-datadir write inventory contained only `OrcaSlicer.conf`
and `OrcaSlicer.conf.bak`; no profile JSON was written. The accepted plugin,
communication state, mock harness, firmware, and printer configuration were
not changed.

## Actual companion round trip in the isolated nightly

The separate nightly-only `0.6.0` companion candidate, SHA-256
`b6cce1ab22ac92af611cf7f74930560de160e1e53e19bbfc8785cf96ffe6dd15`,
was staged after a bytewise backup of the installed accepted `0.5.0`
companion and all five accepted communication artifacts. Orca's native Plugins
manager showed the candidate as local, activated, and version `0.6.0`.

In the actual October 15 Orca panel, **Keep original profile** retained the
saved, edited, and effective values as `220 C`. The native file picker selected
the candidate G-code above, and the panel independently reproduced its byte
count and SHA-256. **Send request** created one new local `print-readiness`
outbox and state file. The visible status said the request was ready for
delivery, no print had started, and no profile had changed. No delivery status
or lifecycle transition was seeded in the Windows storage.

That exact outbox was exercised by the network-disabled native mock at
`800x480`. Its exact correlated, explicitly synthetic result selected `205 C`
and included mock job/completion proof. Returning that JSON unchanged to the
actual Windows inbox produced an actual Orca **NOT APPLIED** result panel. It
showed the original `220 C` values, selected `205 C`, current unchanged
`220 C`, and the existing manual Orca update instructions. Windows persisted
the exact result in its state and wrote the exact correlated acknowledgement.
This proves the candidate's local Windows -> native mock -> Windows result
path; the synthetic completion value is not physical completion evidence and
does not authorize hardware operation.

The result-frame SHA-256 is
`c9074a513c599d2062d1f5393768859e4ad5629cd1283348a3cd480dccf1b75a`.
Raw frames and JSON remain private evidence. A later, unrelated
cancellation/restart case in the same private driver run hit a test-harness
storage-flush timing assertion, so this result capture does not claim that the
complete private driver suite passed.

After capture, all candidate readiness artifacts were transferred to private
evidence and removed from the isolated datadir. The byte-identical accepted
`0.5.0` companion was restored at SHA-256
`bc3d35eb260a1360e1095bd97d8e7d31e3ab96e8b3cafde1f145e3adf5b4d71f`;
the native Plugins manager again showed local, activated version `0.5.0`.
Every accepted communication artifact retained its pre-stage SHA-256, the
temporary backup was removed after verification, and the normal profile
fingerprint remained unchanged.
