from __future__ import annotations

from typing import Any, Mapping, Sequence

SUPPORTED_HS_ALGORITHMS: dict[str, Any]
ENV_PREFIX: str
DEFAULT_SCOPE_SEPARATOR: str


class JWTConfigurationError(RuntimeError): ...


class JWTDecodeError(RuntimeError): ...


class JWTServiceConfig:
    __match_args__ = (
        "secret",
        "algorithms",
        "issuer",
        "default_audience",
        "default_ttl_seconds",
        "scope_separator",
        "leeway_seconds",
    )
    secret: str
    algorithms: tuple[str, ...]
    issuer: str | None
    default_audience: str | None
    default_ttl_seconds: int
    scope_separator: str
    leeway_seconds: int

    def __init__(
        self,
        secret: str,
        algorithms: tuple[str, ...],
        issuer: str | None,
        default_audience: str | None,
        default_ttl_seconds: int,
        scope_separator: str,
        leeway_seconds: int,
    ) -> None: ...


def get_jwt_config() -> JWTServiceConfig: ...


def encode_jwt(payload: Mapping[str, Any], secret: str, *, algorithm: str = ...) -> str: ...


def decode_jwt(
    token: str,
    *,
    secret: str,
    algorithms: Sequence[str],
    audience: Sequence[str] | None = ...,
    issuer: str | None = ...,
    leeway: int = ...,
) -> Mapping[str, Any]: ...


def issue_token(
    subject: str,
    *,
    scopes: Sequence[str] | str | None = ...,
    runs: Sequence[str] | None = ...,
    audience: Sequence[str] | str | None = ...,
    expires_in: int | None = ...,
    extra_claims: Mapping[str, Any] | None = ...,
    issued_at: int | None = ...,
) -> dict[str, Any]: ...


def decode_token(token: str, *, audience: Sequence[str] | str | None = ...) -> Mapping[str, Any]: ...
