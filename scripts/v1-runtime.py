#!/usr/bin/env python3
"""V1 local coordinator: direct events/local artifacts, no Codex test worker.

The default review invocation has no action-enabled printer transport. Default
transport is offline. --moonraker-events requires explicit existing LAN consent.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import secrets
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from integration.v1_contract import ContractError, digest, exact, hex_value, validate_request_v2
from integration.v1_runtime import Coordinator, InstanceLock, atomic_json, read_json
from integration.v1_transport import DirectoryEvents, MoonrakerEvents


def tick(coordinator, storage, transport):
    def event(kind):
        return "helix_orca_v1." + kind + (".v2" if coordinator._current() else ".v1")
    availability = storage / "context-status.json"
    unavailable = availability.exists() and read_json(availability).get("available") is not True
    if unavailable and (coordinator.state["request"] is None or coordinator.state["phase"] in ("blocked", "failed", "cancelled")):
        if coordinator.state["request"] is not None:
            coordinator.offer(coordinator.state["context"])
        if coordinator.state["offer"]:
            offer = dict(coordinator.state["offer"])
            offer["capabilities"] = [dict(id=c["id"], available=False, reason="Current Orca profile context is unavailable.") for c in coordinator.capabilities]
            transport.send(event("context"), offer)
        return
    context = storage / "context.json"
    if coordinator.state["request"] is not None and coordinator.state["phase"] not in ("delivered", "blocked", "failed", "cancelled"):
        transport.send(event("context"), coordinator.state["offer"])
    elif context.exists():
        offer = coordinator.offer(read_json(context))
        transport.send(event("context"), offer)
    native = transport.read()
    if coordinator.state.get("receipt") and native.get("receipt") == coordinator.state["receipt"]:
        coordinator.state["native_acknowledged"] = True
        coordinator._persist()
    offered = coordinator.state["offer"]
    if isinstance(native.get("request"), dict) and offered and native["request"].get("request_id") == offered["request_id"]:
        coordinator.request(native["request"])
    retained = coordinator.state["request"]
    native_v2 = native.get("v2") if isinstance(native.get("v2"), dict) else {}
    warning_state = native_v2.get("warning") if isinstance(native_v2.get("warning"), dict) else {}
    decision = warning_state.get("decision")
    if isinstance(decision, dict) and retained and coordinator._current():
        exact(decision, "schema request_id origin_id prepared_sha256 warning_sha256 warning_codes action intent_id",
              "native warning decision")
        warning = coordinator.warning_event()
        if (warning is None or decision["schema"] != "helix-orca-v1-native-warning-decision/v2"
                or any(decision[key] != warning[key] for key in
                       ("request_id", "origin_id", "prepared_sha256", "warning_sha256", "warning_codes"))
                or decision["action"] not in ("continue", "cancel")):
            raise ContractError("Native warning decision differs from the exact prepared warning")
        hex_value(decision["intent_id"], 32)
        if decision["action"] == "continue":
            acknowledgement = coordinator.state.get("warning_ack") or dict(
                schema="helix-orca-v1-warning-ack/v2", request_id=retained["request_id"],
                prepared_sha256=warning["prepared_sha256"], warning_codes=warning["warning_codes"],
                acknowledged_at=int(coordinator.now()))
            coordinator.acknowledge_warnings(acknowledgement)
        # Cancel is executed only by the separately persisted top-level
        # intent/v2 below. Helix includes the warning decision for prompt
        # correlation, but it must not create a second cancellation identity.
    # V2 native storage carries only the bound warning decision.  The
    # coordinator mints and returns the canonical acknowledgement timestamp;
    # a Helix-local convenience copy must never compete with that authority.
    if (not coordinator._current() and isinstance(native.get("warning_ack"), dict) and retained
            and native["warning_ack"].get("request_id") == retained["request_id"]):
        coordinator.acknowledge_warnings(native["warning_ack"])
    if isinstance(native.get("intent"), dict) and retained and native["intent"].get("request_id") == retained["request_id"]:
        coordinator.intent(native["intent"])
    coordinator.poll_job()
    coordinator.reconcile_native(native)
    if isinstance(native.get("result"), dict) and retained and native["result"].get("request_id") == retained["request_id"]:
        result = coordinator.result(native["result"])
        inbox = dict(result=result, request=coordinator.state["request"],
                     prepared=coordinator.state["prepared"], completion=coordinator.state["completion"])
        if coordinator._current():
            inbox.update(warning_ack=coordinator.state.get("warning_ack"),
                         qualification=coordinator.state.get("qualification"))
        atomic_json(storage / "inbox.json", inbox)
    retry = native.get("application_retry")
    if not isinstance(retry, dict):
        retry = native_v2.get("application_retry")
    if isinstance(retry, dict) and coordinator._current() and coordinator.state.get("result"):
        atomic_json(storage / "application-retry.json", coordinator.authorize_application_retry(retry))
    application = storage / "application.json"
    if coordinator._current() and coordinator.state.get("result") and application.exists():
        transport.send(event("application"), coordinator.application_event(read_json(application)))
    receipt = storage / "receipt.json"
    if coordinator.state["result"] and receipt.exists():
        candidate = read_json(receipt)
        if candidate.get("request_id") == coordinator.state["result"]["request_id"]:
            ack = coordinator.acknowledge(candidate)
            transport.send(event("ack"), ack)
    status = coordinator.status()
    if status:
        atomic_json(storage / "status.json", status)
        context = coordinator.state["context"]
        atomic_json(storage / "view.json", dict(status=status, result=coordinator.state["result"],
            original=dict({role: context[role]["saved"]["name"] for role in ("printer", "process", "filament")},
                nozzle_mm=context["nozzle_mm"], context_sha256=coordinator.state["request"]["context_sha256"],
                edited_roles=[role for role in ("printer", "process", "filament") if context[role]["saved"] != context[role]["edited"]])))
        transport.send(event("status"), status)
        if coordinator._current() and status["phase"] == "warning":
            transport.send(event("warning"), coordinator.warning_event())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storage", type=Path, required=True, help="Exact originating plugin's v1 storage directory")
    parser.add_argument("--config", type=Path, required=True, help="Private explicit generator configuration")
    parser.add_argument("--state", type=Path, help="Dedicated runtime journal; defaults below plugin v1 storage")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--deployment-authorization", type=Path, help="Separately approved owner-private exact deployment record; absent in review")
    parser.add_argument("--run-id", default=None, help="Owned launcher identity, lowercase 32-hex")
    parser.add_argument("--stop-file", type=Path, help="Exact owned JSON stop request path")
    parser.add_argument("--offline-channel", type=Path)
    parser.add_argument("--moonraker-events", action="store_true", help="No physical deployment or Start; V1 events only")
    args = parser.parse_args()
    from integration.v1_routing import generate, capabilities
    config = read_json(args.config)
    root = args.state or args.storage / "runtime"
    run_id = hex_value(args.run_id or secrets.token_hex(16), 32)
    stop_file = args.stop_file or root / "stop.json"
    if args.moonraker_events:
        connection = config["moonraker"]
        transport = MoonrakerEvents(connection["origin"], connection["expected_host"], connection["expected_version"],
            os.environ.get(connection.get("api_key_env", "HELIX_ORCA_MOONRAKER_API_KEY")),
            trusted_lan=connection.get("existing_trusted_lan_ack") is True)
    else:
        transport = DirectoryEvents(args.offline_channel or root / "offline")
    stopped = False
    def stop(*_):
        nonlocal stopped
        stopped = True
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    with InstanceLock(args.storage / "coordinator.lock"), InstanceLock(root / "runtime.lock"):
        from integration.v1_deployment import authorized, require_native_channel
        from integration.v1_jobs import current_candidate_verifier, from_config
        deployment = authorized(args.deployment_authorization, config, Path(__file__))
        if deployment and config.get("owned_jobs", {}).get("actions_enabled") is True:
            require_native_channel(config, args.moonraker_events)
        current = isinstance(config.get("build_qualification"), dict) and \
            config["build_qualification"].get("schema") == "helix-orca-v1-build-qualification/v2"
        jobs = from_config(config, root / "owned-jobs", deployment_authorized=deployment,
            api_key=os.environ.get(config.get("moonraker", {}).get("api_key_env", "HELIX_ORCA_MOONRAKER_API_KEY")),
            candidate_verifier=(current_candidate_verifier(config["build_qualification"])
                                if current else None),
            request_validator=(validate_request_v2 if current else None))
        coordinator = Coordinator(root, generate, config, capabilities(config), job_adapter=jobs)
        while not stopped:
            if stop_file.exists():
                stop_request = read_json(stop_file)
                if stop_request == {"schema": "helix-orca-v1-stop/v1", "run_id": run_id}:
                    break
            try:
                tick(coordinator, args.storage, transport)
                atomic_json(root / "health.json", dict(schema="helix-orca-v1-health/v1", ok=True,
                    checked_at=int(time.time()), actions_enabled=jobs is not None, test_worker_required=False, run_id=run_id, pid=os.getpid()))
            except Exception as exc:
                # Keep original jobs/journal; retry transport without changing request identity.
                atomic_json(root / "health.json", dict(schema="helix-orca-v1-health/v1", ok=False,
                    checked_at=int(time.time()), message=type(exc).__name__ + ": " + str(exc)[:800], actions_enabled=jobs is not None, run_id=run_id, pid=os.getpid()))
                if args.once:
                    raise
            if args.once:
                break
            for _ in range(20):
                if stopped:
                    break
                time.sleep(0.1)
        atomic_json(root / "health.json", dict(schema="helix-orca-v1-health/v1", ok=True, stopped=True,
            checked_at=int(time.time()), actions_enabled=jobs is not None, test_worker_required=False, run_id=run_id, pid=os.getpid()))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
