from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence

__all__ = [
    "CURRENT_VERSION",
    "VERSION_FILENAME",
    "Migration",
    "ensure_version",
    "read_version",
    "write_version",
    "copy_version_for_clone",
]

CURRENT_VERSION: int
VERSION_FILENAME: str


@dataclass(frozen=True)
class Migration:
    target_version: int
    func: Callable[[Path], None]
    description: str | None = ...


def ensure_version(
    wd: str | Path,
    *,
    target_version: int = ...,
    migrations: Iterable[Migration] | None = ...,
) -> int: ...


def read_version(wd: str | Path) -> int: ...


def write_version(wd: str | Path, version: int) -> None: ...


def copy_version_for_clone(base_wd: str | Path, new_wd: str | Path) -> None: ...
