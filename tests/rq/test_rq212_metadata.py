"""Real Redis publication and worker-context coverage for the RQ migration."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest
import redis
from rq import Queue, get_current_job
from rq.job import Job

from wepppy.observability.correlation import (
    current_correlation_id, reset_correlation_id, set_correlation_id,
)
from wepppy.profile_coverage import runtime as profile
from wepppy.rq import auth_actor

pytestmark = pytest.mark.integration


def metadata_task(*, child=False):
    """Return context observed inside a real workhorse and optionally enqueue a child."""
    job = get_current_job()
    result = {
        "actor": auth_actor.current_auth_actor(),
        "correlation": current_correlation_id(),
        "profile": profile.current_profile_trace_slug(),
    }
    if child:
        child_job = Queue(job.origin, connection=job.connection).enqueue(metadata_task)
        result["child_id"] = child_job.id
    return result


@pytest.fixture
def metadata_queue(monkeypatch):
    socket_path = os.getenv("RQ212_METADATA_REDIS_SOCKET")
    if not socket_path:
        pytest.skip("requires an explicitly selected disposable Redis Unix socket")
    connection = redis.StrictRedis(unix_socket_path=socket_path, db=3)
    marker_connection = redis.StrictRedis(unix_socket_path=socket_path, db=0)
    assert marker_connection.get("batch-boundary-test-server") == b"disposable"
    marker_connection.close()
    monkeypatch.setattr(redis, "Redis", redis.StrictRedis)
    for attribute in ("enqueue", "enqueue_call"):
        monkeypatch.setattr(Queue, attribute, getattr(Queue, attribute))
    for attribute in ("_auth_actor_wrapped", "_profile_trace_wrapped"):
        monkeypatch.setattr(Queue, attribute, getattr(Queue, attribute, False), raising=False)
    auth_actor.install_rq_auth_actor_hook()
    profile.install_rq_hooks()
    queue = Queue(f"rq212-metadata-{uuid4()}", connection=connection)
    before = set(connection.scan_iter())
    try:
        yield queue
    finally:
        # DB3 is reserved for this suite on the explicitly disposable server.
        # Remove only newly created keys, including aborted metadata-only hashes.
        created = set(connection.scan_iter()) - before
        if created:
            connection.delete(*created)
        connection.srem("rq:queues", queue.key)
        connection.close()


@pytest.fixture
def metadata_context():
    expected = {"auth_actor": {"token_class": "session", "session_id": "rq212-test"},
                "correlation_id": "rq212-correlation", "profile_trace_slug": "rq212-profile"}
    actor_token = auth_actor.set_auth_actor(expected["auth_actor"])
    correlation_token = set_correlation_id(expected["correlation_id"])
    profile_token = profile.set_profile_trace_slug(expected["profile_trace_slug"])
    try:
        yield expected
    finally:
        profile.reset_profile_trace_slug(profile_token)
        reset_correlation_id(correlation_token)
        auth_actor.reset_auth_actor(actor_token)


@pytest.mark.parametrize("method", ["enqueue", "enqueue_call"])
def test_metadata_is_durable_when_queue_publishes(metadata_queue, metadata_context, monkeypatch, method):
    original = Queue.enqueue_job
    observed = []

    def publish(self, job, *args, **kwargs):
        result = original(self, job, *args, **kwargs)
        # This read is after real Redis publication but before either outer
        # enqueue hook can repair metadata. A worker may consume at this point.
        observed.append(Job.fetch(job.id, connection=self.connection).meta)
        return result

    monkeypatch.setattr(Queue, "enqueue_job", publish)
    job = getattr(metadata_queue, method)(metadata_task)
    assert observed == [metadata_context]
    assert Job.fetch(job.id, connection=metadata_queue.connection).meta == metadata_context


def test_pipeline_abort_never_creates_metadata_only_job(metadata_queue, metadata_context):
    with metadata_queue.connection.pipeline() as pipeline:
        job = metadata_queue.enqueue_call(metadata_task, pipeline=pipeline)
        assert not metadata_queue.connection.exists(job.key)
        assert not metadata_queue.connection.lrange(metadata_queue.key, 0, -1)
        pipeline.reset()
    assert not metadata_queue.connection.exists(job.key)


def test_pipeline_commit_publishes_complete_metadata(metadata_queue, metadata_context):
    with metadata_queue.connection.pipeline() as pipeline:
        job = metadata_queue.enqueue_call(metadata_task, pipeline=pipeline)
        pipeline.execute()
    assert Job.fetch(job.id, connection=metadata_queue.connection).meta == metadata_context
    assert metadata_queue.get_job_ids() == [job.id]


def test_lost_enqueue_ack_recovers_same_job_and_metadata(metadata_queue, metadata_context, monkeypatch):
    original = Queue.enqueue_job

    def lose_ack(self, job, *args, **kwargs):
        original(self, job, *args, **kwargs)
        raise redis.ConnectionError("injected lost acknowledgment after Redis commit")

    monkeypatch.setattr(Queue, "enqueue_job", lose_ack)
    job_id = str(uuid4())
    job = metadata_queue.enqueue_call(metadata_task, job_id=job_id)
    assert job.id == job_id
    assert metadata_queue.get_job_ids() == [job_id]
    assert Job.fetch(job_id, connection=metadata_queue.connection).meta == metadata_context


def test_positional_metadata_joins_enqueue_transaction(metadata_queue, metadata_context):
    job = metadata_queue.enqueue_call(metadata_task, None, None, None, None, None,
                                     None, None, None, None, False, {"custom": "retained"})
    assert Job.fetch(job.id, connection=metadata_queue.connection).meta == {
        **metadata_context, "custom": "retained"}


def test_explicit_metadata_precedence_and_input_immutability(metadata_queue, metadata_context):
    explicit = {"auth_actor": {"token_class": "service", "service_id": "explicit"},
                "correlation_id": "explicit-correlation", "profile_trace_slug": "old-profile"}
    job = metadata_queue.enqueue_call(metadata_task, meta=explicit)
    stored = Job.fetch(job.id, connection=metadata_queue.connection).meta
    assert stored["auth_actor"] == explicit["auth_actor"]
    assert stored["correlation_id"] == explicit["correlation_id"]
    assert stored["profile_trace_slug"] == metadata_context["profile_trace_slug"]
    assert explicit["profile_trace_slug"] == "old-profile"
    repaired = metadata_queue.enqueue_call(metadata_task, meta={"correlation_id": "invalid value !!!"})
    assert repaired.meta["correlation_id"] == metadata_context["correlation_id"]


@pytest.mark.slow
def test_actual_worker_propagates_root_child_and_clears_context(metadata_queue, tmp_path):
    tokens = (auth_actor.set_auth_actor({"token_class": "session", "session_id": "rq212-root"}),
              set_correlation_id("rq212-root-correlation"), profile.set_profile_trace_slug("rq212-root-profile"))
    try:
        root = metadata_queue.enqueue_call(metadata_task, kwargs={"child": True})
    finally:
        profile.reset_profile_trace_slug(tokens[2])
        reset_correlation_id(tokens[1])
        auth_actor.reset_auth_actor(tokens[0])
    unrelated = metadata_queue.enqueue(metadata_task)
    environment = dict(os.environ, ENABLE_PROFILE_COVERAGE="true", PROFILE_COVERAGE_DIR=str(tmp_path),
                       WEPPPY_PROJECT_COMMIT_MODE="disabled", PYTHONPATH=os.pathsep.join((str(Path(__file__).parent), os.environ.get("PYTHONPATH", os.getcwd()))))
    socket_path = metadata_queue.connection.connection_pool.connection_kwargs["path"]
    program = """
import sys
import redis
from rq import Queue
# Route incidental NoDb/status connections to the same disposable server.
# Metadata publication, RQ persistence and the worker itself remain real.
original_pool = redis.ConnectionPool
class IsolatedPool(original_pool):
    def __init__(self, *args, **kwargs):
        for name in ("host", "port", "username", "password", "unix_socket_path", "socket_keepalive", "socket_keepalive_options"):
            kwargs.pop(name, None)
        kwargs.update(connection_class=redis.UnixDomainSocketConnection, path=sys.argv[1], db=3)
        super().__init__(*args, **kwargs)
redis.ConnectionPool = IsolatedPool
redis.client.ConnectionPool = IsolatedPool
from wepppy.rq.rq_worker import WepppyRqWorker
connection = redis.Redis(unix_socket_path=sys.argv[1], db=3)
queue = Queue(sys.argv[2], connection=connection)
worker = WepppyRqWorker([queue], connection=connection)
worker.work(burst=True)
"""
    completed = subprocess.run([sys.executable, "-c", program, socket_path, metadata_queue.name],
                               env=environment, text=True, capture_output=True, timeout=45)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    root.refresh(); unrelated.refresh()
    expected = {"actor": {"token_class": "session", "session_id": "rq212-root"},
                "correlation": "rq212-root-correlation", "profile": "rq212-root-profile"}
    root_result = root.return_value()
    assert root_result is not None, str(root.exc_info) + completed.stdout + completed.stderr
    child = Job.fetch(root_result.pop("child_id"), connection=metadata_queue.connection)
    assert root_result == child.return_value() == expected
    assert unrelated.return_value() == {"actor": None, "correlation": None, "profile": None}
