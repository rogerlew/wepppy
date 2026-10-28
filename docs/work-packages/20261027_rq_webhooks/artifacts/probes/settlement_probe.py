"""Isolated substrate probe; never connects to configured application Redis.

Run from repository root with .venv/bin/python and PYTHONPATH=.
No webhook implementation or environment-acceptance claim.
"""
import json
import logging
import subprocess
import tempfile
import time
from pathlib import Path

import redis
import rq
from rq import Queue, SimpleWorker
from rq.job import Dependency, Job, JobStatus
from redis.exceptions import WatchError
from wepppy.rq.auth_actor import install_rq_auth_actor_hook, set_auth_actor, reset_auth_actor
from wepppy.rq.job_dependencies import release_deferred_job_if_ready


def run_probe(connection):
    results = {"rq_version": rq.__version__, "redis_version": redis.__version__}
    install_rq_auth_actor_hook()
    token = set_auth_actor({"sub": "synthetic"})
    q = Queue("probe", connection=connection)
    try:
        normal = q.enqueue_call(json.loads, args=("1",))
        bulk = q.enqueue_many([q.prepare_data(json.loads, args=("2",))])[0]
        direct = q.enqueue_job(Job.create(json.loads, args=("3",), connection=connection))
        results["actor_capture"] = {"enqueue_call": bool(normal.meta.get("auth_actor")), "enqueue_many": bool(bulk.meta.get("auth_actor")), "enqueue_job": bool(direct.meta.get("auth_actor"))}
        assert results["actor_capture"] == {"enqueue_call": True, "enqueue_many": False, "enqueue_job": False}
        with connection.pipeline() as pipe:
            planned = q.enqueue_call(json.loads, args=("4",), pipeline=pipe)
            assert not connection.exists(planned.key)
            pipe.execute()
            assert connection.exists(planned.key)
        results["caller_pipeline"] = "returned object precedes publication"
        parent = Job.create(json.loads, args=("0",), connection=connection)
        parent.save()
        child = q.enqueue_call(json.loads, args=("5",))
        assert connection.exists(child.key) and not Job.fetch(parent.id, connection=connection).meta
        results["post_enqueue_parent_registration"] = "visible child absent from parent metadata"
    finally:
        reset_auth_actor(token)

    # Use separate queue and actual worker execution to establish dependency behavior.
    q = Queue("dependencies", connection=connection)
    a = q.enqueue_call(json.loads, args=("not-an-integer",))
    b = q.enqueue_call(json.loads, args=("1",), depends_on=a)
    c = q.enqueue_call(json.loads, args=("2",), depends_on=Dependency(b, allow_failure=True))
    d = q.enqueue_call(json.loads, args=("3",), depends_on=Dependency(a, allow_failure=True))
    SimpleWorker([q], connection=connection).work(burst=True, logging_level=logging.CRITICAL)
    states = {name: job.get_status(refresh=True).value for name, job in [("A", a), ("B", b), ("C", c), ("D", d)]}
    assert states == {"A": "failed", "B": "deferred", "C": "deferred", "D": "finished"}
    results["strict_and_allow_failure"] = states
    stopped = Job.create(json.loads, args=("1",), connection=connection, status=JobStatus.STOPPED)
    stopped.save()
    observer = q.enqueue_call(json.loads, args=("2",), depends_on=Dependency(stopped, allow_failure=True))
    assert observer.get_status(refresh=True) == JobStatus.DEFERRED
    release_deferred_job_if_ready(q, observer, stopped_parent_id=stopped.id)
    assert observer.get_status(refresh=True) == JobStatus.QUEUED
    results["stopped_observer"] = "deferred until explicit existing helper release"
    canceled = Job.create(json.loads, args=("1",), connection=connection, status=JobStatus.CANCELED)
    canceled.save()
    blocked = q.enqueue_call(json.loads, args=("2",), depends_on=Dependency(canceled, allow_failure=True))
    release_deferred_job_if_ready(q, blocked)
    assert blocked.get_status(refresh=True) == JobStatus.DEFERRED
    results["canceled_allow_failure"] = "deferred"

    connection.set("probe:revision", 1)
    with connection.pipeline() as pipe:
        pipe.watch("probe:revision")
        assert pipe.get("probe:revision") == b"1"
        connection.incr("probe:revision")
        pipe.multi()
        pipe.set("probe:event", "stale", nx=True)
        try:
            pipe.execute()
        except WatchError:
            pass
        else:
            raise AssertionError("stale snapshot committed")
    assert not connection.exists("probe:event")
    results["conditional_commit"] = "WATCH rejects stale revision; unique insert alone is insufficient"
    return results


def main():
    with tempfile.TemporaryDirectory(prefix="rq-webhook-probe-") as directory:
        socket = str(Path(directory) / "redis.sock")
        proc = subprocess.Popen(["redis-server", "--port", "0", "--unixsocket", socket, "--unixsocketperm", "700", "--save", "", "--appendonly", "no"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        connection = redis.Redis(unix_socket_path=socket)
        try:
            for _ in range(100):
                if proc.poll() is not None:
                    raise RuntimeError("isolated redis exited")
                try:
                    if connection.ping():
                        break
                except redis.ConnectionError:
                    time.sleep(.02)
            else:
                raise RuntimeError("isolated redis did not start")
            results = run_probe(connection)
            results["redis_server"] = connection.info("server")["redis_version"]
            print(json.dumps(results, indent=2, sort_keys=True))
        finally:
            connection.close()
            proc.terminate()
            proc.wait(timeout=5)


if __name__ == "__main__":
    main()
