from __future__ import annotations

import logging
import os
import uuid
from typing import Any, Mapping, Sequence

import redis
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from itsdangerous import BadSignature, Signer

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.base import NoDbBase
from wepppy.weppcloud.utils.helpers import get_wd
from wepppy.weppcloud.utils import auth_tokens

from .auth import AuthError, require_jwt
from .responses import error_response, error_response_with_traceback

logger = logging.getLogger(__name__)

router = APIRouter()

SESSION_TOKEN_TTL_SECONDS = 4 * 24 * 60 * 60
SESSION_TOKEN_SCOPES = ["rq:status", "rq:enqueue"]
SESSION_TOKEN_REQUIRED_SCOPES = ["rq:status"]
SESSION_KEY_PREFIX = "session:"


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


def _secret_key() -> str:
    secret = os.getenv("SECRET_KEY")
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
    with redis.Redis(**conn_kwargs) as redis_conn:
        if not redis_conn.exists(key):
            raise AuthError("Session expired or invalid", status_code=401)


def _store_session_marker(runid: str, session_id: str, ttl_seconds: int) -> None:
    key = f"auth:session:run:{runid}:{session_id}"
    conn_kwargs = redis_connection_kwargs(RedisDB.SESSION)
    with redis.Redis(**conn_kwargs) as redis_conn:
        redis_conn.setex(key, ttl_seconds, "1")


def _resolve_bearer_claims(request: Request) -> Mapping[str, Any] | None:
    if "authorization" not in {key.lower() for key in request.headers.keys()}:
        return None
    return require_jwt(request, required_scopes=SESSION_TOKEN_REQUIRED_SCOPES)


def _normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [item for item in (part.strip() for part in value.split(",")) if item]
    if isinstance(value, Sequence):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _ensure_run_claim(claims: Mapping[str, Any], runid: str) -> None:
    runs = _normalize_list(claims.get("runs") or claims.get("runid"))
    if runs and str(runid) not in runs:
        raise AuthError("Token not authorized for run", status_code=403, code="forbidden")


def _session_id_from_claims(claims: Mapping[str, Any]) -> str:
    token_class = claims.get("token_class")
    if token_class == "session":
        session_id = claims.get("session_id") or claims.get("sub")
        if session_id:
            return str(session_id)
    return uuid.uuid4().hex


def _run_is_public(runid: str) -> bool:
    try:
        wd = get_wd(runid, prefer_active=False)
    except Exception:
        return False
    return NoDbBase.ispublic(wd)


def _resolve_scopes(claims: Mapping[str, Any]) -> list[str]:
    scope_claim = claims.get("scope")
    scope_separator = auth_tokens.get_jwt_config().scope_separator
    if isinstance(scope_claim, str):
        return [scope for scope in scope_claim.split(scope_separator) if scope]
    if isinstance(scope_claim, (list, tuple)):
        return [str(scope) for scope in scope_claim if str(scope)]
    return list(SESSION_TOKEN_SCOPES)


@router.post("/runs/{runid}/{config}/session-token")
def issue_session_token(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = _resolve_bearer_claims(request)
        if claims is not None:
            _ensure_run_claim(claims, runid)
            session_id = _session_id_from_claims(claims)
        else:
            try:
                session_id = _resolve_session_id_from_cookie(request)
                _session_exists(session_id)
            except AuthError:
                if _run_is_public(runid):
                    session_id = uuid.uuid4().hex
                else:
                    raise

        token_payload = auth_tokens.issue_token(
            session_id,
            scopes=SESSION_TOKEN_SCOPES,
            audience="rq-engine",
            expires_in=SESSION_TOKEN_TTL_SECONDS,
            extra_claims={
                "token_class": "session",
                "session_id": session_id,
                "runid": runid,
                "config": config,
                "jti": uuid.uuid4().hex,
            },
        )
        claims = token_payload.get("claims", {})
        _store_session_marker(runid, session_id, SESSION_TOKEN_TTL_SECONDS)
        expires_at = claims.get("exp")
        scopes = _resolve_scopes(claims)
        return JSONResponse(
            {
                "token": token_payload.get("token"),
                "token_class": "session",
                "runid": runid,
                "config": config,
                "session_id": session_id,
                "expires_at": expires_at,
                "scopes": scopes,
                "audience": claims.get("aud"),
            }
        )
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except auth_tokens.JWTConfigurationError as exc:
        return error_response(f"JWT configuration error: {exc}", status_code=500)
    except Exception:
        logger.exception("rq-engine session token issuance failed")
        return error_response_with_traceback("Failed to issue session token", status_code=500)


__all__ = ["router"]
