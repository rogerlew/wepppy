from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Tuple

import pytest
from flask import Flask

import wepppy.weppcloud.routes.rq.api.api as rq_api_module

RUN_ID = "test-run"
CONFIG = "cfg"


@pytest.fixture()
def rq_landuse_client(monkeypatch: pytest.MonkeyPatch, tmp_path):
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

    class DummyLanduse:
        _instances: Dict[str, "DummyLanduse"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.mods = ["disturbed"]
            self.mode = rq_api_module.LanduseMode.Gridded
            self.mapping: str | None = None
            self.mofe_buffer_selection: int | None = None
            self.run_group = "default"
            self.parse_inputs_calls: list[Dict[str, Any]] = []
            self.lc_dir = str(run_dir)
            self.lc_fn = str(run_dir / "landuse.img")

        @classmethod
        def getInstance(cls, wd: str) -> "DummyLanduse":
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

        def parse_inputs(self, payload: Dict[str, Any]) -> None:
            self.parse_inputs_calls.append(payload)
            raw = payload.get("mofe_buffer_selection")
            if isinstance(raw, (list, tuple)):
                raw = raw[0] if raw else None
            if raw not in (None, ""):
                self.mofe_buffer_selection = int(raw)

    monkeypatch.setattr(rq_api_module, "Landuse", DummyLanduse)

    class DummyDisturbed:
        _instances: Dict[str, "DummyDisturbed"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.burn_shrubs = False
            self.burn_grass = False

        @classmethod
        def getInstance(cls, wd: str) -> "DummyDisturbed":
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

    monkeypatch.setattr(rq_api_module, "Disturbed", DummyDisturbed)

    class DummyWatershed:
        _instances: Dict[str, "DummyWatershed"] = {}

        def __init__(self, wd: str) -> None:
            self.subwta = "subwta"

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
        def __init__(self, job_id: str = "job-123") -> None:
            self.id = job_id

    def fake_build_landuse_rq(runid: str) -> None:
        state.setdefault("build_calls", []).append(runid)

    monkeypatch.setattr(rq_api_module, "build_landuse_rq", fake_build_landuse_rq)

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
        yield client, DummyLanduse, DummyDisturbed, DummyRedisPrep, state

    DummyLanduse._instances.clear()
    DummyDisturbed._instances.clear()
    DummyWatershed._instances.clear()
    DummyRedisPrep._instances.clear()
    state.clear()


def test_api_build_landuse_parses_payload_and_toggles(rq_landuse_client):
    client, DummyLanduse, DummyDisturbed, DummyRedisPrep, state = rq_landuse_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/rq/api/build_landuse",
        json={
            "mofe_buffer_selection": 12,
            "checkbox_burn_shrubs": True,
            "checkbox_burn_grass": False,
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Success"] is True
    assert payload["job_id"] == "job-123"

    landuse = DummyLanduse.getInstance(state["run_dir"])
    assert landuse.mofe_buffer_selection == 12
    assert landuse.parse_inputs_calls, "parse_inputs should be invoked for payload normalisation"

    disturbed = DummyDisturbed.getInstance(landuse.wd)
    assert disturbed.burn_shrubs is True
    assert disturbed.burn_grass is False

    prep = DummyRedisPrep.getInstance(landuse.wd)
    assert rq_api_module.TaskEnum.build_landuse in prep.removed
    assert prep.job_ids["build_landuse_rq"] == "job-123"

    queue_call = state["queue_calls"][0]
    assert queue_call["func"] is rq_api_module.build_landuse_rq
    assert queue_call["args"] == (RUN_ID,)
    assert state["redis"] == ["enter", "exit"]


def test_api_build_landuse_requires_mapping_for_user_defined(rq_landuse_client):
    client, DummyLanduse, DummyDisturbed, DummyRedisPrep, state = rq_landuse_client
    landuse = DummyLanduse.getInstance(state["run_dir"])
    landuse.mode = rq_api_module.LanduseMode.UserDefined
    landuse.mods = []

    response = client.post(f"/runs/{RUN_ID}/{CONFIG}/rq/api/build_landuse", json={})

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Success"] is False
    assert "landuse_management_mapping_selection" in payload["Error"]
    assert state.get("queue_calls") is None
    assert landuse.mapping is None


def test_api_build_landuse_user_defined_upload(monkeypatch: pytest.MonkeyPatch, rq_landuse_client):
    client, DummyLanduse, DummyDisturbed, DummyRedisPrep, state = rq_landuse_client
    landuse = DummyLanduse.getInstance(state["run_dir"])
    landuse.mode = rq_api_module.LanduseMode.UserDefined
    landuse.mods = []

    import wepppy.all_your_base.geo as geo_module

    def fake_raster_stacker(src: str, subwta: Any, dest: str) -> None:
        Path(dest).write_bytes(b"ok")
        state["raster_stacker_args"] = (src, subwta, dest)

    monkeypatch.setattr(geo_module, "raster_stacker", fake_raster_stacker)

    data = {
        "landuse_management_mapping_selection": " disturbed ",
        "mofe_buffer_selection": "5",
        "input_upload_landuse": (BytesIO(b"fake"), "custom_map.tif"),
    }

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/rq/api/build_landuse",
        data=data,
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Success"] is True

    assert landuse.mapping == "disturbed"
    assert landuse.mofe_buffer_selection == 5
    assert "raster_stacker_args" in state
    queue_call = state["queue_calls"][0]
    assert queue_call["args"] == (RUN_ID,)
    prep = DummyRedisPrep.getInstance(state["run_dir"])
    assert rq_api_module.TaskEnum.build_landuse in prep.removed
    assert state["redis"] == ["enter", "exit"]
