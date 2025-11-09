from __future__ import annotations

from datetime import timedelta

from flask import Flask
from flask_jwt_extended import JWTManager

DEFAULT_AGENT_TOKEN_TTL: timedelta
AGENT_JWT_SECRET_KEY: str
AGENT_JWT_EXPIRES_KEY: str


def init_agent_jwt(app: Flask) -> JWTManager: ...


def generate_agent_token(
    *,
    user_id: str,
    runid: str,
    config: str,
    tier: str = ...,
    session_id: str | None = ...,
    expires: timedelta | None = ...,
) -> str: ...
