from __future__ import annotations

from typing import Any, Dict, Tuple

import pytest
from flask import Flask

import wepppy.weppcloud.routes.rq.api.api as rq_api_module

RUN_ID = "run-id"
CONFIG = "cfg"


pytestmark = pytest.mark.routes


@pytest.fixture()
def rq_outlet_client(monkeypatch: pytest.MonkeyPatch, tmp_path):
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

        def remove_timestamp(self, task) -> None:  # noqa: ANN001
            self.removed.append(task)

        def set_rq_job_id(self, key: str, job_id: str) -> None:
            self.job_ids[key] = job_id

    monkeypatch.setattr(rq_api_module, "RedisPrep", DummyRedisPrep)

    class DummyQueue:
        def __init__(self, connection: str) -> None:
            state["queue_connection"] = connection

        def enqueue_call(self, func, args: Tuple[Any, ...] = (), timeout: int | None = None):
            job = type("DummyJob", (), {"id": "job-456"})()
            state.setdefault("queue_calls", []).append(
                {"func": func, "args": args, "timeout": timeout, "job": job}
            )
            return job

    monkeypatch.setattr(rq_api_module, "Queue", DummyQueue)

    class DummyRedisConn:
        def __enter__(self) -> str:
            state.setdefault("redis_calls", []).append("enter")
            return "redis-conn"

        def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - errors bubble automatically
            state.setdefault("redis_calls", []).append("exit")

    monkeypatch.setattr(rq_api_module, "_redis_conn", lambda: DummyRedisConn())

    def fake_set_outlet_rq(runid: str, lng: float, lat: float) -> None:
        state.setdefault("jobs", []).append({"runid": runid, "lng": lng, "lat": lat})

    monkeypatch.setattr(rq_api_module, "set_outlet_rq", fake_set_outlet_rq)

    with app.test_client() as client:
        yield client, DummyRedisPrep, state

    DummyRedisPrep._instances.clear()
    state.clear()


def test_api_set_outlet_accepts_json_payload(rq_outlet_client):
    client, DummyRedisPrep, state = rq_outlet_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/rq/api/set_outlet",
        json={"latitude": 44.1, "longitude": -117.5},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {"Success": True, "job_id": "job-456"}

    prep = DummyRedisPrep.getInstance(state["run_dir"])
    assert rq_api_module.TaskEnum.set_outlet in prep.removed
    assert prep.job_ids["set_outlet_rq"] == "job-456"

    queue_call = state["queue_calls"][0]
    assert queue_call["func"] is rq_api_module.set_outlet_rq
    assert queue_call["args"] == (RUN_ID, -117.5, 44.1)
    assert state["redis_calls"] == ["enter", "exit"]


def test_api_set_outlet_accepts_coordinate_object(rq_outlet_client):
    client, DummyRedisPrep, state = rq_outlet_client
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/rq/api/set_outlet",
        json={"coordinates": {"lat": 43.2, "lng": -118.9}},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Success"] is True

    queue_call = state["queue_calls"][0]
    assert queue_call["args"] == (RUN_ID, -118.9, 43.2)


def test_api_set_outlet_requires_coordinates(rq_outlet_client):
    client, _, _ = rq_outlet_client
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/rq/api/set_outlet",
        json={"latitude": None, "longitude": -120},
    )

    assert response.status_code == 500
    data = response.get_json()
    assert data["Success"] is False
    assert "latitude and longitude must be provided as floats" in data["Error"]
