"""Soils parquet and NoDb migrations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Tuple

from wepppy.tools.migrations.parquet_paths import pick_existing_parquet_path

__all__ = [
    "migrate_soils_parquet",
    "migrate_soils_nodb_meta",
    "migrate_soils_dir_paths",
]


def _soils_nodb_has_summaries(soils_nodb: Path) -> Tuple[bool, str | None]:
    try:
        data = json.loads(soils_nodb.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, f"Failed to read soils.nodb: {exc}"

    state = data.get("py/state", data)
    if not isinstance(state, dict):
        return False, "Soils nodb missing state"

    def _has_entries(value: Any) -> bool:
        return isinstance(value, dict) and bool(value)

    if _has_entries(state.get("domsoil_d")):
        return True, None
    if _has_entries(state.get("soils")):
        return True, None

    return False, None


def migrate_soils_parquet(wd: str, *, dry_run: bool = False) -> Tuple[bool, str]:
    """
    Normalize soils parquet schema (topaz_id/wepp_id as Int32).

    Idempotent: safe to run multiple times.

    Args:
        wd: Working directory path
        dry_run: If True, report but don't modify

    Returns:
        (applied, message) tuple
    """
    run_path = Path(wd)
    soils_dir = run_path / "soils"
    soils_parquet = pick_existing_parquet_path(run_path, "soils/soils.parquet")

    if soils_parquet is None:
        soils_csv = soils_dir / "soils.csv"
        if soils_csv.exists():
            return True, "Legacy soils.csv present (nothing to migrate)"

        soils_nodb = run_path / "soils.nodb"
        if not soils_nodb.exists():
            return True, "No soils parquet or nodb file (nothing to migrate)"

        has_summaries, error = _soils_nodb_has_summaries(soils_nodb)
        if error is not None:
            return False, error

        if not has_summaries:
            return True, "Soils not built (nothing to migrate)"

        if dry_run:
            return True, "Would generate soils parquet from soils.nodb"

        try:
            from wepppy.nodb.core import Soils
        except ImportError as exc:
            return False, f"Soils migration unavailable: {exc}"

        try:
            soils = Soils.getInstance(str(run_path))
            soils.dump_soils_parquet()
        except Exception as exc:
            return False, f"Failed to generate soils parquet: {exc}"

        soils_parquet = pick_existing_parquet_path(run_path, "soils/soils.parquet")
        if soils_parquet is not None:
            return True, "Generated soils parquet from soils.nodb"

        return False, "Soils parquet missing after generation attempt"

    try:
        import pyarrow.parquet as pq
        import pandas as pd
    except ImportError:
        return False, "PyArrow/Pandas not available"

    try:
        meta = pq.read_metadata(soils_parquet)
        schema = meta.schema.to_arrow_schema()
        field_names = [f.name for f in schema]
    except Exception as exc:
        return False, f"Failed to read parquet metadata: {exc}"

    # Check if migration needed (has uppercase columns)
    # Note: wepp_id is optional - not all soils files have it
    needs_migration = (
        "TopazID" in field_names
        or "WeppID" in field_names
        or ("topaz_id" not in field_names and "TopazID" not in field_names)
        or ("area" not in field_names and "Area" in field_names)
    )

    if not needs_migration:
        return True, "Soils parquet already normalized"

    if dry_run:
        return True, "Would normalize soils parquet schema"

    try:
        df = pd.read_parquet(soils_parquet)

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
        df.to_parquet(soils_parquet, index=False)
        from wepppy.query_engine import update_catalog_entry
        update_catalog_entry(run_path, "soils/soils.parquet")
        return True, "Normalized soils parquet schema"
    except Exception as exc:
        return False, f"Failed to normalize soils parquet: {exc}"


def migrate_soils_nodb_meta(wd: str, *, dry_run: bool = False) -> Tuple[bool, str]:
    """
    Clear legacy _meta_fn attributes from SoilSummary objects in soils.nodb.

    The _meta_fn attributes point to legacy .json files containing pickled
    WeppSoil objects with numpy scalars. These files cause deserialization
    errors with newer numpy versions. When soils.parquet exists, these
    legacy metadata files are not needed.

    Idempotent: safe to run multiple times.

    Args:
        wd: Working directory path
        dry_run: If True, report but don't modify

    Returns:
        (applied, message) tuple
    """
    run_path = Path(wd)
    soils_parquet = pick_existing_parquet_path(run_path, "soils/soils.parquet")
    soils_nodb = run_path / "soils.nodb"

    # Only migrate if soils.parquet exists (new format is available)
    if soils_parquet is None:
        return True, "No soils.parquet (legacy meta files may still be needed)"

    if not soils_nodb.exists():
        return True, "No soils.nodb file"

    try:
        import jsonpickle
    except ImportError:
        return False, "jsonpickle not available"

    try:
        with open(soils_nodb, "r") as f:
            content = f.read()

        # Check if any _meta_fn attributes with non-null values exist
        # After migration, _meta_fn will be null, so we only need to migrate
        # if there are actual file paths (strings containing .json)
        import re
        has_meta_fn_values = bool(re.search(r"\"_meta_fn\":\s*\"[^\"]+\.json\"", content))

        if not has_meta_fn_values:
            return True, "No legacy _meta_fn attributes found"

        if dry_run:
            return True, "Would clear legacy _meta_fn attributes from soils.nodb"

        # Load the soils nodb object
        # We need to handle legacy module paths
        from wepppy.nodb.base import NoDbBase
        NoDbBase._ensure_legacy_module_imports(content)

        soils_obj = jsonpickle.decode(content)

        # Clear _meta_fn from all SoilSummary objects
        cleared_count = 0
        if hasattr(soils_obj, "soils") and soils_obj.soils:
            for soil_summary in soils_obj.soils.values():
                if hasattr(soil_summary, "_meta_fn") and soil_summary._meta_fn is not None:
                    soil_summary._meta_fn = None
                    cleared_count += 1

        if cleared_count == 0:
            return True, "No _meta_fn attributes to clear"

        # Write back
        with open(soils_nodb, "w") as f:
            f.write(jsonpickle.encode(soils_obj))

        return True, f"Cleared _meta_fn from {cleared_count} soil summaries"
    except Exception as exc:
        return False, f"Failed to migrate soils.nodb meta: {exc}"


def migrate_soils_dir_paths(wd: str, *, dry_run: bool = False) -> Tuple[bool, str]:
    """
    Fix relative soils_dir paths in SoilSummary objects to use absolute paths.

    Old projects stored soils_dir as relative paths like "runid/soils" which
    fail to resolve when the project is synced to a new location. This migration
    updates them to absolute paths based on the run's working directory.

    Idempotent: safe to run multiple times.

    Args:
        wd: Working directory path
        dry_run: If True, report but don't modify

    Returns:
        (applied, message) tuple
    """
    run_path = Path(wd).resolve()
    soils_nodb = run_path / "soils.nodb"
    soils_dir_path = run_path / "soils"
    correct_soils_dir = str(soils_dir_path)

    if not soils_nodb.exists():
        return True, "No soils.nodb file"

    try:
        import jsonpickle
    except ImportError:
        return False, "jsonpickle not available"

    def _needs_fix(current_dir: Any) -> bool:
        """Check if soils_dir needs to be fixed to correct_soils_dir."""
        # Guard against None or non-string values
        if not isinstance(current_dir, str):
            return True

        # Normalize and compare paths
        try:
            current_path = Path(current_dir)
            # If relative, needs fix
            if not current_path.is_absolute():
                return True
            # Compare resolved paths for equivalence (handles symlinks)
            # Note: resolve() may fail if path doesn't exist, so compare strings
            # for non-existent paths
            try:
                if current_path.resolve() != soils_dir_path:
                    return True
            except OSError:
                # Path doesn't exist or is invalid - compare as strings
                if str(current_path) != correct_soils_dir:
                    return True
        except (OSError, ValueError):
            # Invalid path, needs fix
            return True

        return False

    try:
        with open(soils_nodb, "r") as f:
            content = f.read()

        # Load the soils nodb object
        from wepppy.nodb.base import NoDbBase
        NoDbBase._ensure_legacy_module_imports(content)

        soils_obj = jsonpickle.decode(content)

        # Fix soils_dir in all SoilSummary objects
        fixed_count = 0
        if hasattr(soils_obj, "soils") and soils_obj.soils:
            for soil_summary in soils_obj.soils.values():
                if hasattr(soil_summary, "soils_dir"):
                    current_dir = soil_summary.soils_dir
                    if _needs_fix(current_dir):
                        if not dry_run:
                            soil_summary.soils_dir = correct_soils_dir
                        fixed_count += 1

        if fixed_count == 0:
            return True, "No soils_dir paths to fix"

        if dry_run:
            return True, f"Would fix soils_dir in {fixed_count} soil summaries"

        # Write back
        with open(soils_nodb, "w") as f:
            f.write(jsonpickle.encode(soils_obj))

        return True, f"Fixed soils_dir in {fixed_count} soil summaries"
    except Exception as exc:
        return False, f"Failed to migrate soils_dir paths: {exc}"
