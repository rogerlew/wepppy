"""RQ compatibility at real Redis, worker, execution and scheduler boundaries.

Use RQ212_TEST_REDIS_SOCKET for a disposable server, or a local redis-server.
All lifecycle mutations use disposable Redis; no flush is used.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import timedelta
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
from types import SimpleNamespace
from uuid import uuid4

import pytest
import redis
from rq import Queue, Retry, Worker
from rq.command import send_stop_job_command
from rq.registry import DeferredJobRegistry, StartedJobRegistry

from tests.rq.rq212_tasks import lifecycle_job
from wepppy.rq.job_dependencies import failure_tolerant_depends_on, reconcile_deferred_workflow

pytestmark = [pytest.mark.integration, pytest.mark.slow]


def wait_for(predicate, *, timeout=20):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = predicate()
        if result:
            return result
        time.sleep(0.02)
    pytest.fail(f"condition did not become true within {timeout} seconds")


def state(job):
    value = job.get_status(refresh=True)
    return getattr(value, "value", value)


@pytest.fixture
def lifecycle(tmp_path):
    socket_path = os.environ.get("RQ212_TEST_REDIS_SOCKET")
    server = None
    if socket_path:
        guard = redis.StrictRedis(unix_socket_path=socket_path)
        assert guard.get("batch-boundary-test-server") == b"disposable"
        guard.close()
    else:
        executable = shutil.which("redis-server")
        if executable is None:
            pytest.skip("redis-server or RQ212_TEST_REDIS_SOCKET required")
        socket_path = str(tmp_path / "redis.sock")
        server = subprocess.Popen([executable, "--port", "0", "--unixsocket", socket_path,
                                   "--save", "", "--appendonly", "no"],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        wait_for(lambda: Path(socket_path).exists())
    connection = redis.StrictRedis(unix_socket_path=socket_path, db=2)
    prefix = "rq212-" + str(uuid4())
    queue = Queue(prefix, connection=connection)
    processes = []
    logs = []
    audit_path = tmp_path / "outbound.jsonl"

    @contextmanager
    def worker(*, pool=False, burst=False, scheduler=False, maintenance=False, dequeue_and_crash=False):
        log_path = tmp_path / f"worker-{len(logs)}.log"
        logs.append(log_path)
        env = os.environ.copy()
        env.update(WEPPPY_PROJECT_COMMIT_MODE="disabled", ENABLE_PROFILE_COVERAGE="false")
        command = [sys.executable, "-m", "tests.rq.rq212_tasks", socket_path, prefix, str(audit_path)]
        if pool:
            command.append("--pool")
        if burst:
            command.append("--burst")
        if scheduler:
            command.append("--scheduler")
        if maintenance:
            command.append("--maintenance")
        if dequeue_and_crash:
            command.append("--dequeue-and-crash")
        with log_path.open("w") as log:
            process = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=True)
        processes.append(process)
        try:
            yield process
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
            # A deliberately killed supervisor can leave its test scheduler behind.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

    def enqueue(*, operation="success", suffix=None, task_kwargs=None, **options):
        job_id = prefix + "-" + (suffix or str(uuid4()))
        return queue.enqueue(lifecycle_job, job_id=job_id,
                             kwargs={"operation": operation, "marker": job_id, **(task_kwargs or {})}, **options)

    harness = SimpleNamespace(connection=connection, queue=queue, prefix=prefix,
                              worker=worker, enqueue=enqueue, logs=logs)
    try:
        yield harness
    finally:
        for process in processes:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
        connection.close()
        if server is not None:
            server.terminate()
            server.wait(timeout=5)
        for log_path in logs:
            print(log_path.read_text())
        # Jobs use no webhooks. The audit hook observes any attempted TCP delivery,
        # including failed delivery attempts, in the actual worker descendants.
        # Assert after resource cleanup so an egress regression cannot leak Redis.
        assert not audit_path.exists() or not audit_path.read_text(), audit_path.read_text()


def test_success_result_retention_strict_release_and_no_webhooks(lifecycle):
    h = lifecycle
    parent = h.enqueue(result_ttl=-1)
    child = h.queue.enqueue(lifecycle_job, kwargs={"marker": h.prefix + "-child",
                                                  "prerequisite": parent.id}, depends_on=parent)
    assert state(child) == "deferred"
    with h.worker(burst=True) as worker:
        assert worker.wait(timeout=20) == 0
    assert state(parent) == state(child) == "finished"
    assert parent.return_value() == child.return_value() == {"attempt": 1, "value": 42}
    assert h.connection.ttl(parent.key) == -1
    assert not StartedJobRegistry(queue=h.queue).get_job_ids()
    assert not DeferredJobRegistry(queue=h.queue).get_job_ids()
    parent.refresh()
    assert not getattr(parent, "webhooks", [])
    assert not h.connection.hget(parent.key, "webhooks")


def test_strict_failure_tolerant_finalizer_and_obsolete_graph_resubmission(lifecycle):
    h = lifecycle
    parent = h.enqueue(operation="fail")
    strict = h.enqueue(depends_on=parent)
    finalizer = h.enqueue(depends_on=failure_tolerant_depends_on(parent),
                          task_kwargs={"terminal_prerequisite": parent.id})
    with h.worker(burst=True) as worker:
        assert worker.wait(timeout=20) == 0
    assert state(parent) == "failed"
    assert state(strict) == "deferred"
    assert state(finalizer) == "finished"
    assert h.connection.get(strict.id + ":attempts") is None
    outcome = reconcile_deferred_workflow(parent.id, connection=h.connection,
                                         association=lambda job: job.origin == h.queue.name,
                                         root_association=lambda job: job.origin == h.queue.name)
    assert outcome.state == "canceled"
    assert state(strict) == "canceled"
    replacement = h.enqueue()
    successor = h.enqueue(depends_on=replacement)
    with h.worker(burst=True) as worker:
        assert worker.wait(timeout=20) == 0
    assert state(successor) == "finished"
    assert h.connection.get(successor.id + ":attempts") == b"1"
    assert h.connection.get(strict.id + ":attempts") is None


@pytest.mark.parametrize("interval", [0, 2])
def test_retry_attempt_does_not_release_strict_work_early(lifecycle, interval):
    h = lifecycle
    marker = h.prefix + "-retry"
    job = h.queue.enqueue(lifecycle_job, kwargs={"marker": marker, "fail_attempts": 1},
                          retry=Retry(max=1, interval=interval))
    child = h.enqueue(depends_on=job)
    with h.worker(scheduler=True):
        if interval:
            wait_for(lambda: state(job) == "scheduled")
            assert state(child) == "deferred"
            assert h.connection.get(child.id + ":attempts") is None
        wait_for(lambda: state(child) == "finished")
    assert state(job) == "finished"
    assert job.return_value() == {"attempt": 2, "value": 42}
    assert h.connection.get(marker + ":attempts") == b"2"
    assert h.connection.get(child.id + ":attempts") == b"1"


def test_terminal_retry_failure_releases_only_tolerant_finalizer(lifecycle):
    h = lifecycle
    job = h.enqueue(operation="fail", retry=Retry(max=1))
    strict = h.enqueue(depends_on=job)
    finalizer = h.enqueue(depends_on=failure_tolerant_depends_on(job),
                          task_kwargs={"terminal_prerequisite": job.id})
    with h.worker(burst=True) as worker:
        assert worker.wait(timeout=20) == 0
    assert state(job) == "failed"
    assert state(strict) == "deferred"
    assert state(finalizer) == "finished"
    assert h.connection.get(job.id + ":attempts") == b"2"
    assert h.connection.get(finalizer.id + ":attempts") == b"1"


def test_queued_cancellation_never_executes_and_resubmission_runs(lifecycle):
    h = lifecycle
    canceled = h.enqueue()
    from wepppy.rq.cancel_job import _cancel_job_recursive
    _cancel_job_recursive(canceled, h.connection)
    replacement = h.enqueue()
    with h.worker(burst=True) as worker:
        assert worker.wait(timeout=20) == 0
    assert state(canceled) == "canceled"
    assert h.connection.get(canceled.id + ":attempts") is None
    assert state(replacement) == "finished"


@pytest.mark.parametrize("failure", ["stop", "timeout", "sigkill"])
def test_running_stop_timeout_and_workhorse_crash(lifecycle, failure):
    h = lifecycle
    job = h.enqueue(operation="hold", job_timeout=2 if failure == "timeout" else 30)
    finalizer = h.enqueue(depends_on=failure_tolerant_depends_on(job),
                          task_kwargs={"terminal_prerequisite": job.id})
    strict = h.enqueue(depends_on=job)
    with h.worker():
        pid = int(wait_for(lambda: h.connection.get(job.id + ":started")))
        if failure == "stop":
            send_stop_job_command(h.connection, job.id)
        elif failure == "sigkill":
            os.kill(pid, signal.SIGKILL)
        wait_for(lambda: state(job) in {"failed", "stopped"})
        wait_for(lambda: state(finalizer) == "finished")
        replacement = h.enqueue()
        wait_for(lambda: state(replacement) == "finished")
    assert state(job) == ("stopped" if failure == "stop" else "failed")
    assert state(strict) == "deferred"
    assert h.connection.get(strict.id + ":attempts") is None
    assert not StartedJobRegistry(queue=h.queue).get_job_ids()
    assert h.connection.get(replacement.id + ":attempts") == b"1"


def test_execution_ids_discovery_current_job_and_timestamps(lifecycle):
    h = lifecycle
    job = h.enqueue(operation="hold")
    with h.worker():
        wait_for(lambda: h.connection.get(job.id + ":started"))
        registry = StartedJobRegistry(queue=h.queue)
        assert registry.get_job_ids() == [job.id]
        workers = [w for w in Worker.all(connection=h.connection) if h.queue.name in w.queue_names()]
        assert len(workers) == 1
        assert workers[0].get_current_job_id() == job.id
        job.refresh()
        assert json.loads(json.dumps({"status": job.get_status()})) == {"status": "started"}
        assert job.started_at is not None
        if hasattr(job, "get_executions"):
            executions = job.get_executions()
            assert len(executions) == 1
            assert h.connection.zrange(registry.key, 0, -1) == [executions[0].composite_key.encode()]
            assert executions[0].composite_key.startswith(job.id + ":")
            assert job.started_at.utcoffset() == timedelta(0)
        h.connection.set(job.id + ":release", "1")
        wait_for(lambda: state(job) == "finished")
    job.refresh()
    assert job.ended_at >= job.started_at


def test_abandoned_execution_recovery_retains_failure_and_blocks_strict_child(lifecycle):
    h = lifecycle
    job = h.enqueue(operation="hold")
    strict = h.enqueue(depends_on=job)
    with h.worker() as worker:
        horse_pid = int(wait_for(lambda: h.connection.get(job.id + ":started")))
        os.killpg(worker.pid, signal.SIGKILL)
        # RQ places its workhorse in a separate process group. Kill the recorded
        # test horse as well before expiring its execution lease.
        os.kill(horse_pid, signal.SIGKILL)
        worker.wait(timeout=5)
    registry = StartedJobRegistry(queue=h.queue)
    raw_members = h.connection.zrange(registry.key, 0, -1)
    assert raw_members
    # Expire the actual execution lease after supervisor and workhorse are dead.
    h.connection.zadd(registry.key, {member: 1 for member in raw_members})
    registry.cleanup()
    assert state(job) == "failed"
    assert "AbandonedJobError" in job.exc_info
    assert state(strict) == "deferred"
    assert h.connection.get(strict.id + ":attempts") is None


def test_worker_pool_replaces_failed_worker_and_schedules(lifecycle):
    h = lifecycle
    scheduled = h.queue.enqueue_in(timedelta(seconds=2), lifecycle_job,
                                   kwargs={"marker": h.prefix + "-scheduled"})
    prior_client_ids = {client["id"] for client in h.connection.client_list()}
    with h.worker(pool=True):
        wait_for(lambda: state(scheduled) == "finished")
        workers = wait_for(lambda: [w for w in Worker.all(connection=h.connection)
                                    if h.queue.name in w.queue_names() and w.get_state() == "idle"])
        assert len(workers) == 1
        old_pid = workers[0].pid
        # Idle state is published before blocking dequeue. Wait for the actual
        # new DB2 blocking client so this fault cannot miss the inherited-FD bug.
        wait_for(lambda: [client for client in h.connection.client_list()
                          if client["id"] not in prior_client_ids
                          and str(client["db"]) == "2" and client["cmd"] == "blmove"
                          and "b" in client["flags"]])
        os.kill(old_pid, signal.SIGKILL)
        wait_for(lambda: not Path(f"/proc/{old_pid}").exists())
        wait_for(lambda: [w for w in Worker.all(connection=h.connection)
                          if h.queue.name in w.queue_names() and w.name != workers[0].name])
        replacement = h.enqueue()
        wait_for(lambda: state(replacement) == "finished")
        replacement.refresh()
        assert replacement.worker_name != workers[0].name
        current = Worker.find_by_key("rq:worker:" + replacement.worker_name, connection=h.connection)
        assert current.pid != old_pid
        after_replacement = h.queue.enqueue_in(
            timedelta(seconds=2), lifecycle_job,
            kwargs={"marker": h.prefix + "-scheduled-after-replacement"},
        )
        wait_for(lambda: state(after_replacement) == "finished")
    assert scheduled.return_value() == {"attempt": 1, "value": 42}
    assert replacement.return_value() == {"attempt": 1, "value": 42}
    assert after_replacement.return_value() == {"attempt": 1, "value": 42}



def test_interrupted_dequeue_standard_maintenance_preserves_failure_and_recovers(lifecycle):
    h = lifecycle
    interrupted = h.enqueue()
    strict = h.enqueue(depends_on=interrupted)
    finalizer = h.enqueue(depends_on=failure_tolerant_depends_on(interrupted))
    with h.worker(dequeue_and_crash=True) as process:
        assert process.wait(timeout=20) == 72
    intermediate = h.queue.intermediate_queue
    assert intermediate.get_job_ids() == [interrupted.id]
    assert state(interrupted) == "queued"
    assert h.connection.get(interrupted.id + ":attempts") is None
    # Only this test job's clock is advanced across RQ's real 60-second grace.
    h.connection.set(intermediate.get_first_seen_key(interrupted.id), time.time() - 61)
    with h.worker(maintenance=True) as process:
        assert process.wait(timeout=20) == 0
    assert state(interrupted) == "failed"
    assert "stuck in intermediate queue" in interrupted.exc_info
    assert intermediate.get_job_ids() == []
    assert state(strict) == "deferred"
    replacement = h.enqueue()
    with h.worker(burst=True) as process:
        assert process.wait(timeout=20) == 0
    assert state(finalizer) == state(replacement) == "finished"
    assert h.connection.get(interrupted.id + ":attempts") is None
    assert h.connection.get(replacement.id + ":attempts") == b"1"
