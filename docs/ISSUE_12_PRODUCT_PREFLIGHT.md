# Issue #12 AI Product Preflight

**PASS for the isolated native beta.9 flow and actual October 15 Windows
companion UI with a synthetic job.** No material UX defect remains in the
inspected final evidence. This is not hardware validation or Founder acceptance.

A separate reviewer inspected rendered native and Windows frames through the
complete request → Start → monitoring/cancel → completion → return journey.
The native source-bound verifier passes all eleven targets, 88 PNGs and eleven
storage snapshots. Beta.9 ran with `--test`, Docker `--network none`, read-only
runtime/plugin mounts and the private control socket. Authorization, clock,
job identity and completion inputs were synthetic; physical actions were zero.

| Step | Health and observation | Representative native evidence |
| --- | --- | --- |
| 1. Request received | **PASS.** “Not authorized… nothing started” is prominent; Start is absent. Original printer, filament, process, saved/edited/effective values and exact file remain visible. | [Received](evidence/issue-12/native/micro_480x272/received.png) |
| 2. Authorized/ready | **PASS.** Authorization, `210 / 205 / 200°C`, estimate and “Start here” make the distinct native action clear. Separators render correctly. | [Ready](evidence/issue-12/native/micro_portrait_272x480/ready.png) |
| 3. Printing/monitoring | **PASS.** Printing directs the person to the normal Helix Print screen for progress, states that results stay locked, retains file identity and exposes Cancel print. | [Printing](evidence/issue-12/native/medium_800x480/printing.png) |
| 4. Cancel confirmation/outcome | **PASS.** Native confirmation names the exact file, warns that no result will be available and identifies Back as keeping the print running. Cancelled clearly says result unavailable. | [Confirmation](evidence/issue-12/native/micro_480x272/cancel-confirmation.png), [cancelled](evidence/issue-12/native/micro_480x272/cancelled.png) |
| 5. Completion/selection | **PASS.** Independently confirmed synthetic success enables exactly three choices. The selected 205°C and Return selection are clear; failure/cancel paths stay locked. | [Completed](evidence/issue-12/native/medium_800x480/completed.png) |
| 6. Return/acknowledgement | **PASS.** Returning waits for Orca acknowledgement; the acknowledged state shows 205°C and repeats NOT APPLIED. Assertions cover waiting restart and exact ACK persistence. | [Returning](evidence/issue-12/native/medium_800x480/returning.png), [returned](evidence/issue-12/native/medium_800x480/returned.png) |
| 7. Originating Windows result | **PASS.** The actual 0.6 panel leads with NOT APPLIED, original profile/setting, original 220°C values, selected 205°C, unchanged current values and manual update steps. It explicitly states that the companion did not change Orca. | [Private-frame provenance](evidence/issue-12/windows-mock-roundtrip.json), [Windows qualification](ISSUE_12_WINDOWS_NATIVE_QUALIFICATION.md) |

The displayed **15-minute ready estimate is a synthetic fixture value** for UI
qualification. It is not a physical timing qualification. The actual native
export estimates 12 minutes; its combined printer-macro total remains unknown
and physical execution remains blocked.

The final exact Windows outbox also passed the complete native mock scenario
at 800×480. Its selected JSON equals the actual Windows committed inbox and
exact originating receipt, with the original target unchanged. The actual
Windows result-frame SHA-256 is
`c9074a513c599d2062d1f5393768859e4ad5629cd1283348a3cd480dccf1b75a`.
Raw Windows frames and payloads remain private. The accepted 0.5 companion and
five earlier communication artifacts were restored byte-for-byte afterward.

Reflow is clean in the inspected 480×272, 272×480, standard, phone-DPI, tall and
ultrawide frames. Status is communicated in text rather than color alone. The
inherited compact 26 px button token remains a non-blocking **physical touch
validation risk** at 480×272; this candidate does not redesign global tokens.
Screenshots do not establish keyboard/focus behavior, screen-reader output,
physical touch accuracy, or real-printer timing/performance.

[Complete native report](evidence/issue-12/native/report.json),
[engineering review](ISSUE_12_ENGINEERING_REVIEW.md) and
[physical-test readiness](TEMPERATURE_PRINT_READINESS.md) preserve the distinction
between isolated proof, remaining physical gates and separate Founder approval.
