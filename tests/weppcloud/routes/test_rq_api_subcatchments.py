from __future__ import annotations

from typing import Any, Dict, Tuple

import pytest
from flask import Flask

import wepppy.weppcloud.routes.rq.api.api as rq_api_module

RUN_ID = "test-run"
CONFIG = "cfg"

pytestmark = pytest.mark.unit


@pytest.fixture()
def rq_subcatchments_client(monkeypatch: pytest.MonkeyPatch, tmp_path):
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(rq_api_module.rq_api_bp)

    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()

    state: Dict[str, Any] = {"run_dir": str(run_dir)}

    def fake_get_wd(runid: str) -> str:
        assert runid == RUN_ID
        return str(run_dir)

    monkeypatch.setattr(rq_api_module, "get_wd", fake_get_wd)

    class DummyWatershed:
        _instances: Dict[str, "DummyWatershed"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.clip_hillslopes: bool | None = None
            self.clip_hillslope_length: float | None = None
            self.walk_flowpaths: bool | None = None
            self.mofe_target_length: float | None = None
            self.mofe_buffer: bool | None = None
            self.mofe_buffer_length: float | None = None
            self.bieger2015_widths: bool | None = None
            self.run_group: str = "default"

        @classmethod
        def getInstance(cls, wd: str) -> "DummyWatershed":
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

    monkeypatch.setattr(rq_api_module, "Watershed", DummyWatershed)

    class DummyRedisPrep:
        _instances: Dict[str, "DummyRedisPrep"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.removed: list[Any] = []
            self.job_ids: Dict[str, str] = {}

        @classmethod
        def getInstance(cls, wd: str) -> "DummyRedisPrep":
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

        def remove_timestamp(self, task) -> None:  # noqa: ANN001 - mirror signature
            self.removed.append(task)

        def set_rq_job_id(self, key: str, job_id: str) -> None:
            self.job_ids[key] = job_id

    monkeypatch.setattr(rq_api_module, "RedisPrep", DummyRedisPrep)

    class DummyRedisConn:
        def __enter__(self) -> str:
            state.setdefault("redis", []).append("enter")
            return "redis-conn"

        def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - errors bubble automatically
            state.setdefault("redis", []).append("exit")

    monkeypatch.setattr(rq_api_module, "_redis_conn", lambda: DummyRedisConn())

    class DummyJob:
        def __init__(self, job_id: str = "job-999") -> None:
            self.id = job_id

    def fake_build_subcatchments_and_abstract_watershed_rq(runid: str) -> None:
        state.setdefault("build_calls", []).append(runid)

    monkeypatch.setattr(
        rq_api_module,
        "build_subcatchments_and_abstract_watershed_rq",
        fake_build_subcatchments_and_abstract_watershed_rq,
    )

    class DummyQueue:
        def __init__(self, connection: str) -> None:
            state["queue_connection"] = connection

        def enqueue_call(
            self,
            func,
            args: Tuple[Any, ...] = (),
            timeout: int | None = None,
        ) -> DummyJob:
            job = DummyJob()
            state.setdefault("queue_calls", []).append(
                {"func": func, "args": args, "timeout": timeout, "job": job}
            )
            return job

    monkeypatch.setattr(rq_api_module, "Queue", DummyQueue)

    with app.test_client() as client:
        yield client, DummyWatershed, DummyRedisPrep, state

    DummyWatershed._instances.clear()
    DummyRedisPrep._instances.clear()
    state.clear()


def test_api_build_subcatchments_accepts_json_payload(rq_subcatchments_client):
    client, DummyWatershed, DummyRedisPrep, state = rq_subcatchments_client

    payload = {
        "clip_hillslopes": True,
        "clip_hillslope_length": 275,
        "walk_flowpaths": False,
        "mofe_target_length": 42.5,
        "mofe_buffer": True,
        "mofe_buffer_length": 10.0,
        "bieger2015_widths": True,
    }

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/rq/api/build_subcatchments_and_abstract_watershed",
        json=payload,
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body == {"Success": True, "job_id": "job-999"}

    watershed = DummyWatershed.getInstance(state["run_dir"])
    assert watershed.clip_hillslopes is True
    assert watershed.clip_hillslope_length == 275
    assert watershed.walk_flowpaths is False
    assert watershed.mofe_target_length == 42.5
    assert watershed.mofe_buffer is True
    assert watershed.mofe_buffer_length == 10.0
    assert watershed.bieger2015_widths is True

    prep = DummyRedisPrep.getInstance(state["run_dir"])
    assert rq_api_module.TaskEnum.abstract_watershed in prep.removed
    assert rq_api_module.TaskEnum.build_subcatchments in prep.removed
    assert prep.job_ids["build_subcatchments_and_abstract_watershed_rq"] == "job-999"

    queue_call = state["queue_calls"][0]
    assert queue_call["func"] is rq_api_module.build_subcatchments_and_abstract_watershed_rq
    assert queue_call["args"] == (RUN_ID,)
    assert queue_call["timeout"] == rq_api_module.TIMEOUT
    assert state["redis"] == ["enter", "exit"]


def test_api_build_subcatchments_short_circuits_for_batch_runs(rq_subcatchments_client):
    client, DummyWatershed, DummyRedisPrep, state = rq_subcatchments_client

    watershed = DummyWatershed.getInstance(state["run_dir"])
    watershed.run_group = "batch"

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/rq/api/build_subcatchments_and_abstract_watershed",
        json={"clip_hillslopes": False},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body == {"Success": True, "Content": "Set watershed inputs for batch processing"}
    assert "queue_calls" not in state
    prep = DummyRedisPrep.getInstance(state["run_dir"])
    assert not prep.job_ids
