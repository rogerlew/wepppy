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
from pathlib import Path

__all__ = [
    "logical_parquet_to_sidecar_relpath",
    "sidecar_relpath_to_logical_parquet",
    "pick_existing_parquet_relpath",
    "pick_existing_parquet_path",
]


_CLIMATE_LOGICAL_RE = re.compile(r"^climate/([^/]+)\\.parquet$")
_WATERSHED_LOGICAL_RE = re.compile(r"^watershed/([^/]+)\\.parquet$")

_CLIMATE_SIDECAR_RE = re.compile(r"^climate\\.([^/]+)\\.parquet$")
_WATERSHED_SIDECAR_RE = re.compile(r"^watershed\\.([^/]+)\\.parquet$")


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
    logical_relpath = logical_relpath.replace("\\", "/").lstrip("/")

    sidecar_rel = logical_parquet_to_sidecar_relpath(logical_relpath)
    if sidecar_rel is not None and (base / sidecar_rel).is_file():
        return sidecar_rel

    legacy_rel = logical_relpath
    if (base / legacy_rel).is_file():
        return legacy_rel

    return None


def pick_existing_parquet_path(wd: str | Path, logical_relpath: str) -> Path | None:
    """Return the first existing parquet path for a logical parquet id."""
    rel = pick_existing_parquet_relpath(wd, logical_relpath)
    if rel is None:
        return None
    return Path(wd) / rel

