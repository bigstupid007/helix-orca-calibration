-- SPDX-License-Identifier: GPL-3.0-or-later
-- Issue #8 beta.9 extension. This file is appended to a byte-verified copy of
-- the accepted OrcaCal main.lua; the accepted plugin remains unchanged.

local TEMPERATURE_REQUEST_EVENT = "helix_orca_temperature.request.v1"
local TEMPERATURE_ACK_EVENT = "helix_orca_temperature.ack.v1"
local REQUEST_SCHEMA = "helix-orca-temperature-session/v1"
local RESULT_SCHEMA = "helix-orca-temperature-selection/v1"
local ACK_SCHEMA = "helix-orca-temperature-ack/v1"
local TEMPERATURE_CHOICES = {230, 225, 220, 215, 210, 205, 200, 195, 190}
local MAX_FILE_BYTES = 20000000
local MAX_TOMBSTONES = 16

local REQUEST_KEYS = {
    schema=true, simulation_only=true, not_applied=true, request_id=true,
    origin_id=true, context_sha256=true, file_sha256=true, file=true,
    file_bytes=true, printer=true, filament=true, process=true, nozzle_mm=true,
    saved_current=true, edited_current=true, current=true, setting=true,
    choices=true, expires_at=true, ttl_seconds=true,
}
local RESULT_KEYS = {
    schema=true, simulation_only=true, not_applied=true, request_id=true,
    origin_id=true, context_sha256=true, file_sha256=true, file=true,
    file_bytes=true, setting=true, value=true,
}

local tc_active_on = helix.subject.int("tc_active_on", 0)
local tc_baseline_on = helix.subject.int("tc_baseline_on", 1)
local tc_choice_on = helix.subject.int("tc_choice_on", 0)
local tc_waiting_on = helix.subject.int("tc_waiting_on", 0)
local tc_returned_on = helix.subject.int("tc_returned_on", 0)
local tc_choice_idx = helix.subject.int("tc_choice_idx", 0)
local tc_chooser_primary = helix.subject.string("tc_chooser_primary", "Voron 2.4 300 \u{00B7} 0.4 mm")
local tc_chooser_secondary = helix.subject.string("tc_chooser_secondary", "Generic PLA - Rapido \u{00B7} Fast Quality")
local tc_printer = helix.subject.string("tc_printer", "")
local tc_filament = helix.subject.string("tc_filament", "")
local tc_process = helix.subject.string("tc_process", "")
local tc_values = helix.subject.string("tc_values", "")
local tc_file = helix.subject.string("tc_file", "")
local tc_hash = helix.subject.string("tc_hash", "")
local tc_status = helix.subject.string("tc_status", "")
local tc_returned_value = helix.subject.string("tc_returned_value", "")

local temperature_session = nil
local expiry_timer = nil
local persist_wait_timer = nil
local request_wizard_handle = nil
local request_detail_handle = nil

local function exact_keys(value, allowed, expected)
    if type(value) ~= "table" then return false end
    local count = 0
    for key, _ in pairs(value) do
        if not allowed[key] then return false end
        count = count + 1
    end
    return count == expected
end

local function exact_lower_hex(value, length)
    return type(value) == "string" and #value == length
        and value:match("^[0-9a-f]+$") ~= nil
end

local function bounded_text(value)
    return type(value) == "string" and #value > 0 and #value <= 128
        and utf8.len(value) ~= nil and value:find("%S") ~= nil
        and value:find("%c") == nil and value:find("\127", 1, true) == nil
end

local function valid_filename(value)
    return type(value) == "string" and #value > 6 and #value <= 255
        and utf8.len(value) ~= nil
        and value:find("/", 1, true) == nil
        and value:find("\\", 1, true) == nil
        and value:find("..", 1, true) == nil
        and value:find("%c") == nil
        and value:find("\127", 1, true) == nil
        and value:match("%.gcode$") ~= nil
end

local function finite_number(value)
    return type(value) == "number" and value == value
        and value > -math.huge and value < math.huge
end

local function bounded_temperature(value)
    return finite_number(value) and value >= 0 and value <= 500
end

local function exact_choices(values)
    if type(values) ~= "table" or #values ~= #TEMPERATURE_CHOICES then return false end
    for i, expected in ipairs(TEMPERATURE_CHOICES) do
        if values[i] ~= expected then return false end
    end
    return true
end

local function validate_request(data)
    if not exact_keys(data, REQUEST_KEYS, 20)
        or data.schema ~= REQUEST_SCHEMA
        or data.simulation_only ~= true or data.not_applied ~= true
        or not exact_lower_hex(data.request_id, 32)
        or not exact_lower_hex(data.origin_id, 32)
        or not exact_lower_hex(data.context_sha256, 64)
        or not exact_lower_hex(data.file_sha256, 64)
        or not valid_filename(data.file)
        or not finite_number(data.file_bytes) or data.file_bytes ~= math.floor(data.file_bytes)
        or data.file_bytes < 1 or data.file_bytes > MAX_FILE_BYTES
        or not bounded_text(data.printer) or not bounded_text(data.filament)
        or not bounded_text(data.process)
        or not finite_number(data.nozzle_mm) or data.nozzle_mm < 0.05 or data.nozzle_mm > 2
        or not bounded_temperature(data.saved_current)
        or not bounded_temperature(data.edited_current)
        or not bounded_temperature(data.current)
        or data.setting ~= "nozzle_temperature"
        or not exact_choices(data.choices)
        or not finite_number(data.expires_at) or data.expires_at ~= math.floor(data.expires_at)
        or data.expires_at < 1
        or not finite_number(data.ttl_seconds) or data.ttl_seconds ~= math.floor(data.ttl_seconds)
        or data.ttl_seconds < 1 or data.ttl_seconds > 900 then
        return nil
    end
    return data
end

local function same_request(a, b)
    if not a or not b then return false end
    for key, _ in pairs(REQUEST_KEYS) do
        if key == "choices" then
            for i, expected in ipairs(a.choices) do
                if b.choices[i] ~= expected then return false end
            end
        elseif a[key] ~= b[key] then
            return false
        end
    end
    return true
end

local function same_identity(a, b)
    return a and b and a.request_id == b.request_id and a.origin_id == b.origin_id
end

local function result_matches_request(result, request, schema)
    return exact_keys(result, RESULT_KEYS, 11)
        and result.schema == schema
        and result.simulation_only == true and result.not_applied == true
        and result.request_id == request.request_id
        and result.origin_id == request.origin_id
        and result.context_sha256 == request.context_sha256
        and result.file_sha256 == request.file_sha256
        and result.file == request.file and result.file_bytes == request.file_bytes
        and result.setting == request.setting
        and type(result.value) == "number" and result.value == math.floor(result.value)
        and result.value >= 190 and result.value <= 230
        and (235 - result.value) % 5 == 0
end

local function bounded_tombstones(value)
    local out = {}
    if type(value) == "table" then
        local first = math.max(1, #value - MAX_TOMBSTONES + 1)
        for i = first, #value do
            if type(value[i]) == "string" and #value[i] <= 65 then
                out[#out + 1] = value[i]
            end
        end
    end
    return out
end

local function identity_of(request)
    return request.origin_id .. ":" .. request.request_id
end

local function is_tombstoned(session, request)
    local identity = identity_of(request)
    for _, completed in ipairs(session.tombstones or {}) do
        if completed == identity then return true end
    end
    return false
end

local function remember_tombstone(session, request)
    local identity = identity_of(request)
    for _, completed in ipairs(session.tombstones or {}) do
        if completed == identity then return end
    end
    session.tombstones = bounded_tombstones(session.tombstones)
    session.tombstones[#session.tombstones + 1] = identity
    session.tombstones = bounded_tombstones(session.tombstones)
end

local function persist_session()
    local ok, err = pcall(helix.storage.set, "session", temperature_session)
    if not ok then
        tc_status:set("Storage queue failed; selection was not returned")
        return false
    end
    return true
end

local function set_state(state)
    temperature_session.state = state
    tc_choice_on:set(state == "received" and 1 or 0)
    tc_waiting_on:set((state == "queued" or state == "waiting") and 1 or 0)
    tc_returned_on:set(state == "returned" and 1 or 0)
    if state == "received" then
        tc_status:set(temperature_session.recovery_required
            and "Exact request recovery required before selection"
            or "Choose the simulated winning temperature")
    elseif state == "queued" then
        tc_status:set("Selection queued; waiting for companion acknowledgement")
    elseif state == "waiting" then
        tc_status:set("Waiting for originating companion acknowledgement")
    elseif state == "returned" then
        tc_status:set("Returned to originating companion \u{00B7} not applied")
    elseif state == "expired" then
        tc_status:set("Request expired; selection disabled")
    end
end

local function show_request(request)
    tc_active_on:set(1)
    tc_baseline_on:set(0)
    tc_chooser_primary:set(request.printer .. " \u{00B7} " .. tostring(request.nozzle_mm) .. " mm")
    tc_chooser_secondary:set(request.filament .. " \u{00B7} " .. request.process)
    tc_printer:set(request.printer .. " \u{00B7} " .. tostring(request.nozzle_mm) .. " mm nozzle")
    tc_filament:set(request.filament)
    tc_process:set(request.process)
    tc_values:set("Saved " .. tostring(request.saved_current) .. "\u{00B0}C \u{00B7} Edited "
        .. tostring(request.edited_current) .. "\u{00B0}C \u{00B7} Effective "
        .. tostring(request.current) .. "\u{00B0}C")
    tc_file:set(request.file .. " \u{00B7} " .. tostring(request.file_bytes) .. " bytes")
    tc_hash:set("SHA-256 " .. request.file_sha256)
    if temperature_session.result then
        tc_returned_value:set(tostring(temperature_session.result.value) .. "\u{00B0}C")
    else
        tc_returned_value:set("")
    end
    set_state(temperature_session.state)
end

local function cancel_expiry_timer()
    if expiry_timer then expiry_timer:cancel(); expiry_timer = nil end
end

local function arm_expiry(request)
    cancel_expiry_timer()
    expiry_timer = helix.timer.after(request.ttl_seconds * 1000, function()
        expiry_timer = nil
        if temperature_session and not temperature_session.acknowledged then
            remember_tombstone(temperature_session, temperature_session.request)
            set_state("expired")
            persist_session()
        end
    end)
end

local function open_request_stack()
    if not request_wizard_handle then
        request_wizard_handle = helix.ui.overlay("orcacal__wizard", {
            on_close = function()
                request_wizard_handle = nil
            end,
        })
    end
    if not request_detail_handle then
        request_detail_handle = helix.ui.overlay("orcacal__temperature", {
            on_close = function()
                request_detail_handle = nil
            end,
        })
    end
end

local function new_session(request, tombstones)
    return {
        request=request, result=nil, acknowledged=false, recovery_required=false,
        state="received", tombstones=bounded_tombstones(tombstones),
    }
end

local function on_temperature_request(_, data)
    local request = validate_request(data)
    if not request then
        tc_status:set("Rejected invalid Temperature request")
        return
    end
    if temperature_session and same_request(temperature_session.request, request) then
        local recovering = temperature_session.recovery_required
        temperature_session.recovery_required = false
        if temperature_session.state == "expired" then
            tc_status:set("Rejected expired request recovery")
            return
        end
        persist_session()
        show_request(request)
        -- A live duplicate is idempotent and cannot extend the native TTL.
        -- After restart only an exact relay-revalidated recovery event re-arms
        -- the guard; the relay and Orca enforce the request's absolute expiry.
        if recovering then arm_expiry(request) end
        return
    end
    if temperature_session and same_identity(temperature_session.request, request) then
        tc_status:set("Rejected conflicting request identity")
        return
    end
    if temperature_session and not temperature_session.acknowledged
        and temperature_session.state ~= "expired" then
        tc_status:set("Busy with an earlier Temperature request")
        return
    end
    local tombstones = temperature_session and temperature_session.tombstones or {}
    if temperature_session and (temperature_session.acknowledged
        or temperature_session.state == "expired") then
        tombstones[#tombstones + 1] = identity_of(temperature_session.request)
    end
    local candidate = new_session(request, tombstones)
    if is_tombstoned(candidate, request) then
        tc_status:set("Rejected completed request replay")
        return
    end
    temperature_session = candidate
    persist_session()
    tc_choice_idx:set(0)
    show_request(request)
    arm_expiry(request)
    -- A fresh inbound request opens the accepted shell and its existing
    -- Temperature detail. Duplicates and restart recovery update in place and
    -- never reopen a stack the owner has backed out of.
    open_request_stack()
end

local function on_temperature_ack(_, data)
    if not temperature_session or not temperature_session.result
        or not result_matches_request(data, temperature_session.request, ACK_SCHEMA)
        or data.value ~= temperature_session.result.value then
        return
    end
    temperature_session.acknowledged = true
    temperature_session.recovery_required = false
    set_state("returned")
    cancel_expiry_timer()
    persist_session()
end

helix.moonraker.on_agent_event(TEMPERATURE_REQUEST_EVENT, on_temperature_request)
helix.moonraker.on_agent_event(TEMPERATURE_ACK_EVENT, on_temperature_ack)

helix.ui.on("return_selection", function()
    if not temperature_session or temperature_session.recovery_required
        or temperature_session.state ~= "received" then return end
    local index = tc_choice_idx:get()
    if index < 0 or index >= #TEMPERATURE_CHOICES then return end
    local value = TEMPERATURE_CHOICES[index + 1]
    if temperature_session.result and temperature_session.result.value ~= value then
        tc_status:set("First selection is immutable; waiting for its acknowledgement")
        return
    end
    if not temperature_session.result then
        local request = temperature_session.request
        temperature_session.result = {
            schema=RESULT_SCHEMA, simulation_only=true, not_applied=true,
            request_id=request.request_id, origin_id=request.origin_id,
            context_sha256=request.context_sha256, file_sha256=request.file_sha256,
            file=request.file, file_bytes=request.file_bytes,
            setting=request.setting, value=value,
        }
    end
    tc_returned_value:set(tostring(temperature_session.result.value) .. "\u{00B0}C")
    set_state("queued")
    if not persist_session() then return end
    if persist_wait_timer then persist_wait_timer:cancel() end
    persist_wait_timer = helix.timer.after(650, function()
        persist_wait_timer = nil
        if temperature_session and temperature_session.state == "queued" then
            set_state("waiting")
        end
    end)
end)

local function restore_session()
    local ok, stored = pcall(helix.storage.get, "session")
    if not ok or type(stored) ~= "table" then return end
    local request = validate_request(stored.request)
    if not request then return end
    local result = nil
    if stored.result ~= nil then
        if not result_matches_request(stored.result, request, RESULT_SCHEMA) then return end
        result = stored.result
    end
    temperature_session = {
        request=request, result=result, acknowledged=stored.acknowledged == true,
        recovery_required=stored.acknowledged ~= true,
        state=stored.acknowledged == true and "returned" or (result and "waiting" or "received"),
        tombstones=bounded_tombstones(stored.tombstones),
    }
    show_request(request)
    if not temperature_session.acknowledged then arm_expiry(request) end
end

restore_session()
