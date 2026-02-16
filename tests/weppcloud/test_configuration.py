from __future__ import annotations

from datetime import timedelta

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
    monkeypatch.delenv("SESSION_COOKIE_SAMESITE", raising=False)
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
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert app.config["SESSION_REFRESH_EACH_REQUEST"] is True
    assert app.config["REMEMBER_COOKIE_DURATION"] == timedelta(days=30)
    assert app.config["REMEMBER_COOKIE_SECURE"] is True
    assert app.config["REMEMBER_COOKIE_HTTPONLY"] is True
    assert app.config["REMEMBER_COOKIE_SAMESITE"] == "Lax"
    assert app.config["REMEMBER_COOKIE_REFRESH_EACH_REQUEST"] is False


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


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, False),
        ("true", True),
        ("1", True),
        ("off", False),
        ("0", False),
    ],
)
def test_config_app_sets_gl_dashboard_batch_enabled_from_env(
    monkeypatch: pytest.MonkeyPatch, raw: str | None, expected: bool
) -> None:
    if raw is None:
        monkeypatch.delenv("GL_DASHBOARD_BATCH_ENABLED", raising=False)
    else:
        monkeypatch.setenv("GL_DASHBOARD_BATCH_ENABLED", raw)

    app = _build_configured_app(monkeypatch)

    assert app.config["GL_DASHBOARD_BATCH_ENABLED"] is expected


def test_config_app_allows_session_cookie_samesite_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SESSION_COOKIE_SAMESITE", "Strict")
    app = _build_configured_app(monkeypatch)
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Strict"


def test_config_app_reads_required_secrets_from_file_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    secret_key_path = tmp_path / "secret_key"
    secret_key_path.write_text("file-secret\n", encoding="utf-8")
    salt_path = tmp_path / "security_password_salt"
    salt_path.write_text("file-salt\n", encoding="utf-8")

    monkeypatch.setenv("SECRET_KEY_FILE", str(secret_key_path))
    monkeypatch.setenv("SECURITY_PASSWORD_SALT_FILE", str(salt_path))
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("SECURITY_PASSWORD_SALT", raising=False)
    monkeypatch.setattr(configuration, "_build_session_redis", lambda: "redis-client")

    app = _DummyApp()
    configuration.config_app(app)

    assert app.config["SECRET_KEY"] == "file-secret"
    assert app.config["SECURITY_PASSWORD_SALT"] == b"file-salt"


def test_config_app_builds_database_uri_from_postgres_password_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    password_path = tmp_path / "postgres_password"
    password_path.write_text("p@ss\n", encoding="utf-8")

    monkeypatch.setenv("POSTGRES_PASSWORD_FILE", str(password_path))
    monkeypatch.setenv("POSTGRES_HOST", "db")
    monkeypatch.setenv("POSTGRES_PORT", "5433")
    monkeypatch.setenv("POSTGRES_DB", "dbname")
    monkeypatch.setenv("POSTGRES_USER", "user")
    monkeypatch.delenv("SQLALCHEMY_DATABASE_URI", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    app = _build_configured_app(monkeypatch)

    assert app.config["SQLALCHEMY_DATABASE_URI"] == "postgresql://user:p%40ss@db:5433/dbname"


def test_config_app_allows_remember_cookie_env_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("REMEMBER_COOKIE_DAYS", "14")
    monkeypatch.setenv("REMEMBER_COOKIE_SAMESITE", "Strict")
    monkeypatch.setenv("REMEMBER_COOKIE_SECURE", "false")
    monkeypatch.setenv("REMEMBER_COOKIE_HTTPONLY", "false")
    monkeypatch.setenv("REMEMBER_COOKIE_REFRESH_EACH_REQUEST", "false")
    monkeypatch.setenv("SESSION_REFRESH_EACH_REQUEST", "false")

    app = _build_configured_app(monkeypatch)

    assert app.config["REMEMBER_COOKIE_DURATION"] == timedelta(days=14)
    assert app.config["REMEMBER_COOKIE_SAMESITE"] == "Strict"
    assert app.config["REMEMBER_COOKIE_SECURE"] is False
    assert app.config["REMEMBER_COOKIE_HTTPONLY"] is False
    assert app.config["REMEMBER_COOKIE_REFRESH_EACH_REQUEST"] is False
    assert app.config["SESSION_REFRESH_EACH_REQUEST"] is False
