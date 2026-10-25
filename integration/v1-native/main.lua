-- SPDX-License-Identifier: GPL-3.0-or-later
-- V1 derivative uses documented beta.12 subjects/dialogs/editors/event+storage only.
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
for _,name in ipairs({'printer','profiles','context_note','message','calibration','phase','parameters','artifact','qualification','evaluation_note','returned','result_heading','result_note','application_note','monitor','offer_printer','offer_profiles','offer_note','warning_heading','warning_message'}) do string_subject(name) end
string_subject('tile','Ready')
for _,name in ipairs({'resume_on','confirm_on','start_on','cancel_on','evaluate_on','evaluation_idx','monitor_on','warning_on','retry_on'}) do int_subject(name) end
local v1_drafts={}
for id,entry in pairs(V1_CATALOG) do
    string_subject('availability_'..id,'Waiting for Orca companion')
    for key,_ in pairs(entry.parameters) do string_subject(id..'_'..key..'_value') end
end
for _,name in ipairs({'keypad_title','keypad_value','keypad_error','keypad_limits','flow_samples','pa_defaults_note'}) do string_subject(name) end
local v1_settings={temperature='nozzle_temperature',flow_ratio_yolo='filament_flow_ratio',pressure_advance_pattern='pressure_advance',retraction='filament_retraction_length',max_volumetric_speed='filament_max_volumetric_speed'}
local v1_offer=nil
local v1_session=nil
local v1_job_handle=nil
local v1_result_handle=nil
local v1_refresh_result=false
local v1_wizard_handle=nil
local v1_detail_handle=nil
local v1_cancel_pending=false
local v1_warning_handle=nil
local v1_open_warning
local V1_NATIVE_ADAPTER_SCHEMA='helix-orca-v1-native-adapter/v2'
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
local function v1_valid_field(rule,value)
    if rule.kind=='fixed' then return v1_same(value,rule.value) end
    if rule.kind=='boolean' then return type(value)=='boolean' end
    if rule.kind=='positive_int_list' then
        if type(value)~='table' or #value>(rule.max_items or 64) then return false end
        for _,item in ipairs(value) do
            if not v1_number(item) or item<=0 or item%1~=0 or item>2147483647 then return false end
        end
        return true
    end
    if rule.kind=='choice' then
        for _,v in ipairs(rule.values) do if value==v and math.type(value)==math.type(v) then return true end end
        return false
    end
    return v1_number(value) and value>=rule.min and (rule.max==nil or value<=rule.max)
        and (not rule.integer or math.type(value)=='integer') and (not rule.multiple or value%rule.multiple==0)
end
local function v1_valid_parameters(id,p,strict_v2)
    local entry=V1_CATALOG[id]
    if not entry or type(p)~='table' then return false end
    for key,_ in pairs(p) do if not entry.parameters[key] then return false end end
    for key,rule in pairs(entry.parameters) do
        local legacy_optional=(id=='flow_ratio_yolo' and key=='pattern')
            or (id=='pressure_advance_pattern' and (key=='accelerations' or key=='speeds'))
        if p[key]==nil and legacy_optional and not strict_v2 then
            -- Historical v1 parameter objects remain byte-for-byte valid.
        elseif not v1_valid_field(rule,p[key]) then return false end
    end
    if id=='flow_ratio_yolo' then return true end
    if id=='temperature' then return p.start>=p['end']+5 end
    if id=='pressure_advance_pattern' and p.accelerations and p.speeds
        and #p.accelerations>0 and #p.speeds>0 then
        local min_accel=p.accelerations[1];local max_speed=p.speeds[1]
        for _,value in ipairs(p.accelerations) do if value<min_accel then min_accel=value end end
        for _,value in ipairs(p.speeds) do if value>max_speed then max_speed=value end end
        if min_accel<=max_speed then return false end
    end
    return p['end']>=p.start+p.step and (strict_v2 or (p['end']-p.start)/p.step<=1000)
end
local function v1_identity(data)
    return v1_session and type(data)=='table' and data.request_id==v1_session.request.request_id
        and data.origin_id==v1_session.request.origin_id
end
local function v1_persist()
    local ok=pcall(helix.storage.set,'v1_session',v1_session)
    if not ok then
        v1_completion_presentation.disarm()
        if v1_session then v1_session.phase='uncertain' end
        v1_set('message','Local storage unavailable · actions locked')
        for _,key in ipairs({'confirm_on','start_on','cancel_on','evaluate_on'}) do v1_set(key,0) end
    end
    return ok
end
-- Backward-compatible bridge for the amendment's warning and official-preset
-- transaction states. The exact v1 request/result/ACK objects above remain
-- unchanged while the current coordinator uses this versioned envelope.
local function v1_v2(s)
    if not s.v2 then s.v2={schema=V1_NATIVE_ADAPTER_SCHEMA,application_sequence=0} end
    return s.v2
end
local function v1_application(s)
    return s and s.v2 and s.v2.application or nil
end
local v1_v2_validate_prepared
local v1_prepared_qualified
local v1_prepared_reason
-- V1_PARAMETER_CONTROLS
local function v1_options()
    local out={}
    local e=v1_session and v1_session.evaluation
    if e then for _,value in ipairs(e.options) do out[#out+1]=tostring(value)..(e.unit~='' and (' '..e.unit) or '') end end
    return #out>0 and table.concat(out,'\n') or 'Unavailable'
end
local v1_open_job
local v1_open_result
local v1_refresh_job=false
v1_open_job=function()
    if not v1_session then return end
    if v1_session.result then v1_open_result();return end
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
local function v1_retire_preparation_views()
    local job,wizard,detail=v1_job_handle,v1_wizard_handle,v1_detail_handle
    v1_job_handle=nil;v1_wizard_handle=nil;v1_detail_handle=nil
    v1_cancel_pending=false;v1_refresh_job=false
    if job then pcall(job.close) end
    if detail then pcall(detail.close) end
    if wizard then pcall(wizard.close) end
end
-- Only an explicit Return click or manual Resume calls this. ACK/status only
-- update subjects, so an unrelated native page can never be covered on receipt.
v1_open_result=function()
    if not v1_session or not v1_session.result then return end
    if v1_result_handle then
        v1_refresh_result=true;local old=v1_result_handle;v1_result_handle=nil;pcall(old.close);return
    end
    local handle
    handle=helix.ui.overlay('orcacal__v1_result',{on_close=function()
        if v1_result_handle==handle then v1_result_handle=nil end
        if v1_refresh_result then v1_refresh_result=false;v1_open_result() end
    end})
    v1_result_handle=handle
end
helix.ui.on('v1_result_close',function()
    v1_refresh_result=false
    if v1_result_handle then local h=v1_result_handle;v1_result_handle=nil;pcall(h.close) end
end)
local function v1_monitor_text(m)
    if not m or (m.progress==nil and m.elapsed_s==nil) then return 'Progress unavailable' end
    local progress=m.progress~=nil and (tostring(math.floor(m.progress*100+0.5))..'%') or 'Progress unavailable'
    local elapsed=m.elapsed_s~=nil and (tostring(math.floor(m.elapsed_s/60))..'m elapsed') or 'Elapsed unavailable'
    return progress..' · '..elapsed
end
local function v1_open_wizard()
    local handle
    handle=helix.ui.overlay('orcacal__wizard',{on_close=function()
        if v1_wizard_handle==handle then v1_wizard_handle=nil end
    end})
    v1_wizard_handle=handle
end
local function v1_context(o)
    v1_set('printer',o and (o.printer..' · '..tostring(o.nozzle_mm)..' mm') or 'No Orca context')
    local slot=o and o.origin_filament and (' · slot '..tostring(o.origin_filament.slot_number)) or ''
    v1_set('profiles',o and (o.filament..slot..' · '..o.process) or 'Open the V1 companion in Orca')
    v1_set('context_note','Originating filament preset · Orca keeps changes unsaved for review')
end
local function v1_offer_context(o)
    v1_set('offer_printer',o and (o.printer..' · '..tostring(o.nozzle_mm)..' mm') or 'No Orca context')
    local slot=o and o.origin_filament and (' · slot '..tostring(o.origin_filament.slot_number)) or ''
    v1_set('offer_profiles',o and (o.filament..slot..' · '..o.process) or 'Open the V1 companion in Orca')
    v1_set('offer_note','Selected Orca profiles · changes stay unsaved until you save in Orca')
end
local function v1_render()
    v1_offer_context(v1_offer)
    if not v1_session then
        v1_context(v1_offer);v1_set('message','Choose a calibration and configure its parameters.')
        v1_set('warning_on',0);v1_set('retry_on',0);v1_set('application_note','')
        return
    end
    local s=v1_session
    v1_context(s.offer)
    v1_set('resume_on',1);v1_set('calibration',V1_CATALOG[s.request.calibration].name)
    local labels={requested='Preparation requested',preparing='Preparing print',warning='Review Orca warning',blocked='Preparation unavailable',review='Review your print',confirmed='Ready to start',starting='Starting print',printing='Printing',verifying='Checking completion',complete='Ready to evaluate',cancelled='Print cancelled',failed='Print did not complete',uncertain='Check printer connection',returning='Returning your result',delivered='Result returned'}
    local tiles={complete='Pick',printing='Print',blocked='Check',cancelled='Stop',failed='Check'}
    local applied=v1_application(s) and v1_application(s).state=='applied'
    v1_set('phase',labels[s.phase] or 'Status unavailable');v1_set('tile',s.result and ((s.receipt or applied) and 'Done' or 'Send') or tiles[s.phase] or 'Active')
    v1_set('message',s.message or '')
    local p=s.request.parameters
    local kind=s.request.calibration
    local unit=kind=='temperature' and '°C' or kind=='retraction' and 'mm' or kind=='max_volumetric_speed' and 'mm³/s' or 's'
    local summary=kind=='flow_ratio_yolo' and ((p.pass==2 and 'YOLO Perfectionist · 16 samples' or 'YOLO Recommended · 11 samples')..' · Archimedean surface') or
        (tostring(p.start)..' to '..tostring(p['end'])..' '..unit..' · '..tostring(p.step)..' '..unit..' increments')
    if kind=='temperature' then summary=summary..(p.scale and ' · Scaled for nozzle' or ' · Original tower size') end
    v1_set('parameters',summary)
    local prepared=s.prepared
    local artifact=prepared and prepared.artifact
    v1_set('artifact',artifact and ('Print file ready · '..string.format('%.1f',artifact.size/1000000)..' MB') or 'No prepared file')
    v1_set('qualification',v1_prepared_reason(prepared))
    local qualified=v1_prepared_qualified(prepared) and artifact~=nil
    local warning=s.v2 and s.v2.warning
    local warning_blocks=warning and (not warning.decision or warning.decision.action~='continue')
    v1_set('confirm_on',s.phase=='review' and qualified and not s.intent and not warning_blocks and 1 or 0)
    v1_set('start_on',s.phase=='confirmed' and qualified and s.intent and s.intent.action=='confirm' and 1 or 0)
    v1_set('cancel_on',(s.phase=='printing' and s.intent and s.intent.action=='start') and 1 or 0)
    v1_set('evaluate_on',s.phase=='complete' and s.evaluation and not s.result and 1 or 0)
    v1_set('evaluation_note',s.phase=='complete' and 'Choose the best result from the completed calibration.' or '')
    v1_set('monitor_on',(s.phase=='starting' or s.phase=='printing' or s.phase=='verifying' or s.phase=='uncertain') and 1 or 0)
    v1_set('monitor',v1_monitor_text(s.monitor))
    v1_set('warning_on',warning and not warning.decision and not (s.intent and s.intent.action=='cancel') and 1 or 0)
    v1_set('warning_heading',warning and warning.title or '')
    v1_set('warning_message',warning and warning.message or '')
    local units={temperature='°C',flow_ratio_yolo='',pressure_advance_pattern='s',retraction='mm',max_volumetric_speed='mm³/s'}
    local result_unit=units[s.request.calibration]
    local application=v1_application(s)
    local application_state=application and application.state or nil
    local suffix=application_state=='applied' and ' · APPLIED · UNSAVED'
        or application_state=='failed' and ' · NOT APPLIED'
        or application_state=='legacy_returned' and ' · NOT APPLIED'
        or application_state and ' · APPLICATION PENDING'
        or ' · NOT APPLIED'
    v1_set('returned',s.result and (tostring(s.result.value)..(result_unit~='' and (' '..result_unit) or '')..suffix) or '')
    v1_set('result_heading',application_state=='applied' and 'Applied in Orca'
        or application_state=='failed' and 'Application needs attention'
        or application_state=='applying' and 'Applying in Orca'
        or application_state=='pending' and 'Ready for Orca'
        or s.receipt and 'Returned' or 'Returning result')
    v1_set('result_note',application_state=='applied' and 'The originating filament preset is modified and unsaved.'
        or application_state=='failed' and 'Nothing was applied. Review the message and retry.'
        or application_state=='applying' and 'Orca is applying one official preset transaction.'
        or application_state=='pending' and 'Waiting for the originating Orca companion.'
        or s.receipt and 'Received by original Orca without applying.' or 'Waiting for original Orca.')
    v1_set('application_note',application and application.message or '')
    v1_set('retry_on',application_state=='failed' and application.retry_authorization~=nil and 1 or 0)
end
local function v1_capability(offer,id)
    if not offer then return nil end
    for _,c in ipairs(offer.capabilities) do if c.id==id then return c end end
end
local function v1_valid_v2_origin(o)
    local origin=o.origin_filament
    if type(origin)~='table' or not v1_exact(origin,'slot_number preset_name shared_slots')
        or not v1_number(origin.slot_number) or origin.slot_number<1 or origin.slot_number%1~=0
        or not v1_text(origin.preset_name,128) or type(origin.shared_slots)~='table' or #origin.shared_slots<1 or #origin.shared_slots>64 then return false end
    if type(o.filament_slots)~='table' or #o.filament_slots<1 or #o.filament_slots>64 then return false end
    local included=false;local origin_named=false;local seen={}
    for _,entry in ipairs(o.filament_slots) do
        if type(entry)~='table' or not v1_exact(entry,'slot_number preset_name')
            or not v1_number(entry.slot_number) or entry.slot_number<1 or entry.slot_number%1~=0
            or seen[entry.slot_number] or not v1_text(entry.preset_name,128) then return false end
        seen[entry.slot_number]=true
        if entry.slot_number==origin.slot_number and entry.preset_name==origin.preset_name then origin_named=true end
    end
    for _,slot in ipairs(origin.shared_slots) do
        if not v1_number(slot) or slot<1 or slot%1~=0 then return false end
        if not seen[slot] then return false end
        if slot==origin.slot_number then included=true end
    end
    return included and origin_named
end
local function v1_receive_offer(_,o)
    local v2=type(o)=='table' and o.schema=='helix-orca-v1-offer/v2'
    local fields=v2 and 'schema origin_id request_id context_sha256 printer process filament nozzle_mm capabilities defaults created_at expires_at extruder_type origin_filament filament_slots'
        or 'schema origin_id request_id context_sha256 printer process filament nozzle_mm capabilities defaults created_at expires_at extruder_type'
    if not v1_exact(o,fields) or (o.schema~='helix-orca-v1-offer/v1' and not v2)
        or not v1_hex(o.origin_id,32) or not v1_hex(o.request_id,32) or not v1_hex(o.context_sha256,64)
        or not v1_text(o.printer,128) or not v1_text(o.process,128) or not v1_text(o.filament,128)
        or not v1_number(o.nozzle_mm) or o.nozzle_mm<=0 or o.nozzle_mm>2
        or not v1_number(o.created_at) or not v1_number(o.expires_at) or o.expires_at<=o.created_at
        or type(o.defaults)~='table' or type(o.capabilities)~='table' or #o.capabilities~=5
        or (v2 and not v1_valid_v2_origin(o)) then return end
    local seen={}
    for _,c in ipairs(o.capabilities) do
        if type(c)~='table' or not V1_CATALOG[c.id] or seen[c.id] or type(c.available)~='boolean' or not v1_text(c.reason,512) then return end
        seen[c.id]=true
    end
    if o.extruder_type~=nil and o.extruder_type~='direct_drive' and o.extruder_type~='bowden' and o.extruder_type~='unavailable' then return end
    for id,_ in pairs(V1_CATALOG) do
        if not v1_valid_parameters(id,o.defaults[id],v2) then return end
    end
    v1_offer=o;v1_offer_context(o)
    for id,_ in pairs(V1_CATALOG) do
        local c=v1_capability(o,id)
        v1_set('availability_'..id,(c.available and 'Preparation available · ' or 'Blocked · ')..c.reason)
    end
    if not v1_session then v1_render() end
end
helix.ui.on('open',v1_open_wizard)
helix.ui.on('v1_resume',v1_open_job)
helix.ui.on('v1_choose',function(id)
    if not V1_CATALOG[id] then return end
    if v1_session and not v1_session.receipt and v1_session.phase~='blocked' and v1_session.phase~='failed' and v1_session.phase~='cancelled' then
        v1_set('message','Finish or return the active calibration before starting another.');v1_open_job();return
    end
    v1_prepare_draft(id)
    local handle
    handle=helix.ui.overlay('orcacal__v1_'..id,{on_close=function()
        if v1_detail_handle==handle then v1_detail_handle=nil end
    end})
    v1_detail_handle=handle
end)
helix.ui.on('v1_generate',function(id)
    local c=v1_capability(v1_offer,id)
    if not c then v1_set('message','Waiting for Orca context');return end
    if v1_session and v1_session.request.request_id==v1_offer.request_id then v1_set('message','This request was already submitted. Open the active calibration.');return end
    if v1_session and not v1_session.receipt and v1_session.phase~='blocked' and v1_session.phase~='failed' and v1_session.phase~='cancelled' then return end
    local draft=v1_prepare_draft(id)
    local parameters={}
    for key,value in pairs(draft) do parameters[key]=value end
    local use_v2=v1_offer.schema=='helix-orca-v1-offer/v2'
    if not use_v2 then
        -- Historical v1 never carried the beta.12 Pattern/list controls. Keep
        -- its fixture and retained wire objects byte-shape compatible.
        if id=='flow_ratio_yolo' then parameters.pattern=nil end
        if id=='pressure_advance_pattern' then parameters.accelerations=nil;parameters.speeds=nil end
    end
    if not v1_valid_parameters(id,parameters,use_v2) then
        v1_set('message',id=='temperature' and 'Use whole temperatures in steps of 5, with start at least 5 above end.'
            or id=='pressure_advance_pattern' and 'End must exceed start by step; acceleration values must exceed speed values.'
            or 'End must be at least start plus a positive step.');return
    end
    local request={schema=use_v2 and 'helix-orca-v1-request/v2' or 'helix-orca-v1-request/v1',request_id=v1_offer.request_id,origin_id=v1_offer.origin_id,
        context_sha256=v1_offer.context_sha256,calibration=id,parameters=parameters,
        created_at=v1_offer.created_at,expires_at=v1_offer.expires_at}
    if not use_v2 then request.not_applied=true end
    v1_completion_presentation.disarm()
    v1_session={request=request,offer=v1_offer,phase='requested',sequence=0,message='Generation requested · nothing started'}
    if use_v2 then
        v1_session.v2={schema=V1_NATIVE_ADAPTER_SCHEMA,application_sequence=0,
            origin_filament=v1_offer.origin_filament}
    end
    if v1_persist() then v1_render();v1_open_job() end
end)
-- V2 adapter boundary. Keep the build qualification independent of this
-- request: its digest binds a route/source/executable once, while artifact and
-- processing belong to the exact request. The lead may align outer field names
-- here when the shared Python v2 schema freezes; legacy v1 stays untouched.
v1_v2_validate_prepared=function(p)
    if type(p)~='table' or p.schema~='helix-orca-v1-prepared/v2'
        or not v1_exact(p,'schema request_id origin_id context_sha256 request_sha256 calibration parameters artifact generator processing')
        or not v1_exact(p.generator,'source_commit route executable_sha256 qualification_sha256')
        or not v1_hex(p.generator.source_commit,40) or not v1_text(p.generator.route,128)
        or not v1_hex(p.generator.executable_sha256,64) or not v1_hex(p.generator.qualification_sha256,64)
        or not v1_exact(p.processing,'error_code warnings status')
        or not v1_number(p.processing.error_code) or p.processing.error_code<0 or p.processing.error_code%1~=0
        or (p.processing.status~='ready' and p.processing.status~='blocked')
        or type(p.processing.warnings)~='table' or #p.processing.warnings>64 then return false end
    for _,warning in ipairs(p.processing.warnings) do
        if not v1_exact(warning,'level message error_code params known requires_ack')
            or not v1_number(warning.level) or warning.level<0 or warning.level%1~=0
            or not v1_text(warning.message,512) or not v1_text(warning.error_code,32)
            or type(warning.params)~='table' or #warning.params>32
            or type(warning.known)~='boolean' or type(warning.requires_ack)~='boolean' then return false end
        for _,param in ipairs(warning.params) do if type(param)~='string' or #param>512 then return false end end
    end
    local ready=p.processing.error_code==0
    for _,warning in ipairs(p.processing.warnings) do if not warning.known then ready=false end end
    return p.processing.status==(ready and 'ready' or 'blocked')
end
v1_prepared_qualified=function(p)
    return p and ((p.schema=='helix-orca-v1-prepared/v1' and p.parity and p.parity.qualified==true)
        or (p.schema=='helix-orca-v1-prepared/v2' and v1_v2_validate_prepared(p) and p.processing.status=='ready'))
end
v1_prepared_reason=function(p)
    if not p then return 'Waiting for Orca preparation' end
    if p.schema=='helix-orca-v1-prepared/v2' then
        return p.processing.status=='ready' and ('Qualified Orca build · '..p.generator.route) or 'Orca blocked this preparation'
    end
    return p.parity and p.parity.reason or 'Generator qualification unavailable'
end
local function v1_prepared(p,digest)
    local r=v1_session.request
    local core=p.request_id==r.request_id and p.origin_id==r.origin_id
        and p.context_sha256==r.context_sha256 and p.calibration==r.calibration and v1_same(p.parameters,r.parameters)
        and v1_hex(p.request_sha256,64) and v1_hex(digest,64)
        and (p.artifact==nil or (v1_exact(p.artifact,'name size sha256') and v1_text(p.artifact.name,255) and p.artifact.name:match('^[A-Za-z0-9][A-Za-z0-9_.-]*%.gcode$') and not p.artifact.name:find('..',1,true) and v1_number(p.artifact.size)
            and p.artifact.size>0 and p.artifact.size<=100000000 and p.artifact.size%1==0 and v1_hex(p.artifact.sha256,64)))
    if not core then return false end
    if p.schema=='helix-orca-v1-prepared/v1' then
        return v1_exact(p,'schema request_id origin_id context_sha256 request_sha256 calibration parameters artifact generator parity not_applied')
            and p.not_applied==true and v1_exact(p.generator,'build route')
            and v1_text(p.generator.build,128) and v1_text(p.generator.route,128)
            and v1_exact(p.parity,'qualified report_sha256 reason')
            and type(p.parity.qualified)=='boolean' and v1_text(p.parity.reason,512)
            and (not p.parity.qualified or v1_hex(p.parity.report_sha256,64))
            and (not p.parity.qualified or p.artifact~=nil)
    end
    return v1_v2_validate_prepared(p) and p.artifact~=nil
end
local v1_phases={requested=true,preparing=true,warning=true,blocked=true,review=true,confirmed=true,starting=true,printing=true,verifying=true,complete=true,cancelled=true,failed=true,uncertain=true,returning=true,delivered=true}
local function v1_valid_warning_ack(ack,prepared_sha256)
    if ack==nil then return true end
    if not v1_exact(ack,'schema request_id prepared_sha256 warning_codes acknowledged_at')
        or ack.schema~='helix-orca-v1-warning-ack/v2' or ack.request_id~=v1_session.request.request_id
        or ack.prepared_sha256~=prepared_sha256 or type(ack.warning_codes)~='table'
        or not v1_number(ack.acknowledged_at) or ack.acknowledged_at<0 or ack.acknowledged_at%1~=0 then return false end
    for _,code in ipairs(ack.warning_codes) do if not v1_text(code,32) then return false end end
    return true
end
local function v1_status_warning(s,d)
    if d.phase~='warning' then return true end
    if not d.prepared or d.prepared.schema~='helix-orca-v1-prepared/v2' then return false end
    local codes={}
    for _,warning in ipairs(d.prepared.processing.warnings) do
        if warning.requires_ack then codes[#codes+1]=warning.error_code end
    end
    if #codes==0 then return false end
    table.sort(codes)
    local adapter=v1_v2(s);local retained=adapter.warning
    if retained and retained.prepared_sha256~=d.prepared_sha256 then return false end
    if retained and not v1_same(retained.warning_codes,codes) then return false end
    return true
end
local function v1_receive_status(_,d)
    local status_v2=v1_session and v1_session.request.schema=='helix-orca-v1-request/v2'
    local fields=status_v2 and 'schema request_id origin_id sequence phase message prepared job_id prepared_sha256 completion_sha256 evaluation monitor warning_ack qualification_sha256'
        or 'schema request_id origin_id sequence phase message prepared job_id prepared_sha256 completion_sha256 evaluation monitor'
    if not v1_exact(d,fields) or not v1_identity(d)
        or d.schema~=(status_v2 and 'helix-orca-v1-status/v2' or 'helix-orca-v1-status/v1') or not v1_phases[d.phase]
        or not v1_number(d.sequence) or d.sequence%1~=0 or d.sequence<=v1_session.sequence or not v1_text(d.message,768) then return end
    if status_v2 and ((d.qualification_sha256~=nil and not v1_hex(d.qualification_sha256,64))
        or not v1_valid_warning_ack(d.warning_ack,d.prepared_sha256)) then return end
    if d.monitor~=nil then
        local m=d.monitor
        if not v1_exact(m,'elapsed_s progress')
            or (m.elapsed_s~=nil and (not v1_number(m.elapsed_s) or m.elapsed_s<0 or m.elapsed_s>2678400))
            or (m.progress~=nil and (not v1_number(m.progress) or m.progress<0 or m.progress>1)) then return end
    end
    local s=v1_session
    local transitions={requested={requested=true,preparing=true,warning=true,blocked=true,review=true,failed=true,uncertain=true},
        preparing={preparing=true,warning=true,blocked=true,review=true,failed=true,uncertain=true},
        warning={warning=true,review=true,cancelled=true,blocked=true,failed=true,uncertain=true},
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
    local recovering=s.recovery_required==true and s.phase=='uncertain'
    -- The coordinator durably republishes after inspecting the retained marker.
    -- Keep normal strict monotonic sequencing; equal/replayed status never unlocks.
    if recovering and ((s.prepared and not v1_same(s.prepared,d.prepared))
        or (s.prepared_sha256 and s.prepared_sha256~=d.prepared_sha256)
        or (s.job_id and s.job_id~=d.job_id)
        or (s.completion_sha256 and s.completion_sha256~=d.completion_sha256)) then return end
    if status_v2 and not v1_status_warning(s,d) then return end
    local action=s.intent and s.intent.action
    if d.phase=='confirmed' and ((s.phase~='review' and not recovering) or action~='confirm') then return end
    if (d.phase=='starting' or d.phase=='printing' or d.phase=='verifying' or d.phase=='complete') and action~='start' then return end
    if d.phase=='review' and (action~=nil or not v1_prepared_qualified(d.prepared)) then return end
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
    if d.phase=='failed' or d.phase=='cancelled' or d.phase=='uncertain' or d.phase=='blocked' then
        v1_completion_presentation.disarm()
    elseif d.phase=='printing' then v1_completion_presentation.arm(s) end
    s.sequence=d.sequence;s.phase=d.phase;s.message=d.message;s.recovery_required=nil;s.monitor=d.monitor
    if status_v2 and d.warning_ack then
        s.warning_ack=d.warning_ack
        local warning=s.v2 and s.v2.warning
        if warning then warning.decision=warning.decision or {action='continue'} end
    end
    if d.prepared then s.prepared=d.prepared;s.prepared_sha256=d.prepared_sha256 end
    if d.job_id then s.job_id=d.job_id end
    local present=d.phase=='complete' and v1_completion_presentation.claim(s)
    if not v1_persist() then return end
    v1_render()
    if d.phase=='warning' then v1_open_warning()
    elseif present then v1_completion_presentation.open(v1_options())
    elseif d.phase=='complete' and v1_job_handle then v1_open_job() end
end
local function v1_intent(action)
    local s=v1_session
    if not s or not s.prepared or not v1_prepared_qualified(s.prepared) or not v1_hex(s.prepared_sha256,64) then return end
    local warning=s.v2 and s.v2.warning
    if action~='cancel' and warning and (not warning.decision or warning.decision.action~='continue') then return end
    if action=='confirm' and (s.phase~='review' or s.intent) then return end
    if action=='start' and (s.phase~='confirmed' or not s.intent or s.intent.action~='confirm') then return end
    if action=='cancel' and s.phase~='warning' and (s.phase~='printing' or not s.intent or s.intent.action~='start') then return end
    local serial=action=='confirm' and 1 or action=='start' and 2 or 3
    s.intent={schema=s.request.schema=='helix-orca-v1-request/v2' and 'helix-orca-v1-intent/v2' or 'helix-orca-v1-intent/v1',request_id=s.request.request_id,origin_id=s.request.origin_id,
        prepared_sha256=s.prepared_sha256,action=action,intent_id=s.request.request_id:sub(1,24)..string.format('%08x',serial)}
    if action=='start' then s.phase='starting';s.message='Start requested · waiting for coordinator'
    elseif action=='cancel' then s.message='Cancellation requested · waiting for verified status'
    else s.message='Confirmation sent · waiting for coordinator' end
    if v1_persist() then
        if action=='start' then v1_completion_presentation.arm(s) end
        v1_render()
    end
end
for _,action in ipairs({'confirm','start'}) do helix.ui.on('v1_'..action,function() v1_intent(action) end) end
helix.ui.on('v1_cancel',function()
    if not v1_session or v1_session.phase~='printing' or v1_cancel_pending then return end
    local request=v1_session.request.request_id
    v1_cancel_pending=true
    local ok=pcall(helix.ui.confirm,'Cancel this calibration print?',
        'The current print will stop. A new completed calibration is required before choosing a result.',{
            severity='warning',confirm_text='Cancel print',
            on_confirm=function()
                v1_cancel_pending=false
                if v1_session and v1_session.request.request_id==request then v1_intent('cancel') end
            end,
            on_cancel=function() v1_cancel_pending=false end})
    if not ok then v1_cancel_pending=false;v1_set('message','Another confirmation is open. Try again after closing it.') end
end)
helix.ui.on('v1_return',function()
    local s=v1_session
    if not s or s.phase~='complete' or s.result or not s.evaluation then return end
    local value=s.evaluation.options[v1_subjects.evaluation_idx:get()+1]
    if value==nil then return end
    local result_v2=s.request.schema=='helix-orca-v1-request/v2'
    s.result={schema=result_v2 and 'helix-orca-v1-result/v2' or 'helix-orca-v1-result/v1',request_id=s.request.request_id,origin_id=s.request.origin_id,
        context_sha256=s.request.context_sha256,prepared_sha256=s.prepared_sha256,job_id=s.job_id,
        completion_sha256=s.completion_sha256,setting=s.evaluation.setting,value=value}
    if not result_v2 then s.result.not_applied=true end
    local adapter=v1_v2(s)
    adapter.application={schema='helix-orca-v1-application-state/v2',state='pending',sequence=0,
        attempt=1,message='Waiting for Orca to apply the official preset transaction.'}
    s.phase='returning';s.message='Result committed locally · waiting for Orca preset transaction'
    if v1_persist() then
        v1_completion_presentation.close();v1_retire_preparation_views()
        v1_render();v1_open_result()
    end
end)
local function v1_receive_ack(_,d)
    local v2=type(d)=='table' and d.schema=='helix-orca-v1-ack/v2'
    local fields=v2 and 'schema request_id origin_id result_sha256 application_sha256 status'
        or 'schema request_id origin_id result_sha256 result not_applied'
    if not v1_exact(d,fields) or not v1_identity(d) or not v1_hex(d.result_sha256,64)
        or not v1_session.result then return end
    if v2 then
        if v1_session.result.schema~='helix-orca-v1-result/v2' or d.status~='applied'
            or not v1_hex(d.application_sha256,64) then return end
        local known=v1_application(v1_session)
        if known and known.result_sha256 and known.result_sha256~=d.result_sha256 then return end
    elseif d.schema~='helix-orca-v1-ack/v1' or d.not_applied~=true
        or v1_session.result.schema~='helix-orca-v1-result/v1' or not v1_same(d.result,v1_session.result) then return end
    if v1_session.receipt then return end
    v1_session.receipt=d;v1_session.phase='delivered'
    v1_session.message=v2 and 'Applied to originating filament preset · unsaved in Orca' or 'Returned to original Orca · NOT APPLIED'
    local adapter=v1_v2(v1_session)
    if v2 then
        local transaction_id=adapter.application and adapter.application.transaction_id
        if not v1_text(transaction_id,128) then transaction_id=d.application_sha256 end
        adapter.application={schema='helix-orca-v1-application-state/v2',state='applied',
            sequence=adapter.application_sequence or 0,attempt=(adapter.application and adapter.application.attempt) or 1,
            message='Result applied to the edited originating filament preset; it remains unsaved.',
            result_sha256=d.result_sha256,application_sha256=d.application_sha256,dirty=true,unsaved=true,
            transaction_id=transaction_id,retry_authorization=nil}
    else
        adapter.application={schema='helix-orca-v1-application-state/v2',state='legacy_returned',sequence=0,
            attempt=1,message='Legacy companion received the result without applying it.'}
    end
    adapter.application_retry=nil;v1_session.application_retry=nil
    if v1_persist() then v1_render() end
end
local function v1_close_warning()
    local handle=v1_warning_handle;v1_warning_handle=nil
    if handle then pcall(handle.close) end
end
v1_open_warning=function()
    local warning=v1_session and v1_session.v2 and v1_session.v2.warning
    if not warning or warning.decision or v1_warning_handle then return end
    local handle
    local ok=pcall(function()
        handle=helix.ui.dialog('orcacal__v1_warning',{on_close=function()
            if v1_warning_handle==handle then v1_warning_handle=nil end
        end})
    end)
    if ok then v1_warning_handle=handle end
end
local function v1_warning_decision(action)
    local s=v1_session;local warning=s and s.v2 and s.v2.warning
    if not warning or warning.decision or (action~='continue' and action~='cancel') then return end
    if action=='cancel' then
        -- Cancellation has one actionable envelope: intent/v2. Do not also
        -- emit a warning-decision command with a different intent identity.
        s.message='Warning cancelled · nothing started';v1_close_warning();v1_intent('cancel');return
    end
    warning.decision={schema='helix-orca-v1-native-warning-decision/v2',request_id=s.request.request_id,
        origin_id=s.request.origin_id,prepared_sha256=warning.prepared_sha256,warning_sha256=warning.warning_sha256,
        warning_codes=warning.warning_codes,action=action,
        intent_id=s.request.request_id:sub(1,24)..'00000004'}
    -- Native has no authoritative wall clock. Persist only the deliberate
    -- decision; the coordinator bridge mints warning_ack and returns that
    -- canonical object on status/v2.
    s.message='Warning accepted · Orca may continue preparation'
    v1_close_warning()
    if v1_persist() then v1_render() end
end
helix.ui.on('v1_warning_continue',function() v1_warning_decision('continue') end)
helix.ui.on('v1_warning_cancel',function() v1_warning_decision('cancel') end)
helix.ui.on('v1_warning_reopen',v1_open_warning)
local function v1_receive_warning_v2(_,d)
    local s=v1_session
    if not s or s.request.schema~='helix-orca-v1-request/v2' or s.phase~='warning' or not s.prepared
        or not v1_exact(d,'schema request_id origin_id prepared_sha256 warning_sha256 warning_codes title message')
        or d.schema~='helix-orca-v1-native-warning/v2' or not v1_identity(d)
        or d.prepared_sha256~=s.prepared_sha256 or not v1_hex(d.warning_sha256,64)
        or type(d.warning_codes)~='table' or #d.warning_codes<1 or #d.warning_codes>64
        or not v1_text(d.title,96) or not v1_text(d.message,512) then return end
    local expected={};local seen={}
    for _,warning in ipairs(s.prepared.processing.warnings) do
        if warning.requires_ack then expected[#expected+1]=warning.error_code end
    end
    table.sort(expected)
    if #expected~=#d.warning_codes then return end
    for index,code in ipairs(d.warning_codes) do
        if not v1_text(code,32) or seen[code] or code~=expected[index] then return end
        seen[code]=true
    end
    local adapter=v1_v2(s)
    if adapter.warning and not v1_same(adapter.warning,d) then return end
    adapter.warning=d
    if v1_persist() then v1_render();v1_open_warning() end
end
local v1_application_states={applying=true,applied=true,failed=true}
local function v1_retry_authorization(value,d)
    if value==nil then return true end
    return type(value)=='table'
        and v1_exact(value,'schema request_id origin_id result_sha256 failed_application_sha256 attempt token authorized_at')
        and value.schema=='helix-orca-v1-application-retry/v2'
        and value.request_id==d.request_id and value.origin_id==d.origin_id
        and value.result_sha256==d.result_sha256 and v1_hex(value.failed_application_sha256,64)
        and v1_number(value.attempt) and value.attempt>=2 and value.attempt%1==0
        and v1_hex(value.token,32) and v1_number(value.authorized_at) and value.authorized_at>=0 and value.authorized_at%1==0
end
local function v1_receive_application_v2(_,d)
    if not v1_exact(d,'schema request_id origin_id sequence state message result_sha256 result transaction_id dirty unsaved retry_authorization')
        or not v1_identity(d) or d.schema~='helix-orca-v1-application/v2'
        or not v1_number(d.sequence) or d.sequence%1~=0 or d.sequence<1
        or not v1_application_states[d.state] or not v1_text(d.message,512)
        or not v1_hex(d.result_sha256,64) or not v1_session.result or not v1_same(d.result,v1_session.result)
        or type(d.dirty)~='boolean' or type(d.unsaved)~='boolean'
        or type(d.transaction_id)~='string' or #d.transaction_id>128 or d.transaction_id:find('%c')
        or not v1_retry_authorization(d.retry_authorization,d) then return end
    if d.state=='applied' and (not v1_text(d.transaction_id,128) or d.dirty~=true or d.unsaved~=true) then return end
    if d.state~='applied' and (d.dirty~=false or d.unsaved~=false) then return end
    local adapter=v1_v2(v1_session)
    if d.sequence<=adapter.application_sequence then return end
    adapter.application_sequence=d.sequence
    adapter.application={schema='helix-orca-v1-application-state/v2',state=d.state,sequence=d.sequence,
        attempt=(adapter.application and adapter.application.attempt) or 1,message=d.message,
        result_sha256=d.result_sha256,transaction_id=d.transaction_id,dirty=d.dirty,unsaved=d.unsaved,
        retry_authorization=d.retry_authorization}
    adapter.application_retry=nil
    v1_session.application_retry=nil
    if d.state=='applied' then
        adapter.application.state='applying'
        v1_session.phase='returning';v1_session.message='Orca committed the preset transaction · waiting for exact receipt'
    elseif d.state=='failed' then
        v1_session.phase='returning';v1_session.message='Orca did not apply the result · retry available'
    else
        v1_session.phase='returning';v1_session.message=d.message
    end
    if v1_persist() then v1_render() end
end
helix.ui.on('v1_application_retry',function()
    local s=v1_session;local adapter=s and s.v2;local application=adapter and adapter.application
    if not s or not s.result or not application or application.state~='failed' or application.retry_authorization==nil
        or not v1_retry_authorization(application.retry_authorization,{request_id=s.request.request_id,
            origin_id=s.request.origin_id,result_sha256=application.result_sha256}) then return end
    local authorization=application.retry_authorization
    s.application_retry=authorization
    adapter.application_retry=authorization
    adapter.application={schema='helix-orca-v1-application-state/v2',state='pending',sequence=application.sequence,
        attempt=authorization.attempt,message='Retry requested · waiting for originating Orca.',retry_authorization=nil}
    s.message='Application retry requested · no preset change confirmed yet'
    if v1_persist() then v1_render() end
end)
helix.moonraker.on_agent_event('helix_orca_v1.context.v1',v1_receive_offer)
helix.moonraker.on_agent_event('helix_orca_v1.status.v1',v1_receive_status)
helix.moonraker.on_agent_event('helix_orca_v1.ack.v1',v1_receive_ack)
helix.moonraker.on_agent_event('helix_orca_v1.context.v2',v1_receive_offer)
helix.moonraker.on_agent_event('helix_orca_v1.status.v2',v1_receive_status)
helix.moonraker.on_agent_event('helix_orca_v1.ack.v2',v1_receive_ack)
helix.moonraker.on_agent_event('helix_orca_v1.warning.v2',v1_receive_warning_v2)
helix.moonraker.on_agent_event('helix_orca_v1.application.v2',v1_receive_application_v2)
-- Recover retained state without replaying any request/intent or restoring an action.
local v1_ok,v1_saved=pcall(helix.storage.get,'v1_session')
local function v1_restore_v2(s)
    local adapter=s.v2
    if adapter==nil then return end
    if type(adapter)~='table' or adapter.schema~=V1_NATIVE_ADAPTER_SCHEMA
        or not v1_number(adapter.application_sequence or 0) or (adapter.application_sequence or 0)%1~=0 then
        s.v2=nil;return
    end
    if adapter.warning and (type(adapter.warning)~='table' or adapter.warning.schema~='helix-orca-v1-native-warning/v2'
        or adapter.warning.request_id~=s.request.request_id or adapter.warning.origin_id~=s.request.origin_id
        or not v1_hex(adapter.warning.prepared_sha256,64) or not v1_hex(adapter.warning.warning_sha256,64)
        or type(adapter.warning.warning_codes)~='table'
        or not v1_text(adapter.warning.title,96) or not v1_text(adapter.warning.message,512)) then adapter.warning=nil end
    local application=adapter.application
    if application and (type(application)~='table' or application.schema~='helix-orca-v1-application-state/v2'
        or not v1_application_states[application.state] and application.state~='pending' and application.state~='legacy_returned'
        or not v1_number(application.sequence or 0) or not v1_number(application.attempt or 1)
        or not v1_text(application.message,512)) then adapter.application=nil;application=nil end
    if application and application.retry_authorization~=nil
        and not v1_retry_authorization(application.retry_authorization,{request_id=s.request.request_id,
            origin_id=s.request.origin_id,result_sha256=application.result_sha256}) then
        application.retry_authorization=nil
    end
    -- A pending/applying transaction may have committed after the last storage
    -- flush. Never claim success or automatically replay it after restart.
    if application and (application.state=='pending' or application.state=='applying') then
        application.state='failed'
        application.message='Application state needs recheck in Orca before a deliberate retry.'
        adapter.application_retry=nil
    end
    local retry=s.application_retry or adapter.application_retry
    local authorization=application and application.state=='failed' and application.retry_authorization or nil
    if not retry or not authorization or not v1_same(retry,authorization) then
        s.application_retry=nil;adapter.application_retry=nil
    end
end
local function v1_restore(s)
    local request_v2=type(s)=='table' and type(s.request)=='table' and s.request.schema=='helix-orca-v1-request/v2'
    if type(s)~='table' or type(s.request)~='table' or not V1_CATALOG[s.request.calibration]
        or type(s.offer)~='table' or not v1_hex(s.request.request_id,32) or not v1_hex(s.request.origin_id,32)
        or not v1_hex(s.request.context_sha256,64)
        or (not request_v2 and (s.request.schema~='helix-orca-v1-request/v1' or s.request.not_applied~=true))
        or type(s.request.parameters)~='table' or not v1_valid_parameters(s.request.calibration,s.request.parameters,request_v2)
        or not v1_text(s.offer.printer,128) or not v1_text(s.offer.process,128) or not v1_text(s.offer.filament,128)
        or not v1_number(s.offer.nozzle_mm) or not v1_number(s.sequence) or s.sequence<0 or s.sequence%1~=0
        or not v1_phases[s.phase] or (s.message~=nil and not v1_text(s.message,768)) then return false end
    v1_session=s;v1_restore_v2(s)
    if s.prepared and not v1_prepared(s.prepared,s.prepared_sha256) then v1_session=nil;return false end
    if s.intent and (not v1_exact(s.intent,'schema request_id origin_id prepared_sha256 action intent_id')
        or s.intent.schema~=(request_v2 and 'helix-orca-v1-intent/v2' or 'helix-orca-v1-intent/v1') or not v1_identity(s.intent)
        or s.intent.prepared_sha256~=s.prepared_sha256 or not v1_hex(s.intent.intent_id,32)
        or (s.intent.action~='confirm' and s.intent.action~='start' and s.intent.action~='cancel')) then v1_session=nil;return false end
    v1_completion_presentation.recover(s)
    s.monitor=nil -- retained telemetry is not a fresh read of the owned job
    if s.result then
        local r=s.result
        local result_v2=r.schema=='helix-orca-v1-result/v2'
        local fields=result_v2 and 'schema request_id origin_id context_sha256 prepared_sha256 job_id completion_sha256 setting value'
            or 'schema request_id origin_id context_sha256 prepared_sha256 job_id completion_sha256 setting value not_applied'
        if not v1_exact(r,fields) or (result_v2~=request_v2)
            or (not result_v2 and (r.schema~='helix-orca-v1-result/v1' or r.not_applied~=true))
            or not v1_identity(r) or r.context_sha256~=s.request.context_sha256
            or r.prepared_sha256~=s.prepared_sha256 or not v1_hex(r.prepared_sha256,64)
            or not v1_text(r.job_id,128) or not v1_hex(r.completion_sha256,64) or not v1_text(r.setting,128)
            or not v1_number(r.value) then v1_session=nil;return false end
        s.evaluation=nil -- retained result needs no mutable evaluation options
        if s.receipt then
            if result_v2 then
                if not v1_exact(s.receipt,'schema request_id origin_id result_sha256 application_sha256 status')
                    or s.receipt.schema~='helix-orca-v1-ack/v2' or s.receipt.status~='applied'
                    or not v1_hex(s.receipt.result_sha256,64) or not v1_hex(s.receipt.application_sha256,64)
                    or not v1_identity(s.receipt) then s.receipt=nil end
            elseif s.receipt.schema~='helix-orca-v1-ack/v1' or not v1_same(s.receipt.result,r)
                or not v1_hex(s.receipt.result_sha256,64) or s.receipt.not_applied~=true
                or not v1_identity(s.receipt) then s.receipt=nil end
        end
        local application=v1_application(s)
        s.phase=(s.receipt or (application and application.state=='applied')) and 'delivered' or 'returning';s.recovery_required=nil
    elseif s.phase=='blocked' or s.phase=='failed' or s.phase=='cancelled' then
        -- These terminal outcomes authorize no action and must remain dismissible
        -- even if the runtime has already archived them for the next calibration.
        s.evaluation=nil;s.recovery_required=nil
    else
        s.phase='uncertain';s.evaluation=nil;s.recovery_required=true
        s.message='Reconnecting · actions locked until verified coordinator status'
    end
    return true
end
if v1_ok and v1_restore(v1_saved) then v1_persist() end
v1_render()
