from __future__ import annotations

"""Configuration helpers for the profile recorder stack."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol


class _ConfiguredApp(Protocol):
    """Protocol capturing the subset of Flask applications we rely on."""

    config: Mapping[str, Any]


@dataclass(frozen=True)
class RecorderConfig:
    """Immutable runtime configuration for profile recording and playback."""

    data_repo_root: Path
    assembler_enabled: bool


def resolve_recorder_config(app: _ConfiguredApp) -> RecorderConfig:
    """Build a :class:`RecorderConfig` from Flask application settings.

    Args:
        app: Flask (or Flask-like) application exposing the ``config`` mapping.

    Returns:
        The resolved configuration with defaults applied when settings are absent.
    """
    data_root = app.config.get("PROFILE_DATA_ROOT")
    if not data_root:
        data_root = "/workdir/wepppy-test-engine-data"
    assembler_enabled = app.config.get("PROFILE_RECORDER_ASSEMBLER_ENABLED", True)
    return RecorderConfig(Path(data_root), assembler_enabled)
