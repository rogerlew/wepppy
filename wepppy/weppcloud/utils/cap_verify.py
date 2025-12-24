"""CAPTCHA verification helpers for Cap.js."""

from __future__ import annotations

from typing import Any, Dict, Tuple
import os

import requests
from flask import current_app, has_request_context, request


class CapVerificationError(RuntimeError):
    """Raised when CAPTCHA verification fails or cannot be performed."""


def _resolve_cap_config() -> Tuple[str, str, str]:
    base_url = current_app.config.get("CAP_BASE_URL") or os.getenv("CAP_BASE_URL")
    site_key = current_app.config.get("CAP_SITE_KEY") or os.getenv("CAP_SITE_KEY")
    secret = current_app.config.get("CAP_SECRET") or os.getenv("CAP_SECRET")

    if not base_url:
        raise CapVerificationError("CAP_BASE_URL is required for CAPTCHA verification.")
    if not site_key:
        raise CapVerificationError("CAP_SITE_KEY is required for CAPTCHA verification.")
    if not secret:
        raise CapVerificationError("CAP_SECRET is required for CAPTCHA verification.")

    base_url = base_url.rstrip("/")
    if base_url.startswith("/"):
        if not has_request_context():
            raise CapVerificationError(
                "CAP_BASE_URL is relative but no request context is available."
            )
        base_url = f"{request.url_root.rstrip('/')}{base_url}"

    return base_url, site_key, secret


def verify_cap_token(token: str) -> Dict[str, Any]:
    """Validate a Cap.js token and return the raw verification payload."""
    if not token:
        raise CapVerificationError("CAP token is required for verification.")

    base_url, site_key, secret = _resolve_cap_config()
    verify_url = f"{base_url}/{site_key}/siteverify"

    try:
        response = requests.post(
            verify_url,
            json={"secret": secret, "response": token},
            timeout=6,
        )
    except requests.RequestException as exc:
        raise CapVerificationError(f"CAP siteverify request failed: {exc}") from exc

    if response.status_code != 200:
        raise CapVerificationError(
            f"CAP siteverify returned status {response.status_code}."
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise CapVerificationError("CAP siteverify returned invalid JSON.") from exc

    if not isinstance(payload, dict):
        raise CapVerificationError("CAP siteverify returned unexpected payload.")

    return payload
