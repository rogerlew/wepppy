from collections import Counter, deque
from collections.abc import Mapping, Sequence
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
import uuid

import json
import redis
from flask import send_from_directory, session
from flask_security import current_user
from werkzeug.routing import BuildError

from ._common import *  # noqa: F401,F403
from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.weppcloud.utils import auth_tokens
from wepppy.weppcloud.utils.helpers import exception_factory, handle_with_exception_factory
from wepppy.weppcloud.utils.rq_engine_token import issue_user_rq_engine_token


weppcloud_site_bp = Blueprint('weppcloud_site', __name__)

_ACCESS_LOG_ENV_KEY = 'WEPP_ACCESS_LOG_PATH'
_ACCESS_LOG_DEFAULTS = [
    '/geodata/weppcloud_runs/access.csv',
    '/wc1/geodata/weppcloud_runs/access.csv',
]
_RUN_LOCATIONS_FILENAME = 'runid-locations.json'
_LANDING_STATIC_DIRNAME = 'ui-lab'
_OPERATOR_TOKEN_ALLOWED_SCOPES = ("rq:read", "rq:status", "rq:enqueue", "rq:export")
_OPERATOR_TOKEN_ALLOWED_SCOPE_SET = frozenset(_OPERATOR_TOKEN_ALLOWED_SCOPES)
_OPERATOR_TOKEN_DEFAULT_TTL_SECONDS = 900
_OPERATOR_TOKEN_TTL_SECONDS_ENV = "RQ_ENGINE_OPERATOR_TOKEN_TTL_SECONDS"
_OPERATOR_TOKEN_RATE_LIMIT_COUNT_ENV = "RQ_ENGINE_OPERATOR_TOKEN_RATE_LIMIT_COUNT"
_OPERATOR_TOKEN_RATE_LIMIT_WINDOW_SECONDS_ENV = "RQ_ENGINE_OPERATOR_TOKEN_RATE_LIMIT_WINDOW_SECONDS"
_OPERATOR_TOKEN_RATE_LIMIT_MAX_BUCKETS_ENV = "RQ_ENGINE_OPERATOR_TOKEN_RATE_LIMIT_MAX_BUCKETS"
_OPERATOR_TOKEN_REDIS_TIMEOUT_SECONDS_ENV = "RQ_ENGINE_OPERATOR_TOKEN_REDIS_TIMEOUT_SECONDS"
_OPERATOR_TOKEN_RATE_LIMIT_LOCK = threading.Lock()
_OPERATOR_TOKEN_RATE_LIMIT_BUCKETS: dict[str, deque[float]] = {}


def _issue_rq_engine_token() -> str | None:
    return issue_user_rq_engine_token(current_user)


def _safe_int_env(name: str, *, default: int, minimum: int) -> int:
    configured = os.getenv(name, current_app.config.get(name))
    raw = str(configured or "").strip()
    if not raw:
        return default
    try:
        return max(minimum, int(raw))
    except (TypeError, ValueError):
        return default


def _operator_token_ttl_seconds() -> int:
    return _safe_int_env(
        _OPERATOR_TOKEN_TTL_SECONDS_ENV,
        default=_OPERATOR_TOKEN_DEFAULT_TTL_SECONDS,
        minimum=60,
    )


def _operator_token_rate_limit_count() -> int:
    return _safe_int_env(_OPERATOR_TOKEN_RATE_LIMIT_COUNT_ENV, default=20, minimum=1)


def _operator_token_rate_limit_window_seconds() -> int:
    return _safe_int_env(_OPERATOR_TOKEN_RATE_LIMIT_WINDOW_SECONDS_ENV, default=60, minimum=1)


def _operator_token_rate_limit_max_buckets() -> int:
    return _safe_int_env(_OPERATOR_TOKEN_RATE_LIMIT_MAX_BUCKETS_ENV, default=4096, minimum=128)


def _operator_token_redis_timeout_seconds() -> int:
    return _safe_int_env(_OPERATOR_TOKEN_REDIS_TIMEOUT_SECONDS_ENV, default=2, minimum=1)


def _request_has_body() -> bool:
    content_length = str(request.headers.get("Content-Length") or "").strip()
    if content_length:
        try:
            return int(content_length) > 0
        except (TypeError, ValueError):
            return True
    transfer_encoding = str(request.headers.get("Transfer-Encoding") or "").strip()
    return bool(transfer_encoding)


def _content_type_token() -> str:
    return str(request.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()


def _extract_bearer_token() -> str | None:
    authorization = str(request.headers.get("Authorization") or "").strip()
    if not authorization:
        return None
    token_type, _, token = authorization.partition(" ")
    if token_type.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def _scopes_from_claims(claims: Mapping[str, Any]) -> set[str]:
    scope_value = claims.get("scope")
    separator = auth_tokens.get_jwt_config().scope_separator

    def _split_scope_text(text: str) -> set[str]:
        scopes: set[str] = set()
        for chunk in text.split(separator):
            for token in chunk.split():
                cleaned = token.strip()
                if cleaned:
                    scopes.add(cleaned)
        return scopes

    if scope_value is None:
        return set()
    if isinstance(scope_value, str):
        return _split_scope_text(scope_value)
    if isinstance(scope_value, Sequence):
        scopes: set[str] = set()
        for item in scope_value:
            if isinstance(item, str):
                scopes.update(_split_scope_text(item))
        return scopes
    return set()


def _authorized_operator_scopes(claims: Mapping[str, Any]) -> list[str]:
    claim_scopes = _scopes_from_claims(claims)
    return [
        scope
        for scope in _OPERATOR_TOKEN_ALLOWED_SCOPES
        if scope in claim_scopes
    ]


def _default_requested_operator_scopes(authorized_scopes: Sequence[str]) -> list[str]:
    authorized_set = {scope for scope in authorized_scopes}
    for preferred_scope in ("rq:read", "rq:status"):
        if preferred_scope in authorized_set:
            return [preferred_scope]
    return []


def _parse_requested_operator_scopes(
    raw_requested_scopes: Any,
    *,
    authorized_scopes: Sequence[str],
) -> list[str]:
    if raw_requested_scopes is None:
        return _default_requested_operator_scopes(authorized_scopes)

    tokens: list[str] = []
    if isinstance(raw_requested_scopes, str):
        for chunk in raw_requested_scopes.replace(",", " ").split():
            token = chunk.strip()
            if token:
                tokens.append(token)
    elif isinstance(raw_requested_scopes, Sequence):
        for item in raw_requested_scopes:
            if not isinstance(item, str):
                raise ValueError("requested_scopes must contain strings only.")
            token = item.strip()
            if token:
                tokens.append(token)
    else:
        raise ValueError("requested_scopes must be a list of scope strings.")

    if not tokens:
        raise ValueError("requested_scopes must include at least one scope.")

    deduped: list[str] = []
    for scope in tokens:
        if scope not in deduped:
            deduped.append(scope)
    return deduped


def _caller_ip() -> str:
    if request.remote_addr:
        return str(request.remote_addr)
    return "unknown"


def _operator_rate_limit_key(*, subject: str, token_class: str) -> str:
    return f"{token_class}:{subject}:{_caller_ip()}"


def _is_operator_token_rate_limited(*, subject: str, token_class: str) -> tuple[bool, int, int]:
    limit_count = _operator_token_rate_limit_count()
    window_seconds = _operator_token_rate_limit_window_seconds()
    max_buckets = _operator_token_rate_limit_max_buckets()
    bucket_key = _operator_rate_limit_key(subject=subject, token_class=token_class)

    now = time.monotonic()
    cutoff = now - float(window_seconds)
    with _OPERATOR_TOKEN_RATE_LIMIT_LOCK:
        stale_keys: list[str] = []
        for key, candidate_bucket in _OPERATOR_TOKEN_RATE_LIMIT_BUCKETS.items():
            while candidate_bucket and candidate_bucket[0] <= cutoff:
                candidate_bucket.popleft()
            if not candidate_bucket:
                stale_keys.append(key)
        for key in stale_keys:
            _OPERATOR_TOKEN_RATE_LIMIT_BUCKETS.pop(key, None)

        bucket = _OPERATOR_TOKEN_RATE_LIMIT_BUCKETS.get(bucket_key)
        if bucket is None:
            if len(_OPERATOR_TOKEN_RATE_LIMIT_BUCKETS) >= max_buckets:
                return True, limit_count, window_seconds
            bucket = deque()
            _OPERATOR_TOKEN_RATE_LIMIT_BUCKETS[bucket_key] = bucket
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= limit_count:
            return True, limit_count, window_seconds
        bucket.append(now)
    return False, limit_count, window_seconds


def _operator_token_is_revoked(jti: str) -> bool:
    key = f"auth:jwt:revoked:{jti}"
    conn_kwargs = redis_connection_kwargs(RedisDB.LOCK)
    timeout_seconds = float(_operator_token_redis_timeout_seconds())
    conn_kwargs.setdefault("socket_timeout", timeout_seconds)
    conn_kwargs.setdefault("socket_connect_timeout", timeout_seconds)
    redis_conn = redis.Redis(**conn_kwargs)
    try:
        exists_fn = getattr(redis_conn, "exists", None)
        if callable(exists_fn):
            return bool(exists_fn(key))
        get_fn = getattr(redis_conn, "get", None)
        return bool(callable(get_fn) and get_fn(key))
    finally:
        close_fn = getattr(redis_conn, "close", None)
        if callable(close_fn):
            close_fn()


def _audit_operator_token_event(
    *,
    outcome: str,
    status_code: int,
    subject: str,
    token_class: str,
    requested_scopes: Sequence[str],
    granted_scopes: Sequence[str],
) -> None:
    current_app.logger.info(
        "rq_engine_operator_token_audit outcome=%s status_code=%s token_class=%s subject=%s requested_scopes=%s granted_scopes=%s ip=%s",
        outcome,
        status_code,
        token_class,
        subject,
        list(requested_scopes),
        list(granted_scopes),
        _caller_ip(),
    )


def _issue_operator_rq_engine_token(
    *,
    claims: Mapping[str, Any],
    scopes: Sequence[str],
) -> Mapping[str, Any]:
    token_class = str(claims.get("token_class") or "").strip().lower()
    subject = str(claims.get("sub") or "").strip()
    extra_claims: dict[str, Any] = {
        "token_class": token_class,
        "jti": uuid.uuid4().hex,
    }

    for passthrough_claim in ("email", "roles", "groups", "service_groups", "runid", "config"):
        value = claims.get(passthrough_claim)
        if value is not None:
            extra_claims[passthrough_claim] = value

    runs = claims.get("runs")
    if isinstance(runs, Sequence) and not isinstance(runs, str):
        runs = [str(run).strip() for run in runs if str(run).strip()]
    else:
        runs = None

    return auth_tokens.issue_token(
        subject,
        scopes=list(scopes),
        audience="rq-engine",
        expires_in=_operator_token_ttl_seconds(),
        runs=runs,
        extra_claims=extra_claims,
    )


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


def _allowed_origin_set() -> set[tuple[str, str, int]]:
    origins: set[tuple[str, str, int]] = set()

    def _add(candidate: str) -> None:
        normalized = _normalized_origin(candidate)
        if normalized is not None:
            origins.add(normalized)

    _add(request.host_url)
    _add(f"{request.scheme}://{request.host}")

    forwarded_proto = (request.headers.get("X-Forwarded-Proto") or "").split(",")[0].strip().lower()
    forwarded_host = (request.headers.get("X-Forwarded-Host") or "").split(",")[0].strip()
    if forwarded_proto and request.host:
        _add(f"{forwarded_proto}://{request.host}")
    if forwarded_host:
        _add(f"{forwarded_proto or request.scheme}://{forwarded_host}")

    external_host = (
        current_app.config.get("OAUTH_REDIRECT_HOST")
        or current_app.config.get("EXTERNAL_HOST")
        or ""
    )
    external_scheme = (current_app.config.get("OAUTH_REDIRECT_SCHEME") or request.scheme or "").strip().lower()
    if external_host:
        _add(f"{external_scheme}://{external_host}")

    return origins


def _is_same_origin_post() -> bool:
    fetch_site = (request.headers.get("Sec-Fetch-Site") or "").strip().lower()
    if fetch_site == "same-origin":
        return True
    if fetch_site in {"cross-site"}:
        return False

    allowed_origins = _allowed_origin_set()
    origin = request.headers.get("Origin", "").strip()
    if origin:
        normalized_origin = _normalized_origin(origin)
        return normalized_origin in allowed_origins

    referer = request.headers.get("Referer", "").strip()
    if not referer:
        return False

    parsed = urlparse(referer)
    if not parsed.scheme or not parsed.netloc:
        return False
    referer_origin = f"{parsed.scheme}://{parsed.netloc}"
    normalized_referer_origin = _normalized_origin(referer_origin)
    return normalized_referer_origin in allowed_origins


@weppcloud_site_bp.route('/api/auth/rq-engine-token', methods=['POST'])
def issue_rq_engine_token():
    if current_user.is_anonymous:
        response = error_factory('Authentication required.')
        response.status_code = 401
        return response
    if not _is_same_origin_post():
        response = error_factory('Cross-origin request blocked.')
        response.status_code = 403
        return response

    try:
        token = _issue_rq_engine_token()
    except auth_tokens.JWTConfigurationError as exc:
        current_app.logger.exception("Failed to issue rq-engine token via API")
        response = error_factory(f"JWT configuration error: {exc}")
        response.status_code = 500
        return response
    except Exception:
        current_app.logger.exception("Failed to issue rq-engine token via API")
        response = error_factory("Failed to issue rq-engine token.")
        response.status_code = 500
        return response

    return jsonify({"token": token})


@weppcloud_site_bp.route('/api/auth/rq-engine-operator-token', methods=['POST'])
def issue_rq_engine_operator_token():
    bearer_token = _extract_bearer_token()
    if bearer_token is None:
        _audit_operator_token_event(
            outcome="unauthorized",
            status_code=401,
            subject="unknown",
            token_class="unknown",
            requested_scopes=[],
            granted_scopes=[],
        )
        response = error_factory("Bearer token required.")
        response.status_code = 401
        return response

    try:
        claims = auth_tokens.decode_token(bearer_token, audience="rq-engine")
    except auth_tokens.JWTConfigurationError as exc:
        current_app.logger.exception("rq-engine operator token bootstrap configuration failure")
        _audit_operator_token_event(
            outcome="error",
            status_code=500,
            subject="unknown",
            token_class="unknown",
            requested_scopes=[],
            granted_scopes=[],
        )
        response = error_factory(f"JWT configuration error: {exc}")
        response.status_code = 500
        return response
    except auth_tokens.JWTDecodeError:
        _audit_operator_token_event(
            outcome="unauthorized",
            status_code=401,
            subject="unknown",
            token_class="unknown",
            requested_scopes=[],
            granted_scopes=[],
        )
        response = error_factory("Invalid bearer token.")
        response.status_code = 401
        return response
    except Exception:
        current_app.logger.exception("rq-engine operator token bootstrap decode failure")
        _audit_operator_token_event(
            outcome="unauthorized",
            status_code=401,
            subject="unknown",
            token_class="unknown",
            requested_scopes=[],
            granted_scopes=[],
        )
        response = error_factory("Failed to validate bearer token.")
        response.status_code = 401
        return response

    subject = str(claims.get("sub") or "").strip()
    token_class = str(claims.get("token_class") or "").strip().lower()
    jti = str(claims.get("jti") or "").strip()
    if not subject:
        _audit_operator_token_event(
            outcome="unauthorized",
            status_code=401,
            subject="unknown",
            token_class=token_class or "unknown",
            requested_scopes=[],
            granted_scopes=[],
        )
        response = error_factory("Bearer token missing subject claim.")
        response.status_code = 401
        return response
    if not jti:
        _audit_operator_token_event(
            outcome="unauthorized",
            status_code=401,
            subject=subject,
            token_class=token_class or "unknown",
            requested_scopes=[],
            granted_scopes=[],
        )
        response = error_factory("Bearer token missing jti claim.")
        response.status_code = 401
        return response
    if token_class not in {"user", "service"}:
        _audit_operator_token_event(
            outcome="forbidden",
            status_code=403,
            subject=subject,
            token_class=token_class or "unknown",
            requested_scopes=[],
            granted_scopes=[],
        )
        response = error_factory("Bearer token class not authorized for operator bootstrap.")
        response.status_code = 403
        return response

    limited, limit_count, window_seconds = _is_operator_token_rate_limited(subject=subject, token_class=token_class)
    if limited:
        response = error_factory(
            f"Rate limit exceeded: {limit_count} requests per {window_seconds} seconds.",
            status_code=429,
        )
        _audit_operator_token_event(
            outcome="rate_limited",
            status_code=429,
            subject=subject,
            token_class=token_class,
            requested_scopes=[],
            granted_scopes=[],
        )
        return response

    try:
        if _operator_token_is_revoked(jti):
            _audit_operator_token_event(
                outcome="forbidden",
                status_code=403,
                subject=subject,
                token_class=token_class,
                requested_scopes=[],
                granted_scopes=[],
            )
            response = error_factory("Bearer token has been revoked.", status_code=403)
            return response
    except redis.RedisError:
        current_app.logger.exception("rq-engine operator token bootstrap revocation service unavailable")
        _audit_operator_token_event(
            outcome="error",
            status_code=503,
            subject=subject,
            token_class=token_class,
            requested_scopes=[],
            granted_scopes=[],
        )
        response = error_factory(
            "Token revocation service unavailable. Retry with backoff.",
            status_code=503,
        )
        response.headers["Retry-After"] = "5"
        return response
    except Exception:
        current_app.logger.exception("rq-engine operator token bootstrap revocation check failure")
        _audit_operator_token_event(
            outcome="error",
            status_code=500,
            subject=subject,
            token_class=token_class,
            requested_scopes=[],
            granted_scopes=[],
        )
        response = error_factory("Failed to validate bearer token revocation status.", status_code=500)
        return response

    request_payload: Mapping[str, Any] = {}
    if _request_has_body():
        if _content_type_token() != "application/json":
            response = error_factory("Operator token bootstrap request body must use application/json.", status_code=400)
            _audit_operator_token_event(
                outcome="validation_error",
                status_code=400,
                subject=subject,
                token_class=token_class,
                requested_scopes=[],
                granted_scopes=[],
            )
            return response
        parsed_payload = request.get_json(silent=True)
        if parsed_payload is None:
            response = error_factory("Malformed JSON request body.", status_code=400)
            _audit_operator_token_event(
                outcome="validation_error",
                status_code=400,
                subject=subject,
                token_class=token_class,
                requested_scopes=[],
                granted_scopes=[],
            )
            return response
        if not isinstance(parsed_payload, Mapping):
            response = error_factory("JSON request body must be an object.", status_code=400)
            _audit_operator_token_event(
                outcome="validation_error",
                status_code=400,
                subject=subject,
                token_class=token_class,
                requested_scopes=[],
                granted_scopes=[],
            )
            return response
        request_payload = parsed_payload

    authorized_scopes = _authorized_operator_scopes(claims)
    if not authorized_scopes:
        response = error_factory("Bearer token does not authorize operator bootstrap scopes.", status_code=403)
        _audit_operator_token_event(
            outcome="forbidden",
            status_code=403,
            subject=subject,
            token_class=token_class,
            requested_scopes=[],
            granted_scopes=[],
        )
        return response

    try:
        requested_scopes = _parse_requested_operator_scopes(
            request_payload.get("requested_scopes"),
            authorized_scopes=authorized_scopes,
        )
    except ValueError as exc:
        response = error_factory(str(exc), status_code=400)
        _audit_operator_token_event(
            outcome="validation_error",
            status_code=400,
            subject=subject,
            token_class=token_class,
            requested_scopes=[],
            granted_scopes=[],
        )
        return response

    unknown_scopes = [scope for scope in requested_scopes if scope not in _OPERATOR_TOKEN_ALLOWED_SCOPE_SET]
    if unknown_scopes:
        response = error_factory(
            f"Unknown requested scope(s): {', '.join(unknown_scopes)}.",
            status_code=400,
        )
        _audit_operator_token_event(
            outcome="validation_error",
            status_code=400,
            subject=subject,
            token_class=token_class,
            requested_scopes=requested_scopes,
            granted_scopes=[],
        )
        return response

    unauthorized_requested_scopes = [scope for scope in requested_scopes if scope not in set(authorized_scopes)]
    if unauthorized_requested_scopes:
        response = error_factory(
            f"Unauthorized requested scope(s): {', '.join(unauthorized_requested_scopes)}.",
            status_code=403,
        )
        _audit_operator_token_event(
            outcome="forbidden",
            status_code=403,
            subject=subject,
            token_class=token_class,
            requested_scopes=requested_scopes,
            granted_scopes=[],
        )
        return response

    granted_scopes = [scope for scope in requested_scopes if scope in set(authorized_scopes)]
    if not granted_scopes:
        response = error_factory("No authorized scopes available for operator bootstrap.", status_code=403)
        _audit_operator_token_event(
            outcome="forbidden",
            status_code=403,
            subject=subject,
            token_class=token_class,
            requested_scopes=requested_scopes,
            granted_scopes=[],
        )
        return response

    try:
        token_payload = _issue_operator_rq_engine_token(claims=claims, scopes=granted_scopes)
    except auth_tokens.JWTConfigurationError as exc:
        current_app.logger.exception("rq-engine operator token bootstrap issuance failure")
        _audit_operator_token_event(
            outcome="error",
            status_code=500,
            subject=subject,
            token_class=token_class,
            requested_scopes=requested_scopes,
            granted_scopes=[],
        )
        response = error_factory(f"JWT configuration error: {exc}")
        response.status_code = 500
        return response
    except Exception:
        current_app.logger.exception("rq-engine operator token bootstrap issuance failure")
        _audit_operator_token_event(
            outcome="error",
            status_code=500,
            subject=subject,
            token_class=token_class,
            requested_scopes=requested_scopes,
            granted_scopes=[],
        )
        response = error_factory("Failed to issue operator token.")
        response.status_code = 500
        return response

    issued_claims = token_payload.get("claims", {})
    response = jsonify(
        {
            "token": token_payload.get("token"),
            "token_class": issued_claims.get("token_class"),
            "audience": issued_claims.get("aud"),
            "requested_scopes": requested_scopes,
            "granted_scopes": granted_scopes,
            "expires_at": issued_claims.get("exp"),
            "issued_at": issued_claims.get("iat"),
            "expires_in": _operator_token_ttl_seconds(),
        }
    )
    response.headers["Cache-Control"] = "no-store"
    _audit_operator_token_event(
        outcome="issued",
        status_code=200,
        subject=subject,
        token_class=token_class,
        requested_scopes=requested_scopes,
        granted_scopes=granted_scopes,
    )
    return response


@weppcloud_site_bp.route('/api/auth/session-heartbeat', methods=['POST'])
def session_heartbeat():
    if current_user.is_anonymous:
        response = error_factory('Authentication required.')
        response.status_code = 401
        return response
    if not _is_same_origin_post():
        response = error_factory('Cross-origin request blocked.')
        response.status_code = 403
        return response

    heartbeat_at = int(time.time())
    session["_heartbeat_ts"] = heartbeat_at
    session.modified = True
    return jsonify({"ok": True, "heartbeat_at": heartbeat_at})


def _normalized_cookie_path(value: Optional[str]) -> str:
    path = str(value or "").strip()
    if not path:
        return "/"
    if not path.startswith("/"):
        path = f"/{path}"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    return path or "/"


def _path_variants(value: Optional[str]) -> list[str]:
    candidates: list[str] = []
    raw = str(value or "").strip()
    if raw:
        candidates.append(raw)
    normalized = _normalized_cookie_path(value)
    candidates.append(normalized)
    if normalized != "/":
        candidates.append(f"{normalized}/")

    variants: list[str] = []
    for candidate in candidates:
        normalized_candidate = _normalized_cookie_path(candidate)
        if normalized_candidate not in variants:
            variants.append(normalized_candidate)
        if (
            normalized_candidate != "/"
            and not normalized_candidate.endswith("/")
            and f"{normalized_candidate}/" not in variants
        ):
            variants.append(f"{normalized_candidate}/")
    return variants


def _normalized_cookie_domain(value: Optional[str]) -> Optional[str]:
    token = str(value or "").strip().lower()
    if not token:
        return None
    if ":" in token:
        token = token.split(":", 1)[0].strip()
    if not token:
        return None
    return token


def _domain_variants(configured_domain: Optional[str]) -> list[Optional[str]]:
    variants: list[Optional[str]] = []

    def _add(value: Optional[str]) -> None:
        normalized = _normalized_cookie_domain(value)
        if not normalized:
            return
        base = normalized.lstrip(".")
        for candidate in (base, f".{base}"):
            if candidate and candidate not in variants:
                variants.append(candidate)

    _add(configured_domain)
    _add(request.host)
    _add(current_app.config.get("OAUTH_REDIRECT_HOST"))
    _add(current_app.config.get("EXTERNAL_HOST"))

    variants.append(None)
    return variants


def _cookie_clear_targets(
    configured_path: Optional[str],
    configured_domain: Optional[str],
) -> list[tuple[str, Optional[str]]]:
    targets: list[tuple[str, Optional[str]]] = []
    path_values = [
        configured_path,
        current_app.config.get("APPLICATION_ROOT"),
        "/",
    ]

    path_variants: list[str] = []
    for path_value in path_values:
        for variant in _path_variants(path_value):
            if variant not in path_variants:
                path_variants.append(variant)

    for path in path_variants:
        for domain in _domain_variants(configured_domain):
            target = (path, domain)
            if target not in targets:
                targets.append(target)
    return targets


def _clear_reset_browser_state_cookies(response) -> list[dict[str, Optional[str]]]:
    session_cookie_name = current_app.config.get("SESSION_COOKIE_NAME", "session")
    remember_cookie_name = current_app.config.get("REMEMBER_COOKIE_NAME", "remember_token")
    cookie_specs = [
        (
            session_cookie_name,
            current_app.config.get("SESSION_COOKIE_PATH"),
            current_app.config.get("SESSION_COOKIE_DOMAIN"),
        ),
        (
            remember_cookie_name,
            current_app.config.get("REMEMBER_COOKIE_PATH"),
            current_app.config.get("REMEMBER_COOKIE_DOMAIN")
            or current_app.config.get("SESSION_COOKIE_DOMAIN"),
        ),
        (
            "csrf_token",
            current_app.config.get("SESSION_COOKIE_PATH"),
            current_app.config.get("SESSION_COOKIE_DOMAIN"),
        ),
        (
            "csrftoken",
            current_app.config.get("SESSION_COOKIE_PATH"),
            current_app.config.get("SESSION_COOKIE_DOMAIN"),
        ),
    ]

    cleared: list[dict[str, Optional[str]]] = []
    seen_names: set[str] = set()
    for cookie_name, cookie_path, cookie_domain in cookie_specs:
        normalized_name = str(cookie_name or "").strip()
        if not normalized_name or normalized_name in seen_names:
            continue
        seen_names.add(normalized_name)
        for path, domain in _cookie_clear_targets(cookie_path, cookie_domain):
            response.delete_cookie(normalized_name, path=path, domain=domain)
            cleared.append(
                {
                    "name": normalized_name,
                    "path": path,
                    "domain": domain,
                }
            )
    return cleared

@weppcloud_site_bp.route('/api/auth/reset-browser-state', methods=['POST'])
def reset_browser_state():
    if current_user.is_anonymous:
        response = error_factory('Authentication required.')
        response.status_code = 401
        return response
    if not _is_same_origin_post():
        response = error_factory('Cross-origin request blocked.')
        response.status_code = 403
        return response

    session_key_count = len(list(session.keys()))
    session.clear()
    session.modified = True

    try:
        login_url = url_for('security.login')
    except BuildError:
        login_url = '/login'

    response = jsonify(
        {
            "ok": True,
            "login_url": login_url,
            "cleared_session_keys": session_key_count,
            "message": "Browser state reset. Continue by signing in again.",
        }
    )
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    _clear_reset_browser_state_cookies(response)
    return response


def _resolve_access_log_path() -> Path:
    override = os.environ.get(_ACCESS_LOG_ENV_KEY)
    configured = current_app.config.get(_ACCESS_LOG_ENV_KEY)
    if override:
        return Path(override)
    if configured:
        return Path(configured)

    for candidate in _ACCESS_LOG_DEFAULTS:
        candidate_path = Path(candidate)
        if candidate_path.exists():
            return candidate_path
    # Fall back to the first entry so downstream callers still receive a Path
    return Path(_ACCESS_LOG_DEFAULTS[0])


def _resolve_run_locations_path() -> Path:
    """Return a writable path for the run-locations cache file.

    Uses the same directory as the access log (typically /geodata/weppcloud_runs/)
    since that location is writable in production. Falls back to /tmp if the
    access log directory doesn't exist.
    """
    access_log_dir = _resolve_access_log_path().parent
    if access_log_dir.exists():
        return access_log_dir / _RUN_LOCATIONS_FILENAME
    # Fallback to /tmp for environments where geodata isn't mounted
    fallback = Path('/tmp')
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback / _RUN_LOCATIONS_FILENAME


def _resolve_landing_static_root() -> Path:
    return Path(current_app.static_folder) / _LANDING_STATIC_DIRNAME


def _resolve_landing_static_asset(*parts: str) -> Path:
    return _resolve_landing_static_root().joinpath(*parts)


def _load_or_refresh_run_locations(force: bool = False) -> List[Dict[str, Any]]:
    output_path = _resolve_run_locations_path()

    if force and not output_path.exists():
        current_app.logger.warning(
            "Run locations cache missing at %s; waiting for compile_dot_logs.",
            output_path,
        )
    try:
        with output_path.open() as handle:
            cached = json.load(handle)
            if isinstance(cached, list):
                return cached
    except (OSError, json.JSONDecodeError):
        pass
    return []


def _build_landing_state() -> Dict[str, Any]:
    user_info: Dict[str, Any] = {
        'is_authenticated': bool(getattr(current_user, 'is_authenticated', False)),
        'email': getattr(current_user, 'email', None),
        'name': getattr(current_user, 'name', None),
    }
    return {'user': user_info}


def _render_ui_lab_index_with_state(index_path: Path) -> Optional['flask.Response']:
    try:
        html = index_path.read_text(encoding='utf-8')
    except OSError:
        return None

    state_json = json.dumps(_build_landing_state())
    injection = f'<script>window.__WEPP_STATE__ = {state_json};</script>'
    if '</head>' in html:
        html = html.replace('</head>', f'{injection}</head>', 1)
    else:
        html = injection + html

    response = make_response(html)
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    return response


def _landing_assets_dir() -> Path:
    return _resolve_landing_static_asset('assets')


def _render_landing_page(variant: str = 'light') -> 'flask.Response':
    """Render landing page.

    Args:
        variant: 'light' for flat governmental style, 'dark' for aurora/glassmorphism style
    """
    try:
        _load_or_refresh_run_locations()
    except Exception:
        current_app.logger.exception('Failed to refresh landing run locations')

    index_file = 'index-light.html' if variant == 'light' else 'index.html'
    vite_index = _resolve_landing_static_asset(index_file)
    if vite_index.exists():
        rendered = _render_ui_lab_index_with_state(vite_index)
        if rendered is not None:
            return rendered

    return render_template('landing.htm', user=current_user)


@weppcloud_site_bp.route('/')
@handle_with_exception_factory
def index():
    return _render_landing_page('light')


@weppcloud_site_bp.route('/interfaces/', strict_slashes=False)
def interfaces():
    runs_counter = Counter()
    try:
        if _exists('/geodata/weppcloud_runs/runs_counter.json'):
            with open('/geodata/weppcloud_runs/runs_counter.json') as fp:
                runs_counter = Counter(json.load(fp))
    except (OSError, json.JSONDecodeError) as exc:
        current_app.logger.debug("Failed to load runs_counter.json for interfaces: %s", exc)
    except Exception:
        current_app.logger.exception("Unexpected error loading runs_counter.json for interfaces")

    try:
        cap_base_url = (current_app.config.get('CAP_BASE_URL') or os.getenv('CAP_BASE_URL', '/cap')).rstrip('/')
        cap_asset_base_url = (
            current_app.config.get('CAP_ASSET_BASE_URL')
            or os.getenv('CAP_ASSET_BASE_URL', f'{cap_base_url}/assets')
        ).rstrip('/')
        cap_site_key = current_app.config.get('CAP_SITE_KEY') or os.getenv('CAP_SITE_KEY', '')
        return render_template(
            'interfaces.htm',
            user=current_user,
            runs_counter=runs_counter,
            cap_base_url=cap_base_url,
            cap_asset_base_url=cap_asset_base_url,
            cap_site_key=cap_site_key,
        )
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/weppcloud_site.py:465", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return exception_factory()


@weppcloud_site_bp.route('/cap/verify', methods=['POST'])
@handle_with_exception_factory
def cap_verify():
    from wepppy.weppcloud.utils.cap_guard import mark_cap_verified
    from wepppy.weppcloud.utils.cap_verify import CapVerificationError, verify_cap_token

    payload = request.get_json(silent=True) or {}
    cap_token = (request.form.get('cap_token') or payload.get('cap_token') or '').strip()
    if not cap_token:
        response = error_factory('CAPTCHA token is required.')
        response.status_code = 403
        return response

    try:
        verification = verify_cap_token(cap_token)
    except CapVerificationError as exc:
        current_app.logger.error("CAPTCHA verification error from %s: %s", request.remote_addr, exc)
        return exception_factory('CAPTCHA verification failed.')

    if not verification.get('success'):
        current_app.logger.warning(
            "CAPTCHA rejected from %s (errors=%s)",
            request.remote_addr,
            verification.get('error-codes'),
        )
        response = error_factory('CAPTCHA verification failed.')
        response.status_code = 403
        return response

    mark_cap_verified()
    return jsonify({})


def _landing_run_locations_response() -> 'flask.Response':
    dataset = _load_or_refresh_run_locations()
    return jsonify(dataset)


@weppcloud_site_bp.route('/landing/', strict_slashes=False)
@handle_with_exception_factory
def landing():
    return _render_landing_page('light')


@weppcloud_site_bp.route('/landing/light/', strict_slashes=False)
@handle_with_exception_factory
def landing_light():
    """Render the light-themed (governmental aesthetic) landing page variant."""
    return _render_landing_page('light')


@weppcloud_site_bp.route('/landing/dark/', strict_slashes=False)
@handle_with_exception_factory
def landing_dark():
    """Render the dark-themed (aurora/glassmorphism) landing page variant."""
    return _render_landing_page('dark')


@weppcloud_site_bp.route('/landing/run-locations.json', strict_slashes=False)
@handle_with_exception_factory
def landing_run_locations():
    return _landing_run_locations_response()


@weppcloud_site_bp.route('/run-locations.json', strict_slashes=False)
@handle_with_exception_factory
def landing_run_locations_root():
    return _landing_run_locations_response()


def _get_mimetype_for_asset(asset_path: str) -> Optional[str]:
    """Return explicit MIME type for assets that Safari may reject otherwise."""
    if asset_path.endswith('.js'):
        return 'application/javascript'
    if asset_path.endswith('.mjs'):
        return 'application/javascript'
    if asset_path.endswith('.css'):
        return 'text/css'
    if asset_path.endswith('.json'):
        return 'application/json'
    return None


@weppcloud_site_bp.route('/landing/assets/<path:asset_path>', strict_slashes=False)
@handle_with_exception_factory
def landing_static_assets(asset_path: str):
    assets_root = _landing_assets_dir()
    if not assets_root.exists():
        abort(404)
    mimetype = _get_mimetype_for_asset(asset_path)
    if mimetype:
        return send_from_directory(assets_root, asset_path, mimetype=mimetype)
    return send_from_directory(assets_root, asset_path)


@weppcloud_site_bp.route('/assets/<path:asset_path>', strict_slashes=False)
@handle_with_exception_factory
def landing_static_assets_root(asset_path: str):
    return landing_static_assets(asset_path)


@weppcloud_site_bp.route('/landing/vite.svg', strict_slashes=False)
@handle_with_exception_factory
def landing_static_vite_icon():
    icon_path = _resolve_landing_static_asset('vite.svg')
    if not icon_path.exists():
        abort(404)
    return send_from_directory(icon_path.parent, icon_path.name)


@weppcloud_site_bp.route('/vite.svg', strict_slashes=False)
@handle_with_exception_factory
def landing_static_vite_icon_root():
    return landing_static_vite_icon()


def register_csrf_exemptions(csrf) -> None:
    # Bearer-auth operator bootstrap does not rely on browser cookies.
    csrf.exempt(issue_rq_engine_operator_token)
