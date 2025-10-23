from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from flask import Flask

import wepppy.weppcloud.routes.nodb_api.rangeland_bp as rangeland_module
import wepppy.weppcloud.routes.nodb_api.rangeland_cover_bp as cover_module
from tests.factories.singleton import LockedMixin, singleton_factory

pytestmark = pytest.mark.routes

RUN_ID = "test-run"
CONFIG = "cfg"


@pytest.fixture()
def rangeland_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(cover_module.rangeland_cover_bp)
    app.register_blueprint(rangeland_module.rangeland_bp)

    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()

    context = SimpleNamespace(active_root=run_dir)

    monkeypatch.setattr(cover_module, "load_run_context", lambda runid, config: context)
    monkeypatch.setattr(rangeland_module, "load_run_context", lambda runid, config: context)

    helpers = __import__("wepppy.weppcloud.utils.helpers", fromlist=["authorize"])
    monkeypatch.setattr(helpers, "authorize", lambda runid, config, require_owner=False: None)

    def build(self, rap_year=None, default_covers=None):
        self.build_calls.append({"rap_year": rap_year, "defaults": default_covers})

    RangelandStub = singleton_factory(
        "RangelandStub",
        attrs={
            "mode": None,
            "rap_year": None,
            "build_calls": []
        },
        methods={
            "build": build,
            "current_cover_summary": lambda self, _: {},
            "modify_covers": lambda self, *_args: None,
        },
        mixins=(LockedMixin,),
    )

    monkeypatch.setattr(cover_module, "RangelandCover", RangelandStub)
    monkeypatch.setattr(rangeland_module, "RangelandCover", RangelandStub)

    with app.test_client() as client:
        yield client, RangelandStub, str(run_dir)

    RangelandStub.reset_instances()


def test_set_mode_parses_payload(rangeland_client):
    client, RangelandStub, run_dir = rangeland_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_rangeland_cover_mode/",
        data=json.dumps({"mode": "2", "rap_year": "2022"}),
        content_type="application/json",
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Success"] is True

    instance = RangelandStub.getInstance(run_dir)
    from wepppy.nodb.mods.rangeland_cover import RangelandCoverMode

    assert instance.mode == RangelandCoverMode(2)
    assert instance.rap_year == 2022


def test_build_accepts_json_defaults(rangeland_client):
    client, RangelandStub, run_dir = rangeland_client

    defaults = {
        "bunchgrass": "11.5",
        "forbs": "22.1",
        "sodgrass": "33.2",
        "shrub": "44.3",
        "basal": "12.0",
        "rock": "6.0",
        "litter": "25.0",
        "cryptogams": "7.5",
    }
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/build_rangeland_cover/",
        data=json.dumps({"rap_year": 2021, "defaults": defaults}),
        content_type="application/json",
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Success"] is True

    instance = RangelandStub.getInstance(run_dir)
    assert instance.build_calls[-1] == {
        "rap_year": 2021,
        "defaults": {
            "bunchgrass": 11.5,
            "forbs": 22.1,
            "sodgrass": 33.2,
            "shrub": 44.3,
            "basal": 12.0,
            "rock": 6.0,
            "litter": 25.0,
            "cryptogams": 7.5,
        },
    }


def test_build_supports_legacy_form_payload(rangeland_client):
    client, RangelandStub, run_dir = rangeland_client

    form_payload = {
        "rap_year": "2019",
        "bunchgrass_cover": "10",
        "forbs_cover": "20",
        "sodgrass_cover": "30",
        "shrub_cover": "40",
        "basal_cover": "15",
        "rock_cover": "5",
        "litter_cover": "25",
        "cryptogams_cover": "5",
    }

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/build_rangeland_cover/",
        data=form_payload,
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Success"] is True

    instance = RangelandStub.getInstance(run_dir)
    assert instance.build_calls[-1] == {
        "rap_year": 2019,
        "defaults": {
            "bunchgrass": 10.0,
            "forbs": 20.0,
            "sodgrass": 30.0,
            "shrub": 40.0,
            "basal": 15.0,
            "rock": 5.0,
            "litter": 25.0,
            "cryptogams": 5.0,
        },
    }
