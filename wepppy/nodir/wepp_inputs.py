"""Narrow WEPP prep helpers for archive-first NoDir input reads.

This module intentionally covers only the read patterns used by WEPP prep:
- open text/binary inputs by logical run-relative path,
- copy a single source entry to an output file,
- list/glob files in a known logical directory,
- materialize a single file when a downstream consumer requires a real path.
"""

from __future__ import annotations

import fnmatch
import io
import os
import shutil
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO, Iterator, TextIO

from .errors import NoDirError
from .fs import listdir, open_read, resolve, stat
from .paths import normalize_relpath
from .projections import with_root_projection

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


def _resolve_effective(wd_path: Path, rel_norm: str):
    return resolve(str(wd_path), rel_norm, view="effective")


def _resolve_for_read(
    wd_path: Path,
    rel_norm: str,
    *,
    tolerate_mixed: bool,
    mixed_prefer: str,
):
    if not tolerate_mixed:
        return _resolve_effective(wd_path, rel_norm)

    try:
        return _resolve_effective(wd_path, rel_norm)
    except NoDirError as exc:
        if exc.code != "NODIR_MIXED_STATE":
            raise

        if mixed_prefer not in {"archive", "dir"}:
            raise ValueError("mixed_prefer must be one of: archive, dir")

        preferred = resolve(str(wd_path), rel_norm, view=mixed_prefer)
        if preferred is not None:
            return preferred

        fallback_view = "dir" if mixed_prefer == "archive" else "archive"
        return resolve(str(wd_path), rel_norm, view=fallback_view)


def _as_relpath(parent_rel: str, name: str) -> str:
    if parent_rel:
        return f"{parent_rel}/{name}"
    return name


def open_input_binary(
    wd: str,
    rel: str,
    *,
    tolerate_mixed: bool = False,
    mixed_prefer: str = "archive",
) -> BinaryIO:
    """Open a logical WEPP input path for binary reads.

    For NoDir roots this defers to archive-aware `resolve(..., view="effective")`
    and `open_read(...)`; for non-NoDir paths this opens directly from WD.
    """

    wd_path, rel_norm = _normalize_wd_and_rel(wd, rel)
    target = _resolve_for_read(
        wd_path,
        rel_norm,
        tolerate_mixed=tolerate_mixed,
        mixed_prefer=mixed_prefer,
    )
    if target is None:
        return (wd_path / rel_norm).open("rb")
    return open_read(target)


def open_input_text(
    wd: str,
    rel: str,
    *,
    encoding: str = "utf-8",
    errors: str = "strict",
    tolerate_mixed: bool = False,
    mixed_prefer: str = "archive",
) -> TextIO:
    """Open a logical WEPP input path for text reads."""

    raw = open_input_binary(
        wd,
        rel,
        tolerate_mixed=tolerate_mixed,
        mixed_prefer=mixed_prefer,
    )
    return io.TextIOWrapper(raw, encoding=encoding, errors=errors)


def _try_hardlink(src: Path, dst: Path) -> bool:
    try:
        if dst.exists():
            dst.unlink()
    except OSError:
        return False

    try:
        os.link(src, dst)
    except OSError:
        return False
    return True


def copy_input_file(
    wd: str,
    src_rel: str,
    dst_path: str | os.PathLike[str],
    *,
    prefer_hardlink: bool = True,
) -> str:
    """Copy one logical input file to a destination path.

    Archive-backed entries stream through `open_input_binary`. Directory-form NoDir
    sources may use hard links when requested.
    """

    wd_path, src_rel_norm = _normalize_wd_and_rel(wd, src_rel)
    dst = Path(dst_path)
    dst.parent.mkdir(parents=True, exist_ok=True)

    target = _resolve_effective(wd_path, src_rel_norm)

    if prefer_hardlink and target is not None and target.form == "dir":
        src_path = Path(target.dir_path)
        if target.inner_path:
            src_path = src_path / target.inner_path
        if _try_hardlink(src_path, dst):
            return str(dst)

    if prefer_hardlink and target is None:
        src_path = wd_path / src_rel_norm
        if _try_hardlink(src_path, dst):
            return str(dst)

    if dst.exists():
        dst.unlink()

    with open_input_binary(str(wd_path), src_rel_norm) as src_fp, dst.open("wb") as dst_fp:
        shutil.copyfileobj(src_fp, dst_fp)

    return str(dst)


def list_input_files(wd: str, dir_rel: str) -> list[str]:
    """List immediate file names under a logical directory."""

    wd_path, dir_rel_norm = _normalize_wd_and_rel(wd, dir_rel)
    target = _resolve_effective(wd_path, dir_rel_norm)

    names: list[str] = []
    if target is None:
        abs_dir = wd_path / dir_rel_norm
        with os.scandir(abs_dir) as entries:
            for entry in entries:
                if entry.is_file():
                    names.append(entry.name)
        names.sort(key=lambda value: (value.lower(), value))
        return names

    for entry in listdir(target):
        if not entry.is_dir:
            names.append(entry.name)

    names.sort(key=lambda value: (value.lower(), value))
    return names


def glob_input_files(wd: str, pattern: str) -> list[str]:
    """Glob logical input files with wildcards only in the final segment.

    This intentionally supports only the WEPP prep usage pattern where the parent
    directory is concrete and the file segment contains the wildcard.
    """

    _, pattern_rel_norm = _normalize_wd_and_rel(wd, pattern)
    parent_rel, basename_pattern = pattern_rel_norm.rsplit("/", 1)

    if any(token in parent_rel for token in ("*", "?", "[", "]")):
        raise ValueError("glob_input_files only supports wildcards in the final segment")

    if not any(token in basename_pattern for token in ("*", "?", "[", "]")):
        if input_exists(wd, pattern_rel_norm):
            return [pattern_rel_norm]
        return []

    matches = [
        _as_relpath(parent_rel, name)
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
    """Return True when a logical input path exists in directory or archive form."""

    wd_path, rel_norm = _normalize_wd_and_rel(wd, rel)
    target = _resolve_for_read(
        wd_path,
        rel_norm,
        tolerate_mixed=tolerate_mixed,
        mixed_prefer=mixed_prefer,
    )

    if target is None:
        return (wd_path / rel_norm).exists()

    try:
        stat(target)
    except FileNotFoundError:
        return False
    return True



@contextmanager
def with_input_file_path(
    wd: str,
    rel: str,
    *,
    purpose: str = "wepp-input-path",
    tolerate_mixed: bool = False,
    mixed_prefer: str = "archive",
    use_projection: bool = True,
    allow_materialize_fallback: bool = False,
) -> Iterator[str]:
    """Yield a filesystem path for one logical input path.

    Projection-first behavior is used for archive-form NoDir entries.
    `materialize_input_file(...)` remains an explicit compatibility fallback and
    is only used when `allow_materialize_fallback=True`.
    """

    wd_path, rel_norm = _normalize_wd_and_rel(wd, rel)
    target = _resolve_for_read(
        wd_path,
        rel_norm,
        tolerate_mixed=tolerate_mixed,
        mixed_prefer=mixed_prefer,
    )

    if target is None:
        yield str(wd_path / rel_norm)
        return

    if target.form == "dir":
        src_path = Path(target.dir_path)
        if target.inner_path:
            src_path = src_path / target.inner_path
        yield str(src_path)
        return

    if not use_projection:
        if not allow_materialize_fallback:
            raise ValueError("archive-form input paths require projection or explicit materialize fallback")
        yield materialize_input_file(str(wd_path), rel_norm, purpose=purpose)
        return

    try:
        with with_root_projection(
            wd_path,
            target.root,
            mode="read",
            purpose=purpose,
        ) as handle:
            projected_path = Path(handle.mount_path)
            if target.inner_path:
                projected_path = projected_path / target.inner_path
            yield str(projected_path)
            return
    except NoDirError:
        if not allow_materialize_fallback:
            raise

    yield materialize_input_file(str(wd_path), rel_norm, purpose=purpose)


def materialize_input_file(wd: str, rel: str, *, purpose: str = "wepp-input") -> str:
    """Materialize one logical input file for path-only consumers."""

    from .materialize import materialize_file

    wd_path, rel_norm = _normalize_wd_and_rel(wd, rel)
    return materialize_file(str(wd_path), rel_norm, purpose=purpose)
