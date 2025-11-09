from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

from flask import Flask

from .config import RecorderConfig

LOGGER: logging.Logger
EventPayload = Dict[str, Any]
FileHintMap = Dict[str, Path]
KNOWN_FILE_KEYS: Iterable[str]


class ProfileRecorder:
    config: RecorderConfig

    def __init__(self, *, config: RecorderConfig) -> None: ...
    def append_event(
        self,
        event: Dict[str, Any],
        *,
        user: Any | None = ...,
        assembler_override: Optional[bool] = ...,
    ) -> None: ...


def get_profile_recorder(app: Flask) -> ProfileRecorder: ...
