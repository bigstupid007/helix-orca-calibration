# Issue #2 native harness evidence

Status: candidate evidence captured 2026-10-11 UTC from the canonical devbox
checkout. This directory is a bounded promotion from retained capture
`20261010-223015` beneath the harness's durable XDG state directory.

## Exact runtime

- HelixScreen `v1.1.0-beta.4`, source commit
  `13a77bec42616d5c6f4fa397f1d5e12682fa4376`
- Binary origin: forced local build of that exact public source and all 14
  superproject-pinned recursive submodule revisions, using builder recipe
  SHA-256 `988ad9478d513731680bf7c0b0e41ee639d0ac9d776aa15ef369fb9029c9d40e`
- Source-built binary SHA-256
  `29dbb6f32b26561b781522991279bf6f31d6acc4230f4bb6ac0cc9d6947ffcb4`
- Release-data SHA-256
  `a0a618c2ab233e61324ec1024448571b160a8bd65b22b0387007017f4dc21b94`
- Local runtime image ID
  `sha256:88e1d3fb6dbd3b7a1c7dfb57c7a2fbc5522c01473bf7c964509e8672ab3d7e35`
- Local builder image ID
  `sha256:f67960f55aa1b7cfa8af41bd89943b13730b791ce55e1925bc575d5eef89f6d9`
- Runtime posture: exact-source developer binary, `--test`, SDL dummy renderer,
  Docker `--network none`, read-only container and plugin/runtime mounts,
  private Unix control socket

[`native/report.json`](native/report.json) contains the exact runtime metadata,
capture-time harness/CI hashes, assertion results, 44 transient screenshot
hashes, and before/after product hashes. Its repository HEAD is the clean base
commit because the candidate was intentionally captured before commit; the
candidate file hashes are the binding authority. [`native/matrix.tsv`](native/matrix.tsv)
records all eleven passing targets. [`native/promotion.json`](native/promotion.json)
binds the full report to that candidate and every promoted frame.

## Flow result

### Founder Review defect and repair

The rejected candidate registered the tile but seeded it on physical Home page
1 with `main_page_index: 1`. Beta.4 initially honored that retained value, but
its normal Home action always navigated the carousel to physical page 0. The
old validator then hid the defect by finding an off-screen widget and invoking
its callback by object name.

The repaired harness normalizes retained mock configuration to one physical
page (`main`, index 0), places `orcacal__tile` there, and explicitly disables
the beta.4 stock default widgets that would otherwise be appended ahead of it.
It acknowledges the four devices built into the beta.4 mock printer so the
unrelated eight-second hardware-discovery toast cannot intercept the initial
tap at compact sizes. Product files and behavior are unchanged.

At each target the native driver proved:

1. beta.4 discovers and loads enabled plugin `orcacal`;
2. the actual landing state is Home with no navigation overlay, and the entire
   tile is inside the visible viewport;
3. a screen-coordinate pointer press/release on the visible tile opens
   `orcacal__wizard`;
4. the chooser owns native Back and a visible pointer tap opens Temperature;
5. plugin descendants have no horizontal viewport overflow;
6. native scroll makes Start visible where required, and a visible pointer tap
   emits the exact toast `Calibration request test`;
7. Back returns Temperature -> chooser -> Home;
8. Helix's normal Home action keeps the tile on the visible landing page; and
9. another visible pointer tap reopens the chooser.

The 22 PNGs in [`native/screenshots/landing/`](native/screenshots/landing/) and
[`native/screenshots/start-toast/`](native/screenshots/start-toast/) retain the
actual initial Home frame and final Start/toast frame from each target. Visual
inspection covered the two minimum geometries, default, high-DPI phone,
ultrawide, and narrow-tall targets. The landing set shows the tile immediately,
without another page or covering toast; the final set retains the accepted
Helix navigation, dark tokens, compact cards, typography, range, and Start-only
detail.

## Interactive and remote proof

The final interactive path passed:

```text
native Home tile -> chooser -> Temperature -> Start toast -> Back -> Back
```

The viewer and capture driver use the same beta.4 synthetic pointer
`press`/`release` path; native overlay state and the runtime log confirmed each
transition and callback. No object-name `click` command is used for the tile,
Temperature row, or Start button. `./scripts/helix-dev reload` independently
observed `PluginDirWatcher` and a second `[PluginHost] orcacal: loaded` event
without restarting Helix or changing a product file.

Trusted-LAN port `8540` was reserved before bind through shared Development
System PR
[`cdemichael/100-day-development-system#105`](https://github.com/cdemichael/100-day-development-system/pull/105),
merged as `de8d7a66e58aca81fc9b44cda6a6463ffcea47ff`.

After rechecking the authorized Mac mini ED25519 fingerprint
`SHA256:t2CldNhULUtJKegIU6nal5EWBmwb3FIcaUBRtw+tcXA`, read-only GETs from
`dev@192.168.1.122` returned:

```text
http://192.168.1.114:8540/           200, 2563 bytes
http://192.168.1.114:8540/health     200, 47 bytes
http://192.168.1.114:8540/frame.png  200, 4385 bytes
```

Initial `/api/status` reported Home with `overlays: []`. The same independent
client then posted a native tap at `200,63`; `/api/status` reported
`overlays: ["orcacal__wizard"]`. Its bounded Back and normal Home actions
returned the stack to `overlays: []`, and the resulting native frame still
showed the tile. This proves off-box view and normal interaction, not only a
host-local HTTP route.

No public exposure, firewall, DNS, TLS, printer, or Moonraker change was made.

## Reproduce

```sh
./scripts/helix-dev bootstrap
./scripts/helix-dev doctor
./scripts/helix-dev capture
./scripts/helix-dev verify-evidence docs/evidence/issue-2/native
```

Then compare the generated `matrix.tsv`, `report.json`, and hashes. See
[`../../HELIX_DEV_HARNESS.md`](../../HELIX_DEV_HARNESS.md) for the complete
operator contract. The full generated configs, runtime logs, chooser/
Temperature intermediate frames, and cache artifacts remain outside Git by
default; only the proportionate landing and Start/toast review evidence is
promoted here.

## Test-count audit

- Issue #1 exact commit: 7 committed Helix plugin tests.
- Issue #1 reported working tree: 25 = those 7 plus 18 unrelated uncommitted
  Orca diagnostic tests.
- Issue #2 candidate: 22 committed tests = 7 product-policy plus 15 harness.
- Current dirty canonical working tree: 40 = candidate 22 plus the same 18
  unrelated uncommitted Orca tests.

The correction changes evidence provenance only; it does not change Issue #1's
accepted runtime result.
