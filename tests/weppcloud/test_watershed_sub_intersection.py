from __future__ import annotations

from types import SimpleNamespace

import pytest
from flask import Flask

import wepppy.weppcloud.routes.nodb_api.watershed_bp as watershed_bp_module
from wepppy.weppcloud.utils import helpers as helpers_module

RUN_ID = "test-run"
CONFIG = "cfg"


@pytest.fixture()
def watershed_client(monkeypatch: pytest.MonkeyPatch, tmp_path):
    app = Flask("watershed-test")
    app.config["TESTING"] = True
    app.register_blueprint(watershed_bp_module.watershed_bp)

    run_root = tmp_path / "runs" / RUN_ID
    run_root.mkdir(parents=True, exist_ok=True)

    context = SimpleNamespace(active_root=run_root)

    monkeypatch.setattr(
        watershed_bp_module,
        "load_run_context",
        lambda runid, config: context,
    )
    monkeypatch.setattr(helpers_module, "authorize", lambda runid, config: None)

    raw_values = [
        float("-inf"),
        None,
        "nan",
        0,
        0.5,
        1.0,
        62.0,
        82.0,
        82.0,
        83.4,
    ]

    class MapStub:
        def raster_intersection(self, extent, raster_fn=None, discard=()):
            assert extent == [1, 2, 3, 4]
            return raw_values

    map_stub = MapStub()

    class RonStub:
        _instance = None

        @classmethod
        def getInstance(cls, wd: str):
            assert wd == str(run_root)
            if cls._instance is None:
                cls._instance = SimpleNamespace(map=map_stub)
            return cls._instance

    class WatershedStub:
        _instance = None

        def __init__(self):
            self.subwta = "subwta"

        @classmethod
        def getInstance(cls, wd: str):
            assert wd == str(run_root)
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    monkeypatch.setattr(watershed_bp_module, "Ron", RonStub)
    monkeypatch.setattr(watershed_bp_module, "Watershed", WatershedStub)

    with app.test_client() as client:
        yield client

    RonStub._instance = None
    WatershedStub._instance = None


@pytest.mark.unit
def test_sub_intersection_filters_and_coerces_ids(watershed_client):
    client = watershed_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/sub_intersection/",
        json={"extent": [1, 2, 3, 4]},
    )

    assert response.status_code == 200
    assert response.get_json() == [1, 62, 82, 83]
