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
local RETURN_SAFETY_SECONDS = 2
local QUERY_TIMEOUT_MS = 1000
local QUERY_LATENCY_SECONDS = QUERY_TIMEOUT_MS / 1000

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
local ENVELOPE_KEYS = {session=true, lease=true}
local LEASE_KEYS = {issued_eventtime=true, expires_eventtime=true}

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
local acknowledgement_timer = nil
local acknowledgement_pending = false
local request_wizard_handle = nil
local request_detail_handle = nil
local operation_generation = 0

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

local function validate_lease(data, request)
    if not exact_keys(data, LEASE_KEYS, 2)
        or not finite_number(data.issued_eventtime)
        or not finite_number(data.expires_eventtime)
        or data.issued_eventtime < 0
        or data.expires_eventtime <= data.issued_eventtime
        or not request
        or data.expires_eventtime - data.issued_eventtime > request.ttl_seconds then
        return nil
    end
    return data
end

local function validate_envelope(data)
    if not exact_keys(data, ENVELOPE_KEYS, 2) then return nil end
    local request = validate_request(data.session)
    if not request then return nil end
    local lease = validate_lease(data.lease, request)
    if not lease then return nil end
    return request, lease
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
    tc_choice_on:set(state == "received" and not temperature_session.recovery_required and 1 or 0)
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

local function next_operation()
    operation_generation = operation_generation + 1
    return operation_generation
end

local function query_eventtime(generation)
    local timeout = helix.timer.after(QUERY_TIMEOUT_MS, function()
        if operation_generation == generation then next_operation() end
    end)
    local response = helix.moonraker.call("printer.objects.query", {
        objects={print_stats={"state"}},
    })
    timeout:cancel()
    if operation_generation ~= generation then return nil end
    local result = type(response) == "table" and response.result or nil
    local current = type(result) == "table" and result.eventtime or nil
    if not finite_number(current) then return nil end
    -- Moonraker samples eventtime before returning. Charge the full bounded
    -- query latency so delayed callbacks shorten rather than extend the lease.
    return current + QUERY_LATENCY_SECONDS
end

local function clock_is_live(lease, current)
    return finite_number(current)
        and current >= lease.issued_eventtime and current < lease.expires_eventtime
end

local function expire_session()
    if not temperature_session
        or (temperature_session.acknowledged and not acknowledgement_pending) then return end
    next_operation()
    acknowledgement_pending = false
    if acknowledgement_timer then acknowledgement_timer:cancel(); acknowledgement_timer = nil end
    remember_tombstone(temperature_session, temperature_session.request)
    temperature_session.acknowledged = false
    temperature_session.recovery_required = false
    set_state("expired")
    persist_session()
end

local function arm_expiry(current)
    cancel_expiry_timer()
    local session = temperature_session
    local remaining = session.lease.expires_eventtime - current
    if remaining <= 0 then expire_session(); return end
    expiry_timer = helix.timer.after(math.max(1, math.floor(remaining * 1000)), function()
        expiry_timer = nil
        if temperature_session == session
            and (not session.acknowledged or acknowledgement_pending) then
            expire_session()
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

local function new_session(request, lease, tombstones)
    return {
        request=request, lease=lease, result=nil, acknowledged=false, recovery_required=false,
        state="received", tombstones=bounded_tombstones(tombstones),
    }
end

local function on_temperature_request(_, data)
    local request, lease = validate_envelope(data)
    if not request then
        tc_status:set("Rejected invalid Temperature request")
        return
    end
    if temperature_session and same_request(temperature_session.request, request) then
        if temperature_session.state == "expired" then
            tc_status:set("Rejected expired request recovery")
            return
        end
        local recovering = temperature_session.recovery_required
        local generation = next_operation()
        local current = query_eventtime(generation)
        if generation ~= operation_generation then return end
        if not clock_is_live(lease, current) then
            tc_status:set("Rejected request without a live Moonraker lease")
            return
        end
        if recovering then
            temperature_session.lease = lease
        else
            temperature_session.lease = {
                issued_eventtime=lease.issued_eventtime,
                expires_eventtime=math.min(temperature_session.lease.expires_eventtime,
                                           lease.expires_eventtime),
            }
            if not clock_is_live(temperature_session.lease, current) then
                expire_session()
                return
            end
        end
        temperature_session.recovery_required = false
        persist_session()
        show_request(request)
        if not temperature_session.acknowledged then arm_expiry(current) end
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
    local candidate = new_session(request, lease, tombstones)
    if is_tombstoned(candidate, request) then
        tc_status:set("Rejected completed request replay")
        return
    end
    local generation = next_operation()
    local current = query_eventtime(generation)
    if generation ~= operation_generation then return end
    if not clock_is_live(lease, current) then
        tc_status:set("Rejected request without a live Moonraker lease")
        return
    end
    temperature_session = candidate
    persist_session()
    tc_choice_idx:set(0)
    show_request(request)
    arm_expiry(current)
    -- A fresh inbound request opens the accepted shell and its existing
    -- Temperature detail. Duplicates and restart recovery update in place and
    -- never reopen a stack the owner has backed out of.
    open_request_stack()
end

local function on_temperature_ack(_, data)
    if not temperature_session or not temperature_session.result
        or temperature_session.state == "expired"
        or not result_matches_request(data, temperature_session.request, ACK_SCHEMA)
        or data.value ~= temperature_session.result.value then
        return
    end
    if acknowledgement_pending then return end
    local session = temperature_session
    local generation = next_operation()
    local current = query_eventtime(generation)
    if generation ~= operation_generation or temperature_session ~= session then return end
    if not clock_is_live(session.lease, current)
        or session.lease.expires_eventtime - current <= RETURN_SAFETY_SECONDS then
        if finite_number(current) and current >= session.lease.expires_eventtime then
            expire_session()
        else
            tc_status:set("Acknowledgement held; more than 2 seconds of live lease required")
        end
        return
    end
    acknowledgement_pending = true
    tc_status:set("Acknowledgement received; committing returned state")
    if not persist_session() then acknowledgement_pending = false; return end
    acknowledgement_timer = helix.timer.after(650, function()
        acknowledgement_timer = nil
        if generation ~= operation_generation or temperature_session ~= session
            or session.state == "expired" then
            acknowledgement_pending = false
            return
        end
        session.acknowledged = true
        session.recovery_required = false
        session.state = "returned"
        if not persist_session() then
            session.acknowledged = false
            session.state = "waiting"
            acknowledgement_pending = false
            set_state("waiting")
            return
        end
        acknowledgement_timer = helix.timer.after(650, function()
            acknowledgement_timer = nil
            if generation ~= operation_generation or temperature_session ~= session
                or session.state == "expired" then
                acknowledgement_pending = false
                return
            end
            acknowledgement_pending = false
            set_state("returned")
            cancel_expiry_timer()
        end)
    end)
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
    local session = temperature_session
    local generation = next_operation()
    local current = query_eventtime(generation)
    if generation ~= operation_generation or temperature_session ~= session then return end
    if not clock_is_live(session.lease, current)
        or session.lease.expires_eventtime - current <= RETURN_SAFETY_SECONDS then
        if finite_number(current) and current >= session.lease.expires_eventtime then
            expire_session()
        else
            tc_status:set("Selection held; more than 2 seconds of live lease required")
        end
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
    local lease = validate_lease(stored.lease, request)
    if not request or not lease then return end
    local result = nil
    if stored.result ~= nil then
        if not result_matches_request(stored.result, request, RESULT_SCHEMA) then return end
        result = stored.result
    end
    local stored_expired = stored.state == "expired"
    temperature_session = {
        request=request, lease=lease, result=result, acknowledged=stored.acknowledged == true,
        recovery_required=not stored_expired and stored.acknowledged ~= true,
        state=stored_expired and "expired"
            or (stored.acknowledged == true and "returned" or (result and "waiting" or "received")),
        tombstones=bounded_tombstones(stored.tombstones),
    }
    if stored_expired then
        remember_tombstone(temperature_session, request)
    end
    show_request(request)
end

restore_session()
