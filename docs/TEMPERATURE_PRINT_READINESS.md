# First controlled physical Temperature test: readiness

Authority: [Issue #12](https://github.com/bigstupid007/helix-orca-calibration/issues/12)
and [Build Program](BUILD_PROGRAM_TEMPERATURE_PRINT.md). This is an isolated
candidate. No physical test is authorized, and no derivative is installed on
the printer.

## Disposition

**NOT READY for physical execution.** Native Orca preparation now produces the
required miniature, exactly three-band tower with a **12m00s model estimate**.
The printer's macro overhead, including cold startup and normal end behavior,
is not yet bounded; the combined
estimate therefore remains unavailable. The proposed first test must have a
qualified total estimate of **10–20 minutes, never above 1200 seconds**. The
coordinator cannot accept a qualification without that total. No live
qualification or Founder authorization grant has been issued.

The Founder reports **Elegoo Rapid PLA White**, normally **200°C nozzle / 60°C
bed**. Official [ELEGOO Rapid PLA+ family guidance](https://www.elegoo.com/en-gb/collections/elegoo-product-ex-s3-s4-m5/products/elegoo-rapid-pla-plus-filament-1-75mm-colored-1kg)
gives 200–230°C nozzle and 40–60°C bed. The illustrative **210 / 205 / 200°C**
bottom-to-top bands and 60°C bed fit those ranges and the selected PLA profile.
This is family guidance, not a captured exact-spool SKU label; check the actual
spool before a future authorized test. Successful machine completion also does
not establish band quality: the person makes that selection afterward.

## Actual native export

[Windows qualification](ISSUE_12_WINDOWS_NATIVE_QUALIFICATION.md) records the
preferred October 15 nightly `6a7763f08d1a175a464a00ce13f0b5a815662fc4`, native
Calibration → Temperature, Orca's bundled model, uniform native Scale at 70%,
unsaved 0.28 mm layer height and normal slicing/export. The machine start field
was corrected through Orca's native editor to match the existing printer macro;
all temporary edits were discarded without saving presets. No custom G-code
generator or exported-file editing was used.

| Check | Actual result |
| --- | --- |
| File | `temperature-miniature-210-200-step5-xy70-native-abi-12m00s.gcode` |
| Identity | 482357 bytes; SHA-256 `b576aa0aeb2236927899d60ed5bcb3d126a4cc6ed90ce8920bf6ac2c9054b0d8` |
| Geometry | 31.1494 × 7.00002 × 21 mm; 75 layers |
| Extruding bands | 210°C layers 1–25; 205°C 26–50; 200°C 51–75 |
| Band start heights | 0.20 / 7.20 / 14.20 mm |
| Motion envelope | X 131.866–172.149; Y 137.432–162.558; Z 0.20–21.32 mm |
| Native start | `PRINT_START BED_TEMP=60 EXTRUDER_TEMP=210`; no preceding heater wait |
| End | Native `PRINT_END` |
| Orca estimate | 720 seconds, 2.48 g; combined cold-start total **unqualified** |

[Independent byte inspection](evidence/issue-12/native-gcode-inspection.json)
checks actual temperature commands, extruding geometry, order, bounds, native
estimate and file identity. The original 25m17s slice is disqualified. An earlier
12-minute export with incompatible `EXTRUDER`/`BED` arguments is also rejected;
only the hash above has the correct native ABI. Raw G-code, runtime screenshots
and operational payloads remain private in XDG state.

## Bounded lifecycle candidate

Accepted Issue #8 communication and Issue #10 baseline policy remain preserved.
The physical-integration target remains October 15 nightly and beta.9
`e5cdc5dc523280bc3ead681a4f229bf84dfa726a`. Alpha remains an isolated secondary
target with no physical adoption.

- Separate generators derive a single-file Orca companion and storage-only
  Helix plugin from verified accepted source. The accepted implementation,
  beta.4 harness and normal profiles remain unchanged.
- Send creates only a request. Only explicit native screen Start persists its
  bound intent. A separate private Founder grant and local per-tap permit must
  also bind the request, qualification, file, physical machine, configuration
  and Moonraker version. The original Start window is at most 15 minutes.
- Ready requires the qualified combined estimate, current idle/ready state and
  empty queue. After native Start, dispatch additionally requires exact file-byte
  readback and a second fresh status sample. A durable intent precedes the single
  start command. Ambiguous commands are
  never retried, including after restart.
- RPC success does not confirm starting. The same newly running filename,
  job ID and start time must be observed and corroborated through history.
  Completion requires fresh `print_stats=complete` and that exact independent
  history job `status=completed`. History lag stays locked and nonterminal.
- Native Cancel opens a confirmation with exact file identity. Only a fresh
  check of the owned running job permits one cancel command. Cancellation,
  failure, disconnect, stale clocks, replacement or unexpected state cannot
  produce a result. Normal Helix Print remains the monitoring route.
- The picker enables only after independently confirmed success. The selected
  result carries job/proof identity. The original companion commits the result
  before acknowledgement; saved, edited and effective context remain distinct
  and instructions remain **NOT APPLIED**. Restart cannot redispatch Start or
  restore an unverified success; a committed waiting result can re-acknowledge.
- The real adapter defaults to actions disabled. The one-request runner
  defaults to offline preflight and requires explicit execution arguments plus
  the separate grant. This program has never invoked its execution mode,
  created a live permit, uploaded/queued a file or enabled hardware wiring.

## Read-only physical suitability

Bounded GET-only inspection through the existing trusted-LAN path confirms the
accepted Moonraker version, Klipper ready/standby, no homed axes, an empty
paused queue, history and a 0.4 mm nozzle. X/Y 0–300 and Z −5–290 mm contain the
exported motion. Acceleration commands are at or below configured 8000 mm/s²;
pressure advance is 0.035. Exclude-object, gantry-level support and the saved
60°C mesh selected by the existing start macro are present.
The exact MCU CAN identity plus host MACs bind the physical machine separately
from an Orca preset label; raw identities/configuration remain private.
[Sanitized findings](evidence/issue-12/read-only-suitability.json) publish no
address, credential or raw configuration.

The reviewed cold `PRINT_START` path preheats for probing, homes, waits for the
bed, levels the gantry, rehomes Z, loads the temperature-specific saved mesh,
waits for the hotend and runs adaptive purge. These are existing printer
behaviors; none was executed. Their duration and normal end-macro overhead must be conservatively bounded
within the remaining eight minutes or the proposal must be revised through
normal native preparation. No invented startup allowance is accepted. Retained history contains one
completed, substantially longer job with a different initial nozzle target;
it does not bind current macro timing or qualify this proposed total.

## Evidence and review

The native matrix uses pinned beta.9 `--test`, Docker `--network none`, read-only
runtime/plugin mounts and its private control socket. Request, authorization,
Moonraker clock/state, job identity and completion proof are labeled synthetic.
It exercises receipt lock, one native Start intent, duplicate prevention,
restart recovery, history lag, success-only three choices, 205°C return,
waiting restart/ACK, replay retirement and confirmed late cancellation. Native
frames do not prove physical transport, print execution or touch accuracy.
The exact actual Windows request also passed the final native mock at 800×480;
its 205°C result equals the committed Windows inbox and receipt, with original
220°C context and NOT APPLIED instructions.
[Sanitized round-trip provenance](evidence/issue-12/windows-mock-roundtrip.json)
records the private evidence hashes.

The normal entry remains Home tile → chooser → Temperature. The accepted
reserved port 8540 viewer is preserved; no new web app or service is introduced.
The complete source-bound beta.9 matrix passes all eleven targets: 88 frames
and eleven persisted storage snapshots. Its promoted evidence verifier passes.
[AI Product Preflight](ISSUE_12_PRODUCT_PREFLIGHT.md) passes for the isolated
native and actual Windows UI flow with synthetic job/completion inputs.
Physical touch accuracy, keyboard/screen-reader behavior and real-printer
timing/performance remain unproven. [Independent engineering review](ISSUE_12_ENGINEERING_REVIEW.md) passed the
frozen runtime at `0fe55cf`; all 230 tests pass. Engineering review and Product
Preflight do not constitute Founder acceptance.

```sh
python3 -m unittest discover -s tests -v
./scripts/helix-dev verify-evidence docs/evidence/issue-2/native
python3 scripts/temperature-communication-evidence.py verify docs/evidence/issue-8/native
python3 scripts/temperature-print-qualify.py verify docs/evidence/issue-12/native
git diff --check
```

## Gate before a later test

Present the exact export, suitable actual spool, reviewed commands/macros,
private machine/config/file binding and **qualified combined estimate ≤20 min**
to the Founder. Obtain separate explicit physical-test authorization before
installation/activation or any consequential printer action. Then require the
person's physical HelixScreen Start. Request receipt, recovery and a green
software suite never grant physical execution.

No writeback, custom generator, unrelated redesign, firmware/configuration
change, new exposure, Alpha adoption, merge, release or broader deployment is
included. The accepted HTTP trusted-LAN limitation persists: traffic lacks
per-message cryptographic authentication; correlation does not defend against
a malicious LAN participant. Private evidence and earlier accepted proof remain
preserved.
