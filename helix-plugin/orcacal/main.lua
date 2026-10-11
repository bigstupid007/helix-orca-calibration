-- SPDX-License-Identifier: GPL-3.0-or-later
-- Issue #1 keeps the visible product inside Helix's native overlay stack.

local CALIBRATIONS = {
    temperature = {
        component = "orcacal__temperature",
    },
}

helix.ui.on("open", function()
    helix.ui.overlay("orcacal__wizard")
end)

helix.ui.on("select", function(id)
    local calibration = CALIBRATIONS[id]
    if calibration then
        helix.ui.overlay(calibration.component)
    end
end)

helix.ui.on("start", function()
    helix.ui.toast("Calibration request test")
end)
