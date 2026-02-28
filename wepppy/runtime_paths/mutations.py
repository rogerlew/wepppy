"""Directory-only mutation helpers with maintenance locking."""

from __future__ import annotations

import os
from contextlib import ExitStack
from pathlib import Path
from typing import Callable, Iterable, TypeVar

from .errors import NoDirError
from .paths import NODIR_ROOTS
from .thaw_freeze import maintenance_lock

__all__ = [
    "preflight_root_forms",
    "mutate_root",
    "mutate_roots",
]

T = TypeVar("T")


def _normalize_root(root: str) -> str:
    if root not in NODIR_ROOTS:
        raise ValueError(f"unsupported root: {root}")
    return root


def preflight_root_forms(wd: str, roots: Iterable[str]) -> dict[str, str]:
    wd_path = Path(os.path.abspath(wd))
    forms: dict[str, str] = {}
    for root_raw in roots:
        root = _normalize_root(root_raw)
        dir_path = wd_path / root
        archive_path = wd_path / f"{root}.nodir"
        if dir_path.exists():
            forms[root] = "dir"
        elif archive_path.exists():
            forms[root] = "archive"
        else:
            forms[root] = "missing"
    return forms


def _assert_directory_root(wd_path: Path, root: str) -> None:
    dir_path = wd_path / root
    archive_path = wd_path / f"{root}.nodir"
    if archive_path.exists() and not dir_path.exists():
        raise NoDirError(
            http_status=409,
            code="NODIR_ARCHIVE_RETIRED",
            message=f"{root}.nodir exists but archive-backed mutations are retired",
        )


def mutate_root(
    wd: str,
    root: str,
    callback: Callable[[], T],
    *,
    purpose: str = "runtime-path-mutate",
) -> T:
    normalized_root = _normalize_root(root)
    wd_path = Path(os.path.abspath(wd))
    _assert_directory_root(wd_path, normalized_root)
    with maintenance_lock(str(wd_path), normalized_root, purpose=purpose):
        _assert_directory_root(wd_path, normalized_root)
        return callback()


def mutate_roots(
    wd: str,
    roots: Iterable[str],
    callback: Callable[[], T],
    *,
    purpose: str = "runtime-path-mutate",
) -> T:
    normalized_roots = tuple(sorted({_normalize_root(root) for root in roots}))
    wd_path = Path(os.path.abspath(wd))

    for root in normalized_roots:
        _assert_directory_root(wd_path, root)

    with ExitStack() as stack:
        for root in normalized_roots:
            stack.enter_context(maintenance_lock(str(wd_path), root, purpose=f"{purpose}/{root}"))
        for root in normalized_roots:
            _assert_directory_root(wd_path, root)
        return callback()
