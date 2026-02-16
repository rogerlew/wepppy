"""NoDir path normalization and archive-boundary parsing."""

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
    """Normalize a user-supplied relpath.

    - Convert `\\` to `/`.
    - Strip leading `/`.
    - Reject `\\x00`, Windows drive-letter absolute paths, and any `..` segment.
    - Return `"."` for empty.
    """
    if raw is None:
        raise ValueError("relpath is None")

    rel = raw.replace("\\", "/")
    if "\x00" in rel:
        raise ValueError("relpath contains null byte")

    # Treat leading slashes as URL noise; callers always interpret the result as WD-relative.
    rel = rel.lstrip("/")

    # Normalize repeated separators and reject traversal.
    parts: list[str] = []
    for part in rel.split("/"):
        if part == "" or part == ".":
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
    """Parse browse/files/download-style paths into logical relpath + view.

    This recognizes the archive-boundary syntax only for allowlisted NoDir roots:
    - `<root>.nodir/<inner>` -> (`<root>/<inner>`, view="archive")
    - `<root>/nodir/<inner>` -> (`<root>/<inner>`, view="archive") when `allow_admin_alias=True`
    """
    if rel is None:
        raise ValueError("subpath is None")

    # Preserve whether a trailing slash was present so `root.nodir/` is treated as
    # "enter archive", while `root.nodir` can remain a normal file path for raw download.
    raw = rel.replace("\\", "/")
    had_boundary_slash = raw.endswith("/")

    norm = normalize_relpath(raw)
    if norm in (".", ""):
        return ".", "effective"

    parts = norm.split("/")
    first = parts[0]

    # Allowlisted archive-boundary syntax: `<root>.nodir/<inner>`
    if first.endswith(".nodir") and (len(parts) > 1 or had_boundary_slash):
        root = first[: -len(".nodir")]
        if root in NODIR_ROOTS:
            inner = "/".join(parts[1:]).strip("/")
            logical = root if not inner else f"{root}/{inner}"
            return logical, "archive"

    # Admin browse alias: `<root>/nodir/<inner>`
    if allow_admin_alias and len(parts) >= 2 and parts[1] == "nodir" and parts[0] in NODIR_ROOTS:
        root = parts[0]
        inner = "/".join(parts[2:]).strip("/")
        logical = root if not inner else f"{root}/{inner}"
        return logical, "archive"

    return norm, "effective"


def split_nodir_root(rel: str) -> tuple[NoDirRoot | None, str]:
    """Split a normalized logical relpath into (root, inner_path).

    `inner_path` is `""` when `rel` names the root itself.
    """
    rel = normalize_relpath(rel)
    if rel in (".", ""):
        return None, ""

    head, _, tail = rel.partition("/")
    if head not in NODIR_ROOTS:
        return None, ""
    return head, tail
