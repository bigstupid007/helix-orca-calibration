-- SPDX-License-Identifier: GPL-3.0-or-later
-- V1 derivative uses documented beta.9 subjects/overlays/event+storage only.
-- No printer RPC, file transfer, HTTP, process, wall clock or physical action.
local v1_subjects = {}
local function string_subject(name, value)
    local s=helix.subject.string('v1_'..name,value or '')
    v1_subjects[name]=s; return s
end
local function int_subject(name,value)
    local s=helix.subject.int('v1_'..name,value or 0)
    v1_subjects[name]=s; return s
end
for _,name in ipairs({'printer','profiles','context_note','message','calibration','phase','parameters','artifact','qualification','evaluation_note','returned'}) do string_subject(name) end
string_subject('tile','V1')
for _,name in ipairs({'resume_on','confirm_on','start_on','cancel_on','evaluate_on','evaluation_idx'}) do int_subject(name) end
local v1_indices={}
for id,entry in pairs(V1_CATALOG) do
    string_subject('availability_'..id,'Waiting for Orca companion')
    v1_indices[id]={}
    for key,_ in pairs(entry.parameters) do v1_indices[id][key]=int_subject(id..'_'..key..'_idx') end
end
local v1_settings={temperature='nozzle_temperature',flow_ratio_yolo='filament_flow_ratio',pressure_advance_pattern='pressure_advance',retraction='filament_retraction_length',max_volumetric_speed='filament_max_volumetric_speed'}
local v1_offer=nil
local v1_session=nil
local v1_job_handle=nil
local function v1_set(name,value) v1_subjects[name]:set(value) end
local function v1_text(s,limit) return type(s)=='string' and #s>0 and #s<=(limit or 256) and utf8.len(s)~=nil and not s:find('%c') end
local function v1_hex(s,n) return type(s)=='string' and #s==n and s:match('^[0-9a-f]+$')~=nil end
local function v1_number(n) return type(n)=='number' and n==n and n>-math.huge and n<math.huge end
local function v1_same(a,b)
    if type(a)~=type(b) then return false end
    if type(a)~='table' then return a==b end
    for k,v in pairs(a) do if not v1_same(v,b[k]) then return false end end
    for k,_ in pairs(b) do if a[k]==nil then return false end end
    return true
end
local function v1_exact(t,fields)
    if type(t)~='table' then return false end
    local allowed={}
    for k in fields:gmatch('%S+') do allowed[k]=true end
    for k,_ in pairs(t) do if not allowed[k] then return false end end
    return true
end
local function v1_valid_parameters(id,p)
    if id=='flow_ratio_yolo' then return p.pass==1 end
    if not v1_number(p.start) or not v1_number(p['end']) or not v1_number(p.step) then return false end
    if id=='temperature' then return p.start>=p['end']+5 and p.step==5 and (p.start-p['end'])%5==0 end
    return p['end']>=p.start+p.step and (p['end']-p.start)/p.step<=1000
end
local function v1_identity(data)
    return v1_session and type(data)=='table' and data.request_id==v1_session.request.request_id
        and data.origin_id==v1_session.request.origin_id
end
local function v1_persist()
    local ok=pcall(helix.storage.set,'v1_session',v1_session)
    if not ok then
        if v1_session then v1_session.phase='uncertain' end
        v1_set('message','Local storage unavailable · actions locked')
        for _,key in ipairs({'confirm_on','start_on','cancel_on','evaluate_on'}) do v1_set(key,0) end
    end
    return ok
end
local function v1_options()
    local out={}
    local e=v1_session and v1_session.evaluation
    if e then for _,value in ipairs(e.options) do out[#out+1]=tostring(value)..(e.unit~='' and (' '..e.unit) or '') end end
    return #out>0 and table.concat(out,'\n') or 'Unavailable'
end
local v1_open_job
local v1_refresh_job=false
v1_open_job=function()
    if not v1_session then return end
    if v1_job_handle then
        local old=v1_job_handle;v1_job_handle=nil;v1_refresh_job=true;pcall(old.close);return
    end
    local h
    h=helix.ui.overlay('orcacal__v1_job',{evaluation_options=v1_options(),on_close=function()
        if v1_job_handle==h then v1_job_handle=nil end
        if v1_refresh_job then v1_refresh_job=false;v1_open_job() end
    end})
    v1_job_handle=h
end
local function v1_context(o)
    v1_set('printer',o and (o.printer..' · '..tostring(o.nozzle_mm)..' mm') or 'No Orca context')
    v1_set('profiles',o and (o.filament..' · '..o.process) or 'Open the V1 companion in Orca')
    v1_set('context_note','Original profiles preserved · results NOT APPLIED')
end
local function v1_render()
    if not v1_session then
        v1_context(v1_offer);v1_set('message','Choose a calibration and configure its parameters.')
        return
    end
    local s=v1_session
    v1_context(s.offer)
    v1_set('resume_on',1);v1_set('calibration',V1_CATALOG[s.request.calibration].name)
    v1_set('phase',s.phase);v1_set('tile',s.result and (s.receipt and 'Done' or 'Send') or 'Active')
    v1_set('message',s.message or '')
    local p={}
    for _,k in ipairs({'start','end','step','pass','scale'}) do if s.request.parameters[k]~=nil then p[#p+1]=k..': '..tostring(s.request.parameters[k]) end end
    v1_set('parameters',table.concat(p,' · '))
    local prepared=s.prepared
    local artifact=prepared and prepared.artifact
    v1_set('artifact',artifact and (artifact.name..' · '..artifact.size..' bytes') or 'No prepared file')
    v1_set('qualification',prepared and prepared.parity.reason or 'Awaiting generation and independent native parity')
    local qualified=prepared and prepared.parity.qualified==true and artifact~=nil
    v1_set('confirm_on',s.phase=='review' and qualified and not s.intent and 1 or 0)
    v1_set('start_on',s.phase=='confirmed' and qualified and s.intent and s.intent.action=='confirm' and 1 or 0)
    v1_set('cancel_on',(s.phase=='printing' and s.intent and s.intent.action=='start') and 1 or 0)
    v1_set('evaluate_on',s.phase=='complete' and s.evaluation and not s.result and 1 or 0)
    v1_set('evaluation_note',s.phase=='complete' and 'Choose the best result from the completed calibration.' or 'Evaluation unlocks only after independently verified exact-job completion.')
    v1_set('returned',s.result and (tostring(s.result.value)..' · '..(s.receipt and 'Returned to original Orca · NOT APPLIED' or 'Returning · waiting for original Orca receipt · NOT APPLIED')) or '')
end
local function v1_capability(offer,id)
    if not offer then return nil end
    for _,c in ipairs(offer.capabilities) do if c.id==id then return c end end
end
local function v1_receive_offer(_,o)
    if not v1_exact(o,'schema origin_id request_id context_sha256 printer process filament nozzle_mm capabilities defaults created_at expires_at') or o.schema~='helix-orca-v1-offer/v1'
        or not v1_hex(o.origin_id,32) or not v1_hex(o.request_id,32) or not v1_hex(o.context_sha256,64)
        or not v1_text(o.printer,128) or not v1_text(o.process,128) or not v1_text(o.filament,128)
        or not v1_number(o.nozzle_mm) or o.nozzle_mm<=0 or o.nozzle_mm>2
        or not v1_number(o.created_at) or not v1_number(o.expires_at) or o.expires_at<=o.created_at
        or type(o.defaults)~='table' or type(o.capabilities)~='table' or #o.capabilities~=5 then return end
    local seen={}
    for _,c in ipairs(o.capabilities) do
        if type(c)~='table' or not V1_CATALOG[c.id] or seen[c.id] or type(c.available)~='boolean' or not v1_text(c.reason,512) then return end
        seen[c.id]=true
    end
    for id,entry in pairs(V1_CATALOG) do
        if type(o.defaults[id])~='table' then return end
        for key,values in pairs(entry.parameters) do
            local supported=false
            for _,value in ipairs(values) do if value==o.defaults[id][key] then supported=true end end
            if not supported then return end
        end
    end
    v1_offer=o
    for id,_ in pairs(V1_CATALOG) do
        local c=v1_capability(o,id)
        v1_set('availability_'..id,(c.available and 'Preparation available · ' or 'Blocked · ')..c.reason)
    end
    if not v1_session then v1_render() end
end
helix.ui.on('open',function() helix.ui.overlay('orcacal__wizard') end)
helix.ui.on('v1_resume',v1_open_job)
helix.ui.on('v1_choose',function(id)
    if not V1_CATALOG[id] then return end
    if v1_session and not v1_session.receipt and v1_session.phase~='blocked' and v1_session.phase~='failed' and v1_session.phase~='cancelled' then
        v1_set('message','Finish or return the active calibration before starting another.');v1_open_job();return
    end
    local defaults=v1_offer and v1_offer.defaults[id]
    for key,subject in pairs(v1_indices[id]) do
        local values=V1_CATALOG[id].parameters[key]
        for i,v in ipairs(values) do if defaults and defaults[key]==v then subject:set(i-1) end end
    end
    helix.ui.overlay('orcacal__v1_'..id)
end)
helix.ui.on('v1_generate',function(id)
    local c=v1_capability(v1_offer,id)
    if not c or not c.available then v1_set('message',c and ('Generation blocked · '..c.reason) or 'Waiting for Orca context');return end
    if v1_session and v1_session.request.request_id==v1_offer.request_id then v1_set('message','This request was already submitted. Open the active calibration.');return end
    if v1_session and not v1_session.receipt and v1_session.phase~='blocked' and v1_session.phase~='failed' and v1_session.phase~='cancelled' then return end
    local parameters={}
    for key,subject in pairs(v1_indices[id]) do
        local value=V1_CATALOG[id].parameters[key][subject:get()+1]
        if value==nil then return end
        parameters[key]=value
    end
    if not v1_valid_parameters(id,parameters) then v1_set('message','Choose a valid range: end and increment must describe at least two samples.');return end
    local request={schema='helix-orca-v1-request/v1',request_id=v1_offer.request_id,origin_id=v1_offer.origin_id,
        context_sha256=v1_offer.context_sha256,calibration=id,parameters=parameters,
        created_at=v1_offer.created_at,expires_at=v1_offer.expires_at,not_applied=true}
    v1_session={request=request,offer=v1_offer,phase='requested',sequence=0,message='Generation requested · nothing started'}
    if v1_persist() then v1_render();v1_open_job() end
end)
local function v1_prepared(p,digest)
    local r=v1_session.request
    return v1_exact(p,'schema request_id origin_id context_sha256 request_sha256 calibration parameters artifact generator parity not_applied') and p.schema=='helix-orca-v1-prepared/v1' and p.request_id==r.request_id and p.origin_id==r.origin_id
        and p.context_sha256==r.context_sha256 and p.calibration==r.calibration and v1_same(p.parameters,r.parameters)
        and v1_hex(p.request_sha256,64) and v1_hex(digest,64) and p.not_applied==true
        and v1_exact(p.generator,'build route') and v1_text(p.generator.build,128) and v1_text(p.generator.route,128)
        and v1_exact(p.parity,'qualified report_sha256 reason') and type(p.parity.qualified)=='boolean' and v1_text(p.parity.reason,512)
        and (not p.parity.qualified or v1_hex(p.parity.report_sha256,64))
        and (p.artifact==nil or (v1_exact(p.artifact,'name size sha256') and v1_text(p.artifact.name,255) and p.artifact.name:match('^[A-Za-z0-9][A-Za-z0-9_.-]*%.gcode$') and not p.artifact.name:find('..',1,true) and v1_number(p.artifact.size)
            and p.artifact.size>0 and p.artifact.size<=100000000 and p.artifact.size%1==0 and v1_hex(p.artifact.sha256,64)))
        and (not p.parity.qualified or p.artifact~=nil)
end
local v1_phases={requested=true,preparing=true,blocked=true,review=true,confirmed=true,starting=true,printing=true,verifying=true,complete=true,cancelled=true,failed=true,uncertain=true,returning=true,delivered=true}
local function v1_receive_status(_,d)
    if not v1_exact(d,'schema request_id origin_id sequence phase message prepared job_id prepared_sha256 completion_sha256 evaluation') or not v1_identity(d) or d.schema~='helix-orca-v1-status/v1' or not v1_phases[d.phase]
        or not v1_number(d.sequence) or d.sequence%1~=0 or d.sequence<=v1_session.sequence or not v1_text(d.message,768) then return end
    local s=v1_session
    local transitions={requested={requested=true,preparing=true,blocked=true,review=true,failed=true,uncertain=true},
        preparing={preparing=true,blocked=true,review=true,failed=true,uncertain=true},
        review={review=true,confirmed=true,blocked=true,failed=true,uncertain=true},
        confirmed={confirmed=true,blocked=true,failed=true,uncertain=true},
        starting={starting=true,blocked=true,printing=true,verifying=true,complete=true,failed=true,cancelled=true,uncertain=true},
        printing={printing=true,verifying=true,complete=true,failed=true,cancelled=true,uncertain=true},
        verifying={verifying=true,complete=true,failed=true,cancelled=true,uncertain=true},
        uncertain={blocked=true,review=true,confirmed=true,starting=true,printing=true,verifying=true,complete=true,failed=true,cancelled=true,uncertain=true},
        blocked={blocked=true}}
    if not transitions[s.phase] or not transitions[s.phase][d.phase] then return end
    if s.result or s.phase=='failed' or s.phase=='cancelled' or s.phase=='complete' then return end
    if d.phase=='returning' or d.phase=='delivered' then return end -- only exact ACK commits delivery
    if d.prepared~=nil then
        if not v1_prepared(d.prepared,d.prepared_sha256) then return end
        if s.prepared_sha256 and s.prepared_sha256~=d.prepared_sha256 then return end
    elseif d.phase=='review' or d.phase=='confirmed' or d.phase=='starting' or d.phase=='printing' or d.phase=='verifying' or d.phase=='complete' then return end
    local action=s.intent and s.intent.action
    if d.phase=='confirmed' and (s.phase~='review' or action~='confirm') then return end
    if (d.phase=='starting' or d.phase=='printing' or d.phase=='verifying' or d.phase=='complete') and action~='start' then return end
    if d.phase=='review' and (action~=nil or not d.prepared.parity.qualified) then return end
    if (d.phase=='printing' or d.phase=='verifying' or d.phase=='complete') and not v1_text(d.job_id,128) then return end
    if s.job_id and d.job_id~=s.job_id and (d.phase=='printing' or d.phase=='verifying' or d.phase=='complete') then return end
    if d.phase=='complete' then
        local e=d.evaluation
        if not v1_hex(d.completion_sha256,64) or type(e)~='table' or not v1_text(e.setting,128)
            or e.setting~=v1_settings[s.request.calibration]
            or type(e.options)~='table' or #e.options<1 or #e.options>128 or type(e.unit)~='string' or #e.unit>16 or e.unit:find('%c') or utf8.len(e.unit)==nil then return end
        for _,v in ipairs(e.options) do if not v1_number(v) then return end end
        s.completion_sha256=d.completion_sha256;s.evaluation=e
    end
    s.sequence=d.sequence;s.phase=d.phase;s.message=d.message
    if d.prepared then s.prepared=d.prepared;s.prepared_sha256=d.prepared_sha256 end
    if d.job_id then s.job_id=d.job_id end
    if v1_persist() then v1_render();if d.phase=='complete' and v1_job_handle then v1_open_job() end end
end
local function v1_intent(action)
    local s=v1_session
    if not s or not s.prepared or not s.prepared.parity.qualified or not v1_hex(s.prepared_sha256,64) then return end
    if action=='confirm' and (s.phase~='review' or s.intent) then return end
    if action=='start' and (s.phase~='confirmed' or not s.intent or s.intent.action~='confirm') then return end
    if action=='cancel' and (s.phase~='printing' or not s.intent or s.intent.action~='start') then return end
    local serial=action=='confirm' and 1 or action=='start' and 2 or 3
    s.intent={schema='helix-orca-v1-intent/v1',request_id=s.request.request_id,origin_id=s.request.origin_id,
        prepared_sha256=s.prepared_sha256,action=action,intent_id=s.request.request_id:sub(1,24)..string.format('%08x',serial)}
    if action=='start' then s.phase='starting';s.message='Start requested · physical action adapter disabled in this candidate'
    elseif action=='cancel' then s.message='Cancellation requested · waiting for verified status'
    else s.message='Confirmation sent · waiting for coordinator' end
    if v1_persist() then v1_render() end
end
for _,action in ipairs({'confirm','start','cancel'}) do helix.ui.on('v1_'..action,function() v1_intent(action) end) end
helix.ui.on('v1_return',function()
    local s=v1_session
    if not s or s.phase~='complete' or s.result or not s.evaluation then return end
    local value=s.evaluation.options[v1_subjects.evaluation_idx:get()+1]
    if value==nil then return end
    s.result={schema='helix-orca-v1-result/v1',request_id=s.request.request_id,origin_id=s.request.origin_id,
        context_sha256=s.request.context_sha256,prepared_sha256=s.prepared_sha256,job_id=s.job_id,
        completion_sha256=s.completion_sha256,setting=s.evaluation.setting,value=value,not_applied=true}
    s.phase='returning';s.message='Result committed locally · waiting for original Orca receipt'
    if v1_persist() then v1_render() end
end)
local function v1_receive_ack(_,d)
    if not v1_exact(d,'schema request_id origin_id result_sha256 result not_applied') or not v1_identity(d) or d.schema~='helix-orca-v1-ack/v1' or d.not_applied~=true
        or not v1_hex(d.result_sha256,64) or not v1_session.result or not v1_same(d.result,v1_session.result) then return end
    if v1_session.receipt then return end
    v1_session.receipt=d;v1_session.phase='delivered';v1_session.message='Returned to original Orca · NOT APPLIED'
    if v1_persist() then v1_render() end
end
helix.moonraker.on_agent_event('helix_orca_v1.context.v1',v1_receive_offer)
helix.moonraker.on_agent_event('helix_orca_v1.status.v1',v1_receive_status)
helix.moonraker.on_agent_event('helix_orca_v1.ack.v1',v1_receive_ack)
-- Recover retained state without replaying any request/intent or restoring an action.
local v1_ok,v1_saved=pcall(helix.storage.get,'v1_session')
local function v1_restore(s)
    if type(s)~='table' or type(s.request)~='table' or not V1_CATALOG[s.request.calibration]
        or type(s.offer)~='table' or not v1_hex(s.request.request_id,32) or not v1_hex(s.request.origin_id,32)
        or not v1_hex(s.request.context_sha256,64) or s.request.schema~='helix-orca-v1-request/v1' or s.request.not_applied~=true
        or type(s.request.parameters)~='table' or not v1_valid_parameters(s.request.calibration,s.request.parameters)
        or not v1_text(s.offer.printer,128) or not v1_text(s.offer.process,128) or not v1_text(s.offer.filament,128)
        or not v1_number(s.offer.nozzle_mm) or not v1_number(s.sequence) or s.sequence<0 or s.sequence%1~=0
        or not v1_phases[s.phase] or (s.message~=nil and not v1_text(s.message,768)) then return false end
    v1_session=s
    if s.prepared and not v1_prepared(s.prepared,s.prepared_sha256) then v1_session=nil;return false end
    if s.intent and (not v1_exact(s.intent,'schema request_id origin_id prepared_sha256 action intent_id')
        or s.intent.schema~='helix-orca-v1-intent/v1' or not v1_identity(s.intent)
        or s.intent.prepared_sha256~=s.prepared_sha256 or not v1_hex(s.intent.intent_id,32)
        or (s.intent.action~='confirm' and s.intent.action~='start' and s.intent.action~='cancel')) then v1_session=nil;return false end
    if s.result then
        local r=s.result
        if not v1_exact(r,'schema request_id origin_id context_sha256 prepared_sha256 job_id completion_sha256 setting value not_applied')
            or r.schema~='helix-orca-v1-result/v1' or not v1_identity(r) or r.context_sha256~=s.request.context_sha256
            or r.prepared_sha256~=s.prepared_sha256 or not v1_hex(r.prepared_sha256,64)
            or not v1_text(r.job_id,128) or not v1_hex(r.completion_sha256,64) or not v1_text(r.setting,128)
            or not v1_number(r.value) or r.not_applied~=true then v1_session=nil;return false end
        s.evaluation=nil -- retained result needs no mutable evaluation options
        if s.receipt and (s.receipt.schema~='helix-orca-v1-ack/v1' or not v1_same(s.receipt.result,r)
            or not v1_hex(s.receipt.result_sha256,64) or s.receipt.not_applied~=true
            or not v1_identity(s.receipt)) then s.receipt=nil end
        s.phase=s.receipt and 'delivered' or 'returning'
    else
        s.phase='uncertain';s.evaluation=nil
        s.message='Reconnecting · actions locked until verified coordinator status'
    end
    return true
end
if v1_ok then v1_restore(v1_saved) end
v1_render()
