"""Authorization helpers shared across browse-service route families."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Mapping, Sequence
from urllib.parse import quote

import redis
from starlette.exceptions import HTTPException
from starlette.requests import Request as StarletteRequest
from starlette.responses import RedirectResponse

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.microservices.rq_engine.auth import (
    AuthError as RqAuthError,
    authorize_run_access,
)
from wepppy.nodb.base import NoDbBase
from wepppy.weppcloud.utils import auth_tokens
from wepppy.weppcloud.utils.auth_tokens import JWTConfigurationError, JWTDecodeError
from wepppy.weppcloud.utils.browse_cookie import browse_cookie_name_candidates
from wepppy.weppcloud.utils.helpers import get_wd

DEFAULT_BROWSE_JWT_COOKIE_NAME = "wepp_browse_jwt"
BROWSE_JWT_COOKIE_NAME_ENV = "WEPP_BROWSE_JWT_COOKIE_NAME"
DEFAULT_SITE_PREFIX = "/weppcloud"
ROOT_ONLY_FILENAMES = frozenset({"exceptions.log", "exception_factory.log"})
RUN_ALLOWED_TOKEN_CLASSES = frozenset({"session", "user", "service"})
USER_SERVICE_TOKEN_CLASSES = frozenset({"user", "service"})
GROUP_USER_TOKEN_ALLOWED_ROLES = frozenset({"admin", "poweruser", "dev", "root"})


@dataclass(frozen=True)
class AuthContext:
    claims: Mapping[str, Any] | None
    token_class: str | None
    roles: frozenset[str]
    source: str = "none"

    @property
    def is_authenticated(self) -> bool:
        return self.claims is not None

    @property
    def is_root(self) -> bool:
        return "root" in self.roles


class BrowseAuthError(Exception):
    """Raised when browse-route authentication or authorization fails."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 401,
        code: str = "unauthorized",
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


def _normalize_prefix(prefix: str | None) -> str:
    if not prefix:
        return ""
    trimmed = prefix.strip()
    if not trimmed or trimmed == "/":
        return ""
    return "/" + trimmed.strip("/")


def site_prefix() -> str:
    return _normalize_prefix(os.getenv("SITE_PREFIX", DEFAULT_SITE_PREFIX))


def browse_jwt_cookie_name() -> str:
    raw = (os.getenv(BROWSE_JWT_COOKIE_NAME_ENV) or "").strip()
    return raw or DEFAULT_BROWSE_JWT_COOKIE_NAME


def request_prefers_navigation(request: StarletteRequest) -> bool:
    sec_fetch_mode = (request.headers.get("sec-fetch-mode") or "").strip().lower()
    if sec_fetch_mode == "navigate":
        return True

    sec_fetch_dest = (request.headers.get("sec-fetch-dest") or "").strip().lower()
    if sec_fetch_dest in {"document", "iframe"}:
        return True

    accept = (request.headers.get("accept") or "").lower()
    return "text/html" in accept


def build_runs0_nocfg_redirect(
    runid: str,
    request_target: str,
    *,
    prefix: str | None = None,
) -> str:
    base_prefix = _normalize_prefix(prefix) if prefix is not None else site_prefix()
    encoded_next = quote(request_target, safe="")
    return f"{base_prefix}/runs/{runid}/?next={encoded_next}"


def is_root_only_path(raw_path: str) -> bool:
    if not raw_path:
        return False
    normalized = raw_path.replace("\\", "/")
    parts = [part.casefold() for part in normalized.split("/") if part not in ("", ".")]
    if not parts:
        return False
    if "_logs" in parts:
        return True
    return parts[-1] in ROOT_ONLY_FILENAMES


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


def _normalize_roles(value: Any) -> frozenset[str]:
    if value is None:
        return frozenset()
    if isinstance(value, str):
        return frozenset(
            role.strip().lower() for role in value.split(",") if role.strip()
        )
    if isinstance(value, Sequence):
        values: set[str] = set()
        for item in value:
            if isinstance(item, dict) and "name" in item:
                candidate = item.get("name")
            else:
                candidate = item
            if candidate is None:
                continue
            token = str(candidate).strip().lower()
            if token:
                values.add(token)
        return frozenset(values)
    return frozenset()


def _normalize_token_class(claims: Mapping[str, Any]) -> str | None:
    token_class = str(claims.get("token_class") or "").strip().lower()
    return token_class or None


def _extract_bearer_token(request: StarletteRequest) -> str | None:
    header = request.headers.get("Authorization")
    if not header:
        return None
    parts = header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise BrowseAuthError("Authorization header must be Bearer token")
    return parts[1].strip()


def _check_revocation(jti: str) -> None:
    if not jti:
        raise BrowseAuthError("Token missing jti claim")
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
            raise BrowseAuthError(
                "Token has been revoked",
                status_code=403,
                code="forbidden",
            )
    finally:
        close_fn = getattr(redis_conn, "close", None)
        if callable(close_fn):
            close_fn()


def _decode_token(token: str) -> Mapping[str, Any]:
    audience = (os.getenv("RQ_ENGINE_JWT_AUDIENCE") or "rq-engine").strip() or None
    try:
        claims = auth_tokens.decode_token(token, audience=audience)
    except JWTConfigurationError as exc:
        raise BrowseAuthError(
            f"JWT configuration error: {exc}",
            status_code=500,
            code="internal_error",
        ) from exc
    except JWTDecodeError as exc:
        raise BrowseAuthError(f"Invalid token: {exc}") from exc

    _check_revocation(str(claims.get("jti") or ""))
    return claims


def _context_from_claims(claims: Mapping[str, Any], *, source: str) -> AuthContext:
    return AuthContext(
        claims=claims,
        token_class=_normalize_token_class(claims),
        roles=_normalize_roles(claims.get("roles")),
        source=source,
    )


def _browse_cookie_names_for_request(
    *,
    runid: str | None = None,
    config: str | None = None,
) -> list[str]:
    default_name = browse_jwt_cookie_name()
    if runid and config:
        return browse_cookie_name_candidates(default_name, runid, config)
    return [default_name]


def resolve_auth_context(
    request: StarletteRequest,
    *,
    runid: str | None = None,
    config: str | None = None,
) -> AuthContext:
    cookie_failure: BrowseAuthError | None = None

    for cookie_name in _browse_cookie_names_for_request(runid=runid, config=config):
        cookie_token = request.cookies.get(cookie_name)
        if not cookie_token:
            continue
        try:
            return _context_from_claims(_decode_token(cookie_token), source="cookie")
        except BrowseAuthError as exc:
            if exc.status_code >= 500:
                raise
            cookie_failure = exc

    bearer_context = resolve_bearer_context(request)
    if bearer_context is not None:
        return bearer_context

    # Treat an invalid/stale cookie as anonymous when no bearer token is provided.
    # Private endpoints still reject anonymous callers; public browse remains accessible.
    if cookie_failure is not None:
        return AuthContext(claims=None, token_class=None, roles=frozenset())

    return AuthContext(claims=None, token_class=None, roles=frozenset())


def resolve_bearer_context(request: StarletteRequest) -> AuthContext | None:
    bearer_token = _extract_bearer_token(request)
    if not bearer_token:
        return None
    return _context_from_claims(_decode_token(bearer_token), source="bearer")


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
    except Exception:
        return False
    return NoDbBase.ispublic(wd)


def _require_identifier_claim(
    claims: Mapping[str, Any],
    identifier: str,
    *,
    require_service_claim: bool = True,
    require_session_claim: bool = True,
    identifier_aliases: Sequence[str] | None = None,
) -> None:
    token_class = _normalize_token_class(claims)
    if token_class not in {"service", "session"}:
        return

    allowed_identifiers = {str(identifier)}
    if identifier_aliases:
        allowed_identifiers.update(
            str(alias).strip() for alias in identifier_aliases if str(alias).strip()
        )

    run_claims = _normalize_list(claims.get("runs") or claims.get("runid"))
    if token_class == "service" and require_service_claim and not run_claims:
        raise BrowseAuthError(
            "Token missing run scope",
            status_code=403,
            code="forbidden",
        )
    if token_class == "session" and require_session_claim and not run_claims:
        raise BrowseAuthError(
            "Session token missing run scope",
            status_code=403,
            code="forbidden",
        )
    if run_claims and allowed_identifiers.isdisjoint(run_claims):
        raise BrowseAuthError(
            "Token not authorized for run",
            status_code=403,
            code="forbidden",
        )


def authorize_run_request(
    request: StarletteRequest,
    *,
    runid: str,
    config: str,
    subpath: str,
    allow_public_without_token: bool,
    require_authenticated: bool,
    allowed_token_classes: Sequence[str] = tuple(RUN_ALLOWED_TOKEN_CLASSES),
) -> AuthContext:
    def _evaluate_context(context: AuthContext) -> AuthContext:
        root_only = is_root_only_path(subpath)

        if not context.is_authenticated:
            if (
                allow_public_without_token
                and not require_authenticated
                and not root_only
                and _run_is_public(runid)
            ):
                return context
            raise BrowseAuthError("Authentication required")

        token_class = context.token_class
        if token_class not in {item.lower() for item in allowed_token_classes}:
            raise BrowseAuthError(
                "Token class is not allowed for this endpoint",
                status_code=403,
                code="forbidden",
            )

        assert context.claims is not None  # For type narrowing.
        _require_identifier_claim(context.claims, runid)
        try:
            authorize_run_access(context.claims, runid)
        except RqAuthError as exc:
            raise BrowseAuthError(
                exc.message,
                status_code=exc.status_code,
                code=exc.code,
            ) from exc

        if root_only and not context.is_root:
            raise BrowseAuthError(
                "Root role required for this path",
                status_code=403,
                code="forbidden",
            )
        return context

    context = resolve_auth_context(request, runid=runid, config=config)
    try:
        return _evaluate_context(context)
    except BrowseAuthError as primary_exc:
        if context.source == "cookie":
            bearer_context = resolve_bearer_context(request)
            if bearer_context is not None:
                return _evaluate_context(bearer_context)
        raise primary_exc


def authorize_group_request(
    request: StarletteRequest,
    *,
    identifier: str,
    subpath: str,
    allowed_token_classes: Sequence[str] = tuple(USER_SERVICE_TOKEN_CLASSES),
    required_service_groups: Sequence[str] | None = None,
    allow_public_without_token: bool = False,
    public_runid: str | None = None,
    identifier_claim_aliases: Sequence[str] | None = None,
) -> AuthContext:
    allowed_token_classes_lower = {item.lower() for item in allowed_token_classes}

    def _evaluate_context(context: AuthContext) -> AuthContext:
        root_only = is_root_only_path(subpath)

        if not context.is_authenticated:
            if (
                allow_public_without_token
                and not root_only
                and public_runid
                and _run_is_public(public_runid)
            ):
                return context
            raise BrowseAuthError("Authentication required")

        token_class = context.token_class
        if token_class not in allowed_token_classes_lower:
            raise BrowseAuthError(
                "Token class is not allowed for this endpoint",
                status_code=403,
                code="forbidden",
            )

        assert context.claims is not None  # For type narrowing.
        _require_identifier_claim(
            context.claims,
            identifier,
            require_service_claim=True,
            require_session_claim="session" in allowed_token_classes_lower,
            identifier_aliases=identifier_claim_aliases,
        )
        if context.token_class == "user" and not (
            context.roles & GROUP_USER_TOKEN_ALLOWED_ROLES
        ):
            raise BrowseAuthError(
                "User token requires Admin, PowerUser, Dev, or Root role",
                status_code=403,
                code="forbidden",
            )

        if context.token_class == "service" and required_service_groups:
            required = {
                str(group).strip().lower()
                for group in required_service_groups
                if str(group).strip()
            }
            if required:
                present = {
                    group.lower()
                    for group in _normalize_list(context.claims.get("service_groups"))
                    if group
                }
                missing = required - present
                if missing:
                    raise BrowseAuthError(
                        "Service token missing required group scope",
                        status_code=403,
                        code="forbidden",
                    )

        if root_only and not context.is_root:
            raise BrowseAuthError(
                "Root role required for this path",
                status_code=403,
                code="forbidden",
            )
        return context

    context = resolve_auth_context(request)
    try:
        return _evaluate_context(context)
    except BrowseAuthError as primary_exc:
        if context.source == "cookie":
            bearer_context = resolve_bearer_context(request)
            if bearer_context is not None:
                return _evaluate_context(bearer_context)
        raise primary_exc


def handle_auth_error(
    request: StarletteRequest,
    *,
    runid: str,
    error: BrowseAuthError,
    redirect_on_401: bool,
    redirect_html_only: bool = False,
) -> RedirectResponse:
    if error.status_code == 401 and redirect_on_401:
        if (not redirect_html_only) or request_prefers_navigation(request):
            request_target = request.url.path
            if request.url.query:
                request_target = f"{request_target}?{request.url.query}"
            return RedirectResponse(
                build_runs0_nocfg_redirect(runid, request_target),
                status_code=302,
            )

    raise HTTPException(status_code=error.status_code, detail=error.message)


__all__ = [
    "AuthContext",
    "BROWSE_JWT_COOKIE_NAME_ENV",
    "BrowseAuthError",
    "DEFAULT_BROWSE_JWT_COOKIE_NAME",
    "GROUP_USER_TOKEN_ALLOWED_ROLES",
    "RUN_ALLOWED_TOKEN_CLASSES",
    "USER_SERVICE_TOKEN_CLASSES",
    "authorize_group_request",
    "authorize_run_request",
    "browse_jwt_cookie_name",
    "build_runs0_nocfg_redirect",
    "handle_auth_error",
    "is_root_only_path",
    "request_prefers_navigation",
    "resolve_bearer_context",
    "resolve_auth_context",
    "site_prefix",
]
