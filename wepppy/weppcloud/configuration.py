import os
from datetime import timedelta
from typing import Any

import redis


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"{name} must be provided as an environment variable for WEPPcloud."
        )
    return value


def _build_session_redis(db_default: int = 11) -> redis.Redis:
    url = os.getenv("SESSION_REDIS_URL") or os.getenv("REDIS_URL")
    db = int(os.getenv("SESSION_REDIS_DB", db_default))

    if url:
        return redis.from_url(url, db=db)

    host = os.getenv("SESSION_REDIS_HOST", os.getenv("REDIS_HOST", "localhost"))
    port = int(os.getenv("SESSION_REDIS_PORT", os.getenv("REDIS_PORT", "6379")))
    return redis.Redis(host=host, port=port, db=db)


def config_app(app: Any):
    """
    Configure the Flask application instance using environment variables.
    """
    app.config["MAIL_SERVER"] = "mx.uidaho.edu"
    app.config["MAIL_PORT"] = 25
    app.config["MAIL_USE_TLS"] = False
    app.config["MAIL_USE_SSL"] = False
    app.config["MAIL_USERNAME"] = "noreply@uidaho.edu"

    site_prefix = os.getenv("SITE_PREFIX", "/weppcloud")
    app.config["APPLICATION_ROOT"] = site_prefix
    app.config["DEBUG"] = True
    app.config["SITE_PREFIX"] = site_prefix

    # Flask-Security configuration
    app.config["SECRET_KEY"] = _require_env("SECRET_KEY")
    salt = _require_env("SECURITY_PASSWORD_SALT")
    app.config["SECURITY_PASSWORD_SALT"] = salt.encode("utf-8")
    app.config["SECURITY_PASSWORD_HASH"] = "bcrypt"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        os.getenv("SQLALCHEMY_DATABASE_URI")
        or os.getenv("DATABASE_URL")
        or "postgresql://wepppy:c0ff33@postgres/wepppy"
    )

    app.config["SECURITY_EMAIL_SENDER"] = "cals-wepp@uidaho.edu"
    app.config["SECURITY_CONFIRMABLE"] = True
    app.config["SECURITY_LOGIN_WITHOUT_CONFIRMATION"] = True
    app.config["SECURITY_REGISTERABLE"] = True
    app.config["SECURITY_TRACKABLE"] = True
    app.config["SECURITY_CHANGEABLE"] = True
    app.config["SECURITY_RECOVERABLE"] = True
    app.config["SECURITY_URL_PREFIX"] = app.config["SITE_PREFIX"]
    app.config["SECURITY_LOGIN_USER_TEMPLATE"] = "security/login_user.html"
    app.config["SECURITY_POST_LOGIN_VIEW"] = "security_ui.welcome"
    app.config["SECURITY_POST_LOGOUT_VIEW"] = "security_ui.goodbye"
    app.config["SECURITY_LOGIN_ERROR_VIEW"] = "security_ui.login"
    app.config["SECURITY_UNAUTHORIZED_VIEW"] = "security_ui.login"
    app.config["SECURITY_DEFAULT_REMEMBER_ME"] = True

    # Flask session configuration
    app.config["SESSION_TYPE"] = "redis"
    app.config["SESSION_REDIS"] = _build_session_redis()
    app.config["SESSION_USE_SIGNER"] = True
    app.config["SESSION_PERMANENT"] = False
    app.config["SESSION_KEY_PREFIX"] = "session:"
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=12)
    app.config["SESSION_COOKIE_SAMESITE"] = "None"
    app.config["SESSION_COOKIE_SECURE"] = True

    return app
