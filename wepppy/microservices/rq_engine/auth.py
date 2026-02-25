from __future__ import annotations

import os
from typing import Any, Mapping, Sequence

import redis
from fastapi import Request

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.core import Ron
from wepppy.rq.auth_actor import set_auth_actor
from wepppy.weppcloud.utils.auth_tokens import (
    JWTConfigurationError,
    JWTDecodeError,
    decode_token,
    get_jwt_config,
)
from wepppy.weppcloud.utils.helpers import get_run_owners_lazy, get_wd


class AuthError(Exception):
    """Raised when JWT authentication fails."""

    def __init__(self, message: str, *, status_code: int = 401, code: str = "unauthorized") -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


def _extract_bearer_token(request: Request) -> str:
    header = request.headers.get("Authorization")
    if not header:
        raise AuthError("Missing Authorization header")
    parts = header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthError("Authorization header must be Bearer token")
    return parts[1].strip()


def _normalize_scopes(raw: Any, separator: str) -> set[str]:
    if raw is None:
        return set()
    if isinstance(raw, str):
        return {scope for scope in raw.split(separator) if scope}
    if isinstance(raw, Sequence):
        scopes: set[str] = set()
        for item in raw:
            if isinstance(item, str):
                scopes.update(scope for scope in item.split(separator) if scope)
        return scopes
    return set()


def _normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [item for item in (part.strip() for part in value.split(",")) if item]
    if isinstance(value, Sequence):
        items: list[str] = []
        for item in value:
            text = str(item).strip()
            if text:
                items.append(text)
        return items
    return []


def _normalize_roles(raw: Any) -> set[str]:
    if raw is None:
        return set()
    if isinstance(raw, str):
        return {role.strip().lower() for role in raw.split(",") if role.strip()}
    if isinstance(raw, Sequence):
        roles: set[str] = set()
        for item in raw:
            if isinstance(item, dict) and "name" in item:
                candidate = item.get("name")
            else:
                candidate = item
            if candidate is None:
                continue
            roles.add(str(candidate).strip().lower())
        return {role for role in roles if role}
    return set()


def _parse_user_id(raw: Any) -> int | None:
    if raw is None or isinstance(raw, bool):
        return None
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return None


def _sanitize_auth_actor(claims: Mapping[str, Any]) -> dict[str, Any] | None:
    token_class = str(claims.get("token_class") or "").strip().lower()
    if not token_class:
        return None

    actor: dict[str, Any] = {"token_class": token_class}

    if token_class == "user":
        user_id = _parse_user_id(claims.get("sub"))
        if user_id is None:
            return None
        actor["user_id"] = user_id
        return actor

    if token_class == "session":
        session_id = claims.get("session_id") or claims.get("sub")
        if not session_id:
            return None
        actor["session_id"] = str(session_id)
        return actor

    if token_class == "service":
        service_sub = str(claims.get("sub") or "").strip()
        if service_sub:
            actor["sub"] = service_sub
        service_groups = _normalize_list(claims.get("service_groups"))
        if service_groups:
            actor["service_groups"] = service_groups
        return actor if len(actor) > 1 else None

    if token_class == "mcp":
        mcp_sub = str(claims.get("sub") or "").strip()
        if mcp_sub:
            actor["sub"] = mcp_sub
        return actor if len(actor) > 1 else None

    return None


def require_roles(claims: Mapping[str, Any], required_roles: Sequence[str]) -> None:
    roles = _normalize_roles(claims.get("roles"))
    missing = [role for role in required_roles if role.lower() not in roles]
    if missing:
        raise AuthError(
            f"Token missing required role(s): {', '.join(missing)}",
            status_code=403,
            code="forbidden",
        )


def _authorization_runid(runid: str) -> str:
    raw = str(runid or "")
    parts = raw.split(";;")
    if len(parts) >= 3 and parts[-2] in {"omni", "omni-contrast"} and parts[-1]:
        return ";;".join(parts[:-2])
    return raw


def _authorize_user_claims(claims: Mapping[str, Any], runid: str) -> None:
    auth_runid = _authorization_runid(runid)
    roles = _normalize_roles(claims.get("roles"))
    if "admin" in roles or "root" in roles:
        return

    wd = get_wd(auth_runid, prefer_active=False)
    owners = get_run_owners_lazy(auth_runid)
    if Ron.ispublic(wd):
        return

    if not owners:
        if auth_runid.startswith("batch;;"):
            raise AuthError("Token not authorized for run", status_code=403, code="forbidden")
        return

    token_sub = str(claims.get("sub") or "").strip()
    token_email = str(claims.get("email") or "").strip().lower()
    for owner in owners:
        if token_sub and str(getattr(owner, "id", "")) == token_sub:
            return
        if token_email and getattr(owner, "email", "").lower() == token_email:
            return

    raise AuthError("Token not authorized for run", status_code=403, code="forbidden")


def _check_revocation(jti: str) -> None:
    if not jti:
        raise AuthError("Token missing jti claim")

    key = f"auth:jwt:revoked:{jti}"
    conn_kwargs = redis_connection_kwargs(RedisDB.LOCK)
    redis_conn = redis.Redis(**conn_kwargs)
    try:
        exists_fn = getattr(redis_conn, "exists", None)
        if callable(exists_fn):
            is_revoked = bool(exists_fn(key))
        else:
            get_fn = getattr(redis_conn, "get", None)
            is_revoked = bool(callable(get_fn) and get_fn(key))
        if is_revoked:
            raise AuthError("Token has been revoked", status_code=403, code="forbidden")
    finally:
        close_fn = getattr(redis_conn, "close", None)
        if callable(close_fn):
            close_fn()


def _check_session_marker(session_id: str, runid: str) -> None:
    if not session_id or not runid:
        raise AuthError("Session token missing required identifiers", status_code=403, code="forbidden")

    key = f"auth:session:run:{runid}:{session_id}"
    conn_kwargs = redis_connection_kwargs(RedisDB.SESSION)
    with redis.Redis(**conn_kwargs) as redis_conn:
        if not redis_conn.exists(key):
            raise AuthError(
                "Session token invalid or expired. Reload the page to continue.",
                status_code=401,
                code="unauthorized",
            )


def require_session_marker(claims: Mapping[str, Any], runid: str) -> None:
    token_class = str(claims.get("token_class") or "").strip().lower()
    if token_class != "session":
        return

    session_id = claims.get("session_id") or claims.get("sub")
    token_runid = claims.get("runid")
    if not session_id or not token_runid:
        raise AuthError("Session token missing run scope", status_code=403, code="forbidden")
    if str(token_runid) != str(runid):
        raise AuthError("Session token run mismatch", status_code=403, code="forbidden")

    _check_session_marker(str(session_id), str(runid))


def authorize_run_access(claims: Mapping[str, Any], runid: str) -> None:
    if not runid:
        return

    token_class = str(claims.get("token_class") or "").strip().lower()
    if token_class == "session":
        require_session_marker(claims, runid)
        return
    if token_class == "user":
        _authorize_user_claims(claims, runid)
        return

    run_claims = _normalize_list(claims.get("runs") or claims.get("runid"))
    if token_class in {"service", "mcp"} and not run_claims:
        raise AuthError("Token missing run scope", status_code=403, code="forbidden")
    if run_claims and str(runid) not in run_claims:
        raise AuthError("Token not authorized for run", status_code=403, code="forbidden")


def require_jwt(
    request: Request,
    *,
    audience: str | Sequence[str] | None = None,
    required_scopes: Sequence[str] | None = None,
) -> Mapping[str, Any]:
    token = _extract_bearer_token(request)
    if audience is None:
        audience = (os.getenv("RQ_ENGINE_JWT_AUDIENCE") or "rq-engine").strip() or None

    try:
        claims = decode_token(token, audience=audience)
    except JWTConfigurationError as exc:
        raise AuthError(f"JWT configuration error: {exc}", status_code=500) from exc
    except JWTDecodeError as exc:
        raise AuthError(f"Invalid token: {exc}") from exc

    _check_revocation(str(claims.get("jti") or ""))

    scope_separator = get_jwt_config().scope_separator
    scopes = _normalize_scopes(claims.get("scope"), scope_separator)
    if required_scopes:
        missing = [scope for scope in required_scopes if scope not in scopes]
        if missing:
            raise AuthError(
                f"Token missing required scope(s): {', '.join(missing)}",
                status_code=403,
                code="forbidden",
            )

    auth_actor = _sanitize_auth_actor(claims)
    if auth_actor is not None:
        set_auth_actor(auth_actor)

    return claims


__all__ = [
    "AuthError",
    "authorize_run_access",
    "require_jwt",
    "require_roles",
    "require_session_marker",
]
