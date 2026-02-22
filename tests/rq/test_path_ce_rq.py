from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from wepppy.nodir.errors import NoDirError

import wepppy.rq.path_ce_rq as path_ce_rq

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
        self.config = {"post_fire_scenario": "undisturbed"}
        self.status_updates: list[tuple[str, str | None, float | None]] = []
        self.run_calls = 0

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

    def run(self):
        self.run_calls += 1
        return {"status": "ok"}


class OmniStub:
    _instances: dict[str, "OmniStub"] = {}

    def __init__(self, wd: str) -> None:
        self.wd = wd
        self.parse_calls: list[list[object]] = []
        self.run_calls = 0

    @classmethod
    def getInstance(cls, wd: str) -> "OmniStub":
        instance = cls._instances.get(wd)
        if instance is None:
            instance = cls(wd)
            cls._instances[wd] = instance
        return instance

    @classmethod
    def reset_instances(cls) -> None:
        cls._instances.clear()

    def parse_scenarios(self, inputs):
        self.parse_calls.append(list(inputs))

    def run_omni_scenarios(self) -> None:
        self.run_calls += 1


@pytest.fixture()
def path_ce_rq_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    published: list[tuple[str, str]] = []
    monkeypatch.setattr(path_ce_rq.StatusMessenger, "publish", lambda channel, message: published.append((channel, message)))
    monkeypatch.setattr(path_ce_rq, "get_current_job", lambda: SimpleNamespace(id="job-22"))
    monkeypatch.setattr(path_ce_rq, "get_wd", lambda runid: str(tmp_path / runid))

    RedisPrepStub.reset_instances()
    PathCeStub.reset_instances()
    OmniStub.reset_instances()

    monkeypatch.setattr(path_ce_rq, "RedisPrep", RedisPrepStub)
    monkeypatch.setattr(path_ce_rq, "PathCostEffective", PathCeStub)
    monkeypatch.setattr(path_ce_rq, "Omni", OmniStub)

    monkeypatch.setattr(path_ce_rq, "_hydrate_existing_scenarios", lambda omni: [("existing", {"type": "existing"})])
    monkeypatch.setattr(path_ce_rq, "_hydrate_required_scenarios", lambda base_scenario: [("required", {"type": base_scenario})])
    monkeypatch.setattr(path_ce_rq, "_merge_scenario_sets", lambda existing, required: ["merged-scenarios"])

    return published, tmp_path


def test_run_path_cost_effective_rq_preflights_omni_roots(
    path_ce_rq_environment,
    monkeypatch: pytest.MonkeyPatch,
):
    published, base_path = path_ce_rq_environment

    preflight_calls: list[tuple[str, str, str]] = []

    def _resolve(wd: str, root: str, view: str = "effective"):
        preflight_calls.append((wd, root, view))

    monkeypatch.setattr(path_ce_rq, "nodir_resolve", _resolve)

    result = path_ce_rq.run_path_cost_effective_rq("demo")

    run_wd = str(base_path / "demo")
    assert preflight_calls == [
        (run_wd, "climate", "effective"),
        (run_wd, "watershed", "effective"),
        (run_wd, "landuse", "effective"),
        (run_wd, "soils", "effective"),
    ]

    controller = PathCeStub.getInstance(run_wd)
    omni = OmniStub.getInstance(run_wd)
    prep = RedisPrepStub.tryGetInstance(run_wd)

    assert result == {"status": "ok"}
    assert omni.parse_calls == [["merged-scenarios"]]
    assert omni.run_calls == 1
    assert controller.run_calls == 1
    assert path_ce_rq.TaskEnum.run_omni_scenarios in prep.timestamps
    assert path_ce_rq.TaskEnum.run_path_cost_effective in prep.timestamps
    assert any("TRIGGER path_ce PATH_CE_RUN_COMPLETE" in message for _, message in published)


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
    controller = PathCeStub.getInstance(run_wd)
    omni = OmniStub.getInstance(run_wd)

    assert omni.run_calls == 0
    assert controller.run_calls == 0
    assert any(status == "failed" for status, _message, _progress in controller.status_updates)
    assert any("EXCEPTION run_path_cost_effective_rq(demo)" in message for _, message in published)


def test_run_path_cost_effective_rq_marks_failed_on_controller_error(
    path_ce_rq_environment,
    monkeypatch: pytest.MonkeyPatch,
):
    published, base_path = path_ce_rq_environment

    preflight_calls: list[tuple[str, str, str]] = []

    def _resolve(wd: str, root: str, view: str = "effective"):
        preflight_calls.append((wd, root, view))

    monkeypatch.setattr(path_ce_rq, "nodir_resolve", _resolve)

    def _raise_controller_error(self: PathCeStub):
        self.run_calls += 1
        raise RuntimeError("controller run failed")

    monkeypatch.setattr(PathCeStub, "run", _raise_controller_error)

    with pytest.raises(RuntimeError) as exc_info:
        path_ce_rq.run_path_cost_effective_rq("demo")

    assert str(exc_info.value) == "controller run failed"

    run_wd = str(base_path / "demo")
    assert preflight_calls == [
        (run_wd, "climate", "effective"),
        (run_wd, "watershed", "effective"),
        (run_wd, "landuse", "effective"),
        (run_wd, "soils", "effective"),
    ]

    controller = PathCeStub.getInstance(run_wd)
    omni = OmniStub.getInstance(run_wd)
    prep = RedisPrepStub.tryGetInstance(run_wd)

    assert omni.run_calls == 1
    assert controller.run_calls == 1

    assert any(
        status == "failed" and message == "controller run failed"
        for status, message, _progress in controller.status_updates
    )
    assert path_ce_rq.TaskEnum.run_omni_scenarios in prep.timestamps
    assert path_ce_rq.TaskEnum.run_path_cost_effective not in prep.timestamps
    assert any("EXCEPTION run_path_cost_effective_rq(demo)" in message for _, message in published)
    assert not any("TRIGGER path_ce PATH_CE_RUN_COMPLETE" in message for _, message in published)
