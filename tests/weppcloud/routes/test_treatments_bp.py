from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("flask")
from flask import Flask

import wepppy.weppcloud.routes.nodb_api.treatments_bp as treatments_module
from tests.factories.singleton import singleton_factory

pytestmark = pytest.mark.routes

RUN_ID = "demo-run"
CONFIG = "cfg"


@pytest.fixture()
def treatments_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(treatments_module.treatments_bp)

    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()

    TreatmentsMode = treatments_module.TreatmentsMode

    def mode_getter(self):
        return self._mode

    def mode_setter(self, value):
        self.mode_assignments.append(value)
        self._mode = value

    TreatmentsStub = singleton_factory(
        "TreatmentsStub",
        attrs={
            "_mode": TreatmentsMode.Undefined,
            "mode_assignments": [],
        },
        methods={
            "mode": property(mode_getter, mode_setter),
        },
    )

    monkeypatch.setattr(treatments_module, "Treatments", TreatmentsStub)
    monkeypatch.setattr(treatments_module, "get_wd", lambda runid: str(run_dir))

    with app.test_client() as client:
        yield client, TreatmentsStub, str(run_dir)

    TreatmentsStub.reset_instances()


def test_set_mode_accepts_json_payload(treatments_client):
    client, TreatmentsStub, run_dir = treatments_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_treatments_mode/",
        json={"mode": treatments_module.TreatmentsMode.UserDefinedMap.value},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {"Success": True}

    instance = TreatmentsStub.getInstance(run_dir)
    assert instance.mode_assignments[-1] == treatments_module.TreatmentsMode.UserDefinedMap


def test_set_mode_accepts_legacy_form_payload(treatments_client):
    client, TreatmentsStub, run_dir = treatments_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_treatments_mode/",
        data={"treatments_mode": "1"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {"Success": True}

    instance = TreatmentsStub.getInstance(run_dir)
    assert instance.mode_assignments[-1] == treatments_module.TreatmentsMode.UserDefinedSelection


def test_set_mode_requires_value(treatments_client):
    client, TreatmentsStub, run_dir = treatments_client
    TreatmentsStub.getInstance(run_dir).mode_assignments.clear()

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_treatments_mode/",
        json={},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {"Success": False, "Error": "mode must be provided"}
    assert TreatmentsStub.getInstance(run_dir).mode_assignments == []


def test_set_mode_validates_integer_input(treatments_client):
    client, TreatmentsStub, run_dir = treatments_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_treatments_mode/",
        json={"mode": "not-an-int"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {"Success": False, "Error": "mode must be an integer"}
    assert TreatmentsStub.getInstance(run_dir).mode_assignments == []
