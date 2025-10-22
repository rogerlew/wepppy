from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Tuple

import json
import pytest
from flask import Flask

import wepppy.weppcloud.routes.rq.api.api as rq_api_module

RUN_ID = "test-run"
CONFIG = "cfg"


@pytest.fixture()
def rq_omni_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
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

    class DummyOmni:
        _instances: Dict[str, "DummyOmni"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.scenario_calls: List[List[Tuple[Any, Dict[str, Any]]]] = []

        @classmethod
        def getInstance(cls, wd: str) -> "DummyOmni":
            inst = cls._instances.get(wd)
            if inst is None:
                inst = cls(wd)
                cls._instances[wd] = inst
            return inst

        def parse_scenarios(self, payload: List[Tuple[Any, Dict[str, Any]]]) -> None:
            self.scenario_calls.append(payload)

    monkeypatch.setattr(rq_api_module, "Omni", DummyOmni)

    class DummyRedisPrep:
        _instances: Dict[str, "DummyRedisPrep"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.removed: List[Any] = []
            self.job_ids: Dict[str, str] = {}

        @classmethod
        def getInstance(cls, wd: str) -> "DummyRedisPrep":
            inst = cls._instances.get(wd)
            if inst is None:
                inst = cls(wd)
                cls._instances[wd] = inst
            return inst

        def remove_timestamp(self, task) -> None:  # noqa: ANN001 - mirror signature
            self.removed.append(task)

        def set_rq_job_id(self, key: str, job_id: str) -> None:
            self.job_ids[key] = job_id

    monkeypatch.setattr(rq_api_module, "RedisPrep", DummyRedisPrep)

    class DummyRedisConn:
        def __enter__(self) -> str:
            state.setdefault("redis", []).append("enter")
            return "redis-conn"

        def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover
            state.setdefault("redis", []).append("exit")

    monkeypatch.setattr(rq_api_module, "_redis_conn", lambda: DummyRedisConn())

    class DummyJob:
        def __init__(self, job_id: str = "job-omni") -> None:
            self.id = job_id

    def fake_enqueue(func, args=(), timeout=None):  # noqa: ANN001
        state.setdefault("queue_calls", []).append({"func": func, "args": args, "timeout": timeout})
        return DummyJob()

    class DummyQueue:
        def __init__(self, connection: str) -> None:
            state["queue_connection"] = connection

        def enqueue_call(self, func, args=(), timeout=None):  # noqa: ANN001
            return fake_enqueue(func, args, timeout)

    monkeypatch.setattr(rq_api_module, "Queue", DummyQueue)

    def fake_run_omni_scenarios_rq(runid: str) -> None:
        state.setdefault("job_funcs", []).append(runid)

    monkeypatch.setattr(rq_api_module, "run_omni_scenarios_rq", fake_run_omni_scenarios_rq)

    def fake_save_run_file(**kwargs):  # noqa: ANN001
        dest = Path(kwargs["run_root"]) / kwargs["dest_subdir"] / "stub.tif"
        dest.parent.mkdir(parents=True, exist_ok=True)
        return dest

    monkeypatch.setattr(rq_api_module, "save_run_file", fake_save_run_file)

    with app.test_client() as client:
        yield client, DummyOmni, DummyRedisPrep, state

    DummyOmni._instances.clear()
    DummyRedisPrep._instances.clear()
    state.clear()


def test_api_run_omni_accepts_json_payload(rq_omni_client):
    client, DummyOmni, DummyRedisPrep, state = rq_omni_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/rq/api/run_omni",
        json={"scenarios": [{"type": "uniform_low"}]},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Success"] is True
    assert payload["job_id"] == "job-omni"

    omni = DummyOmni.getInstance(state["run_dir"])
    assert len(omni.scenario_calls) == 1
    scenario_enum, scenario_params = omni.scenario_calls[0][0]
    assert scenario_enum is rq_api_module.OmniScenario.UniformLow
    assert scenario_params == {"type": "uniform_low"}

    prep = DummyRedisPrep.getInstance(state["run_dir"])
    assert rq_api_module.TaskEnum.run_omni_scenarios in prep.removed
    assert prep.job_ids["run_omni_rq"] == "job-omni"
    assert state["redis"] == ["enter", "exit"]
    assert state["queue_calls"][0]["func"] is rq_api_module.run_omni_scenarios_rq
    assert state["queue_calls"][0]["args"] == (RUN_ID,)


def test_api_run_omni_requires_sbs_upload(rq_omni_client):
    client, DummyOmni, DummyRedisPrep, state = rq_omni_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/rq/api/run_omni",
        data={
            "scenarios": json.dumps([{"type": "sbs_map"}]),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Success"] is False
    assert "Missing SBS file" in payload["Error"]

    # queue should not be invoked on error
    assert "queue_calls" not in state


def test_api_run_omni_uploads_sbs_files(rq_omni_client):
    client, DummyOmni, DummyRedisPrep, state = rq_omni_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/rq/api/run_omni",
        data={
            "scenarios": json.dumps([{"type": "sbs_map"}]),
            "scenarios[0][sbs_file]": (BytesIO(b"fake"), "layer.tif"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Success"] is True

    omni = DummyOmni.getInstance(state["run_dir"])
    scenario_enum, params = omni.scenario_calls[0][0]
    assert scenario_enum is rq_api_module.OmniScenario.SBSmap
    assert params["type"] == "sbs_map"
    assert params["sbs_file_path"].endswith("stub.tif")
