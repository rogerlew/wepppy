"""Helpers for guarding routes with Cap.js verification."""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar
import os
import time

from flask import current_app, render_template, request, session, url_for
from flask_security import current_user

from wepppy.weppcloud.utils.cap_verify import CapVerificationError
from wepppy.weppcloud.utils.helpers import error_factory, exception_factory


ResponseValue = TypeVar("ResponseValue")

CAP_SESSION_KEY = "cap_verified_at"
DEFAULT_TTL_SECONDS = 20 * 60


def _cap_ttl_seconds(override: Optional[int] = None) -> int:
    if override is not None:
        return int(override)
    configured = current_app.config.get("CAP_SESSION_TTL_SECONDS")
    if configured is None:
        configured = os.getenv("CAP_SESSION_TTL_SECONDS")
    if configured is None:
        return DEFAULT_TTL_SECONDS
    try:
        return int(configured)
    except (TypeError, ValueError):
        return DEFAULT_TTL_SECONDS


def _cap_session_valid(ttl_seconds: int) -> bool:
    raw = session.get(CAP_SESSION_KEY)
    if raw is None:
        return False
    try:
        timestamp = float(raw)
    except (TypeError, ValueError):
        return False
    return (time.time() - timestamp) <= ttl_seconds


def mark_cap_verified() -> None:
    session[CAP_SESSION_KEY] = time.time()


def _cap_ui_config() -> Dict[str, str]:
    base_url = (current_app.config.get("CAP_BASE_URL") or os.getenv("CAP_BASE_URL", "/cap")).rstrip("/")
    asset_base_url = (
        current_app.config.get("CAP_ASSET_BASE_URL")
        or os.getenv("CAP_ASSET_BASE_URL", f"{base_url}/assets")
    ).rstrip("/")
    site_key = current_app.config.get("CAP_SITE_KEY") or os.getenv("CAP_SITE_KEY", "")

    if not base_url:
        raise CapVerificationError("CAP_BASE_URL is required for CAPTCHA gating.")
    if not site_key:
        raise CapVerificationError("CAP_SITE_KEY is required for CAPTCHA gating.")

    api_endpoint = f"{base_url}/{site_key}/"
    return {
        "cap_base_url": base_url,
        "cap_asset_base_url": asset_base_url,
        "cap_site_key": site_key,
        "cap_api_endpoint": api_endpoint,
    }


def _next_url() -> str:
    path = request.full_path or request.path or "/"
    if path.endswith("?"):
        path = path[:-1]
    script_root = (request.script_root or "").rstrip("/")
    if script_root:
        return f"{script_root}{path}"
    return path


def cap_gate_response(next_url: Optional[str] = None, reason: Optional[str] = None) -> Any:
    target_url = next_url or _next_url()
    config = _cap_ui_config()
    return render_template(
        "cap_gate.htm",
        cap_next=target_url,
        cap_reason=reason,
        cap_verify_url=url_for("weppcloud_site.cap_verify"),
        **config,
    )


def requires_cap(
    ttl_seconds: Optional[int] = None,
    gate_reason: Optional[str] = None,
) -> Callable[[Callable[..., ResponseValue]], Callable[..., ResponseValue | Any]]:
    """Decorator that enforces Cap.js verification for anonymous users."""

    def decorator(func: Callable[..., ResponseValue]) -> Callable[..., ResponseValue | Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> ResponseValue | Any:
            if current_user.is_authenticated:
                return func(*args, **kwargs)

            ttl = _cap_ttl_seconds(ttl_seconds)
            if _cap_session_valid(ttl):
                return func(*args, **kwargs)

            if request.method in ("GET", "HEAD"):
                try:
                    return cap_gate_response(reason=gate_reason)
                except CapVerificationError as exc:
                    current_app.logger.error("CAPTCHA gate config error: %s", exc)
                    return exception_factory("CAPTCHA configuration error.")

            response = error_factory("CAPTCHA verification required.")
            response.status_code = 403
            return response

        return wrapper

    return decorator
