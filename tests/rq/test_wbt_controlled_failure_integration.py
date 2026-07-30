from __future__ import annotations

import uuid

import pytest
import redis
from rq import Queue, SimpleWorker, get_current_job
from rq.job import Job
from rq.registry import (
    CanceledJobRegistry,
    DeferredJobRegistry,
    FailedJobRegistry,
)

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
import wepppy.rq.job_info as job_info_module
from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.core.watershed_errors import (
    WATERSHED_BOUNDARY_TOUCH_MESSAGE,
    WatershedBoundaryTouchesEdgeError,
)
from wepppy.rq.project_rq import _cancel_deferred_job
from wepppy.rq.rq_worker import WepppyRqWorker
from wepppy.rq.job_info import get_wepppy_rq_job_info

pytestmark = pytest.mark.integration


def _noop_job() -> None:
    return None


def _controlled_boundary_failure_job() -> None:
    job = get_current_job()
    assert job is not None
    error_id = "integration-controlled-error"
    job.meta["error"] = {
        "code": "watershed_boundary_touches_dem_edge",
        "message": WATERSHED_BOUNDARY_TOUCH_MESSAGE,
        "details": {"edge_hillslope_ids": [1, 3]},
    }
    job.meta["error_id"] = error_id
    job.save_meta()
    for dependent_id in job.dependent_ids:
        dependent = Job.fetch(dependent_id, connection=job.connection)
        _cancel_deferred_job(dependent)
    raise WatershedBoundaryTouchesEdgeError([3, 1, 3])


class _InlineWepppyWorker(WepppyRqWorker, SimpleWorker):
    pass


@pytest.fixture
def rq_connection():
    connection = redis.StrictRedis(**redis_connection_kwargs(RedisDB.RQ))
    try:
        connection.ping()
    except redis.RedisError as exc:
        pytest.skip(f"compose Redis is unavailable: {exc}")
    return connection


def test_cancel_deferred_job_cleans_registry_and_dependency_sets(
    rq_connection,
) -> None:
    queue_name = f"surf14a-cancel-{uuid.uuid4().hex}"
    queue = Queue(queue_name, connection=rq_connection)
    parent = queue.enqueue(_noop_job)
    dependent = queue.enqueue(_noop_job, depends_on=parent)
    deferred = DeferredJobRegistry(queue_name, connection=rq_connection)

    try:
        assert dependent.id in deferred.get_job_ids()
        assert dependent.id in parent.dependent_ids

        _cancel_deferred_job(dependent)
        dependent.refresh()
        refreshed_parent = Job.fetch(parent.id, connection=rq_connection)

        assert dependent.get_status(refresh=True) == "canceled"
        assert dependent.id not in deferred.get_job_ids()
        assert dependent.dependency_ids == []
        assert dependent.id not in refreshed_parent.dependent_ids
        assert dependent.id in CanceledJobRegistry(
            queue_name,
            connection=rq_connection,
        ).get_job_ids()
    finally:
        for candidate in (dependent, parent):
            try:
                candidate.delete(remove_from_queue=True)
            except Exception:
                pass
        queue.delete(delete_jobs=True)


def test_worker_retains_only_sanitized_controlled_failure(
    rq_connection,
) -> None:
    queue_name = f"surf14a-worker-{uuid.uuid4().hex}"
    queue = Queue(queue_name, connection=rq_connection)
    job = queue.enqueue(_controlled_boundary_failure_job)
    worker = _InlineWepppyWorker(
        [queue],
        connection=rq_connection,
        name=f"surf14a-inline-{uuid.uuid4().hex}",
    )

    try:
        worker.work(burst=True, logging_level="WARNING")
        stored = Job.fetch(job.id, connection=rq_connection)
        retained = " ".join(
            [
                str(stored.meta.get("exc_string") or ""),
                str(stored.exc_info or ""),
            ]
        )

        assert stored.get_status(refresh=True) == "failed"
        assert stored.meta["error_id"] == "integration-controlled-error"
        assert stored.meta["exc_string"] == WATERSHED_BOUNDARY_TOUCH_MESSAGE
        assert WATERSHED_BOUNDARY_TOUCH_MESSAGE in retained
        assert "Traceback" not in retained
        assert __file__ not in retained
        assert stored.id in FailedJobRegistry(
            queue_name,
            connection=rq_connection,
        ).get_job_ids()
    finally:
        try:
            job.delete(remove_from_queue=True)
        except Exception:
            pass
        queue.delete(delete_jobs=True)


def test_real_tree_http_payload_and_retry_are_terminal_and_sanitized(
    rq_connection,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(job_info_module.redis, "Redis", redis.StrictRedis)
    queue_name = f"surf14a-tree-{uuid.uuid4().hex}"
    queue = Queue(queue_name, connection=rq_connection)
    root = queue.enqueue(_noop_job, meta={"runid": "integration-run"})
    child = queue.enqueue(
        _controlled_boundary_failure_job,
        meta={"runid": "integration-run"},
    )
    abstraction = queue.enqueue(_noop_job, depends_on=child)
    root.meta["jobs:0,func:build_subcatchments_rq"] = child.id
    root.meta["jobs:1,func:abstract_watershed_rq"] = abstraction.id
    root.save_meta()
    worker = _InlineWepppyWorker(
        [queue],
        connection=rq_connection,
        name=f"surf14a-tree-worker-{uuid.uuid4().hex}",
    )

    retry_build: Job | None = None
    retry_abstraction: Job | None = None
    try:
        with caplog.at_level("ERROR", logger="rq.worker"):
            worker.work(burst=True, logging_level="WARNING")

        stored_abstraction = Job.fetch(
            abstraction.id,
            connection=rq_connection,
        )
        assert stored_abstraction.get_status(refresh=True) == "canceled"
        assert abstraction.id not in DeferredJobRegistry(
            queue_name,
            connection=rq_connection,
        ).get_job_ids()

        payload = get_wepppy_rq_job_info(root.id)
        serialized = str(payload)
        assert payload["status"] == "failed"
        assert payload["error_id"] == "integration-controlled-error"
        assert payload["error"]["message"] == WATERSHED_BOUNDARY_TOUCH_MESSAGE
        assert payload["exc_info"] is None
        assert "Traceback" not in serialized
        assert __file__ not in serialized
        assert payload["children"]["1"][0]["status"] == "canceled"
        controlled_logs = [
            record
            for record in caplog.records
            if record.getMessage().startswith("Controlled RQ failure")
        ]
        assert len(controlled_logs) == 1
        assert controlled_logs[0].error_id == "integration-controlled-error"
        assert controlled_logs[0].runid == "integration-run"
        assert controlled_logs[0].edge_hillslope_ids == [1, 3]
        assert "Traceback" not in controlled_logs[0].getMessage()
        assert __file__ not in controlled_logs[0].getMessage()

        with TestClient(rq_engine.app) as client:
            response = client.get(f"/api/jobinfo/{root.id}")
        assert response.status_code == 200
        assert response.json() == payload
        assert "Traceback" not in response.text
        assert __file__ not in response.text

        retry_build = queue.enqueue(_noop_job)
        retry_abstraction = queue.enqueue(_noop_job, depends_on=retry_build)
        worker.work(burst=True, logging_level="WARNING")
        assert retry_build.get_status(refresh=True) == "finished"
        assert retry_abstraction.get_status(refresh=True) == "finished"
        assert DeferredJobRegistry(
            queue_name,
            connection=rq_connection,
        ).get_job_ids() == []
    finally:
        for candidate in (
            retry_abstraction,
            retry_build,
            abstraction,
            child,
            root,
        ):
            if candidate is None:
                continue
            try:
                candidate.delete(remove_from_queue=True)
            except Exception:
                pass
        queue.delete(delete_jobs=True)
