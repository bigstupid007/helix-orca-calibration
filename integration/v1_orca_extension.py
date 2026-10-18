"""Embedded after the qualified October 15 plugin. UI callbacks/local I/O only."""
import os
import secrets
from decimal import Decimal
V1_PAGE = r'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>
*{box-sizing:border-box}body{font:14px system-ui;margin:0;background:#f5f7f8;color:#203440}main{max-width:720px;margin:auto;padding:20px}h1{font-size:24px;line-height:1.2;margin:4px 0 8px}h2{font-size:16px;margin:0 0 12px}p{line-height:1.5}.eyebrow{color:#087e76;font-size:11px;font-weight:750;letter-spacing:.1em;text-transform:uppercase}.muted{color:#59707c;font-size:13px}.card{background:white;border:1px solid #dce4e8;border-radius:12px;padding:18px;margin:16px 0;overflow-wrap:anywhere}.row{display:grid;grid-template-columns:90px 1fr;gap:8px 14px}.label{color:#59707c}.value{font-weight:600}.badge{display:inline-block;padding:5px 9px;background:#e4f3ef;color:#086c5b;border-radius:6px;font-size:12px;font-weight:700}.pending{background:#fff0d9;color:#785510}.result{border-color:#008579;border-width:2px}.big{font-size:30px;color:#007a70;font-weight:700}button{font:inherit;background:white;color:#006c65;border:1px solid #a1c5bf;border-radius:6px;padding:9px 12px;cursor:pointer}button:focus-visible,summary:focus-visible{outline:3px solid #008579;outline-offset:3px}details{margin:18px 0}summary{cursor:pointer;color:#59707c;font-size:12px}pre{white-space:pre-wrap;font:12px system-ui}#status{white-space:pre-wrap} [hidden]{display:none!important}@media(max-width:360px){main{padding:12px}.card{padding:14px}.row{grid-template-columns:70px 1fr;gap:7px}}
</style></head><body><main><span class="eyebrow">Helix Calibration · V1 candidate</span><h1>Ready at the printer</h1><p class="muted">Choose and configure your calibration on Helix. Orca keeps the profiles, preparation and returned result together here.</p>
<section id="result" class="card result" hidden><span class="badge pending">NOT APPLIED</span><h2 style="margin-top:12px">Your calibration result</h2><div id="result-value" class="big"></div><p id="result-setting"></p><p class="muted">Returned to the original context. No profile has been changed.</p></section>
<section class="card"><h2>Selected Orca profiles</h2><div id="profiles" class="row"></div><p id="profile-note" class="muted"></p><button id="refresh">Refresh profiles</button></section>
<section class="card"><span id="phase" class="badge">Waiting for Helix</span><h2 style="margin-top:14px">Preparation</h2><p id="status" role="status" aria-live="polite">Open this panel to share the selected profiles with the local coordinator.</p><div id="job" class="row"></div><p class="muted">Generation does not start a print. Confirm and Start are separate actions on Helix. Physical execution is disabled in this review candidate.</p></section>
<details><summary>Connection and provenance</summary><pre id="technical"></pre></details></main><script>(function(){'use strict';function send(command){window.orca.postMessage({command:command});}function text(id,value){document.getElementById(id).textContent=value;}function rows(id,values){var root=document.getElementById(id);root.textContent='';values.forEach(function(pair){var a=document.createElement('span'),b=document.createElement('span');a.className='label';b.className='value';a.textContent=pair[0];b.textContent=pair[1];root.append(a,b);});}window.orca.onMessage(function(s){if(!s||s.command!=='v1_state')return;var c=s.context,v=s.view||{},st=v.status||{},original=v.original;rows('profiles',c?[['Printer',c.printer.saved.name],['Process',c.process.saved.name],['Filament',c.filament.saved.name],['Nozzle',c.nozzle_mm+' mm']]:[['Profiles','Unavailable']]);text('profile-note',original?'Calibration retains original '+original.filament+' even when the selected profile changes.':'Saved preset identity, edited copy and effective values are retained separately.');text('phase',st.phase?st.phase.replace(/_/g,' '):'Waiting for Helix');text('status',s.error||st.message||'Choose a calibration on Helix. The local coordinator must be running.');var p=st.prepared;rows('job',p?[['Calibration',p.calibration.replace(/_/g,' ')],['Parameters',JSON.stringify(p.parameters)],['Artifact',p.artifact?p.artifact.name:'Unavailable'],['Native parity',p.parity.qualified?'Qualified':p.parity.reason]]:[]);var r=v.result;document.getElementById('result').hidden=!r;if(r){text('result-value',String(r.value));text('result-setting',r.setting+' · original '+(original?original.filament:'profile'));}text('technical','Runtime: '+(c?c.runtime.version+' / '+c.runtime.build:'Unavailable')+'\nContext: '+(s.context_sha256||'Unavailable')+'\n'+(p?'Generator: '+p.generator.route+' / '+p.generator.build:'No generated job')+'\n'+(s.health||'Coordinator status unavailable')+'\nResult changes are never applied automatically.');});document.getElementById('refresh').onclick=function(){send('refresh');};send('ready');setInterval(function(){send('poll');},2000);})();</script></body></html>'''


def v1_storage(root):
    directory = pathlib.Path(str(root)) / "v1"
    if directory.is_symlink():
        raise ContractError("V1 storage must not be a link")
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def v1_write(path, value):
    if path.is_symlink():
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
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_MESSAGE:
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
            if sensitive:
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
        current = Decimal(original["effective"]["filament_flow_ratio"])
        choices = [float(current + Decimal(i) / 100) for i in range(-5, 6)]
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

    def on_message(self, message):
        if not isinstance(message, dict) or message.get("command") not in ("ready", "refresh", "poll"):
            return
        self.error = None
        try:
            if message["command"] in ("ready", "refresh"):
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
            view = v1_read(self.directory / "view.json")
            health = v1_read(self.directory / "runtime" / "health.json")
            committed = v1_commit_inbox(self.directory)
            if view:
                view["result"] = None
            if committed:
                view = view or {}
                view["result"] = committed["result"]
                view["original"] = {role: committed["original"][role]["saved"]["name"] for role in ("printer", "process", "filament")}
        except Exception as exc:
            self.error = "Unavailable: " + str(exc)[:500]
            view = health = None
        if self.panel and self.panel.is_open():
            self.panel.post(dict(command="v1_state", context=self.context, context_sha256=digest(self.context) if self.context else None,
                                 view=view, error=self.error,
                                 health="Coordinator responding" if health and health.get("ok") else "Coordinator unavailable or blocked"))
