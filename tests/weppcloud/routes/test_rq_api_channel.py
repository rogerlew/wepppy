from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Dict, Tuple

import pytest
from flask import Flask

import wepppy.weppcloud.routes.rq.api.api as rq_api_module

RUN_ID = "test-run"
CONFIG = "cfg"


@pytest.fixture()
def rq_channel_client(monkeypatch: pytest.MonkeyPatch, tmp_path):
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
            self.run_group = "default"
            self._mcl: float | None = None
            self._csa: float | None = None
            self._wbt_fill_or_breach: str | None = None
            self._wbt_blc_dist: int | None = None
            self._set_extent_mode: int | None = None
            self._map_bounds_text: str = ""
            self.delineation_backend_is_wbt = True
            self._lock_calls = 0

        @classmethod
        def getInstance(cls, wd: str) -> "DummyWatershed":
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

        @contextmanager
        def locked(self):
            self._lock_calls += 1
            yield

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
        def __init__(self, job_id: str = "job-123") -> None:
            self.id = job_id

    class DummyQueue:
        def __init__(self, connection: str) -> None:
            state["queue_connection"] = connection

        def enqueue_call(self, func, args: Tuple[Any, ...] = (), timeout: int | None = None) -> DummyJob:
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


def test_fetch_dem_and_build_channels_accepts_json_payload(rq_channel_client):
    client, DummyWatershed, DummyRedisPrep, state = rq_channel_client

    payload = {
        "map_center": [-117.52, 46.88],
        "map_zoom": 13,
        "map_bounds": [-118.0, 46.5, -117.0, 47.0],
        "map_distance": 12000,
        "mcl": 60,
        "csa": 5,
        "wbt_fill_or_breach": "breach",
        "wbt_blc_dist": 500,
        "set_extent_mode": 1,
        "map_bounds_text": "-118.0, 46.5, -117.0, 47.0",
    }

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/rq/api/fetch_dem_and_build_channels",
        json=payload,
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["Success"] is True
    assert body["job_id"] == "job-123"

    queue_call = state["queue_calls"][0]
    assert queue_call["func"] is rq_api_module.fetch_dem_and_build_channels_rq
    args = queue_call["args"]
    assert args[0] == RUN_ID
    assert args[1] == payload["map_bounds"]
    assert args[2] == payload["map_center"]
    assert args[3] == pytest.approx(float(payload["map_zoom"]))
    assert args[4] == pytest.approx(float(payload["csa"]))
    assert args[5] == pytest.approx(float(payload["mcl"]))
    assert args[6] == "breach"
    assert args[7] == 500
    assert args[8] == 1
    assert args[9] == payload["map_bounds_text"]

    prep = DummyRedisPrep.getInstance(state["run_dir"])
    assert rq_api_module.TaskEnum.fetch_dem in prep.removed
    assert rq_api_module.TaskEnum.build_channels in prep.removed
    assert prep.job_ids["fetch_dem_and_build_channels_rq"] == "job-123"

    assert state["redis"] == ["enter", "exit"]


def test_fetch_dem_and_build_channels_accepts_form_payload(rq_channel_client):
    client, DummyWatershed, DummyRedisPrep, state = rq_channel_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/rq/api/fetch_dem_and_build_channels",
        data={
            "map_center": "-117.52,46.88",
            "map_zoom": "12",
            "map_bounds": "-118.0,46.5,-117.0,47.0",
            "mcl": "45",
            "csa": "4.5",
            "set_extent_mode": "0",
            "map_bounds_text": "",
        },
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["Success"] is True

    queue_call = state["queue_calls"][0]
    args = queue_call["args"]
    assert args[1] == [-118.0, 46.5, -117.0, 47.0]
    assert args[2] == [-117.52, 46.88]
    assert args[3] == pytest.approx(12.0)
    assert args[4] == pytest.approx(4.5)
    assert args[5] == pytest.approx(45.0)
    assert args[6] is None
    assert args[7] is None
    assert args[8] == 0


def test_fetch_dem_and_build_channels_batch_mode_short_circuits(rq_channel_client):
    client, DummyWatershed, DummyRedisPrep, state = rq_channel_client

    watershed = DummyWatershed.getInstance(state["run_dir"])
    watershed.run_group = "batch"

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/rq/api/fetch_dem_and_build_channels",
        json={
            "map_center": [-117.0, 46.0],
            "map_zoom": 14,
            "map_bounds": [-118.0, 45.5, -116.5, 47.0],
            "mcl": 70,
            "csa": 6.5,
            "set_extent_mode": 1,
            "map_bounds_text": "manual bounds",
            "wbt_fill_or_breach": "breach",
            "wbt_blc_dist": 400,
        },
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["Success"] is True
    assert body["Content"] == 'Set watershed inputs for batch processing'

    assert "_lock_calls" in vars(watershed)
    assert watershed._lock_calls == 1
    assert watershed._mcl == pytest.approx(70.0)
    assert watershed._csa == pytest.approx(6.5)
    assert watershed._set_extent_mode == 1
    assert watershed._map_bounds_text == "manual bounds"
    assert watershed._wbt_fill_or_breach == "breach"
    assert watershed._wbt_blc_dist == 400

    assert "queue_calls" not in state or state["queue_calls"] == []
