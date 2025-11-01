from __future__ import annotations

import re

_SAFE_COMPONENT_RE = re.compile(r"[^A-Za-z0-9._-]+")


def sanitise_component(value: str) -> str:
    """Normalise arbitrary identifiers so they are safe for filesystem paths."""

    if not value:
        return "default"
    safe = _SAFE_COMPONENT_RE.sub("-", value)
    safe = safe.strip("-._")
    return safe or "default"
