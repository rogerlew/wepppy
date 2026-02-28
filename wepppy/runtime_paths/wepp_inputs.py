"""Directory-only WEPP input helpers."""

from __future__ import annotations

import fnmatch
import io
import os
import shutil
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO, Iterator, TextIO

from .paths import normalize_relpath

__all__ = [
    "open_input_binary",
    "open_input_text",
    "copy_input_file",
    "list_input_files",
    "glob_input_files",
    "input_exists",
    "with_input_file_path",
    "materialize_input_file",
]


def _normalize_wd_and_rel(wd: str, rel: str) -> tuple[Path, str]:
    wd_path = Path(os.path.abspath(wd))
    rel_norm = normalize_relpath(rel)
    return wd_path, rel_norm


def materialize_input_file(wd: str, rel: str, *, purpose: str = "wepp-input") -> str:
    _ = purpose
    wd_path, rel_norm = _normalize_wd_and_rel(wd, rel)
    abs_path = wd_path / rel_norm
    if not abs_path.exists():
        raise FileNotFoundError(rel_norm)
    if abs_path.is_dir():
        raise IsADirectoryError(abs_path)
    return str(abs_path)


def open_input_binary(
    wd: str,
    rel: str,
    *,
    tolerate_mixed: bool = False,
    mixed_prefer: str = "archive",
) -> BinaryIO:
    _ = (tolerate_mixed, mixed_prefer)
    abs_path = Path(materialize_input_file(wd, rel))
    return abs_path.open("rb")


def open_input_text(
    wd: str,
    rel: str,
    *,
    encoding: str = "utf-8",
    errors: str = "strict",
    tolerate_mixed: bool = False,
    mixed_prefer: str = "archive",
) -> TextIO:
    raw = open_input_binary(
        wd,
        rel,
        tolerate_mixed=tolerate_mixed,
        mixed_prefer=mixed_prefer,
    )
    return io.TextIOWrapper(raw, encoding=encoding, errors=errors)


def copy_input_file(
    wd: str,
    src_rel: str,
    dst_path: str | os.PathLike[str],
    *,
    prefer_hardlink: bool = True,
) -> str:
    src = Path(materialize_input_file(wd, src_rel))
    dst = Path(dst_path)
    dst.parent.mkdir(parents=True, exist_ok=True)

    if dst.exists():
        dst.unlink()

    if prefer_hardlink:
        try:
            os.link(src, dst)
            return str(dst)
        except OSError:
            pass

    shutil.copyfile(src, dst)
    return str(dst)


def list_input_files(
    wd: str,
    dir_rel: str,
    *,
    tolerate_mixed: bool = False,
    mixed_prefer: str = "archive",
) -> list[str]:
    _ = (tolerate_mixed, mixed_prefer)
    wd_path, dir_rel_norm = _normalize_wd_and_rel(wd, dir_rel)
    abs_dir = wd_path / dir_rel_norm
    if not abs_dir.exists():
        raise FileNotFoundError(dir_rel_norm)
    if not abs_dir.is_dir():
        raise NotADirectoryError(abs_dir)

    names = [entry.name for entry in abs_dir.iterdir() if entry.is_file()]
    names.sort(key=lambda value: (value.lower(), value))
    return names


def glob_input_files(
    wd: str,
    pattern: str,
    *,
    tolerate_mixed: bool = False,
    mixed_prefer: str = "archive",
) -> list[str]:
    _ = (tolerate_mixed, mixed_prefer)
    _, pattern_rel_norm = _normalize_wd_and_rel(wd, pattern)
    parent_rel, basename_pattern = pattern_rel_norm.rsplit("/", 1)

    if any(token in parent_rel for token in ("*", "?", "[", "]")):
        raise ValueError("glob_input_files only supports wildcards in the final segment")

    if not any(token in basename_pattern for token in ("*", "?", "[", "]")):
        if input_exists(wd, pattern_rel_norm):
            return [pattern_rel_norm]
        return []

    matches = [
        f"{parent_rel}/{name}" if parent_rel else name
        for name in list_input_files(wd, parent_rel)
        if fnmatch.fnmatch(name, basename_pattern)
    ]
    matches.sort(key=lambda value: (value.lower(), value))
    return matches


def input_exists(
    wd: str,
    rel: str,
    *,
    tolerate_mixed: bool = False,
    mixed_prefer: str = "archive",
) -> bool:
    _ = (tolerate_mixed, mixed_prefer)
    wd_path, rel_norm = _normalize_wd_and_rel(wd, rel)
    return (wd_path / rel_norm).is_file()


@contextmanager
def with_input_file_path(
    wd: str,
    rel: str,
    *,
    purpose: str = "wepp-input",
    tolerate_mixed: bool = False,
    mixed_prefer: str = "archive",
    allow_materialize_fallback: bool = False,
    use_projection: bool = False,
) -> Iterator[str]:
    _ = (tolerate_mixed, mixed_prefer, allow_materialize_fallback, use_projection)
    yield materialize_input_file(wd, rel, purpose=purpose)
