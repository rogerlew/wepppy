"""JWT encoding/decoding utilities for WEPPCloud service auth."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Iterable, Mapping, Sequence

SUPPORTED_HS_ALGORITHMS = {
    "HS256": hashlib.sha256,
    "HS384": hashlib.sha384,
    "HS512": hashlib.sha512,
}

ENV_PREFIX = "WEPP_AUTH_JWT_"
DEFAULT_SCOPE_SEPARATOR = " "


class JWTConfigurationError(RuntimeError):
    """Raised when JWT configuration is missing or invalid."""


class JWTDecodeError(RuntimeError):
    """Raised when a token cannot be decoded or fails validation."""


@dataclass(frozen=True)
class JWTServiceConfig:
    secret: str
    algorithms: tuple[str, ...]
    issuer: str | None
    default_audience: str | None
    default_ttl_seconds: int
    scope_separator: str
    leeway_seconds: int


def _parse_algorithms(value: str | None) -> tuple[str, ...]:
    """Parse and validate the configured signing algorithm list.

    Args:
        value: Comma-delimited algorithm string or None.

    Returns:
        Tuple of supported algorithm identifiers.

    Raises:
        JWTConfigurationError: If the value is empty or contains unsupported algorithms.
    """
    if not value:
        return ("HS256",)
    algs: list[str] = []
    for item in value.split(","):
        alg = item.strip().upper()
        if not alg:
            continue
        if alg not in SUPPORTED_HS_ALGORITHMS:
            raise JWTConfigurationError(f"Unsupported algorithm '{alg}' configured")
        algs.append(alg)
    if not algs:
        raise JWTConfigurationError("At least one JWT algorithm must be configured")
    return tuple(algs)


@lru_cache(maxsize=1)
def get_jwt_config() -> JWTServiceConfig:
    """Load and cache JWT issuance settings from environment variables.

    Returns:
        Parsed `JWTServiceConfig` containing secrets and defaults.

    Raises:
        JWTConfigurationError: If the shared secret cannot be resolved.
    """
    secret = os.getenv(f"{ENV_PREFIX}SECRET")
    if not secret:
        raise JWTConfigurationError("WEPP_AUTH_JWT_SECRET must be set to issue tokens")

    algorithms = _parse_algorithms(os.getenv(f"{ENV_PREFIX}ALGORITHMS"))
    issuer = os.getenv(f"{ENV_PREFIX}ISSUER") or None
    default_audience = os.getenv(f"{ENV_PREFIX}DEFAULT_AUDIENCE") or None
    scope_separator = os.getenv(f"{ENV_PREFIX}SCOPE_SEPARATOR", DEFAULT_SCOPE_SEPARATOR)
    default_ttl = int(os.getenv(f"{ENV_PREFIX}DEFAULT_TTL_SECONDS", "3600") or 3600)
    leeway = int(os.getenv(f"{ENV_PREFIX}LEEWAY", "0") or 0)

    return JWTServiceConfig(
        secret=secret,
        algorithms=algorithms,
        issuer=issuer,
        default_audience=default_audience,
        default_ttl_seconds=default_ttl,
        scope_separator=scope_separator,
        leeway_seconds=leeway,
    )


def _urlsafe_b64encode(data: bytes) -> str:
    """Encode bytes using URL-safe base64 without padding."""
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _urlsafe_b64decode(segment: str, *, label: str) -> bytes:
    """Decode a URL-safe base64 segment, raising descriptive errors.

    Args:
        segment: Encoded token segment.
        label: Segment name to improve error messages.

    Returns:
        Decoded bytes for the requested segment.

    Raises:
        JWTDecodeError: If the data cannot be decoded.
    """
    padding = "=" * (-len(segment) % 4)
    try:
        return base64.urlsafe_b64decode(segment + padding)
    except (ValueError, binascii.Error) as exc:
        raise JWTDecodeError(f"Invalid token {label}") from exc


def encode_jwt(payload: Mapping[str, Any], secret: str, *, algorithm: str = "HS256") -> str:
    """Create a signed JWT for the provided payload.

    Args:
        payload: Mapping of claims to encode.
        secret: Shared secret used for HMAC signing.
        algorithm: Name of the HMAC digest.

    Returns:
        Fully encoded JWT string.

    Raises:
        ValueError: If the requested algorithm is not supported.
    """
    digest_factory = SUPPORTED_HS_ALGORITHMS.get(algorithm)
    if digest_factory is None:
        raise ValueError(f"Unsupported algorithm '{algorithm}'")

    header = {"alg": algorithm, "typ": "JWT"}
    header_segment = _urlsafe_b64encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_segment = _urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))

    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
    signature = hmac.new(secret.encode("utf-8"), signing_input, digest_factory).digest()
    signature_segment = _urlsafe_b64encode(signature)

    return f"{header_segment}.{payload_segment}.{signature_segment}"


def _decode_segments(token: str) -> tuple[Mapping[str, Any], Mapping[str, Any], bytes]:
    """Split a JWT into decoded header, payload, and signature segments."""
    segments = token.split(".")
    if len(segments) != 3:
        raise JWTDecodeError("Invalid token format")

    header_raw = _urlsafe_b64decode(segments[0], label="header")
    payload_raw = _urlsafe_b64decode(segments[1], label="payload")
    signature = _urlsafe_b64decode(segments[2], label="signature")

    try:
        header = json.loads(header_raw.decode("utf-8"))
        payload = json.loads(payload_raw.decode("utf-8"))
    except (ValueError, json.JSONDecodeError) as exc:
        raise JWTDecodeError("Invalid token payload") from exc

    if not isinstance(header, Mapping) or not isinstance(payload, Mapping):
        raise JWTDecodeError("Invalid token structure")

    return header, payload, signature


def decode_jwt(token: str, *, secret: str, algorithms: Sequence[str], audience: Sequence[str] | None = None, issuer: str | None = None, leeway: int = 0) -> Mapping[str, Any]:
    """Validate and decode a JWT using the provided verification context.

    Args:
        token: Encoded JWT to decode.
        secret: Shared secret used to validate the signature.
        algorithms: Allowed signing algorithms.
        audience: Expected audience list.
        issuer: Expected token issuer.
        leeway: Seconds of tolerance for `exp`/`nbf`/`iat` validation.

    Returns:
        Mapping of validated claims.

    Raises:
        JWTDecodeError: If the token structure, signature, or claims are invalid.
    """
    header, payload, signature = _decode_segments(token)

    algorithm = header.get("alg")
    if algorithm not in algorithms:
        raise JWTDecodeError("Token signed with unsupported algorithm")

    signing_input = ".".join(token.split(".")[:2]).encode("ascii")
    digest_factory = SUPPORTED_HS_ALGORITHMS.get(algorithm)
    expected = hmac.new(secret.encode("utf-8"), signing_input, digest_factory).digest()
    if not hmac.compare_digest(expected, signature):
        raise JWTDecodeError("Token signature mismatch")

    _validate_time_claims(payload, issuer=issuer, audience=audience, leeway=leeway)
    return payload


def _validate_time_claims(payload: Mapping[str, Any], *, issuer: str | None, audience: Sequence[str] | None, leeway: int) -> None:
    """Verify temporal, issuer, and audience constraints on a payload.

    Args:
        payload: Claims mapping to validate.
        issuer: Expected issuer or None to skip issuer checks.
        audience: Allowed audience values.
        leeway: Number of seconds added to tolerate clock skew.

    Raises:
        JWTDecodeError: If any constraint is violated.
    """
    now = time.time()

    exp = payload.get("exp")
    if exp is not None:
        if not isinstance(exp, (int, float)):
            raise JWTDecodeError("Token 'exp' claim must be numeric")
        if now > exp + leeway:
            raise JWTDecodeError("Token has expired")

    nbf = payload.get("nbf")
    if nbf is not None:
        if not isinstance(nbf, (int, float)):
            raise JWTDecodeError("Token 'nbf' claim must be numeric")
        if now + leeway < nbf:
            raise JWTDecodeError("Token not yet valid")

    iat = payload.get("iat")
    if iat is not None:
        if not isinstance(iat, (int, float)):
            raise JWTDecodeError("Token 'iat' claim must be numeric")
        if now + leeway < iat:
            raise JWTDecodeError("Token issued at time is in the future")

    if issuer is not None:
        token_issuer = payload.get("iss")
        if token_issuer != issuer:
            raise JWTDecodeError("Token issuer mismatch")

    if audience:
        token_aud = payload.get("aud")
        audiences: set[str]
        if token_aud is None:
            raise JWTDecodeError("Token missing audience")
        if isinstance(token_aud, str):
            audiences = {token_aud}
        elif isinstance(token_aud, Iterable):
            audiences = {str(item) for item in token_aud}
        else:
            raise JWTDecodeError("Token audience must be a string or list")
        if not audiences.intersection(audience):
            raise JWTDecodeError("Token audience not allowed")


def _format_scope_claim(scopes: Sequence[str] | str | None, separator: str) -> str | None:
    """Normalize scope inputs into a separator-delimited string.

    Args:
        scopes: Scope list or raw string from the caller.
        separator: Character(s) used to join scopes.

    Returns:
        Normalized scope claim or `None` if no scopes are provided.
    """
    if scopes is None:
        return None
    if isinstance(scopes, str):
        return scopes
    flattened: list[str] = []
    for scope in scopes:
        part = str(scope).strip()
        if part:
            flattened.append(part)
    if not flattened:
        return None
    return separator.join(flattened)


def issue_token(
    subject: str,
    *,
    scopes: Sequence[str] | str | None = None,
    runs: Sequence[str] | None = None,
    audience: Sequence[str] | str | None = None,
    expires_in: int | None = None,
    extra_claims: Mapping[str, Any] | None = None,
    issued_at: int | None = None,
) -> dict[str, Any]:
    """Issue a signed JWT suitable for downstream services.

    Args:
        subject: Value assigned to the `sub` claim.
        scopes: Optional scope list or string.
        runs: Optional run identifiers baked into the token.
        audience: Overrides for the `aud` claim.
        expires_in: TTL in seconds (defaults to the configured value).
        extra_claims: Additional claims to merge into the payload.
        issued_at: Optional custom `iat` timestamp.

    Returns:
        Dict containing the encoded `token` plus the final `claims`.

    Raises:
        ValueError: If the TTL is non-positive.
    """
    config = get_jwt_config()
    algorithm = config.algorithms[0]
    now = issued_at if issued_at is not None else int(time.time())
    ttl = expires_in if expires_in is not None else config.default_ttl_seconds
    if ttl <= 0:
        raise ValueError("expires_in must be positive")

    claims: dict[str, Any] = dict(extra_claims or {})
    claims["sub"] = subject
    claims["iat"] = now
    claims["exp"] = now + ttl

    if config.issuer:
        claims.setdefault("iss", config.issuer)

    resolved_audience: list[str] = []
    if config.default_audience:
        resolved_audience.append(config.default_audience)
    if audience is not None:
        if isinstance(audience, str):
            resolved_audience.append(audience)
        else:
            resolved_audience.extend(str(item) for item in audience)
    if resolved_audience:
        unique_audience = list(dict.fromkeys(str(a) for a in resolved_audience if a))
        if unique_audience:
            if len(unique_audience) == 1:
                claims["aud"] = unique_audience[0]
            else:
                claims["aud"] = unique_audience

    scope_claim = _format_scope_claim(scopes, config.scope_separator)
    if scope_claim:
        claims["scope"] = scope_claim

    if runs is not None:
        runs_list = [str(run).strip() for run in runs if str(run).strip()]
        if runs_list:
            claims["runs"] = runs_list

    token = encode_jwt(claims, config.secret, algorithm=algorithm)
    return {"token": token, "claims": claims}


def decode_token(token: str, *, audience: Sequence[str] | str | None = None) -> Mapping[str, Any]:
    """Decode and validate a token using the global JWT configuration.

    Args:
        token: JWT string to verify.
        audience: Optional audience override used during validation.

    Returns:
        Mapping of validated claims.
    """
    config = get_jwt_config()
    if audience is None:
        audience_set = [config.default_audience] if config.default_audience else None
    elif isinstance(audience, str):
        audience_set = [audience]
    else:
        audience_set = list(audience)

    return decode_jwt(
        token,
        secret=config.secret,
        algorithms=config.algorithms,
        audience=audience_set,
        issuer=config.issuer,
        leeway=config.leeway_seconds,
    )
