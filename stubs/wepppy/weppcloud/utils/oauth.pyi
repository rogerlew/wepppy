from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, Optional, Tuple

from authlib.integrations.flask_client import OAuth
from flask import Flask


def ensure_oauth_client(
    provider: str,
    provider_settings: Dict[str, Any],
    *,
    app: Optional[Flask] = ...,
) -> Any: ...


def build_pkce_pair() -> Tuple[str, str]: ...


def utc_now() -> datetime: ...


def normalize_token_scopes(
    token: Optional[Dict[str, Any]],
    provider_settings: Optional[Dict[str, Any]] = ...,
) -> str: ...


def provider_enabled(provider_settings: Optional[Dict[str, Any]]) -> bool: ...
