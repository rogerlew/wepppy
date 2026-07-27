from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import pytest
from flask import Blueprint, Flask, redirect, session
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user
from flask_login.utils import encode_cookie

from wepppy.weppcloud.routes._security import ui as security_ui


pytestmark = pytest.mark.unit


class _User(UserMixin):
    id = "user-1"


@pytest.fixture()
def remember_app() -> Flask:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY="remember-cookie-test",
        REMEMBER_COOKIE_DURATION=timedelta(days=90),
        REMEMBER_COOKIE_SECURE=True,
        REMEMBER_COOKIE_HTTPONLY=True,
        REMEMBER_COOKIE_SAMESITE="Lax",
        REMEMBER_COOKIE_REFRESH_EACH_REQUEST=False,
    )
    login_manager = LoginManager(app)

    @login_manager.user_loader
    def _load_user(user_id):
        return _User() if user_id == _User.id else None

    auth_bp = Blueprint("security", __name__)

    @auth_bp.post("/actual-login")
    def login():
        return redirect("/ping")

    @auth_bp.get("/actual-logout")
    def logout():
        logout_user()
        return redirect("/")

    app.register_blueprint(auth_bp)
    app.register_blueprint(security_ui.security_bp)

    @app.get("/login-session")
    def _login_session():
        login_user(_User(), remember=False)
        return "ok"

    @app.get("/login-remembered")
    def _login_remembered():
        login_user(_User(), remember=True)
        return "ok"

    @app.get("/login-opt-out")
    def _login_opt_out():
        login_user(_User(), remember=False)
        session["_remember"] = "clear"
        return "ok"

    @app.get("/ping")
    @login_required
    def _ping():
        return "ok"

    @app.get("/logout-test")
    @login_required
    def _logout():
        logout_user()
        return "ok"

    return app


def _remember_headers(response) -> list[str]:
    return [
        value for value in response.headers.getlist("Set-Cookie")
        if value.startswith("remember_token=")
    ]


def test_ordinary_session_does_not_create_remember_cookie(remember_app: Flask) -> None:
    response = remember_app.test_client().get("/login-session")
    assert _remember_headers(response) == []


def test_opted_in_cookie_is_secure_and_refreshes(remember_app: Flask) -> None:
    client = remember_app.test_client()
    login_response = client.get("/login-remembered")
    issued = _remember_headers(login_response)
    assert len(issued) == 1
    assert "Secure" in issued[0]
    assert "HttpOnly" in issued[0]
    assert "SameSite=Lax" in issued[0]
    assert "Expires=" in issued[0]
    expires_text = issued[0].split("Expires=", 1)[1].split(";", 1)[0]
    remaining = parsedate_to_datetime(expires_text) - datetime.now(timezone.utc)
    assert timedelta(days=89) < remaining <= timedelta(days=90)

    refresh_response = client.get("/ping")
    assert len(_remember_headers(refresh_response)) == 1


def test_remember_cookie_restores_identity_without_session(remember_app: Flask) -> None:
    client = remember_app.test_client()
    client.get("/login-remembered")
    client.delete_cookie("session")
    assert client.get("/ping").status_code == 200


def test_opt_out_deletes_preexisting_remember_cookie(remember_app: Flask) -> None:
    client = remember_app.test_client()
    client.get("/login-remembered")
    response = client.get("/login-opt-out")
    deleted = _remember_headers(response)
    assert len(deleted) == 1
    assert "Expires=Thu, 01 Jan 1970 00:00:00 GMT" in deleted[0]


def test_real_login_opt_out_clears_cookie_before_form_short_circuit(
    remember_app: Flask,
) -> None:
    client = remember_app.test_client()
    client.get("/login-remembered")
    client.delete_cookie("session")
    response = client.post("/actual-login", data={})
    deleted = _remember_headers(response)
    assert len(deleted) == 1
    assert "Expires=Thu, 01 Jan 1970 00:00:00 GMT" in deleted[0]


def test_invalid_remember_cookie_is_not_refreshed(remember_app: Flask) -> None:
    client = remember_app.test_client()
    client.get("/login-session")
    client.set_cookie("remember_token", "invalid-token")
    response = client.get("/ping")
    assert _remember_headers(response) == []


def test_mismatched_valid_remember_cookie_is_not_refreshed(
    remember_app: Flask,
) -> None:
    client = remember_app.test_client()
    client.get("/login-session")
    with remember_app.app_context():
        client.set_cookie("remember_token", encode_cookie("other-user"))
    response = client.get("/ping")
    assert _remember_headers(response) == []


def test_logout_deletes_remember_cookie(remember_app: Flask) -> None:
    client = remember_app.test_client()
    client.get("/login-remembered")
    response = client.get("/logout-test")
    deleted = _remember_headers(response)
    assert len(deleted) == 1
    assert "Expires=Thu, 01 Jan 1970 00:00:00 GMT" in deleted[0]


def test_security_logout_deletes_session_and_remember_cookies(
    remember_app: Flask,
) -> None:
    client = remember_app.test_client()
    client.get("/login-remembered")
    response = client.get("/actual-logout")
    cookies = response.headers.getlist("Set-Cookie")
    assert any(
        value.startswith("remember_token=")
        and "Expires=Thu, 01 Jan 1970 00:00:00 GMT" in value
        and "Secure" in value
        and "HttpOnly" in value
        and "SameSite=Lax" in value
        for value in cookies
    )
    assert any(
        value.startswith("session=")
        and "Expires=Thu, 01 Jan 1970 00:00:00 GMT" in value
        for value in cookies
    )


def test_rotating_user_identity_invalidates_copied_remember_cookie(
    remember_app: Flask,
) -> None:
    client = remember_app.test_client()
    client.get("/login-remembered")
    client.delete_cookie("session")
    _User.id = "rotated-user-id"
    try:
        response = client.get("/ping")
        assert response.status_code == 401
    finally:
        _User.id = "user-1"
