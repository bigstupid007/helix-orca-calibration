-- Beta.12 app numeric editor for ordinary values, plus an owned precise editor
-- for Pressure Advance and thousandth-step fields the app's 0..2 decimals
-- cannot represent. Both paths commit through the same bounded draft validator.
local v1_keypad_handle=nil
local v1_editor_open=false
local v1_edit_target=nil
local v1_edit_buffer=''
local function v1_copy_parameters(p)
    local out={}
    for key,value in pairs(p) do
        if type(value)=='table' then local copy={};for i,item in ipairs(value) do copy[i]=item end;out[key]=copy
        else out[key]=value end
    end
    return out
end
local function v1_draft_fields(id,p)
    local entry=V1_CATALOG[id]
    if not entry or type(p)~='table' then return false end
    for key,_ in pairs(p) do if not entry.parameters[key] then return false end end
    for key,rule in pairs(entry.parameters) do if not v1_valid_field(rule,p[key]) then return false end end
    return true
end
local drafts_ok,retained_drafts=pcall(helix.storage.get,'v1_parameter_drafts')
if drafts_ok and type(retained_drafts)=='table' then
    for id,p in pairs(retained_drafts) do if v1_draft_fields(id,p) then v1_drafts[id]=v1_copy_parameters(p) end end
end
local function v1_save_drafts()
    local ok=pcall(helix.storage.set,'v1_parameter_drafts',v1_drafts)
    if not ok then v1_set('message','Draft storage unavailable; keep this view open until submitting.') end
end
local function v1_draw_draft(id)
    local p=v1_drafts[id]
    for key,value in pairs(p) do
        local text=type(value)=='boolean' and (value and 'On' or 'Off')
            or type(value)=='table' and (#value>0 and table.concat(value,',') or 'Automatic') or tostring(value)
        if id=='flow_ratio_yolo' then text=value==1 and 'Recommended' or 'Perfectionist' end
        if id=='flow_ratio_yolo' and key=='pattern' then text=value=='monotonic' and 'Monotonic' or 'Archimedean Chords' end
        v1_set(id..'_'..key..'_value',text)
    end
    if id=='flow_ratio_yolo' then
        if p.pattern==nil then v1_set('flow_ratio_yolo_pattern_value','Archimedean Chords · legacy v1') end
        v1_set('flow_samples',p.pass==1 and '11 samples; fixed additive offsets: -0.05 to +0.05 in 0.01 steps.' or '16 samples; fixed additive offsets: -0.04 to +0.035 in 0.005 steps.')
    end
end
local function v1_prepare_draft(id)
    if not v1_drafts[id] then
        local defaults=v1_offer and v1_offer.defaults[id] or V1_DEFAULTS[id]
        v1_drafts[id]=v1_copy_parameters(defaults)
        if id=='pressure_advance_pattern' then
            v1_drafts[id].accelerations=v1_drafts[id].accelerations or {}
            v1_drafts[id].speeds=v1_drafts[id].speeds or {}
        end
    end
    v1_draw_draft(id)
    if id=='pressure_advance_pattern' then
        local kind=v1_offer and v1_offer.extruder_type
        v1_set('pa_defaults_note',kind=='direct_drive' and 'Orca reports Direct Drive. Use defaults buttons only to replace the editable values.'
            or kind=='bowden' and 'Orca reports Bowden. Use defaults buttons only to replace the editable values.'
            or 'Extruder type not reported; Direct Drive defaults shown initially. Edited values are retained.')
    end
    return v1_drafts[id]
end
local function v1_edit_allowed()
    if v1_session and not v1_session.receipt and v1_session.phase~='blocked' and v1_session.phase~='failed' and v1_session.phase~='cancelled' then
        v1_set('message','The submitted request is fixed. Finish the active calibration before editing.');return false
    end
    return true
end
local function v1_commit_edit(id,key,value)
    local rule=V1_CATALOG[id].parameters[key]
    if not v1_valid_field(rule,value) then return false end
    v1_drafts[id][key]=value;v1_draw_draft(id);v1_save_drafts();return true
end
local function v1_precise_editor(id,key,rule,p,entry)
    v1_edit_target={id=id,key=key,kind=rule.kind}
    v1_edit_buffer=rule.kind=='positive_int_list' and table.concat(p[key],',') or tostring(p[key])
    v1_set('keypad_title',entry.labels[key]..(rule.kind=='positive_int_list' and '' or ' · precise'))
    v1_set('keypad_value',v1_edit_buffer=='' and 'Automatic' or v1_edit_buffer);v1_set('keypad_error','')
    local limits=rule.kind=='positive_int_list' and 'Optional: up to 64 positive whole numbers separated by commas.'
        or (rule.exclusive_min and 'Greater than: ' or 'Minimum: ')..tostring(rule.min)..(rule.max and ('; maximum: '..tostring(rule.max)) or '; no Orca product maximum')
            ..(rule.multiple and '; multiples of '..rule.multiple or '')..'.'
    v1_set('keypad_limits',limits)
    local handle
    handle=helix.ui.overlay('orcacal__v1_keypad',{on_close=function()
        if v1_keypad_handle==handle then v1_keypad_handle=nil;v1_edit_target=nil;v1_edit_buffer='' end
    end})
    v1_keypad_handle=handle
end
helix.ui.on('v1_edit',function(arg)
    if not v1_edit_allowed() or type(arg)~='string' then return end
    local id,key=arg:match('^([a-z_]+):([a-z_]+)$')
    local entry=id and V1_CATALOG[id];local rule=entry and entry.parameters[key]
    if not rule or (rule.kind~='number' and rule.kind~='positive_int_list') then return end
    if v1_keypad_handle or v1_editor_open then return end
    local p=v1_prepare_draft(id)
    local precise=rule.kind=='positive_int_list' or rule.max==nil or id=='pressure_advance_pattern' or (key=='step' and rule.min<0.01)
    if precise then v1_precise_editor(id,key,rule,p,entry);return end
    local decimals=rule.integer and 0 or 2
    local units={temperature='°C',retraction='mm',max_volumetric_speed='mm³/s'}
    v1_editor_open=true
    local ok=pcall(helix.ui.edit_number,{title=entry.labels[key],value=p[key],min=rule.min,max=rule.max,
        decimals=decimals,unit=units[id] or '',
        validate=function(value) return v1_valid_field(rule,value),'Use a value allowed by Orca.' end,
        on_accept=function(value)
            v1_editor_open=false
            if not v1_edit_allowed() or not v1_commit_edit(id,key,value) then
                v1_set('message','The value was not accepted; the previous draft is unchanged.')
            end
        end,
        on_cancel=function() v1_editor_open=false end})
    if not ok then
        v1_editor_open=false
        v1_set('message','The numeric editor is busy. Close the current dialog and try again.')
    end
end)
helix.ui.on('v1_evaluation_edit',function()
    local e=v1_session and v1_session.evaluation
    if not e or v1_session.phase~='complete' or v1_session.result or not e.range
        or v1_keypad_handle or v1_editor_open then return end
    v1_edit_target={id='__evaluation',key='value',kind='number',range=e.range}
    v1_edit_buffer=tostring(e.value or e.range.start)
    v1_set('keypad_title','Choose printed result')
    v1_set('keypad_value',v1_edit_buffer);v1_set('keypad_error','')
    v1_set('keypad_limits','Use an exact printed step from '..tostring(e.range.start)..' to '..tostring(e.range['end'])..' in '..tostring(e.range.step)..' increments.')
    local handle
    handle=helix.ui.overlay('orcacal__v1_keypad',{on_close=function()
        if v1_keypad_handle==handle then v1_keypad_handle=nil;v1_edit_target=nil;v1_edit_buffer='' end
    end})
    v1_keypad_handle=handle
end)
helix.ui.on('v1_key',function(key)
    if not v1_edit_target or not v1_keypad_handle then return end
    v1_set('keypad_error','')
    if key=='clear' then v1_edit_buffer=''
    elseif key=='back' then v1_edit_buffer=v1_edit_buffer:sub(1,-2)
    elseif key==',' and v1_edit_target.kind=='positive_int_list' then
        if #v1_edit_buffer>=512 then v1_set('keypad_error','This list exceeds the bounded editor size.');return end
        if v1_edit_buffer=='' or v1_edit_buffer:sub(-1)==',' then return end
        v1_edit_buffer=v1_edit_buffer..','
    elseif key=='.' and v1_edit_target.kind=='number' then
        if #v1_edit_buffer>=512 then v1_set('keypad_error','This number exceeds the bounded editor size.');return end
        if v1_edit_buffer:find('%.') then return end
        if v1_edit_buffer=='' then v1_edit_buffer='0' end
        v1_edit_buffer=v1_edit_buffer..'.'
    elseif type(key)=='string' and key:match('^%d$') then
        if #v1_edit_buffer>=512 then v1_set('keypad_error','This entry exceeds the bounded editor size.');return end
        if v1_edit_target.kind=='number' and v1_edit_buffer=='0' then v1_edit_buffer=key else v1_edit_buffer=v1_edit_buffer..key end
    else return end
    v1_set('keypad_value',v1_edit_buffer=='' and 'Automatic' or v1_edit_buffer)
end)
helix.ui.on('v1_key_set',function()
    if not v1_edit_target or not v1_keypad_handle then return end
    local id,key=v1_edit_target.id,v1_edit_target.key
    if id~='__evaluation' and not v1_edit_allowed() then return end
    local rule=id=='__evaluation' and {kind='number',min=v1_edit_target.range.start,max=v1_edit_target.range['end']}
        or V1_CATALOG[id].parameters[key]
    if rule.kind=='positive_int_list' then
        local values={}
        if v1_edit_buffer~='' then
            if v1_edit_buffer:sub(-1)==',' or not v1_edit_buffer:match('^[%d,]+$') then
                v1_set('keypad_error','Use positive whole numbers separated by single commas.');return
            end
            for item in v1_edit_buffer:gmatch('[^,]+') do
                local value=tonumber(item)
                if not value or value<=0 or value%1~=0 or value>2147483647 then
                    v1_set('keypad_error','Each value must be a positive Orca integer.');return
                end
                values[#values+1]=value
                if #values>rule.max_items then v1_set('keypad_error','Use at most 64 values.');return end
            end
        end
        if not v1_commit_edit(id,key,values) then return end
        local handle=v1_keypad_handle;v1_keypad_handle=nil;v1_edit_target=nil;v1_edit_buffer='';pcall(handle.close);return
    end
    local number=tonumber(v1_edit_buffer)
    if rule.integer and number then number=math.tointeger(number) end
    if not v1_edit_buffer:match('^%d+%.?%d*$') or not v1_valid_field(rule,number) then
        v1_set('keypad_error','Enter a finite value at or above the displayed minimum'..(rule.multiple and ', in multiples of '..rule.multiple or '')..'.');return
    end
    if id=='__evaluation' then
        if not v1_evaluation_range_value(v1_session.evaluation,number) then
            v1_set('keypad_error','Choose one exact printed increment from the displayed range.');return
        end
        v1_session.evaluation.value=number;v1_set('evaluation_value',tostring(number)..
            (v1_session.evaluation.unit~='' and (' '..v1_session.evaluation.unit) or ''))
        if not v1_persist() then return end
        local handle=v1_keypad_handle;v1_keypad_handle=nil;v1_edit_target=nil;v1_edit_buffer='';pcall(handle.close);return
    end
    if not v1_commit_edit(id,key,number) then return end
    local handle=v1_keypad_handle;v1_keypad_handle=nil;v1_edit_target=nil;v1_edit_buffer='';pcall(handle.close)
end)
helix.ui.on('v1_flow_mode',function(mode)
    if not v1_edit_allowed() or (mode~='1' and mode~='2') then return end
    v1_prepare_draft('flow_ratio_yolo');v1_drafts.flow_ratio_yolo.pass=tonumber(mode)
    v1_draw_draft('flow_ratio_yolo');v1_save_drafts()
end)
helix.ui.on('v1_flow_pattern',function(pattern)
    if not v1_edit_allowed() or (pattern~='archimedean_chords' and pattern~='monotonic') then return end
    local p=v1_prepare_draft('flow_ratio_yolo')
    if p.pattern==nil then v1_set('message','Pattern choice requires the current V2 Orca context.');return end
    p.pattern=pattern;v1_draw_draft('flow_ratio_yolo');v1_save_drafts()
end)
helix.ui.on('v1_scale',function()
    if not v1_edit_allowed() then return end
    local p=v1_prepare_draft('temperature');p.scale=not p.scale;v1_draw_draft('temperature');v1_save_drafts()
end)
helix.ui.on('v1_pa_defaults',function(kind)
    if not v1_edit_allowed() or (kind~='direct_drive' and kind~='bowden') then return end
    v1_prepare_draft('pressure_advance_pattern')
    local current=v1_drafts.pressure_advance_pattern
    v1_drafts.pressure_advance_pattern=v1_copy_parameters(V1_PA_DEFAULTS[kind])
    v1_drafts.pressure_advance_pattern.accelerations=current.accelerations or {}
    v1_drafts.pressure_advance_pattern.speeds=current.speeds or {}
    v1_draw_draft('pressure_advance_pattern');v1_save_drafts()
end)
