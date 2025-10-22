from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest
from flask import Flask

import wepppy.weppcloud.routes.rq.api.api as rq_api_module

from tests.factories.singleton import singleton_factory

RUN_ID = "test-run"
CONFIG = "cfg"


@pytest.fixture()
def rq_omni_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
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

    def _parse_scenarios(self, payload: List[Tuple[Any, Dict[str, Any]]]) -> None:
        self.scenario_calls.append(payload)

    OmniStub = singleton_factory(
        "OmniStub",
        attrs={"scenario_calls": []},
        methods={"parse_scenarios": _parse_scenarios},
    )

    monkeypatch.setattr(rq_api_module, "Omni", OmniStub)

    env = rq_environment
    env.patch_module(monkeypatch, rq_api_module, default_job_id="job-omni")

    def fake_run_omni_scenarios_rq(runid: str) -> None:
        state.setdefault("job_funcs", []).append(runid)

    monkeypatch.setattr(rq_api_module, "run_omni_scenarios_rq", fake_run_omni_scenarios_rq)

    def fake_save_run_file(**kwargs):  # noqa: ANN001
        dest = Path(kwargs["run_root"]) / kwargs["dest_subdir"] / "stub.tif"
        dest.parent.mkdir(parents=True, exist_ok=True)
        return dest

    monkeypatch.setattr(rq_api_module, "save_run_file", fake_save_run_file)

    with app.test_client() as client:
        yield client, OmniStub, env, state

    OmniStub.reset_instances()
    env.redis_prep_class.reset_instances()
    env.recorder.reset()
    state.clear()


def test_api_run_omni_accepts_json_payload(rq_omni_client):
    client, OmniStub, env, state = rq_omni_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/rq/api/run_omni",
        json={"scenarios": [{"type": "uniform_low"}]},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Success"] is True
    assert payload["job_id"] == "job-omni"

    omni = OmniStub.getInstance(state["run_dir"])
    assert len(omni.scenario_calls) == 1
    scenario_enum, scenario_params = omni.scenario_calls[0][0]
    assert scenario_enum is rq_api_module.OmniScenario.UniformLow
    assert scenario_params == {"type": "uniform_low"}

    prep = env.redis_prep_class.getInstance(state["run_dir"])
    assert rq_api_module.TaskEnum.run_omni_scenarios in prep.removed
    assert prep.job_ids["run_omni_rq"] == "job-omni"

    entries = env.recorder.redis_entries
    assert "enter" in entries and "exit" in entries

    queue_call = env.recorder.queue_calls[0]
    assert queue_call.func is rq_api_module.run_omni_scenarios_rq
    assert queue_call.args == (RUN_ID,)


def test_api_run_omni_requires_sbs_upload(rq_omni_client):
    client, OmniStub, env, state = rq_omni_client

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

    assert env.recorder.queue_calls == []


def test_api_run_omni_uploads_sbs_files(rq_omni_client):
    client, OmniStub, env, state = rq_omni_client

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

    omni = OmniStub.getInstance(state["run_dir"])
    scenario_enum, params = omni.scenario_calls[0][0]
    assert scenario_enum is rq_api_module.OmniScenario.SBSmap
    assert params["type"] == "sbs_map"
    assert params["sbs_file_path"].endswith("stub.tif")

    queue_call = env.recorder.queue_calls[0]
    assert queue_call.func is rq_api_module.run_omni_scenarios_rq
