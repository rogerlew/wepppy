"""JWT helpers for Codex/agent integrations."""

from __future__ import annotations

import os
from datetime import timedelta
from typing import Optional

from flask import Flask, current_app
from flask_jwt_extended import JWTManager, create_access_token

DEFAULT_AGENT_TOKEN_TTL = timedelta(hours=24)
AGENT_JWT_SECRET_KEY = "AGENT_JWT_SECRET"
AGENT_JWT_EXPIRES_KEY = "AGENT_JWT_EXPIRES"


def init_agent_jwt(app: Flask) -> JWTManager:
    """Configure Flask-JWT-Extended for Wojak agent sessions.

    Args:
        app: Flask application instance that hosts the JWT endpoints.

    Returns:
        Initialized `JWTManager` bound to the provided Flask app.

    Raises:
        RuntimeError: If neither `AGENT_JWT_SECRET` nor `SECRET_KEY` are configured.
    """
    secret = app.config.get(AGENT_JWT_SECRET_KEY)
    if not secret:
        secret = os.getenv(AGENT_JWT_SECRET_KEY)
        if secret:
            app.config[AGENT_JWT_SECRET_KEY] = secret

    if not secret:
        secret = app.config.get("SECRET_KEY")
        if secret:
            app.logger.warning(
                "%s not configured; falling back to SECRET_KEY for agent JWTs",
                AGENT_JWT_SECRET_KEY,
            )
        else:
            raise RuntimeError(
                "Unable to configure agent JWTs: SECRET_KEY is not set on the Flask app"
            )

    app.config.setdefault("JWT_SECRET_KEY", secret)
    app.config.setdefault("JWT_ALGORITHM", "HS256")
    app.config.setdefault("JWT_TOKEN_LOCATION", ["headers"])
    app.config.setdefault("JWT_HEADER_TYPE", "Bearer")
    app.config.setdefault(AGENT_JWT_EXPIRES_KEY, DEFAULT_AGENT_TOKEN_TTL)

    return JWTManager(app)


def _resolve_expiry(expires: Optional[timedelta]) -> timedelta:
    """Resolve the token TTL from an explicit value or Flask config.

    Args:
        expires: Optional override supplied by the caller.

    Returns:
        The effective lifetime for a generated token.
    """
    if expires is not None:
        return expires

    config_value = current_app.config.get(AGENT_JWT_EXPIRES_KEY)
    if isinstance(config_value, timedelta):
        return config_value
    if isinstance(config_value, (int, float)):
        return timedelta(seconds=float(config_value))
    if isinstance(config_value, str):
        try:
            return timedelta(seconds=float(config_value))
        except ValueError:
            current_app.logger.warning(
                "Invalid %s value '%s'; defaulting to %s",
                AGENT_JWT_EXPIRES_KEY,
                config_value,
                DEFAULT_AGENT_TOKEN_TTL,
            )
    return DEFAULT_AGENT_TOKEN_TTL


def generate_agent_token(
    *,
    user_id: str,
    runid: str,
    config: str,
    tier: str = "wojak",
    session_id: Optional[str] = None,
    expires: Optional[timedelta] = None,
) -> str:
    """Issue a run-scoped JWT for an interactive agent.

    Args:
        user_id: Primary identifier for the interactive session.
        runid: WEPPCloud run folder identifier tied to the token.
        config: Run configuration slug.
        tier: Optional privilege tier included in the claims.
        session_id: Optional tracking identifier for correlated requests.
        expires: Optional explicit TTL; defaults to the Flask config.

    Returns:
        Encoded JWT containing the requested claims.

    Raises:
        ValueError: If any of the required identifiers are missing.
    """
    if not user_id:
        raise ValueError("user_id is required for agent tokens")
    if not runid:
        raise ValueError("runid is required for agent tokens")
    if not config:
        raise ValueError("config is required for agent tokens")

    ttl = _resolve_expiry(expires)
    claims = {
        "tier": tier,
        "runid": runid,
        "config": config,
    }
    if session_id:
        claims["session_id"] = session_id

    return create_access_token(identity=user_id, additional_claims=claims, expires_delta=ttl)
