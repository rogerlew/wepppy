from concurrent.futures import ThreadPoolExecutor
import json
from uuid import uuid4

import pytest
import redis
from rq import Queue, SimpleWorker, worker_registration
from rq.job import JobStatus
from rq.suspension import WORKERS_SUSPENDED, resume, suspend

from wepppy.rq.run_catalog_rq import enqueue_sweep, is_catalog_job, deployment_identity
from wepppy.rq.job_info import recursive_get_job_details
from rq.utils import utcnow
from tests.weppcloud.test_run_catalog_postgres import database
from tests.rq.test_batch_task_boundary import isolated_rq

pytestmark = pytest.mark.integration


def _register_consumer(queue, identity, state="idle"):
    worker = SimpleWorker([queue], connection=queue.connection, name="catalog-test-" + uuid4().hex)
    worker.register_birth()
    worker.set_state(state)
    queue.connection.hset(worker.key, "run_catalog_configuration", json.dumps(
        {"protocol": 1, "database": identity, "write_mode": "catalog"}))
    return worker


@pytest.fixture
def admission_queue(isolated_rq, monkeypatch):
    monkeypatch.setenv("WEPPPY_PROJECT_COMMIT_MODE", "postgres")
    monkeypatch.setenv("WEPPCLOUD_RUN_CATALOG_WRITE_MODE", "catalog")
    monkeypatch.setenv("WEPPCLOUD_RUN_CATALOG_READ_MODE", "legacy")
    monkeypatch.setenv("DATABASE_URL", "postgresql://catalog-test@localhost/catalog_test_" + uuid4().hex)
    monkeypatch.delenv("SQLALCHEMY_DATABASE_URI", raising=False)
    queue = Queue("catalog-test-" + uuid4().hex, connection=isolated_rq)
    try:
        yield queue
    finally:
        for key in worker_registration.get_keys(queue=queue):
            isolated_rq.srem(worker_registration.WORKERS_BY_QUEUE_KEY % queue.name, key)
            isolated_rq.srem(worker_registration.REDIS_WORKER_KEYS, key)
            isolated_rq.delete(key)
        queue.delete(delete_jobs=True)
        isolated_rq.delete("run-catalog:admission:" + deployment_identity())


def test_real_queued_sweep_publishes_sql_and_safe_tree(database, tmp_path, monkeypatch, isolated_rq):
    import os
    import sqlalchemy as sa
    from wepppy.weppcloud.run_catalog import adapter
    from wepppy.weppcloud.run_catalog.paths import Roots
    from wepppy.weppcloud.run_catalog.schema import catalog, runs
    suffix = uuid4().hex
    monkeypatch.setenv("WEPPPY_PROJECT_COMMIT_MODE", "postgres")
    monkeypatch.setenv("WEPPCLOUD_RUN_CATALOG_WRITE_MODE", "catalog")
    monkeypatch.setenv("WEPPCLOUD_RUN_CATALOG_READ_MODE", "legacy")
    monkeypatch.setenv("DATABASE_URL", "postgresql://catalog-test@localhost/catalog_test_" + suffix)
    monkeypatch.delenv("SQLALCHEMY_DATABASE_URI", raising=False)
    monkeypatch.setattr(adapter, "_engines", {(os.getpid(), False): database, (os.getpid(), True): database})
    from wepppy.nodb import persistence_events
    monkeypatch.setattr(persistence_events, "_observer", None)
    roots = Roots(primary=str(tmp_path), legacy=str(tmp_path / "legacy"))
    monkeypatch.setattr(Roots, "from_environ", classmethod(lambda cls: roots))
    project = tmp_path / "te" / "test"
    project.mkdir(parents=True)
    (project / "ron.nodb").write_text('{"_name":"RQ source"}')
    with database.begin() as sql:
        sql.execute(runs.insert().values(id=1, runid="test"))
    connection = isolated_rq
    queue = Queue("catalog-test-" + suffix, connection=connection)
    identity = deployment_identity()
    worker = _register_consumer(queue, identity)
    try:
        assert enqueue_sweep(queue)
        identifier = queue.get_job_ids()[0]
        worker.register_death()
        worker.work(burst=True)
        job = queue.fetch_job(identifier)
        assert job.get_status() == JobStatus.FINISHED
        assert job.return_value() is None
        tree = recursive_get_job_details(job, connection, utcnow())
        assert tree["job_id"] == identifier
        assert tree["description"] == "Run catalog maintenance"
        assert "RQ source" not in str(tree)
        with database.connect() as sql:
            assert sql.scalar(sa.select(catalog.c.name)) == "RQ source"
        health = json.loads(connection.get("run-catalog:health:" + identity))
        assert health["state"] == "completed"
        assert health["attempted"] == 1
        job.delete()
    finally:
        worker.register_death()
        connection.delete(worker.key)
        queue.delete(delete_jobs=True)
        connection.delete("run-catalog:admission:" + identity, "run-catalog:health:" + identity)
        connection.close()


def test_real_rq_atomic_admission_and_private_terminal_record(monkeypatch, isolated_rq):
    suffix = uuid4().hex
    url = "postgresql://catalog-test@localhost/catalog_test_" + suffix
    monkeypatch.setenv("WEPPPY_PROJECT_COMMIT_MODE", "postgres")
    monkeypatch.setenv("WEPPCLOUD_RUN_CATALOG_WRITE_MODE", "catalog")
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.delenv("SQLALCHEMY_DATABASE_URI", raising=False)
    connection = isolated_rq
    queue = Queue("catalog-test-" + suffix, connection=connection)
    key = "run-catalog:admission:" + deployment_identity()
    identifiers = []
    worker = _register_consumer(queue, deployment_identity())
    try:
        with ThreadPoolExecutor(max_workers=4) as pool:
            admitted = list(pool.map(lambda _: enqueue_sweep(queue), range(4)))
        assert sum(admitted) == 1
        identifiers = queue.get_job_ids()
        assert len(identifiers) == 1
        assert is_catalog_job(identifiers[0])
        job = queue.fetch_job(identifiers[0])
        assert job.description == "Run catalog maintenance"
        job.set_status(JobStatus.FAILED)
        job.meta["error"] = {"message": "private-path-canary"}
        job.save_meta()
        connection.hset(job.key, "exc_info", "private-database-canary")
        details = recursive_get_job_details(job, connection, utcnow())
        assert details["exc_info"] is None
        assert details["result"] is None
        assert "private" not in str(details)
        assert enqueue_sweep(queue)
        identifiers = queue.get_job_ids()
        assert len(identifiers) == 2
    finally:
        worker.register_death()
        connection.delete(worker.key)
        for identifier in identifiers:
            job = queue.fetch_job(identifier)
            if job:
                job.delete()
        queue.delete(delete_jobs=True)
        connection.delete(key)
        connection.close()


def test_no_workers_skip_repeated_ticks_then_recover(admission_queue):
    queue = admission_queue
    key = "run-catalog:admission:" + deployment_identity()
    queue.connection.set(key, "retained-terminal-pointer")
    for _ in range(20):
        assert not enqueue_sweep(queue)
    assert queue.count == 0
    assert queue.connection.get(key) == b"retained-terminal-pointer"
    _register_consumer(queue, deployment_identity())
    assert enqueue_sweep(queue)
    assert queue.count == 1


@pytest.mark.parametrize("condition", [
    "busy", "suspended", "unknown", "missing_state", "missing", "expired", "nonexpiring",
    "dead", "other_queue", "reused_name", "missing_config", "malformed_config", "invalid_encoding",
    "wrong_database", "wrong_protocol", "wrong_mode",
])
def test_unavailable_worker_does_not_change_admission(admission_queue, condition):
    queue = admission_queue
    connection = queue.connection
    identity = deployment_identity()
    worker = _register_consumer(queue, identity)
    if condition in {"busy", "suspended", "unknown"}:
        worker.set_state(condition)
    elif condition == "missing_state":
        connection.hdel(worker.key, "state")
    elif condition == "missing":
        connection.delete(worker.key)
    elif condition == "expired":
        connection.expire(worker.key, 0)
    elif condition == "nonexpiring":
        connection.persist(worker.key)
    elif condition == "dead":
        connection.hset(worker.key, "death", "observed-death")
    elif condition == "other_queue":
        connection.hset(worker.key, "queues", "other-queue")
    elif condition == "reused_name":
        connection.delete(worker.key)
        connection.hset(worker.key, mapping={"state": "idle", "queues": "other-queue",
                                            "run_catalog_configuration": json.dumps(
                                                {"protocol": 1, "database": identity, "write_mode": "catalog"})})
        connection.expire(worker.key, 60)
    elif condition == "missing_config":
        connection.hdel(worker.key, "run_catalog_configuration")
    elif condition in {"malformed_config", "invalid_encoding"}:
        connection.hset(worker.key, "run_catalog_configuration", "{" if condition == "malformed_config" else b"\xff")
    else:
        configuration = {"protocol": 1, "database": identity, "write_mode": "catalog"}
        configuration[{"wrong_database": "database", "wrong_protocol": "protocol", "wrong_mode": "write_mode"}[condition]] = "incompatible"
        connection.hset(worker.key, "run_catalog_configuration", json.dumps(configuration))
    key = "run-catalog:admission:" + identity
    before = connection.get(key)
    assert not enqueue_sweep(queue)
    assert connection.get(key) == before
    assert queue.count == 0


def test_idle_worker_in_mixed_pool_is_enough(admission_queue):
    _register_consumer(admission_queue, deployment_identity(), state="busy")
    _register_consumer(admission_queue, deployment_identity())
    assert enqueue_sweep(admission_queue)


def test_global_suspension_and_observation_are_passive(admission_queue):
    queue = admission_queue
    connection = queue.connection
    worker = _register_consumer(queue, deployment_identity())
    connection.pexpire(worker.key, 30000)
    before = connection.hgetall(worker.key)
    ttl = connection.pttl(worker.key)
    previous_suspension = connection.get(WORKERS_SUSPENDED)
    assert previous_suspension is None
    try:
        suspend(connection)
        assert not enqueue_sweep(queue)
        assert queue.count == 0
        assert connection.get("run-catalog:admission:" + deployment_identity()) is None
        assert connection.hgetall(worker.key) == before
        assert 0 < connection.pttl(worker.key) <= ttl
    finally:
        resume(connection)
    assert enqueue_sweep(queue)
    assert connection.hgetall(worker.key) == before
    assert 0 < connection.pttl(worker.key) <= ttl


@pytest.mark.parametrize("state", ["queued", "started", "deferred", "scheduled"])
def test_existing_sweep_survives_busy_pool_and_repeated_ticks(admission_queue, state):
    queue = admission_queue
    worker = _register_consumer(queue, deployment_identity())
    assert enqueue_sweep(queue)
    identifier = queue.get_job_ids()[0]
    queue.fetch_job(identifier).set_status(state)
    worker.set_state("busy")
    for _ in range(20):
        assert not enqueue_sweep(queue)
    worker.set_state("idle")
    restarted_queue = Queue(queue.name, connection=queue.connection)
    assert not enqueue_sweep(restarted_queue)
    assert queue.get_job_ids() == [identifier]


def test_worker_loss_after_observation_still_coalesces(admission_queue, monkeypatch):
    from wepppy.rq import run_catalog_rq
    queue = admission_queue
    worker = _register_consumer(queue, deployment_identity())
    observe = run_catalog_rq._has_available_worker

    def lose_worker(observed_queue, identity):
        available = observe(observed_queue, identity)
        worker.register_death()
        return available

    monkeypatch.setattr(run_catalog_rq, "_has_available_worker", lose_worker)
    assert enqueue_sweep(queue)
    monkeypatch.setattr(run_catalog_rq, "_has_available_worker", observe)
    assert not enqueue_sweep(queue)
    _register_consumer(queue, deployment_identity())
    assert not enqueue_sweep(queue)
    assert queue.count == 1


def test_redis_observation_error_is_not_silenced(admission_queue, monkeypatch):
    def unavailable(*args, **kwargs):
        raise redis.ConnectionError("injected unavailable registry")

    with monkeypatch.context() as context:
        context.setattr(worker_registration, "get_keys", unavailable)
        with pytest.raises(redis.ConnectionError, match="injected unavailable registry"):
            enqueue_sweep(admission_queue)
    assert admission_queue.count == 0
