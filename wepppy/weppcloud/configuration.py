import os
from datetime import timedelta
from typing import Any, Dict, List, Optional

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


def _get_env_any(names: List[str], default: Optional[str] = None) -> Optional[str]:
    for name in names:
        value = os.getenv(name)
        if value is not None:
            trimmed = value.strip()
            if trimmed:
                return trimmed
    return default


def _normalize_site_prefix(site_prefix: str) -> str:
    if not site_prefix:
        return ""
    prefix = site_prefix.strip()
    if not prefix:
        return ""
    if not prefix.startswith("/"):
        prefix = f"/{prefix}"
    if len(prefix) > 1 and prefix.endswith("/"):
        prefix = prefix.rstrip("/")
    return prefix


def _build_oauth_redirect_uri(
    scheme: str,
    host: Optional[str],
    site_prefix: str,
    provider: str,
    override: Optional[str] = None,
) -> Optional[str]:
    if override:
        return override
    if not host:
        return None
    normalized_prefix = _normalize_site_prefix(site_prefix)
    callback_path = f"{normalized_prefix}/oauth/{provider}/callback"
    if not callback_path.startswith("/"):
        callback_path = f"/{callback_path}"
    return f"{scheme}://{host}{callback_path}"


def _load_oauth_providers(
    redirect_scheme: str, redirect_host: Optional[str], site_prefix: str
) -> Dict[str, Dict[str, Any]]:
    providers: Dict[str, Dict[str, Any]] = {}

    github_client_id = _get_env_any(
        ["OAUTH_GITHUB_CLIENT_ID", "GITHUB_OAUTH_CLIENT_ID", "GITHUB_OAUTH_CLIENTID"]
    )
    github_client_secret = _get_env_any(
        [
            "OAUTH_GITHUB_CLIENT_SECRET",
            "GITHUB_OAUTH_CLIENT_SECRET",
            "GITHUB_OAUTH_SECRET_KEY",
        ]
    )
    github_redirect_override = _get_env_any(
        [
            "OAUTH_GITHUB_REDIRECT_URI",
            "GITHUB_OAUTH_REDIRECT_URI",
            "GITHUB_OAUTH_CALLBACK_URL",
        ]
    )
    github_redirect_uri = _build_oauth_redirect_uri(
        redirect_scheme, redirect_host, site_prefix, "github", github_redirect_override
    )

    providers["github"] = {
        "name": "GitHub",
        "client_id": github_client_id,
        "client_secret": github_client_secret,
        "redirect_uri": github_redirect_uri,
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "emails_url": "https://api.github.com/user/emails",
        "scope": ["read:user", "user:email"],
        "enabled": bool(
            github_client_id and github_client_secret and github_redirect_uri
        ),
    }

    google_client_id = _get_env_any(
        ["OAUTH_GOOGLE_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_ID"]
    )
    google_client_secret = _get_env_any(
        ["OAUTH_GOOGLE_CLIENT_SECRET", "GOOGLE_OAUTH_CLIENT_SECRET"]
    )
    google_redirect_override = _get_env_any(
        [
            "OAUTH_GOOGLE_REDIRECT_URI",
            "GOOGLE_OAUTH_REDIRECT_URI",
            "GOOGLE_OAUTH_CALLBACK_URL",
        ]
    )
    google_redirect_uri = _build_oauth_redirect_uri(
        redirect_scheme, redirect_host, site_prefix, "google", google_redirect_override
    )

    providers["google"] = {
        "name": "Google",
        "client_id": google_client_id,
        "client_secret": google_client_secret,
        "redirect_uri": google_redirect_uri,
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://openidconnect.googleapis.com/v1/userinfo",
        "server_metadata_url": "https://accounts.google.com/.well-known/openid-configuration",
        "scope": ["openid", "email", "profile"],
        "client_kwargs": {
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
        },
        "enabled": bool(
            google_client_id and google_client_secret and google_redirect_uri
        ),
    }

    return providers


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

    redirect_scheme_raw = os.getenv("OAUTH_REDIRECT_SCHEME") or "https"
    oauth_redirect_scheme = redirect_scheme_raw.strip() or "https"
    oauth_redirect_host = _get_env_any(["OAUTH_REDIRECT_HOST", "EXTERNAL_HOST"])

    app.config["OAUTH_REDIRECT_SCHEME"] = oauth_redirect_scheme
    app.config["OAUTH_REDIRECT_HOST"] = oauth_redirect_host
    app.config["OAUTH_PROVIDERS"] = _load_oauth_providers(
        oauth_redirect_scheme, oauth_redirect_host, site_prefix
    )

    return app
