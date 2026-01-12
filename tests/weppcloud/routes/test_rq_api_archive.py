from __future__ import annotations

import pytest
from flask import Flask

import wepppy.weppcloud.routes.rq.api.api as rq_api_module


pytestmark = pytest.mark.routes


@pytest.fixture()
def rq_archive_app(monkeypatch: pytest.MonkeyPatch, tmp_path):
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["LOGIN_DISABLED"] = True
    app.config["SECRET_KEY"] = "test-secret"
    app.register_blueprint(rq_api_module.rq_api_bp)

    missing_run_path = tmp_path / "missing-run"
    monkeypatch.setattr(rq_api_module, "get_wd", lambda runid: str(missing_run_path))

    return app


def test_archive_returns_404_for_missing_run(rq_archive_app):
    with rq_archive_app.test_request_context(
        "/runs/run-x/live/rq/api/archive",
        method="POST",
        json={},
    ):
        response = rq_api_module.api_archive.__wrapped__("run-x", "live")

    assert response.status_code == 404
    payload = response.get_json()
    assert payload["error"]["message"] == "Project run-x not found"


def test_restore_archive_requires_name(rq_archive_app):
    with rq_archive_app.test_request_context(
        "/runs/run-x/live/rq/api/restore-archive",
        method="POST",
        json={},
    ):
        response = rq_api_module.api_restore_archive.__wrapped__("run-x", "live")

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"]["message"] == "Missing archive_name parameter"


def test_delete_archive_requires_name(rq_archive_app):
    with rq_archive_app.test_request_context(
        "/runs/run-x/live/rq/api/delete-archive",
        method="POST",
        json={},
    ):
        response = rq_api_module.api_delete_archive.__wrapped__("run-x", "live")

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"]["message"] == "Missing archive_name parameter"


def test_fork_returns_404_for_missing_run(rq_archive_app):
    with rq_archive_app.test_request_context(
        "/runs/run-x/live/rq/api/fork",
        method="POST",
        data={},
    ):
        response = rq_api_module.api_fork("run-x", "live")

    assert response.status_code == 404
    payload = response.get_json()
    assert payload["error"]["message"] == "Error forking project, run_id=run-x does not exist"
