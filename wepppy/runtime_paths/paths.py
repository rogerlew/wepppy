"""Path normalization helpers for directory-only runtime roots."""

from __future__ import annotations

import re
from typing import Literal

__all__ = [
    "NoDirRoot",
    "NoDirView",
    "NODIR_ROOTS",
    "normalize_relpath",
    "parse_external_subpath",
    "split_nodir_root",
]

NoDirRoot = Literal["landuse", "soils", "climate", "watershed"]
NoDirView = Literal["effective", "dir", "archive"]

NODIR_ROOTS: tuple[NoDirRoot, ...] = ("landuse", "soils", "climate", "watershed")

_WIN_DRIVE_RE = re.compile(r"^[A-Za-z]:")


def normalize_relpath(raw: str) -> str:
    if raw is None:
        raise ValueError("relpath is None")

    rel = raw.replace("\\", "/")
    if "\x00" in rel:
        raise ValueError("relpath contains null byte")

    rel = rel.lstrip("/")

    parts: list[str] = []
    for part in rel.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            raise ValueError("path traversal is not allowed")
        parts.append(part)

    if not parts:
        return "."
    if _WIN_DRIVE_RE.match(parts[0]):
        raise ValueError("absolute Windows paths are not allowed")
    return "/".join(parts)


def parse_external_subpath(rel: str, *, allow_admin_alias: bool) -> tuple[str, NoDirView]:
    """Parse external browse/download path syntax.

    Archive boundary aliases (``<root>.nodir/...`` and ``<root>/nodir/...``)
    are intentionally retired in directory-only mode.
    """

    if rel is None:
        raise ValueError("subpath is None")

    raw = rel.replace("\\", "/")
    norm = normalize_relpath(raw)
    if norm in ("", "."):
        return ".", "effective"

    parts = norm.split("/")
    first = parts[0]

    if first.endswith(".nodir"):
        root = first[: -len(".nodir")]
        if root in NODIR_ROOTS:
            raise ValueError("archive boundary paths are retired")

    if allow_admin_alias and len(parts) >= 2 and parts[1] == "nodir" and parts[0] in NODIR_ROOTS:
        raise ValueError("archive boundary paths are retired")

    return norm, "effective"


def split_nodir_root(rel: str) -> tuple[NoDirRoot | None, str]:
    rel_norm = normalize_relpath(rel)
    if rel_norm in ("", "."):
        return None, ""

    head, _, tail = rel_norm.partition("/")
    if head not in NODIR_ROOTS:
        return None, ""
    return head, tail
