-- SPDX-License-Identifier: GPL-3.0-or-later
-- Display-only adaptation of the HelixScreen beta.9 Calibration Bridge.
-- The agent event is the only entry point; subjects update one native overlay.

local EVENT_NAME = "helix_orca_display.available.v1"
local SCHEMA = "helix-orca-display/v1"
local MAX_CONTEXT_TEXT = 128
local MAX_FILE_BYTES = 64 * 1024 * 1024
local TEMPERATURES = {230, 225, 220, 215, 210, 205, 200, 195, 190}
local PAYLOAD_KEYS = {
    schema = true, display_only = true, request_id = true, file_sha256 = true,
    file = true, file_bytes = true, printer = true, filament = true,
    process = true, nozzle_mm = true, current_temperature_c = true,
    temperatures = true,
}

local receipt_line = helix.subject.string("receipt_line", "")
local printer_line = helix.subject.string("printer_line", "")
local filament_line = helix.subject.string("filament_line", "")
local process_line = helix.subject.string("process_line", "")
local file_line = helix.subject.string("file_line", "")
local hash_line = helix.subject.string("hash_line", "")
local temperatures_line = helix.subject.string("temperatures_line", "")
local effective_line = helix.subject.string("effective_line", "")

local overlay_handle = nil

local function exact_lower_hex(value, length)
    return type(value) == "string"
        and #value == length
        and value:match("^[0-9a-f]+$") ~= nil
end

local function bounded_text(value)
    return type(value) == "string"
        and #value > 0
        and #value <= MAX_CONTEXT_TEXT
        and value:find("%S") ~= nil
        and value:find("%c") == nil
end

local function valid_filename(value)
    return type(value) == "string"
        and #value > 6
        and #value <= 255
        and value:find("/", 1, true) == nil
        and value:find("\\", 1, true) == nil
        and value:find("..", 1, true) == nil
        and value:find("%c") == nil
        and value:match("%.gcode$") ~= nil
end

local function finite_number(value)
    return type(value) == "number"
        and value == value
        and value > -math.huge
        and value < math.huge
end

local function exact_temperatures(values)
    if type(values) ~= "table" or #values ~= #TEMPERATURES then
        return false
    end
    for i, expected in ipairs(TEMPERATURES) do
        local value = values[i]
        if type(value) ~= "number" or value ~= math.floor(value) or value ~= expected then
            return false
        end
    end
    return true
end

local function validate(data)
    if type(data) ~= "table" then
        return nil
    end
    local key_count = 0
    for key, _ in pairs(data) do
        if not PAYLOAD_KEYS[key] then
            return nil
        end
        key_count = key_count + 1
    end
    if key_count ~= 12
        or data.schema ~= SCHEMA
        or data.display_only ~= true
        or not exact_lower_hex(data.request_id, 32)
        or not exact_lower_hex(data.file_sha256, 64)
        or not valid_filename(data.file)
        or not finite_number(data.file_bytes)
        or data.file_bytes ~= math.floor(data.file_bytes)
        or data.file_bytes < 1
        or data.file_bytes > MAX_FILE_BYTES
        or not bounded_text(data.printer)
        or not bounded_text(data.filament)
        or not bounded_text(data.process)
        or not finite_number(data.nozzle_mm)
        or data.nozzle_mm < 0.05
        or data.nozzle_mm > 2
        or not finite_number(data.current_temperature_c)
        or data.current_temperature_c < 0
        or data.current_temperature_c > 500
        or not exact_temperatures(data.temperatures) then
        return nil
    end

    -- Copy every displayed value only after the complete event has passed.
    return {
        request_id = data.request_id,
        file_sha256 = data.file_sha256,
        file = data.file,
        file_bytes = data.file_bytes,
        printer = data.printer,
        filament = data.filament,
        process = data.process,
        nozzle_mm = data.nozzle_mm,
        current_temperature_c = data.current_temperature_c,
    }
end

local function on_overlay_closed()
    overlay_handle = nil
end

local function show_receipt(receipt)
    receipt_line:set("Receipt " .. receipt.request_id)
    printer_line:set(receipt.printer .. " \u{00B7} " .. tostring(receipt.nozzle_mm) .. " mm nozzle")
    filament_line:set(receipt.filament)
    process_line:set(receipt.process)
    effective_line:set("Original effective: " .. tostring(receipt.current_temperature_c) .. "\u{00B0}C")
    file_line:set(receipt.file .. " \u{00B7} " .. tostring(receipt.file_bytes) .. " bytes")
    hash_line:set("SHA-256 " .. receipt.file_sha256)
    temperatures_line:set("230\u{00B0}C \u{2192} 190\u{00B0}C \u{00B7} 5\u{00B0}C steps")

    if not overlay_handle then
        overlay_handle = helix.ui.overlay("helix-orca-display__receipt", {
            on_close = on_overlay_closed,
        })
    end
end

helix.moonraker.on_agent_event(EVENT_NAME, function(_, data)
    local receipt = validate(data)
    if receipt then
        show_receipt(receipt)
    end
end)

helix.ui.on("dismiss", function()
    if overlay_handle then
        overlay_handle.close()
    end
end)
