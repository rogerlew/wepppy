from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
import redis
from rq import Queue
from rq.job import JobStatus

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.rq.run_catalog_rq import enqueue_sweep, is_catalog_job, deployment_identity
from wepppy.rq.job_info import recursive_get_job_details
from rq.utils import utcnow
from tests.weppcloud.test_run_catalog_postgres import database

pytestmark = pytest.mark.integration
REDIS_OPTIONS = redis_connection_kwargs(RedisDB.RQ)


def test_real_queued_sweep_publishes_sql_and_safe_tree(database, tmp_path, monkeypatch):
    import json
    import os
    import sqlalchemy as sa
    from rq import SimpleWorker
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
    connection = redis.StrictRedis(**REDIS_OPTIONS)
    queue = Queue("catalog-test-" + suffix, connection=connection)
    identity = deployment_identity()
    try:
        assert enqueue_sweep(queue)
        identifier = queue.get_job_ids()[0]
        worker = SimpleWorker([queue], connection=connection, name="catalog-test-" + suffix)
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
        queue.delete(delete_jobs=True)
        connection.delete("run-catalog:admission:" + identity, "run-catalog:health:" + identity)
        connection.close()


def test_real_rq_atomic_admission_and_private_terminal_record(monkeypatch):
    suffix = uuid4().hex
    url = "postgresql://catalog-test@localhost/catalog_test_" + suffix
    monkeypatch.setenv("WEPPPY_PROJECT_COMMIT_MODE", "postgres")
    monkeypatch.setenv("WEPPCLOUD_RUN_CATALOG_WRITE_MODE", "catalog")
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.delenv("SQLALCHEMY_DATABASE_URI", raising=False)
    connection = redis.StrictRedis(**REDIS_OPTIONS)
    queue = Queue("catalog-test-" + suffix, connection=connection)
    key = "run-catalog:admission:" + deployment_identity()
    identifiers = []
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
        for identifier in identifiers:
            job = queue.fetch_job(identifier)
            if job:
                job.delete()
        queue.delete(delete_jobs=True)
        connection.delete(key)
        connection.close()
