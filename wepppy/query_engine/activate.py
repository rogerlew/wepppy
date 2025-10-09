from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List

from wepppy.nodb.core.climate import Climate
from wepppy.wepp.interchange import (
    generate_interchange_documentation,
    run_wepp_hillslope_interchange,
    run_wepp_watershed_interchange,
)

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


def activate_query_engine(
    wd: str | Path,
    *,
    run_interchange: bool = True,
) -> Dict[str, object]:
    """Scan a WEPPcloud working directory and build the query-engine catalog.

    Parameters
    ----------
    wd : str | Path
        Working directory for a WEPPcloud run (parent of wepp/, landuse/, etc.).
    run_interchange : bool, optional
        When True, run the WEPP interchange exporters for any `wepp/output`
        folder that does not already contain an `interchange` directory, by default True.

    Returns
    -------
    dict
        The catalog dictionary persisted under `<wd>/_query_engine/catalog.json`.

    Raises
    ------
    FileNotFoundError
        If the working directory does not exist.
    """

    base = Path(wd).expanduser().resolve()
    if not base.exists():
        raise FileNotFoundError(base)

    query_engine_dir = base / "_query_engine"
    query_engine_dir.mkdir(exist_ok=True)
    cache_dir = query_engine_dir / "cache"
    cache_dir.mkdir(exist_ok=True)

    if run_interchange:
        start_year = None
        try:
            climate = Climate.getInstance(str(base))
            if getattr(climate, "observed_start_year", None) is not None:
                start_year = climate.observed_start_year
        except Exception:  # pragma: no cover - best effort
            LOGGER.debug(
                "Unable to infer start_year from climate for %s; proceeding without override",
                base,
                exc_info=True,
            )
        _ensure_interchange(base, start_year=start_year)

    catalog_entries = _build_catalog(base)

    catalog: Dict[str, object] = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": str(base),
        "files": catalog_entries,
    }

    catalog_path = query_engine_dir / "catalog.json"
    catalog_path.write_text(json.dumps(catalog, indent=2, sort_keys=True), encoding="utf-8")

    return catalog


def _ensure_interchange(base: Path, *, start_year: int | None) -> None:
    """Generate WEPP interchange outputs when missing."""

    for output_dir in base.rglob("output"):
        if output_dir.parent.name != "wepp":
            continue

        interchange_dir = output_dir / "interchange"
        if interchange_dir.exists():
            continue

        LOGGER.info("Generating interchange outputs for %s", output_dir)
        try:
            run_wepp_hillslope_interchange(output_dir, start_year=start_year)
            run_wepp_watershed_interchange(output_dir, start_year=start_year)
            generate_interchange_documentation(interchange_dir)
        except Exception as exc:  # pragma: no cover - defensive logging
            LOGGER.exception("Failed to generate interchange products for %s", output_dir)
            raise


def _build_catalog(base: Path) -> List[Dict[str, object]]:
    """Walk the directory tree and collect metadata for known asset types."""

    entries: List[Dict[str, object]] = []
    base_len = len(str(base)) + 1

    for root, _, files in os.walk(base):
        root_path = Path(root)
        for name in files:
            path = root_path / name
            suffix = path.suffix.lower()
            if suffix not in SUPPORTED_EXTENSIONS:
                continue

            try:
                stat = path.stat()
            except FileNotFoundError:
                continue

            rel_path = str(path)[base_len:]
            entry: Dict[str, object] = {
                "path": rel_path.replace(os.sep, "/"),
                "extension": suffix,
                "size_bytes": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            }

            if suffix == ".parquet":
                entry["schema"] = _read_parquet_schema(path)

            entries.append(entry)

    entries.sort(key=lambda item: item["path"])
    return entries


def _read_parquet_schema(path: Path) -> Dict[str, object] | None:
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
