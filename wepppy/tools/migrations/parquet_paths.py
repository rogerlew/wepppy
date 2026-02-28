"""Directory-only parquet path resolution for migration helpers."""

from __future__ import annotations

from pathlib import Path

from wepppy.runtime_paths.parquet_sidecars import logical_parquet_to_sidecar_relpath

__all__ = [
    "pick_existing_parquet_path",
    "find_retired_root_resource_path",
]


def _normalize_logical_relpath(logical_relpath: str) -> str | None:
    rel = logical_relpath.strip().replace("\\", "/").lstrip("/")
    if not rel or rel in (".", ".."):
        return None
    parts = [part for part in rel.split("/") if part]
    if not parts or any(part in (".", "..") for part in parts):
        return None
    return "/".join(parts)


def _canonical_relpath(logical_relpath: str) -> str | None:
    if logical_relpath == "landuse/landuse.parquet":
        return logical_relpath
    if logical_relpath == "soils/soils.parquet":
        return logical_relpath
    if logical_relpath.startswith("climate/") and logical_relpath.endswith(".parquet"):
        name = logical_relpath[len("climate/") : -len(".parquet")]
        if not name or "/" in name:
            return None
        return logical_relpath
    if logical_relpath.startswith("watershed/") and logical_relpath.endswith(".parquet"):
        name = logical_relpath[len("watershed/") : -len(".parquet")]
        if not name or "/" in name:
            return None
        return logical_relpath
    return None


def find_retired_root_resource_path(
    wd: str | Path,
    logical_relpath: str,
) -> Path | None:
    normalized = _normalize_logical_relpath(logical_relpath)
    if normalized is None:
        return None

    sidecar_rel = logical_parquet_to_sidecar_relpath(normalized)
    if sidecar_rel is None:
        return None

    candidate = Path(wd) / sidecar_rel
    if candidate.is_file():
        return candidate

    return None


def pick_existing_parquet_path(
    wd: str | Path,
    logical_relpath: str,
    *,
    directory_first: bool = True,
) -> Path | None:
    """Return canonical directory parquet path when present.

    Args:
        wd: Run working directory.
        logical_relpath: Canonical logical parquet relpath.
        directory_first: Retained for compatibility; ignored in directory-only mode.
    """

    _ = directory_first
    normalized = _normalize_logical_relpath(logical_relpath)
    if normalized is None:
        return None

    canonical_rel = _canonical_relpath(normalized)
    if canonical_rel is None:
        return None

    candidate = Path(wd) / canonical_rel
    if candidate.is_file():
        return candidate

    return None
