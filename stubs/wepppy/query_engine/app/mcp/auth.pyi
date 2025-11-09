from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class AuthError(Exception):
    status_code: int
    code: str
    detail: str
    headers: dict[str, str]

class Unauthorized(AuthError): ...

class Forbidden(AuthError): ...

class MCPPrincipal:
    subject: str
    scopes: frozenset[str]
    run_ids: frozenset[str] | None
    token_id: str | None
    issuer: str | None
    claims: Mapping[str, Any]

    def has_scope(self, scope: str) -> bool: ...
    def require_scope(self, scope: str) -> None: ...

class MCPAuthConfig:
    secret: str
    algorithms: tuple[str, ...]
    audience: str | None
    issuer: str | None
    leeway_seconds: int
    scope_separator: str
    allowed_scopes: frozenset[str] | None

class MCPAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, config: MCPAuthConfig | None = ..., path_prefix: str = ..., optional: bool = ...) -> None: ...
    async def dispatch(self, request: Request, call_next) -> Response: ...

def decode_bearer_token(token: str, config: MCPAuthConfig) -> MCPPrincipal: ...

def encode_jwt(payload: Mapping[str, Any], secret: str, *, algorithm: str = ..., headers: Mapping[str, Any] | None = ...) -> str: ...

def get_auth_config() -> MCPAuthConfig: ...

def get_principal(request: Request) -> MCPPrincipal: ...

def require_scope(request: Request, scope: str) -> MCPPrincipal: ...
