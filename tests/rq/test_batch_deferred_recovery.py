from __future__ import annotations

from types import SimpleNamespace
import uuid

import pytest
import redis
from rq import Queue
from rq.job import Dependency, Job, JobStatus
from rq.registry import DeferredJobRegistry

from wepppy.rq import batch_rq
from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.rq.job_dependencies import failure_tolerant_depends_on
from wepppy.rq.omni_rq import _finalize_omni_scenarios_rq, run_omni_scenarios_rq


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
    omni_receipt = queue.enqueue(
        _finalize_omni_scenarios_rq,
        runid,
        depends_on=failure_tolerant_depends_on(child),
        meta={"runid": runid},
    )
    batch_finalizer = queue.enqueue(
        batch_rq._final_batch_complete_rq,
        batch_name,
        depends_on=failure_tolerant_depends_on(omni_receipt),
        meta={"runid": batch_name},
    )
    root.meta["jobs:0,func:run_omni_scenarios_rq"] = child.id
    child.meta["jobs:3,func:_finalize_omni_scenarios_rq"] = omni_receipt.id
    child.save_meta()
    root.meta["jobs:1,func:_final_batch_complete_rq"] = batch_finalizer.id
    root.save_meta()
    queue.remove(root)
    root.set_status("failed")
    monkeypatch.setattr(
        batch_rq.BatchRunner,
        "getInstanceFromBatchName",
        lambda _name: SimpleNamespace(
            rq_job_ids={
                "run_batch_rq": root.id,
                "final_batch_complete_rq": batch_finalizer.id,
            }
        ),
    )

    try:
        conflicts = batch_rq.reconcile_deferred_batch_jobs(
            batch_name,
            redis_conn=rq_connection,
        )

        child.refresh()
        omni_receipt.refresh()
        batch_finalizer.refresh()
        assert conflicts == []
        assert child.get_status(refresh=True) == "canceled"
        assert omni_receipt.get_status(refresh=True) == "canceled"
        assert batch_finalizer.get_status(refresh=True) == "canceled"
        deferred_ids = DeferredJobRegistry("batch", connection=rq_connection).get_job_ids()
        assert {child.id, omni_receipt.id, batch_finalizer.id}.isdisjoint(deferred_ids)
    finally:
        for candidate in (batch_finalizer, omni_receipt, child, root):
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
