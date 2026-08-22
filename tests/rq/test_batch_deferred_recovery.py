from __future__ import annotations

from types import SimpleNamespace
import uuid

import pytest
import redis
from rq import Queue
from rq.job import Job, JobStatus
from rq.registry import DeferredJobRegistry

from wepppy.rq import batch_rq
from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.rq.omni_rq import run_omni_scenarios_rq


pytestmark = pytest.mark.integration


@pytest.fixture
def rq_connection():
    connection = redis.StrictRedis(**redis_connection_kwargs(RedisDB.RQ))
    try:
        connection.ping()
    except redis.RedisError as exc:
        pytest.skip(f"compose Redis is unavailable: {exc}")
    return connection


def test_batch_recovery_uses_persisted_root_and_cancels_omni_descendant(
    rq_connection, monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch_name = f"retry-{uuid.uuid4().hex}"
    runid = f"batch;;{batch_name};;1"
    queue = Queue("batch", connection=rq_connection)
    root = queue.enqueue(
        batch_rq.run_batch_rq,
        batch_name,
        meta={"runid": batch_name},
    )
    child = queue.enqueue(
        run_omni_scenarios_rq,
        runid,
        depends_on=root,
        meta={"runid": runid},
    )
    root.meta["jobs:0,func:run_omni_scenarios_rq"] = child.id
    root.save_meta()
    root.set_status("failed")
    monkeypatch.setattr(
        batch_rq.BatchRunner,
        "getInstanceFromBatchName",
        lambda _name: SimpleNamespace(
            rq_job_ids={
                "run_batch_rq": root.id,
                "final_batch_complete_rq": child.id,
            }
        ),
    )

    try:
        conflicts = batch_rq.reconcile_deferred_batch_jobs(
            batch_name,
            redis_conn=rq_connection,
        )

        child.refresh()
        assert conflicts == []
        assert child.get_status(refresh=True) == "canceled"
        assert child.id not in DeferredJobRegistry(
            "batch", connection=rq_connection
        ).get_job_ids()
    finally:
        for candidate in (child, root):
            try:
                Job.fetch(candidate.id, connection=rq_connection).delete(
                    remove_from_queue=True
                )
            except Exception:
                pass


def test_batch_recovery_detects_bytes_id_in_intermediate_queue(
    rq_connection, monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch_name = f"retry-{uuid.uuid4().hex}"
    queue = Queue("batch", connection=rq_connection)
    job = queue.create_job(
        batch_rq.run_batch_rq,
        args=(batch_name,),
        meta={"runid": batch_name},
        status=JobStatus.QUEUED,
    )
    job.save()
    monkeypatch.setattr(
        batch_rq.BatchRunner,
        "getInstanceFromBatchName",
        lambda _name: SimpleNamespace(rq_job_ids={}),
    )
    rq_connection.rpush(queue.intermediate_queue_key, job.id)

    try:
        conflicts = batch_rq.reconcile_deferred_batch_jobs(
            batch_name,
            redis_conn=rq_connection,
        )

        assert conflicts == [f"{job.id}:queued"]
    finally:
        rq_connection.lrem(queue.intermediate_queue_key, 0, job.id)
        try:
            Job.fetch(job.id, connection=rq_connection).delete(remove_from_queue=True)
        except Exception:
            pass
