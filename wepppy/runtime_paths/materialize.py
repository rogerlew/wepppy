"""Directory-only materialization helpers."""

from __future__ import annotations

import os
from pathlib import Path

from .paths import normalize_relpath

__all__ = [
    "materialize_file",
    "materialize_path_if_archive",
]


def materialize_file(wd: str, rel: str, *, purpose: str = "browse") -> str:
    _ = purpose
    wd_path = Path(os.path.abspath(wd))
    rel_norm = normalize_relpath(rel)
    abs_path = wd_path / rel_norm

    if not abs_path.exists():
        raise FileNotFoundError(rel_norm)
    if abs_path.is_dir():
        raise IsADirectoryError(abs_path)

    return str(abs_path)


def materialize_path_if_archive(wd: str, path: str | Path, *, purpose: str = "export") -> str:
    _ = purpose
    base = Path(os.path.abspath(wd))
    candidate = Path(path)
    if candidate.is_absolute():
        return str(candidate)
    return str(base / candidate)
