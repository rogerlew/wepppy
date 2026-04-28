from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import wepppy.rq.roads_rq as roads_rq

pytestmark = pytest.mark.unit


class RoadsStub:
    _instances: dict[str, "RoadsStub"] = {}

    def __init__(self, wd: str, cfg_fn: str) -> None:
        self.wd = wd
        self.cfg_fn = cfg_fn
        self.enabled = False
        self.prepare_calls = 0
        self.run_calls = 0
        type(self)._instances[wd] = self

    @classmethod
    def tryGetInstance(cls, wd: str):
        return cls._instances.get(wd)

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)

    def prepare_segments(self):
        self.prepare_calls += 1
        return {"prepared": True}

    def run_roads_wepp(self):
        self.run_calls += 1
        return {"completed": True}


class RonStub:
    _instances: dict[str, "RonStub"] = {}

    def __init__(self, wd: str) -> None:
        self.wd = wd
        self.mods = ["roads"]
        self.config_stem = "cfg"

    @classmethod
    def getInstance(cls, wd: str) -> "RonStub":
        instance = cls._instances.get(wd)
        if instance is None:
            instance = cls(wd)
            cls._instances[wd] = instance
        return instance


class RedisPrepStub:
    _instances: dict[str, "RedisPrepStub"] = {}

    def __init__(self, wd: str) -> None:
        self.wd = wd
        self.removed: list[object] = []
        self.timestamps: list[object] = []

    @classmethod
    def tryGetInstance(cls, wd: str) -> "RedisPrepStub":
        instance = cls._instances.get(wd)
        if instance is None:
            instance = cls(wd)
            cls._instances[wd] = instance
        return instance

    def remove_timestamp(self, task) -> None:
        self.removed.append(task)

    def timestamp(self, task) -> None:
        self.timestamps.append(task)


@pytest.fixture()
def roads_rq_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    published: list[tuple[str, str]] = []
    clear_calls: list[tuple[str, str]] = []

    RoadsStub._instances.clear()
    RonStub._instances.clear()
    RedisPrepStub._instances.clear()

    monkeypatch.setattr(roads_rq.StatusMessenger, "publish", lambda channel, message: published.append((channel, message)))
    monkeypatch.setattr(roads_rq, "get_current_job", lambda: SimpleNamespace(id="job-77"))
    monkeypatch.setattr(roads_rq, "get_wd", lambda runid: str(tmp_path / runid))
    monkeypatch.setattr(roads_rq, "Roads", RoadsStub)
    monkeypatch.setattr(roads_rq, "Ron", RonStub)
    monkeypatch.setattr(roads_rq, "RedisPrep", RedisPrepStub)
    monkeypatch.setattr(
        roads_rq,
        "clear_nodb_file_cache",
        lambda runid, *, pup_relpath: clear_calls.append((runid, str(pup_relpath))),
    )
    monkeypatch.setattr(roads_rq, "acquire_roads_runtime_lock", lambda _runid, _owner: True)
    monkeypatch.setattr(roads_rq, "release_roads_runtime_lock", lambda _runid, _owner: None)

    return published, tmp_path, clear_calls


def test_run_roads_prepare_rq_prepares_segments_and_emits_trigger(roads_rq_environment):
    published, base_path, clear_calls = roads_rq_environment

    result = roads_rq.run_roads_prepare_rq("demo")

    wd = str(base_path / "demo")
    prep = RedisPrepStub.tryGetInstance(wd)
    roads = RoadsStub.tryGetInstance(wd)

    assert result == {"prepared": True}
    assert roads is not None
    assert roads.enabled is True
    assert roads.prepare_calls == 1
    assert clear_calls == [("demo", "roads.nodb")]
    assert prep.removed == [roads_rq.TaskEnum.run_roads]
    assert any("TRIGGER roads ROADS_PREPARE_TASK_COMPLETED" in message for _, message in published)


def test_run_roads_rq_runs_and_timestamps_completion(roads_rq_environment):
    published, base_path, clear_calls = roads_rq_environment

    result = roads_rq.run_roads_rq("demo")

    wd = str(base_path / "demo")
    prep = RedisPrepStub.tryGetInstance(wd)
    roads = RoadsStub.tryGetInstance(wd)

    assert result == {"completed": True}
    assert roads is not None
    assert roads.enabled is True
    assert roads.run_calls == 1
    assert clear_calls == [("demo", "roads.nodb")]
    assert prep.removed == [roads_rq.TaskEnum.run_roads]
    assert prep.timestamps == [roads_rq.TaskEnum.run_roads]
    assert any("TRIGGER roads ROADS_RUN_TASK_COMPLETED" in message for _, message in published)


def test_run_roads_prepare_rq_fails_when_mod_not_enabled(
    roads_rq_environment,
    monkeypatch: pytest.MonkeyPatch,
):
    published, base_path, clear_calls = roads_rq_environment
    wd = str(base_path / "demo")
    RonStub.getInstance(wd).mods = []

    with pytest.raises(ValueError, match="not enabled"):
        roads_rq.run_roads_prepare_rq("demo")

    assert clear_calls == [("demo", "roads.nodb")]
    assert any("EXCEPTION run_roads_prepare_rq(demo)" in message for _, message in published)


def test_run_roads_rq_fails_when_runtime_lock_busy(
    roads_rq_environment,
    monkeypatch: pytest.MonkeyPatch,
):
    published, _base_path, clear_calls = roads_rq_environment
    monkeypatch.setattr(roads_rq, "acquire_roads_runtime_lock", lambda _runid, _owner: False)

    with pytest.raises(roads_rq.RoadsSingleFlightConflict, match="already running"):
        roads_rq.run_roads_rq("demo")

    assert clear_calls == []
    assert any("EXCEPTION run_roads_rq(demo)" in message for _, message in published)
