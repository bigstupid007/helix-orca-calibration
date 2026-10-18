-- SPDX-License-Identifier: GPL-3.0-or-later
-- Temporary beta.9 presentation adapter. Founder accepts native-dialog overlap.
-- Replace only open() when the host offers queued overlays. No delay/preferences.
local completion_presentation = {}
local presentation_armed = false
local presentation_handle = nil
function completion_presentation.arm(s)
    if not s.auto_presentation_claim then presentation_armed = true end
end
function completion_presentation.disarm()
    presentation_armed = false
end
function completion_presentation.claim(s)
    local attempt = presentation_armed and not s.auto_presentation_claim
    presentation_armed = false
    if not s.auto_presentation_claim then
        s.auto_presentation_claim = {request_id=s.request.request_id,origin_id=s.request.origin_id,
            job_id=s.proof.job_id,completion_sha256=s.proof.completion_sha256,
            reason=attempt and "automatic-attempt" or "recovery-suppressed"}
    end
    return attempt
end
function completion_presentation.recover(s)
    -- Storage writes are deferred by the host. Never infer a new popup from
    -- a restored completion, even if a crash lost the last claimed write.
    presentation_armed = false
    if s.state == "complete" and not s.auto_presentation_claim then
        s.auto_presentation_claim = {request_id=s.request.request_id,origin_id=s.request.origin_id,
            reason="recovery-suppressed"}
        return true
    end
    return false
end
function completion_presentation.open()
    -- A separate owned identity stays above a buried manual Temperature view.
    -- Its layout, subjects and callbacks are generated from the unchanged detail.
    -- Closing never consumes the pending result or clears its presentation claim.
    local ok, handle = pcall(helix.ui.overlay,"orcacal__auto_temperature",{
        on_close=function() presentation_handle=nil end})
    if ok then presentation_handle=handle end
    -- No automatic retry on failure: manual native reopening remains available.
    return ok
end
