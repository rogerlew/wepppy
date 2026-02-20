from __future__ import annotations

from flask import Flask
import pytest

pytest.importorskip("flask")

import wepppy.weppcloud.routes.nodb_api.omni_bp as omni_bp_module

pytestmark = pytest.mark.routes

RUN_ID = "run-123"
CFG = "cfg"


@pytest.fixture()
def omni_bp_client(monkeypatch: pytest.MonkeyPatch, tmp_path):
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(omni_bp_module.omni_bp)

    wd = tmp_path / RUN_ID
    wd.mkdir(parents=True)

    monkeypatch.setattr(omni_bp_module, "authorize", lambda runid, config: None)
    monkeypatch.setattr(omni_bp_module, "get_wd", lambda runid: str(wd))

    with app.test_client() as client:
        yield client


class _OmniStub:
    def __init__(self) -> None:
        self.scenarios = [{"type": "uniform_low"}]
        self.scenario_run_state = [{"scenario": "uniform_low", "status": "executed"}]
        self.scenario_dependency_tree = {"uniform_low": {"dependency_sha1": "abc"}}
        self.deleted_payloads: list[list[str]] = []

    def scenario_run_markers(self):
        return {"uniform_low": True, "undisturbed": False}

    def delete_scenarios(self, scenario_names):
        values = [str(v) for v in scenario_names]
        self.deleted_payloads.append(values)
        return {"removed": values, "missing": []}


def test_get_scenarios_uses_omni_facade_contract(
    omni_bp_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = omni_bp_client
    stub = _OmniStub()
    monkeypatch.setattr(omni_bp_module.Omni, "getInstance", lambda wd: stub)

    response = client.get(f"/runs/{RUN_ID}/{CFG}/api/omni/get_scenarios")

    assert response.status_code == 200
    assert response.get_json() == [{"type": "uniform_low"}]


def test_get_scenario_run_state_returns_all_expected_sections(
    omni_bp_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = omni_bp_client
    stub = _OmniStub()
    monkeypatch.setattr(omni_bp_module.Omni, "getInstance", lambda wd: stub)

    response = client.get(f"/runs/{RUN_ID}/{CFG}/api/omni/get_scenario_run_state")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["run_state"] == [{"scenario": "uniform_low", "status": "executed"}]
    assert payload["dependency_tree"] == {"uniform_low": {"dependency_sha1": "abc"}}
    assert payload["run_markers"] == {"uniform_low": True, "undisturbed": False}


def test_delete_scenarios_normalizes_string_payload_to_list(
    omni_bp_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = omni_bp_client
    stub = _OmniStub()

    monkeypatch.setattr(omni_bp_module.Omni, "getInstance", lambda wd: stub)
    monkeypatch.setattr(
        omni_bp_module,
        "parse_request_payload",
        lambda request: {"scenario_names": "uniform_low"},
    )

    response = client.post(f"/runs/{RUN_ID}/{CFG}/api/omni/delete_scenarios")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Content"] == {"removed": ["uniform_low"], "missing": []}
    assert stub.deleted_payloads == [["uniform_low"]]


def test_delete_scenarios_coerces_non_sequence_payload_to_empty_list(
    omni_bp_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = omni_bp_client
    stub = _OmniStub()

    monkeypatch.setattr(omni_bp_module.Omni, "getInstance", lambda wd: stub)
    monkeypatch.setattr(
        omni_bp_module,
        "parse_request_payload",
        lambda request: {"scenario_names": {"invalid": True}},
    )

    response = client.post(f"/runs/{RUN_ID}/{CFG}/api/omni/delete_scenarios")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Content"] == {"removed": [], "missing": []}
    assert stub.deleted_payloads == [[]]
