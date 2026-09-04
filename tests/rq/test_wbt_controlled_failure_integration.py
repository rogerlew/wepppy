from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
import uuid

import pytest
import redis
from rq import Queue, SimpleWorker, get_current_job
from rq.exceptions import NoSuchJobError
from rq.job import Dependency, Job
from rq.registry import (
    CanceledJobRegistry,
    DeferredJobRegistry,
    FailedJobRegistry,
)

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
import wepppy.rq.job_info as job_info_module
import wepppy.rq.job_dependencies as job_dependencies_module
import wepppy.rq.project_rq as project_rq
import wepppy.rq.wepp_rq_stage_prep as wepp_stage_prep
from wepppy.topo.watershed_abstraction.slope_file import clip_slope_file_length
from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.core.watershed_errors import (
    WATERSHED_BOUNDARY_TOUCH_MESSAGE,
    WatershedBoundaryTouchesEdgeError,
)
from wepppy.rq.project_rq import _cancel_deferred_job
from wepppy.rq.job_dependencies import reconcile_deferred_workflow
from wepppy.rq.rq_worker import WepppyRqWorker
from wepppy.rq.job_info import get_wepppy_rq_job_info

pytestmark = pytest.mark.integration


def _noop_job() -> None:
    return None


def _fail_required_prerequisite() -> None:
    raise RuntimeError("required prerequisite failed")


def _must_not_execute_after_failure() -> None:
    raise AssertionError("strict dependent executed after prerequisite failure")


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


def _serial_policy_build_job(
    runid: str,
    _updates: dict,
    boundary_policy: dict,
    _abstract_after_build: bool,
) -> None:
    job = get_current_job()
    assert job is not None
    policy = boundary_policy["effective_policy"]
    event_key = f"surf14a:serial-events:{runid}"
    readiness_key = f"surf14a:serial-readiness:{runid}"
    job.connection.rpush(event_key, f"build:{policy}")
    if policy == "error":
        job.connection.delete(readiness_key)
        project_rq._cancel_policy_dependents(job)
        raise RuntimeError("controlled serial policy failure")
    job.connection.rpush(event_key, "abstract:warn")
    job.connection.set(readiness_key, "warn-ready")


def _serial_policy_abstract_job(
    runid: str,
    _mutation_already_completed: bool,
) -> None:
    return None


class _InlineWepppyWorker(WepppyRqWorker, SimpleWorker):
    pass


class _PipelineExecuteFault:
    def __init__(
        self,
        pipeline,
        *,
        commit: bool,
        error: Exception,
        before_error=None,
    ) -> None:
        self._pipeline = pipeline
        self._commit = commit
        self._error = error
        self._before_error = before_error

    def __getattr__(self, name):
        return getattr(self._pipeline, name)

    def execute(self):
        if self._commit:
            self._pipeline.execute()
        if self._before_error is not None:
            self._before_error()
        raise self._error


@pytest.fixture
def rq_connection():
    connection = redis.StrictRedis(**redis_connection_kwargs(RedisDB.RQ))
    try:
        connection.ping()
    except redis.RedisError as exc:
        pytest.skip(f"compose Redis is unavailable: {exc}")
    return connection


def test_real_rq_strict_dependency_never_executes_after_failure(
    rq_connection,
) -> None:
    queue = Queue(f"strict-dependency-{uuid.uuid4().hex}", connection=rq_connection)
    parent = queue.enqueue(_fail_required_prerequisite)
    dependent = queue.enqueue(_must_not_execute_after_failure, depends_on=parent)
    try:
        worker = _InlineWepppyWorker([queue], connection=rq_connection)
        worker.work(burst=True, logging_level="WARNING")

        assert parent.get_status(refresh=True) == "failed"
        assert dependent.get_status(refresh=True) == "deferred"
        assert dependent.started_at is None
    finally:
        dependent.cancel(enqueue_dependents=False)
        dependent.delete()
        parent.delete()
        queue.delete(delete_jobs=True)


def test_mofe_clipping_prep_failure_is_visible_and_blocks_downstream(
    rq_connection,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(job_info_module.redis, "Redis", redis.StrictRedis)
    runid = "mofe-clipping-failure"
    wd = tmp_path / runid
    (wd / "watershed").mkdir(parents=True)
    (wd / "soils").mkdir()
    (wd / "landuse").mkdir()
    malformed = wd / "watershed" / "malformed.mofe.slp"
    destination = wd / "prior.slp"
    malformed.write_text("97.5\n1\nbogus 80\n2 100\n0, 0.1 1, 0.2\n", encoding="utf-8")
    destination.write_text("prior destination\n", encoding="utf-8")

    class _FailingWepp:
        def _prep_multi_ofe(self, _translator) -> None:
            clip_slope_file_length(str(malformed), str(destination), 60.0)

    monkeypatch.setattr(wepp_stage_prep, "get_wd", lambda _runid: str(wd))
    monkeypatch.setattr(wepp_stage_prep.Wepp, "getInstance", lambda _wd: _FailingWepp())
    monkeypatch.setattr(
        wepp_stage_prep.Watershed,
        "getInstance",
        lambda _wd: SimpleNamespace(translator_factory=lambda: object()),
    )

    queue_name = f"mofe-clipping-failure-{uuid.uuid4().hex}"
    queue = Queue(queue_name, connection=rq_connection)
    root = queue.enqueue(_noop_job, meta={"runid": runid})
    prep = queue.enqueue(wepp_stage_prep._prep_multi_ofe_rq, runid, depends_on=root)
    downstream = queue.enqueue(_must_not_execute_after_failure, depends_on=prep)
    root.meta["jobs:0,func:_prep_multi_ofe_rq"] = prep.id
    root.meta["jobs:1,func:_run_hillslopes_rq"] = downstream.id
    root.save_meta()

    try:
        worker = _InlineWepppyWorker([queue], connection=rq_connection)
        worker.work(burst=True, logging_level="WARNING")

        prep.refresh()
        downstream.refresh()
        payload = get_wepppy_rq_job_info(root.id)
        prep_payload = payload["children"]["0"][0]
        assert payload["status"] == "failed"
        assert prep.get_status(refresh=True) == "failed"
        assert "invalid geometry header" in str(prep_payload["exc_info"])
        assert downstream.get_status(refresh=True) == "deferred"
        assert downstream.started_at is None
        assert destination.read_text(encoding="utf-8") == "prior destination\n"
        assert not list(wd.glob(".prior.slp.*.tmp"))
    finally:
        for candidate in (downstream, prep, root):
            try:
                candidate.delete(remove_from_queue=True)
            except Exception:
                pass
        queue.delete(delete_jobs=True)


@pytest.mark.parametrize("register_dependent_after_failure", [False, True])
def test_real_rq_tolerant_dependency_releases_for_both_registration_orders(
    rq_connection,
    register_dependent_after_failure: bool,
) -> None:
    queue = Queue(f"tolerant-dependency-{uuid.uuid4().hex}", connection=rq_connection)
    parent = queue.enqueue(_fail_required_prerequisite)
    dependent: Job | None = None
    try:
        worker = _InlineWepppyWorker([queue], connection=rq_connection)
        if register_dependent_after_failure:
            worker.work(burst=True, logging_level="WARNING")
            assert parent.get_status(refresh=True) == "failed"

        dependent = queue.enqueue(
            _noop_job,
            depends_on=Dependency(jobs=[parent], allow_failure=True),
        )
        if register_dependent_after_failure:
            job_dependencies_module.release_deferred_job_if_ready(queue, dependent)

        worker.work(burst=True, logging_level="WARNING")

        assert parent.get_status(refresh=True) == "failed"
        assert dependent.get_status(refresh=True) == "finished"
    finally:
        if dependent is not None:
            dependent.delete()
        parent.delete()
        queue.delete(delete_jobs=True)


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


def test_reconcile_deferred_workflow_cancels_and_detaches_complete_graph(
    rq_connection,
) -> None:
    queue_name = f"deferred-retry-{uuid.uuid4().hex}"
    queue = Queue(queue_name, connection=rq_connection)
    parent = queue.enqueue(_noop_job, meta={"runid": "run-1"})
    dependent = queue.enqueue(
        _noop_job,
        depends_on=parent,
        meta={"runid": "run-1"},
    )
    parent.set_status("failed")

    try:
        result = reconcile_deferred_workflow(
            dependent.id,
            connection=rq_connection,
            association=lambda job: job.meta.get("runid") == "run-1",
            root_association=lambda job: job.meta.get("runid") == "run-1",
        )

        dependent.refresh()
        refreshed_parent = Job.fetch(parent.id, connection=rq_connection)
        assert result.state == "canceled"
        assert dependent.get_status(refresh=True) == "canceled"
        assert dependent.id not in DeferredJobRegistry(
            queue_name,
            connection=rq_connection,
        ).get_job_ids()
        assert dependent.dependency_ids == []
        assert dependent.dependent_ids == []
        assert dependent.id not in refreshed_parent.dependent_ids
    finally:
        for candidate in (dependent, parent):
            try:
                candidate.delete(remove_from_queue=True)
            except Exception:
                pass
        queue.delete(delete_jobs=True)


def test_reconcile_deferred_workflow_follows_serialized_metadata_links(
    rq_connection,
) -> None:
    queue_name = f"deferred-meta-retry-{uuid.uuid4().hex}"
    queue = Queue(queue_name, connection=rq_connection)
    root = queue.enqueue(_noop_job, meta={"runid": "run-meta"})
    child = queue.enqueue(_noop_job, meta={"runid": "run-meta"})
    root.meta["jobs:0,func:child"] = child.id
    root.save_meta()
    root.set_status("failed")
    child.set_status("deferred")
    DeferredJobRegistry(queue_name, connection=rq_connection).add(child)

    try:
        result = reconcile_deferred_workflow(
            root.id,
            connection=rq_connection,
            association=lambda job: job.meta.get("runid") == "run-meta",
            root_association=lambda job: job.meta.get("runid") == "run-meta",
        )

        child.refresh()
        assert result.state == "canceled"
        assert result.job_ids == (child.id,)
        assert child.get_status(refresh=True) == "canceled"
        assert child.id not in DeferredJobRegistry(
            queue_name,
            connection=rq_connection,
        ).get_job_ids()
    finally:
        for candidate in (child, root):
            try:
                candidate.delete(remove_from_queue=True)
            except Exception:
                pass
        queue.delete(delete_jobs=True)


def test_reconcile_deferred_workflow_stops_at_external_serialization_edge(
    rq_connection,
) -> None:
    queue_name = f"wbt-root-boundary-{uuid.uuid4().hex}"
    queue = Queue(queue_name, connection=rq_connection)
    prior_build = queue.enqueue(
        _noop_job,
        meta={"runid": "run-wbt", "wbt_subcatchment_admission_root": "root-1"},
    )
    root = queue.enqueue(_noop_job, meta={"runid": "run-wbt", "role": "root"})
    build = queue.enqueue(
        _noop_job,
        depends_on=prior_build,
        meta={
            "runid": "run-wbt",
            "wbt_subcatchment_admission_root": root.id,
            "wbt_subcatchment_admission_previous": prior_build.id,
        },
    )
    root.meta["jobs:0,func:build_subcatchments_rq"] = build.id
    root.save_meta()
    root.set_status("failed")

    try:
        result = reconcile_deferred_workflow(
            root.id,
            connection=rq_connection,
            association=lambda job: job.meta.get("runid") == "run-wbt",
            root_association=lambda job: job.meta.get("role") == "root",
            excluded_dependency_job_ids=lambda job: (
                job.meta.get("wbt_subcatchment_admission_previous"),
            ),
        )

        assert result.state == "canceled"
        assert build.get_status(refresh=True) == "canceled"
        assert prior_build.get_status(refresh=True) == "queued"
        assert prior_build.id in queue.get_job_ids()
    finally:
        for candidate in (build, root, prior_build):
            try:
                candidate.delete(remove_from_queue=True)
            except Exception:
                pass
        queue.delete(delete_jobs=True)


def test_reconcile_deferred_workflow_rejects_allowed_descendant_as_receipt_root(
    rq_connection,
) -> None:
    queue_name = f"deferred-child-receipt-{uuid.uuid4().hex}"
    queue = Queue(queue_name, connection=rq_connection)
    root = queue.enqueue(_noop_job, meta={"runid": "root-run", "role": "root"})
    child = queue.enqueue(
        _noop_job,
        depends_on=root,
        meta={"runid": "root-run", "role": "child"},
    )
    root.set_status("failed")

    try:
        result = reconcile_deferred_workflow(
            child.id,
            connection=rq_connection,
            association=lambda job: job.meta.get("runid") == "root-run",
            root_association=lambda job: job.meta.get("role") == "root",
        )

        assert result.state == "mismatch"
        assert child.get_status(refresh=True) == "deferred"
        assert child.id in DeferredJobRegistry(
            queue_name, connection=rq_connection
        ).get_job_ids()
    finally:
        for candidate in (child, root):
            try:
                candidate.delete(remove_from_queue=True)
            except Exception:
                pass
        queue.delete(delete_jobs=True)


def test_reconcile_deferred_workflow_observes_deferred_to_queued_race(
    rq_connection, monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue_name = f"deferred-promotion-{uuid.uuid4().hex}"
    queue = Queue(queue_name, connection=rq_connection)
    root = queue.enqueue(_noop_job, meta={"runid": "race-run"})
    child = queue.enqueue(_noop_job, meta={"runid": "race-run"})
    root.meta["jobs:0,func:child"] = child.id
    root.save_meta()
    root.set_status("failed")
    child.set_status("deferred")
    DeferredJobRegistry(queue_name, connection=rq_connection).add(child)
    original_snapshot = job_dependencies_module._snapshot_linked_job_ids
    promoted = False

    def _promoting_snapshot(pipeline, job):
        nonlocal promoted
        if not promoted:
            promoted = True
            child.set_status("queued")
        return original_snapshot(pipeline, job)

    monkeypatch.setattr(
        job_dependencies_module, "_snapshot_linked_job_ids", _promoting_snapshot
    )
    try:
        result = reconcile_deferred_workflow(
            root.id,
            connection=rq_connection,
            association=lambda job: job.meta.get("runid") == "race-run",
            root_association=lambda job: job.meta.get("runid") == "race-run",
        )
        assert result.state == "active"
        assert child.get_status(refresh=True) == "queued"
    finally:
        for candidate in (child, root):
            try:
                candidate.delete(remove_from_queue=True)
            except Exception:
                pass
        queue.delete(delete_jobs=True)


def test_reconcile_deferred_workflow_contains_association_change_after_watched_fetch(
    rq_connection, monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue_name = f"deferred-association-race-{uuid.uuid4().hex}"
    queue = Queue(queue_name, connection=rq_connection)
    child = queue.enqueue(_noop_job, meta={"runid": "owned-run"})
    child.set_status("deferred")
    DeferredJobRegistry(queue_name, connection=rq_connection).add(child)
    original_fetch = job_dependencies_module.Job.fetch
    changed = False

    def fetch_then_change(job_id, connection):
        nonlocal changed
        watched_snapshot = original_fetch(job_id, connection=connection)
        if not changed and str(job_id) == child.id:
            changed = True
            attacker = original_fetch(job_id, connection=connection)
            attacker.meta["runid"] = "other-run"
            attacker.save_meta()
        return watched_snapshot

    monkeypatch.setattr(job_dependencies_module.Job, "fetch", fetch_then_change)
    try:
        result = reconcile_deferred_workflow(
            child.id,
            connection=rq_connection,
            association=lambda job: job.meta.get("runid") == "owned-run",
            root_association=lambda job: job.meta.get("runid") == "owned-run",
        )

        child.refresh()
        assert result.state == "mismatch"
        assert child.get_status(refresh=True) == "deferred"
    finally:
        try:
            child.delete(remove_from_queue=True)
        except Exception:
            pass
        queue.delete(delete_jobs=True)


def test_reconcile_deferred_workflow_retries_root_created_after_missing_fetch(
    rq_connection, monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue_name = f"deferred-missing-race-{uuid.uuid4().hex}"
    queue = Queue(queue_name, connection=rq_connection)
    root_id = f"late-{uuid.uuid4().hex}"
    original_fetch = job_dependencies_module.Job.fetch
    injected = False

    def missing_then_create(job_id, connection):
        nonlocal injected
        if not injected and str(job_id) == root_id:
            injected = True
            queue.enqueue(_noop_job, job_id=root_id, meta={"runid": "late-run"})
            raise NoSuchJobError
        return original_fetch(job_id, connection=connection)

    monkeypatch.setattr(job_dependencies_module.Job, "fetch", missing_then_create)
    try:
        result = reconcile_deferred_workflow(
            root_id,
            connection=rq_connection,
            association=lambda job: job.meta.get("runid") == "late-run",
            root_association=lambda job: job.meta.get("runid") == "late-run",
        )

        assert result.state == "active"
        assert result.job_ids == (root_id,)
    finally:
        try:
            original_fetch(root_id, connection=rq_connection).delete(remove_from_queue=True)
        except NoSuchJobError:
            pass
        queue.delete(delete_jobs=True)


@pytest.mark.parametrize("active_status", ["queued", "started", "scheduled"])
def test_reconcile_deferred_workflow_classifies_every_real_active_status(
    rq_connection,
    active_status: str,
) -> None:
    queue_name = f"deferred-active-{uuid.uuid4().hex}"
    queue = Queue(queue_name, connection=rq_connection)
    job = queue.enqueue(_noop_job, meta={"runid": "active-run"})
    job.set_status(active_status)
    try:
        result = reconcile_deferred_workflow(
            job.id,
            connection=rq_connection,
            association=lambda candidate: candidate.meta.get("runid") == "active-run",
            root_association=lambda candidate: candidate.meta.get("runid") == "active-run",
        )

        assert result.state == "active"
        assert result.job_ids == (job.id,)
        assert job.get_status(refresh=True) == active_status
    finally:
        try:
            job.delete(remove_from_queue=True)
        except Exception:
            pass
        queue.delete(delete_jobs=True)


def test_reconcile_deferred_workflow_rejects_inserted_hostile_edge(
    rq_connection, monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue_name = f"deferred-edge-race-{uuid.uuid4().hex}"
    queue = Queue(queue_name, connection=rq_connection)
    root = queue.enqueue(_noop_job, meta={"runid": "owned-run"})
    child = queue.enqueue(_noop_job, meta={"runid": "owned-run"})
    hostile = queue.enqueue(_noop_job, meta={"runid": "other-run"})
    root.meta["jobs:0,func:child"] = child.id
    root.save_meta()
    root.set_status("failed")
    child.set_status("deferred")
    DeferredJobRegistry(queue_name, connection=rq_connection).add(child)
    original_snapshot = job_dependencies_module._snapshot_linked_job_ids
    inserted = False

    def _inserting_snapshot(pipeline, job):
        nonlocal inserted
        if not inserted:
            inserted = True
            root.meta["jobs:1,func:hostile"] = hostile.id
            root.save_meta()
        return original_snapshot(pipeline, job)

    monkeypatch.setattr(
        job_dependencies_module, "_snapshot_linked_job_ids", _inserting_snapshot
    )
    try:
        result = reconcile_deferred_workflow(
            root.id,
            connection=rq_connection,
            association=lambda job: job.meta.get("runid") == "owned-run",
            root_association=lambda job: job.meta.get("runid") == "owned-run",
        )
        assert result.state == "mismatch"
        assert child.get_status(refresh=True) == "deferred"
    finally:
        for candidate in (hostile, child, root):
            try:
                candidate.delete(remove_from_queue=True)
            except Exception:
                pass
        queue.delete(delete_jobs=True)


@pytest.mark.parametrize("promoted_status", ["queued", "started"])
def test_reconcile_deferred_workflow_watch_aborts_late_promotion(
    rq_connection,
    monkeypatch: pytest.MonkeyPatch,
    promoted_status: str,
) -> None:
    queue_name = f"deferred-watch-{uuid.uuid4().hex}"
    queue = Queue(queue_name, connection=rq_connection)
    parent = queue.enqueue(_noop_job, meta={"runid": "watch-run"})
    child = queue.enqueue(
        _noop_job, depends_on=parent, meta={"runid": "watch-run"}
    )
    parent.set_status("failed")
    original_pipeline_factory = rq_connection.pipeline
    promoted = False

    class _PromotionPipeline:
        def __init__(self, pipeline):
            self._pipeline = pipeline

        def __enter__(self):
            self._pipeline.__enter__()
            return self

        def __exit__(self, exc_type, exc, tb):
            return self._pipeline.__exit__(exc_type, exc, tb)

        def __getattr__(self, name):
            return getattr(self._pipeline, name)

        def execute(self):
            nonlocal promoted
            if not promoted:
                promoted = True
                child.set_status(promoted_status)
            return self._pipeline.execute()

    monkeypatch.setattr(
        rq_connection,
        "pipeline",
        lambda *args, **kwargs: _PromotionPipeline(
            original_pipeline_factory(*args, **kwargs)
        ),
    )
    try:
        result = reconcile_deferred_workflow(
            child.id,
            connection=rq_connection,
            association=lambda job: job.meta.get("runid") == "watch-run",
            root_association=lambda job: job.meta.get("runid") == "watch-run",
        )
        assert result.state == "active"
        assert child.get_status(refresh=True) == promoted_status
    finally:
        for candidate in (child, parent):
            try:
                candidate.delete(remove_from_queue=True)
            except Exception:
                pass
        queue.delete(delete_jobs=True)


def test_reconcile_deferred_workflow_cancels_multilevel_metadata_graph(
    rq_connection,
) -> None:
    queue_name = f"deferred-multilevel-{uuid.uuid4().hex}"
    queue = Queue(queue_name, connection=rq_connection)
    root = queue.enqueue(_noop_job, meta={"runid": "tree-run"})
    middle = queue.enqueue(_noop_job, meta={"runid": "tree-run"})
    leaf = queue.enqueue(_noop_job, meta={"runid": "tree-run"})
    root.meta["jobs:0,func:middle"] = middle.id
    middle.meta["jobs:0,func:leaf"] = leaf.id
    root.save_meta()
    middle.save_meta()
    root.set_status("failed")
    for candidate in (middle, leaf):
        candidate.set_status("deferred")
        DeferredJobRegistry(queue_name, connection=rq_connection).add(candidate)
    try:
        result = reconcile_deferred_workflow(
            root.id,
            connection=rq_connection,
            association=lambda job: job.meta.get("runid") == "tree-run",
            root_association=lambda job: job.meta.get("runid") == "tree-run",
        )
        assert result.state == "canceled"
        assert set(result.job_ids) == {middle.id, leaf.id}
        assert middle.get_status(refresh=True) == "canceled"
        assert leaf.get_status(refresh=True) == "canceled"
    finally:
        for candidate in (leaf, middle, root):
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


@pytest.mark.parametrize(
    ("policies", "expected_events", "expected_readiness"),
    [
        (
            ("error", "warn"),
            ["build:error", "build:warn", "abstract:warn"],
            b"warn-ready",
        ),
        (
            ("warn", "error"),
            ["build:warn", "abstract:warn", "build:error"],
            None,
        ),
    ],
)
def test_same_run_policy_trees_serialize_through_abstraction(
    rq_connection,
    monkeypatch: pytest.MonkeyPatch,
    policies: tuple[str, str],
    expected_events: list[str],
    expected_readiness: bytes | None,
) -> None:
    queue_name = f"surf14a-serial-{uuid.uuid4().hex}"
    runid = f"serial-{uuid.uuid4().hex}"
    queue = Queue(queue_name, connection=rq_connection)
    event_key = f"surf14a:serial-events:{runid}"
    readiness_key = f"surf14a:serial-readiness:{runid}"
    monkeypatch.setattr(
        project_rq,
        "build_subcatchments_rq",
        _serial_policy_build_job,
    )
    tail_key = project_rq._subcatchment_tail_key(runid)

    jobs: list[Job] = []
    parents: list[Job] = []
    try:
        for policy in policies:
            parent = queue.create_job(
                _noop_job,
                job_id=f"parent-{uuid.uuid4().hex}",
                meta={},
            )
            parent.save()
            parents.append(parent)
            argument = {
                    "schema_version": 1,
                    "effective_policy": policy,
                    "source": "user_preference",
                }
            build, receipt = project_rq._enqueue_serial_subcatchment_tree(
                rq_connection,
                queue,
                runid=runid,
                updates={},
                boundary_policy=argument,
                child_meta=None,
                receipt_meta={},
                parent_job=parent,
            )
            assert len(build.id) == 36 and build.id.count("-") == 4
            assert len(receipt.id) == 36 and receipt.id.count("-") == 4
            assert parent.meta["jobs:0,func:build_subcatchments_rq"] == build.id
            assert (
                parent.meta["jobs:1,func:abstract_watershed_rq"]
                == receipt.id
            )
            assert parent.meta[
                project_rq._WBT_ADMISSION_FINGERPRINT_KEY
            ] == build.meta[project_rq._WBT_ADMISSION_FINGERPRINT_KEY]
            assert receipt.id in build.dependent_ids
            jobs.extend((build, receipt))

        worker = _InlineWepppyWorker(
            [queue],
            connection=rq_connection,
            name=f"surf14a-serial-worker-{uuid.uuid4().hex}",
        )
        worker.work(burst=True, logging_level="WARNING")

        events = [
            value.decode("utf-8")
            for value in rq_connection.lrange(event_key, 0, -1)
        ]
        assert events == expected_events
        assert rq_connection.get(readiness_key) == expected_readiness
        assert queue.get_job_ids() == []
        assert DeferredJobRegistry(
            queue_name,
            connection=rq_connection,
        ).get_job_ids() == []

        statuses = [job.get_status(refresh=True) for job in jobs]
        if policies[0] == "error":
            assert statuses == ["failed", "canceled", "finished", "finished"]
        else:
            assert statuses == ["finished", "finished", "failed", "canceled"]
    finally:
        rq_connection.delete(
            event_key,
            readiness_key,
            tail_key,
        )
        for candidate in (*jobs, *parents):
            try:
                candidate.delete(remove_from_queue=True)
            except Exception:
                pass
        queue.delete(delete_jobs=True)


def test_retry_splices_canceled_tail_back_to_active_predecessor(
    rq_connection,
) -> None:
    queue_name = f"wbt-tail-splice-{uuid.uuid4().hex}"
    runid = f"tail-splice-{uuid.uuid4().hex}"
    queue = Queue(queue_name, connection=rq_connection)
    jobs: list[Job] = []
    parents: list[Job] = []

    def _tree() -> tuple[Job, Job, Job]:
        parent = queue.create_job(
            _noop_job,
            meta={"runid": runid, "role": "root"},
        )
        parent.save()
        build, receipt = project_rq._enqueue_serial_subcatchment_tree(
            rq_connection,
            queue,
            runid=runid,
            updates={},
            boundary_policy=None,
            child_meta={"runid": runid},
            receipt_meta={"runid": runid},
            parent_job=parent,
        )
        parents.append(parent)
        jobs.extend((build, receipt))
        return parent, build, receipt

    try:
        _parent_a, build_a, _receipt_a = _tree()
        parent_b, build_b, _receipt_b = _tree()
        assert build_b.get_status(refresh=True) == "deferred"
        assert {
            dependency_id.decode().removeprefix("rq:job:")
            if isinstance(dependency_id, bytes)
            else str(dependency_id).removeprefix("rq:job:")
            for dependency_id in build_b.dependency_ids
        } == {build_a.id}

        parent_b.set_status("failed")
        result = reconcile_deferred_workflow(
            parent_b.id,
            connection=rq_connection,
            association=lambda job: job.meta.get("runid") == runid,
            root_association=lambda job: job.meta.get("role") == "root",
            excluded_dependency_job_ids=lambda job: (
                job.meta.get(project_rq._WBT_ADMISSION_PREVIOUS_KEY),
            ),
        )
        assert result.state == "canceled"
        assert build_b.get_status(refresh=True) == "canceled"
        assert build_a.get_status(refresh=True) == "queued"

        _parent_c, build_c, _receipt_c = _tree()
        assert build_c.get_status(refresh=True) == "deferred"
        assert {
            dependency_id.decode().removeprefix("rq:job:")
            if isinstance(dependency_id, bytes)
            else str(dependency_id).removeprefix("rq:job:")
            for dependency_id in build_c.dependency_ids
        } == {build_a.id}
        assert build_c.meta[project_rq._WBT_ADMISSION_PREVIOUS_KEY] == build_a.id
    finally:
        rq_connection.delete(project_rq._subcatchment_tail_key(runid))
        for candidate in (*jobs, *parents):
            try:
                candidate.delete(remove_from_queue=True)
            except Exception:
                pass
        queue.delete(delete_jobs=True)


def test_complete_child_uses_snapshot_and_extended_nodir_lock(
    rq_connection,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    runid = f"serial-mutation-{uuid.uuid4().hex}"
    events: list[str] = []
    lock_ttls: list[int | None] = []

    class _Job:
        id = f"job-warn-{uuid.uuid4().hex}"
        connection = rq_connection
        dependent_ids: list[str] = []
        meta = {
            project_rq.WBT_BOUNDARY_POLICY_SNAPSHOT_KEY: {
                "schema_version": 1,
                "runid": runid,
                "actor_token_class": "user",
                "actor_user_id": 2,
                "config_policy": "warn",
                "effective_policy": "warn",
                "source": "user_preference",
            }
        }

        @staticmethod
        def save_meta() -> None:
            return None

    class _Watershed:
        delineation_backend_is_topaz = False
        delineation_backend_is_wbt = True
        wbt_boundary_touch_behavior = "warn"
        wbt_boundary_touch_config_behavior = "warn"
        edge_hillslopes = [7]
        subwta = str(tmp_path / "SUBWTA.ARC")
        logger = SimpleNamespace(warning=lambda *_args, **_kwargs: None)

        def __init__(self) -> None:
            self.ready = False

        def persist_wbt_boundary_touch_config_behavior(self) -> None:
            events.append("persist-policy")

        def build_subcatchments(self, *, boundary_touch_behavior=None) -> None:
            policy = str(boundary_touch_behavior)
            events.append(f"build:{policy}")
            self.ready = True

        def abstract_watershed(self) -> None:
            events.append("abstract:warn")

    watershed = _Watershed()

    @contextmanager
    def _maintenance_lock(
        _wd: str,
        _root: str,
        *,
        purpose: str,
        ttl_seconds: int | None = None,
    ):
        lock_ttls.append(ttl_seconds)
        yield

    monkeypatch.setattr(project_rq, "get_wd", lambda _runid: str(tmp_path))
    monkeypatch.setattr(project_rq, "get_current_job", lambda: _Job())
    monkeypatch.setattr(
        project_rq,
        "nodir_resolve",
        lambda *_args, **_kwargs: SimpleNamespace(form="dir"),
    )
    monkeypatch.setattr(project_rq, "nodir_maintenance_lock", _maintenance_lock)
    monkeypatch.setattr(project_rq, "clear_nodb_file_cache", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(project_rq, "wait_for_path", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(project_rq.StatusMessenger, "publish", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(project_rq.Watershed, "getInstance", lambda _wd: watershed)
    monkeypatch.setattr(
        project_rq.Watershed,
        "load_detached",
        lambda _wd, allow_nonexistent=True: SimpleNamespace(centroid=(-116.2, 43.6)),
    )

    tail_key = project_rq._subcatchment_tail_key(runid)
    try:
        rq_connection.set(tail_key, _Job.id)
        project_rq.build_subcatchments_rq(
            runid,
            {},
            {
                "schema_version": 1,
                "effective_policy": "warn",
                "source": "user_preference",
            },
            True,
        )

        assert events == ["persist-policy", "build:warn", "abstract:warn"]
        assert watershed.ready is True
        assert watershed.wbt_boundary_touch_behavior == "warn"
        assert watershed.wbt_boundary_touch_config_behavior == "warn"
        assert lock_ttls == [project_rq.WBT_SUBCATCHMENT_TREE_LOCK_TTL_SECONDS]
        assert project_rq.WBT_SUBCATCHMENT_TREE_LOCK_TTL_SECONDS > project_rq.TIMEOUT
        assert rq_connection.get(tail_key) == _Job.id.encode()
    finally:
        rq_connection.delete(tail_key)


def test_completion_receipt_releases_only_its_terminal_build_tail(
    rq_connection,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    queue_name = f"surf14a-receipt-tail-{uuid.uuid4().hex}"
    runid = f"receipt-tail-{uuid.uuid4().hex}"
    queue = Queue(queue_name, connection=rq_connection)
    build_id = f"build-{uuid.uuid4().hex}"
    receipt = queue.create_job(
        _noop_job,
        job_id=f"receipt-{uuid.uuid4().hex}",
        meta={project_rq._WBT_ADMISSION_BUILD_KEY: build_id},
    )
    receipt.save()
    tail_key = project_rq._subcatchment_tail_key(runid)
    monkeypatch.setattr(project_rq, "get_current_job", lambda: receipt)
    monkeypatch.setattr(project_rq, "get_wd", lambda _runid: str(tmp_path))
    monkeypatch.setattr(
        project_rq.StatusMessenger,
        "publish",
        lambda *_args, **_kwargs: None,
    )

    try:
        rq_connection.set(tail_key, build_id)
        project_rq.abstract_watershed_rq(runid, True)
        assert rq_connection.get(tail_key) is None

        newer_build_id = f"build-{uuid.uuid4().hex}"
        rq_connection.set(tail_key, newer_build_id)
        project_rq.abstract_watershed_rq(runid, True)
        assert rq_connection.get(tail_key) == newer_build_id.encode()
    finally:
        rq_connection.delete(tail_key)
        receipt.delete(remove_from_queue=True)
        queue.delete(delete_jobs=True)


def test_admission_discards_terminal_stale_tail(
    rq_connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue_name = f"surf14a-stale-tail-{uuid.uuid4().hex}"
    runid = f"stale-tail-{uuid.uuid4().hex}"
    queue = Queue(queue_name, connection=rq_connection)
    monkeypatch.setattr(
        project_rq,
        "build_subcatchments_rq",
        _serial_policy_build_job,
    )
    prior = queue.enqueue(
        _serial_policy_build_job,
        runid,
        {},
        {"effective_policy": "warn"},
        True,
        meta={project_rq._WBT_ADMISSION_ROOT_KEY: "prior-root"},
    )
    worker = _InlineWepppyWorker(
        [queue],
        connection=rq_connection,
        name=f"surf14a-stale-tail-worker-{uuid.uuid4().hex}",
    )
    worker.work(burst=True, logging_level="WARNING")
    assert prior.get_status(refresh=True) == "finished"

    tail_key = project_rq._subcatchment_tail_key(runid)
    rq_connection.set(tail_key, prior.id)
    parent = queue.create_job(
        _noop_job,
        job_id=f"parent-{uuid.uuid4().hex}",
        meta={},
    )
    parent.save()
    admitted: tuple[Job, Job] | None = None
    try:
        admitted = project_rq._enqueue_serial_subcatchment_tree(
            rq_connection,
            queue,
            runid=runid,
            updates={},
            boundary_policy={
                "schema_version": 1,
                "effective_policy": "warn",
                "source": "user_preference",
            },
            child_meta=None,
            receipt_meta={},
            parent_job=parent,
        )
        build, receipt = admitted

        assert build.dependency_ids == []
        assert build.get_status(refresh=True) == "queued"
        assert receipt.get_status(refresh=True) == "deferred"
        assert rq_connection.get(tail_key) == build.id.encode("utf-8")
    finally:
        rq_connection.delete(tail_key)
        candidates = (
            (*admitted, prior, parent)
            if admitted is not None
            else (prior, parent)
        )
        for candidate in candidates:
            try:
                candidate.delete(remove_from_queue=True)
            except Exception:
                pass
        queue.delete(delete_jobs=True)


def test_admission_rejects_nonterminal_tail_outside_execution_registries(
    rq_connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue_name = f"surf14a-orphan-tail-{uuid.uuid4().hex}"
    runid = f"orphan-tail-{uuid.uuid4().hex}"
    queue = Queue(queue_name, connection=rq_connection)
    monkeypatch.setattr(
        project_rq,
        "build_subcatchments_rq",
        _serial_policy_build_job,
    )
    prior = queue.create_job(
        _serial_policy_build_job,
        args=(runid, {}, {"effective_policy": "warn"}, True),
        job_id=f"orphan-{uuid.uuid4().hex}",
        meta={project_rq._WBT_ADMISSION_ROOT_KEY: "prior-root"},
    )
    prior.set_status(project_rq.JobStatus.STARTED)
    prior.save()
    parent = queue.create_job(
        _noop_job,
        job_id=f"parent-{uuid.uuid4().hex}",
        meta={"preserved": True},
    )
    parent.save()
    tail_key = project_rq._subcatchment_tail_key(runid)
    rq_connection.set(tail_key, prior.id)

    try:
        with pytest.raises(
            RuntimeError,
            match="outside every valid execution registry",
        ):
            project_rq._enqueue_serial_subcatchment_tree(
                rq_connection,
                queue,
                runid=runid,
                updates={},
                boundary_policy=None,
                child_meta=None,
                receipt_meta={},
                parent_job=parent,
            )
        parent.refresh()
        assert parent.meta == {"preserved": True}
        assert rq_connection.get(tail_key) == prior.id.encode()
        assert queue.get_job_ids() == []
        assert DeferredJobRegistry(
            queue_name,
            connection=rq_connection,
        ).get_job_ids() == []
    finally:
        rq_connection.delete(tail_key)
        for candidate in (prior, parent):
            candidate.delete(remove_from_queue=True)
        queue.delete(delete_jobs=True)


def test_atomic_admission_retries_watch_conflict_without_partial_state(
    rq_connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue_name = f"surf14a-watch-retry-{uuid.uuid4().hex}"
    runid = f"watch-retry-{uuid.uuid4().hex}"
    queue = Queue(queue_name, connection=rq_connection)
    parent = queue.create_job(
        _noop_job,
        job_id=f"parent-{uuid.uuid4().hex}",
        meta={},
    )
    parent.save()
    tail_key = project_rq._subcatchment_tail_key(runid)
    real_pipeline = rq_connection.pipeline
    attempts = 0

    def _pipeline(*args, **kwargs):
        nonlocal attempts
        pipeline = real_pipeline(*args, **kwargs)
        attempts += 1
        if attempts == 1:
            return _PipelineExecuteFault(
                pipeline,
                commit=False,
                error=redis.exceptions.WatchError(),
            )
        return pipeline

    monkeypatch.setattr(rq_connection, "pipeline", _pipeline)
    admitted: tuple[Job, Job] | None = None
    try:
        admitted = project_rq._enqueue_serial_subcatchment_tree(
            rq_connection,
            queue,
            runid=runid,
            updates={},
            boundary_policy=None,
            child_meta=None,
            receipt_meta={},
            parent_job=parent,
        )
        build, receipt = admitted
        assert attempts == 2
        assert rq_connection.get(tail_key) == build.id.encode()
        assert queue.get_job_ids() == [build.id]
        assert receipt.id in DeferredJobRegistry(
            queue_name,
            connection=rq_connection,
        ).get_job_ids()
    finally:
        monkeypatch.setattr(rq_connection, "pipeline", real_pipeline)
        rq_connection.delete(tail_key)
        for candidate in (*admitted, parent) if admitted else (parent,):
            try:
                candidate.delete(remove_from_queue=True)
            except Exception:
                pass
        queue.delete(delete_jobs=True)


def test_exact_tree_rejects_queued_build_dependency_residue(
    rq_connection,
) -> None:
    queue_name = f"surf14a-build-residue-{uuid.uuid4().hex}"
    runid = f"build-residue-{uuid.uuid4().hex}"
    queue = Queue(queue_name, connection=rq_connection)
    parent = queue.create_job(
        _noop_job,
        job_id=f"parent-{uuid.uuid4().hex}",
        meta={},
    )
    parent.save()
    tail_key = project_rq._subcatchment_tail_key(runid)
    admitted: tuple[Job, Job] | None = None
    try:
        admitted = project_rq._enqueue_serial_subcatchment_tree(
            rq_connection,
            queue,
            runid=runid,
            updates={},
            boundary_policy=None,
            child_meta=None,
            receipt_meta={},
            parent_job=parent,
        )
        build, _receipt = admitted
        rq_connection.sadd(build.dependencies_key, "stale-prior")
        parent.refresh()
        with pytest.raises(RuntimeError, match="prior dependency"):
            project_rq._enqueue_serial_subcatchment_tree(
                rq_connection,
                queue,
                runid=runid,
                updates={},
                boundary_policy=None,
                child_meta=None,
                receipt_meta={},
                parent_job=parent,
            )
    finally:
        rq_connection.delete(tail_key)
        for candidate in (*admitted, parent) if admitted else (parent,):
            try:
                candidate.delete(remove_from_queue=True)
            except Exception:
                pass
        queue.delete(delete_jobs=True)


def test_exact_tree_rejects_canceled_receipt_dependency_residue(
    rq_connection,
) -> None:
    queue_name = f"surf14a-receipt-residue-{uuid.uuid4().hex}"
    runid = f"receipt-residue-{uuid.uuid4().hex}"
    queue = Queue(queue_name, connection=rq_connection)
    parent = queue.create_job(
        _noop_job,
        job_id=f"parent-{uuid.uuid4().hex}",
        meta={},
    )
    parent.save()
    tail_key = project_rq._subcatchment_tail_key(runid)
    admitted: tuple[Job, Job] | None = None
    try:
        admitted = project_rq._enqueue_serial_subcatchment_tree(
            rq_connection,
            queue,
            runid=runid,
            updates={},
            boundary_policy=None,
            child_meta=None,
            receipt_meta={},
            parent_job=parent,
        )
        build, receipt = admitted
        project_rq._cancel_deferred_job(receipt)
        rq_connection.sadd(receipt.dependencies_key, build.id)
        rq_connection.sadd(build.dependents_key, receipt.id)
        parent.refresh()
        with pytest.raises(RuntimeError, match="stale completion-receipt link"):
            project_rq._enqueue_serial_subcatchment_tree(
                rq_connection,
                queue,
                runid=runid,
                updates={},
                boundary_policy=None,
                child_meta=None,
                receipt_meta={},
                parent_job=parent,
            )
    finally:
        rq_connection.delete(tail_key)
        for candidate in (*admitted, parent) if admitted else (parent,):
            try:
                candidate.delete(remove_from_queue=True)
            except Exception:
                pass
        queue.delete(delete_jobs=True)


def test_exact_tree_accepts_queued_build_in_intermediate_queue(
    rq_connection,
) -> None:
    queue_name = f"surf14a-intermediate-{uuid.uuid4().hex}"
    runid = f"intermediate-{uuid.uuid4().hex}"
    queue = Queue(queue_name, connection=rq_connection)
    parent = queue.create_job(
        _noop_job,
        job_id=f"parent-{uuid.uuid4().hex}",
        meta={},
    )
    parent.save()
    tail_key = project_rq._subcatchment_tail_key(runid)
    admitted: tuple[Job, Job] | None = None
    try:
        admitted = project_rq._enqueue_serial_subcatchment_tree(
            rq_connection,
            queue,
            runid=runid,
            updates={},
            boundary_policy=None,
            child_meta=None,
            receipt_meta={},
            parent_job=parent,
        )
        build, receipt = admitted
        assert rq_connection.lmove(
            queue.key,
            queue.intermediate_queue_key,
        ) == build.id.encode()
        parent.refresh()
        repeated = project_rq._enqueue_serial_subcatchment_tree(
            rq_connection,
            queue,
            runid=runid,
            updates={},
            boundary_policy=None,
            child_meta=None,
            receipt_meta={},
            parent_job=parent,
        )
        assert tuple(job.id for job in repeated) == (build.id, receipt.id)
    finally:
        rq_connection.delete(tail_key)
        if admitted is not None:
            rq_connection.lrem(
                queue.intermediate_queue_key,
                0,
                admitted[0].id,
            )
        for candidate in (*admitted, parent) if admitted else (parent,):
            try:
                candidate.delete(remove_from_queue=True)
            except Exception:
                pass
        queue.delete(delete_jobs=True)


def test_atomic_admission_reconciles_competing_exact_root_commit(
    rq_connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue_name = f"surf14a-watch-exact-{uuid.uuid4().hex}"
    runid = f"watch-exact-{uuid.uuid4().hex}"
    queue = Queue(queue_name, connection=rq_connection)
    parent = queue.create_job(
        _noop_job,
        job_id=f"parent-{uuid.uuid4().hex}",
        meta={"preserved": True},
    )
    parent.save()
    tail_key = project_rq._subcatchment_tail_key(runid)
    real_pipeline = rq_connection.pipeline
    competing: list[tuple[Job, Job]] = []
    injected = False

    def _commit_competing_tree() -> None:
        monkeypatch.setattr(rq_connection, "pipeline", real_pipeline)
        competing_parent = Job.fetch(parent.id, connection=rq_connection)
        competing.append(
            project_rq._enqueue_serial_subcatchment_tree(
                rq_connection,
                queue,
                runid=runid,
                updates={},
                boundary_policy=None,
                child_meta=None,
                receipt_meta={},
                parent_job=competing_parent,
            )
        )

    def _pipeline(*args, **kwargs):
        nonlocal injected
        pipeline = real_pipeline(*args, **kwargs)
        if not injected:
            injected = True
            return _PipelineExecuteFault(
                pipeline,
                commit=False,
                error=redis.exceptions.WatchError(),
                before_error=_commit_competing_tree,
            )
        return pipeline

    monkeypatch.setattr(rq_connection, "pipeline", _pipeline)
    admitted: tuple[Job, Job] | None = None
    try:
        admitted = project_rq._enqueue_serial_subcatchment_tree(
            rq_connection,
            queue,
            runid=runid,
            updates={},
            boundary_policy=None,
            child_meta=None,
            receipt_meta={},
            parent_job=parent,
        )
        assert len(competing) == 1
        assert tuple(job.id for job in admitted) == tuple(
            job.id for job in competing[0]
        )
        build, receipt = admitted
        parent.refresh()
        assert parent.meta["preserved"] is True
        assert parent.meta["jobs:0,func:build_subcatchments_rq"] == build.id
        assert parent.meta["jobs:1,func:abstract_watershed_rq"] == receipt.id
        assert rq_connection.get(tail_key) == build.id.encode()
        assert queue.get_job_ids() == [build.id]
        assert DeferredJobRegistry(
            queue_name,
            connection=rq_connection,
        ).get_job_ids() == [receipt.id]
    finally:
        monkeypatch.setattr(rq_connection, "pipeline", real_pipeline)
        rq_connection.delete(tail_key)
        candidates = (*admitted, parent) if admitted else (parent,)
        for candidate in candidates:
            try:
                candidate.delete(remove_from_queue=True)
            except Exception:
                pass
        queue.delete(delete_jobs=True)


def test_atomic_admission_watch_exhaustion_creates_no_work(
    rq_connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue_name = f"surf14a-watch-exhaust-{uuid.uuid4().hex}"
    runid = f"watch-exhaust-{uuid.uuid4().hex}"
    queue = Queue(queue_name, connection=rq_connection)
    parent = queue.create_job(
        _noop_job,
        job_id=f"parent-{uuid.uuid4().hex}",
        meta={"preserved": True},
    )
    parent.save()
    tail_key = project_rq._subcatchment_tail_key(runid)
    real_pipeline = rq_connection.pipeline
    attempts = 0

    def _pipeline(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        return _PipelineExecuteFault(
            real_pipeline(*args, **kwargs),
            commit=False,
            error=redis.exceptions.WatchError(),
        )

    monkeypatch.setattr(rq_connection, "pipeline", _pipeline)
    try:
        with pytest.raises(RuntimeError, match="conflicted five times"):
            project_rq._enqueue_serial_subcatchment_tree(
                rq_connection,
                queue,
                runid=runid,
                updates={},
                boundary_policy=None,
                child_meta=None,
                receipt_meta={},
                parent_job=parent,
            )
        assert attempts == project_rq.WBT_SUBCATCHMENT_ADMISSION_RETRY_ATTEMPTS
        assert rq_connection.get(tail_key) is None
        assert queue.get_job_ids() == []
        assert DeferredJobRegistry(
            queue_name,
            connection=rq_connection,
        ).get_job_ids() == []
        parent.refresh()
        assert parent.meta == {"preserved": True}
    finally:
        monkeypatch.setattr(rq_connection, "pipeline", real_pipeline)
        parent.delete(remove_from_queue=True)
        queue.delete(delete_jobs=True)


def test_atomic_admission_reconciles_commit_then_connection_error(
    rq_connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue_name = f"surf14a-ambiguous-commit-{uuid.uuid4().hex}"
    runid = f"ambiguous-commit-{uuid.uuid4().hex}"
    queue = Queue(queue_name, connection=rq_connection)
    parent = queue.create_job(
        _noop_job,
        job_id=f"parent-{uuid.uuid4().hex}",
        meta={},
    )
    parent.save()
    tail_key = project_rq._subcatchment_tail_key(runid)
    real_pipeline = rq_connection.pipeline
    faulted = False

    def _pipeline(*args, **kwargs):
        nonlocal faulted
        pipeline = real_pipeline(*args, **kwargs)
        if not faulted:
            faulted = True
            return _PipelineExecuteFault(
                pipeline,
                commit=True,
                error=redis.ConnectionError("response lost after EXEC"),
            )
        return pipeline

    monkeypatch.setattr(rq_connection, "pipeline", _pipeline)
    admitted: tuple[Job, Job] | None = None
    try:
        admitted = project_rq._enqueue_serial_subcatchment_tree(
            rq_connection,
            queue,
            runid=runid,
            updates={"outlet": "same"},
            boundary_policy=None,
            child_meta=None,
            receipt_meta={},
            parent_job=parent,
        )
        build, receipt = admitted
        assert rq_connection.get(tail_key) == build.id.encode()
        assert queue.get_job_ids() == [build.id]
        assert receipt.id in build.dependent_ids

        repeated = project_rq._enqueue_serial_subcatchment_tree(
            rq_connection,
            queue,
            runid=runid,
            updates={"outlet": "same"},
            boundary_policy=None,
            child_meta=None,
            receipt_meta={},
            parent_job=parent,
        )
        assert [job.id for job in repeated] == [build.id, receipt.id]
        assert queue.get_job_ids() == [build.id]
    finally:
        monkeypatch.setattr(rq_connection, "pipeline", real_pipeline)
        rq_connection.delete(tail_key)
        for candidate in (*admitted, parent) if admitted else (parent,):
            try:
                candidate.delete(remove_from_queue=True)
            except Exception:
                pass
        queue.delete(delete_jobs=True)


def test_atomic_admission_existing_tree_mismatch_fails_without_duplicate(
    rq_connection,
) -> None:
    queue_name = f"surf14a-exact-mismatch-{uuid.uuid4().hex}"
    runid = f"exact-mismatch-{uuid.uuid4().hex}"
    queue = Queue(queue_name, connection=rq_connection)
    parent = queue.create_job(
        _noop_job,
        job_id=f"parent-{uuid.uuid4().hex}",
        meta={},
    )
    parent.save()
    tail_key = project_rq._subcatchment_tail_key(runid)
    admitted: tuple[Job, Job] | None = None
    try:
        admitted = project_rq._enqueue_serial_subcatchment_tree(
            rq_connection,
            queue,
            runid=runid,
            updates={},
            boundary_policy=None,
            child_meta=None,
            receipt_meta={},
            parent_job=parent,
        )
        build, receipt = admitted
        receipt.meta[project_rq._WBT_ADMISSION_BUILD_KEY] = "wrong-build"
        receipt.save_meta()

        with pytest.raises(RuntimeError, match="does not link to its build"):
            project_rq._enqueue_serial_subcatchment_tree(
                rq_connection,
                queue,
                runid=runid,
                updates={},
                boundary_policy=None,
                child_meta=None,
                receipt_meta={},
                parent_job=parent,
            )

        assert queue.get_job_ids() == [build.id]
        assert rq_connection.get(tail_key) == build.id.encode()
        assert DeferredJobRegistry(
            queue_name,
            connection=rq_connection,
        ).get_job_ids() == [receipt.id]
    finally:
        rq_connection.delete(tail_key)
        for candidate in (*admitted, parent) if admitted else (parent,):
            try:
                candidate.delete(remove_from_queue=True)
            except Exception:
                pass
        queue.delete(delete_jobs=True)


def test_atomic_admission_fails_closed_when_exec_did_not_commit(
    rq_connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue_name = f"surf14a-ambiguous-empty-{uuid.uuid4().hex}"
    runid = f"ambiguous-empty-{uuid.uuid4().hex}"
    queue = Queue(queue_name, connection=rq_connection)
    parent = queue.create_job(
        _noop_job,
        job_id=f"parent-{uuid.uuid4().hex}",
        meta={"preserved": True},
    )
    parent.save()
    tail_key = project_rq._subcatchment_tail_key(runid)
    real_pipeline = rq_connection.pipeline
    faulted = False

    def _pipeline(*args, **kwargs):
        nonlocal faulted
        pipeline = real_pipeline(*args, **kwargs)
        if not faulted:
            faulted = True
            return _PipelineExecuteFault(
                pipeline,
                commit=False,
                error=redis.ConnectionError("failed before EXEC"),
            )
        return pipeline

    monkeypatch.setattr(rq_connection, "pipeline", _pipeline)
    try:
        with pytest.raises(RuntimeError, match="could not be reconciled exactly"):
            project_rq._enqueue_serial_subcatchment_tree(
                rq_connection,
                queue,
                runid=runid,
                updates={},
                boundary_policy=None,
                child_meta=None,
                receipt_meta={},
                parent_job=parent,
            )
        assert rq_connection.get(tail_key) is None
        assert queue.get_job_ids() == []
        assert DeferredJobRegistry(
            queue_name,
            connection=rq_connection,
        ).get_job_ids() == []
        parent.refresh()
        assert parent.meta == {"preserved": True}
    finally:
        monkeypatch.setattr(rq_connection, "pipeline", real_pipeline)
        parent.delete(remove_from_queue=True)
        queue.delete(delete_jobs=True)


def test_actual_root_rq_retry_reuses_original_snapshot_and_exact_tree(
    rq_connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runid = f"snapshot-retry-{uuid.uuid4().hex}"
    root_queue = Queue(
        f"surf14a-root-retry-{uuid.uuid4().hex}",
        connection=rq_connection,
    )
    child_queue = Queue(
        f"surf14a-child-retry-{uuid.uuid4().hex}",
        connection=rq_connection,
    )
    snapshot = {
        "schema_version": 1,
        "runid": runid,
        "actor_token_class": "user",
        "actor_user_id": 73,
        "config_policy": "warn",
        "effective_policy": "error",
        "source": "user_preference",
    }
    argument = {
        "schema_version": 1,
        "effective_policy": "error",
        "source": "user_preference",
    }
    root = root_queue.enqueue(
        project_rq.build_subcatchments_and_abstract_watershed_rq,
        runid,
        {},
        argument,
        meta={
            project_rq.WBT_BOUNDARY_POLICY_SNAPSHOT_KEY: snapshot,
            "auth_actor": {"token_class": "user", "user_id": 73},
        },
    )

    class _RedisContext:
        def __enter__(self):
            return rq_connection

        def __exit__(self, _exc_type, _exc, _tb):
            return False

    monkeypatch.setattr(
        project_rq.redis,
        "Redis",
        lambda **_kwargs: _RedisContext(),
    )
    monkeypatch.setattr(project_rq, "Queue", lambda connection: child_queue)
    monkeypatch.setattr(
        project_rq.StatusMessenger,
        "publish",
        lambda *_args, **_kwargs: None,
    )
    tail_key = project_rq._subcatchment_tail_key(runid)
    children: tuple[Job, Job] | None = None
    try:
        worker = _InlineWepppyWorker(
            [root_queue],
            connection=rq_connection,
            name=f"surf14a-root-retry-worker-{uuid.uuid4().hex}",
        )
        worker.work(burst=True, logging_level="WARNING")
        root.refresh()
        build_id = root.meta["jobs:0,func:build_subcatchments_rq"]
        receipt_id = root.meta["jobs:1,func:abstract_watershed_rq"]
        children = (
            Job.fetch(build_id, connection=rq_connection),
            Job.fetch(receipt_id, connection=rq_connection),
        )
        assert children[0].args[2] == argument
        assert children[0].meta[
            project_rq.WBT_BOUNDARY_POLICY_SNAPSHOT_KEY
        ] == snapshot

        # A later account preference change is deliberately not consulted by
        # RQ retry; the stored root argument and private snapshot remain exact.
        rq_connection.set(f"surf14a:preference-now:{runid}", "warn")
        root_queue.enqueue_job(root)
        worker.work(burst=True, logging_level="WARNING")
        root.refresh()

        assert root.meta["jobs:0,func:build_subcatchments_rq"] == build_id
        assert root.meta["jobs:1,func:abstract_watershed_rq"] == receipt_id
        assert child_queue.get_job_ids() == [build_id]
        assert Job.fetch(build_id, connection=rq_connection).args[2] == argument
        assert rq_connection.get(tail_key) == build_id.encode()
    finally:
        rq_connection.delete(tail_key, f"surf14a:preference-now:{runid}")
        for candidate in (*children, root) if children else (root,):
            try:
                candidate.delete(remove_from_queue=True)
            except Exception:
                pass
        root_queue.delete(delete_jobs=True)
        child_queue.delete(delete_jobs=True)


def test_policy_apply_failure_cancels_receipt_and_leaves_no_dependency_residue(
    rq_connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue_name = f"surf14a-apply-failure-{uuid.uuid4().hex}"
    runid = f"apply-failure-{uuid.uuid4().hex}"
    queue = Queue(queue_name, connection=rq_connection)
    parent = queue.create_job(
        _noop_job,
        job_id=f"parent-{uuid.uuid4().hex}",
        meta={},
    )
    parent.save()
    snapshot = {
        "schema_version": 1,
        "runid": runid,
        "actor_token_class": "user",
        "actor_user_id": 81,
        "config_policy": "warn",
        "effective_policy": "error",
        "source": "user_preference",
    }
    argument = {
        "schema_version": 1,
        "effective_policy": "error",
        "source": "user_preference",
    }
    tail_key = project_rq._subcatchment_tail_key(runid)
    readiness_key = f"surf14a:apply-failure-readiness:{runid}"
    rq_connection.set(readiness_key, "preserved")
    admitted: tuple[Job, Job] | None = None
    try:
        admitted = project_rq._enqueue_serial_subcatchment_tree(
            rq_connection,
            queue,
            runid=runid,
            updates={},
            boundary_policy=argument,
            child_meta={
                project_rq.WBT_BOUNDARY_POLICY_SNAPSHOT_KEY: snapshot,
            },
            receipt_meta={},
            parent_job=parent,
        )
        build, receipt = admitted
        monkeypatch.setattr(
            project_rq,
            "get_wd",
            lambda _runid: "/tmp/wbt-policy-apply-failure",
        )
        monkeypatch.setattr(
            project_rq.Watershed,
            "getInstance",
            lambda _wd: (_ for _ in ()).throw(
                FileNotFoundError("watershed root unavailable")
            ),
        )
        monkeypatch.setattr(
            project_rq,
            "_run_with_directory_root_lock",
            lambda _wd, _root, callback, **_kwargs: callback(),
        )
        monkeypatch.setattr(
            project_rq.StatusMessenger,
            "publish",
            lambda *_args, **_kwargs: None,
        )
        worker = _InlineWepppyWorker(
            [queue],
            connection=rq_connection,
            name=f"surf14a-apply-failure-worker-{uuid.uuid4().hex}",
        )
        worker.work(burst=True, logging_level="WARNING")

        build.refresh()
        receipt.refresh()
        assert build.get_status(refresh=True) == "failed"
        assert build.meta["error"]["code"] == "wbt_boundary_policy_apply_failed"
        assert build.meta["error"]["message"] == (
            project_rq.WBT_BOUNDARY_POLICY_APPLY_FAILED_MESSAGE
        )
        assert receipt.get_status(refresh=True) == "canceled"
        assert receipt.id not in DeferredJobRegistry(
            queue_name,
            connection=rq_connection,
        ).get_job_ids()
        assert project_rq._stored_dependency_ids(receipt) == set()
        assert receipt.id not in build.dependent_ids
        assert rq_connection.get(tail_key) is None
        assert rq_connection.get(readiness_key) == b"preserved"
    finally:
        rq_connection.delete(tail_key, readiness_key)
        for candidate in (*admitted, parent) if admitted else (parent,):
            try:
                candidate.delete(remove_from_queue=True)
            except Exception:
                pass
        queue.delete(delete_jobs=True)
