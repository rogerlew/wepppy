"""Directory-only filesystem helpers for runtime path access."""

from __future__ import annotations

import os
import stat as statmod
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Literal

from .errors import NoDirError
from .parquet_sidecars import require_directory_parquet_path
from .paths import NoDirRoot, NoDirView, normalize_relpath, split_nodir_root

__all__ = [
    "NoDirForm",
    "ResolvedNoDirPath",
    "NoDirDirEntry",
    "resolve",
    "listdir",
    "stat",
    "open_read",
]

NoDirForm = Literal["dir", "archive"]


@dataclass(frozen=True, slots=True)
class ResolvedNoDirPath:
    wd: str
    root: NoDirRoot
    inner_path: str
    form: NoDirForm
    dir_path: str
    archive_path: str
    archive_fp: tuple[int, int] | None


@dataclass(frozen=True, slots=True)
class NoDirDirEntry:
    name: str
    is_dir: bool
    size_bytes: int | None
    mtime_ns: int | None


def _as_target_path(target: ResolvedNoDirPath) -> Path:
    base = Path(target.dir_path)
    if target.inner_path:
        return base / target.inner_path
    return base


def _logical_relpath(target: ResolvedNoDirPath) -> str:
    if target.inner_path:
        return f"{target.root}/{target.inner_path}"
    return target.root


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _resolve_contained_path(target: ResolvedNoDirPath, path: Path, *, logical_rel: str) -> Path:
    if not path.exists():
        raise FileNotFoundError(logical_rel)

    try:
        wd_real = Path(target.wd).resolve(strict=True)
        root_real = Path(target.dir_path).resolve(strict=True)
        target_real = path.resolve(strict=True)
    except (FileNotFoundError, OSError, RuntimeError):
        raise FileNotFoundError(logical_rel)

    if not _is_relative_to(root_real, wd_real):
        raise FileNotFoundError(logical_rel)
    if not _is_relative_to(target_real, root_real):
        raise FileNotFoundError(logical_rel)
    return target_real


def _entry_for_path(path: Path, *, name: str | None = None) -> NoDirDirEntry:
    st = path.stat()
    is_dir = path.is_dir()
    mtime_ns = getattr(st, "st_mtime_ns", None)
    if mtime_ns is None:
        mtime_ns = int(st.st_mtime * 1_000_000_000)
    entry_name = name if name is not None else path.name
    return NoDirDirEntry(
        name=entry_name,
        is_dir=is_dir,
        size_bytes=None if is_dir else int(st.st_size),
        mtime_ns=int(mtime_ns),
    )


def resolve(wd: str, rel: str, *, view: NoDirView = "effective") -> ResolvedNoDirPath | None:
    rel_norm = normalize_relpath(rel)
    root, inner = split_nodir_root(rel_norm)
    if root is None:
        return None

    wd_path = Path(os.path.abspath(wd))
    dir_path = wd_path / root
    archive_path = wd_path / f"{root}.nodir"

    if view == "archive":
        return None

    if archive_path.exists() and not dir_path.exists():
        raise NoDirError(
            http_status=409,
            code="NODIR_ARCHIVE_RETIRED",
            message=f"{root}.nodir exists but archive-backed runtime access is retired",
        )

    if view == "dir" and not dir_path.exists():
        return None

    return ResolvedNoDirPath(
        wd=str(wd_path),
        root=root,
        inner_path=inner,
        form="dir",
        dir_path=str(dir_path),
        archive_path=str(archive_path),
        archive_fp=None,
    )


def listdir(target: ResolvedNoDirPath) -> list[NoDirDirEntry]:
    if target.form != "dir":
        raise FileNotFoundError(target.inner_path or target.root)

    path = _as_target_path(target)
    logical_rel = _logical_relpath(target)
    path = _resolve_contained_path(target, path, logical_rel=logical_rel)
    if not path.is_dir():
        raise NotADirectoryError(path)

    entries: list[NoDirDirEntry] = []
    with os.scandir(path) as listing:
        for item in listing:
            item_path = Path(item.path)
            st = item_path.stat(follow_symlinks=False)
            is_dir = statmod.S_ISDIR(st.st_mode)
            mtime_ns = getattr(st, "st_mtime_ns", None)
            if mtime_ns is None:
                mtime_ns = int(st.st_mtime * 1_000_000_000)
            entries.append(
                NoDirDirEntry(
                    name=item.name,
                    is_dir=is_dir,
                    size_bytes=None if is_dir else int(st.st_size),
                    mtime_ns=int(mtime_ns),
                )
            )

    entries.sort(key=lambda entry: (0 if entry.is_dir else 1, entry.name.lower(), entry.name))
    return entries


def stat(target: ResolvedNoDirPath) -> NoDirDirEntry:
    wd_path = Path(target.wd)
    logical_rel = _logical_relpath(target)

    if logical_rel.endswith(".parquet"):
        try:
            parquet_path = require_directory_parquet_path(wd_path, logical_rel)
        except FileNotFoundError:
            parquet_path = None
        if parquet_path is not None:
            safe_parquet_path = _resolve_contained_path(target, parquet_path, logical_rel=logical_rel)
            return _entry_for_path(safe_parquet_path, name=Path(logical_rel).name)

    path = _as_target_path(target)
    safe_path = _resolve_contained_path(target, path, logical_rel=logical_rel)
    return _entry_for_path(safe_path, name=Path(logical_rel).name)


def open_read(target: ResolvedNoDirPath) -> BinaryIO:
    wd_path = Path(target.wd)
    logical_rel = _logical_relpath(target)

    if logical_rel.endswith(".parquet"):
        try:
            parquet_path = require_directory_parquet_path(wd_path, logical_rel)
        except FileNotFoundError:
            parquet_path = None
        if parquet_path is not None:
            safe_parquet_path = _resolve_contained_path(target, parquet_path, logical_rel=logical_rel)
            return safe_parquet_path.open("rb")

    path = _as_target_path(target)
    safe_path = _resolve_contained_path(target, path, logical_rel=logical_rel)
    if safe_path.is_dir():
        raise IsADirectoryError(safe_path)
    return safe_path.open("rb")
