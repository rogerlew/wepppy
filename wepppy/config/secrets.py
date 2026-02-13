"""Secret resolution helpers.

This module centralizes the project's "secret as file" contract:
- Prefer `<NAME>_FILE` when set (read secret value from the referenced file).
- Fall back to `<NAME>` for transition/backwards compatibility.

Callers should treat returned values as sensitive and never log them.
"""

from __future__ import annotations

import os
from pathlib import Path


def get_secret(
    env_name: str,
    *,
    required: bool = False,
    file_env_name: str | None = None,
) -> str | None:
    """Resolve a secret from `<NAME>_FILE` or `<NAME>` (in that order).

    If the file env var is set, it is treated as authoritative. Fail fast when
    the file cannot be read or the secret is empty.
    """

    file_key = file_env_name or f"{env_name}_FILE"
    file_path = (os.getenv(file_key) or "").strip()
    if file_path:
        try:
            value = Path(file_path).read_text(encoding="utf-8").strip()
        except OSError as exc:  # pragma: no cover - exercised via integration/env
            raise RuntimeError(f"Unable to read {file_key} at '{file_path}': {exc}") from exc
        if not value:
            raise RuntimeError(f"{file_key} at '{file_path}' is empty")
        return value

    value = os.getenv(env_name)
    if value is not None:
        stripped = value.strip()
        if stripped:
            return stripped

    if required:
        raise RuntimeError(f"{env_name} (or {file_key}) must be configured")
    return None


def require_secret(env_name: str, *, file_env_name: str | None = None) -> str:
    """Return a configured secret value or raise."""

    value = get_secret(env_name, required=True, file_env_name=file_env_name)
    assert value is not None  # narrow type for callers
    return value

