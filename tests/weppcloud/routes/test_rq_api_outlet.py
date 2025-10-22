from __future__ import annotations

from typing import Any, Dict

import pytest
from flask import Flask

import wepppy.weppcloud.routes.rq.api.api as rq_api_module

RUN_ID = "run-id"
CONFIG = "cfg"


pytestmark = pytest.mark.routes


@pytest.fixture()
def rq_outlet_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    rq_environment,
):
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

    env = rq_environment
    env.patch_module(
        monkeypatch,
        rq_api_module,
        default_job_id="job-456",
    )

    def fake_set_outlet_rq(runid: str, lng: float, lat: float) -> None:
        state.setdefault("jobs", []).append({"runid": runid, "lng": lng, "lat": lat})

    monkeypatch.setattr(rq_api_module, "set_outlet_rq", fake_set_outlet_rq)

    with app.test_client() as client:
        yield client, env, state

    env.redis_prep_class.reset_instances()
    state.clear()


def test_api_set_outlet_accepts_json_payload(rq_outlet_client):
    client, env, state = rq_outlet_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/rq/api/set_outlet",
        json={"latitude": 44.1, "longitude": -117.5},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {"Success": True, "job_id": "job-456"}

    prep = env.redis_prep_class.getInstance(state["run_dir"])
    assert rq_api_module.TaskEnum.set_outlet in prep.removed
    assert prep.job_ids["set_outlet_rq"] == "job-456"

    queue_call = env.recorder.queue_calls[0]
    assert queue_call.func is rq_api_module.set_outlet_rq
    assert queue_call.args == (RUN_ID, -117.5, 44.1)
    entries = env.recorder.redis_entries
    assert "enter" in entries and "exit" in entries


def test_api_set_outlet_accepts_coordinate_object(rq_outlet_client):
    client, env, state = rq_outlet_client
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/rq/api/set_outlet",
        json={"coordinates": {"lat": 43.2, "lng": -118.9}},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Success"] is True

    queue_call = env.recorder.queue_calls[0]
    assert queue_call.args == (RUN_ID, -118.9, 43.2)


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
