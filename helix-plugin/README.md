# HelixScreen Orca Calibration plugin

`orcacal/` is the native HelixScreen Issue #1 candidate. It targets the stock
Lua plugin framework introduced in `v1.1.0-beta.4` and requests no permissions.

The implemented flow is intentionally small:

`home tile -> calibration chooser -> Temperature detail`

The chooser shows the hard-coded development context in a compact two-line card
above the calibration list and exposes only Temperature. The detail shows
`230°C -> 190°C`; **Start** displays the native toast
`Calibration request test`. Moonraker integration, G-code, printing, results,
storage, networking, and Orca writeback are not present.

This chooser/detail shell is the baseline for later calibration modules. A
future module extends the local registry and supplies its own plugin-owned
native detail component; it does not replace Helix navigation or invent another
application shell.

## Test locally

The canonical devbox path uses the repository-owned real beta.4 mock harness:

```sh
./scripts/helix-dev bootstrap  # first setup only
./scripts/helix-dev up
./scripts/helix-dev status
```

Open `http://192.168.1.114:8540/`. The tile must already be visible on the
initial Home screen; tap it directly, select **Temperature**, tap **Start**,
and confirm the toast reads `Calibration request test`. Plugin saves hot-reload
in about one second. Use `./scripts/helix-dev down` when done, or
`./scripts/helix-dev capture` for the complete eleven-target gate. See
[`../docs/HELIX_DEV_HARNESS.md`](../docs/HELIX_DEV_HARNESS.md).

With another verified HelixScreen `v1.1.0-beta.4` developer build, the direct
upstream invocation remains:

```sh
HELIX_PLUGIN_DIR="$PWD/helix-plugin" \
  /path/to/helix-screen --test --skip-wizard --dark -vv
```

In HelixScreen:

1. Open **Settings > Plugins > Orca Calibration** and enable it.
2. Add **Orca Calibration** from the home panel's Plugins widget category.
3. Tap the tile, select **Temperature**, and tap **Start**.
4. Confirm the toast reads `Calibration request test` and native Back returns
   first to the chooser, then Home.

Run the repository policy tests with:

```sh
python3 -m unittest discover -s tests -v
```

The current `references/helixscreen` checkout predates the Lua framework. The
source/runtime authority, supported viewport matrix, and native acceptance are
recorded in [`CAPABILITY_PREFLIGHT.md`](CAPABILITY_PREFLIGHT.md) and
[`PREFLIGHT.md`](PREFLIGHT.md).

## Install on a printer

Copy the complete `orcacal` folder to:

```text
printer_data/config/helixscreen/plugins/orcacal/
```

HelixScreen mirrors plugin changes without a restart, but never enables or
places a new plugin automatically. Enable it under **Settings > Plugins**, then
add its tile from the home panel.
