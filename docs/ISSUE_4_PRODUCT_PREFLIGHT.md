# Issue #4 consolidated Founder Review repair

Status: focused repair validation and lead AI Product Preflight pass; independent
re-review is pending at the frozen boundary. PR #5 remains open and unmerged. The
Founder rejected the earlier candidate's navigation and simulated completion.
That report supersedes the earlier clean AI preflight. No Founder acceptance
is claimed. Windows qualification is complete and was not restarted.

## Defect closure ledger and diagnosis

The reported experience was a roughly 55-minute simulated print with no
obvious Finish, loss of the active task after Home, and a viewer that did not
feel like normal Helix. The repair base is
`69e5d4ac016a11b2042d8c63ddf044bc4b8c9262`.

| Founder defect | Verified cause | Exact acceptance proof |
| --- | --- | --- |
| Finish unavailable or undiscoverable | The earlier fresh viewer contained a small Finish button. Narrow browser controls overflowed; the owner's exact missing-button/session cause is unconfirmed. | Fresh browser Start immediately enables prominent Finish at 375/640/1280 pixels; Finish reaches native choices without waiting. A native Finish is also available after returning to the calibration. |
| Home loses the active task | Native Home correctly clears overlays. The isolated proof disabled the stock print card and had no calibration resume widget. | Native Home retains state and exposes Mock Temperature plus the stock active-print card. Card returns to Print Status; Back returns normally; tile resumes printing, choices and result. No Settings recovery. |
| Completion/navigation becomes inconsistent | Setting complete subjects left the synthetic simulator running. Its next snapshot could publish printing again and reopen Print Status. | The proof parks its clock before remote input is created. Complete remains stable through Home/Back, native dropdown/Next and result resume. |

Source inspection used exact pinned Helix `13a77bec…`, including native
navigation, widget configuration/grid placement, remote freeze/pointer handling
and the mock backend. No upstream navigation defect or patch is claimed.

## Repair and focused convergence

The separate proof now seeds a native Mock Temperature return tile and the
stock print-status card. The accepted Orca Calibration tile/chooser/detail is
unchanged. Home/Back remain native actions; the viewer does not trap or reroute
Home. Tile status identifies the retained task stage.

Finish is prominent above the native frame and inside the printing calibration.
The native callback writes a bounded request-ID/sequence action. The owned
mock driver validates identity and started state, and consumes it once.
An already completed/cancelled task takes precedence. The same guard serves the
viewer button. No physical printer command or route is added.

The responsive viewer avoids narrow-browser control overflow, labels the mock
boundary, and reloads updated pages when candidate identity changes. Founder
handoff uses a fresh page. The normal viewer/harness remains unchanged.

Focused failures during repair exposed portrait track remapping, a wrong stock
card selector, queued navigation timing, simulator rollback, and an entry animation interrupted by freeze. Those were
corrected at their causal boundaries. Review startup now requires a stable
native entry frame before parking its clock. A browser coordinate check initially
reported success after selecting 220°C; visual inspection caught that false
positive. The corrected check awaits each real input response and validates the
exact correlated terminal 205°C artifact as well as its visible frame. In particular, empty grid coordinates
were rejected by beta.4 configuration loading; orientation-tagged native track
layouts now fit portrait. These are recorded repair iterations, not another
Windows qualification or a new certification workstream.

The existing native test freeze parks simulation and pre-existing periodic
timers before the remote pointer is created. Remote pointer sampling, native
navigation/update queues and rendering remain live. Animations are disabled;
this is an explicit mock-review limitation. No upstream binary change, security
change, new port, or new remote-access mechanism is involved.

## Candidate and retained evidence

The exact runtime source hashes and executed binary are bound by
[`evidence/issue-4/roundtrip/report.json`](evidence/issue-4/roundtrip/report.json).
The actually qualified Orca plugin remains `0.4.0`, SHA `fd4d37b5…`.
Helix source remains `13a77bec…` and the executed source-built binary remains
`29dbb6f3…`; the optional Actions binary was not executed.

Original request `f4a33a9c526e24c63c2d653fc51cfb0c` retains the real Windows
export and original profile context. Saved **220°C**, edited **217°C** and
effective **217°C** remain distinct. The retained native result is **205°C**,
with original-profile **NOT APPLIED** instructions. Existing Windows
profile-switch/stale/duplicate/conflicting-result evidence remains applicable
because the Orca plugin, request, export and result contract are unchanged.

## Validation and review gate

The lead's focused AI Product Preflight used the actual browser/native surface
from two fresh runtime/browser sessions. Toolbar Finish worked directly after
native Start. The second path used native Home, the stock active-print card,
Back, the Mock Temperature return tile and its native Finish. Both reached
205°C through native dropdown/drag/Next, retained that result after Home, and
validated the exact correlated result artifact. Actual terminal frames were
visually inspected; the first false-positive 220°C run is excluded.

Finish is fully visible with no horizontal control overflow at browser widths
375, 640 and 1280. No browser page errors occurred. Spare independently read
back the updated LAN viewer (HTTP 200, Finish/Home present, matching candidate
version) through the existing unelevated SSH worker. No new access mechanism
or exposure was required.

The bounded [browser proof](evidence/issue-4/roundtrip/browser/report.json)
binds source hashes, browser driver/image, fresh contexts, viewport checks,
actual 205°C selections and promoted before/after frames. The lead inspected
normal Home composition, the native Finish, choices and the visible not-applied
result against the accepted native shell. The complete thirteen-phase,
eleven-target matrix is bound to the final startup/control sources. All 75
dependency-free tests, static checks, evidence integrity and whitespace checks
pass. Independent re-review follows this frozen candidate.
The exact final PR head and CI disposition are recorded in Issue #4.

Preservation: main remains `8e093c19…`; the canonical unrelated tracked-diff
fingerprint remains `d4cf0158…`. The recorded post-round-trip check matched all
1,429 normal Orca settings/profile files. This repair has made no Windows
installation/profile changes. Helix remains `--test`, Docker `--network none`,
with read-only runtime/product/bridge/G-code mounts and a private control socket.
OSS account/remote safeguards remain mandatory for GitHub mutations.

## Founder Review handoff

Follow [the tested short walkthrough](TEMPERATURE_ROUND_TRIP.md#working-review-path)
using a fresh private LAN viewer page and the retained isolated Orca companion
on Spare. Unlock Spare if its desktop is locked; no security bypass is part of
this workflow. Review immediate Finish, normal Home/Back return, 205 selection
and the visible original-profile not-applied result. Physical printers, profile
application, picker expansion, release and merge remain excluded.
