"""Embedded after the qualified October 15 plugin. UI callbacks/local I/O only."""
import os
import queue
import secrets
import time
from decimal import Decimal
V1_PAGE = r'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>
*{box-sizing:border-box}body{font:14px system-ui;margin:0;background:#f5f7f8;color:#203440}main{max-width:720px;margin:auto;padding:20px}h1{font-size:24px;line-height:1.2;margin:4px 0 8px}h2{font-size:16px;margin:0 0 12px}p{line-height:1.5}.eyebrow{color:#087e76;font-size:11px;font-weight:750;letter-spacing:.1em;text-transform:uppercase}.muted{color:#59707c;font-size:13px}.card{background:white;border:1px solid #dce4e8;border-radius:12px;padding:18px;margin:16px 0;overflow-wrap:anywhere}.row{display:grid;grid-template-columns:90px 1fr;gap:8px 14px}.label{color:#59707c}.value{font-weight:600}.badge{display:inline-block;padding:5px 9px;background:#e4f3ef;color:#086c5b;border-radius:6px;font-size:12px;font-weight:700}.pending{background:#fff0d9;color:#785510}.result{border-color:#008579;border-width:2px}.big{font-size:30px;color:#007a70;font-weight:700}button{font:inherit;background:white;color:#006c65;border:1px solid #a1c5bf;border-radius:6px;padding:9px 12px;cursor:pointer}button:focus-visible,summary:focus-visible{outline:3px solid #008579;outline-offset:3px}details{margin:18px 0}summary{cursor:pointer;color:#59707c;font-size:12px}pre{white-space:pre-wrap;font:12px system-ui}#status{white-space:pre-wrap} [hidden]{display:none!important}@media(max-width:360px){main{padding:12px}.card{padding:14px}.row{grid-template-columns:70px 1fr;gap:7px}}
</style></head><body><main><span class="eyebrow">Helix Calibration · V1 candidate</span><h1 id="headline">Waiting for Helix</h1><p class="muted">Choose and configure your calibration on Helix. Orca keeps the profiles, preparation and returned result together here.</p>
<section id="result" class="card result" hidden><span class="badge pending">NOT APPLIED</span><h2 style="margin-top:12px">Your calibration result</h2><div id="result-value" class="big"></div><p id="result-setting"></p><p class="muted">Returned to the original context. No profile has been changed.</p></section>
<section class="card"><h2>Current Orca selection</h2><div id="profiles" class="row"></div><p id="profile-note" class="muted"></p><button id="refresh">Refresh selection</button></section>
<section class="card"><span id="phase" class="badge pending">Waiting for Helix</span><h2 style="margin-top:14px">Preparation</h2><p id="status" role="status" aria-live="polite">Open this panel to share the selected profiles with the local coordinator.</p><section id="calibration-context" hidden><h2>Original calibration context</h2><div id="original-profiles" class="row"></div><p class="muted">This job keeps these profiles when the current Orca selection changes.</p></section><div id="job" class="row"></div><p class="muted">Generation does not start a print. Confirm and Start are separate actions on Helix. Physical execution is disabled in this review candidate.</p></section>
<details><summary>Connection and provenance</summary><pre id="technical"></pre></details></main><script>(function(){'use strict';function send(command){window.orca.postMessage({command:command});}function text(id,value){document.getElementById(id).textContent=value;}var names={temperature:'Temperature',flow_ratio_yolo:'Flow Ratio YOLO',pressure_advance_pattern:'Pressure Advance',retraction:'Retraction',max_volumetric_speed:'Max Volumetric Speed'},phases={requested:'Preparation requested',preparing:'Preparing print',blocked:'Preparation unavailable',review:'Ready to review on Helix',confirmed:'Ready to start on Helix',starting:'Starting print',printing:'Printing',verifying:'Checking completion',complete:'Ready to evaluate',cancelled:'Print cancelled',failed:'Print did not complete',uncertain:'Check connection',returning:'Returning result',delivered:'Result returned'};function parameters(p){if(p.calibration==='flow_ratio_yolo')return (p.parameters.pass===2?'YOLO Perfectionist · 16 samples':'YOLO Recommended · 11 samples')+' · Archimedean surface';var v=p.parameters,u=p.calibration==='temperature'?'°C':p.calibration==='retraction'?'mm':p.calibration==='max_volumetric_speed'?'mm³/s':'s';return v.start+' → '+v.end+' '+u+' · '+v.step+' '+u+' increments';}function preset(c,role){var a=c[role].saved,b=c[role].edited,keys=Object.keys(a.config),edited=a.name!==b.name||keys.length!==Object.keys(b.config).length||keys.some(function(k){return a.config[k]!==b.config[k];});return a.name+(edited?' · edited':'');}function rows(id,values){var root=document.getElementById(id);root.textContent='';values.forEach(function(pair){var a=document.createElement('span'),b=document.createElement('span');a.className='label';b.className='value';a.textContent=pair[0];b.textContent=pair[1];root.append(a,b);});}window.orca.onMessage(function(s){if(!s||s.command!=='v1_state')return;var c=s.context,v=s.view||{},st=v.status||{},original=v.original,resultOriginal=v.result_original;rows('profiles',c?[['Printer',preset(c,'printer')],['Process',preset(c,'process')],['Filament',preset(c,'filament')],['Nozzle',c.nozzle_mm+' mm']]:[['Profiles','Unavailable']]);text('profile-note','Saved preset identity, edited copy and effective values are retained separately.');document.getElementById('calibration-context').hidden=!(st.request_id&&original);rows('original-profiles',st.request_id&&original?[['Printer',original.printer+(original.edited_roles&&original.edited_roles.includes('printer')?' · edited':'')],['Process',original.process+(original.edited_roles&&original.edited_roles.includes('process')?' · edited':'')],['Filament',original.filament+(original.edited_roles&&original.edited_roles.includes('filament')?' · edited':'')],['Nozzle',original.nozzle_mm===undefined?'Unavailable':original.nozzle_mm+' mm']]:[]);var phaseLabel=phases[st.phase]||'Waiting for Helix';text('headline',phaseLabel);text('phase',phaseLabel);document.getElementById('phase').className='badge'+(['review','confirmed','complete','delivered'].includes(st.phase)?'':' pending');text('status',s.error||st.message||'Choose a calibration on Helix. The local coordinator must be running.');var p=st.prepared;rows('job',p?[['Calibration',names[p.calibration]||'Calibration'],['Parameters',parameters(p)],['Artifact',p.artifact?p.artifact.name:'Unavailable'],['Orca comparison',p.parity.qualified?'Verified':p.parity.reason]]:[]);var r=v.result;document.getElementById('result').hidden=!r;if(r){text('result-value',String(r.value));text('result-setting',({nozzle_temperature:'Nozzle temperature',filament_flow_ratio:'Filament flow ratio',pressure_advance:'Pressure advance',filament_retraction_length:'Retraction length',filament_max_volumetric_speed:'Maximum volumetric speed'}[r.setting]||'Selected value')+' · original '+(resultOriginal?resultOriginal.filament:'profile'));}text('technical','Runtime: '+(c?c.runtime.version+' / '+c.runtime.build:'Unavailable')+'\nCurrent selection context: '+(s.context_sha256||'Unavailable')+'\nCalibration context: '+(st.request_id&&original?original.context_sha256||'Unavailable':'No active request')+'\n'+(p?'Generator: '+p.generator.route+' / '+p.generator.build:'No generated job')+'\n'+(s.health||'Coordinator status unavailable')+'\nResult changes are never applied automatically.');});document.getElementById('refresh').onclick=function(){send('refresh');};send('ready');setInterval(function(){send('poll');},2000);})();</script></body></html>'''


def v1_storage(root):
    directory = pathlib.Path(str(root)) / "v1"
    if directory.is_symlink():
        raise ContractError("V1 storage must not be a link")
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def v1_write(path, value):
    if path.is_symlink() or path.parent.is_symlink():
        raise ContractError("Linked V1 artifact refused")
    import tempfile
    fd, name = tempfile.mkstemp(prefix=".v1-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(canonical(value))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def v1_read(path):
    if not path.exists():
        return None
    if path.is_symlink() or path.parent.is_symlink() or not path.is_file() or path.stat().st_size > MAX_MESSAGE:
        raise ContractError("Invalid V1 artifact")
    with path.open("rb") as stream:
        raw = stream.read(MAX_MESSAGE + 1)
    if len(raw) > MAX_MESSAGE:
        raise ContractError("Oversized V1 artifact")
    value = json.loads(raw)
    canonical(value)
    return value


def v1_capture(host, origin_id):
    # Keep the qualified October 15 runtime/one-filament/edited/effective checks.
    target = capture_temperature_target(host)
    if target["runtime"] != {"version": "2.5.0-dev", "build": "6a7763f0"}:
        raise ContractError("V1 preparation requires the October 15 baseline")
    bundle = host.preset_bundle()
    value = dict(schema="helix-orca-v1-context/v1", origin_id=origin_id,
                 runtime=target["runtime"], nozzle_mm=target["nozzle_mm"])
    def config(obj, keys="config_keys", read="config_value"):
        result = {}
        for key in getattr(obj, keys)():
            sensitive, _ = _is_sensitive_key(key)
            # The private V1 preparer must distinguish empty hooks from executable
            # post-processing. It rejects nonempty scripts rather than executing
            # them. Public diagnostics retain their existing path redaction.
            if sensitive and key != "post_process":
                continue
            raw = getattr(obj, read)(key)
            if not isinstance(raw, str):
                raise ContractError("Serialized configuration unavailable: " + key)
            result[key] = raw
        return result
    for role, collection in (("printer", bundle.printers), ("process", bundle.prints), ("filament", bundle.filaments)):
        value[role] = {}
        for name, method in (("saved", "selected_preset"), ("edited", "edited_preset")):
            preset = _call(collection, method)
            value[role][name] = dict(name=_preset_view(preset)["name"], config=config(preset))
    value["effective"] = config(bundle, "full_config_keys", "full_config_value")
    return validate_context(value)


def v1_commit_inbox(directory):
    inbox = v1_read(directory / "inbox.json")
    if not inbox:
        return v1_read(directory / "committed.json")
    exact(inbox, "result request prepared completion", "inbox")
    result, request, prepared, proof = (inbox[k] for k in ("result", "request", "prepared", "completion"))
    request = validate_request(request, now=request["created_at"])
    original = v1_read(directory / "origins" / (request["origin_id"] + ".json"))
    if original is None or digest(validate_context(original)) != request["context_sha256"]:
        raise ContractError("Returned result has no retained original Orca context")
    validate_prepared(prepared, request)
    exact(result, "schema request_id origin_id context_sha256 prepared_sha256 job_id completion_sha256 setting value not_applied", "returned result")
    exact(proof, "job_id file_sha256 print_state history_state history_job_id history_file_sha256", "completion proof")
    if (result["schema"] != "helix-orca-v1-result/v1" or result["not_applied"] is not True
            or any(result[k] != request[k] for k in ("request_id", "origin_id", "context_sha256"))
            or result["prepared_sha256"] != digest(prepared) or result["completion_sha256"] != digest(proof)
            or not prepared["parity"]["qualified"] or not prepared["artifact"]
            or proof["print_state"] != "complete" or proof["history_state"] != "completed"
            or proof["job_id"] != proof["history_job_id"] or proof["job_id"] != result["job_id"]
            or proof["file_sha256"] != proof["history_file_sha256"] or proof["file_sha256"] != prepared["artifact"]["sha256"]):
        raise ContractError("Returned result lacks exact independent same-job proof")
    kind, parameters = request["calibration"], request["parameters"]
    if kind == "temperature":
        choices = list(range(parameters["start"], parameters["end"] - 1, -5))
    elif kind == "flow_ratio_yolo":
        choices = flow_ratio_choices(original["effective"]["filament_flow_ratio"], parameters["pass"])
    else:
        start, end, step = (Decimal(str(parameters[k])) for k in ("start", "end", "step"))
        choices = [float(start + step * i) for i in range(int((end - start) // step) + 1)]
    if result["setting"] != SETTINGS[kind] or type(result["value"]) not in (int, float) or result["value"] not in choices:
        raise ContractError("Returned result is outside original calibration choices")
    results = directory / "results"
    results.mkdir(exist_ok=True)
    path = results / (request["request_id"] + ".json")
    previous = v1_read(path)
    committed = dict(result=result, original=original, request=request)
    if previous is not None and canonical(previous) != canonical(committed):
        raise ContractError("A different result was already committed for this request")
    v1_write(path, committed)
    v1_write(directory / "committed.json", committed)
    receipt = dict(schema="helix-orca-v1-ack/v1", request_id=result["request_id"], origin_id=result["origin_id"],
                   result_sha256=digest(result), result=result, not_applied=True)
    # Acknowledgement follows durable original-context commitment, never receipt alone.
    v1_write(directory / "receipt.json", receipt)
    return committed


class V1CalibrationPanel(orca.script.ScriptPluginCapabilityBase):
    def __init__(self):
        super().__init__()
        self.panel = None
        self.directory = None
        self.context = None
        self.error = None
        self.refresh_pending = True

    def get_name(self):
        return "Helix V1 Calibration"

    def execute(self):
        if self.panel is not None and self.panel.is_open():
            self.panel.show()
            return orca.ExecutionResult.success("V1 companion already open.")
        self.directory = v1_storage(orca.host.plugin.storage())
        kwargs = dict(html=V1_PAGE, title="Helix V1 Calibration", width=460, height=740,
                      on_message=self.on_message, on_close=self.on_close)
        try:
            self.panel = orca.host.ui.create_dock_panel(**kwargs, dock="right")
        except Exception:
            self.panel = orca.host.ui.create_window(**kwargs)
        return orca.ExecutionResult.success("V1 companion opened; no profile changes or print actions.")

    def on_close(self):
        self.panel = None

    def on_lifecycle_event(self, event, context):
        if _enum_name(event) in {"PresetSelected", "ProjectDirtyChanged"}:
            # Event callbacks may run outside the supported UI callback phase.
            # Only flag a subsequent UI poll; never capture/write on that thread.
            self.refresh_pending = True

    def retained_result_view(self, view):
        committed = v1_read(self.directory / "committed.json")
        if view:
            view["result"] = None
        if committed:
            view = view or {}
            view["result"] = committed["result"]
            original = committed["original"]
            view["result_original"] = dict({role: original[role]["saved"]["name"] for role in ("printer", "process", "filament")},
                nozzle_mm=original["nozzle_mm"], context_sha256=digest(original),
                edited_roles=[role for role in ("printer", "process", "filament") if original[role]["saved"] != original[role]["edited"]])
        return view

    def on_message(self, message):
        if not isinstance(message, dict) or message.get("command") not in ("ready", "refresh", "poll"):
            return
        self.error = None
        refreshing = message["command"] in ("ready", "refresh") or self.refresh_pending
        try:
            if refreshing:
                self.refresh_pending = False
                retained = v1_read(self.directory / "context.json")
                origin = retained["origin_id"] if retained else secrets.token_hex(16)
                current = v1_capture(orca.host, origin)
                if retained and current != retained:
                    current["origin_id"] = secrets.token_hex(16)
                self.context = validate_context(current)
                v1_write(self.directory / "context.json", self.context)
                origins = self.directory / "origins"
                origins.mkdir(exist_ok=True)
                origin_path = origins / (self.context["origin_id"] + ".json")
                retained_origin = v1_read(origin_path)
                if retained_origin is not None and canonical(retained_origin) != canonical(self.context):
                    raise ContractError("Original profile snapshot is immutable")
                v1_write(origin_path, self.context)
                v1_write(self.directory / "context-status.json", dict(available=True))
            view = v1_read(self.directory / "view.json")
            health = v1_read(self.directory / "runtime" / "health.json")
            v1_commit_inbox(self.directory)
            view = self.retained_result_view(view)
        except Exception as exc:
            self.error = "Unavailable: " + str(exc)[:500]
            if refreshing:
                self.context = None
                v1_write(self.directory / "context-status.json", dict(available=False, reason="Selected Orca context is unavailable. Refresh after restoring a valid profile selection."))
            health = None
            # A later malformed inbox or unavailable selection must not hide a
            # previously committed NOT APPLIED result from the original context.
            try:
                view = self.retained_result_view(None)
            except Exception:
                view = None
        if self.panel and self.panel.is_open():
            self.panel.post(dict(command="v1_state", context=self.context, context_sha256=digest(self.context) if self.context else None,
                                 view=view, error=self.error,
                                 health=("Coordinator stopped" if health and health.get("stopped") else "Coordinator last reported running" if health and health.get("ok") else "Coordinator unavailable or blocked")))


# Current-nightly V2. These helpers are deliberately separate from the
# historical V1 UI/receipt path above. A generated plugin may call capture from
# a UI callback, but v2_apply_inbox must run from Script.execute's worker.
V2_APPLICATION_KEYS = {
    "temperature": ("nozzle_temperature",),
    "flow_ratio_yolo": ("filament_flow_ratio",),
    "pressure_advance_pattern": ("enable_pressure_advance", "pressure_advance"),
    "retraction": ("filament_retraction_length",),
    "max_volumetric_speed": ("filament_max_volumetric_speed",),
}
V2_PAGE = r'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>
*{box-sizing:border-box}body{font:14px system-ui;margin:0;background:#f5f7f8;color:#203440}main{max-width:680px;margin:auto;padding:18px}.card{background:#fff;border:1px solid #dce4e8;border-radius:12px;padding:16px;margin:14px 0}h1{font-size:22px}label{display:block;font-weight:650;margin:10px 0 5px}select,button{font:inherit;padding:9px;border:1px solid #94aaa9;border-radius:6px;background:white}button{color:#006c65;font-weight:650;margin:8px 8px 0 0}.badge{display:inline-block;padding:5px 8px;border-radius:6px;background:#e4f3ef;color:#086c5b;font-weight:700}.warn{background:#fff0d9;color:#785510}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:12px system-ui}</style></head><body><main>
<span class="badge">Pinned beta.12 companion</span><h1>Helix Calibration</h1><p>Choose the filament slot that originated this exact job. Shared slots remain visible; Orca applies a result only to the official edited preset transaction and never saves it.</p>
<section class="card"><label for="slot">Originating filament slot</label><select id="slot"></select><div><button id="capture">Use this slot</button><button id="refresh">Refresh slots</button></div><pre id="context">Loading Orca selection…</pre></section>
<section class="card"><span class="badge warn">Originating preset transaction</span><p id="status">Waiting for the owner-local coordinator.</p><pre id="application"></pre></section>
<script>(function(){'use strict';var slot=document.getElementById('slot'),status=document.getElementById('status');function send(command,extra){window.orca.postMessage(Object.assign({command:command},extra||{}));}window.orca.onMessage(function(m){if(!m)return;if(m.command==='v2_slots'){slot.textContent='';(m.slots||[]).forEach(function(s){var o=document.createElement('option');o.value=s.slot_number;o.textContent='Slot '+s.slot_number+' · '+s.preset_name;slot.appendChild(o);});status.textContent=m.error||'Choose the originating slot.';}if(m.command==='v2_context'){document.getElementById('context').textContent=m.error||('Origin: slot '+m.context.origin_filament.slot_number+' · '+m.context.origin_filament.preset_name+'\nShared slots: '+m.context.origin_filament.shared_slots.join(', ')+'\nContext: '+m.context_sha256);status.textContent=m.error||'Exact context available. A returned result is applied automatically through Orca’s official transaction.';}if(m.command==='v2_application'){status.textContent=m.error||(m.state?m.state.message:'No returned result is waiting.');document.getElementById('application').textContent=m.state?JSON.stringify(m.state,null,2):'';}});document.getElementById('capture').onclick=function(){send('capture',{origin_slot:Number(slot.value)});};document.getElementById('refresh').onclick=function(){send('slots');};send('slots');})();</script></main></body></html>'''


def _v2_config(obj, keys="config_keys", read="config_value"):
    result = {}
    for key in getattr(obj, keys)():
        sensitive, _ = _is_sensitive_key(key)
        if sensitive and key != "post_process":
            continue
        raw = getattr(obj, read)(key)
        if not isinstance(raw, str):
            raise ContractError("Serialized configuration unavailable: " + key)
        result[key] = raw
    return result


def v2_capture(host, origin_id, origin_slot):
    """Capture an explicitly chosen 1-based originating filament slot."""
    info = dict(host.app_info())
    if ({key: info.get(key) for key in ("version", "build")} != ORCA_RUNTIME_V2):
        raise ContractError("V2 requires the pinned b5e9cb3c Orca nightly")
    if type(origin_slot) is not int or origin_slot < 1:
        raise ContractError("Choose an explicit 1-based originating filament slot")
    bundle = host.preset_bundle()
    names = list(bundle.current_filament_preset_names())
    if origin_slot > len(names) or not names[origin_slot - 1]:
        raise ContractError("The chosen originating filament slot is unavailable")
    slots = [dict(slot_number=index, preset_name=str(name))
             for index, name in enumerate(names, 1) if name]
    if len(slots) != len(names):
        raise ContractError("Every active filament slot needs an exact preset identity")
    origin_name = str(names[origin_slot - 1])
    value = dict(schema="helix-orca-v1-context/v2", origin_id=origin_id,
                 runtime=dict(version=info["version"], build=info["build"],
                              source_commit=ORCA_SOURCE_V2,
                              executable_sha256=ORCA_EXECUTABLE_SHA256_V2),
                 filament_slots=slots,
                 origin_filament=dict(slot_number=origin_slot, preset_name=origin_name,
                                      shared_slots=[slot["slot_number"] for slot in slots
                                                    if slot["preset_name"] == origin_name]))
    for role, collection in (("printer", bundle.printers), ("process", bundle.prints)):
        value[role] = {}
        for name, method in (("saved", "selected_preset"), ("edited", "edited_preset")):
            preset = _call(collection, method)
            value[role][name] = dict(name=_preset_view(preset)["name"], config=_v2_config(preset))
    assigned = list(bundle.current_filament_presets())
    if len(assigned) != len(names) or assigned[origin_slot - 1] is None:
        raise ContractError("The originating filament preset cannot be resolved")
    saved_filament = assigned[origin_slot - 1]
    edited_filament = _call(bundle.filaments, "edited_preset", "get_edited_preset")
    if _preset_view(edited_filament)["name"] != origin_name:
        raise ContractError("Select the originating filament preset in Orca before opening calibration")
    value["filament"] = {
        "saved": dict(name=origin_name, config=_v2_config(saved_filament)),
        "edited": dict(name=origin_name, config=_v2_config(edited_filament)),
    }
    value["effective"] = _v2_config(bundle, "full_config_keys", "full_config_value")
    nozzles, nozzle_error = _parse_number_vector(value["effective"].get("nozzle_diameter"), "nozzle_diameter")
    if nozzle_error:
        raise ContractError(nozzle_error)
    if not nozzles or any(not number > 0 for number in nozzles) or any(number != nozzles[0] for number in nozzles):
        raise ContractError("V2 requires one unambiguous effective nozzle diameter")
    value["nozzle_mm"] = nozzles[0]
    return validate_context_v2(value)


def _v2_decimal(value):
    number_value = Decimal(str(value))
    if not number_value.is_finite():
        raise ContractError("A finite preset value is required")
    result = format(number_value, "f")
    if "." in result:
        result = result.rstrip("0").rstrip(".")
    return result or "0"


def v2_application_updates(request, result, original):
    setting = SETTINGS[request["calibration"]]
    if result.get("setting") != setting:
        raise ContractError("Returned setting does not match the calibration")
    value = result.get("value")
    if type(value) not in (int, float):
        raise ContractError("Returned result value must be numeric")
    parameters = request["parameters"]
    if request["calibration"] == "temperature":
        choices = list(range(parameters["start"], parameters["end"] - 1, -5))
    elif request["calibration"] == "flow_ratio_yolo":
        ratios, ratio_error = _parse_number_vector(
            original["effective"].get("filament_flow_ratio"), "filament_flow_ratio")
        slot_index = original["origin_filament"]["slot_number"] - 1
        if ratio_error or slot_index < 0 or slot_index >= len(ratios):
            raise ContractError("Effective flow ratio is unavailable for the originating filament slot")
        choices = flow_ratio_choices(str(ratios[slot_index]), parameters["pass"])
    else:
        start, end, step = (Decimal(str(parameters[key])) for key in ("start", "end", "step"))
        choices = [float(start + step * index) for index in range(int((end - start) // step) + 1)]
    if value not in choices:
        raise ContractError("Returned result is outside the completed calibration choices")
    if request["calibration"] == "pressure_advance_pattern":
        return [("enable_pressure_advance", "1"), ("pressure_advance", _v2_decimal(value))]
    return [(setting, _v2_decimal(value))]


def _v2_update_result(result):
    value = dict(category=result.category, target_name=result.target_name,
                 selection_changed=result.selection_changed, slot_number=result.slot_number,
                 slot_assignment_changed=result.slot_assignment_changed,
                 shared_slots=list(result.shared_slots), keys=list(result.keys), dirty=result.dirty)
    exact(value, "category target_name selection_changed slot_number slot_assignment_changed shared_slots keys dirty", "preset update result")
    if value["category"] != "filament" or any(type(value[key]) is not bool for key in ("selection_changed", "slot_assignment_changed", "dirty")):
        raise ContractError("Orca returned an invalid filament update result")
    return value


def v2_apply_inbox(directory, preset_editor, now=None):
    """Apply one result through Orca's atomic filament transaction.

    This function must be invoked on the persistent Script worker, never from
    a WebView/UI callback. It writes intent before begin_update(), records the
    commit boundary, and never retries a pending/uncertain transaction.
    """
    directory = pathlib.Path(directory)
    application_path = directory / "application.json"
    prior = v1_read(application_path)
    attempt = 1
    if prior is not None:
        if prior.get("status") == "pending":
            crossed_commit = prior.get("phase") == "commit_started"
            prior.update(status="uncertain" if crossed_commit else "failed",
                         phase="recovered_commit_started" if crossed_commit else "recovered_before_commit",
                         message=("A prior commit crossed an unobserved boundary; no retry is permitted."
                                  if crossed_commit else
                                  "A prior attempt ended before commit; an explicit result-bound retry is required."))
            v1_write(application_path, prior)
        if prior.get("status") == "applied":
            return prior
        if prior.get("status") == "uncertain":
            raise ContractError("Preset application is uncertain; no retry is permitted")
        if prior.get("status") != "failed":
            raise ContractError("Malformed retained preset application state")
        retry = v1_read(directory / "application-retry.json")
        if retry is None:
            raise ContractError("Failed application requires an exact explicit result-bound retry")
        exact(retry, "schema request_id origin_id result_sha256 failed_application_sha256 attempt token authorized_at", "V2 application retry")
        if (retry["schema"] != "helix-orca-v1-application-retry/v2"
                or retry["request_id"] != prior["request_id"] or retry["origin_id"] != prior["origin_id"]
                or retry["result_sha256"] != prior["result_sha256"]
                or retry["failed_application_sha256"] != digest(prior)
                or type(retry["attempt"]) is not int or retry["attempt"] != prior.get("attempt", 1) + 1
                or type(retry["authorized_at"]) is not int):
            raise ContractError("Failed application requires an exact explicit result-bound retry")
        hex_value(retry["token"], 32)
        consumed = v1_read(directory / "application-retry-consumed.json")
        if isinstance(consumed, dict) and consumed.get("retry_sha256") == digest(retry):
            raise ContractError("This explicit retry was already consumed; inspect the failed attempt before authorizing another")
        attempts = directory / "application-attempts"
        attempts.mkdir(exist_ok=True)
        v1_write(attempts / (str(prior.get("attempt", 1)) + "-" + digest(prior) + ".json"), prior)
        v1_write(directory / "application-retry-consumed.json",
                 dict(schema="helix-orca-v1-application-retry-consumed/v2",
                      retry_sha256=digest(retry), token=retry["token"], consumed_at=int(time.time() if now is None else now)))
        attempt = retry["attempt"]
    inbox = v1_read(directory / "inbox.json")
    if inbox is None:
        return None
    exact(inbox, "result request prepared completion warning_ack qualification", "V2 inbox")
    request = validate_request_v2(inbox["request"], now=inbox["request"]["created_at"])
    prepared = validate_prepared_v2(inbox["prepared"], request)
    qualification = validate_build_qualification_v2(inbox["qualification"])
    if digest(qualification) != prepared["generator"]["qualification_sha256"]:
        raise ContractError("Prepared job is unrelated to build-level qualification")
    if prepared["processing"]["status"] != "ready":
        raise ContractError("Unknown warning or processor error blocks application")
    acknowledgement = inbox["warning_ack"]
    required = any(warning["requires_ack"] for warning in prepared["processing"]["warnings"])
    if required:
        validate_warning_acknowledgement_v2(acknowledgement, prepared)
    elif acknowledgement is not None:
        validate_warning_acknowledgement_v2(acknowledgement, prepared)
    original = v1_read(directory / "origins" / (request["origin_id"] + ".json"))
    if original is None or digest(validate_context_v2(original)) != request["context_sha256"]:
        raise ContractError("Returned result has no retained originating filament context")
    if prepared["generator"]["machine_sha256"] != machine_sha256_v2(original):
        raise ContractError("Returned result differs from its immutable machine context")
    result = validate_result_v2(inbox["result"], request, prepared)
    proof = inbox["completion"]
    exact(proof, "job_id file_sha256 print_state history_state history_job_id history_file_sha256", "completion proof")
    if (proof["print_state"] != "complete" or proof["history_state"] != "completed"
            or proof["job_id"] != proof["history_job_id"] or proof["job_id"] != result["job_id"]
            or proof["file_sha256"] != proof["history_file_sha256"]
            or proof["file_sha256"] != prepared["artifact"]["sha256"]
            or result["completion_sha256"] != digest(proof)):
        raise ContractError("Returned result lacks exact independent same-job proof")
    updates = v2_application_updates(request, result, original)
    origin = original["origin_filament"]
    stamp = int(time.time() if now is None else now)
    state = dict(schema="helix-orca-v1-application/v2", status="pending", phase="binding",
                 request_id=request["request_id"], origin_id=request["origin_id"],
                 result_sha256=digest(result), attempt=attempt, target_name=origin["preset_name"],
                 slot_number=origin["slot_number"], shared_slots=origin["shared_slots"],
                 updates=[dict(key=key, value=value) for key, value in updates],
                 created_at=stamp, updated_at=stamp,
                 message="Binding the official originating-filament-preset transaction.", outcome=None)
    v1_write(application_path, state)
    try:
        transaction = preset_editor.begin_update(slot_number=origin["slot_number"],
                                                 preset_name=origin["preset_name"])
        for key, value in updates:
            transaction.set(key, value)
    except Exception as exc:
        state.update(status="failed", phase="before_commit", updated_at=int(time.time() if now is None else now),
                     message=("Preset transaction did not reach commit: " + str(exc))[:768])
        v1_write(application_path, state)
        raise
    state.update(phase="commit_started", updated_at=int(time.time() if now is None else now),
                 message="Atomic preset commit started; an interrupted outcome must be treated as uncertain.")
    v1_write(application_path, state)
    try:
        outcome = _v2_update_result(transaction.commit())
    except Exception as exc:
        state.update(status="failed", phase="commit_rolled_back", updated_at=int(time.time() if now is None else now),
                     message=("Orca rejected the atomic commit and rolled back every staged setting; an explicit result-bound retry is required: " + str(exc))[:768])
        v1_write(application_path, state)
        raise
    expected_keys = [key for key, _ in updates]
    if (outcome["target_name"] != origin["preset_name"] or outcome["slot_number"] != origin["slot_number"]
            or outcome["keys"] != expected_keys
            or outcome["slot_assignment_changed"] is not False or outcome["dirty"] is not True):
        state.update(status="uncertain", phase="unexpected_outcome", updated_at=int(time.time() if now is None else now),
                     message="Orca committed but returned an unexpected target/result; inspect the edited preset without retrying.",
                     outcome=outcome)
        v1_write(application_path, state)
        raise ContractError(state["message"])
    state.update(status="applied", phase="committed", updated_at=int(time.time() if now is None else now),
                 message="Result applied to Orca's edited originating filament preset; it remains unsaved and dirty.",
                 outcome=outcome)
    v1_write(application_path, state)
    v1_write(directory / "receipt.json", dict(schema="helix-orca-v1-ack/v2",
             request_id=request["request_id"], origin_id=request["origin_id"],
             result_sha256=digest(result), application_sha256=digest(state), status="applied"))
    return state


class V2CalibrationPanel(orca.script.ScriptPluginCapabilityBase):
    """Ordinary owner-local companion with one persistent Script worker.

    WebView callbacks enqueue commands only. The worker owns the blocking
    begin_update/set/commit transaction as required by the pinned host API.
    """
    def __init__(self):
        super().__init__()
        self.panel = None
        self.directory = None
        self.commands = queue.Queue(maxsize=16)
        self.stopping = False
        self.last_application_notice = None

    def get_name(self):
        return "Helix Calibration"

    def execute(self):
        self.directory = v1_storage(orca.host.plugin.storage())
        kwargs = dict(html=V2_PAGE, title="Helix Calibration", width=460, height=740,
                      on_message=self.on_message, on_close=self.on_close)
        try:
            self.panel = orca.host.ui.create_dock_panel(**kwargs, dock="right")
        except Exception:
            self.panel = orca.host.ui.create_window(**kwargs)
        while not self.stopping:
            try:
                command = self.commands.get(timeout=.25)
            except queue.Empty:
                command = dict(command="poll_application")
            if command["command"] == "stop":
                break
            if command["command"] == "slots":
                try:
                    names = list(orca.host.preset_bundle().current_filament_preset_names())
                    slots = [dict(slot_number=index, preset_name=str(name))
                             for index, name in enumerate(names, 1) if name]
                    payload = dict(command="v2_slots", slots=slots,
                                   error=None if len(slots) == len(names) else "One or more active slots has no preset identity.")
                except Exception as exc:
                    payload = dict(command="v2_slots", slots=[], error=("Unavailable: " + str(exc))[:768])
                if self.panel and self.panel.is_open():
                    self.panel.post(payload)
            elif command["command"] == "capture":
                try:
                    retained = v1_read(self.directory / "context.json")
                    origin_id = retained["origin_id"] if retained else secrets.token_hex(16)
                    captured = v2_capture(orca.host, origin_id, command["origin_slot"])
                    if retained and captured != retained:
                        captured["origin_id"] = secrets.token_hex(16)
                    captured = validate_context_v2(captured)
                    origins = self.directory / "origins"
                    origins.mkdir(exist_ok=True)
                    v1_write(self.directory / "context.json", captured)
                    origin_path = origins / (captured["origin_id"] + ".json")
                    old = v1_read(origin_path)
                    if old is not None and canonical(old) != canonical(captured):
                        raise ContractError("Original V2 context is immutable")
                    v1_write(origin_path, captured)
                    payload = dict(command="v2_context", context=captured,
                                   context_sha256=digest(captured), error=None)
                except Exception as exc:
                    payload = dict(command="v2_context", context=None, context_sha256=None,
                                   error=("Unavailable: " + str(exc))[:768])
                if self.panel and self.panel.is_open():
                    self.panel.post(payload)
            elif command["command"] == "poll_application":
                try:
                    state = v2_apply_inbox(self.directory, orca.host.preset.filament)
                    payload = dict(command="v2_application", state=state, error=None)
                except Exception as exc:
                    payload = dict(command="v2_application", state=v1_read(self.directory / "application.json"),
                                   error=("Unavailable: " + str(exc))[:768])
                notice = canonical(payload)
                if self.panel and self.panel.is_open() and notice != self.last_application_notice:
                    self.last_application_notice = notice
                    self.panel.post(payload)
        return orca.ExecutionResult.success("Helix Calibration worker stopped.")

    def on_message(self, message):
        if not isinstance(message, dict) or message.get("command") not in ("slots", "capture"):
            return
        command = dict(command=message["command"])
        if command["command"] == "capture":
            if type(message.get("origin_slot")) is not int or message["origin_slot"] < 1:
                return
            command["origin_slot"] = message["origin_slot"]
        try:
            self.commands.put_nowait(command)
        except queue.Full:
            if self.panel and self.panel.is_open():
                self.panel.post(dict(command="v2_application", state=None,
                                     error="Application request already queued."))

    def on_close(self):
        self.stopping = True
        try:
            self.commands.put_nowait(dict(command="stop"))
        except queue.Full:
            pass
        self.panel = None
