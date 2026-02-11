from __future__ import annotations

from types import SimpleNamespace

import pytest

pytest.importorskip("flask")
from flask import Flask

import wepppy.weppcloud.routes.weppcloud_site as weppcloud_site_module
from wepppy.weppcloud.routes.weppcloud_site import weppcloud_site_bp
from wepppy.weppcloud.utils import auth_tokens

pytestmark = pytest.mark.routes


def _build_app() -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test-secret"
    app.register_blueprint(weppcloud_site_bp, url_prefix="/weppcloud")
    return app


def test_issue_rq_engine_token_requires_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _build_app()
    monkeypatch.setattr(
        weppcloud_site_module,
        "current_user",
        SimpleNamespace(is_anonymous=True),
        raising=False,
    )

    with app.test_client() as client:
        response = client.post("/weppcloud/api/auth/rq-engine-token")

    assert response.status_code == 401
    payload = response.get_json()
    assert payload["error"]["message"] == "Authentication required."


def test_issue_rq_engine_token_returns_token(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _build_app()
    monkeypatch.setattr(
        weppcloud_site_module,
        "current_user",
        SimpleNamespace(is_anonymous=False, is_authenticated=True),
        raising=False,
    )
    monkeypatch.setattr(
        weppcloud_site_module,
        "_issue_rq_engine_token",
        lambda: "rq-user-token",
    )

    with app.test_client() as client:
        response = client.post("/weppcloud/api/auth/rq-engine-token")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {"token": "rq-user-token"}


def test_issue_rq_engine_token_blocks_cross_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _build_app()
    monkeypatch.setattr(
        weppcloud_site_module,
        "current_user",
        SimpleNamespace(is_anonymous=False, is_authenticated=True),
        raising=False,
    )
    monkeypatch.setattr(
        weppcloud_site_module,
        "_issue_rq_engine_token",
        lambda: "rq-user-token",
    )

    with app.test_client() as client:
        response = client.post(
            "/weppcloud/api/auth/rq-engine-token",
            headers={"Origin": "https://evil.example"},
        )

    assert response.status_code == 403
    payload = response.get_json()
    assert payload["error"]["message"] == "Cross-origin request blocked."


def test_issue_rq_engine_token_uses_expected_claims(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyUser:
        is_anonymous = False
        id = 42
        email = "user@example.com"
        roles = [SimpleNamespace(name="Admin"), SimpleNamespace(name="Hydrologist")]

        @staticmethod
        def get_id() -> str:
            return "42"

    monkeypatch.setattr(
        weppcloud_site_module,
        "current_user",
        DummyUser(),
        raising=False,
    )

    captured: dict[str, object] = {}

    def _fake_issue_token(subject: str, **kwargs):
        captured["subject"] = subject
        captured["kwargs"] = kwargs
        return {"token": "issued-token"}

    monkeypatch.setattr(weppcloud_site_module.auth_tokens, "issue_token", _fake_issue_token)

    token = weppcloud_site_module._issue_rq_engine_token()

    assert token == "issued-token"
    assert captured["subject"] == "42"
    kwargs = captured["kwargs"]
    assert kwargs["scopes"] == ["rq:enqueue", "rq:status", "rq:export"]
    assert kwargs["audience"] == "rq-engine"
    extra_claims = kwargs["extra_claims"]
    assert extra_claims["token_class"] == "user"
    assert extra_claims["email"] == "user@example.com"
    assert extra_claims["roles"] == ["Admin", "Hydrologist"]
    assert isinstance(extra_claims["jti"], str)
    assert extra_claims["jti"]


def test_issue_rq_engine_token_handles_jwt_config_error(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _build_app()
    monkeypatch.setattr(
        weppcloud_site_module,
        "current_user",
        SimpleNamespace(is_anonymous=False, is_authenticated=True),
        raising=False,
    )

    def _raise_config_error():
        raise auth_tokens.JWTConfigurationError("missing secret")

    monkeypatch.setattr(
        weppcloud_site_module,
        "_issue_rq_engine_token",
        _raise_config_error,
    )

    with app.test_client() as client:
        response = client.post("/weppcloud/api/auth/rq-engine-token")

    assert response.status_code == 500
    payload = response.get_json()
    assert payload["error"]["message"] == "JWT configuration error: missing secret"
