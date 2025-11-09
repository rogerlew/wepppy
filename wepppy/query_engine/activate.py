"""Catalog activation helpers for WEPPcloud query engine assets."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from collections.abc import Iterable

LOGGER = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS: tuple[str, ...] = (
    ".nodb",
    ".tsv",
    ".csv",
    ".tif",
    ".parquet",
    ".json",
    ".geojson",
)

GEO_SCHEMA_EXTENSIONS: tuple[str, ...] = (
    ".geojson",
)

READONLY_SENTINEL = "READONLY"


def activate_query_engine(
    wd: str | Path,
    *,
    run_interchange: bool = True,
) -> dict[str, object]:
    """Scan a working directory and build the query-engine catalog.

    Args:
        wd: Working directory for a WEPPcloud run (parent of `wepp/`, `landuse/`, etc.).
        run_interchange: When True, generate missing WEPP interchange outputs.

    Returns:
        Catalog dictionary persisted under `<wd>/_query_engine/catalog.json`.

    Raises:
        FileNotFoundError: If the supplied working directory does not exist.
        PermissionError: If the working directory is flagged read-only.
    """

    base = Path(wd).expanduser().resolve()
    if not base.exists():
        raise FileNotFoundError(base)

    _raise_if_readonly(base)

    query_engine_dir = base / "_query_engine"
    query_engine_dir.mkdir(exist_ok=True)
    cache_dir = query_engine_dir / "cache"
    cache_dir.mkdir(exist_ok=True)

    if run_interchange:
        start_year = None
        try:
            from wepppy.nodb.core.climate import Climate  # local import to avoid heavy deps during import

            climate = Climate.getInstance(str(base))
            if getattr(climate, "observed_start_year", '') != '':
                start_year = climate.observed_start_year
        except Exception:  # pragma: no cover - best effort
            LOGGER.debug(
                "Unable to infer start_year from climate for %s; proceeding without override",
                base,
                exc_info=True,
            )
        _ensure_interchange(base, start_year=start_year)

    catalog_entries = _build_catalog(base)

    catalog: dict[str, object] = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": str(base),
        "files": catalog_entries,
    }

    catalog_path = query_engine_dir / "catalog.json"
    catalog_path.write_text(json.dumps(catalog, indent=2, sort_keys=True), encoding="utf-8")

    return catalog


def update_catalog_entry(
    wd: str | Path,
    asset_path: str,
) -> dict[str, object] | None:
    """Update the catalog entry for a single asset under the WEPP working directory.

    Args:
        wd: Working directory for a WEPPcloud run.
        asset_path: File path relative to the working directory (or absolute path).

    Returns:
        The updated catalog entry or None if the file was removed.

    Raises:
        FileNotFoundError: If the working directory or catalog does not exist.
        PermissionError: If the working directory is flagged as read-only.
        ValueError: If the requested path resides outside the working directory.
    """

    base = Path(wd).expanduser().resolve()
    if not base.exists():
        raise FileNotFoundError(base)

    _raise_if_readonly(base)

    rel_path_obj = Path(asset_path)
    if rel_path_obj.is_absolute():
        target = rel_path_obj.resolve()
    else:
        target = (base / rel_path_obj).resolve()

    try:
        rel_from_base = target.relative_to(base)
    except ValueError as exc:
        raise ValueError(f"Path '{asset_path}' is outside working directory '{base}'") from exc

    catalog_path = base / "_query_engine" / "catalog.json"
    if not catalog_path.exists():
        # fall back to full activation
        return activate_query_engine(base, run_interchange=False)

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    files: list[dict[str, object]] = catalog.get("files", [])
    files_by_path = {entry["path"]: entry for entry in files}

    updated_entry: dict[str, object] | None = None
    if target.exists():
        if target.is_dir():
            new_entries = _build_catalog_subset(base, target)
            for entry in new_entries:
                files_by_path[entry["path"]] = entry
            updated_entry = None
        else:
            entry = _build_entry(base, target)
            if entry is None:
                raise ValueError(f"Unsupported asset type for '{target}'")
            files_by_path[entry["path"]] = entry
            updated_entry = entry
    else:
        files_by_path.pop(str(rel_from_base).replace(os.sep, "/"), None)

    catalog["files"] = sorted(files_by_path.values(), key=lambda item: item["path"])
    catalog["generated_at"] = datetime.now(timezone.utc).isoformat()
    catalog_path.write_text(json.dumps(catalog, indent=2, sort_keys=True), encoding="utf-8")

    return updated_entry


def _ensure_interchange(base: Path, *, start_year: int | None) -> None:
    """Generate WEPP interchange outputs when missing.

    Args:
        base: Working directory path.
        start_year: Optional start year override for climate-aware runs.
    """
    try:
        start_year = int(start_year)  # type: ignore
    except (TypeError, ValueError):
        start_year = None

    from wepppy.wepp.interchange import (
        generate_interchange_documentation,
        needs_major_refresh,
        remove_incompatible_interchange,
        run_wepp_hillslope_interchange,
        run_wepp_watershed_interchange,
    )

    for output_dir in base.rglob("output"):
        if output_dir.parent.name != "wepp":
            continue

        interchange_dir = output_dir / "interchange"
        refresh_required = needs_major_refresh(interchange_dir)
        if interchange_dir.exists() and not refresh_required:
            continue

        if refresh_required:
            LOGGER.info("Refreshing interchange outputs for %s due to version change", output_dir)
            remove_incompatible_interchange(interchange_dir)

        LOGGER.info("Generating interchange outputs for %s", output_dir)
        try:
            run_wepp_hillslope_interchange(output_dir, start_year=start_year)
            run_wepp_watershed_interchange(output_dir, start_year=start_year)
            generate_interchange_documentation(interchange_dir)
        except Exception as exc:  # pragma: no cover - defensive logging
            LOGGER.warning("Failed to generate interchange products for %s", output_dir)
            pass


def _build_catalog(base: Path) -> list[dict[str, object]]:
    """Walk the directory tree and collect metadata for known asset types.

    Args:
        base: Working directory root.

    Returns:
        Sorted list of catalog entries keyed by path.
    """

    entries: list[dict[str, object]] = []
    base_len = len(str(base)) + 1

    for root, _, files in os.walk(base):
        root_path = Path(root)
        for name in files:
            path = root_path / name
            entry = _build_entry(base, path, base_len=base_len)
            if entry is None:
                continue
            entries.append(entry)

    entries.sort(key=lambda item: item["path"])
    return entries


def _build_catalog_subset(base: Path, directory: Path) -> list[dict[str, object]]:
    """Build catalog entries limited to a specific directory subtree.

    Args:
        base: Run directory root.
        directory: Directory tree that should be re-indexed.

    Returns:
        List of catalog entries contained inside the subtree.
    """
    entries: list[dict[str, object]] = []
    base_len = len(str(base)) + 1

    for root, _, files in os.walk(directory):
        root_path = Path(root)
        for name in files:
            path = root_path / name
            entry = _build_entry(base, path, base_len=base_len)
            if entry is None:
                continue
            entries.append(entry)

    return entries


def _read_parquet_schema(path: Path) -> dict[str, object] | None:
    """Read parquet schema metadata for inclusion in the catalog.

    Args:
        path: Path to the parquet file.

    Returns:
        Dictionary describing schema fields, or None if unavailable.
    """
    try:
        import pyarrow.parquet as pq  # type: ignore
    except ImportError:  # pragma: no cover
        LOGGER.debug("pyarrow not available; skipping schema for %s", path)
        return None

    try:
        schema = pq.read_schema(path)
    except Exception:  # pragma: no cover - corrupted parquet or missing dependencies
        LOGGER.debug("Unable to read parquet schema for %s", path, exc_info=True)
        return None

    fields = []
    for field in schema:
        field_info = {"name": field.name, "type": str(field.type)}
        if field.metadata:
            if b"units" in field.metadata:
                field_info["units"] = field.metadata[b"units"].decode(errors="ignore")
            if b"description" in field.metadata:
                field_info["description"] = field.metadata[b"description"].decode(errors="ignore")
        fields.append(field_info)

    return {"fields": fields}


def _read_geo_schema(path: Path) -> dict[str, object] | None:
    """Attempt to read schema metadata for geojson-compatible files.

    Args:
        path: Path to the geospatial file.

    Returns:
        Dictionary describing schema fields, or None.
    """
    try:
        import duckdb
    except ImportError:  # pragma: no cover
        LOGGER.debug("duckdb not available; skipping geo schema for %s", path)
        return None


def _build_entry(base: Path, path: Path, *, base_len: int | None = None) -> dict[str, object] | None:
    """Build a catalog entry for a single file path.

    Args:
        base: Base working directory.
        path: File path being catalogued.
        base_len: Optional cached length of the base path for slicing.

    Returns:
        Catalog entry dictionary or None when unsupported.
    """
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        return None

    try:
        stat = path.stat()
    except FileNotFoundError:
        return None

    if base_len is None:
        base_len = len(str(base)) + 1

    rel_path = str(path)[base_len:]
    entry: dict[str, object] = {
        "path": rel_path.replace(os.sep, "/"),
        "extension": suffix,
        "size_bytes": stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
    }

    if suffix == ".parquet":
        entry["schema"] = _read_parquet_schema(path)
    elif suffix in GEO_SCHEMA_EXTENSIONS:
        entry["schema"] = _read_geo_schema(path)

    return entry


def _raise_if_readonly(base: Path) -> None:
    """Raise PermissionError when a WEPP run is marked read-only."""
    if (base / READONLY_SENTINEL).exists():
        raise PermissionError(f"Working directory '{base}' is flagged as read-only")
