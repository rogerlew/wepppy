"""Shared access policy for the public project creation endpoint."""

import os


def allow_anonymous_project_creation() -> bool:
    """Read the opt-out flag, rejecting explicit empty or malformed settings."""
    name = "WEPPCLOUD_ALLOW_ANONYMOUS_PROJECT_CREATION"
    raw = os.getenv(name)
    if raw is None:
        return True
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean (true/false, 1/0, yes/no, on/off).")
