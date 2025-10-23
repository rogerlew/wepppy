from __future__ import annotations

import json
from typing import Tuple

import pytest
from flask import Flask

from tests.factories.singleton import LockedMixin, singleton_factory

pytestmark = pytest.mark.unit

pytest.importorskip("flask")

import wepppy.weppcloud.routes.nodb_api.observed_bp as observed_module  # noqa: E402

RUN_ID = "demo"
CONFIG = "live"


def make_observed_stub():
    def parse_textdata(self, text):
        if getattr(self, "raise_parse_error", False):
            raise ValueError("parse failure")
        self.parse_calls.append(text)

    def calc_model_fit(self):
        if getattr(self, "raise_calc_error", False):
            raise RuntimeError("calc failure")
        self.calc_calls += 1

    return singleton_factory(
        "ObservedStub",
        attrs={
            "parse_calls": [],
            "calc_calls": 0,
            "raise_parse_error": False,
            "raise_calc_error": False,
        },
        methods={
            "parse_textdata": parse_textdata,
            "calc_model_fit": calc_model_fit,
        },
        mixins=(LockedMixin,),
    )


@pytest.fixture()
def observed_app(monkeypatch: pytest.MonkeyPatch, tmp_path) -> Tuple[Flask, type, str]:
    observed_cls = make_observed_stub()
    observed_cls.reset_instances()

    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()

    monkeypatch.setattr(observed_module, "get_wd", lambda runid: str(run_dir))
    monkeypatch.setattr(observed_module, "Observed", observed_cls)

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(observed_module.observed_bp)

    return app, observed_cls, str(run_dir)


def test_submit_run_model_fit_accepts_json_payload(observed_app):
    app, observed_cls, run_dir = observed_app

    payload = "Date,Streamflow (mm)\n01/01/2020,15\n"

    with app.test_client() as client:
        response = client.post(
            f"/runs/{RUN_ID}/{CONFIG}/tasks/run_model_fit/",
            data=json.dumps({"data": payload}),
            content_type="application/json",
        )

    assert response.status_code == 200
    assert response.get_json() == {"Success": True}

    instance = observed_cls.getInstance(run_dir)
    assert instance.parse_calls == [payload]
    assert instance.calc_calls == 1


def test_submit_run_model_fit_accepts_form_payload(observed_app):
    app, observed_cls, run_dir = observed_app

    payload = "Date,Streamflow (mm)\n01/01/2020,10\n"

    with app.test_client() as client:
        response = client.post(
            f"/runs/{RUN_ID}/{CONFIG}/tasks/run_model_fit/",
            data={"observed_text": payload},
            content_type="application/x-www-form-urlencoded",
        )

    assert response.status_code == 200
    assert response.get_json() == {"Success": True}

    instance = observed_cls.getInstance(run_dir)
    assert instance.parse_calls == [payload]
    assert instance.calc_calls == 1


def test_submit_run_model_fit_requires_payload(observed_app):
    app, observed_cls, run_dir = observed_app

    with app.test_client() as client:
        response = client.post(
            f"/runs/{RUN_ID}/{CONFIG}/tasks/run_model_fit/",
            data=json.dumps({"unexpected": "value"}),
            content_type="application/json",
        )

    assert response.status_code == 400
    body = response.get_json()
    assert body["Success"] is False
    assert "No observed dataset" in body["Error"]

    instance = observed_cls.getInstance(run_dir)
    assert instance.parse_calls == []
    assert instance.calc_calls == 0


def test_submit_run_model_fit_handles_processing_errors(observed_app):
    app, observed_cls, run_dir = observed_app

    instance = observed_cls.getInstance(run_dir)
    instance.raise_parse_error = True

    with app.test_client() as client:
        response = client.post(
            f"/runs/{RUN_ID}/{CONFIG}/tasks/run_model_fit/",
            data=json.dumps({"data": "Date\n01/01/2020\n"}),
            content_type="application/json",
        )

    assert response.status_code == 500
    body = response.get_json()
    assert body["Success"] is False
    assert body["Error"] == "Error parsing text"

    instance.raise_parse_error = False
    instance.raise_calc_error = True

    with app.test_client() as client:
        response = client.post(
            f"/runs/{RUN_ID}/{CONFIG}/tasks/run_model_fit/",
            data=json.dumps({"data": "Date,Value\n01/01/2020,1\n"}),
            content_type="application/json",
        )

    assert response.status_code == 500
    body = response.get_json()
    assert body["Success"] is False
    assert body["Error"] == "Error running model fit"

    instance = observed_cls.getInstance(run_dir)
    assert instance.calc_calls == 0
