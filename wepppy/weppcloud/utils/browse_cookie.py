"""Helpers for browse JWT cookie naming and path scoping."""

from __future__ import annotations

import hashlib


def _normalize_site_prefix(prefix: str) -> str:
    trimmed = str(prefix or "").strip()
    if not trimmed or trimmed == "/":
        return ""
    return "/" + trimmed.strip("/")


def browse_cookie_name(base_name: str, runid: str, config: str) -> str:
    """Return the cookie key for a run/config browse session token."""
    normalized_base = str(base_name or "").strip()
    if ";" not in str(runid):
        return normalized_base

    digest_input = f"{runid}\n{config}".encode("utf-8")
    digest = hashlib.sha256(digest_input).hexdigest()[:16]
    return f"{normalized_base}_{digest}"


def browse_cookie_name_candidates(base_name: str, runid: str, config: str) -> list[str]:
    """Return cookie keys to try, ordered from most specific to legacy."""
    scoped_name = browse_cookie_name(base_name, runid, config)
    if scoped_name == base_name:
        return [base_name]
    return [scoped_name, base_name]


def browse_cookie_path(site_prefix: str, runid: str, config: str) -> str:
    """Return a cookie path safe for browsers that reject semicolons."""
    prefix = _normalize_site_prefix(site_prefix)
    if ";" in str(runid):
        return f"{prefix}/runs/"
    return f"{prefix}/runs/{runid}/{config}/"


__all__ = [
    "browse_cookie_name",
    "browse_cookie_name_candidates",
    "browse_cookie_path",
]
