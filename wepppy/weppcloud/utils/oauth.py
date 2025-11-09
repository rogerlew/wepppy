"""Helpers for configuring OAuth clients."""

from __future__ import annotations

import base64
import hashlib
import os
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional, Tuple
from urllib.parse import urlparse

from authlib.integrations.flask_client import OAuth
from flask import Flask, current_app


def _get_oauth_extension(app: Flask) -> OAuth:
    """Return the Authlib OAuth extension, creating it if needed.

    Args:
        app: Flask application instance.

    Returns:
        Configured Authlib `OAuth` extension.
    """
    oauth = app.extensions.get("authlib_oauth")
    if oauth is None:
        oauth = OAuth(app)
        app.extensions["authlib_oauth"] = oauth
    return oauth


def _infer_api_base_url(provider_settings: Dict[str, Any]) -> Optional[str]:
    """Infer an API base URL using provider metadata.

    Args:
        provider_settings: Provider configuration dictionary.

    Returns:
        String URL when it can be inferred, otherwise None.
    """
    api_base_url = provider_settings.get("api_base_url")
    if api_base_url:
        return api_base_url

    userinfo_url = provider_settings.get("userinfo_url")
    if not userinfo_url:
        return None

    parsed = urlparse(userinfo_url)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}/"


def ensure_oauth_client(
    provider: str,
    provider_settings: Dict[str, Any],
    *,
    app: Optional[Flask] = None,
):
    """Create (or retrieve) an Authlib client for the given provider.

    Args:
        provider: Provider slug used throughout the app.
        provider_settings: Dictionary loaded from configuration.
        app: Optional Flask app; defaults to `current_app`.

    Returns:
        Authlib client instance or None when the provider is disabled.
    """
    app = app or current_app

    client_id = provider_settings.get("client_id")
    client_secret = provider_settings.get("client_secret")
    if not (client_id and client_secret):
        return None

    oauth = _get_oauth_extension(app)
    client = oauth.create_client(provider)
    if client is not None:
        return client

    scope = provider_settings.get("scope") or []
    if isinstance(scope, str):
        scope = scope.split()

    client_kwargs = provider_settings.get("client_kwargs", {}).copy()
    if scope and "scope" not in client_kwargs:
        client_kwargs["scope"] = " ".join(scope)

    oauth.register(
        name=provider,
        client_id=client_id,
        client_secret=client_secret,
        access_token_url=provider_settings.get("token_url"),
        authorize_url=provider_settings.get("authorize_url"),
        api_base_url=_infer_api_base_url(provider_settings),
        client_kwargs=client_kwargs,
        userinfo_endpoint=provider_settings.get("userinfo_url"),
        server_metadata_url=provider_settings.get("server_metadata_url"),
    )

    return oauth.create_client(provider)


def build_pkce_pair() -> Tuple[str, str]:
    """Generate a PKCE verifier/challenge pair.

    Returns:
        Tuple containing `(code_verifier, code_challenge)`.
    """
    verifier_bytes = os.urandom(40)
    code_verifier = base64.urlsafe_b64encode(verifier_bytes).rstrip(b"=").decode("ascii")
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return code_verifier, code_challenge


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp.

    Returns:
        Current `datetime` in UTC.
    """
    return datetime.now(timezone.utc)


def _stringify_scopes(values: Iterable[Any]) -> str:
    """Convert a scope iterable into a canonical space-delimited string."""
    return " ".join(
        scope.strip()
        for scope in (str(item) for item in values)
        if scope and scope.strip()
    )


def normalize_token_scopes(
    token: Optional[Dict[str, Any]],
    provider_settings: Optional[Dict[str, Any]] = None,
) -> str:
    """Normalize scopes returned from an OAuth token exchange.

    Args:
        token: Token payload (if present) returned from Authlib.
        provider_settings: Provider configuration dictionary.

    Returns:
        Space-delimited scope string (may be empty).
    """
    token_scopes = ""
    if token:
        candidate = token.get("scope")
        if isinstance(candidate, str):
            token_scopes = _stringify_scopes(candidate.split())
        elif isinstance(candidate, (list, tuple, set)):
            token_scopes = _stringify_scopes(candidate)

    if token_scopes:
        return token_scopes

    if provider_settings:
        fallback = provider_settings.get("scope")
        if isinstance(fallback, str):
            return _stringify_scopes(fallback.split())
        if isinstance(fallback, (list, tuple, set)):
            return _stringify_scopes(fallback)

    return ""


def provider_enabled(provider_settings: Optional[Dict[str, Any]]) -> bool:
    """Return True when the provider configuration is enabled."""
    return bool(provider_settings and provider_settings.get("enabled"))
