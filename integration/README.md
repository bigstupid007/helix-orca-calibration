# Issue #4 native mock integration

This is a development-only adaptation of Preston Brown's native
[`calibration-bridge`](https://github.com/prestonbrown/helixscreen/tree/ed8d0c4977873969613fcb49024109ff7df7d84e/examples/plugins/calibration-bridge)
at `ed8d0c4977873969613fcb49024109ff7df7d84e`. The copied Lua, manifest, and
native overlay XML retain the explicit Start, print-state observer, picker,
result, and native navigation flow. Upstream is unchanged. These adapted files
are GPL-3.0-or-later; [COPYING](COPYING) retains the upstream license.

The accepted `helix-plugin/orcacal/` and ordinary `scripts/helix-dev` are
unchanged. Only `scripts/temperature-roundtrip.py` mounts this bridge beside
that plugin, in the same pinned beta.4 `--test`, `--network none`, read-only
container. No physical-printer route, upload, G-code generator, preset write,
or production integration exists.

Actual beta.4 lacks the newer example's `helix.i18n` binding. The adapter uses
English and the supported close callback to reopen an overlay after queued
navigation. It validates the mock marker, request/context/file correlation,
original profile identities, and the exact nine qualified Temperature choices.
The compact layout uses native vertical scrolling at all eleven target sizes.

Beta.4's HTTP backend refuses every loopback/local-interface destination to
protect the printer host. This guard remains intact. The proof therefore uses
**real artifact transport**, not HTTP: Orca explicitly exports its immutable
request beneath host-owned plugin storage; the existing pinned SSH testing
route transfers the JSON and unchanged G-code bytes to devbox. The driver
validates both digests and seeds native bridge plugin storage. Native
`helix.storage.get("request")` receives the request, and
`helix.storage.set("result", …)` writes the correlated result atomically.
The driver extracts that native result, then the same SSH route returns its
bytes for explicit Orca selection. Receiving a request only opens the bridge;
a visible native Start is required.

The failure run starts with missing request delivery. After native failure is
visible, the driver delivers the real artifact and hot-reloads the private
bridge copy to clear beta.4's storage cache. It makes only that run's private
plugin-data directory temporarily non-writable for the first result attempt,
restores it, and retries Next with the same ID and selection. It never changes
normal settings or permissions. Tests simulate progress/completion through
beta.4's private native subjects after the real mock Start publishes printing.
Native pointer input starts the mock; native LVGL dropdown/value and click
events select/return the result while the mock is frozen for reproducible
capture. Freeze occurs before remote pointer creation; its later-created sampler stays
live while the test clock remains parked. No product code
uses these controls.

Use the operator commands and retained evidence in
[Temperature round-trip proof](../docs/TEMPERATURE_ROUND_TRIP.md).


Founder Review repair preserves ordinary native Home/Back. The proof seeds a
native **Mock Temperature** resume tile and restores the stock print-status
card on Home. The tile reopens retained available/printing/choice/result state;
it does not modify the accepted Orca Calibration tile. The proof uses the
native track grid for its orientation, with a card that fits the portrait grid.

A prominent responsive viewer **Finish simulated print** control is available
immediately after Start. The resumed native calibration has the same control;
it writes a bounded native-storage action with request ID and sequence. Only
the owned mock driver consumes it, checks identity/started state, and simulates
completion. Duplicate actions are idempotent, and Cancel/completion is honored.
No production printer command, navigation override or Settings recovery is used.
