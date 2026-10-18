#!/usr/bin/env python3
"""V1 local coordinator: direct events/local artifacts, no Codex test worker.

No action-enabled printer transport exists in this review candidate. Default
transport is offline. --moonraker-events requires explicit existing LAN consent.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from integration.v1_contract import ContractError
from integration.v1_runtime import Coordinator, InstanceLock, atomic_json, read_json
from integration.v1_transport import DirectoryEvents, MoonrakerEvents


def tick(coordinator, storage, transport):
    context = storage / "context.json"
    if context.exists():
        offer = coordinator.offer(read_json(context))
        transport.send("helix_orca_v1.context.v1", offer)
    native = transport.read()
    if coordinator.state.get("receipt") and native.get("receipt") == coordinator.state["receipt"]:
        coordinator.state["native_acknowledged"] = True
        coordinator._persist()
    offered = coordinator.state["offer"]
    if isinstance(native.get("request"), dict) and offered and native["request"].get("request_id") == offered["request_id"]:
        coordinator.request(native["request"])
    retained = coordinator.state["request"]
    if isinstance(native.get("intent"), dict) and retained and native["intent"].get("request_id") == retained["request_id"]:
        coordinator.intent(native["intent"])
    coordinator.poll_job()
    if native.get("result") is not None:
        result = coordinator.result(native["result"])
        atomic_json(storage / "inbox.json", dict(result=result, request=coordinator.state["request"],
            prepared=coordinator.state["prepared"], completion=coordinator.state["completion"]))
    receipt = storage / "receipt.json"
    if coordinator.state["result"] and receipt.exists():
        ack = coordinator.acknowledge(read_json(receipt))
        transport.send("helix_orca_v1.ack.v1", ack)
    status = coordinator.status()
    if status:
        atomic_json(storage / "status.json", status)
        context = coordinator.state["context"]
        atomic_json(storage / "view.json", dict(status=status, result=coordinator.state["result"],
            original={role: context[role]["saved"]["name"] for role in ("printer", "process", "filament")}))
        transport.send("helix_orca_v1.status.v1", status)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storage", type=Path, required=True, help="Exact originating plugin's v1 storage directory")
    parser.add_argument("--config", type=Path, required=True, help="Private explicit generator configuration")
    parser.add_argument("--state", type=Path, help="Dedicated runtime journal; defaults below plugin v1 storage")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--offline-channel", type=Path)
    parser.add_argument("--moonraker-events", action="store_true", help="No physical deployment or Start; V1 events only")
    args = parser.parse_args()
    from integration.v1_generation import generate, capabilities
    config = read_json(args.config)
    root = args.state or args.storage / "runtime"
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
    with InstanceLock(root / "runtime.lock"):
        coordinator = Coordinator(root, generate, config, capabilities(config))
        while not stopped:
            try:
                tick(coordinator, args.storage, transport)
                atomic_json(root / "health.json", dict(schema="helix-orca-v1-health/v1", ok=True,
                    checked_at=int(time.time()), actions_enabled=False, test_worker_required=False))
            except Exception as exc:
                # Keep original jobs/journal; retry transport without changing request identity.
                atomic_json(root / "health.json", dict(schema="helix-orca-v1-health/v1", ok=False,
                    checked_at=int(time.time()), message=type(exc).__name__ + ": " + str(exc)[:800], actions_enabled=False))
                if args.once:
                    raise
            if args.once:
                break
            for _ in range(20):
                if stopped:
                    break
                time.sleep(0.1)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
