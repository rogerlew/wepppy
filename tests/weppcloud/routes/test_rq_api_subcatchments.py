from __future__ import annotations

from typing import Any, Dict

import pytest
from flask import Flask

import wepppy.weppcloud.routes.rq.api.api as rq_api_module

from tests.factories.singleton import singleton_factory

RUN_ID = "test-run"
CONFIG = "cfg"

pytestmark = pytest.mark.unit


@pytest.fixture()
def rq_subcatchments_client(
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

    def fake_build_subcatchments_and_abstract_watershed_rq(runid: str) -> None:
        state.setdefault("build_calls", []).append(runid)

    monkeypatch.setattr(
        rq_api_module,
        "build_subcatchments_and_abstract_watershed_rq",
        fake_build_subcatchments_and_abstract_watershed_rq,
    )

    WatershedStub = singleton_factory(
        "WatershedStub",
        attrs={
            "clip_hillslopes": None,
            "clip_hillslope_length": None,
            "walk_flowpaths": None,
            "mofe_target_length": None,
            "mofe_buffer": None,
            "mofe_buffer_length": None,
            "bieger2015_widths": None,
            "run_group": "default",
        },
    )

    monkeypatch.setattr(rq_api_module, "Watershed", WatershedStub)

    env = rq_environment
    env.patch_module(monkeypatch, rq_api_module, default_job_id="job-999")

    with app.test_client() as client:
        yield client, WatershedStub, env, state

    WatershedStub.reset_instances()
    env.redis_prep_class.reset_instances()
    env.recorder.reset()
    state.clear()


def test_api_build_subcatchments_accepts_json_payload(rq_subcatchments_client):
    client, WatershedStub, env, state = rq_subcatchments_client

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

    watershed = WatershedStub.getInstance(state["run_dir"])
    assert watershed.clip_hillslopes is True
    assert watershed.clip_hillslope_length == 275
    assert watershed.walk_flowpaths is False
    assert watershed.mofe_target_length == 42.5
    assert watershed.mofe_buffer is True
    assert watershed.mofe_buffer_length == 10.0
    assert watershed.bieger2015_widths is True

    prep = env.redis_prep_class.getInstance(state["run_dir"])
    assert rq_api_module.TaskEnum.abstract_watershed in prep.removed
    assert rq_api_module.TaskEnum.build_subcatchments in prep.removed
    assert prep.job_ids["build_subcatchments_and_abstract_watershed_rq"] == "job-999"

    queue_call = env.recorder.queue_calls[0]
    assert queue_call.func is rq_api_module.build_subcatchments_and_abstract_watershed_rq
    assert queue_call.args == (RUN_ID,)
    assert queue_call.timeout == rq_api_module.TIMEOUT
    entries = env.recorder.redis_entries
    assert "enter" in entries and "exit" in entries


def test_api_build_subcatchments_short_circuits_for_batch_runs(rq_subcatchments_client):
    client, WatershedStub, env, state = rq_subcatchments_client

    watershed = WatershedStub.getInstance(state["run_dir"])
    watershed.run_group = "batch"

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/rq/api/build_subcatchments_and_abstract_watershed",
        json={"clip_hillslopes": False},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body == {"Success": True, "Content": "Set watershed inputs for batch processing"}
    assert env.recorder.queue_calls == []
    prep = env.redis_prep_class.getInstance(state["run_dir"])
    assert not prep.job_ids
