"""Landuse parquet migrations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Tuple

from wepppy.tools.migrations.parquet_paths import pick_existing_parquet_path

__all__ = ["migrate_landuse_parquet"]


def _landuse_nodb_has_summaries(landuse_nodb: Path) -> Tuple[bool, str | None]:
    try:
        data = json.loads(landuse_nodb.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, f"Failed to read landuse.nodb: {exc}"

    state = data.get("py/state", data)
    if not isinstance(state, dict):
        return False, "Landuse nodb missing state"

    def _has_entries(value: Any) -> bool:
        return isinstance(value, dict) and bool(value)

    if _has_entries(state.get("domlc_d")):
        return True, None
    if _has_entries(state.get("managements")):
        return True, None

    return False, None


def migrate_landuse_parquet(wd: str, *, dry_run: bool = False) -> Tuple[bool, str]:
    """
    Normalize landuse parquet schema (topaz_id/wepp_id as Int32).

    Idempotent: safe to run multiple times.

    Args:
        wd: Working directory path
        dry_run: If True, report but don't modify

    Returns:
        (applied, message) tuple
    """
    run_path = Path(wd)
    landuse_dir = run_path / "landuse"
    landuse_parquet = pick_existing_parquet_path(run_path, "landuse/landuse.parquet")

    if landuse_parquet is None:
        landuse_csv = landuse_dir / "landuse.csv"
        if landuse_csv.exists():
            return True, "Legacy landuse.csv present (nothing to migrate)"

        landuse_nodb = run_path / "landuse.nodb"
        if not landuse_nodb.exists():
            return True, "No landuse parquet or nodb file (nothing to migrate)"

        has_summaries, error = _landuse_nodb_has_summaries(landuse_nodb)
        if error is not None:
            return False, error

        if not has_summaries:
            return True, "Landuse not built (nothing to migrate)"

        if dry_run:
            return True, "Would generate landuse parquet from landuse.nodb"

        try:
            from wepppy.nodb.core import Landuse
        except ImportError as exc:
            return False, f"Landuse migration unavailable: {exc}"

        try:
            landuse = Landuse.getInstance(str(run_path))
            landuse.dump_landuse_parquet()
        except Exception as exc:
            return False, f"Failed to generate landuse parquet: {exc}"

        landuse_parquet = pick_existing_parquet_path(run_path, "landuse/landuse.parquet")
        if landuse_parquet is not None:
            return True, "Generated landuse parquet from landuse.nodb"

        return False, "Landuse parquet missing after generation attempt"

    try:
        import pyarrow.parquet as pq
        import pandas as pd
    except ImportError:
        return False, "PyArrow/Pandas not available"

    try:
        meta = pq.read_metadata(landuse_parquet)
        schema = meta.schema.to_arrow_schema()
        field_names = [f.name for f in schema]
    except Exception as exc:
        return False, f"Failed to read parquet metadata: {exc}"

    # Check if migration needed (has uppercase columns)
    # Note: wepp_id is optional - not all landuse files have it
    needs_migration = (
        "TopazID" in field_names
        or "WeppID" in field_names
        or ("topaz_id" not in field_names and "TopazID" not in field_names)
        or ("area" not in field_names and "Area" in field_names)
    )

    if not needs_migration:
        return True, "Landuse parquet already normalized"

    if dry_run:
        return True, "Would normalize landuse parquet schema"

    try:
        df = pd.read_parquet(landuse_parquet)

        # Normalize column names
        if "TopazID" in df.columns and "topaz_id" not in df.columns:
            df["topaz_id"] = df["TopazID"].astype("Int32")
        if "WeppID" in df.columns and "wepp_id" not in df.columns:
            df["wepp_id"] = df["WeppID"].astype("Int32")
        if "Area" in df.columns and "area" not in df.columns:
            df["area"] = pd.to_numeric(df["Area"], errors="coerce")

        # Ensure types
        if "topaz_id" in df.columns:
            df["topaz_id"] = df["topaz_id"].astype("Int32")
        if "wepp_id" in df.columns:
            df["wepp_id"] = df["wepp_id"].astype("Int32")

        # Drop uppercase columns
        df = df.drop(columns=["TopazID", "WeppID"], errors="ignore")
        if "Area" in df.columns and "area" in df.columns:
            df = df.drop(columns=["Area"], errors="ignore")

        # Write back
        df.to_parquet(landuse_parquet, index=False)
        from wepppy.query_engine import update_catalog_entry
        update_catalog_entry(run_path, "landuse/landuse.parquet")
        return True, "Normalized landuse parquet schema"
    except Exception as exc:
        return False, f"Failed to normalize landuse parquet: {exc}"
