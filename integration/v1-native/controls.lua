-- Native, plugin-owned numeric input; beta.9 exposes no built-in keypad API.
local v1_keypad_handle=nil
local v1_edit_target=nil
local v1_edit_buffer=''
local function v1_copy_parameters(p)
    local out={};for key,value in pairs(p) do out[key]=value end;return out
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
        local text=type(value)=='boolean' and (value and 'On' or 'Off') or tostring(value)
        if id=='flow_ratio_yolo' then text=value==1 and 'Recommended' or 'Perfectionist' end
        v1_set(id..'_'..key..'_value',text)
    end
    if id=='flow_ratio_yolo' then
        v1_set('flow_samples',p.pass==1 and '11 samples; fixed additive offsets: -0.05 to +0.05 in 0.01 steps.' or '16 samples; fixed additive offsets: -0.04 to +0.035 in 0.005 steps.')
    end
end
local function v1_prepare_draft(id)
    if not v1_drafts[id] then
        local defaults=v1_offer and v1_offer.defaults[id] or V1_DEFAULTS[id]
        v1_drafts[id]=v1_copy_parameters(defaults)
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
helix.ui.on('v1_edit',function(arg)
    if not v1_edit_allowed() or type(arg)~='string' then return end
    local id,key=arg:match('^([a-z_]+):([a-z_]+)$')
    local entry=id and V1_CATALOG[id];local rule=entry and entry.parameters[key]
    if not rule or rule.kind~='number' then return end
    if v1_keypad_handle then return end
    local p=v1_prepare_draft(id)
    v1_edit_target={id=id,key=key};v1_edit_buffer=tostring(p[key])
    v1_set('keypad_title',entry.labels[key]);v1_set('keypad_value',v1_edit_buffer);v1_set('keypad_error','')
    v1_set('keypad_limits','V1 range: '..tostring(rule.min)..' to '..tostring(rule.max)..(rule.multiple and '; multiples of '..rule.multiple or '')..'.')
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
    elseif key=='.' then
        if #v1_edit_buffer>=12 then v1_set('keypad_error','Use at most 12 characters.');return end
        if v1_edit_buffer:find('%.') then return end
        if v1_edit_buffer=='' then v1_edit_buffer='0' end
        v1_edit_buffer=v1_edit_buffer..'.'
    elseif type(key)=='string' and key:match('^%d$') then
        if #v1_edit_buffer>=12 then v1_set('keypad_error','Use at most 12 characters.');return end
        if v1_edit_buffer=='0' then v1_edit_buffer=key else v1_edit_buffer=v1_edit_buffer..key end
    else return end
    v1_set('keypad_value',v1_edit_buffer)
end)
helix.ui.on('v1_key_set',function()
    if not v1_edit_target or not v1_keypad_handle or not v1_edit_allowed() then return end
    local id,key=v1_edit_target.id,v1_edit_target.key
    local rule=V1_CATALOG[id].parameters[key];local number=tonumber(v1_edit_buffer)
    if rule.integer and number then number=math.tointeger(number) end
    if not v1_edit_buffer:match('^%d+%.?%d*$') or not v1_valid_field(rule,number) then
        v1_set('keypad_error','Enter a valid value within the displayed range'..(rule.multiple and ', in multiples of '..rule.multiple or '')..'.');return
    end
    v1_drafts[id][key]=number;v1_draw_draft(id);v1_save_drafts()
    local handle=v1_keypad_handle;v1_keypad_handle=nil;v1_edit_target=nil;v1_edit_buffer='';pcall(handle.close)
end)
helix.ui.on('v1_flow_mode',function(mode)
    if not v1_edit_allowed() or (mode~='1' and mode~='2') then return end
    v1_prepare_draft('flow_ratio_yolo');v1_drafts.flow_ratio_yolo.pass=tonumber(mode)
    v1_draw_draft('flow_ratio_yolo');v1_save_drafts()
end)
helix.ui.on('v1_scale',function()
    if not v1_edit_allowed() then return end
    local p=v1_prepare_draft('temperature');p.scale=not p.scale;v1_draw_draft('temperature');v1_save_drafts()
end)
helix.ui.on('v1_pa_defaults',function(kind)
    if not v1_edit_allowed() or (kind~='direct_drive' and kind~='bowden') then return end
    v1_prepare_draft('pressure_advance_pattern')
    v1_drafts.pressure_advance_pattern=v1_copy_parameters(V1_PA_DEFAULTS[kind])
    v1_draw_draft('pressure_advance_pattern');v1_save_drafts()
end)
