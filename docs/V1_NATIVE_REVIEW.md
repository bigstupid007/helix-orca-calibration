# Bounded V1 native interactive review

This derivative viewer presents actual pinned beta.9 Helix pixels and forwards
native pointer/Home/Back input. Its external preparation, parity, print and
receipt statuses are fixed synthetic qualification fixtures. The conspicuous
`SYNTHETIC ONLY` viewer heading remains visible above the native frame. No real
printer, generator, runtime job adapter or physical action is connected. This
viewer does not qualify generator parity or physical readiness.

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
configure its supported native parameters, and request preparation. Fixed mock
preparation reaches Review. Confirm the job in native Helix, then deliberately
press native Start separately. Only now is the browser's **Finish simulated
print** control enabled. Finish the simulation, choose the result in native
Helix, Return result, inspect Returned / NOT APPLIED, and dismiss with Done.
Temperature preserves its accepted automatic presentation; the other kinds
refresh their owned job view and support manual reopen. Home/Back remain native
navigation; drag the native frame to scroll. Save capture retains at most 32
manual frames in the private managed artifacts.

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

Thirteen focused dependency-free checks pass. Actual viewer lifecycle/browser
qualification must follow the frozen full native matrix and the queued engine
diagnostic; no listener was started while the matrix was active. This document
will be updated with the resulting managed proof before claiming that check.
