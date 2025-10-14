from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Iterable, Mapping, Sequence

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


DEFAULT_SCOPE_SEPARATOR = " "
ENV_PREFIX = "WEPP_MCP_JWT_"
SUPPORTED_HS_ALGORITHMS = {
    "HS256": hashlib.sha256,
    "HS384": hashlib.sha384,
    "HS512": hashlib.sha512,
}


class AuthError(Exception):
    """Base class for authentication or authorization errors."""

    def __init__(self, *, status_code: int, code: str, detail: str, headers: Mapping[str, str] | None = None) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.code = code
        self.detail = detail
        self.headers = dict(headers or {})


class Unauthorized(AuthError):
    def __init__(self, detail: str = "Authentication required", headers: Mapping[str, str] | None = None) -> None:
        base_headers = {"WWW-Authenticate": 'Bearer realm="mcp"'}
        if headers:
            base_headers.update(headers)
        super().__init__(status_code=401, code="unauthorized", detail=detail, headers=base_headers)


class Forbidden(AuthError):
    def __init__(self, detail: str = "Insufficient scope") -> None:
        super().__init__(status_code=403, code="forbidden", detail=detail)


@dataclass(frozen=True)
class MCPPrincipal:
    subject: str
    scopes: frozenset[str] = field(default_factory=frozenset)
    run_ids: frozenset[str] | None = None
    token_id: str | None = None
    issuer: str | None = None
    claims: Mapping[str, Any] = field(default_factory=dict)

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes

    def require_scope(self, scope: str) -> None:
        if not self.has_scope(scope):
            raise Forbidden(detail=f"Scope '{scope}' is required")


@dataclass(frozen=True)
class MCPAuthConfig:
    secret: str
    algorithms: tuple[str, ...] = ("HS256",)
    audience: str | None = None
    issuer: str | None = None
    leeway_seconds: int = 0
    scope_separator: str = DEFAULT_SCOPE_SEPARATOR
    allowed_scopes: frozenset[str] | None = None


def _normalise_scope_claim(value: Any, *, separator: str = DEFAULT_SCOPE_SEPARATOR) -> frozenset[str]:
    if value is None:
        return frozenset()
    if isinstance(value, str):
        candidates = value.split(separator)
    elif isinstance(value, Iterable):
        candidates = []
        for item in value:
            if isinstance(item, str):
                candidates.extend(item.split(separator))
    else:
        return frozenset()
    scopes = [item.strip() for item in candidates if item and item.strip()]
    return frozenset(scopes)


def _normalise_runs_claim(value: Any) -> frozenset[str] | None:
    if value is None:
        return None
    if isinstance(value, str):
        return frozenset([value]) if value else frozenset()
    if isinstance(value, Iterable):
        runs = [str(item).strip() for item in value if str(item).strip()]
        return frozenset(runs)
    return None


def _ensure_allowed_scopes(scopes: frozenset[str], allowed_scopes: frozenset[str] | None) -> frozenset[str]:
    if allowed_scopes is None:
        return scopes
    invalid = scopes.difference(allowed_scopes)
    if invalid:
        raise Unauthorized(detail=f"Token includes unsupported scope(s): {', '.join(sorted(invalid))}")
    return scopes


def _decode_token(token: str, config: MCPAuthConfig) -> Mapping[str, Any]:
    header_segment, payload_segment, signature_segment = _split_token(token)
    header = _decode_segment(header_segment, "header")
    algorithm = header.get("alg")
    if algorithm not in config.algorithms:
        raise Unauthorized(detail="Token signed with unsupported algorithm")

    _verify_signature(header_segment, payload_segment, signature_segment, config.secret, algorithm)

    claims = _decode_segment(payload_segment, "payload")
    _validate_claims(claims, config)
    return claims


def _build_principal(claims: Mapping[str, Any], config: MCPAuthConfig) -> MCPPrincipal:
    subject = claims.get("sub")
    if not subject or not isinstance(subject, str):
        raise Unauthorized(detail="Token subject is missing")

    scopes = _normalise_scope_claim(claims.get("scope"), separator=config.scope_separator)
    scopes = _ensure_allowed_scopes(scopes, config.allowed_scopes)

    run_ids = _normalise_runs_claim(claims.get("runs"))
    token_id = claims.get("jti")
    issuer = claims.get("iss")

    return MCPPrincipal(
        subject=subject,
        scopes=scopes,
        run_ids=run_ids,
        token_id=token_id if isinstance(token_id, str) else None,
        issuer=issuer if isinstance(issuer, str) else None,
        claims=dict(claims),
    )


def decode_bearer_token(token: str, config: MCPAuthConfig) -> MCPPrincipal:
    claims = _decode_token(token, config)
    return _build_principal(claims, config)


def _split_token(token: str) -> tuple[str, str, str]:
    segments = token.split(".")
    if len(segments) != 3:
        raise Unauthorized(detail="Invalid token format")
    return segments[0], segments[1], segments[2]


def _urlsafe_b64decode(segment: str, *, label: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    try:
        return base64.urlsafe_b64decode(segment + padding)
    except (ValueError, binascii.Error) as exc:
        raise Unauthorized(detail=f"Invalid token {label}") from exc


def _decode_segment(segment: str, label: str) -> Mapping[str, Any]:
    raw = _urlsafe_b64decode(segment, label=label)
    try:
        decoded = json.loads(raw.decode("utf-8"))
    except (ValueError, json.JSONDecodeError) as exc:
        raise Unauthorized(detail=f"Invalid token {label}") from exc
    if not isinstance(decoded, Mapping):
        raise Unauthorized(detail=f"Invalid token {label}")
    return decoded


def _verify_signature(header_segment: str, payload_segment: str, signature_segment: str, secret: str, algorithm: str) -> None:
    digest_factory = SUPPORTED_HS_ALGORITHMS.get(algorithm)
    if digest_factory is None:
        raise Unauthorized(detail=f"Unsupported HMAC algorithm '{algorithm}'")

    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
    secret_bytes = secret.encode("utf-8")
    expected = hmac.new(secret_bytes, signing_input, digest_factory).digest()

    signature = _urlsafe_b64decode(signature_segment, label="signature")
    if not hmac.compare_digest(expected, signature):
        raise Unauthorized(detail="Invalid or expired access token")


def _validate_time_claim(claims: Mapping[str, Any], claim: str, comparison, *, leeway: int, detail: str) -> None:
    value = claims.get(claim)
    if value is None:
        return
    if not isinstance(value, (int, float)):
        raise Unauthorized(detail=f"Token {claim} claim must be numeric")
    now = time.time()
    if not comparison(now, value, leeway):
        raise Unauthorized(detail=detail)


def _validate_claims(claims: Mapping[str, Any], config: MCPAuthConfig) -> None:
    _validate_time_claim(
        claims,
        "exp",
        lambda now, exp, leeway: now <= exp + leeway,
        leeway=config.leeway_seconds,
        detail="Access token has expired",
    )
    _validate_time_claim(
        claims,
        "nbf",
        lambda now, nbf, leeway: now + leeway >= nbf,
        leeway=config.leeway_seconds,
        detail="Access token not yet valid",
    )
    _validate_time_claim(
        claims,
        "iat",
        lambda now, iat, leeway: now + leeway >= iat,
        leeway=config.leeway_seconds,
        detail="Access token issued-at time in the future",
    )

    if config.issuer is not None:
        issuer = claims.get("iss")
        if issuer != config.issuer:
            raise Unauthorized(detail="Token issuer mismatch")

    if config.audience is not None:
        audiences = claims.get("aud")
        if audiences is None:
            raise Unauthorized(detail="Token missing required audience")
        if isinstance(audiences, str):
            audiences = [audiences]
        if not isinstance(audiences, Iterable) or config.audience not in set(str(a).strip() for a in audiences):
            raise Unauthorized(detail="Token audience mismatch")


def encode_jwt(payload: Mapping[str, Any], secret: str, *, algorithm: str = "HS256", headers: Mapping[str, Any] | None = None) -> str:
    """Utility helper primarily for testing to issue HMAC JWTs."""
    digest_factory = SUPPORTED_HS_ALGORITHMS.get(algorithm)
    if digest_factory is None:
        raise ValueError(f"Unsupported algorithm '{algorithm}'")

    jwt_headers = {"alg": algorithm, "typ": "JWT"}
    if headers:
        jwt_headers.update(headers)

    header_segment = _urlsafe_b64encode(json.dumps(jwt_headers, separators=(",", ":")).encode("utf-8"))
    payload_segment = _urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
    signature = hmac.new(secret.encode("utf-8"), signing_input, digest_factory).digest()
    signature_segment = _urlsafe_b64encode(signature)
    return f"{header_segment}.{payload_segment}.{signature_segment}"


def _urlsafe_b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


@lru_cache(maxsize=1)
def get_auth_config() -> MCPAuthConfig:
    secret = os.getenv(f"{ENV_PREFIX}SECRET")
    if not secret:
        raise RuntimeError("WEPP_MCP_JWT_SECRET environment variable is required for MCP JWT auth")

    algorithms_env = os.getenv(f"{ENV_PREFIX}ALGORITHMS")
    algorithms: Sequence[str]
    if algorithms_env:
        algorithms = tuple(
            alg.strip()
            for alg in algorithms_env.split(",")
            if alg.strip()
        )
    else:
        algorithms = ("HS256",)

    audience = os.getenv(f"{ENV_PREFIX}AUDIENCE") or None
    issuer = os.getenv(f"{ENV_PREFIX}ISSUER") or None
    leeway = int(os.getenv(f"{ENV_PREFIX}LEEWAY", "0") or 0)
    scope_separator = os.getenv(f"{ENV_PREFIX}SCOPE_SEPARATOR", DEFAULT_SCOPE_SEPARATOR)

    allowed_scopes_env = os.getenv(f"{ENV_PREFIX}ALLOWED_SCOPES")
    allowed_scopes = (
        frozenset(scope.strip() for scope in allowed_scopes_env.split(",") if scope.strip())
        if allowed_scopes_env
        else None
    )

    return MCPAuthConfig(
        secret=secret,
        algorithms=tuple(algorithms),
        audience=audience,
        issuer=issuer,
        leeway_seconds=leeway,
        scope_separator=scope_separator,
        allowed_scopes=allowed_scopes,
    )


def _extract_bearer_token(header_value: str | None) -> str:
    if not header_value:
        raise Unauthorized(detail="Missing Authorization header")
    parts = header_value.strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise Unauthorized(detail="Authorization header must be 'Bearer <token>'")
    return parts[1]


class MCPAuthMiddleware(BaseHTTPMiddleware):
    """Authenticate MCP requests using JWT bearer tokens."""

    def __init__(
        self,
        app,
        *,
        config: MCPAuthConfig | None = None,
        path_prefix: str = "/mcp",
        optional: bool = False,
    ) -> None:
        super().__init__(app)
        self._config = config or get_auth_config()
        self._path_prefix = path_prefix.rstrip("/") or "/mcp"
        self._optional = optional

    async def dispatch(self, request: Request, call_next) -> Response:
        if not request.url.path.startswith(self._path_prefix):
            return await call_next(request)

        try:
            header = request.headers.get("Authorization")
            if header is None and self._optional:
                return await call_next(request)
            token = _extract_bearer_token(header)
            principal = decode_bearer_token(token, self._config)
            request.state.mcp_principal = principal
        except AuthError as exc:
            payload = {"errors": [{"code": exc.code, "detail": exc.detail}]}
            return JSONResponse(payload, status_code=exc.status_code, headers=exc.headers)

        return await call_next(request)


def get_principal(request: Request) -> MCPPrincipal:
    principal = getattr(request.state, "mcp_principal", None)
    if principal is None:
        raise Unauthorized(detail="Missing authentication context")
    return principal


def require_scope(request: Request, scope: str) -> MCPPrincipal:
    principal = get_principal(request)
    principal.require_scope(scope)
    return principal
