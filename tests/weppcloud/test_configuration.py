from __future__ import annotations

import pytest

import wepppy.weppcloud.configuration as configuration
from wepppy.config import redis_settings

pytestmark = pytest.mark.unit


class _DummyApp:
    def __init__(self) -> None:
        self.config = {}


def _build_configured_app(
    monkeypatch: pytest.MonkeyPatch,
    *,
    zoho_email: str | None = None,
    zoho_password: str | None = None,
) -> _DummyApp:
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("SECURITY_PASSWORD_SALT", "test-salt")
    monkeypatch.setattr(configuration, "_build_session_redis", lambda: "redis-client")

    if zoho_email is None:
        monkeypatch.delenv("ZOHO_NOREPLY_EMAIL", raising=False)
    else:
        monkeypatch.setenv("ZOHO_NOREPLY_EMAIL", zoho_email)

    if zoho_password is None:
        monkeypatch.delenv("ZOHO_NOREPLY_EMAIL_PASSWORD", raising=False)
    else:
        monkeypatch.setenv("ZOHO_NOREPLY_EMAIL_PASSWORD", zoho_password)

    app = _DummyApp()
    configuration.config_app(app)
    return app


def test_build_session_redis_uses_session_url_helper(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {}

    def fake_session_url(db_default: int = 11) -> str:
        captured["db_default"] = db_default
        return "redis://session-cache:6380/11"

    def fake_from_url(url: str):
        captured["url"] = url
        return "client"

    monkeypatch.setattr(redis_settings, "session_redis_url", fake_session_url)
    monkeypatch.setattr(configuration.redis, "from_url", fake_from_url)

    result = configuration._build_session_redis()

    assert result == "client"
    assert captured["db_default"] == 11
    assert captured["url"] == "redis://session-cache:6380/11"


def test_config_app_uses_uidaho_mail_defaults_when_zoho_is_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _build_configured_app(monkeypatch)

    assert app.config["MAIL_SERVER"] == "mx.uidaho.edu"
    assert app.config["MAIL_PORT"] == 25
    assert app.config["MAIL_USE_TLS"] is False
    assert app.config["MAIL_USE_SSL"] is False
    assert app.config["MAIL_USERNAME"] == "noreply@uidaho.edu"
    assert "MAIL_PASSWORD" not in app.config
    assert app.config["SECURITY_EMAIL_SENDER"] == "cals-wepp@uidaho.edu"
    assert app.config["EMAIL_SUBJECT_REGISTER"] == "Welcome to WEPPcloud"
    assert app.config["EMAIL_SUBJECT_CONFIRM"] == "Confirm your WEPPcloud email"
    assert app.config["EMAIL_SUBJECT_PASSWORD_RESET"] == "Reset your WEPPcloud password"
    assert app.config["EMAIL_SUBJECT_PASSWORD_NOTICE"] == "Your WEPPcloud password was reset"
    assert (
        app.config["EMAIL_SUBJECT_PASSWORD_CHANGE_NOTICE"]
        == "Your WEPPcloud password was changed"
    )


def test_config_app_uses_uidaho_mail_defaults_when_zoho_password_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _build_configured_app(monkeypatch, zoho_email="noreply@wepp.cloud")

    assert app.config["MAIL_SERVER"] == "mx.uidaho.edu"
    assert app.config["MAIL_USERNAME"] == "noreply@uidaho.edu"
    assert "MAIL_PASSWORD" not in app.config
    assert app.config["SECURITY_EMAIL_SENDER"] == "cals-wepp@uidaho.edu"


def test_config_app_enables_zoho_mail_when_credentials_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _build_configured_app(
        monkeypatch,
        zoho_email="noreply@wepp.cloud",
        zoho_password="zoho-app-password",
    )

    assert app.config["MAIL_SERVER"] == "smtp.zoho.com"
    assert app.config["MAIL_PORT"] == 587
    assert app.config["MAIL_USE_TLS"] is True
    assert app.config["MAIL_USE_SSL"] is False
    assert app.config["MAIL_USERNAME"] == "noreply@wepp.cloud"
    assert app.config["MAIL_PASSWORD"] == "zoho-app-password"
    assert app.config["SECURITY_EMAIL_SENDER"] == "noreply@wepp.cloud"
