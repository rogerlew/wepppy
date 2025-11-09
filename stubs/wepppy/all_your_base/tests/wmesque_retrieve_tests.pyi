from __future__ import annotations

from pathlib import Path
from typing import Sequence

TEST_DIR: Path
DEFAULT_EXTENT: tuple[float, float, float, float]


def run_smoke(extent: Sequence[float] | None = ..., cellsize: float = ...) -> None: ...
