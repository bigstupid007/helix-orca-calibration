-- SPDX-License-Identifier: GPL-3.0-or-later
-- HelixScreen beta.12 queues plugin dialogs behind every app-owned dialog.
-- Persist the claim before requesting the dialog: recovery may suppress a
-- duplicate, but can never manufacture a second automatic attempt.
local v1_completion_presentation = {}
local v1_presentation_armed = false
local v1_presentation_handle = nil
local v1_presentation_options = nil

function v1_completion_presentation.arm(s)
    if s and s.request and not s.auto_presentation_claim then v1_presentation_armed=true end
end

function v1_completion_presentation.disarm()
    v1_presentation_armed=false
end

function v1_completion_presentation.claim(s)
    local attempt=v1_presentation_armed and not s.auto_presentation_claim
    v1_presentation_armed=false
    if not s.auto_presentation_claim then
        s.auto_presentation_claim={schema='helix-orca-v1-presentation-claim/v2',
            request_id=s.request.request_id,origin_id=s.request.origin_id,
            context_sha256=s.request.context_sha256,prepared_sha256=s.prepared_sha256,
            job_id=s.job_id,completion_sha256=s.completion_sha256,
            calibration=s.request.calibration,
            reason=attempt and 'beta12-queued-automatic-attempt' or 'recovery-suppressed'}
    end
    return attempt
end

function v1_completion_presentation.recover(s)
    -- Host storage writes are deferred. A restored completion without a claim
    -- may already have shown before power loss, so recovery is manual only.
    v1_presentation_armed=false
    if s.phase=='complete' and not s.auto_presentation_claim then
        s.auto_presentation_claim={schema='helix-orca-v1-presentation-claim/v2',
            request_id=s.request.request_id,origin_id=s.request.origin_id,
            calibration=s.request.calibration,reason='recovery-suppressed'}
        return true
    end
    return false
end

function v1_completion_presentation.open(options)
    if v1_presentation_handle then return true end
    local handle
    local ok=pcall(function()
        v1_presentation_options=options
        handle=helix.ui.dialog('orcacal__v1_result_picker',{evaluation_options=options,
            on_open=function()
                -- The durable claim already exists. Showing carries no state
                -- transition and therefore cannot duplicate a result.
            end,
            on_close=function()
                if v1_presentation_handle==handle then
                    v1_presentation_handle=nil;v1_presentation_options=nil
                end
            end})
    end)
    if ok then v1_presentation_handle=handle end
    -- Never automatically retry a refused, failed or dismissed presentation.
    -- The owned job overlay remains the deliberate manual reopen path.
    return ok
end

function v1_completion_presentation.close()
    local handle=v1_presentation_handle
    v1_presentation_handle=nil;v1_presentation_options=nil
    if handle then pcall(handle.close) end
end

helix.ui.on('v1_result_later',function()
    v1_completion_presentation.close()
end)
