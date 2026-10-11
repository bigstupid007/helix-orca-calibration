# Concept

## Product direction

Orca Calibration is a native HelixScreen calibration launcher. Temperature is
the first module and the only module currently exposed. Issue #1 proves the
reusable chooser/detail structure inside the real stock plugin framework; it
does not pretend that calibration execution exists.

The separately installed OrcaSlicer Python plugin remains a read-only context
and diagnostic research tool. It is not the Issue #1 application shell and is
not connected to HelixScreen.

## Current Helix journey

1. The user adds **Orca Calibration** from Helix's Plugins widget catalog.
2. Tapping the tile pushes the native **Orca Calibration** chooser overlay.
3. The chooser shows the fixed development printer, nozzle, filament, and
   process context in a compact two-line card and one available calibration,
   Temperature. The calibration list is the dominant content.
4. Tapping Temperature pushes its native detail overlay.
5. The detail shows `230°C -> 190°C`. **Start** displays
   `Calibration request test` and performs no external action.
6. Helix's inherited Back control returns to the chooser and then Home.

This is intentionally the product's smallest honest state. The registry and
detail component boundary can support later modules, but the UI shows no future
cards, stages, or controls until they have real behavior. Future modules extend
this accepted chooser/detail baseline rather than reinterpret the shell.

## Visual and interaction rule

The plugin must read as part of HelixScreen: Helix owns global navigation,
overlay headers, Back behavior, colors, spacing, typography, cards, icons, and
responsive breakpoints. The plugin does not draw an application sidebar,
workspace toolbar, or web dashboard inside that shell.

## Non-goals

- Moonraker coordination or any network transport.
- G-code generation, modification, slicing, upload, or execution.
- Print start, monitoring, results, or scoring.
- Generate/Run/Result stage simulations.
- Orca preset mutation or writeback.
- Placeholder calibration modules.
- Upstream Orca, HelixScreen, Moonraker, or Klipper patches.
