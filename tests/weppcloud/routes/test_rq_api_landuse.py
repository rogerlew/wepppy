from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any, Dict

import pytest
from flask import Flask

import wepppy.weppcloud.routes.rq.api.api as rq_api_module

from tests.factories.singleton import ParseInputsRecorderMixin, singleton_factory

RUN_ID = "test-run"
CONFIG = "cfg"


@pytest.fixture()
def rq_landuse_client(
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

    def fake_build_landuse_rq(runid: str) -> None:
        state.setdefault("build_calls", []).append(runid)

    monkeypatch.setattr(rq_api_module, "build_landuse_rq", fake_build_landuse_rq)

    def _parse_inputs(self, payload: Dict[str, Any]) -> None:
        ParseInputsRecorderMixin.parse_inputs(self, payload)
        raw = payload.get("mofe_buffer_selection")
        if isinstance(raw, (list, tuple)):
            raw = raw[0] if raw else None
        if raw not in (None, ""):
            self.mofe_buffer_selection = int(raw)

    LanduseStub = singleton_factory(
        "LanduseStub",
        attrs={
            "mods": ["disturbed"],
            "mode": rq_api_module.LanduseMode.Gridded,
            "mapping": None,
            "mofe_buffer_selection": None,
            "run_group": "default",
            "lc_dir": str(run_dir),
            "lc_fn": str(run_dir / "landuse.img"),
        },
        methods={"parse_inputs": _parse_inputs},
        mixins=(ParseInputsRecorderMixin,),
    )

    DisturbedStub = singleton_factory(
        "DisturbedStub",
        attrs={"burn_shrubs": False, "burn_grass": False},
    )

    WatershedStub = singleton_factory(
        "WatershedStub",
        attrs={"subwta": "subwta"},
    )

    monkeypatch.setattr(rq_api_module, "Landuse", LanduseStub)
    monkeypatch.setattr(rq_api_module, "Disturbed", DisturbedStub)
    monkeypatch.setattr(rq_api_module, "Watershed", WatershedStub)

    env = rq_environment
    env.patch_module(monkeypatch, rq_api_module, default_job_id="job-123")

    with app.test_client() as client:
        yield client, LanduseStub, DisturbedStub, env, state

    LanduseStub.reset_instances()
    DisturbedStub.reset_instances()
    WatershedStub.reset_instances()
    env.redis_prep_class.reset_instances()
    env.recorder.reset()
    state.clear()


def test_api_build_landuse_parses_payload_and_toggles(rq_landuse_client):
    client, LanduseStub, DisturbedStub, env, state = rq_landuse_client

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

    landuse = LanduseStub.getInstance(state["run_dir"])
    assert landuse.mofe_buffer_selection == 12
    assert landuse.parse_inputs_calls, "parse_inputs should be invoked for payload normalisation"

    disturbed = DisturbedStub.getInstance(landuse.wd)
    assert disturbed.burn_shrubs is True
    assert disturbed.burn_grass is False

    prep = env.redis_prep_class.getInstance(landuse.wd)
    assert rq_api_module.TaskEnum.build_landuse in prep.removed
    assert prep.job_ids["build_landuse_rq"] == "job-123"

    queue_call = env.recorder.queue_calls[0]
    assert queue_call.func is rq_api_module.build_landuse_rq
    assert queue_call.args == (RUN_ID,)
    entries = env.recorder.redis_entries
    assert "enter" in entries and "exit" in entries


def test_api_build_landuse_requires_mapping_for_user_defined(rq_landuse_client):
    client, LanduseStub, DisturbedStub, env, state = rq_landuse_client
    landuse = LanduseStub.getInstance(state["run_dir"])
    landuse.mode = rq_api_module.LanduseMode.UserDefined
    landuse.mods = []

    response = client.post(f"/runs/{RUN_ID}/{CONFIG}/rq/api/build_landuse", json={})

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Success"] is False
    assert "landuse_management_mapping_selection" in payload["Error"]
    assert env.recorder.queue_calls == []
    assert landuse.mapping is None


def test_api_build_landuse_user_defined_upload(monkeypatch: pytest.MonkeyPatch, rq_landuse_client):
    client, LanduseStub, DisturbedStub, env, state = rq_landuse_client
    landuse = LanduseStub.getInstance(state["run_dir"])
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
    queue_call = env.recorder.queue_calls[0]
    assert queue_call.args == (RUN_ID,)
    prep = env.redis_prep_class.getInstance(state["run_dir"])
    assert rq_api_module.TaskEnum.build_landuse in prep.removed
    entries = env.recorder.redis_entries
    assert "enter" in entries and "exit" in entries
