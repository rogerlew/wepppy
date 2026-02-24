from __future__ import annotations

import pytest

pytest.importorskip("flask")
from flask import Flask, jsonify
from flask_wtf.csrf import CSRFError, CSRFProtect, generate_csrf

import wepppy.weppcloud.routes.bootstrap as bootstrap_module
import wepppy.weppcloud.routes.weppcloud_site as weppcloud_site_module
from wepppy.weppcloud.bootstrap.api_shared import BootstrapForwardAuthContext
from wepppy.weppcloud.routes.bootstrap import bootstrap_bp
from wepppy.weppcloud.routes.weppcloud_site import weppcloud_site_bp

pytestmark = pytest.mark.routes


def _build_site_app() -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "csrf-test-secret"
    CSRFProtect(app)
    app.register_blueprint(weppcloud_site_bp, url_prefix="/weppcloud")

    @app.errorhandler(CSRFError)
    def csrf_error(_exc):
        return jsonify({"error": {"message": "csrf failed"}}), 400

    @app.get("/csrf-token")
    def csrf_token_endpoint():
        return jsonify({"csrf_token": generate_csrf()})

    return app


def _build_bootstrap_app() -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "csrf-test-secret"
    csrf = CSRFProtect(app)
    app.register_blueprint(bootstrap_bp)
    bootstrap_module.register_csrf_exemptions(csrf)

    @app.errorhandler(CSRFError)
    def csrf_error(_exc):
        return jsonify({"error": {"message": "csrf failed"}}), 400

    return app


def _csrf_token(client) -> str:
    response = client.get("/csrf-token")
    assert response.status_code == 200
    payload = response.get_json()
    token = payload.get("csrf_token")
    assert token
    return token


def test_session_heartbeat_rejects_missing_csrf(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _build_site_app()
    monkeypatch.setattr(
        weppcloud_site_module,
        "current_user",
        type("U", (), {"is_anonymous": False, "is_authenticated": True})(),
        raising=False,
    )

    with app.test_client() as client:
        response = client.post(
            "/weppcloud/api/auth/session-heartbeat",
            headers={"Origin": "http://localhost"},
        )

    assert response.status_code == 400


def test_session_heartbeat_accepts_valid_csrf(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _build_site_app()
    monkeypatch.setattr(
        weppcloud_site_module,
        "current_user",
        type("U", (), {"is_anonymous": False, "is_authenticated": True})(),
        raising=False,
    )

    with app.test_client() as client:
        token = _csrf_token(client)
        response = client.post(
            "/weppcloud/api/auth/session-heartbeat",
            headers={
                "Origin": "http://localhost",
                "X-CSRFToken": token,
            },
        )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True


def test_session_heartbeat_valid_csrf_still_blocks_cross_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _build_site_app()
    monkeypatch.setattr(
        weppcloud_site_module,
        "current_user",
        type("U", (), {"is_anonymous": False, "is_authenticated": True})(),
        raising=False,
    )

    with app.test_client() as client:
        token = _csrf_token(client)
        response = client.post(
            "/weppcloud/api/auth/session-heartbeat",
            headers={
                "Origin": "https://evil.example",
                "X-CSRFToken": token,
            },
        )

    assert response.status_code == 403
    payload = response.get_json()
    assert payload["error"]["message"] == "Cross-origin request blocked."


def test_rq_engine_token_rejects_missing_csrf(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _build_site_app()
    monkeypatch.setattr(
        weppcloud_site_module,
        "current_user",
        type("U", (), {"is_anonymous": False, "is_authenticated": True})(),
        raising=False,
    )
    monkeypatch.setattr(weppcloud_site_module, "_issue_rq_engine_token", lambda: "rq-user-token")

    with app.test_client() as client:
        response = client.post(
            "/weppcloud/api/auth/rq-engine-token",
            headers={"Origin": "http://localhost"},
        )

    assert response.status_code == 400


def test_rq_engine_token_accepts_valid_csrf(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _build_site_app()
    monkeypatch.setattr(
        weppcloud_site_module,
        "current_user",
        type("U", (), {"is_anonymous": False, "is_authenticated": True})(),
        raising=False,
    )
    monkeypatch.setattr(weppcloud_site_module, "_issue_rq_engine_token", lambda: "rq-user-token")

    with app.test_client() as client:
        token = _csrf_token(client)
        response = client.post(
            "/weppcloud/api/auth/rq-engine-token",
            headers={
                "Origin": "http://localhost",
                "X-CSRFToken": token,
            },
        )

    assert response.status_code == 200
    assert response.get_json() == {"token": "rq-user-token"}


def test_bootstrap_verify_token_is_csrf_exempt(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _build_bootstrap_app()
    monkeypatch.setattr(
        bootstrap_module,
        "verify_forward_auth_context",
        lambda **kwargs: BootstrapForwardAuthContext(runid="ab-run", email="user@example.com"),
    )
    monkeypatch.setattr(bootstrap_module, "ensure_bootstrap_eligibility", lambda *args, **kwargs: (object(), object()))
    monkeypatch.setattr(bootstrap_module, "ensure_bootstrap_opt_in", lambda runid: object())

    with app.test_client() as client:
        response = client.post(
            "/api/bootstrap/verify-token",
            headers={
                "Authorization": "Basic token",
                "X-Forwarded-Uri": "/git/ab/ab-run/.git/info/refs",
            },
        )

    assert response.status_code == 200
    assert response.headers.get("X-Auth-User") == "user@example.com"
