-- SPDX-License-Identifier: GPL-3.0-or-later
-- Development-only adaptation of Preston Brown calibration-bridge @ ed8d0c4.
-- The ordinary product harness never mounts this plugin.
-- The pinned native state machine, overlays and explicit mock start are retained.
-- Repository adapter receives and returns real artifact bytes through native
-- plugin storage. beta.4 refuses HTTP to loopback; that guard is preserved.

-- beta.4 predates the example's translation binding. Native UI uses English.
local t = helix.i18n and helix.i18n.t or function(text) return text end

-- States: 0 idle, 1 available, 2 printing, 3 asking, 4 done.
local state = helix.subject.int("state", 0)
local start_on = helix.subject.int("start_on", 0)
local printing_on = helix.subject.int("printing_on", 0)
local progress_line = helix.subject.string("progress_line", "Mock progress: 0%")
local pick_on = helix.subject.int("pick_on", 0)
local result_on = helix.subject.int("result_on", 0)
-- LVGL dropdown selection, 0-based; the first option is pre-selected.
local choice_idx = helix.subject.int("choice_idx", 0)
local state_title = helix.subject.string("state_title", t("No calibration running"))
local ctx_printer = helix.subject.string("ctx_printer", "")
local ctx_filament = helix.subject.string("ctx_filament", "")
local ctx_current = helix.subject.string("ctx_current", "")
local result_value = helix.subject.string("result_value", "")
local result_sub = helix.subject.string("result_sub", "")
local status_line = helix.subject.string("status_line", "")
local tile_status = helix.subject.string("tile_status", "Waiting for request")
local review_sequence = 0

-- The English source of whatever the status line and result note show, so a
-- language switch can say them again in the new language. nil = raw text or
-- nothing standing.
local status_key, result_key

local function set_status(key)
    status_key = key
    status_line:set(key and t(key) or "")
end

local function set_result_note(key, raw)
    result_key = key
    result_sub:set(key and t(key) or raw)
end

local WIZARDS = {
    temp_tower = { name = "Temperature tower", fmt = "%d\u{00B0}C", integral = true },
    pa_pattern = { name = "PA pattern", fmt = "%.2f" },
    flow_rate = { name = "Flow rate", fmt = "%d%%", integral = true },
}

-- The calibration in flight. `choices` holds numbers; the dropdown labels and
-- the posted value come from one formatter, so what the user read is what the
-- companion receives.
local cal = nil
local delivered = false
local overlay_handle = nil
local start_inflight = false

local function set_state(v)
    state:set(v)
    start_on:set(v == 1 and 1 or 0)
    printing_on:set(v == 2 and 1 or 0)
    pick_on:set(v == 3 and 1 or 0)
    result_on:set(v == 4 and 1 or 0)
    tile_status:set(({[0]="Waiting for request",[1]="Ready to start",[2]="Printing · tap to return",[3]="Choose temperature",[4]="Result · not applied"})[v])
end

-- The context lines, rebuilt rather than patched so a language switch can
-- re-say them from the same data.
local function refresh_ctx()
    if not cal then
        state_title:set(t("No calibration running"))
        ctx_printer:set("")
        ctx_filament:set("")
        ctx_current:set("")
        return
    end
    local w = WIZARDS[cal.wizard]
    state_title:set(t(w.name))
    local nozzle = cal.nozzle_mm and (" \u{00B7} " .. t("nozzle") .. " " .. tostring(cal.nozzle_mm)) or ""
    ctx_printer:set(cal.printer .. nozzle)
    ctx_filament:set(cal.filament)
    ctx_current:set(t("Effective") .. ": " .. w.fmt:format(cal.current))
end

-- beta.4 closes overlays through its queued navigation lifecycle. Reopen only
-- from the supported close callback, avoiding a handle to the dying component.
local reopen_options = nil
local show_ask
show_ask = function(options)
    overlay_handle = helix.ui.overlay("calibration-bridge__ask", {
        opts = options,
        on_close = function()
            overlay_handle = nil
            if reopen_options then
                local next_options = reopen_options
                reopen_options = nil
                show_ask(next_options)
            end
        end,
    })
end
local function open_ask()
    local labels = {}
    for i, v in ipairs(cal.choices) do
        labels[i] = WIZARDS[cal.wizard].fmt:format(v)
    end
    local options = table.concat(labels, "\n")
    if overlay_handle then
        reopen_options = options
        overlay_handle.close()
    else
        show_ask(options)
    end
end

local function cancel_cal()
    cal = nil
    set_state(0)
    refresh_ctx()
    choice_idx:set(0)
    set_status(nil)
    set_result_note(nil, "")
end

local function on_available(data)
    if type(data) ~= "table" then
        return
    end
    if cal and cal.request_id == data.request_id then return end
    if cal and state:get() == 2 then set_status("A mock print is already active"); return end
    if data.mock_only ~= true or data.wizard ~= "temp_tower"
        or type(data.request_id) ~= "string" or not data.request_id:match("^[a-f0-9]+$") or #data.request_id ~= 32
        or type(data.context_sha256) ~= "string" or #data.context_sha256 ~= 64
        or type(data.file_sha256) ~= "string" or #data.file_sha256 ~= 64
        or data.file ~= "helix-temp-" .. data.request_id .. ".gcode"
        or type(data.saved_current) ~= "number" or data.saved_current ~= math.floor(data.saved_current)
        or type(data.printer) ~= "string" or data.printer == ""
        or type(data.filament) ~= "string" or data.filament == "" then
        set_status("bad mock request"); return
    end
    local w = WIZARDS[data.wizard]
    if not w or type(data.choices) ~= "table" then
        set_status("bad event")
        return
    end
    -- Validate everything before mutating anything: a refused event must not
    -- leave a half-applied calibration behind.
    local choices = {}
    for i, v in ipairs(data.choices) do
        local n = tonumber(v)
        if not n or (w.integral and n ~= math.floor(n)) then
            set_status("bad event")
            return
        end
        choices[i] = n
    end
    for i, n in ipairs(choices) do
        if n ~= 235 - i * 5 then set_status("bad Temperature choices"); return end
    end
    if #choices ~= 9 then
        set_status("bad event")
        return
    end
    local current = tonumber(data.current)
    if not current or (w.integral and current ~= math.floor(current)) then
        set_status("bad event")
        return
    end
    cal = {
        request_id = data.request_id,
        context_sha256 = data.context_sha256,
        file_sha256 = data.file_sha256,
        saved_current = data.saved_current,
        wizard = data.wizard,
        filament = tostring(data.filament or ""),
        printer = tostring(data.printer or ""),
        nozzle_mm = tonumber(data.nozzle_mm),
        current = current,
        choices = choices,
        file = tostring(data.file or ""),
    }
    choice_idx:set(0)
    delivered = false
    set_status("Mock request received; not started")
    set_state(1)
    refresh_ctx()
    if helix.settings.get("auto_open") ~= false then
        open_ask()
    end
end

local function post_result(value)
    local body = {
        event = "chosen",
        mock_only = true,
        request_id = cal.request_id,
        context_sha256 = cal.context_sha256,
        file_sha256 = cal.file_sha256,
        printer = cal.printer,
        saved_current = cal.saved_current,
        setting = "nozzle_temperature",
        wizard = cal.wizard,
        value = value,
        filament = cal.filament,
        current = cal.current,
    }
    local ok, err = pcall(helix.storage.set, "result", body)
    if ok then
        delivered = true
        set_status(nil)
        set_result_note("sent to the companion; not applied", "")
    else
        set_state(3)
        set_status("Result artifact delivery failed; Next retries the same request")
    end
end

-- Printing ends: complete hands over to the picker; a pause is not an end;
-- anything else returns to available with the reason on the status line.
local prev_printing = false
local function on_print_state(v)
    if not cal or state:get() ~= 2 then
        prev_printing = v == "printing"
        return
    end
    if v == "printing" then
        prev_printing = true
        return
    end
    if v == "paused" or not prev_printing then
        return
    end
    prev_printing = false
    if v == "complete" then
        helix.log.debug("Mock bridge print complete")
        set_status("Mock print complete; choose a temperature")
        set_state(3)
        if helix.settings.get("auto_ask") ~= false then
            open_ask()
        end
    else
        set_state(1)
        set_status(v == "cancelled" and "print cancelled" or "print failed")
    end
end

helix.printer.watch("print_state", on_print_state)
helix.printer.watch("progress", function(v)
    if type(v) == "number" then progress_line:set(("Mock progress: %d%%"):format(v)) end
end)

-- Native storage front door: only the isolated harness writes the initial
-- request artifact. A missing delivery remains visible and never starts a print.
helix.timer.after(1000, function()
local request = helix.storage.get("request")
if request then
    on_available(request)
else
    set_status("Mock request delivery failed; deliver artifact and reload")
    overlay_handle = helix.ui.overlay("calibration-bridge__ask", {opts = ""})
end
end)

helix.ui.on("open", function()
    if cal then
        open_ask()
    else
        helix.ui.toast(t("No calibration running"))
    end
end)

helix.ui.on("start", function()
    if not cal or state:get() ~= 1 or start_inflight then
        return
    end
    if cal.file == "" then
        set_status("no print file in the event")
        return
    end
    start_inflight = true
    local ok, err = helix.moonraker.call("printer.print.start", { filename = cal.file })
    start_inflight = false
    if not ok then
        set_status("print failed")
        return
    end
    set_status("Mock print started")
    set_state(2)
end)

helix.ui.on("accept", function()
    if not cal or state:get() ~= 3 or delivered then
        return
    end
    local i = choice_idx:get()
    if i < 0 or i >= #cal.choices then
        return -- out of range: a list shrank between pick and accept
    end
    local value = cal.choices[i + 1]
    result_value:set(WIZARDS[cal.wizard].fmt:format(value))
    set_state(4)
    post_result(value)
end)

-- This bridge exists only in the owned network-none mock harness. The native
-- action writes a bounded request; only its guarded development driver may
-- simulate completion. It never sends a printer command or starts a request.
helix.ui.on("finish_mock", function()
    if not cal or state:get() ~= 2 then return end
    review_sequence = review_sequence + 1
    local ok = pcall(helix.storage.set, "review_action", {
        action = "finish_simulation", request_id = cal.request_id,
        sequence = review_sequence,
    })
    set_status(ok and "Finishing simulation..." or "Simulation finish request failed; try again")
end)

helix.ui.on("cancel", function()
    if cal and state:get() == 2 then
        -- The button sits next to the running calibration print: cancelling
        -- the calibration stops the print too.
        helix.moonraker.call("printer.print.cancel", {})
    end
    cancel_cal()
end)

-- Subject-carried strings re-say themselves on a language switch.
if helix.i18n then helix.i18n.on_change(function()
    refresh_ctx()
    if status_key then
        status_line:set(t(status_key))
    end
    if result_key then
        result_sub:set(t(result_key))
    end
end) end
