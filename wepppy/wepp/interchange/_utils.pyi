from __future__ import annotations

from pathlib import Path
from typing import Tuple

def _wait_for_path(path: Path | str, timeout: float = ..., poll: float = ...) -> None: ...

def _parse_float(token: str) -> float: ...

def _julian_to_calendar(year: int, julian: int) -> Tuple[int, int]: ...
