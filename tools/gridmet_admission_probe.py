#!/usr/bin/env python3
"""Bounded GridMET acceptance clients; stdout is sanitized JSON lines.

Use the same unique --key and timing options for every participating container.
`worker` emits its PID before acquiring, allowing an operator to SIGKILL that
exact process for waiter/holder expiry exercises. `observe` never renews owners.
No mode deletes Redis keys: normal contexts release only their own permits and
killed owners expire according to the admission contract.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import time


CANONICAL_KEY = "wepppy:gridmet:admission:v1"
ACCEPTANCE_PREFIX = "wepppy:gridmet:admission:acceptance:"
REPO_ROOT = Path(__file__).resolve().parents[1]


class ProbeInterrupted(RuntimeError):
    """A graceful stop which still unwinds owned permit contexts."""


def validate_key(key: str, *, readonly: bool = False) -> str:
    if not re.fullmatch(r"[A-Za-z0-9:_.-]{1,160}", key):
        raise ValueError("invalid namespace identifier")
    if readonly:
        return key
    operational = os.environ.get("GRIDMET_REDIS_ADMISSION_KEY", CANONICAL_KEY).strip()
    if key in {CANONICAL_KEY, operational}:
        raise ValueError("operational namespaces permit read-only inspection only")
    if not key.startswith(ACCEPTANCE_PREFIX) or len(key.removeprefix(ACCEPTANCE_PREFIX)) < 12:
        raise ValueError("use the acceptance prefix and a unique candidate/timestamp suffix")
    return key


def bounded_number(text: str) -> float:
    value = float(text)
    if not math.isfinite(value) or not 0 < value <= 600:
        raise argparse.ArgumentTypeError("value must be finite and between 0 and 600 seconds")
    return value


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("mode", choices=("worker", "observe", "run", "public", "inspect", "public-request", "summarize"))
    result.add_argument("--key", required=True)
    result.add_argument("--limit", type=int, default=2)
    result.add_argument("--wait-seconds", type=bounded_number, default=120.0)
    result.add_argument("--lease-seconds", type=bounded_number, default=30.0)
    result.add_argument("--queue-ttl-seconds", type=bounded_number, default=9.0)
    result.add_argument("--poll-seconds", type=bounded_number, default=0.05)
    result.add_argument("--hold-seconds", type=bounded_number, default=3.0)
    result.add_argument("--duration-seconds", type=bounded_number, default=30.0)
    result.add_argument("--timeout-seconds", type=bounded_number, default=180.0)
    result.add_argument("--contenders", type=int, default=6)
    result.add_argument("--id", "--worker-id", default="worker")
    result.add_argument("--input", action="append", type=Path, default=[])
    result.add_argument("--require-peak", action="store_true")
    result.add_argument("--require-queued", action="store_true")
    result.add_argument("--minimum-containers", type=int, default=1)
    return result


def emit(event: dict) -> None:
    print(json.dumps(event, sort_keys=True), flush=True)


def identity() -> dict:
    return {"container": socket.gethostname(), "pid": os.getpid()}


def configuration(args):
    from wepppy.climates.gridmet.admission import GridMetAdmissionConfig

    return GridMetAdmissionConfig(
        key=args.key, limit=args.limit,
        wait_timeout_seconds=args.wait_seconds,
        lease_seconds=args.lease_seconds,
        queue_ttl_seconds=args.queue_ttl_seconds,
        poll_interval_seconds=args.poll_seconds,
    )


def controller(args):
    from wepppy.climates.gridmet.admission import GridMetAdmissionController

    return GridMetAdmissionController(configuration(args))


def observe_once(client) -> dict:
    # Snapshot prunes expired debris only; it never renews or changes live owners.
    snapshot = client.snapshot()
    return {
        "active": snapshot.active, "queued": snapshot.queued,
        "limit": snapshot.limit, "server_time": snapshot.server_time_seconds,
    }


def observe(args) -> dict:
    client = controller(args)
    deadline = time.monotonic() + args.duration_seconds
    peak = 0
    queued_seen = False
    count = 0
    violations = 0
    while True:
        sample = observe_once(client)
        peak = max(peak, sample["active"])
        queued_seen |= sample["queued"] > 0
        violations += sample["active"] > sample["limit"]
        count += 1
        emit({"event": "sample", "key": args.key, **identity(), **sample})
        if args.mode == "inspect" or time.monotonic() >= deadline:
            break
        time.sleep(min(args.poll_seconds, max(0, deadline - time.monotonic())))
    return {
        "event": "summary", "mode": args.mode, **identity(), "key": args.key,
        "configured_limit": args.limit, "observed_peak": peak,
        "queued_seen": queued_seen, "limit_violations": violations,
        "samples": count, "cleanup_counts": sample,
        "pass": (violations == 0 and (not args.require_peak or peak == args.limit)
                 and (not args.require_queued or queued_seen)),
    }


def worker(args) -> dict:
    client = controller(args)
    emit({"event": "started", "key": args.key, "id": args.id, **identity()})
    with client.acquire(request_kind="acceptance probe") as permit:
        emit({
            "event": "acquired", "key": args.key, "id": args.id, **identity(),
            "sequence": permit.snapshot.sequence,
            "admitted_at_server_seconds": permit.snapshot.server_time_seconds,
            **observe_once(client),
        })
        deadline = time.monotonic() + args.hold_seconds
        while time.monotonic() < deadline:
            permit.check()
            time.sleep(min(0.1, max(0, deadline - time.monotonic())))
    return {"event": "released", "key": args.key, "id": args.id, **identity(), "pass": True}


def child_command(args, mode: str, *, contender: int = 0) -> list[str]:
    return [
        sys.executable, str(Path(__file__).resolve()), mode,
        "--key", args.key, "--limit", str(args.limit),
        "--wait-seconds", str(args.wait_seconds),
        "--lease-seconds", str(args.lease_seconds),
        "--queue-ttl-seconds", str(args.queue_ttl_seconds),
        "--poll-seconds", str(args.poll_seconds),
        "--hold-seconds", str(args.hold_seconds),
        "--timeout-seconds", str(args.timeout_seconds),
        "--id", str(contender),
    ]


def stop_children(children) -> None:
    for child in children:
        if child.poll() is None:
            child.terminate()
    deadline = time.monotonic() + 5
    for child in children:
        try:
            child.wait(timeout=max(0.01, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=5)


def summarize(events: list[dict], samples: list[dict], expected: int, limit: int) -> dict:
    acquired = [event for event in events if event["event"] == "acquired"]
    ordered = sorted(acquired, key=lambda event: (event["admitted_at_server_seconds"], event["sequence"]))
    sequences = [event["sequence"] for event in ordered]
    peak = max((sample["active"] for sample in samples), default=0)
    queued_seen = any(sample["queued"] for sample in samples)
    violations = sum(sample["active"] > limit for sample in samples)
    final = samples[-1] if samples else {"active": -1, "queued": -1}
    released = sum(event["event"] == "released" for event in events)
    acquired_ids = sorted((event["container"], event["pid"], event["id"]) for event in acquired)
    released_ids = sorted((event["container"], event["pid"], event["id"])
                          for event in events if event["event"] == "released")
    owners_match = acquired_ids == released_ids and len(set(acquired_ids)) == len(acquired_ids)
    fifo = sequences == sorted(sequences) and len(set(sequences)) == len(sequences)
    return {
        "event": "summary", "configured_limit": limit,
        "observed_peak": peak, "queued_seen": queued_seen,
        "limit_violations": violations, "acquisition_order": sequences,
        "fifo": fifo, "completed": released, "expected": expected,
        "containers": sorted({event["container"] for event in acquired}),
        "owners_match": owners_match,
        "cleanup_counts": final,
        "pass": (len(acquired) == released == expected and owners_match and fifo and queued_seen
                 and peak == limit and violations == 0
                 and final["active"] == final["queued"] == 0),
    }


def summarize_files(args) -> dict:
    if not args.input:
        raise ValueError("summarize requires --input files")
    events = []
    samples = []
    for path in args.input:
        if path.stat().st_size > 16 * 1024 * 1024:
            raise ValueError("probe input exceeds 16 MiB")
        for line in path.read_text().splitlines():
            event = json.loads(line)
            if event.get("event") in {"sample", "acquired", "released"} and event.get("key") != args.key:
                raise ValueError("evidence namespace differs from requested acceptance namespace")
            if event.get("event") == "sample":
                samples.append(event)
            elif event.get("event") in {"acquired", "released", "error"}:
                events.append(event)
    samples.sort(key=lambda sample: sample["server_time"])
    result = summarize(events, samples, args.contenders, args.limit)
    result.update(mode="summarize", key=args.key)
    result["pass"] &= not any(event["event"] == "error" for event in events)
    result["pass"] &= len(result["containers"]) >= args.minimum_containers
    return result


def run(args) -> dict:
    client = controller(args)
    initial = observe_once(client)
    if initial["active"] or initial["queued"]:
        raise ValueError("acceptance namespace already has live owners")
    children = []
    events = []
    samples = []
    timed_out = False
    try:
        for contender in range(args.contenders):
            children.append(subprocess.Popen(child_command(args, "worker", contender=contender),
                                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True))
        deadline = time.monotonic() + args.timeout_seconds
        while any(child.poll() is None for child in children):
            samples.append(observe_once(client))
            if time.monotonic() >= deadline:
                timed_out = True
                break
            time.sleep(args.poll_seconds)
    finally:
        stop_children(children)
    for child in children:
        output, _ = child.communicate(timeout=5)
        events.extend(json.loads(line) for line in output.splitlines())
    samples.append(observe_once(client))
    for event in events:
        emit(event)
    result = summarize(events, samples, args.contenders, args.limit)
    result.update(mode="run", key=args.key, timed_out=timed_out, **identity())
    result["pass"] &= not timed_out and all(child.returncode == 0 for child in children)
    return result


def public_request(args) -> dict:
    from wepppy.climates.gridmet.gridmet_singlelocation_client import retrieve_historical_precip

    signal.signal(signal.SIGALRM, interrupt)
    signal.setitimer(signal.ITIMER_REAL, args.timeout_seconds)
    try:
        data = retrieve_historical_precip(-116.2, 43.7, 2020, 2020, admission=configuration(args))
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    valid = len(data) == 366 and "pr(mm/day)" in data and bool(data["pr(mm/day)"].notna().all())
    return {"event": "public_result", **identity(), "rows": len(data), "year": 2020,
            "valid_public_result": valid, "pass": valid}


def public(args) -> dict:
    client = controller(args)
    initial = observe_once(client)
    if initial["active"] or initial["queued"]:
        raise ValueError("acceptance namespace already has live owners")
    child = subprocess.Popen(child_command(args, "public-request"), stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, text=True)
    timed_out = False
    try:
        output, _ = child.communicate(timeout=args.timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        stop_children([child])
        output, _ = child.communicate(timeout=5)
    finally:
        stop_children([child])
    events = [json.loads(line) for line in output.splitlines()]
    for event in events:
        emit(event)
    final = observe_once(client)
    return {"event": "summary", "mode": "public", **identity(), "key": args.key,
            "timed_out": timed_out, "cleanup_counts": final,
            "external_observer_required": True,
            "pass": (not timed_out and child.returncode == 0 and final["active"] == final["queued"] == 0
                     and any(event.get("valid_public_result") for event in events))}


def interrupt(_signal, _frame) -> None:
    raise ProbeInterrupted("probe interrupted")


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        validate_key(args.key, readonly=args.mode in {"inspect", "observe", "summarize"})
        if not 1 <= args.limit <= 16 or not 1 <= args.contenders <= 16:
            raise ValueError("limit and contender count must be between 1 and 16")
        if not 1 <= args.minimum_containers <= 16:
            raise ValueError("minimum container count must be between 1 and 16")
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", args.id):
            raise ValueError("invalid contender identifier")
        if args.poll_seconds < 0.01:
            raise ValueError("probe sampling interval must be at least 0.01 seconds")
        if args.mode in {"public", "public-request"} and args.lease_seconds < 90:
            raise ValueError("public request requires --lease-seconds at least 90")
        signal.signal(signal.SIGTERM, interrupt)
        action = {"worker": worker, "run": run, "observe": observe, "inspect": observe,
                  "public": public, "public-request": public_request,
                  "summarize": summarize_files}[args.mode]
        result = action(args)
    except Exception as exc:
        # CLI trust boundary: exception text may include URLs or credentials.
        emit({"event": "error", "mode": args.mode, "error_type": type(exc).__name__, "pass": False})
        return 1
    emit(result)
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.path.insert(0, str(REPO_ROOT))
    raise SystemExit(main())
