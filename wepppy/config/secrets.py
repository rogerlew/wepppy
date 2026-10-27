"""Secret resolution helpers.

This module centralizes the project's "secret as file" contract:
- Prefer `<NAME>_FILE` when set (read secret value from the referenced file).
- Fall back to `<NAME>` for transition/backwards compatibility.

Callers should treat returned values as sensitive and never log them.
"""

from __future__ import annotations

import os
from pathlib import Path


class SecretConfigurationError(RuntimeError):
    """Configuration failure with a public description that excludes file paths."""

    def __init__(self, message: str, setting: str, reason: str) -> None:
        super().__init__(message)
        self.setting = setting
        self.reason = reason
        self.public_message = (
            f"Server configuration error: {setting} {reason}. "
            "The service operator must correct this configuration before retrying."
        )

    def __reduce__(self):
        # Process pools transport exceptions through pickle; RuntimeError's
        # default reducer supplies only message and would lose required metadata.
        return type(self), (self.args[0], self.setting, self.reason), self.__dict__


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
    value: str | None
    file_path = (os.getenv(file_key) or "").strip()
    if file_path:
        try:
            value = Path(file_path).read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError) as exc:
            raise SecretConfigurationError(
                f"Unable to read {file_key} at '{file_path}': {exc}",
                setting=file_key, reason="could not be read",
            ) from exc
        if not value:
            raise SecretConfigurationError(
                f"{file_key} at '{file_path}' is empty",
                setting=file_key, reason="is empty",
            )
        return value

    value = os.getenv(env_name)
    if value is not None:
        stripped = value.strip()
        if stripped:
            return stripped

    if required:
        raise SecretConfigurationError(
            f"{env_name} (or {file_key}) must be configured",
            setting=f"{env_name} (or {file_key})", reason="is not configured",
        )
    return None


def require_secret(env_name: str, *, file_env_name: str | None = None) -> str:
    """Return a configured secret value or raise."""

    value = get_secret(env_name, required=True, file_env_name=file_env_name)
    assert value is not None  # narrow type for callers
    return value

