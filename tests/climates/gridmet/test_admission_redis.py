"""Real Lua boundary tests in fresh interpreters, outside the global Redis stub.

Set GRIDMET_ADMISSION_TEST_REDIS_HOST (and optional _PORT) to a disposable,
unauthenticated Redis service. Every scenario uses one unique namespace. No
scenario flushes a database or deletes keys belonging to another scenario.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.slow]


def _isolated_environment():
    host = os.environ.get("GRIDMET_ADMISSION_TEST_REDIS_HOST")
    if not host:
        pytest.skip("Set GRIDMET_ADMISSION_TEST_REDIS_HOST to an isolated real Redis service")
    env = os.environ.copy()
    for key in ("REDIS_URL", "RQ_REDIS_URL", "SESSION_REDIS_URL", "REDIS_PASSWORD", "REDIS_PASSWORD_FILE"):
        env.pop(key, None)
    env.update(REDIS_HOST=host, REDIS_PORT=env.get("GRIDMET_ADMISSION_TEST_REDIS_PORT", "6379"))
    return env


@pytest.mark.parametrize("scenario", ["ownership", "fifo", "processes", "persistent", "outage", "lost-reply", "clocks", "killed", "corruption", "heartbeat"])
def test_real_redis_boundary(scenario):
    result = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "scenario", scenario],
        env=_isolated_environment(), capture_output=True, text=True, timeout=150,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    evidence = json.loads(result.stdout.strip().splitlines()[-1])
    assert evidence["passed"] is True


@pytest.mark.parametrize("operation", ["enqueue", "poll", "renew", "release"])
def test_real_socket_timeout_recovery(operation):
    env = _isolated_environment()
    if env.get("GRIDMET_ADMISSION_TEST_ALLOW_PAUSE") != "true":
        pytest.skip("Pause tests require explicit opt-in on a dedicated disposable Redis")
    result = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "scenario", "delay-" + operation],
        env=env, capture_output=True, text=True, timeout=45,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "TimeoutError" in result.stderr
    assert json.loads(result.stdout.strip().splitlines()[-1])["passed"]


def _config(key=None, limit=2):
    from wepppy.climates.gridmet.admission import GridMetAdmissionConfig
    return GridMetAdmissionConfig(
        key=key or "wepppy:gridmet:test:" + uuid.uuid4().hex, limit=limit,
        lease_seconds=22, queue_ttl_seconds=7, poll_interval_seconds=0.01,
        wait_timeout_seconds=50,
    )


def _wait(predicate, timeout=20):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(0.01)
    raise AssertionError("bounded state observation timed out")


def _spawn(config, mode="normal", label="worker", hold=0.3):
    return subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "worker", config.key,
         str(config.limit), mode, label, str(hold)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=os.environ.copy(),
    )


def _finish(process, timeout=5):
    stdout, stderr = process.communicate(timeout=timeout)
    assert process.returncode == 0, stdout + stderr
    return json.loads(stdout.strip().splitlines()[-1])


def _scenario(name):
    from dataclasses import replace
    from wepppy.climates.gridmet.admission import (
        GridMetAdmissionController, GridMetAdmissionConflict, GridMetAdmissionLostLease,
        GridMetAdmissionTimeout, GridMetAdmissionUnavailable,
    )
    config = _config(limit=1 if name in {"fifo", "ownership", "persistent", "killed", "corruption", "heartbeat"} else 2)
    controller = GridMetAdmissionController(config)
    children = []
    permits = []
    evidence = {"scenario": name, "passed": False}
    try:
        assert controller.snapshot().active == 0
        if name == "ownership":
            permit = controller.acquire(request_kind="owner")
            permits.append(permit)
            for op in ("renew", "release", "cancel"):
                with pytest.raises(GridMetAdmissionLostLease):
                    controller._transition(op, permit.ticket_id, "foreign")
                assert controller.snapshot().active == 1
            wrong = GridMetAdmissionController(replace(config, limit=3))
            with pytest.raises(GridMetAdmissionConflict):
                wrong.acquire(request_kind="conflict")
            assert wrong.snapshot().limit == 1
            controller._transition("enqueue", "waiting", "owned")
            assert controller.snapshot("waiting").position == 0
            with pytest.raises(GridMetAdmissionLostLease):
                controller._transition("cancel", "waiting", "foreign")
            controller._transition("cancel", "waiting", "owned")
            permit.release()
            # An idle namespace can adopt a new policy atomically.
            with wrong.acquire(request_kind="new policy"):
                assert wrong.snapshot().limit == 3
            # Original lease expiry cannot be resurrected by renew.
            expired = controller.acquire(request_kind="expired")
            permits.append(expired)
            controller._connection().zadd(controller._keys[4], {expired.ticket_id: 1})
            with pytest.raises(GridMetAdmissionLostLease):
                expired.renew()
            expired.release()
        elif name == "fifo":
            blocker = controller.acquire(request_kind="blocker")
            permits.append(blocker)
            for index in range(4):
                children.append(_spawn(config, label=str(index), hold=0.15))
                _wait(lambda: controller.snapshot().queued == index + 1)
            blocker.release()
            records = [_finish(child) for child in children]
            assert [record["label"] for record in sorted(records, key=lambda r: r["granted"])] == ["0", "1", "2", "3"]
            assert [record["sequence"] for record in records] == sorted(record["sequence"] for record in records)
            evidence["order"] = [record["label"] for record in records]
        elif name == "processes":
            permits.extend(controller.acquire(request_kind="blocker") for _ in range(2))
            for index in range(6):
                children.append(_spawn(config, label=str(index)))
            _wait(lambda: controller.snapshot().queued == 6)
            for permit in permits:
                permit.release()
            peak, queued_seen = 0, False
            while any(child.poll() is None for child in children):
                snap = controller.snapshot()
                peak = max(peak, snap.active)
                queued_seen |= snap.queued > 0
                assert snap.active <= 2
                time.sleep(0.005)
            records = [_finish(child) for child in children]
            assert peak == 2 and queued_seen
            assert len({record["pid"] for record in records}) == 6
            evidence.update(peak=peak, queued_seen=queued_seen)
        elif name == "persistent":
            import threading
            # Legacy budget is deliberately shorter than the live queue wait.
            config = replace(config, wait_timeout_seconds=0.05)
            controller = GridMetAdmissionController(config)
            blocker = controller.acquire(request_kind="blocker")
            permits.append(blocker)
            result = []

            def waiter():
                with controller.acquire(request_kind="persistent"):
                    result.append("admitted")

            thread = threading.Thread(target=waiter, daemon=True)
            thread.start()
            _wait(lambda: controller.snapshot().queued == 1)
            time.sleep(0.2)
            assert thread.is_alive() and not result
            assert controller.snapshot().queued == 1
            blocker.release()
            thread.join(5)
            assert result == ["admitted"]
        elif name == "outage":
            import redis
            connection = controller._connection()
            original_eval = connection.eval
            calls = []

            def unavailable_then_recover(*args):
                calls.append(args[8])
                if len(calls) == 1:
                    raise redis.exceptions.ConnectionError("private connection URL")
                return original_eval(*args)

            connection.eval = unavailable_then_recover
            with controller.acquire(request_kind="outage recovery"):
                assert controller.snapshot().active == 1
            assert calls[:2] == ["enqueue", "enqueue"]
            connection.eval = original_eval
        elif name == "lost-reply":
            import redis
            connection = controller._connection()
            original_eval = connection.eval
            lost = set()

            def lose_committed_reply(*args):
                result = original_eval(*args)
                operation = args[8]
                if operation in {"enqueue", "poll", "renew", "release"} and operation not in lost:
                    lost.add(operation)
                    raise redis.exceptions.TimeoutError("private Redis URL")
                return result

            connection.eval = lose_committed_reply
            with controller.acquire(request_kind="lost reply") as permit:
                assert controller.snapshot().active == 1
                permit.renew()
                permit.check()
            holders = [controller.acquire(request_kind="holder") for _ in range(2)]
            permits.extend(holders)
            first, _ = controller._transition("enqueue", "queued", "queued-owner")
            replay, _ = controller._transition("enqueue", "queued", "queued-owner")
            assert first.sequence == replay.sequence and replay.position == 0
            with pytest.raises(GridMetAdmissionLostLease):
                controller._transition("enqueue", "queued", "foreign")
            holders[0].release()
            admitted, _ = controller._retry_transition("poll", "queued", "queued-owner")
            assert admitted.state == "active" and controller.snapshot().active == 2
            controller._transition("release", "queued", "queued-owner")
            holders[1].release()
            assert lost == {"enqueue", "poll", "renew", "release"}
            connection.eval = original_eval
        elif name.startswith("delay-"):
            # Only explicitly opted-in disposable Redis may be paused. This
            # exercises actual redis-py socket timeouts, not fabricated errors.
            assert os.environ.get("GRIDMET_ADMISSION_TEST_ALLOW_PAUSE") == "true"
            import threading
            from datetime import date
            from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
            from wepppy.climates.gridmet.acquisition import request_single_location_json

            operation = name.removeprefix("delay-")
            config = replace(config, lease_seconds=300)
            controller = GridMetAdmissionController(config)
            connection = controller._connection()
            original_eval = connection.eval
            paused = []

            def delay_command(*args):
                if args[8] == operation and not paused:
                    paused.append(operation)
                    connection.execute_command("CLIENT", "PAUSE", 2400, "ALL")
                return original_eval(*args)

            connection.eval = delay_command
            if operation == "poll":
                # Enqueue behind a holder, free capacity, then lose the poll
                # response while it transitions the existing ticket to active.
                holder = controller.acquire(request_kind="poll holder")
                second = controller.acquire(request_kind="second holder")
                permits.extend([holder, second])
                controller._transition("enqueue", "waiter", "owner")
                holder.release()
                snapshot, _ = controller._retry_transition("poll", "waiter", "owner")
                assert snapshot.state == "active"
                controller._transition("release", "waiter", "owner")
                second.release()
            elif operation == "release":
                # Exercise real requests HTTP, response close, permit release,
                # JSON parsing and validation through the production client.
                payload = {"data": [{"yyyy-mm-dd": ["2025-01-01"], "pr(mm)": [1.0]}]}

                class Handler(BaseHTTPRequestHandler):
                    def do_GET(self):
                        body = json.dumps(payload).encode()
                        self.send_response(200)
                        self.send_header("Content-Length", str(len(body)))
                        self.end_headers()
                        self.wfile.write(body)

                    def log_message(self, *_args):
                        pass  # Test HTTP fixture has no request logging.

                server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                from wepppy.climates.gridmet import acquisition
                original_prepare = acquisition._prepare_admission
                acquisition._prepare_admission = lambda *_args: controller
                try:
                    data = request_single_location_json(
                        f"http://127.0.0.1:{server.server_port}/gridmet",
                        required_series=("pr(mm)",), start_date=date(2025, 1, 1),
                        end_date=date(2025, 1, 1), admission=config,
                    )
                    assert data == payload["data"][0]
                    evidence["validated_http"] = True
                finally:
                    acquisition._prepare_admission = original_prepare
                    server.shutdown()
                    server.server_close()
                    thread.join(2)
            else:
                with controller.acquire(request_kind="socket delay") as permit:
                    if operation == "renew":
                        permit.renew()
                    permit.check()
                    assert controller.snapshot().active == 1
            assert paused == [operation]
            connection.eval = original_eval
            evidence["pause_ms"] = 2400
        elif name == "clocks":
            real_time = time.time
            time.time = lambda: real_time() + 10**9
            with controller.acquire(request_kind="clock disagreement") as permit:
                now = controller.snapshot(permit.ticket_id).server_time_seconds
                assert abs(now - real_time()) < 5
                permit.renew()
                permit.check()
        elif name == "corruption":
            holder = controller.acquire(request_kind="holder")
            permits.append(holder)
            controller._transition("enqueue", "waiting", "owned")
            redis = controller._connection()
            keys = controller._keys

            def unchanged_on_failure():
                before = [redis.dump(key) for key in keys]
                with pytest.raises(GridMetAdmissionUnavailable):
                    controller._transition("enqueue", "intruder", "new-token")
                assert [redis.dump(key) for key in keys] == before

            sequence = redis.get(keys[1])
            redis.delete(keys[1])
            unchanged_on_failure()
            redis.set(keys[1], "1.0", px=45000)
            unchanged_on_failure()
            redis.set(keys[1], sequence, px=45000)
            expiry = redis.zscore(keys[3], "waiting")
            redis.zrem(keys[3], "waiting")
            redis.zadd(keys[3], {"foreign": expiry})
            unchanged_on_failure()
            redis.zrem(keys[3], "foreign")
            # An expired liveness entry must not prune a live holder's ownership.
            redis.zadd(keys[3], {holder.ticket_id: 1})
            unchanged_on_failure()
            redis.zrem(keys[3], holder.ticket_id)
            redis.zadd(keys[3], {"waiting": expiry})
            owners = redis.hgetall(keys[5])
            redis.delete(keys[5])
            redis.set(keys[5], "wrong-type", px=45000)
            unchanged_on_failure()
            redis.delete(keys[5])
            redis.hset(keys[5], mapping=owners)
            controller._transition("enqueue", "waiting-two", "owned-two")
            original_rank = redis.zscore(keys[2], "waiting-two")
            redis.zadd(keys[2], {"waiting-two": redis.zscore(keys[2], "waiting")})
            unchanged_on_failure()
            redis.zadd(keys[2], {"waiting-two": original_rank})
            redis.zadd(keys[4], {holder.ticket_id: float("inf")})
            unchanged_on_failure()
            redis.zadd(keys[4], {holder.ticket_id: time.time() * 1000 + 22000})
            controller._transition("cancel", "waiting-two", "owned-two")
            controller._transition("cancel", "waiting", "owned")
            holder.release()
        elif name == "heartbeat":
            holder = controller.acquire(request_kind="heartbeat holder")
            permits.append(holder)
            initial_expiry = controller._connection().zscore(controller._keys[4], holder.ticket_id)
            child = _spawn(config, label="live waiter")
            children.append(child)
            _wait(lambda: controller.snapshot().queued == 1)
            waiting_id = controller._connection().zrange(controller._keys[2], 0, 0)[0]
            initial_sequence = controller._connection().zscore(controller._keys[2], waiting_id)
            time.sleep(8)
            assert controller.snapshot().queued == 1
            assert controller._connection().zscore(controller._keys[2], waiting_id) == initial_sequence
            assert controller._connection().zscore(controller._keys[4], holder.ticket_id) > initial_expiry
            holder.check()
            holder.release()
            _finish(child)
        elif name == "killed":
            holder = _spawn(config, mode="no-renew", label="holder", hold=60)
            children.append(holder)
            _wait(lambda: controller.snapshot().active == 1)
            waiter = _spawn(config, mode="normal", label="waiter", hold=60)
            children.append(waiter)
            _wait(lambda: controller.snapshot().queued == 1)
            started = time.monotonic()
            waiter.kill()
            holder.kill()
            waiter.communicate(timeout=3)
            holder.communicate(timeout=3)
            _wait(lambda: controller.snapshot().queued == 0, timeout=9)
            _wait(lambda: controller.snapshot().active == 0, timeout=24)
            assert time.monotonic() - started < 25
            with controller.acquire(request_kind="reclaimed"):
                assert controller.snapshot().active == 1
            evidence["reclaimed_seconds"] = round(time.monotonic() - started, 2)
        for permit in permits:
            permit.release()
        final = controller.snapshot()
        assert final.queued == final.active == 0
        evidence.update(passed=True, queued=final.queued, active=final.active)
        print(json.dumps(evidence))
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
                child.communicate(timeout=3)
        for permit in permits:
            permit.release()


def _worker():
    from wepppy.climates.gridmet.admission import GridMetAdmissionController
    config = _config(key=sys.argv[2], limit=int(sys.argv[3]))
    mode, label, hold = sys.argv[4], sys.argv[5], float(sys.argv[6])
    controller = GridMetAdmissionController(config)
    with controller.acquire(request_kind="test worker") as permit:
        if mode == "no-renew":
            permit._stop.set()
        record = {"label": label, "pid": os.getpid(), "sequence": permit.snapshot.sequence,
                  "granted": permit.snapshot.server_time_seconds}
        time.sleep(hold)
    print(json.dumps(record), flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "worker":
        _worker()
    else:
        _scenario(sys.argv[2])
