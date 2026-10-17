"""Join native storage intent, the one-shot coordinator and originating Orca.

No command line, service or automatic authorization is provided. The caller
must supply the existing bounded event/artifact transports; physical permit
issuance remains separate and absent during this readiness program.
"""
from __future__ import annotations
import copy
import importlib.util
from pathlib import Path
import types

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('_print_companion_parts',ROOT/'scripts/temperature-print-companion.py')
generator=importlib.util.module_from_spec(spec);spec.loader.exec_module(generator)
protocol=types.ModuleType('_print_readiness_protocol')
exec(generator.generated_parts().split('COMMUNICATION_ACTION_NAME')[0],protocol.__dict__)
IDENTITY=('request_id','origin_id','context_sha256','file_sha256','file','file_bytes','printer')

class ControllerError(ValueError):pass

class NativePrintController:
    def __init__(self,coordinator,outbox,qualification,*,event_sink,write_inbox,authorize_intent=None):
        probe=outbox.get('payload',{}) if isinstance(outbox,dict) else {}
        recovered=coordinator.status().phase!='empty'
        structural=probe.get('expires_at',0)-probe.get('ttl_seconds',0) if recovered else int(coordinator.wall_time())
        self.outbox=protocol.validate_outbox(outbox,now=structural)
        self.request=copy.deepcopy(self.outbox['payload'])
        self.coordinator=coordinator
        if not recovered:
            self.coordinator.bind_request(self.request,qualification)
        else:
            bound=self.coordinator.bound_request().as_dict()
            if any(self.request.get(k)!=v for k,v in bound.items()):
                raise ControllerError('Recovered journal does not match the originating request')
            saved=self.coordinator._qualification_from_state()
            incoming=type(saved).from_mapping(qualification)
            if incoming.as_dict()!=saved.as_dict():
                raise ControllerError('Recovered qualification differs from the reviewed job')
        self.event_sink=event_sink;self.write_inbox=write_inbox
        self.authorize_intent=authorize_intent
        self.committed_result=copy.deepcopy(self.coordinator._state.get("native_result"))
    def _identity(self):return {k:self.request[k] for k in IDENTITY}
    def offer(self):
        created=self.request['expires_at']-self.request['ttl_seconds']
        if self.coordinator.status().phase!='awaiting_start' or self.coordinator.wall_time()>=created+900:
            raise ControllerError('Original physical Start window is closed')
        sample=self.coordinator._normalized_snapshot()
        if not sample.connected or not sample.ready or sample.state!='standby' or sample.queue_job_ids:
            raise ControllerError('Printer is not available for a request')
        remaining=self.request['expires_at']-self.coordinator.wall_time()
        if not 0<remaining<=3600:raise ControllerError('Request expired')
        envelope=self.coordinator._state.get('native_envelope')
        if envelope is None:
            envelope={'session':copy.deepcopy(self.request),'lease':{'issued_eventtime':sample.eventtime,'expires_eventtime':sample.eventtime+remaining}}
            self.coordinator._state['native_envelope']=copy.deepcopy(envelope)
        attempts=self.coordinator._state.get('forward_attempts',0)
        if type(attempts) is not int or attempts>=5:raise ControllerError('Bounded request delivery exhausted')
        self.coordinator._state['forward_attempts']=attempts+1;self.coordinator._persist()
        self.event_sink('helix_orca_temperature_print.request.v1',copy.deepcopy(envelope))
        return self._publish()
    def _publish(self):
        state=self.coordinator.status()
        phase=state.phase
        if phase=='awaiting_start':
            created=self.request['expires_at']-self.request['ttl_seconds']
            native='ready' if self.authorize_intent and self.coordinator.wall_time()<created+900 else 'received'
        elif phase in ('start_dispatch_intent','start_dispatched'):native='starting'
        elif phase=='printing':native='printing'
        elif phase=='completion_pending':native='confirming'
        elif phase in ('cancel_dispatch_intent','cancel_dispatched'):native='cancelling'
        elif phase=='completed' and state.result_available:native='complete'
        elif phase=='cancelled':native='cancelled'
        elif 'uncertain' in phase or phase=='completed':native='uncertain'
        else:native='failed'
        eventtime=self.coordinator._state.get('last_eventtime',0)
        if native not in ('failed','cancelled','uncertain'):
            try:
                sample=self.coordinator._normalized_snapshot()
                if not sample.connected or not sample.ready:raise ControllerError('Printer unavailable')
                eventtime=sample.eventtime
            except Exception:
                self.coordinator._fail('failed','Printer status unavailable during publication')
                state=self.coordinator.status();native='uncertain'
        sequence=self.coordinator.reserve_status_sequence()
        data=dict(self._identity(),schema='helix-orca-temperature-print-status/v1',state=native,
            eventtime=eventtime,sequence=sequence)
        if native=='ready':
            data.update(authorized=True,estimated_duration_s=self.coordinator._qualification_from_state().estimated_duration_s)
        if state.job_id:data['job_id']=state.job_id
        if native=='complete':
            data.update(job_id=state.job_id,completion_sha256=state.completion_proof_sha256,observed_running=True)
        self.event_sink('helix_orca_temperature_print.status.v1',data)
        return state
    def step(self,native_storage):
        session=native_storage.get('print_session') if isinstance(native_storage,dict) else None
        if not isinstance(session,dict) or session.get('request')!=self.request:
            raise ControllerError('Native storage does not bind the originating request')
        state=self.coordinator.status()
        intent=session.get('start_intent')
        if intent and state.phase=='awaiting_start':
            if self.authorize_intent is None:raise ControllerError('Separate physical authorization is absent')
            parsed=self.coordinator.parse_start_intent(intent)
            permit=self.authorize_intent(self.coordinator,parsed)
            self.coordinator.start(parsed,permit=permit)
        cancel=session.get('cancel_intent')
        if cancel and self.coordinator.status().phase=='printing':
            check=dict(cancel)
            if check.get('schema')!='helix-orca-temperature-cancel/v1':raise ControllerError('Invalid native cancellation')
            check['schema']='helix-orca-temperature-start/v1'
            parsed=self.coordinator.parse_start_intent(check)
            sample=self.coordinator.adapter.snapshot()
            if not parsed.eventtime<=sample.eventtime<parsed.expires_eventtime:
                raise ControllerError('Stale native cancellation')
            self.coordinator.cancel()
        self.coordinator.poll()
        state=self.coordinator.status()
        result=session.get('result')
        if result:
            if not state.result_available or not state.completion_proof_sha256:
                raise ControllerError('A result requires independent successful completion')
            selected=protocol.validate_selection_result(self.request,result,now=int(self.coordinator.wall_time()))
            if selected['job_id']!=state.job_id or selected['completion_sha256']!=state.completion_proof_sha256:
                raise ControllerError('Result completion evidence does not match the monitored job')
            if self.committed_result is not None and selected!=self.committed_result:
                raise ControllerError('The first selected result is immutable')
            self.coordinator._state['native_result']=copy.deepcopy(selected)
            self.coordinator._persist()
            self.write_inbox(copy.deepcopy(selected));self.committed_result=selected
        return self._publish()
    def acknowledge(self,receipt):
        if self.committed_result is None:raise ControllerError('No result has been returned')
        expected=protocol.make_ack(self.committed_result)
        if receipt!=expected:raise ControllerError('Receipt differs from originating committed result')
        self.event_sink('helix_orca_temperature_print.ack.v1',copy.deepcopy(receipt))
