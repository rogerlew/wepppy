from __future__ import annotations

import hashlib
import json
import logging
import os
import pickle
import uuid
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

import redis
from flask import has_app_context
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from itsdangerous import BadSignature, Signer

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.config.secrets import get_secret
from wepppy.nodb.base import NoDbBase
from wepppy.weppcloud.utils.helpers import get_run_owners_lazy, get_user_models, get_wd
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
SESSION_TOKEN_SCOPES = ["rq:read", "rq:status", "rq:enqueue", "rq:export"]
SESSION_TOKEN_REQUIRED_SCOPES = ["rq:status"]
SESSION_KEY_PREFIX = "session:"
DEFAULT_BROWSE_JWT_COOKIE_NAME = "wepp_browse_jwt"
BROWSE_JWT_COOKIE_NAME_ENV = "WEPP_BROWSE_JWT_COOKIE_NAME"
DEFAULT_SITE_PREFIX = "/weppcloud"
TRUST_FORWARDED_ORIGIN_HEADERS_ENV = "RQ_ENGINE_TRUST_FORWARDED_ORIGIN_HEADERS"
IDEMPOTENCY_KEY_HEADER = "Idempotency-Key"
RUN_STATE_MATCH_HEADER = "X-Run-State-Match"
IDEMPOTENCY_REPLAY_REJECTED_CODE = "idempotency_replay_rejected"
IDEMPOTENCY_MISMATCH_CODE = "idempotency_key_conflict"
STALE_RUN_STATE_CODE = "stale_run_state"
DEFAULT_IDEMPOTENCY_TTL_SECONDS = 24 * 60 * 60


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


def _candidate_fs_uniquifier(raw: Any) -> str | None:
    if raw is None or isinstance(raw, bool):
        return None
    token = str(raw).strip()
    if not token:
        return None
    return token


def _resolve_user_id_from_fs_uniquifier(raw: Any) -> int | None:
    fs_uniquifier = _candidate_fs_uniquifier(raw)
    if fs_uniquifier is None:
        return None

    _, User, _ = get_user_models()

    def _lookup() -> Any | None:
        return User.query.filter(User.fs_uniquifier == fs_uniquifier).first()

    if has_app_context():
        match = _lookup()
    else:
        from wepppy.weppcloud.app import app as flask_app

        with flask_app.app_context():
            match = _lookup()

    if match is None:
        return None
    return _parse_user_id(getattr(match, "id", None))


def _owner_id_matches(owner: Any, user_id: int) -> bool:
    owner_id = getattr(owner, "id", None)
    if owner_id is None:
        return False
    try:
        return int(owner_id) == int(user_id)
    except (TypeError, ValueError):
        return False


def _identity_from_session_payload(payload: Mapping[str, Any]) -> tuple[int | None, list[str]]:
    raw_user_id = payload.get("_user_id") or payload.get("user_id")
    user_id = _parse_user_id(raw_user_id)
    if user_id is None:
        user_id = _resolve_user_id_from_fs_uniquifier(raw_user_id)
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


def _idempotency_ttl_seconds() -> int:
    raw = str(os.getenv("RQ_ENGINE_SESSION_TOKEN_IDEMPOTENCY_TTL_SECONDS") or "").strip()
    if not raw:
        return DEFAULT_IDEMPOTENCY_TTL_SECONDS
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return DEFAULT_IDEMPOTENCY_TTL_SECONDS


def _normalize_idempotency_key(raw_value: str | None) -> str | None:
    if raw_value is None:
        return None
    value = str(raw_value).strip()
    if not value:
        return None
    if len(value) > 200:
        raise AuthError(
            "Idempotency key exceeds maximum length (200).",
            status_code=400,
            code="validation_error",
        )
    return value


def _extract_expected_run_state_revision(request: Request, payload: Mapping[str, Any]) -> str | None:
    header_value = str(request.headers.get(RUN_STATE_MATCH_HEADER) or "").strip()
    if header_value:
        return header_value

    raw_value = payload.get("expected_run_state_revision")
    if raw_value is None:
        return None
    value = str(raw_value).strip()
    return value or None


def _request_has_body(request: Request) -> bool:
    content_length = str(request.headers.get("Content-Length") or "").strip()
    if content_length:
        try:
            return int(content_length) > 0
        except (TypeError, ValueError):
            return True
    transfer_encoding = str(request.headers.get("Transfer-Encoding") or "").strip()
    return bool(transfer_encoding)


def _content_type_token(request: Request) -> str:
    return str(request.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()


async def _parse_optional_json_payload(request: Request) -> dict[str, Any]:
    if not _request_has_body(request):
        return {}

    content_type = _content_type_token(request)
    if content_type != "application/json":
        raise AuthError(
            "Session-token request body must use application/json.",
            status_code=400,
            code="validation_error",
        )

    try:
        raw_payload = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise AuthError(
            "Malformed JSON request body.",
            status_code=400,
            code="validation_error",
        ) from exc

    if raw_payload is None:
        return {}
    if not isinstance(raw_payload, Mapping):
        raise AuthError(
            "JSON request body must be an object.",
            status_code=400,
            code="validation_error",
        )

    return {str(key): value for key, value in raw_payload.items()}


def _canonicalize_payload_for_hash(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Mapping):
        return {
            str(key): _canonicalize_payload_for_hash(inner)
            for key, inner in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, list):
        return [_canonicalize_payload_for_hash(item) for item in value]
    if isinstance(value, tuple):
        return [_canonicalize_payload_for_hash(item) for item in value]
    if isinstance(value, set):
        normalized = [_canonicalize_payload_for_hash(item) for item in value]
        return sorted(normalized, key=lambda item: json.dumps(item, sort_keys=True, default=str))
    return str(value)


def _load_run_state_revision(runid: str, config: str) -> str:
    from . import schema_defaults_routes

    try:
        runtime = schema_defaults_routes._load_runtime_state(runid, config)
    except ValueError as exc:
        raise AuthError("Run not found", status_code=404, code="not_found") from exc
    except FileNotFoundError as exc:
        raise AuthError("Run not found", status_code=404, code="not_found") from exc
    except schema_defaults_routes.RunConfigMismatchError as exc:
        raise AuthError("Run not found", status_code=404, code="not_found") from exc
    return str(runtime.run_state_revision)


def _stale_run_state_response(*, expected: str, current: str) -> JSONResponse:
    return JSONResponse(
        {
            "error": {
                "message": "Run state changed since last read.",
                "code": STALE_RUN_STATE_CODE,
                "details": f"expected={expected} current={current}",
            },
            "current_run_state_revision": current,
        },
        status_code=409,
    )


def _idempotency_fingerprint(
    *,
    runid: str,
    config: str,
    auth_mode: str,
    claims: Mapping[str, Any] | None,
    user_id: int | None,
    roles: Sequence[str],
    payload: Mapping[str, Any],
    expected_run_state_revision: str | None,
) -> str:
    source = {
        "runid": runid,
        "config": config,
        "auth_mode": auth_mode,
        "token_class": str((claims or {}).get("token_class") or ""),
        "subject": str((claims or {}).get("sub") or ""),
        "user_id": user_id,
        "roles": list(roles),
        "payload": _canonicalize_payload_for_hash(dict(payload)),
        "expected_run_state_revision": expected_run_state_revision,
    }
    digest_input = json.dumps(source, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(digest_input).hexdigest()


def _idempotency_storage_key(runid: str, config: str, idempotency_key: str, *, principal_namespace: str) -> str:
    token = f"{runid}\n{config}\n{principal_namespace}\n{idempotency_key}".encode("utf-8")
    digest = hashlib.sha256(token).hexdigest()
    return f"auth:idempotency:rq_engine_issue_session_token:{digest}"


def _idempotency_principal_namespace(
    *,
    auth_mode: str,
    claims: Mapping[str, Any] | None,
    user_id: int | None,
    session_id: str,
    anonymous_public_fallback: bool,
) -> str:
    if claims is not None:
        subject = str(claims.get("sub") or "").strip()
        if subject:
            return f"{auth_mode}:{subject}"
    if user_id is not None:
        return f"{auth_mode}:user:{user_id}"
    if anonymous_public_fallback:
        return f"{auth_mode}:public_anonymous"
    return f"{auth_mode}:session:{session_id}"


def _decode_idempotency_payload(raw_value: Any) -> Mapping[str, Any]:
    if raw_value is None:
        return {}
    if isinstance(raw_value, bytes):
        text = raw_value.decode("utf-8", errors="replace")
    else:
        text = str(raw_value)
    try:
        payload = json.loads(text)
    except (TypeError, ValueError):
        return {}
    if isinstance(payload, Mapping):
        return payload
    return {}


def _reserve_idempotency_key(
    *,
    runid: str,
    config: str,
    principal_namespace: str,
    idempotency_key: str,
    fingerprint: str,
) -> tuple[str | None, JSONResponse | None]:
    storage_key = _idempotency_storage_key(
        runid,
        config,
        idempotency_key,
        principal_namespace=principal_namespace,
    )
    ttl_seconds = _idempotency_ttl_seconds()
    serialized = json.dumps({"fingerprint": fingerprint}, sort_keys=True, separators=(",", ":"))
    conn_kwargs = redis_connection_kwargs(RedisDB.SESSION)
    redis_conn = redis.Redis(**conn_kwargs)
    try:
        existing = _decode_idempotency_payload(redis_conn.get(storage_key))
        if existing:
            existing_fingerprint = str(existing.get("fingerprint") or "")
            if existing_fingerprint == fingerprint:
                return (
                    None,
                    error_response(
                        "Duplicate idempotent replay rejected.",
                        status_code=409,
                        code=IDEMPOTENCY_REPLAY_REJECTED_CODE,
                    ),
                )
            return (
                None,
                error_response(
                    "Idempotency key reused with a different request payload.",
                    status_code=409,
                    code=IDEMPOTENCY_MISMATCH_CODE,
                ),
            )

        if redis_conn.set(storage_key, serialized, ex=ttl_seconds, nx=True):
            return (storage_key, None)

        raced = _decode_idempotency_payload(redis_conn.get(storage_key))
        raced_fingerprint = str(raced.get("fingerprint") or "")
        if raced_fingerprint == fingerprint:
            return (
                None,
                error_response(
                    "Duplicate idempotent replay rejected.",
                    status_code=409,
                    code=IDEMPOTENCY_REPLAY_REJECTED_CODE,
                ),
            )
        return (
            None,
            error_response(
                "Idempotency key reused with a different request payload.",
                status_code=409,
                code=IDEMPOTENCY_MISMATCH_CODE,
            ),
        )
    finally:
        close_fn = getattr(redis_conn, "close", None)
        if callable(close_fn):
            close_fn()


def _release_idempotency_key(storage_key: str | None) -> None:
    if not storage_key:
        return
    conn_kwargs = redis_connection_kwargs(RedisDB.SESSION)
    redis_conn = redis.Redis(**conn_kwargs)
    try:
        redis_conn.delete(storage_key)
    finally:
        close_fn = getattr(redis_conn, "close", None)
        if callable(close_fn):
            close_fn()


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
        "Supports Bearer or same-origin session-cookie auth. Bearer path requires `rq:status`; "
        "cookie path validates a server session marker with public-run fallback. "
        "Optional `X-Run-State-Match` and `Idempotency-Key` checks. "
        "Synchronously mints a run-scoped session token cookie."
    ),
    tags=["rq-engine", "session"],
    operation_id=rq_operation_id("issue_session_token"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Session token issued.",
    ),
)
async def issue_session_token(runid: str, config: str, request: Request) -> JSONResponse:
    idempotency_storage_key: str | None = None
    try:
        user_id: int | None = None
        roles: list[str] = []
        anonymous_public_fallback = False
        claims = _resolve_bearer_claims(request)
        auth_mode = "bearer_jwt" if claims is not None else "session_cookie_same_origin"
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
                    anonymous_public_fallback = True
                else:
                    raise

        request_payload = await _parse_optional_json_payload(request)
        expected_run_state_revision = _extract_expected_run_state_revision(request, request_payload)
        if expected_run_state_revision is not None:
            current_run_state_revision = _load_run_state_revision(runid, config)
            if expected_run_state_revision != current_run_state_revision:
                return _stale_run_state_response(
                    expected=expected_run_state_revision,
                    current=current_run_state_revision,
                )

        idempotency_key = _normalize_idempotency_key(request.headers.get(IDEMPOTENCY_KEY_HEADER))
        if idempotency_key is not None:
            principal_namespace = _idempotency_principal_namespace(
                auth_mode=auth_mode,
                claims=claims,
                user_id=user_id,
                session_id=session_id,
                anonymous_public_fallback=anonymous_public_fallback,
            )
            fingerprint = _idempotency_fingerprint(
                runid=runid,
                config=config,
                auth_mode=auth_mode,
                claims=claims,
                user_id=user_id,
                roles=roles,
                payload=request_payload,
                expected_run_state_revision=expected_run_state_revision,
            )
            idempotency_storage_key, conflict_response = _reserve_idempotency_key(
                runid=runid,
                config=config,
                principal_namespace=principal_namespace,
                idempotency_key=idempotency_key,
                fingerprint=fingerprint,
            )
            if conflict_response is not None:
                return conflict_response

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
        _release_idempotency_key(idempotency_storage_key)
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except auth_tokens.JWTConfigurationError as exc:
        _release_idempotency_key(idempotency_storage_key)
        return error_response(f"JWT configuration error: {exc}", status_code=500)
    except Exception:
        _release_idempotency_key(idempotency_storage_key)
        logger.exception("rq-engine session token issuance failed")
        return error_response_with_traceback("Failed to issue session token", status_code=500)


__all__ = ["router"]
