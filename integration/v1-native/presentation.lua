-- SPDX-License-Identifier: GPL-3.0-or-later
-- Adapted from the accepted beta.9 Temperature presentation adapter. The
-- approved immediate overlay can overlap native dialogs; no timer/preferences.
-- Replace only open() when a supported queued-overlay API becomes available.
local v1_completion_presentation = {}
local v1_presentation_armed = false
local v1_presentation_handle = nil
function v1_completion_presentation.arm(s)
    if s.request.calibration=='temperature' and not s.auto_presentation_claim then v1_presentation_armed=true end
end
function v1_completion_presentation.disarm()
    v1_presentation_armed=false
end
function v1_completion_presentation.claim(s)
    if s.request.calibration~='temperature' then v1_presentation_armed=false;return false end
    local attempt=v1_presentation_armed and not s.auto_presentation_claim
    v1_presentation_armed=false
    if not s.auto_presentation_claim then
        s.auto_presentation_claim={request_id=s.request.request_id,origin_id=s.request.origin_id,
            context_sha256=s.request.context_sha256,prepared_sha256=s.prepared_sha256,
            job_id=s.job_id,completion_sha256=s.completion_sha256,
            reason=attempt and 'automatic-attempt' or 'recovery-suppressed'}
    end
    return attempt
end
function v1_completion_presentation.recover(s)
    -- Host writes are deferred: a restored completion may already have appeared
    -- even when its claim write was lost. Never reconstruct an automatic attempt.
    v1_presentation_armed=false
    if s.request.calibration=='temperature' and s.phase=='complete' and not s.auto_presentation_claim then
        s.auto_presentation_claim={request_id=s.request.request_id,origin_id=s.request.origin_id,
            reason='recovery-suppressed'}
        return true
    end
    return false
end
function v1_completion_presentation.open(options)
    local handle
    local ok=pcall(function()
        handle=helix.ui.overlay('orcacal__v1_auto_result',{evaluation_options=options,
            on_close=function()
                if v1_presentation_handle==handle then v1_presentation_handle=nil end
            end})
    end)
    if ok then v1_presentation_handle=handle end
    -- Never automatically retry a failed or dismissed attempt. Pending choices
    -- remain manually reachable through the accepted home tile/native wizard.
    return ok
end
