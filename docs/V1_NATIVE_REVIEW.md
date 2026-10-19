# Bounded V1 native interactive review

The viewer presents actual pinned beta.9 Helix pixels and forwards native
pointer/Home/Back input. Its default now uses the real V1 Coordinator, routing,
and DirectoryEvents journal, with no configured generator or printer adapter.
Choose and edit every calibration, request preparation, and inspect the genuine
unavailable-generator message. Exact native requests are retained unchanged in
transport and coordinator traces. The viewer cannot manufacture a Prepared job,
completion or qualification. The former synthetic full-workflow capture below
is historical evidence only.

The default profile context is explicitly synthetic. To use an existing captured
Orca context, pass `--context /absolute/private/context.json`; it stays outside the
container mount and normal profile storage is never read or changed. This is
an offline transport review, not production deployment or physical readiness.

From this checkout, after every capture/build has released the shared resource
gate, launch one foreground review:

```sh
python3 scripts/v1-native-review.py launch
```

Open `http://192.168.1.114:8540` on the existing private development LAN. This is
the existing reserved viewer address and port; no wildcard/public bind or port
option exists. The session lasts at most 900 seconds including setup/cleanup;
the interactive window reserves 20 seconds within that budget. A shorter
`--seconds 60..900` can be supplied. Do not launch a second heavy runtime while
this foreground command owns the shared lifecycle gate.

Tap the compact Orca Calibration tile. Choose any of the five calibrations,
edit the native numeric fields through their keypad, select either YOLO mode,
and request preparation. Drag the native frame to scroll; numeric entry and
Set use the same native pointer path. The real coordinator retains the selected
values and reports its actual capability blocker. Confirm and Start remain
inaccessible without a genuinely parity-qualified prepared job. No simulated
finish control exists. Home/Back use native navigation. Save capture retains
at most32 manual frames in the private managed artifacts.

Read-only `/api/geometry`, `/api/subject`, and `/api/parameter-state` expose
calibration geometry, displayed subjects, and exact request/coordination traces
for independent operator proof. They cannot edit parameters or issue actions.

From another terminal in the same checkout:

```sh
python3 scripts/v1-native-review.py status
python3 scripts/v1-native-review.py stop
```

Stop validates the owner-private retained session, exact managed app/repository,
artifact inode and exact owned container label, then writes only that run's
schema/run-ID stop record. The foreground owner closes its listener normally;
ManagedRun retires exactly its own runtime and verifies the baseline inventory.
No broad signals or name-based deletion are used. Ctrl-C remains subject to the
same ManagedRun ownership and teardown controls.

The wrapper reuses the accepted pixel viewer HTML and source-verified private
beta.9 input socket, without changing the accepted harness. It verifies the reviewed shared ManagedRun helper (4a42a94; SHA-256
`8a2cb48220f14c8f4ca5c2cc9f6fcdcdf28fa436fe4b7dd50cf6489178ba6fcc`)
lazily before actual lifecycle operations (pure controls and test imports need
no devbox helper), and retains it with pinned runtime/fixture/source inventories; mounts runtime/plugin read-only; uses
`--test`, Docker `--network none`, no published container ports, a private
control socket, 2 CPU, 512 MiB RAM, 128 PIDs and bounded logs. ManagedRun requires
5 GiB disk reserve plus a 512 MiB peak and 512 MiB margin. The new session,
source/fixture inventories (including the owner-private file validator), manifests, snapshots and captures remain in XDG
state; managed manifests and the shared gate always follow the verified helper
ROOT even when a viewer XDG override is present. Generated fixture plugins remain in the existing user cache.

HTTP actions are a fixed typed allowlist, bounded to the 800×480 native frame.
The wrapper validates the exact LAN Host, rejects foreign Origins and requires
a random per-session token on each mutation. Every response sends
`X-Frame-Options: DENY` and CSP `frame-ancestors 'none'` to prevent framed native
input. It has no CORS, arbitrary command,
RPC, G-code, profile/configuration update or production activation endpoint.
Malformed input fails closed. If a pointer press may have applied before an
RPC failure, the wrapper makes one bounded release attempt on a fresh private
socket and preserves the original error. Deployment authorization and the ordinary Windows
coordinator remain separate, default-off product/runtime work.

Twelve focused dependency-free review checks pass, including actual coordinator
request retention and archive tracing.

Historical synthetic qualification run
`d7c80433b4a74a44aede3ae9567ef7e8` passed after the full 396-frame matrix and
engine cleanup released the resource gate. Chromium 140.0.7339.186 with
Playwright 1.64.1 used a fresh isolated profile and actual native browser pointer
input: Generate, Confirm, deliberate Start, simulated completion, Return result,
NOT APPLIED receipt, Done, Home and Back. Finish remained disabled before Start.
Nine synchronized full browser frames and zero page errors are retained in the
[interactive evidence](evidence/issue-14/interactive-review/report.json).

Live bad Host, foreign Origin, missing token, unsupported command and out-of-range
pointer requests all returned 400 with frame protection. Exact nonce-bound Stop
then exited 0, closed the listener and retired the owned container; runtime clear
and verification errors `[]` were checked against the full private manifest. The
browser closed with zero remaining processes carrying its unique profile.
Source closure is `247f3b462d34b70c18be3647f2e1e2a72fcf6727167cc14c9e3978eb24666119`.
Full inventories remain private.

The cached browser initially lacked desktop shared libraries. Fourteen public
Ubuntu packages (under 1 MiB compressed) were extracted only into an owned user
cache and passed to that browser through its child environment; no system
installation or maintainer script ran. Package and browser hashes are retained.
Earlier failed setup records remain private. An earlier passed workflow had
immediate screenshots ahead of the periodic image refresh; the final evidence
recheck explicitly awaited fresh frames and the native Returned label. No product
source changed for that capture correction. The normal viewer operation above
does not depend on the qualification browser/library bundle.
