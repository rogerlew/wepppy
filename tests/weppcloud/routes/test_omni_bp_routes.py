from __future__ import annotations

from flask import Flask
import pytest
from werkzeug.exceptions import Forbidden

pytest.importorskip("flask")

import wepppy.weppcloud.routes.nodb_api.omni_bp as omni_bp_module
import wepppy.weppcloud.utils.cap_guard as cap_guard

pytestmark = pytest.mark.routes

RUN_ID = "run-123"
CFG = "cfg"


@pytest.fixture()
def omni_bp_client(monkeypatch: pytest.MonkeyPatch, tmp_path):
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["PROPAGATE_EXCEPTIONS"] = False
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


class _RoleUser:
    def __init__(self, *roles: str, authenticated: bool = True) -> None:
        self._roles = set(roles)
        self.is_authenticated = authenticated

    def has_role(self, role: str) -> bool:
        return role in self._roles


class _EmptyReport:
    empty = True


class _OmniReportStub:
    contrast_selection_mode = "cumulative"

    def contrasts_report(self):
        return _EmptyReport()

    def contrast_status_report(self):
        return {"items": []}


@pytest.mark.parametrize(
    "roles,expected_status",
    [
        (("User",), 403),
        (("PowerUser",), 403),
        (("Admin",), 403),
        (("Dev",), 200),
        (("Root",), 200),
    ],
)
def test_contrast_report_enforces_role_before_data_read(
    omni_bp_client,
    monkeypatch: pytest.MonkeyPatch,
    roles: tuple[str, ...],
    expected_status: int,
) -> None:
    client = omni_bp_client
    user = _RoleUser(*roles)
    entered = {"value": False}

    monkeypatch.setattr(cap_guard, "current_user", user)
    monkeypatch.setattr(omni_bp_module, "current_user", user)

    def _get_omni(wd):
        entered["value"] = True
        return _OmniReportStub()

    monkeypatch.setattr(omni_bp_module.Omni, "getInstance", _get_omni)
    monkeypatch.setattr(omni_bp_module.Watershed, "getInstance", lambda wd: object())
    monkeypatch.setattr(omni_bp_module, "render_template", lambda *args, **kwargs: "report")

    response = client.get(f"/runs/{RUN_ID}/{CFG}/report/omni_contrasts")

    assert response.status_code == expected_status
    assert entered["value"] is (expected_status == 200)
    if expected_status == 403:
        assert response.get_json()["error"] == {
            "code": "forbidden",
            "message": "Not Authorized",
        }


def test_contrast_report_preserves_run_access_for_dev(
    omni_bp_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = omni_bp_client
    user = _RoleUser("Dev")
    entered = {"value": False}

    monkeypatch.setattr(cap_guard, "current_user", user)
    monkeypatch.setattr(omni_bp_module, "current_user", user)

    def _deny_run_access(runid, config):
        raise Forbidden()

    monkeypatch.setattr(omni_bp_module, "authorize", _deny_run_access)

    def _get_omni(wd):
        entered["value"] = True
        return _OmniReportStub()

    monkeypatch.setattr(omni_bp_module.Omni, "getInstance", _get_omni)

    response = client.get(f"/runs/{RUN_ID}/{CFG}/report/omni_contrasts")

    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "forbidden"
    assert entered["value"] is False


def test_contrast_report_preserves_cap_gate_before_data_read(
    omni_bp_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = omni_bp_client
    anonymous = _RoleUser(authenticated=False)
    entered = {"value": False}

    monkeypatch.setattr(cap_guard, "current_user", anonymous)
    monkeypatch.setattr(cap_guard, "_cap_session_valid", lambda ttl: False)
    monkeypatch.setattr(cap_guard, "cap_gate_response", lambda **kwargs: ("CAP required", 403))
    monkeypatch.setattr(omni_bp_module, "current_user", _RoleUser("Dev"))

    def _get_omni(wd):
        entered["value"] = True
        return _OmniReportStub()

    monkeypatch.setattr(omni_bp_module.Omni, "getInstance", _get_omni)

    response = client.get(f"/runs/{RUN_ID}/{CFG}/report/omni_contrasts")

    assert response.status_code == 403
    assert entered["value"] is False


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
