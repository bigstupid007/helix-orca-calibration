# Generated-plugin extension. This file is inserted after the accepted October 15 source.
COMMUNICATION_ACTION_NAME = "Helix Temperature Communication (no printing)"

COMMUNICATION_PAGE = r'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>
*{box-sizing:border-box}body{font:14px system-ui;margin:16px;color:#162b40;background:white}h1{font-size:22px;margin:0 0 4px}h2{font-size:16px;margin:0 0 10px}.card{border:1px solid #dbe3e8;border-radius:8px;padding:14px;margin:14px 0;overflow-wrap:anywhere}.result{border:2px solid #008579}.badge{display:inline-block;background:#fff0cc;color:#644700;font-weight:750;padding:6px 10px;border-radius:5px}.muted,.label{color:#526777;font-size:12px}.grid{display:grid;grid-template-columns:minmax(115px,1fr) 2fr;gap:7px 12px}.value{font-weight:650}.large{font-size:25px;color:#00786e}button{padding:10px;border:0;border-radius:5px;background:#008579;color:white;cursor:pointer;margin-right:6px}button:disabled{opacity:.5}input{max-width:100%;margin:8px 0}#status{border-left:3px solid #008579;padding:8px;white-space:pre-wrap}[hidden]{display:none!important}details{margin:14px 0}summary{cursor:pointer;font-weight:600}pre{white-space:pre-wrap;font:12px system-ui}</style></head><body>
<h1>Temperature communication</h1><p class="muted">Simulated selection only · no printing · no setting is applied.</p>
<section id="result" class="card result" hidden><span class="badge">NOT APPLIED</span><h2>Returned selection</h2><div class="grid"><span class="label">Original profile</span><span id="r-profile" class="value"></span><span class="label">Setting</span><span id="r-setting" class="value"></span><span class="label">Original saved</span><span id="r-saved"></span><span class="label">Original edited</span><span id="r-edited"></span><span class="label">Original effective</span><span id="r-current"></span><span class="label">Simulated selection</span><span id="r-selected" class="large"></span><span class="label">Current Orca profile</span><span id="live-profile">Unavailable</span><span class="label">Current effective value</span><span id="live-current">Unavailable</span></div><p id="selection-notice"></p><h2>Optional manual update</h2><ol><li>Return to the original filament profile: <strong id="manual-profile"></strong>.</li><li>Open <strong>Filament &gt; Print temperature &gt; Nozzle &gt; Other layers</strong>.</li><li>Enter <strong id="manual-value"></strong> and save only if you later decide to keep the simulated selection.</li></ol><p>The selected value is simulated; it is not a measured outcome. The companion has not changed Orca.</p></section>
<section class="card"><h2>Original calibration target</h2><div id="target" class="grid"><span class="muted">No profile retained.</span></div><p><button id="freeze">Keep original profile</button></p><label>Exact normally prepared Temperature file<input type="file" id="file" accept=".gcode"></label><p id="file-summary" class="muted">No file selected</p><button id="send" disabled>Send request</button><button id="retry" disabled>Retry same request</button><p class="muted">Sending creates one immutable durable request. Retry preserves its IDs and expiry.</p></section>
<p id="status" role="status" aria-live="polite"></p><p id="delivery-status" class="muted"></p>
<details><summary>Technical details</summary><pre id="technical"></pre></details>
<script>(function(){'use strict';var send=function(command,extra){window.orca.postMessage(Object.assign({command:command},extra||{}));},had=false;
function text(id,value){document.getElementById(id).textContent=value;}function deg(v){return typeof v==='number'&&Number.isFinite(v)?v+' °C':'Unavailable';}function row(label,value){return '<span class="label">'+label+'</span><span class="value"></span>';}
function render(s){var t=s.target,p=s.payload,i=s.instructions,box=document.getElementById('target');box.textContent='';if(t){[['Printer',t.printer.selected_saved.name],['Process',t.process.selected_saved.name],['Filament',t.filament.selected_saved.name],['Nozzle',t.nozzle_mm+' mm'],['Saved',deg(t.saved_temperature)],['Edited',deg(t.edited_temperature)],['Effective',deg(t.effective_temperature)]].forEach(function(x){var a=document.createElement('span'),b=document.createElement('span');a.className='label';a.textContent=x[0];b.className='value';b.textContent=x[1];box.append(a,b);});}else{var e=document.createElement('span');e.className='muted';e.textContent='No profile retained.';box.append(e);}document.getElementById('result').hidden=!i;if(i){text('r-profile',i.profile);text('r-setting',i.setting_label+' ('+i.setting+')');text('r-saved',deg(i.original_saved_value));text('r-edited',deg(i.original_edited_value));text('r-current',deg(i.original_effective_value));text('r-selected',deg(i.selected_value));text('manual-profile',i.profile);text('manual-value',deg(i.selected_value));text('live-profile',s.current_profile||'Unavailable');text('live-current',deg(s.current_effective));text('selection-notice',s.current_matches_target?'The original profile and settings are still selected. Review the simulated result before changing anything.':'Orca’s current profile or settings differ from the calibration start. Return to the original profile above before any optional manual update.');if(!had)window.scrollTo(0,0);}had=!!i;text('file-summary',s.file?s.file.name+' · '+s.file.size+' bytes · SHA-256 '+s.file.sha256:'No file selected');text('status',s.status||'');text('delivery-status',i?'Selection committed locally; transport status cannot replace these NOT APPLIED instructions.':(s.delivery_status||''));text('technical',(p?'Request '+p.request_id+'\nOrigin '+p.origin_id+'\nContext '+p.context_sha256+'\nExpires '+new Date(p.expires_at*1000).toISOString():'No request')+(s.current_matches_target?'\nCurrent Orca context matches the retained original.':'\nCurrent Orca context differs or is unavailable.'));document.getElementById('send').disabled=!t||!s.file||!!p;document.getElementById('retry').disabled=!p||!!i;document.getElementById('freeze').disabled=!!p&&!i&&p.expires_at>Math.floor(Date.now()/1000);}
window.orca.onMessage(function(s){if(s&&s.command==='communication_state')render(s);});document.getElementById('freeze').onclick=function(){send('freeze');};document.getElementById('send').onclick=function(){send('send');};document.getElementById('retry').onclick=function(){send('send');};
__FILE_HASHING__
document.getElementById('file').onchange=async function(){var f=this.files[0];if(!f){send('file',{file:null});return;}try{if(!/\.gcode$/.test(f.name)||f.size<=0||f.size>20000000)throw Error('Select a nonempty lowercase .gcode file below 20 MB.');var bytes=await f.arrayBuffer(),t=new TextDecoder('utf-8',{fatal:true}).decode(bytes),bands=[],m,pattern=/^M10[49]\s+S(\d+)(?:\s|$)/gm;while((m=pattern.exec(t))!==null){var n=Number(m[1]);if(n>0&&bands.indexOf(n)<0)bands.push(n);}if(JSON.stringify(bands)!==JSON.stringify([230,225,220,215,210,205,200,195,190]))throw Error('Temperature choices do not match the qualified file.');var sha=sha256(bytes);send('file',{file:{name:f.name,size:f.size,sha256:sha,bands:bands}});}catch(e){text('status','Rejected: '+e.message);send('file',{file:null});}};
send('ready');setInterval(function(){send('poll');},2000);})();</script></body></html>'''.replace('__FILE_HASHING__', FILE_SHA256_JAVASCRIPT)


class TemperatureCommunicationPanel(orca.script.ScriptPluginCapabilityBase):
    def __init__(self):
        super().__init__()
        self.panel = None
        self.storage_root = None
        self.state = None
        self.status = "Keep the original profile to begin a new calibration."
        self.delivery_status = ""

    def get_name(self):
        return COMMUNICATION_ACTION_NAME

    def execute(self):
        if self.panel is not None and self.panel.is_open():
            self.panel.show()
            return orca.ExecutionResult.success("Temperature communication is already open.")
        self.storage_root = orca.host.plugin.storage()
        kwargs = dict(html=COMMUNICATION_PAGE, title="Temperature communication (no printing)", width=440,
                      height=720, on_message=self.on_message, on_close=self.on_close)
        try:
            self.panel = orca.host.ui.create_dock_panel(**kwargs, dock="right")
        except Exception:
            self.panel = orca.host.ui.create_window(**kwargs)
        return orca.ExecutionResult.success("Temperature communication opened; no printing or profile write is available.")

    def on_close(self):
        self.panel = None
        self.state = None

    def on_message(self, message):
        if not isinstance(message, dict):
            return
        command = message.get("command")
        try:
            if command == "ready":
                self.state = TemperatureCommunicationState(self.storage_root)
                if self.state.recovery_error:
                    self.status = "Recovery unavailable: " + self.state.recovery_error
                elif self.state.payload:
                    self.status = "Pending request restored unchanged."
            elif self.state is None:
                raise CommunicationProtocolError("Panel state is not ready.")
            elif command == "freeze":
                self.state.start_new(capture_temperature_target(orca.host))
                self.delivery_status = ""
                self.status = "Original profile retained. Select its exact normally prepared Temperature file."
            elif command == "file":
                self.state.select_file(message.get("file"), validate_temperature_file)
                self.status = "Exact file identity retained; ready to send."
            elif command == "send":
                self.status = self.state.send()
                self.delivery_status = "Waiting for the relay to report delivery."
            elif command == "poll":
                outcome = self.state.poll_inbox()
                if outcome:
                    self.status = outcome
                if self.state.instructions is None:
                    if self.state.is_expired():
                        self.status = "Request expired. Returned selections are refused; keep the original profile to start a new calibration."
                    try:
                        delivery_status = self.state.poll_delivery()
                        if delivery_status:
                            self.delivery_status = delivery_status
                    except CommunicationProtocolError:
                        # A stale or malformed relay status is untrusted and
                        # cannot replace the last validated status or target.
                        pass
            else:
                return
        except Exception as exc:
            self.status = "Rejected: " + _error_reason(exc)
        self._post_state()

    def _post_state(self):
        if self.panel is None or not self.panel.is_open() or self.state is None:
            return
        same = False
        current_profile = None
        current_effective = None
        try:
            current = capture_temperature_target(orca.host)
            same = self.state.target is not None and json_digest(current) == json_digest(self.state.target)
            current_profile = current["filament"]["selected_saved"]["name"]
            current_effective = current["effective_temperature"]
        except Exception:
            pass
        self.panel.post({"command": "communication_state", "target": self.state.target, "file": self.state.file,
                         "payload": self.state.payload, "instructions": self.state.instructions,
                         "status": self.status, "current_matches_target": same,
                         "current_profile": current_profile, "current_effective": current_effective,
                         "delivery_status": self.delivery_status})

