from __future__ import annotations

import logging
import os
import pickle
import uuid
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

import redis
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from itsdangerous import BadSignature, Signer

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.config.secrets import get_secret
from wepppy.nodb.base import NoDbBase
from wepppy.weppcloud.utils.helpers import get_run_owners_lazy, get_wd
from wepppy.weppcloud.utils import auth_tokens
from wepppy.weppcloud.utils.browse_cookie import (
    browse_cookie_name,
    browse_cookie_path,
)

from .auth import AuthError, authorize_run_access, require_jwt
from .openapi import agent_route_responses, rq_operation_id
from .responses import error_response, error_response_with_traceback

logger = logging.getLogger(__name__)

router = APIRouter()

SESSION_TOKEN_TTL_SECONDS = 4 * 24 * 60 * 60
SESSION_TOKEN_SCOPES = ["rq:status", "rq:enqueue", "rq:export"]
SESSION_TOKEN_REQUIRED_SCOPES = ["rq:status"]
SESSION_KEY_PREFIX = "session:"
DEFAULT_BROWSE_JWT_COOKIE_NAME = "wepp_browse_jwt"
BROWSE_JWT_COOKIE_NAME_ENV = "WEPP_BROWSE_JWT_COOKIE_NAME"
DEFAULT_SITE_PREFIX = "/weppcloud"
TRUST_FORWARDED_ORIGIN_HEADERS_ENV = "RQ_ENGINE_TRUST_FORWARDED_ORIGIN_HEADERS"


def _bool_env(name: str, *, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    token = raw.strip().lower()
    if token in {"1", "true", "yes", "on"}:
        return True
    if token in {"0", "false", "no", "off"}:
        return False
    return default


def _session_cookie_name() -> str:
    return os.getenv("SESSION_COOKIE_NAME", "session")


def _session_use_signer() -> bool:
    return _bool_env("SESSION_USE_SIGNER", default=True)


def _trust_forwarded_origin_headers() -> bool:
    return _bool_env(TRUST_FORWARDED_ORIGIN_HEADERS_ENV, default=False)


def _secret_key() -> str:
    secret = get_secret("SECRET_KEY")
    if not secret:
        raise AuthError("SECRET_KEY is required to validate sessions", status_code=500)
    return secret


def _unsign_session_id(raw_cookie: str) -> str:
    if not _session_use_signer():
        return raw_cookie
    signer = Signer(_secret_key(), salt="flask-session", key_derivation="hmac")
    try:
        return signer.unsign(raw_cookie).decode("utf-8")
    except BadSignature as exc:
        raise AuthError("Invalid session cookie", status_code=401) from exc


def _resolve_session_id_from_cookie(request: Request) -> str:
    cookie_name = _session_cookie_name()
    raw_cookie = request.cookies.get(cookie_name)
    if not raw_cookie:
        raise AuthError("Missing session cookie", status_code=401)
    session_id = _unsign_session_id(raw_cookie)
    if not session_id:
        raise AuthError("Invalid session cookie", status_code=401)
    return session_id


def _session_exists(session_id: str) -> None:
    key_prefix = os.getenv("SESSION_KEY_PREFIX", SESSION_KEY_PREFIX)
    key = f"{key_prefix}{session_id}"
    conn_kwargs = redis_connection_kwargs(RedisDB.SESSION)
    redis_conn = redis.Redis(**conn_kwargs)
    try:
        if not redis_conn.exists(key):
            raise AuthError("Session expired or invalid", status_code=401)
    finally:
        close_fn = getattr(redis_conn, "close", None)
        if callable(close_fn):
            close_fn()


def _session_payload(session_id: str) -> Mapping[str, Any]:
    key_prefix = os.getenv("SESSION_KEY_PREFIX", SESSION_KEY_PREFIX)
    key = f"{key_prefix}{session_id}"
    conn_kwargs = redis_connection_kwargs(RedisDB.SESSION)
    redis_conn = redis.Redis(**conn_kwargs)
    try:
        raw_value = redis_conn.get(key)
    finally:
        close_fn = getattr(redis_conn, "close", None)
        if callable(close_fn):
            close_fn()
    if raw_value is None:
        raise AuthError("Session expired or invalid", status_code=401)
    try:
        payload = pickle.loads(raw_value)
    except (AttributeError, EOFError, ImportError, IndexError, ValueError, pickle.UnpicklingError) as exc:
        logger.exception("rq-engine invalid session payload", extra={"session_id": session_id})
        raise AuthError("Invalid session payload", status_code=401) from exc
    if not isinstance(payload, Mapping):
        raise AuthError("Invalid session payload", status_code=401)
    return payload


def _session_not_authorized_message(request: Request, *, user_id: int | None) -> str:
    if user_id is None and request.cookies.get("remember_token"):
        return (
            "Session not authorized for run. Your login session is stale. "
            "Log out and sign in again, then retry."
        )
    return "Session not authorized for run"


def _store_session_marker(runid: str, session_id: str, ttl_seconds: int) -> None:
    key = f"auth:session:run:{runid}:{session_id}"
    conn_kwargs = redis_connection_kwargs(RedisDB.SESSION)
    redis_conn = redis.Redis(**conn_kwargs)
    try:
        redis_conn.setex(key, ttl_seconds, "1")
    finally:
        close_fn = getattr(redis_conn, "close", None)
        if callable(close_fn):
            close_fn()


def _resolve_bearer_claims(request: Request) -> Mapping[str, Any] | None:
    if "authorization" not in {key.lower() for key in request.headers.keys()}:
        return None
    return require_jwt(request, required_scopes=SESSION_TOKEN_REQUIRED_SCOPES)


def _normalized_origin(value: str) -> tuple[str, str, int] | None:
    candidate = str(value or "").strip()
    if not candidate:
        return None
    parsed = urlparse(candidate)
    scheme = (parsed.scheme or "").strip().lower()
    host = (parsed.hostname or "").strip().lower()
    if not scheme or not host:
        return None
    port = parsed.port
    if port is None:
        if scheme == "https":
            port = 443
        elif scheme == "http":
            port = 80
        else:
            return None
    return scheme, host, int(port)


def _request_origin(request: Request) -> str:
    url = request.url
    if not url:
        return ""
    scheme = (url.scheme or "").strip().lower()
    host = (url.hostname or "").strip().lower()
    port = url.port
    if not scheme or not host:
        return ""
    if port is None:
        if scheme == "https":
            port = 443
        elif scheme == "http":
            port = 80
        else:
            return ""
    return f"{scheme}://{host}:{int(port)}"


def _external_origin_scheme(request: Request) -> str:
    for env_key in ("OAUTH_REDIRECT_SCHEME", "EXTERNAL_SCHEME"):
        token = (os.getenv(env_key) or "").strip().lower()
        if token in {"https", "http"}:
            return token
    return (request.url.scheme or "").strip().lower() or "https"


def _allowed_origin_set(request: Request) -> set[tuple[str, str, int]]:
    origins: set[tuple[str, str, int]] = set()

    def _add(candidate: str) -> None:
        normalized = _normalized_origin(candidate)
        if normalized is not None:
            origins.add(normalized)

    _add(_request_origin(request))

    host_header = (request.headers.get("host") or "").strip()
    if host_header:
        scheme = (request.url.scheme or "").strip().lower() or "https"
        _add(f"{scheme}://{host_header}")

    forwarded_proto = ""
    if _trust_forwarded_origin_headers():
        forwarded_proto = (request.headers.get("X-Forwarded-Proto") or "").split(",")[0].strip().lower()
        forwarded_host = (request.headers.get("X-Forwarded-Host") or "").split(",")[0].strip()
        if forwarded_proto and host_header:
            _add(f"{forwarded_proto}://{host_header}")
        if forwarded_host:
            _add(f"{forwarded_proto or request.url.scheme}://{forwarded_host}")

    for env_key in ("OAUTH_REDIRECT_HOST", "EXTERNAL_HOST"):
        host_value = (os.getenv(env_key) or "").strip()
        if host_value:
            _add(f"{_external_origin_scheme(request)}://{host_value}")

    return origins


def _is_same_origin_cookie_request(request: Request) -> bool:
    fetch_site = (request.headers.get("Sec-Fetch-Site") or "").strip().lower()
    if fetch_site == "same-origin":
        return True
    if fetch_site in {"cross-site"}:
        return False

    allowed_origins = _allowed_origin_set(request)
    origin = (request.headers.get("Origin") or "").strip()
    if origin:
        normalized_origin = _normalized_origin(origin)
        return normalized_origin in allowed_origins

    referer = (request.headers.get("Referer") or "").strip()
    if not referer:
        return False
    parsed = urlparse(referer)
    if not parsed.scheme or not parsed.netloc:
        return False
    normalized_referer_origin = _normalized_origin(f"{parsed.scheme}://{parsed.netloc}")
    return normalized_referer_origin in allowed_origins


def _normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [item for item in (part.strip() for part in value.split(",")) if item]
    if isinstance(value, Sequence):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _ensure_identifier_claim(claims: Mapping[str, Any], runid: str) -> None:
    token_class = str(claims.get("token_class") or "").strip().lower()
    run_claims = _normalize_list(claims.get("runs") or claims.get("runid"))
    if token_class == "service" and not run_claims:
        raise AuthError("Token missing run scope", status_code=403, code="forbidden")
    if run_claims and str(runid) not in run_claims:
        raise AuthError("Token not authorized for run", status_code=403, code="forbidden")


def _normalize_roles(raw: Any) -> list[str]:
    roles = _normalize_list(raw)
    if not roles:
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for role in roles:
        if not role:
            continue
        key = role.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(role)
    return normalized


def _parse_user_id(raw: Any) -> int | None:
    if raw is None or isinstance(raw, bool):
        return None
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return None


def _owner_id_matches(owner: Any, user_id: int) -> bool:
    owner_id = getattr(owner, "id", None)
    if owner_id is None:
        return False
    try:
        return int(owner_id) == int(user_id)
    except (TypeError, ValueError):
        return False


def _identity_from_session_payload(payload: Mapping[str, Any]) -> tuple[int | None, list[str]]:
    user_id = _parse_user_id(payload.get("_user_id") or payload.get("user_id"))
    roles = _normalize_roles(
        payload.get("_roles_mask") or payload.get("_roles") or payload.get("roles")
    )
    return user_id, roles


def _identity_from_claims(claims: Mapping[str, Any]) -> tuple[int | None, list[str]]:
    user_id = _parse_user_id(claims.get("user_id") or claims.get("sub"))
    roles = _normalize_roles(claims.get("roles"))
    return user_id, roles


def _session_id_from_claims(claims: Mapping[str, Any]) -> str:
    token_class = claims.get("token_class")
    if token_class == "session":
        session_id = claims.get("session_id") or claims.get("sub")
        if session_id:
            return str(session_id)
    return uuid.uuid4().hex


def _authorization_runid(runid: str) -> str:
    raw = str(runid or "")
    parts = raw.split(";;")
    if len(parts) >= 3 and parts[-2] in {"omni", "omni-contrast"} and parts[-1]:
        return ";;".join(parts[:-2])
    return raw


def _run_is_public(runid: str) -> bool:
    auth_runid = _authorization_runid(runid)
    try:
        wd = get_wd(auth_runid, prefer_active=False)
    except ValueError:
        return False
    return NoDbBase.ispublic(wd)


def _session_user_authorized_for_run(runid: str, user_id: int | None, roles: Sequence[str]) -> bool:
    auth_runid = _authorization_runid(runid)
    if _run_is_public(runid):
        return True

    role_set = {role.lower() for role in roles}
    if "admin" in role_set or "root" in role_set:
        return True

    owners = get_run_owners_lazy(auth_runid)
    if not owners:
        return not auth_runid.startswith("batch;;")

    if user_id is None:
        return False

    for owner in owners:
        if _owner_id_matches(owner, user_id):
            return True
    return False


def _resolve_scopes(claims: Mapping[str, Any]) -> list[str]:
    scope_claim = claims.get("scope")
    scope_separator = auth_tokens.get_jwt_config().scope_separator
    if isinstance(scope_claim, str):
        return [scope for scope in scope_claim.split(scope_separator) if scope]
    if isinstance(scope_claim, (list, tuple)):
        return [str(scope) for scope in scope_claim if str(scope)]
    return list(SESSION_TOKEN_SCOPES)


def _browse_jwt_cookie_name() -> str:
    value = (os.getenv(BROWSE_JWT_COOKIE_NAME_ENV) or "").strip()
    return value or DEFAULT_BROWSE_JWT_COOKIE_NAME


def _browse_jwt_cookie_key(runid: str, config: str) -> str:
    return browse_cookie_name(_browse_jwt_cookie_name(), runid, config)


def _normalize_prefix(prefix: str | None) -> str:
    if not prefix:
        return ""
    trimmed = prefix.strip()
    if not trimmed or trimmed == "/":
        return ""
    return "/" + trimmed.strip("/")


def _site_prefix() -> str:
    return _normalize_prefix(os.getenv("SITE_PREFIX", DEFAULT_SITE_PREFIX))


def _session_jwt_cookie_path(runid: str, config: str) -> str:
    return browse_cookie_path(_site_prefix(), runid, config)


def _cookie_samesite() -> str:
    value = (os.getenv("WEPP_AUTH_SESSION_COOKIE_SAMESITE") or "lax").strip().lower()
    if value in {"lax", "strict", "none"}:
        return value
    return "lax"


def _request_is_secure(request: Request) -> bool:
    forwarded_proto = (request.headers.get("X-Forwarded-Proto") or "").split(",")[0].strip().lower()
    if forwarded_proto in {"https", "http"}:
        return forwarded_proto == "https"

    forwarded_ssl = (request.headers.get("X-Forwarded-Ssl") or "").strip().lower()
    if forwarded_ssl in {"on", "off"}:
        return forwarded_ssl == "on"

    return (request.url.scheme or "").lower() == "https"


def _session_cookie_secure(request: Request) -> bool:
    default_secure = _request_is_secure(request)
    if os.getenv("WEPP_AUTH_SESSION_COOKIE_SECURE") is None:
        return default_secure
    return _bool_env("WEPP_AUTH_SESSION_COOKIE_SECURE", default=default_secure)


def _set_session_jwt_cookie(
    response: JSONResponse,
    *,
    runid: str,
    config: str,
    token: str,
    request: Request,
) -> None:
    response.set_cookie(
        key=_browse_jwt_cookie_key(runid, config),
        value=token,
        max_age=SESSION_TOKEN_TTL_SECONDS,
        httponly=True,
        secure=_session_cookie_secure(request),
        samesite=_cookie_samesite(),
        path=_session_jwt_cookie_path(runid, config),
    )


@router.post(
    "/runs/{runid}/{config}/session-token",
    summary="Issue a run-scoped session token",
    description=(
        "Supports Bearer or Flask session-cookie auth. Bearer path requires scope `rq:status`; "
        "cookie path validates the server session marker with public-run fallback. "
        "Synchronously mints a run-scoped session token and sets an HttpOnly browse cookie."
    ),
    tags=["rq-engine", "session"],
    operation_id=rq_operation_id("issue_session_token"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Session token issued.",
    ),
)
def issue_session_token(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        user_id: int | None = None
        roles: list[str] = []
        claims = _resolve_bearer_claims(request)
        if claims is not None:
            authorize_run_access(claims, runid)
            _ensure_identifier_claim(claims, runid)
            session_id = _session_id_from_claims(claims)
            user_id, roles = _identity_from_claims(claims)
        else:
            if not _is_same_origin_cookie_request(request):
                raise AuthError(
                    "Cross-origin request blocked.",
                    status_code=403,
                    code="forbidden",
                )
            try:
                session_id = _resolve_session_id_from_cookie(request)
                _session_exists(session_id)
                session_payload = _session_payload(session_id)
                user_id, roles = _identity_from_session_payload(session_payload)
                if not _session_user_authorized_for_run(runid, user_id, roles):
                    raise AuthError(
                        _session_not_authorized_message(request, user_id=user_id),
                        status_code=401,
                        code="unauthorized",
                    )
            except AuthError:
                if _run_is_public(runid):
                    session_id = uuid.uuid4().hex
                    user_id = None
                    roles = []
                else:
                    raise

        extra_claims: dict[str, Any] = {
            "token_class": "session",
            "session_id": session_id,
            "runid": runid,
            "config": config,
            "jti": uuid.uuid4().hex,
        }
        if user_id is not None:
            extra_claims["user_id"] = user_id
            extra_claims["roles"] = roles

        token_payload = auth_tokens.issue_token(
            session_id,
            scopes=SESSION_TOKEN_SCOPES,
            audience="rq-engine",
            expires_in=SESSION_TOKEN_TTL_SECONDS,
            extra_claims=extra_claims,
        )
        claims = token_payload.get("claims", {})
        _store_session_marker(runid, session_id, SESSION_TOKEN_TTL_SECONDS)
        expires_at = claims.get("exp")
        scopes = _resolve_scopes(claims)
        payload: dict[str, Any] = {
            "token": token_payload.get("token"),
            "token_class": "session",
            "runid": runid,
            "config": config,
            "session_id": session_id,
            "expires_at": expires_at,
            "scopes": scopes,
            "audience": claims.get("aud"),
        }
        if claims.get("user_id") is not None:
            payload["user_id"] = claims.get("user_id")
            payload["roles"] = claims.get("roles") or []

        response = JSONResponse(payload)
        token_value = token_payload.get("token")
        if isinstance(token_value, str) and token_value:
            _set_session_jwt_cookie(
                response,
                runid=runid,
                config=config,
                token=token_value,
                request=request,
            )
        return response
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except auth_tokens.JWTConfigurationError as exc:
        return error_response(f"JWT configuration error: {exc}", status_code=500)
    except Exception:
        logger.exception("rq-engine session token issuance failed")
        return error_response_with_traceback("Failed to issue session token", status_code=500)


__all__ = ["router"]
