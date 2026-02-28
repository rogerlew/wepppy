"""Directory-only parquet resolution helpers for NoDir roots."""

from __future__ import annotations

import re
from pathlib import Path

from .errors import nodir_migration_required
from .paths import NODIR_ROOTS, normalize_relpath

__all__ = [
    "logical_parquet_to_sidecar_relpath",
    "sidecar_relpath_to_logical_parquet",
    "find_existing_retired_root_resource_relpath",
    "list_existing_retired_root_resources",
    "pick_existing_parquet_relpath",
    "pick_existing_parquet_path",
    "require_directory_parquet_path",
]

_CLIMATE_LOGICAL_RE = re.compile(r"^climate/([^/]+)\.parquet$")
_WATERSHED_LOGICAL_RE = re.compile(r"^watershed/([^/]+)\.parquet$")
_CLIMATE_SIDECAR_RE = re.compile(r"^climate\.([^/]+)\.parquet$")
_WATERSHED_SIDECAR_RE = re.compile(r"^watershed\.([^/]+)\.parquet$")


def logical_parquet_to_sidecar_relpath(logical_relpath: str) -> str | None:
    logical = logical_relpath.strip().lstrip("/")
    if logical == "landuse/landuse.parquet":
        return "landuse.parquet"
    if logical == "soils/soils.parquet":
        return "soils.parquet"

    climate_match = _CLIMATE_LOGICAL_RE.match(logical)
    if climate_match:
        return f"climate.{climate_match.group(1)}.parquet"

    watershed_match = _WATERSHED_LOGICAL_RE.match(logical)
    if watershed_match:
        return f"watershed.{watershed_match.group(1)}.parquet"

    return None


def sidecar_relpath_to_logical_parquet(sidecar_relpath: str) -> str | None:
    sidecar = sidecar_relpath.strip().lstrip("/")
    if sidecar == "landuse.parquet":
        return "landuse/landuse.parquet"
    if sidecar == "soils.parquet":
        return "soils/soils.parquet"

    climate_match = _CLIMATE_SIDECAR_RE.match(sidecar)
    if climate_match:
        return f"climate/{climate_match.group(1)}.parquet"

    watershed_match = _WATERSHED_SIDECAR_RE.match(sidecar)
    if watershed_match:
        return f"watershed/{watershed_match.group(1)}.parquet"

    return None


def _normalize_logical_parquet_relpath(logical_relpath: str) -> str | None:
    try:
        logical = normalize_relpath(logical_relpath)
    except ValueError:
        return None

    if logical in ("", "."):
        return None
    if logical.split("/", 1)[0] not in NODIR_ROOTS:
        return None
    if not logical.endswith(".parquet"):
        return None

    return logical


def find_existing_retired_root_resource_relpath(
    wd: str | Path,
    logical_relpath: str,
) -> str | None:
    logical = _normalize_logical_parquet_relpath(logical_relpath)
    if logical is None:
        return None

    sidecar_rel = logical_parquet_to_sidecar_relpath(logical)
    if sidecar_rel is None:
        return None

    if (Path(wd) / sidecar_rel).is_file():
        return sidecar_rel

    return None


def list_existing_retired_root_resources(wd: str | Path) -> list[str]:
    """Return in-scope retired WD-root resources that still exist."""
    base = Path(wd)
    resources: set[str] = set()

    for fixed in ("landuse.parquet", "soils.parquet", "wepp_cli_pds_mean_metric.csv"):
        if (base / fixed).is_file():
            resources.add(fixed)

    for candidate in base.glob("climate.*.parquet"):
        if candidate.is_file():
            resources.add(candidate.name)

    for candidate in base.glob("watershed.*.parquet"):
        if candidate.is_file():
            resources.add(candidate.name)

    return sorted(resources)


def pick_existing_parquet_relpath(wd: str | Path, logical_relpath: str) -> str | None:
    """Return canonical parquet relpath when present under its directory root.

    Runtime fallback to WD-root sidecars is retired in Phase 7.
    """
    logical = _normalize_logical_parquet_relpath(logical_relpath)
    if logical is None:
        return None

    if (Path(wd) / logical).is_file():
        return logical

    return None


def pick_existing_parquet_path(wd: str | Path, logical_relpath: str) -> Path | None:
    relpath = pick_existing_parquet_relpath(wd, logical_relpath)
    if relpath is None:
        return None
    return Path(wd) / relpath


def require_directory_parquet_path(wd: str | Path, logical_relpath: str) -> Path:
    """Return canonical directory parquet path or raise explicit migration-required error."""
    logical = _normalize_logical_parquet_relpath(logical_relpath)
    if logical is None:
        raise FileNotFoundError(logical_relpath)

    parquet_path = Path(wd) / logical
    if parquet_path.is_file():
        return parquet_path

    retired_root = find_existing_retired_root_resource_relpath(wd, logical)
    if retired_root is not None:
        raise nodir_migration_required(
            f"Retired root resource '{retired_root}' detected for '{logical}'. "
            "Migration required before runtime access."
        )

    raise FileNotFoundError(logical)
