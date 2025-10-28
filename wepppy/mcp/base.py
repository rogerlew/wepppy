from __future__ import annotations

import os
from functools import wraps
from typing import Any, Callable, Mapping, Sequence, TypeVar, cast

from wepppy.weppcloud.utils.agent_auth import AGENT_JWT_SECRET_KEY
from wepppy.weppcloud.utils.auth_tokens import JWTDecodeError, decode_jwt

F = TypeVar("F", bound=Callable[..., Any])

TOKEN_ENV_VAR = "AGENT_JWT_TOKEN"
ALGORITHMS_ENV_VAR = "AGENT_JWT_ALGORITHMS"
CLAIMS_KWARG = "_jwt_claims"


def _parse_algorithms(raw: str | None) -> Sequence[str]:
    if not raw:
        return ("HS256",)
    algorithms = [item.strip().upper() for item in raw.split(",") if item.strip()]
    if not algorithms:
        return ("HS256",)
    return tuple(algorithms)


def _load_claims(expected_tier: str) -> Mapping[str, Any]:
    token = os.getenv(TOKEN_ENV_VAR)
    if not token:
        raise PermissionError("Agent token missing from environment")

    secret = os.getenv(AGENT_JWT_SECRET_KEY)
    if not secret:
        raise PermissionError("Agent JWT secret missing from environment")

    algorithms = _parse_algorithms(os.getenv(ALGORITHMS_ENV_VAR))

    try:
        claims = decode_jwt(token, secret=secret, algorithms=algorithms)
    except JWTDecodeError as exc:
        raise PermissionError(f"Token validation failed: {exc}") from exc

    tier = claims.get("tier")
    if tier != expected_tier:
        raise PermissionError(
            f"Token tier {tier!r} does not match required tier {expected_tier!r}"
        )

    return claims


def mcp_tool(*, tier: str = "wojak") -> Callable[[F], F]:
    """
    Decorator for MCP tools that validates the Wojak session token before execution.
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            claims = kwargs.get(CLAIMS_KWARG)
            if claims is None:
                claims = _load_claims(tier)
                kwargs[CLAIMS_KWARG] = claims
            return func(*args, **kwargs)

        return cast(F, wrapper)

    return decorator


def validate_run_scope(
    runid: str, claims: Mapping[str, Any], *, config: str | None = None
) -> None:
    """
    Ensure the requested run/config matches the JWT scope.
    """

    token_runid = claims.get("runid")
    if token_runid != runid:
        raise PermissionError(f"Token scope denies access to run '{runid}'")

    token_config = claims.get("config")
    if config is not None and token_config is not None and token_config != config:
        raise PermissionError(
            f"Token scope denies access to config '{config}' (token grants '{token_config}')"
        )


def validate_runid(runid: str, claims: Mapping[str, Any]) -> None:
    """
    Backwards-compatible helper that validates run scope only.
    """

    validate_run_scope(runid, claims)
