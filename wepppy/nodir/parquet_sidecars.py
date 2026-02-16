"""Deterministic mapping for WD-level parquet sidecars.

Contract summary (see docs/schemas/nodir-contract-spec.md):
- Logical paths remain under the NoDir roots (e.g., landuse/landuse.parquet).
- Physical storage for those parquets is canonical at WD-level sidecars
  (e.g., WD/landuse.parquet).
- When reading, callers should prefer sidecar and (optionally) fall back to the
  legacy in-tree parquet path for directory-form runs.
"""

from __future__ import annotations

import re
import stat as statmod
from pathlib import Path

from .paths import NODIR_ROOTS, normalize_relpath
from .symlinks import _derive_allowed_symlink_roots, _is_within_any_root, _resolve_path_safely

__all__ = [
    "logical_parquet_to_sidecar_relpath",
    "sidecar_relpath_to_logical_parquet",
    "pick_existing_parquet_relpath",
    "pick_existing_parquet_path",
]


_CLIMATE_LOGICAL_RE = re.compile(r"^climate/([^/]+)\.parquet$")
_WATERSHED_LOGICAL_RE = re.compile(r"^watershed/([^/]+)\.parquet$")

_CLIMATE_SIDECAR_RE = re.compile(r"^climate\.([^/]+)\.parquet$")
_WATERSHED_SIDECAR_RE = re.compile(r"^watershed\.([^/]+)\.parquet$")


def logical_parquet_to_sidecar_relpath(logical_relpath: str) -> str | None:
    """Return the WD-level sidecar relpath for a logical parquet path.

    Examples:
    - landuse/landuse.parquet -> landuse.parquet
    - climate/wepp_cli.parquet -> climate.wepp_cli.parquet
    """
    logical_relpath = logical_relpath.strip().lstrip("/")
    if logical_relpath == "landuse/landuse.parquet":
        return "landuse.parquet"
    if logical_relpath == "soils/soils.parquet":
        return "soils.parquet"
    match = _CLIMATE_LOGICAL_RE.match(logical_relpath)
    if match:
        name = match.group(1)
        return f"climate.{name}.parquet"
    match = _WATERSHED_LOGICAL_RE.match(logical_relpath)
    if match:
        name = match.group(1)
        return f"watershed.{name}.parquet"
    return None


def sidecar_relpath_to_logical_parquet(sidecar_relpath: str) -> str | None:
    """Return the logical parquet path for a WD-level sidecar relpath."""
    sidecar_relpath = sidecar_relpath.strip().lstrip("/")
    if sidecar_relpath == "landuse.parquet":
        return "landuse/landuse.parquet"
    if sidecar_relpath == "soils.parquet":
        return "soils/soils.parquet"
    match = _CLIMATE_SIDECAR_RE.match(sidecar_relpath)
    if match:
        return f"climate/{match.group(1)}.parquet"
    match = _WATERSHED_SIDECAR_RE.match(sidecar_relpath)
    if match:
        return f"watershed/{match.group(1)}.parquet"
    return None


def pick_existing_parquet_relpath(wd: str | Path, logical_relpath: str) -> str | None:
    """Choose the on-disk parquet relpath for a logical parquet id.

    Preference order:
    1) WD-level sidecar (if mapped and present)
    2) Legacy in-tree parquet (if present)
    """
    base = Path(wd)
    try:
        logical_relpath = normalize_relpath(logical_relpath)
    except ValueError:
        return None
    if logical_relpath in ("", "."):
        return None
    if logical_relpath.split("/", 1)[0] not in NODIR_ROOTS:
        return None

    allowed_roots = _derive_allowed_symlink_roots(base)

    def _is_regular_file_or_allowed_symlink(candidate: Path) -> bool:
        try:
            st = candidate.stat(follow_symlinks=False)
        except FileNotFoundError:
            return False
        if statmod.S_ISREG(st.st_mode):
            return True
        if statmod.S_ISLNK(st.st_mode):
            resolved = _resolve_path_safely(candidate)
            if resolved is None or not _is_within_any_root(resolved, allowed_roots):
                return False
            try:
                resolved_st = resolved.stat()
            except FileNotFoundError:
                return False
            return statmod.S_ISREG(resolved_st.st_mode)
        return False

    sidecar_rel = logical_parquet_to_sidecar_relpath(logical_relpath)
    if sidecar_rel is not None and _is_regular_file_or_allowed_symlink(base / sidecar_rel):
        return sidecar_rel

    legacy_rel = logical_relpath
    if _is_regular_file_or_allowed_symlink(base / legacy_rel):
        return legacy_rel

    return None


def pick_existing_parquet_path(wd: str | Path, logical_relpath: str) -> Path | None:
    """Return the first existing parquet path for a logical parquet id."""
    rel = pick_existing_parquet_relpath(wd, logical_relpath)
    if rel is None:
        return None
    return Path(wd) / rel
