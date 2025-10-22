from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any, Dict

import pytest
from flask import Flask

import wepppy.weppcloud.routes.rq.api.api as rq_api_module

from tests.factories.singleton import LockedMixin, ParseInputsRecorderMixin, singleton_factory

RUN_ID = "test-run"
CONFIG = "cfg"


@pytest.fixture()
def rq_ash_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    rq_environment,
):
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(rq_api_module.rq_api_bp)

    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()
    (run_dir / "ash").mkdir()

    state: Dict[str, Any] = {"run_dir": str(run_dir)}

    monkeypatch.setattr(rq_api_module, "get_wd", lambda runid: str(run_dir))

    def _parse_inputs(self, payload: Dict[str, Any]) -> None:
        ParseInputsRecorderMixin.parse_inputs(self, payload.copy())

    def _ash_load_fn(self) -> str | None:
        return getattr(self, "_ash_load_fn", None)

    def _locked(self):
        return LockedMixin.locked(self)

    AshStub = singleton_factory(
        "AshStub",
        attrs={
            "ash_dir": str(run_dir / "ash"),
            "_ash_load_fn": str(run_dir / "ash" / "default_load.tif"),
            "_ash_type_map_fn": None,
            "_spatial_mode": rq_api_module.AshSpatialMode.Single,
            "ash_depth_mode": None,
        },
        methods={
            "parse_inputs": _parse_inputs,
            "ash_load_fn": property(_ash_load_fn),
            "locked": _locked,
        },
        mixins=(ParseInputsRecorderMixin, LockedMixin),
    )

    monkeypatch.setattr(rq_api_module, "Ash", AshStub)

    env = rq_environment
    env.patch_module(monkeypatch, rq_api_module, default_job_id="job-ash")

    def fake_run_ash_rq(runid: str, fire_date: str, white_depth: float, black_depth: float) -> None:
        state.setdefault("rq_calls", []).append(
            {
                "runid": runid,
                "fire_date": fire_date,
                "white_depth": white_depth,
                "black_depth": black_depth,
            }
        )

    monkeypatch.setattr(rq_api_module, "run_ash_rq", fake_run_ash_rq)

    def fake_upload(runid: str, config: str, field: str, *, required: bool = True, overwrite: bool = True) -> str | None:
        state.setdefault("uploads", []).append({"field": field, "required": required})
        if required and field == "input_upload_ash_load":
            return "ash_load_uploaded.tif"
        if field == "input_upload_ash_type_map":
            return "ash_type_uploaded.tif"
        return None

    monkeypatch.setattr(rq_api_module, "_task_upload_ash_map", fake_upload)

    with app.test_client() as client:
        yield client, AshStub, env, state

    AshStub.reset_instances()
    env.redis_prep_class.reset_instances()
    env.recorder.reset()
    state.clear()


def test_run_ash_depth_mode_one_enqueues_job(rq_ash_client):
    client, AshStub, env, state = rq_ash_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/rq/api/run_ash",
        json={
            "ash_depth_mode": 1,
            "fire_date": "8/04",
            "ini_black_depth": 3.2,
            "ini_white_depth": 4.4,
            "field_black_bulkdensity": 0.7,
            "field_white_bulkdensity": 0.8,
            "ash_model": "multi",
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Success"] is True
    assert payload["job_id"] == "job-ash"

    ash = AshStub.getInstance(state["run_dir"])
    assert ash.ash_depth_mode == 1
    assert ash.parse_inputs_calls
    parsed_payload = ash.parse_inputs_calls[0]
    assert parsed_payload["ash_model"] == "multi"
    assert parsed_payload["field_black_bulkdensity"] == 0.7

    prep = env.redis_prep_class.getInstance(state["run_dir"])
    assert rq_api_module.TaskEnum.run_watar in prep.removed
    assert prep.job_ids["run_ash_rq"] == "job-ash"

    queue_call = env.recorder.queue_calls[0]
    assert queue_call.func is rq_api_module.run_ash_rq
    assert queue_call.args == (RUN_ID, "8/04", 4.4, 3.2)
    entries = env.recorder.redis_entries
    assert "enter" in entries and "exit" in entries


def test_run_ash_mode_zero_converts_loads(rq_ash_client):
    client, AshStub, env, state = rq_ash_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/rq/api/run_ash",
        json={
            "ash_depth_mode": 0,
            "ini_black_load": 12.0,
            "ini_white_load": 10.0,
            "field_black_bulkdensity": 2.0,
            "field_white_bulkdensity": 1.0,
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Success"] is True

    queue_call = env.recorder.queue_calls[0]
    assert queue_call.args[2] == pytest.approx(10.0)
    assert queue_call.args[3] == pytest.approx(6.0)


def test_run_ash_mode_two_handles_uploads(rq_ash_client):
    client, AshStub, env, state = rq_ash_client

    ash = AshStub.getInstance(state["run_dir"])
    ash._ash_load_fn = None

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/rq/api/run_ash",
        data={
            "ash_depth_mode": "2",
            "input_upload_ash_load": (BytesIO(b"fake"), "load.tif"),
            "input_upload_ash_type_map": (BytesIO(b"fake"), "type.tif"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    res_json = response.get_json()
    assert res_json["Success"] is True

    assert state["uploads"][0]["field"] == "input_upload_ash_load"
    assert state["uploads"][1]["field"] == "input_upload_ash_type_map"

    assert ash._ash_load_fn == "ash_load_uploaded.tif"
    assert ash._ash_type_map_fn == "ash_type_uploaded.tif"
    assert ash._spatial_mode is rq_api_module.AshSpatialMode.Gridded
    assert ash.ash_depth_mode == 2


def test_run_ash_missing_required_fields_returns_error(rq_ash_client):
    client, AshStub, env, state = rq_ash_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/rq/api/run_ash",
        json={
            "ash_depth_mode": 1,
            "ini_black_depth": 2.5,
            "ini_white_depth": "not-a-number",
        },
    )

    assert response.status_code == 500
    payload = response.get_json()
    assert payload["Success"] is False
    assert "Field must be numeric" in payload["Error"]

    assert env.recorder.queue_calls == []


def test_run_ash_mode_two_missing_load_errors(monkeypatch: pytest.MonkeyPatch, rq_ash_client):
    client, AshStub, env, state = rq_ash_client

    def raise_upload(*args, **kwargs):
        raise ValueError("Missing file for input_upload_ash_load")

    monkeypatch.setattr(rq_api_module, "_task_upload_ash_map", raise_upload)

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/rq/api/run_ash",
        data={
            "ash_depth_mode": "2",
            "input_upload_ash_type_map": (BytesIO(b"fake"), "type.tif"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 500
    payload = response.get_json()
    assert payload["Success"] is False
    assert "Missing file" in payload["Error"]

    assert env.recorder.queue_calls == []
