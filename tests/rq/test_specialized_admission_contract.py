from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Callable

import pytest
from redis.exceptions import RedisError

from wepppy.microservices.rq_engine import ag_fields_routes
from wepppy.microservices.rq_engine import culvert_routes
from wepppy.microservices.rq_engine import roads_routes
from wepppy.rq import roads_rq, wepp_rq
from wepppy.weppcloud.routes.nodb_api import roads_bp

pytestmark = pytest.mark.unit

WEPP_ALLOWED_NAMES = (
    "run_ss_batch_hillslope_rq", "run_hillslope_rq", "run_watershed_rq",
    "run_ss_batch_watershed_rq", "run_wepp_rq", "run_wepp_noprep_rq",
    "run_wepp_watershed_rq", "prep_wepp_watershed_rq",
    "run_wepp_watershed_noprep_rq", "_prep_multi_ofe_rq", "_prep_slopes_rq",
    "_run_hillslopes_rq", "_prep_managements_rq", "_prep_soils_rq",
    "_prep_climates_rq", "_prep_remaining_rq", "_prep_watershed_rq",
    "_post_run_cleanup_out_rq", "_analyze_return_periods_rq",
    "_build_hillslope_interchange_rq", "_build_totalwatsed3_rq",
    "_run_hillslope_watbal_rq", "_post_prep_details_rq",
    "_post_watershed_interchange_rq", "_post_legacy_arc_export_rq",
    "_post_gpkg_export_rq", "post_dss_export_rq", "_post_make_loss_grid_rq",
    "_log_complete_rq", "_log_prep_complete_rq", "run_swat_rq",
    "run_swat_noprep_rq", "_build_swat_inputs_rq", "_run_swat_rq",
)


@dataclass(frozen=True)
class ReconcilerCase:
    name: str
    module: Any
    invoke: Callable[[Any, Any], None]
    target: Callable[[Any, str], bool]
    allowed_func_names: tuple[str, ...]
    conflict_type: type[Exception]


class PrepStub:
    def __init__(self, keys: tuple[str, ...]) -> None:
        self.job_ids = {key: f"old-{key}" for key in keys}

    def get_rq_job_id(self, key: str) -> str | None:
        return self.job_ids.get(key)

    def set_rq_job_id(self, key: str, job_id: str) -> None:
        self.job_ids[key] = job_id

    def remove_timestamp(self, _task: Any) -> None:
        return None


RECONCILERS = (
    ReconcilerCase(
        "roads-fastapi-and-flask-prepare-run",
        roads_rq,
        lambda prep, conn: roads_rq.reconcile_deferred_roads_jobs("run-1", prep, conn),
        roads_rq._roads_job_targets_run,
        ("run_roads_prepare_rq", "run_roads_rq"),
        roads_rq.RoadsSingleFlightConflict,
    ),
    ReconcilerCase(
        "wepp-swat-prep-and-noprep-family",
        wepp_rq,
        lambda prep, conn: wepp_rq.reconcile_deferred_wepp_jobs("run-1", prep, conn),
        wepp_rq._wepp_job_targets_run,
        WEPP_ALLOWED_NAMES,
        wepp_rq.WeppSingleFlightConflict,
    ),
    ReconcilerCase(
        "agfields-build-plant-wepp-direct-and-suite",
        ag_fields_routes,
        lambda prep, conn: ag_fields_routes._reconcile_deferred_agfields_jobs(prep, conn, "run-1"),
        ag_fields_routes._agfields_job_targets_run,
        tuple(
            func.__qualname__
            for func in (
                ag_fields_routes.build_ag_fields_subfields_rq,
                ag_fields_routes.process_ag_fields_plant_db_rq,
                ag_fields_routes.run_ag_fields_watershed_rq,
                ag_fields_routes.run_ag_fields_watershed_suite_rq,
                ag_fields_routes.finalize_ag_fields_watershed_suite_rq,
                ag_fields_routes.run_ag_fields_wepp_rq,
            )
        ),
        ag_fields_routes.AgFieldsJobConflict,
    ),
)


def _keys(case: ReconcilerCase) -> tuple[str, ...]:
    if case.module is roads_rq:
        return tuple(roads_rq.ROADS_RQ_JOB_KEYS)
    if case.module is wepp_rq:
        return tuple(wepp_rq.WEPP_RQ_JOB_KEYS)
    return tuple(ag_fields_routes.AGFIELDS_ALL_JOB_KEYS)


def _allowed_func(case: ReconcilerCase) -> str:
    short_name = case.allowed_func_names[0]
    return _qualified_func(case, short_name)


def _qualified_func(case: ReconcilerCase, short_name: str) -> str:
    if case.module is roads_rq:
        return f"wepppy.rq.roads_rq.{short_name}"
    if case.module is wepp_rq and short_name in {
        "run_swat_rq", "run_swat_noprep_rq", "_build_swat_inputs_rq", "_run_swat_rq"
    }:
        return f"wepppy.rq.swat_rq.{short_name}"
    if case.module is ag_fields_routes:
        func = getattr(ag_fields_routes, short_name)
        return f"{func.__module__}.{func.__qualname__}"
    return f"{case.module.__name__}.{short_name}"


def _candidate(case: ReconcilerCase, mismatch: str | None = None):
    func_name = _allowed_func(case)
    origin = "default"
    args = ("run-1",)
    if mismatch == "cross-run":
        args = ("other-run",)
    elif mismatch == "wrong-operation":
        func_name = "wepppy.rq.project_rq.build_soils_rq"
    elif mismatch == "hostile-lineage":
        func_name = f"{case.module.__name__}._undeclared_descendant_rq"
    elif mismatch == "wrong-origin":
        origin = "hostile-queue"
    return SimpleNamespace(func_name=func_name, origin=origin, args=args, meta={"runid": args[0]})


@pytest.mark.parametrize("case", RECONCILERS, ids=lambda case: case.name)
def test_specialized_reconciler_accepts_every_declared_operation(case: ReconcilerCase) -> None:
    for short_name in case.allowed_func_names:
        func_name = _qualified_func(case, short_name)
        candidate = SimpleNamespace(func_name=func_name, origin="default", args=("run-1",), meta={})
        assert case.target(candidate, "run-1") is True


@pytest.mark.parametrize("status", ("queued", "started", "scheduled"))
@pytest.mark.parametrize("case", RECONCILERS, ids=lambda case: case.name)
def test_specialized_reconciler_preserves_active_protection(
    case: ReconcilerCase, status: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    prep = PrepStub(_keys(case))

    def reconcile(*_args, **kwargs):
        assert kwargs["association"](_candidate(case)) is True
        return SimpleNamespace(state="active", job_ids=(f"old-{status}",))

    monkeypatch.setattr(case.module, "reconcile_deferred_workflow", reconcile)
    with pytest.raises(case.conflict_type):
        case.invoke(prep, object())


@pytest.mark.parametrize("mismatch", ("cross-run", "wrong-operation", "wrong-origin", "hostile-lineage"))
@pytest.mark.parametrize("case", RECONCILERS, ids=lambda case: case.name)
def test_specialized_reconciler_contains_foreign_candidates(
    case: ReconcilerCase, mismatch: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    prep = PrepStub(_keys(case))

    def reconcile(*_args, **kwargs):
        assert kwargs["association"](_candidate(case, mismatch)) is False
        return SimpleNamespace(state="mismatch", job_ids=(mismatch,))

    monkeypatch.setattr(case.module, "reconcile_deferred_workflow", reconcile)
    with pytest.raises(case.conflict_type):
        case.invoke(prep, object())


@pytest.mark.parametrize("case", RECONCILERS, ids=lambda case: case.name)
def test_specialized_reconciler_clears_deferred_family(case: ReconcilerCase, monkeypatch: pytest.MonkeyPatch) -> None:
    prep = PrepStub(_keys(case))
    reconciled: list[str] = []

    def reconcile(job_id, **kwargs):
        assert kwargs["association"](_candidate(case)) is True
        reconciled.append(job_id)
        return SimpleNamespace(state="canceled", job_ids=(job_id,))

    monkeypatch.setattr(case.module, "reconcile_deferred_workflow", reconcile)
    case.invoke(prep, object())
    assert reconciled == list(prep.job_ids.values())


@pytest.mark.parametrize("case", RECONCILERS, ids=lambda case: case.name)
def test_specialized_reconciler_propagates_cleanup_failure(case: ReconcilerCase, monkeypatch: pytest.MonkeyPatch) -> None:
    prep = PrepStub(_keys(case))
    monkeypatch.setattr(
        case.module,
        "reconcile_deferred_workflow",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RedisError("cleanup failed")),
    )
    with pytest.raises(RedisError, match="cleanup failed"):
        case.invoke(prep, object())


CULVERT_UUID = "11111111-1111-4111-8111-111111111111"


class _CulvertConnection:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def lock(self, *_args, **_kwargs):
        return SimpleNamespace(
            acquire=lambda **_kwargs: True,
            extend=lambda *_args, **_kwargs: True,
            release=lambda: None,
        )


class _CulvertRunner:
    def __init__(self, *, fail_save: bool = False) -> None:
        self.rq_job_ids = {"run_culvert_batch_rq": "old-culvert"}
        self.fail_save = fail_save

    def set_rq_job_id(self, key: str, job_id: str) -> None:
        if self.fail_save:
            raise OSError("culvert receipt save failed")
        self.rq_job_ids[key] = job_id


def _culvert_candidate(mismatch: str | None = None):
    func_name = (
        f"{culvert_routes.run_culvert_batch_rq.__module__}."
        f"{culvert_routes.run_culvert_batch_rq.__qualname__}"
    )
    origin = "batch"
    args = (CULVERT_UUID,)
    meta = {"culvert_batch_uuid": CULVERT_UUID}
    if mismatch == "cross-run":
        args = ("22222222-2222-4222-8222-222222222222",)
    elif mismatch == "wrong-operation":
        func_name = "wepppy.rq.project_rq.build_soils_rq"
    elif mismatch == "wrong-origin":
        origin = "default"
    elif mismatch == "hostile-lineage":
        func_name = "wepppy.rq.culvert_rq.unrelated_culvert_rq"
    return SimpleNamespace(func_name=func_name, origin=origin, args=args, meta=meta)


def _invoke_culvert(monkeypatch: pytest.MonkeyPatch, *, state: str, failure: str | None = None):
    runner = _CulvertRunner(fail_save=failure == "hint-save")
    connection = _CulvertConnection()
    enqueued: list[dict[str, Any]] = []
    monkeypatch.setattr(culvert_routes.redis, "Redis", lambda **_kwargs: connection)
    monkeypatch.setattr(culvert_routes, "_culvert_runner", lambda _uuid: runner)
    monkeypatch.setattr(culvert_routes, "new_rq_job_id", lambda: "replacement-culvert")

    def reconcile(*_args, **kwargs):
        if failure == "cleanup":
            raise RedisError("culvert cleanup failed")
        candidate = _culvert_candidate(state if state in {
            "cross-run", "wrong-operation", "wrong-origin", "hostile-lineage"
        } else None)
        associated = kwargs["association"](candidate)
        if state in {"cross-run", "wrong-operation", "wrong-origin", "hostile-lineage"}:
            assert associated is False
            return SimpleNamespace(state="mismatch", job_ids=(state,))
        assert associated is True
        return SimpleNamespace(state=state, job_ids=("old-culvert",))

    class QueueStub:
        def __init__(self, *_args, **_kwargs):
            pass

        def enqueue_call(self, **kwargs):
            enqueued.append(kwargs)
            if failure == "enqueue":
                raise RedisError("culvert enqueue failed")
            return SimpleNamespace(id=kwargs["job_id"])

    monkeypatch.setattr(culvert_routes, "reconcile_deferred_workflow", reconcile)
    monkeypatch.setattr(culvert_routes, "Queue", QueueStub)
    result = culvert_routes._enqueue_culvert_job(
        CULVERT_UUID,
        job_key="run_culvert_batch_rq",
        func=culvert_routes.run_culvert_batch_rq,
        args=[CULVERT_UUID],
        meta={"culvert_batch_uuid": CULVERT_UUID},
    )
    return result, runner, enqueued


@pytest.mark.parametrize("status", ("queued", "started", "scheduled"))
def test_culvert_actual_producer_preserves_active_states(
    status: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(culvert_routes.RqSubmissionConflict):
        _invoke_culvert(monkeypatch, state="active")


@pytest.mark.parametrize("mismatch", ("cross-run", "wrong-operation", "wrong-origin", "hostile-lineage"))
def test_culvert_actual_producer_contains_foreign_candidates(
    mismatch: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(culvert_routes.RqSubmissionConflict):
        _invoke_culvert(monkeypatch, state=mismatch)


def test_culvert_actual_producer_replaces_deferred_exactly(monkeypatch: pytest.MonkeyPatch) -> None:
    result, runner, enqueued = _invoke_culvert(monkeypatch, state="canceled")
    assert result == "replacement-culvert"
    assert runner.rq_job_ids["run_culvert_batch_rq"] == "replacement-culvert"
    assert enqueued[0]["job_id"] == "replacement-culvert"


@pytest.mark.parametrize("failure", ("cleanup", "hint-save", "enqueue"))
def test_culvert_actual_producer_partial_failures(
    failure: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises((OSError, RedisError)):
        _invoke_culvert(monkeypatch, state="canceled", failure=failure)


@pytest.mark.parametrize("module", (roads_routes, roads_bp), ids=("fastapi", "flask"))
@pytest.mark.parametrize(
    ("func", "job_key"),
    (
        (roads_rq.run_roads_prepare_rq, "run_roads_prepare_rq"),
        (roads_rq.run_roads_rq, "run_roads_rq"),
    ),
    ids=("prepare", "run"),
)
def test_roads_actual_producers_replace_deferred_with_exact_receipt(
    module: Any,
    func: Callable[..., Any],
    job_key: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prep = PrepStub(tuple(roads_rq.ROADS_RQ_JOB_KEYS))
    enqueued: list[str] = []
    connection = _CulvertConnection()

    class QueueStub:
        def __init__(self, *_args, **_kwargs):
            pass

        def enqueue_call(self, *_args, **kwargs):
            job_id = str(kwargs["job_id"])
            enqueued.append(job_id)
            return SimpleNamespace(id=job_id)

    monkeypatch.setattr(module, "get_wd", lambda _runid: "/runs/run-1")
    monkeypatch.setattr(module.RedisPrep, "getInstance", lambda _wd: prep)
    monkeypatch.setattr(module.redis, "Redis", lambda **_kwargs: connection)
    monkeypatch.setattr(module, "Queue", QueueStub)
    monkeypatch.setattr(module, "new_rq_job_id", lambda: "replacement-roads")
    monkeypatch.setattr(module, "reconcile_deferred_roads_jobs", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(module, "ensure_no_active_roads_job", lambda *_args, **_kwargs: None)

    result = module._enqueue_roads_job("run-1", func=func, prep_key=job_key)

    result_id = result if isinstance(result, str) else result["job_id"]
    assert result_id == "replacement-roads"
    assert prep.job_ids[job_key] == "replacement-roads"
    assert enqueued == ["replacement-roads"]


@pytest.mark.parametrize("module", (roads_routes, roads_bp), ids=("fastapi", "flask"))
@pytest.mark.parametrize("failure", ("cleanup", "hint-save", "enqueue"))
def test_roads_actual_producer_failure_postconditions(
    module: Any, failure: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    prep = PrepStub(tuple(roads_rq.ROADS_RQ_JOB_KEYS))
    original = dict(prep.job_ids)
    enqueued: list[str] = []
    connection = _CulvertConnection()

    if failure == "hint-save":
        def fail_save(_key: str, _job_id: str) -> None:
            raise OSError("roads receipt save failed")

        prep.set_rq_job_id = fail_save  # type: ignore[method-assign]

    class QueueStub:
        def __init__(self, *_args, **_kwargs):
            pass

        def enqueue_call(self, *_args, **kwargs):
            enqueued.append(str(kwargs["job_id"]))
            if failure == "enqueue":
                raise RedisError("roads enqueue failed")
            return SimpleNamespace(id=kwargs["job_id"])

    def reconcile(*_args, **_kwargs):
        if failure == "cleanup":
            raise RedisError("roads cleanup failed")

    monkeypatch.setattr(module, "get_wd", lambda _runid: "/runs/run-1")
    monkeypatch.setattr(module.RedisPrep, "getInstance", lambda _wd: prep)
    monkeypatch.setattr(module.redis, "Redis", lambda **_kwargs: connection)
    monkeypatch.setattr(module, "Queue", QueueStub)
    monkeypatch.setattr(module, "new_rq_job_id", lambda: "replacement-roads")
    monkeypatch.setattr(module, "reconcile_deferred_roads_jobs", reconcile)
    monkeypatch.setattr(module, "ensure_no_active_roads_job", lambda *_args, **_kwargs: None)

    with pytest.raises((OSError, RedisError)):
        module._enqueue_roads_job(
            "run-1", func=roads_rq.run_roads_rq, prep_key="run_roads_rq"
        )

    if failure in {"cleanup", "hint-save"}:
        assert prep.job_ids == original
        assert enqueued == []
    else:
        assert prep.job_ids["run_roads_rq"] == "replacement-roads"
        assert enqueued == ["replacement-roads"]
