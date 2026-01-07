from __future__ import annotations

from pathlib import Path
from typing import Iterable

__all__ = ["RUN_SKELETON_ALLOWLIST", "RUN_SKELETON_DENYLIST", "skeletonize_run"]

RUN_SKELETON_ALLOWLIST: tuple[str, ...]
RUN_SKELETON_DENYLIST: tuple[str, ...]

def skeletonize_run(
    run_wd: str | Path,
    allowlist: Iterable[str] = RUN_SKELETON_ALLOWLIST,
    denylist: Iterable[str] = RUN_SKELETON_DENYLIST,
) -> None: ...
