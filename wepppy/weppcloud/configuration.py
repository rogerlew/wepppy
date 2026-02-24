import os
from datetime import timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import redis

from wepppy.config.secrets import get_secret, require_secret


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"{name} must be provided as an environment variable for WEPPcloud."
        )
    return value


def _build_session_redis(db_default: int = 11) -> redis.Redis:
    from wepppy.config import redis_settings

    return redis.from_url(redis_settings.session_redis_url(db_default))

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


def _get_env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default

    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False

    return default


def _get_env_int(name: str, default: int, *, minimum: int | None = None) -> int:
    raw = os.getenv(name)
    if raw is None:
        value = default
    else:
        try:
            value = int(raw.strip())
        except (TypeError, ValueError):
            value = default
    if minimum is not None:
        value = max(minimum, value)
    return value


def _get_env_optional_int(name: str, *, minimum: int = 0) -> Optional[int]:
    raw = os.getenv(name)
    if raw is None:
        return None
    try:
        value = int(raw.strip())
    except (TypeError, ValueError):
        return None
    return max(minimum, value)


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


def _resolve_mail_config() -> Dict[str, Any]:
    zoho_email = (os.getenv("ZOHO_NOREPLY_EMAIL") or "").strip()
    zoho_password = get_secret("ZOHO_NOREPLY_EMAIL_PASSWORD") or ""

    if zoho_email and zoho_password:
        return {
            "MAIL_SERVER": "smtp.zoho.com",
            "MAIL_PORT": 587,
            "MAIL_USE_TLS": True,
            "MAIL_USE_SSL": False,
            "MAIL_USERNAME": zoho_email,
            "MAIL_PASSWORD": zoho_password,
            "SECURITY_EMAIL_SENDER": zoho_email,
        }

    return {
        "MAIL_SERVER": "mx.uidaho.edu",
        "MAIL_PORT": 25,
        "MAIL_USE_TLS": False,
        "MAIL_USE_SSL": False,
        "MAIL_USERNAME": "noreply@uidaho.edu",
        "SECURITY_EMAIL_SENDER": "cals-wepp@uidaho.edu",
    }


def _build_postgres_uri() -> str:
    """Build a PostgreSQL SQLAlchemy URI from non-secret env + POSTGRES_PASSWORD."""

    host = (os.getenv("POSTGRES_HOST") or "postgres").strip() or "postgres"
    port = (os.getenv("POSTGRES_PORT") or "5432").strip() or "5432"
    dbname = (os.getenv("POSTGRES_DB") or "wepppy").strip() or "wepppy"
    user = (os.getenv("POSTGRES_USER") or "wepppy").strip() or "wepppy"
    password = get_secret("POSTGRES_PASSWORD")

    user_enc = quote(user, safe="")
    if password:
        password_enc = quote(password, safe="")
        return f"postgresql://{user_enc}:{password_enc}@{host}:{port}/{dbname}"

    return f"postgresql://{user_enc}@{host}:{port}/{dbname}"


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
    github_client_secret = get_secret("OAUTH_GITHUB_CLIENT_SECRET") or _get_env_any(
        ["GITHUB_OAUTH_CLIENT_SECRET", "GITHUB_OAUTH_SECRET_KEY"]
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
    google_client_secret = get_secret("OAUTH_GOOGLE_CLIENT_SECRET") or _get_env_any(
        ["GOOGLE_OAUTH_CLIENT_SECRET"]
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

    orcid_client_id = _get_env_any(
        ["OAUTH_ORCID_CLIENT_ID", "ORCID_OAUTH_CLIENT_ID", "ORCID_OAUTH_CLIENTID"]
    )
    orcid_client_secret = get_secret("OAUTH_ORCID_CLIENT_SECRET") or _get_env_any(
        ["ORCID_OAUTH_CLIENT_SECRET", "ORCID_OAUTH_SECRET_KEY"]
    )
    orcid_redirect_override = _get_env_any(
        [
            "OAUTH_ORCID_REDIRECT_URI",
            "ORCID_OAUTH_REDIRECT_URI",
            "ORCID_OAUTH_CALLBACK_URL",
        ]
    )
    orcid_redirect_uri = _build_oauth_redirect_uri(
        redirect_scheme, redirect_host, site_prefix, "orcid", orcid_redirect_override
    )

    providers["orcid"] = {
        "name": "ORCID",
        "client_id": orcid_client_id,
        "client_secret": orcid_client_secret,
        "redirect_uri": orcid_redirect_uri,
        "authorize_url": "https://orcid.org/oauth/authorize",
        "token_url": "https://orcid.org/oauth/token",
        "userinfo_url": "https://pub.orcid.org/v3.0/~/person",
        "scope": ["/authenticate"],
        "client_kwargs": {
            "token_endpoint_auth_method": "client_secret_post",
            "headers": {"Accept": "application/json"},
        },
        "enabled": bool(
            orcid_client_id and orcid_client_secret and orcid_redirect_uri
        ),
    }

    return providers


def config_app(app: Any):
    """
    Configure the Flask application instance using environment variables.
    """
    app.config.update(_resolve_mail_config())

    site_prefix = os.getenv("SITE_PREFIX", "/weppcloud")
    app.config["APPLICATION_ROOT"] = site_prefix
    debug_enabled = _get_env_bool("FLASK_DEBUG", False)
    if not debug_enabled:
        debug_enabled = _get_env_bool("DEBUG", False)
    app.config["DEBUG"] = debug_enabled
    app.config["SITE_PREFIX"] = site_prefix
    app.config["ENABLE_LOCAL_LOGIN"] = _get_env_bool("ENABLE_LOCAL_LOGIN", True)
    app.config["GL_DASHBOARD_BATCH_ENABLED"] = _get_env_bool(
        "GL_DASHBOARD_BATCH_ENABLED", False
    )

    test_support_enabled = os.getenv("TEST_SUPPORT_ENABLED", "false").strip().lower()
    app.config["TEST_SUPPORT_ENABLED"] = test_support_enabled in {"1", "true", "yes"}

    # Flask-Security configuration
    app.config["SECRET_KEY"] = require_secret("SECRET_KEY")
    salt = require_secret("SECURITY_PASSWORD_SALT")
    app.config["SECURITY_PASSWORD_SALT"] = salt.encode("utf-8")
    app.config["SECURITY_PASSWORD_HASH"] = "bcrypt"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        os.getenv("SQLALCHEMY_DATABASE_URI")
        or os.getenv("DATABASE_URL")
        or _build_postgres_uri()
    )
    idle_in_tx_timeout = os.getenv("POSTGRES_IDLE_IN_TX_TIMEOUT")
    if idle_in_tx_timeout:
        engine_options = dict(app.config.get("SQLALCHEMY_ENGINE_OPTIONS") or {})
        connect_args = dict(engine_options.get("connect_args") or {})
        existing_options = connect_args.get("options", "")
        parts = [existing_options] if existing_options else []
        parts.append(f"-c idle_in_transaction_session_timeout={idle_in_tx_timeout}")
        connect_args["options"] = " ".join(parts).strip()
        engine_options["connect_args"] = connect_args
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = engine_options

    app.config["SECURITY_CONFIRMABLE"] = True
    app.config["SECURITY_LOGIN_WITHOUT_CONFIRMATION"] = True
    app.config["SECURITY_REGISTERABLE"] = True
    app.config["SECURITY_TRACKABLE"] = True
    app.config["SECURITY_CHANGEABLE"] = True
    app.config["SECURITY_RECOVERABLE"] = True
    app.config["EMAIL_SUBJECT_REGISTER"] = "Welcome to WEPPcloud"
    app.config["EMAIL_SUBJECT_CONFIRM"] = "Confirm your WEPPcloud email"
    app.config["EMAIL_SUBJECT_PASSWORD_RESET"] = "Reset your WEPPcloud password"
    app.config["EMAIL_SUBJECT_PASSWORD_NOTICE"] = "Your WEPPcloud password was reset"
    app.config["EMAIL_SUBJECT_PASSWORD_CHANGE_NOTICE"] = "Your WEPPcloud password was changed"
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
    app.config["SESSION_COOKIE_PATH"] = os.getenv("SESSION_COOKIE_PATH", "/")
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=12)
    app.config["SESSION_COOKIE_SAMESITE"] = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    app.config["SESSION_COOKIE_SECURE"] = True
    app.config["SESSION_REFRESH_EACH_REQUEST"] = _get_env_bool(
        "SESSION_REFRESH_EACH_REQUEST", True
    )
    remember_cookie_samesite = os.getenv(
        "REMEMBER_COOKIE_SAMESITE", app.config["SESSION_COOKIE_SAMESITE"]
    )
    app.config["REMEMBER_COOKIE_DURATION"] = timedelta(
        days=_get_env_int("REMEMBER_COOKIE_DAYS", 30, minimum=1)
    )
    app.config["REMEMBER_COOKIE_SECURE"] = _get_env_bool(
        "REMEMBER_COOKIE_SECURE", True
    )
    app.config["REMEMBER_COOKIE_HTTPONLY"] = _get_env_bool(
        "REMEMBER_COOKIE_HTTPONLY", True
    )
    app.config["REMEMBER_COOKIE_SAMESITE"] = remember_cookie_samesite
    app.config["REMEMBER_COOKIE_REFRESH_EACH_REQUEST"] = _get_env_bool(
        "REMEMBER_COOKIE_REFRESH_EACH_REQUEST", False
    )
    app.config["WTF_CSRF_ENABLED"] = _get_env_bool("WTF_CSRF_ENABLED", True)
    app.config["WTF_CSRF_HEADERS"] = ["X-CSRFToken", "X-CSRF-Token"]
    csrf_time_limit = _get_env_optional_int("WTF_CSRF_TIME_LIMIT_SECONDS")
    if csrf_time_limit is None:
        csrf_time_limit = _get_env_optional_int("WTF_CSRF_TIME_LIMIT")
    app.config["WTF_CSRF_TIME_LIMIT"] = csrf_time_limit

    redirect_scheme_raw = os.getenv("OAUTH_REDIRECT_SCHEME") or "https"
    oauth_redirect_scheme = redirect_scheme_raw.strip() or "https"
    oauth_redirect_host = _get_env_any(["OAUTH_REDIRECT_HOST", "EXTERNAL_HOST"])

    app.config["OAUTH_REDIRECT_SCHEME"] = oauth_redirect_scheme
    app.config["OAUTH_REDIRECT_HOST"] = oauth_redirect_host
    app.config["OAUTH_PROVIDERS"] = _load_oauth_providers(
        oauth_redirect_scheme, oauth_redirect_host, site_prefix
    )

    return app
