from __future__ import annotations

from typing import Any, Dict

import pytest
from flask import Flask

import wepppy.weppcloud.routes.rq.api.api as rq_api_module

from tests.factories.singleton import LockedMixin, singleton_factory

RUN_ID = "test-run"
CONFIG = "cfg"


@pytest.fixture()
def rq_channel_client(
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

    WatershedStub = singleton_factory(
        "WatershedStub",
        attrs={
            "run_group": "default",
            "_mcl": None,
            "_csa": None,
            "_wbt_fill_or_breach": None,
            "_wbt_blc_dist": None,
            "_set_extent_mode": None,
            "_map_bounds_text": "",
            "delineation_backend_is_wbt": True,
        },
        mixins=(LockedMixin,),
    )

    monkeypatch.setattr(rq_api_module, "Watershed", WatershedStub)

    env = rq_environment
    env.patch_module(monkeypatch, rq_api_module, default_job_id="job-123")

    with app.test_client() as client:
        yield client, WatershedStub, env, state

    WatershedStub.reset_instances()
    env.redis_prep_class.reset_instances()
    env.recorder.reset()
    state.clear()


def test_fetch_dem_and_build_channels_accepts_json_payload(rq_channel_client):
    client, WatershedStub, env, state = rq_channel_client

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

    queue_call = env.recorder.queue_calls[0]
    assert queue_call.func is rq_api_module.fetch_dem_and_build_channels_rq
    args = queue_call.args
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
    assert args[10] is None

    prep = env.redis_prep_class.getInstance(state["run_dir"])
    assert rq_api_module.TaskEnum.fetch_dem in prep.removed
    assert rq_api_module.TaskEnum.build_channels in prep.removed
    assert prep.job_ids["fetch_dem_and_build_channels_rq"] == "job-123"

    entries = env.recorder.redis_entries
    assert "enter" in entries and "exit" in entries


def test_fetch_dem_and_build_channels_accepts_map_object_payload(rq_channel_client):
    client, WatershedStub, env, state = rq_channel_client

    map_object_payload = {
        "py/object": "wepppy.nodb.ron.Map",
        "extent": [-76.8294525146484, 39.9344864571048, -76.3961791992188, 40.2659044192667],
        "center": [-76.6128158569336, 40.1003972269821],
        "zoom": 11,
        "cellsize": 30,
        "utm": {"py/tuple": [344441.491229245, 4458876.15347613, 18, "T"]},
        "_ul_x": 344441.491229245,
        "_ul_y": 4458876.15347613,
        "_lr_x": 380706.64397684,
        "_lr_y": 4421418.99485695,
        "_num_cols": 1209,
        "_num_rows": 1249,
    }

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/rq/api/fetch_dem_and_build_channels",
        json={
            "map_object": map_object_payload,
            "mcl": 60,
            "csa": 5,
            "set_extent_mode": 2,
        },
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["Success"] is True

    queue_call = env.recorder.queue_calls[0]
    args = queue_call.args
    assert args[1] == map_object_payload["extent"]
    assert args[2] == map_object_payload["center"]
    assert args[3] == pytest.approx(float(map_object_payload["zoom"]))
    assert args[8] == 2
    assert args[9] == ", ".join(str(v) for v in map_object_payload["extent"])
    assert args[10] is not None
    assert getattr(args[10], "extent") == map_object_payload["extent"]
    assert getattr(args[10], "center") == map_object_payload["center"]


def test_fetch_dem_and_build_channels_accepts_form_payload(rq_channel_client):
    client, WatershedStub, env, state = rq_channel_client

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

    queue_call = env.recorder.queue_calls[0]
    args = queue_call.args
    assert args[1] == [-118.0, 46.5, -117.0, 47.0]
    assert args[2] == [-117.52, 46.88]
    assert args[3] == pytest.approx(12.0)
    assert args[4] == pytest.approx(4.5)
    assert args[5] == pytest.approx(45.0)
    assert args[6] is None
    assert args[7] is None
    assert args[8] == 0
    assert args[10] is None


def test_fetch_dem_and_build_channels_batch_mode_short_circuits(rq_channel_client):
    client, WatershedStub, env, state = rq_channel_client

    watershed = WatershedStub.getInstance(state["run_dir"])
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

    assert env.recorder.queue_calls == []
