#!/usr/bin/env python3
"""Windows-origin offline qualification bridge for actual native UI requests.

Offer and status come from real Coordinator/DirectoryEvents/normal tick.
No prepared job, status, print adapter or expired nonce is synthesized.
Full contexts, configuration, reports and G-code remain Windows-local.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from integration import v1_contract as c, v1_routing as routing, v1_parity as parity
from integration.v1_runtime import Coordinator, InstanceLock, atomic_json, read_json
from integration.v1_transport import DirectoryEvents

PIN = '6a7763f08d1a175a464a00ce13f0b5a815662fc4'
EXE_SHA = 'e2b6da4c20e7080eade97379f326dcfcaa90f1ecb9991f1db9eb61e3065a9759'
CONTEXT_SHA = '3bf24bab6c2ac71cf7c0017d8889d4430006d3cd489a512ff656990f41324b3c'
MARKER_SHA = '5bc7b6c9412068f0bf1b536376c319fb7c572ce29912aa6983b1c24d1496e2fa'
SCHEMA = 'helix-orca-v1-windows-parameter-bridge/v1'
TERMINAL = ('blocked', 'failed', 'cancelled', 'delivered')
SOURCE_NAMES = ('scripts/v1-windows-parameter-bridge.py', 'scripts/v1-runtime.py',
                'integration/v1_contract.py', 'integration/v1_runtime.py', 'integration/v1_transport.py',
                'integration/v1_routing.py', 'integration/v1_generation.py', 'integration/v1_parity.py',
                'integration/v1_engine.py')


class Refused(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise Refused(code)


def ordinary(path, exists=True):
    path = Path(path)
    require(path.is_absolute() and not str(path).startswith(('\\\\', '//')), 'local_absolute_path_required')
    for entry in (path, *path.parents):
        if entry.exists() or entry.is_symlink():
            info = entry.lstat()
            require(not stat.S_ISLNK(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & 0x400,
                    'linked_or_reparse_path_refused')
    return path.resolve(strict=exists)


def sha(path):
    path = ordinary(path)
    require(path.is_file() and path.stat().st_size <= c.MAX_MESSAGE, 'bounded_local_metadata_required')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_tick():
    spec = importlib.util.spec_from_file_location('parameter_bridge_normal_tick', ROOT/'scripts/v1-runtime.py')
    module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.tick


def generator_config(path):
    config = read_json(path)
    require(isinstance(config, dict), 'private_generator_config_required')
    require(not set(config).intersection(('now', 'runner', 'owned_jobs', 'moonraker', 'deployment_authorization')),
            'clock_runner_or_physical_adapter_config_refused')
    require(config.get('source_commit') == PIN and config.get('runtime') == parity.PINS[PIN],
            'pinned_runtime_required')
    require(config.get('executable_sha256') == EXE_SHA, 'pinned_windows_executable_required')
    timeout = config.get('timeout_seconds', 45)
    require(type(timeout) in (int,float) and 1 <= timeout <= 45, 'bounded_generation_timeout_required')
    config['timeout_seconds'] = timeout
    if 'native_engine' in config:
        native = config['native_engine']
        require(isinstance(native,dict) and not set(native).intersection(('now','runner')),
                'native_clock_or_runner_override_refused')
        timeout = native.get('timeout_seconds',45)
        require(type(timeout) in (int,float) and 1 <= timeout <= 45, 'bounded_native_timeout_required')
        native['timeout_seconds'] = timeout
    # No fallback/route substitution. Native Windows unavailability remains real.
    routing.routes(config)
    return config


def validate_session(value, coordinator, context, now):
    if isinstance(value, dict) and set(value) == {'v1_session'}:
        value = value['v1_session']
    require(isinstance(value, dict), 'actual_native_session_required')
    request = c.validate_request(value.get('request'), now=now)
    offer = coordinator.state['offer']
    require(isinstance(offer, dict) and c.canonical(value.get('offer')) == c.canonical(offer),
            'native_offer_differs_from_actual_coordinator')
    require(c.digest(context) == request['context_sha256'] and context['origin_id'] == request['origin_id'],
            'original_context_binding_mismatch')
    for key in ('request_id','origin_id','context_sha256','created_at','expires_at'):
        require(request[key] == offer[key], 'native_request_identity_differs_from_actual_offer')
    require(offer['nozzle_mm'] == context['nozzle_mm'], 'native_offer_nozzle_mismatch')
    for role in ('printer','process','filament'):
        require(offer[role] == context[role]['saved']['name'], 'native_offer_profile_identity_mismatch')
    require(coordinator.state['context'] == context, 'actual_coordinator_context_changed')
    retained = coordinator.state['request']
    if retained is None:
        require(set(value) == {'request','offer','phase','sequence','message'}
                and value['phase'] == 'requested' and type(value['sequence']) is int and value['sequence'] == 0,
                'unconsumed_native_generate_session_required')
        require(isinstance(value['message'],str) and len(value['message'].encode()) <= 768,
                'bounded_native_message_required')
    else:
        require(request == retained, 'immutable_request_already_retained')
        for key in ('result','receipt'):
            require(value.get(key) is None, 'result_or_receipt_outside_parameter_trial')
        if value.get('prepared') is not None:
            require(value['prepared'] == coordinator.state['prepared'], 'native_prepared_differs_from_actual_coordinator')
    event = {'request': request}
    if value.get('intent') is not None:
        intent = value['intent']
        require(isinstance(intent,dict) and intent.get('action') == 'cancel', 'only_actual_prestart_cancel_supported')
        event['intent'] = intent
    return copy.deepcopy(value), event


def trace(coordinator, root, event=None):
    request = coordinator.state['request']
    result = dict(schema=SCHEMA, actual_offline_coordinator=True, test_transport=True,
                  physical_actions=False, physical_readiness=False, actions_adapter_present=False,
                  context_sha256=c.digest(coordinator.state['context']), offer=coordinator.state['offer'],
                  source_files=read_json(root/'source-files.json'))
    if request is None:
        result.update(op='offer', offer_sha256=c.digest(result['offer']))
        return result
    directory = root/'coordinator/jobs'/request['request_id']
    prepared = coordinator.state['prepared']
    artifact_verified = False
    if prepared and prepared['artifact']:
        try:
            Coordinator.verify_artifact(prepared,directory);artifact_verified = True
        except (ValueError,OSError,KeyError):
            pass
    qualified = False
    if artifact_verified and prepared['parity']['qualified']:
        try:
            Coordinator.verify_parity(prepared,directory);qualified = True
        except (ValueError,OSError,KeyError):
            pass
    result.update(op='consume', request=request, request_sha256=c.digest(request),
                  status=coordinator.status(), status_sha256=c.digest(coordinator.status()),
                  generator_dispatched=directory.is_dir(),
                  executable_invocation_recorded=(directory/'invocation.json').is_file(),
                  artifact_generated=artifact_verified,
                  qualified=qualified,
                  generation_state=('not_dispatched' if not directory.is_dir() else
                                    'artifact_qualified' if qualified else
                                    'artifact_unqualified' if artifact_verified else 'blocked_before_artifact'))
    if event:
        result['native_event_sha256'] = c.digest(event)
        transport = read_json(root/'offline/native.json')
        journal = read_json(coordinator.path)
        result.update(transport_request=transport.get('request'),
                      coordinator_request=journal.get('request'),
                      transport_request_sha256=c.digest(transport.get('request')),
                      coordinator_request_sha256=c.digest(journal.get('request')),
                      transport_event_sha256=c.digest(transport))
    return result


def execute(op, root, context, config, source_files, native_value=None, native_file_sha=None, now=time.time):
    """Core also supports source-only tests with real routing but unavailable backends."""
    storage, channel = root/'storage', root/'offline'
    if op == 'offer' and not root.exists():
        root.mkdir(exist_ok=False)
        atomic_json(root/'source-files.json',source_files)
        atomic_json(storage/'context.json',context)
    else:
        require(root.is_dir() and read_json(root/'source-files.json') == source_files,
                'actual_offer_source_files_changed')
        require(read_json(storage/'context.json') == context, 'original_context_copy_changed')
    with InstanceLock(root/'bridge.lock'):
        coordinator = Coordinator(root/'coordinator',routing.generate,config,routing.capabilities(config),now=now,job_adapter=None)
        require(coordinator.job_adapter is None and coordinator.state.get('job') is None,
                'physical_or_started_job_refused')
        transport = DirectoryEvents(channel)
        if op == 'offer':
            require(coordinator.state['request'] is None or coordinator.state['phase'] in TERMINAL,
                    'active_trial_requires_actual_native_cancel')
            # Archive authority through normal Coordinator.offer; discard only the
            # owned event copy already retained in trials, never native UI storage.
            if (channel/'native.json').exists():
                (channel/'native.json').unlink()
            load_tick()(coordinator,storage,transport)
            offer = read_json(channel/'context.json')
            require(offer == coordinator.state['offer'] and coordinator.state['request'] is None,
                    'normal_tick_did_not_issue_offer')
            trial = root/'trials'/offer['request_id'];trial.mkdir(parents=True,exist_ok=True)
            if (trial/'offered-config.json').exists():
                require(read_json(trial/'offered-config.json') == config, 'existing_offer_configuration_changed')
            else:
                atomic_json(trial/'offered-config.json',config)
                atomic_json(trial/'offer.json',offer)
        else:
            session,event = validate_session(native_value,coordinator,context,now())
            request = event['request'];trial = root/'trials'/request['request_id']
            require(read_json(trial/'offer.json') == coordinator.state['offer'], 'retained_offer_changed')
            original = read_json(trial/'offered-config.json')
            # Matching independent reference may be attached after native UI export;
            # recipe/executable/profile/source configuration cannot be swapped.
            require({k:v for k,v in original.items() if k != 'native_reference'} ==
                    {k:v for k,v in config.items() if k != 'native_reference'}, 'offered_generator_configuration_changed')
            stamp = str(time.time_ns())
            atomic_json(trial/('native-session-'+stamp+'.json'),session)
            atomic_json(trial/('native-event-'+stamp+'.json'),event)
            atomic_json(trial/('consume-config-'+stamp+'.json'),config)
            atomic_json(trial/('input-provenance-'+stamp+'.json'),dict(native_file_sha256=native_file_sha,
                        native_session_sha256=c.digest(session),native_event_sha256=c.digest(event)))
            # A terminal duplicate is read-only; normal tick would issue the next
            # offer before consuming stale input. Only explicit `offer` advances.
            duplicate_terminal = coordinator.state['request'] == request and coordinator.state['phase'] in TERMINAL
            if not duplicate_terminal:
                atomic_json(channel/'native.json',event)
                load_tick()(coordinator,storage,transport)
            require(coordinator.state['request'] == request, 'normal_tick_did_not_retain_exact_native_request')
        atomic_json(root/'private-generator-config.json',config)
        result = trace(coordinator,root, event if op == 'consume' else None)
        require(len(c.canonical(result)) <= 65536, 'metadata_summary_oversized')
        atomic_json(trial/('bridge-'+op+'-'+str(time.time_ns())+'.json'),result)
        return result


def run(args):
    require(os.name == 'nt', 'windows_execution_required')
    base = ordinary(Path(os.environ['LOCALAPPDATA'])/'HelixOrcaCalibration/v1-qualification')
    require(sha(base/'data/.helix-orca-v1-qualification') == MARKER_SHA, 'isolated_target_marker_mismatch')
    root = ordinary(args.root,exists=False)
    require(root != base and root.is_relative_to(base), 'owned_qualification_root_required')
    for path in (args.context,args.config):
        require(ordinary(path).is_relative_to(base), 'private_input_outside_qualification_root')
    context = c.validate_context(read_json(args.context))
    require(c.digest(context) == CONTEXT_SHA and context['runtime'] == parity.PINS[PIN],
            'immutable_original_context_or_runtime_mismatch')
    config = generator_config(args.config)
    source_files = {name:sha(ROOT/name) for name in SOURCE_NAMES}
    native,native_sha = None,None
    if args.op == 'consume':
        require(args.native_session is not None and ordinary(args.native_session).is_relative_to(base),
                'actual_local_native_session_required')
        native_sha = sha(args.native_session);native = read_json(args.native_session)
    else:
        require(args.native_session is None, 'offer_cannot_import_a_native_request')
    return execute(args.op,root,context,config,source_files,native,native_sha)


class Parser(argparse.ArgumentParser):
    def error(self,message):
        raise Refused('invalid_cli_arguments')


def main():
    try:
        parser = Parser(description=__doc__)
        parser.add_argument('--op',choices=('offer','consume'),required=True)
        for name in ('root','context','config'):
            parser.add_argument('--'+name,type=Path,required=True)
        parser.add_argument('--native-session',type=Path)
        print(c.canonical(run(parser.parse_args())).decode())
        return 0
    except Exception as error:
        code = str(error) if isinstance(error,Refused) else 'local_parameter_bridge_failed'
        print(json.dumps(dict(schema=SCHEMA,success=False,qualified=False,failure=code,
                              physical_actions=False,physical_readiness=False),sort_keys=True))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
