"""Replay genuine 1.16.2 records on an exclusively owned Redis database.

Set RQ212_HISTORICAL_REDIS_SOCKET to an isolated Unix socket. DB4 must contain
only rq212-historical-disposable=owned before running. No live Redis is used.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest
import redis
from rq import Queue
from rq.job import Job
from rq.scheduler import RQScheduler

pytestmark = [pytest.mark.integration, pytest.mark.slow]
FIXTURES = Path(__file__).parents[1] / "data" / "rq_1_16_2"
MARKER = b"rq212-historical-disposable"


@pytest.fixture
def historical_connection(monkeypatch):
    socket = os.environ.get("RQ212_HISTORICAL_REDIS_SOCKET")
    if not socket:
        pytest.skip("requires dedicated marked RQ212 historical Redis socket")
    monkeypatch.setattr(redis, "Redis", redis.StrictRedis)
    connection = redis.Redis(unix_socket_path=socket, db=4)
    assert connection.get(MARKER) == b"owned"
    assert set(connection.scan_iter()) == {MARKER}, "DB4 contains unrelated state"
    try:
        yield connection
    finally:
        # This fixture admitted only an empty, explicitly marked database. Delete
        # its restored/generated records, never a live application database.
        keys = [key for key in connection.scan_iter() if key != MARKER]
        if keys:
            connection.delete(*keys)
        connection.close()


def restore(connection, name):
    snapshot = json.loads((FIXTURES / name).read_text())
    decode = base64.b64decode
    for item in snapshot["keys"]:
        key = decode(item["key"])
        assert not connection.exists(key)
        kind, value = item["type"], item["value"]
        if kind == "string":
            connection.set(key, decode(value))
        elif kind == "hash":
            connection.hset(key, mapping={decode(k): decode(v) for k, v in value.items()})
        elif kind == "list":
            connection.rpush(key, *(decode(v) for v in value))
        elif kind == "set":
            connection.sadd(key, *(decode(v) for v in value))
        elif kind == "zset":
            connection.zadd(key, {decode(k): v for k, v in value.items()})
        elif kind == "stream":
            for identifier, fields in value:
                connection.xadd(key, {decode(k): decode(v) for k, v in fields.items()}, id=decode(identifier))
        else:
            raise ValueError(f"Unsupported fixture key type: {kind}")
        if item["pttl"] > 0:
            connection.pexpire(key, item["pttl"])
    return snapshot


def work(connection, queue_name):
    socket = connection.connection_pool.connection_kwargs["path"]
    code = (
        "import redis; from rq import Queue, Worker; "
        f"c=redis.Redis(unix_socket_path={socket!r},db=4); "
        f"Worker([Queue({queue_name!r},connection=c)],connection=c).work(burst=True)"
    )
    process = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=30,
    )
    assert process.returncode == 0, process.stdout + process.stderr


def test_read_all_six_historical_states_and_retained_results(historical_connection):
    connection = historical_connection
    snapshot = restore(connection, "running.json")
    jobs = {state: Job.fetch(identifier, connection=connection) for state, identifier in snapshot["jobs"].items()}
    assert {state: job.get_status() for state, job in jobs.items()} == {state: state for state in jobs}
    assert jobs["finished"].latest_result().return_value == 9.0
    assert "ValueError: math domain error" in jobs["failed"].latest_result().exc_string
    # Old running entries are plain job IDs; they cannot represent an RQ2
    # execution identity. Readability alone is not a supported running handover.
    registry = Queue(snapshot["queue"], connection=connection).started_job_registry
    assert connection.zrange(registry.key, 0, -1) == [jobs["started"].id.encode()]
    assert jobs["started"].get_status() == "started"


def test_drained_legacy_queue_dependencies_and_schedule_execute(historical_connection):
    connection = historical_connection
    snapshot = restore(connection, "drained.json")
    queue = Queue(snapshot["queue"], connection=connection)
    jobs = {state: Job.fetch(identifier, connection=connection) for state, identifier in snapshot["jobs"].items()}
    assert connection.zcard(queue.started_job_registry.key) == 0
    assert jobs["stopped"].get_status() == "stopped"
    assert jobs["deferred"].get_status() == "deferred"
    assert connection.smembers(jobs["deferred"].dependencies_key) == {jobs["queued"].id.encode()}
    assert jobs["scheduled"].get_status() == "scheduled"
    work(connection, queue.name)
    for state, expected in (("queued", 4.0), ("deferred", 5.0)):
        assert jobs[state].get_status() == "finished"
        assert jobs[state].latest_result().return_value == expected
    assert jobs["scheduled"].get_status() == "scheduled"
    # Advance only the fixture's due score, simulating the historical schedule
    # reaching its due time. Exercise the actual scheduler and forked worker.
    connection.zadd(queue.scheduled_job_registry.key, {jobs["scheduled"].id: time.time() - 1})
    scheduler = RQScheduler([queue.name], connection=connection)
    scheduler.acquire_locks()
    try:
        scheduler.enqueue_scheduled_jobs()
    finally:
        scheduler.release_locks()
    assert jobs["scheduled"].get_status() == "queued"
    work(connection, queue.name)
    assert jobs["scheduled"].get_status() == "finished"
    assert jobs["scheduled"].latest_result().return_value == 6.0
    assert jobs["finished"].latest_result().return_value == 9.0
    assert jobs["failed"].get_status() == "failed"
    assert queue.count == 0
    assert connection.zcard(queue.deferred_job_registry.key) == 0
