from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from wepppy.runtime_paths.errors import NoDirError

import wepppy.rq.path_ce_rq as path_ce_rq
from wepppy.nodb.mods.path_ce.preconditions import (
    PathCEPreconditionError,
    PreconditionReport,
)

pytestmark = pytest.mark.unit


class RedisPrepStub:
    _instances: dict[str, "RedisPrepStub"] = {}

    def __init__(self, wd: str) -> None:
        self.wd = wd
        self.job_ids: list[tuple[str, str]] = []
        self.removed: list[object] = []
        self.timestamps: list[object] = []

    @classmethod
    def tryGetInstance(cls, wd: str) -> "RedisPrepStub":
        instance = cls._instances.get(wd)
        if instance is None:
            instance = cls(wd)
            cls._instances[wd] = instance
        return instance

    @classmethod
    def reset_instances(cls) -> None:
        cls._instances.clear()

    def set_rq_job_id(self, key: str, job_id: str) -> None:
        self.job_ids.append((key, job_id))

    def remove_timestamp(self, key) -> None:
        self.removed.append(key)

    def timestamp(self, key) -> None:
        self.timestamps.append(key)


class PathCeStub:
    _instances: dict[str, "PathCeStub"] = {}

    def __init__(self, wd: str) -> None:
        self.wd = wd
        self.status_updates: list[tuple[str, str | None, float | None]] = []
        self.run_calls = 0
        self.callbacks: list[object] = []

    @classmethod
    def getInstance(cls, wd: str) -> "PathCeStub":
        instance = cls._instances.get(wd)
        if instance is None:
            instance = cls(wd)
            cls._instances[wd] = instance
        return instance

    @classmethod
    def reset_instances(cls) -> None:
        cls._instances.clear()

    def set_status(self, status: str, message: str | None = None, progress: float | None = None) -> None:
        self.status_updates.append((status, message, progress))

    def run(self, status_callback=None):
        self.run_calls += 1
        self.callbacks.append(status_callback)
        if status_callback is not None:
            status_callback("Running cost-effective site selection")
        return {"primary_status": 1}


@pytest.fixture()
def path_ce_rq_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    published: list[tuple[str, str]] = []
    monkeypatch.setattr(
        path_ce_rq.StatusMessenger, "publish", lambda channel, message: published.append((channel, message))
    )
    monkeypatch.setattr(path_ce_rq, "get_current_job", lambda: SimpleNamespace(id="job-22"))
    monkeypatch.setattr(path_ce_rq, "get_wd", lambda runid: str(tmp_path / runid))

    RedisPrepStub.reset_instances()
    PathCeStub.reset_instances()

    monkeypatch.setattr(path_ce_rq, "RedisPrep", RedisPrepStub)
    monkeypatch.setattr(path_ce_rq, "PathCostEffective", PathCeStub)
    monkeypatch.setattr(path_ce_rq, "clear_nodb_file_cache", lambda runid, *, pup_relpath: None)

    return published, tmp_path


def test_run_path_cost_effective_rq_happy_path(
    path_ce_rq_environment,
    monkeypatch: pytest.MonkeyPatch,
):
    published, base_path = path_ce_rq_environment

    call_order: list[str] = []
    preflight_calls: list[tuple[str, str, str]] = []

    def _resolve(wd, root, view="effective"):
        call_order.append(f"resolve:{root}")
        preflight_calls.append((wd, root, view))

    monkeypatch.setattr(path_ce_rq, "nodir_resolve", _resolve)
    monkeypatch.setattr(
        path_ce_rq,
        "clear_nodb_file_cache",
        lambda runid, *, pup_relpath: call_order.append(f"clear:{pup_relpath}"),
    )
    original_get = PathCeStub.getInstance.__func__

    def _get_instance(cls, wd):
        call_order.append("get:path_ce")
        return original_get(cls, wd)

    monkeypatch.setattr(PathCeStub, "getInstance", classmethod(_get_instance))

    result = path_ce_rq.run_path_cost_effective_rq("demo")

    run_wd = str(base_path / "demo")
    assert preflight_calls == [
        (run_wd, "climate", "effective"),
        (run_wd, "watershed", "effective"),
        (run_wd, "landuse", "effective"),
        (run_wd, "soils", "effective"),
    ]
    # root rejection precedes cache invalidation and mutable hydration
    assert call_order.index("resolve:soils") < call_order.index("clear:path_ce.nodb")
    assert call_order.index("clear:path_ce.nodb") < call_order.index("get:path_ce")

    controller = PathCeStub.getInstance(run_wd)
    prep = RedisPrepStub.tryGetInstance(run_wd)

    assert result == {"primary_status": 1}
    assert controller.run_calls == 1
    assert controller.callbacks[0] is not None
    assert path_ce_rq.TaskEnum.run_path_cost_effective in prep.timestamps
    # stage messages from the controller's callback are streamed
    assert any("STATUS Running cost-effective site selection" in m for _, m in published)
    assert any("TRIGGER path_ce PATH_CE_RUN_COMPLETE" in m for _, m in published)
    # no Omni provisioning in v2
    assert not hasattr(path_ce_rq, "Omni")


def test_run_path_cost_effective_rq_stops_on_nodir_preflight_error(
    path_ce_rq_environment,
    monkeypatch: pytest.MonkeyPatch,
):
    published, base_path = path_ce_rq_environment

    def _raise_on_soils(wd: str, root: str, view: str = "effective"):
        if root == "soils":
            raise NoDirError(http_status=409, code="NODIR_MIXED_STATE", message="mixed root state")
        return None

    monkeypatch.setattr(path_ce_rq, "nodir_resolve", _raise_on_soils)

    with pytest.raises(NoDirError) as exc_info:
        path_ce_rq.run_path_cost_effective_rq("demo")

    assert exc_info.value.code == "NODIR_MIXED_STATE"

    run_wd = str(base_path / "demo")
    # preflight rejection happens before the controller is ever hydrated
    assert run_wd not in PathCeStub._instances
    assert any("EXCEPTION run_path_cost_effective_rq(demo)" in m for _, m in published)


def test_run_path_cost_effective_rq_streams_precondition_errors(
    path_ce_rq_environment,
    monkeypatch: pytest.MonkeyPatch,
):
    published, base_path = path_ce_rq_environment
    monkeypatch.setattr(path_ce_rq, "nodir_resolve", lambda wd, root, view="effective": None)

    report = PreconditionReport(
        ok=False,
        errors=["omni/contrasts.out.parquet not found — run Omni contrasts"],
    )

    def _raise_precondition(self, status_callback=None):
        self.run_calls += 1
        self.set_status("failed", message="preconditions not met")
        raise PathCEPreconditionError(report)

    monkeypatch.setattr(PathCeStub, "run", _raise_precondition)

    with pytest.raises(PathCEPreconditionError):
        path_ce_rq.run_path_cost_effective_rq("demo")

    run_wd = str(base_path / "demo")
    prep = RedisPrepStub.tryGetInstance(run_wd)
    assert path_ce_rq.TaskEnum.run_path_cost_effective not in prep.timestamps
    assert any("PRECONDITION" in m and "run Omni contrasts" in m for _, m in published)
    assert any("EXCEPTION run_path_cost_effective_rq(demo)" in m for _, m in published)
    assert not any("TRIGGER" in m for _, m in published)


def test_run_path_cost_effective_rq_marks_failed_on_controller_error(
    path_ce_rq_environment,
    monkeypatch: pytest.MonkeyPatch,
):
    published, base_path = path_ce_rq_environment
    monkeypatch.setattr(path_ce_rq, "nodir_resolve", lambda wd, root, view="effective": None)

    def _raise_controller_error(self, status_callback=None):
        self.run_calls += 1
        raise RuntimeError("controller run failed")

    monkeypatch.setattr(PathCeStub, "run", _raise_controller_error)

    with pytest.raises(RuntimeError) as exc_info:
        path_ce_rq.run_path_cost_effective_rq("demo")

    assert str(exc_info.value) == "controller run failed"

    run_wd = str(base_path / "demo")
    controller = PathCeStub.getInstance(run_wd)
    prep = RedisPrepStub.tryGetInstance(run_wd)

    assert controller.run_calls == 1
    assert any(
        status == "failed" and message == "controller run failed"
        for status, message, _p in controller.status_updates
    )
    assert path_ce_rq.TaskEnum.run_path_cost_effective not in prep.timestamps
    assert any("EXCEPTION run_path_cost_effective_rq(demo)" in m for _, m in published)
    assert not any("TRIGGER path_ce PATH_CE_RUN_COMPLETE" in m for _, m in published)
