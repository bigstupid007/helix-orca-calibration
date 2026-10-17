-- SPDX-License-Identifier: GPL-3.0-or-later
-- Issue #12 storage-only derivative; no print RPC, HTTP, G-code or permission upgrade.
-- The controller consumes persisted native intent only after a separately authorized test.
local REQUEST_EVENT = "helix_orca_temperature_print.request.v1"
local STATUS_EVENT = "helix_orca_temperature_print.status.v1"
local ACK_EVENT = "helix_orca_temperature_print.ack.v1"
local active = helix.subject.int("tc_active_on", 0)
local baseline = helix.subject.int("tc_baseline_on", 1)
local choice = helix.subject.int("tc_choice_on", 0)
local start_on = helix.subject.int("tp_start_on", 0)
local cancel_on = helix.subject.int("tp_cancel_on", 0)
local waiting = helix.subject.int("tc_waiting_on", 0)
local returned = helix.subject.int("tc_returned_on", 0)
local index = helix.subject.int("tc_choice_idx", 0)
local primary = helix.subject.string("tc_chooser_primary", "Voron 2.4 300 · 0.4 mm")
local secondary = helix.subject.string("tc_chooser_secondary", "Generic PLA - Rapido · Fast Quality")
local printer = helix.subject.string("tc_printer", "")
local filament = helix.subject.string("tc_filament", "")
local process = helix.subject.string("tc_process", "")
local values = helix.subject.string("tc_values", "")
local file = helix.subject.string("tc_file", "")
local hash = helix.subject.string("tc_hash", "")
local status = helix.subject.string("tc_status", "")
local selected = helix.subject.string("tc_returned_value", "")
local session = nil
local detail_handle = nil
local wizard_handle = nil
local choices = {210,205,200}
local identity_keys = {"request_id","origin_id","context_sha256","file_sha256","file","file_bytes","printer"}
local function finite(n) return type(n)=="number" and n==n and n>-math.huge and n<math.huge end
local function hex(s,n) return type(s)=="string" and #s==n and s:match("^[0-9a-f]+$")~=nil end
local function text(s,n) return type(s)=="string" and #s>0 and #s<=n and utf8.len(s)~=nil and not s:find("%c") end
local function same(a,b)
    if type(a)~="table" or type(b)~="table" then return false end
    for _,k in ipairs(identity_keys) do if a[k]~=b[k] then return false end end
    return true
end
local function valid(r)
    if type(r)~="table" or r.schema~="helix-orca-temperature-print-session/v1"
        or r.physical_calibration~=true or r.not_applied~=true
        or not hex(r.request_id,32) or not hex(r.origin_id,32)
        or not hex(r.context_sha256,64) or not hex(r.file_sha256,64)
        or not text(r.file,255) or not r.file:match("%.gcode$")
        or r.file:find("/",1,true) or r.file:find("\\",1,true) or r.file:find("..",1,true)
        or not finite(r.file_bytes) or r.file_bytes%1~=0 or r.file_bytes<1 or r.file_bytes>20000000
        or not text(r.printer,128) or not text(r.filament,128) or not text(r.process,128)
        or not finite(r.nozzle_mm) or r.nozzle_mm<0.05 or r.nozzle_mm>2
        or r.setting~="nozzle_temperature" or type(r.choices)~="table" or #r.choices~=3
        or not finite(r.ttl_seconds) or r.ttl_seconds%1~=0 or r.ttl_seconds<1 or r.ttl_seconds>3600
        or not finite(r.expires_at) or r.expires_at%1~=0 then return false end
    for i,v in ipairs(choices) do if r.choices[i]~=v then return false end end
    for _,k in ipairs({"saved_current","edited_current","current"}) do
        if not finite(r[k]) or r[k]<0 or r[k]>500 then return false end
    end
    return true
end
local messages = {
    received="Not authorized for a physical test · nothing started",
    ready="Three bands · 210 → 205 → 200°C · press Start here when ready",
    starting="Start requested · waiting for the printer to confirm",
    printing="Printing · result selection stays locked until success is confirmed",
    cancelling="Cancellation requested · waiting for the printer to confirm",
    complete="Print completed successfully · choose the best temperature band",
    failed="Print failed · result unavailable",
    cancelled="Print cancelled · result unavailable",
    uncertain="Printer state is uncertain · result unavailable · do not retry Start",
    waiting="Returning selection · waiting for Orca acknowledgement",
    returned="Returned to the original Orca profile · NOT APPLIED",
}
local function render()
    start_on:set(session and session.state=="ready" and not session.start_intent and 1 or 0)
    cancel_on:set(session and session.state=="printing" and not session.cancel_intent and 1 or 0)
    choice:set(session and session.state=="complete" and session.proof and 1 or 0)
    waiting:set(session and session.state=="waiting" and 1 or 0)
    returned:set(session and session.state=="returned" and 1 or 0)
    status:set(session and messages[session.state] or "")
end
local function persist()
    local ok = pcall(helix.storage.set,"print_session",session)
    if not ok then
        session.state="uncertain"; render(); return false
    end
    return true
end
local query_busy=false
local function clock()
    if query_busy then return nil end
    query_busy=true
    local timed_out=false
    local timeout=helix.timer.after(1000,function()
        timed_out=true
        if session then session.state="uncertain"; persist(); render() end
    end)
    local ok,response = pcall(helix.moonraker.call,"printer.objects.query",{objects={print_stats={"state","filename"}}})
    timeout:cancel(); query_busy=false
    if not ok or timed_out then return nil end
    local r=type(response)=="table" and response.result or nil
    local p=r and type(r.status)=="table" and r.status.print_stats or nil
    if not r or not finite(r.eventtime) or not p or type(p.state)~="string" then return nil end
    return r.eventtime,p.state,p.filename
end
local function live(t)
    return session and finite(t) and t>=session.lease.issued_eventtime and t+1<session.lease.expires_eventtime
end
local function show(r)
    active:set(1); baseline:set(0)
    primary:set(r.printer.." · "..tostring(r.nozzle_mm).." mm")
    secondary:set(r.filament.." · "..r.process)
    printer:set(r.printer.." · "..tostring(r.nozzle_mm).." mm nozzle")
    filament:set(r.filament); process:set(r.process)
    values:set("Saved "..r.saved_current.."°C · Edited "..r.edited_current.."°C · Effective "..r.current.."°C")
    file:set(r.file.." · "..r.file_bytes.." bytes"); hash:set("SHA-256 "..r.file_sha256)
    render()
end
local function receive(_,data)
    if type(data)~="table" or not valid(data.session) or type(data.lease)~="table" then return end
    local r,l=data.session,data.lease
    if not finite(l.issued_eventtime) or not finite(l.expires_eventtime)
        or l.expires_eventtime<=l.issued_eventtime or l.expires_eventtime-l.issued_eventtime>r.ttl_seconds then return end
    if session then
        -- Neither duplicate delivery nor changed data may reset a one-shot session.
        return
    end
    session={request=r,lease=l,state="received"}
    if query_busy then return end
    local t,state=clock()
    if not live(t) or (state~="standby" and state~="complete" and state~="cancelled") then
        session=nil; return
    end
    if not persist() then return end
    show(r)
    wizard_handle=helix.ui.overlay("orcacal__wizard",{on_close=function() wizard_handle=nil end})
    detail_handle=helix.ui.overlay("orcacal__temperature",{on_close=function() detail_handle=nil end})
end
local sequence=-1
local function update(_,data)
    if not session or type(data)~="table" or data.schema~="helix-orca-temperature-print-status/v1"
        or not same(session.request,data) or not finite(data.sequence) or data.sequence%1~=0
        or data.sequence<=sequence or not messages[data.state] then return end
    if query_busy then return end
    local t,state,name=clock()
    if not live(t) or not finite(data.eventtime) or data.eventtime>t or t-data.eventtime>5 then
        session.state="uncertain"; persist(); render(); return
    end
    if session.state=="failed" or session.state=="cancelled" or session.state=="uncertain"
        or session.state=="returned" or session.state=="waiting" then return end
    if data.state=="ready" then
        if session.state~="received" or session.start_intent or data.authorized~=true
            or t>=session.lease.issued_eventtime+900
            or not finite(data.estimated_duration_s) or data.estimated_duration_s<=0 or data.estimated_duration_s>1200
            or (state~="standby" and state~="complete" and state~="cancelled") then return end
    elseif data.state=="printing" then
        if not session.start_intent or state~="printing" or name~=session.request.file then return end
    elseif data.state=="complete" then
        if not session.start_intent or session.state~="printing" or session.cancel_intent
            or state~="complete" or name~=session.request.file or not hex(data.completion_sha256,64)
            or not text(data.job_id,64) then return end
        session.proof={job_id=data.job_id,completion_sha256=data.completion_sha256}
    elseif data.state=="received" or data.state=="returned" or data.state=="waiting" then return
    elseif data.state=="starting" or data.state=="cancelling" then return end
    sequence=data.sequence; session.state=data.state
    persist(); render()
end
local function intent(schema,t)
    local out={schema=schema,nonce=session.request.request_id..":"..string.format("%.0f",math.floor(t*1000000)),eventtime=t,
        expires_eventtime=math.min(schema=="helix-orca-temperature-start/v1"
            and session.lease.issued_eventtime+900 or t+30,session.lease.expires_eventtime),choices=choices}
    for _,k in ipairs(identity_keys) do out[k]=session.request[k] end
    return out
end
helix.ui.on("print_start",function()
    if not session or session.state~="ready" or session.start_intent then return end
    if query_busy then return end
    local t,state=clock()
    if not live(t) or t>=session.lease.issued_eventtime+900
        or (state~="standby" and state~="complete" and state~="cancelled") then
        session.state="uncertain"; persist(); render(); return
    end
    session.start_intent=intent("helix-orca-temperature-start/v1",t)
    session.state="starting"; persist(); render()
end)
helix.ui.on("print_cancel",function()
    if not session or session.state~="printing" or session.cancel_intent then return end
    if query_busy then return end
    local t,state,name=clock()
    if not live(t) or state~="printing" or name~=session.request.file then
        session.state="uncertain"; persist(); render(); return
    end
    session.cancel_intent=intent("helix-orca-temperature-cancel/v1",t)
    session.state="cancelling"; persist(); render()
end)
helix.ui.on("return_selection",function()
    if not session or session.state~="complete" or not session.proof or session.cancel_intent then return end
    if query_busy then return end
    local t,state,name=clock()
    local i=index:get()
    if not live(t) or state~="complete" or name~=session.request.file or i<0 or i>=3 then return end
    local r=session.request
    session.result={schema="helix-orca-temperature-print-selection/v1",physical_calibration=true,not_applied=true,
        request_id=r.request_id,origin_id=r.origin_id,context_sha256=r.context_sha256,file_sha256=r.file_sha256,
        file=r.file,file_bytes=r.file_bytes,setting=r.setting,value=choices[i+1],
        job_id=session.proof.job_id,completion_sha256=session.proof.completion_sha256}
    session.state="waiting"; selected:set(choices[i+1].."°C"); persist(); render()
end)
helix.moonraker.on_agent_event(REQUEST_EVENT,receive)
helix.moonraker.on_agent_event(STATUS_EVENT,update)
helix.moonraker.on_agent_event(ACK_EVENT,function(_,data)
    if not session or session.state~="waiting" or type(data)~="table" or not session.result
        or data.schema~="helix-orca-temperature-print-ack/v1" then return end
    for k,v in pairs(session.result) do
        if k~="schema" and data[k]~=v then return end
    end
    if query_busy then return end
    local t,state,name=clock()
    if not live(t) or state~="complete" or name~=session.request.file then return end
    session.state="returned"; persist(); render()
end)
-- Reload/restart cannot redispatch, re-enable Start, or restore unconfirmed success.
local ok,stored=pcall(helix.storage.get,"print_session")
if ok and type(stored)=="table" and valid(stored.request) then
    session=stored; session.state="uncertain"; session.proof=nil; show(session.request)
end
-- Missing/disconnected printer data and expired requests lock all actions.
helix.timer.every(1000,function()
    if not session or session.state=="uncertain" or session.state=="returned" then return end
    if query_busy then return end
    local t,state,name=clock()
    local unexpected = (session.state=="ready" or session.state=="received")
        and state~="standby" and state~="complete" and state~="cancelled"
    unexpected = unexpected or (session.state=="printing" and (name~=session.request.file
        or (state~="printing" and state~="complete")))
    unexpected = unexpected or ((session.state=="received" or session.state=="ready") and finite(t) and t>=session.lease.issued_eventtime+900)
    if not live(t) or unexpected then session.state="uncertain"; persist(); render() end
end)
