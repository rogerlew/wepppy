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


@pytest.mark.parametrize("scenario", ["ownership", "fifo", "processes", "timeout", "outage", "clocks", "killed", "corruption", "heartbeat"])
def test_real_redis_boundary(scenario):
    result = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "scenario", scenario],
        env=_isolated_environment(), capture_output=True, text=True, timeout=150,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    evidence = json.loads(result.stdout.strip().splitlines()[-1])
    assert evidence["passed"] is True


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
    config = _config(limit=1 if name in {"fifo", "ownership", "timeout", "killed", "corruption", "heartbeat"} else 2)
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
        elif name == "timeout":
            blocker = controller.acquire(request_kind="blocker")
            permits.append(blocker)
            with pytest.raises(GridMetAdmissionTimeout):
                controller.acquire(request_kind="timeout", deadline=time.monotonic() + 0.1)
            assert controller.snapshot().queued == 0
            assert controller.snapshot().active == 1
            blocker.release()
        elif name == "outage":
            import redis
            from redis.backoff import NoBackoff
            from redis.retry import Retry
            controller._redis = redis.Redis(host="127.0.0.1", port=1, socket_connect_timeout=0.1,
                                             socket_timeout=0.1, retry=Retry(NoBackoff(), 0))
            controller._pid = os.getpid()
            started = time.monotonic()
            with pytest.raises(GridMetAdmissionUnavailable) as caught:
                controller.acquire(request_kind="outage")
            assert time.monotonic() - started < 2
            assert "127.0.0.1" not in str(caught.value)
            controller._redis = None
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
