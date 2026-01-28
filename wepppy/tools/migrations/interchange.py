"""WEPP interchange migrations."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Tuple

__all__ = ["migrate_interchange", "refresh_query_catalog"]


def migrate_interchange(wd: str, *, force: bool = False, dry_run: bool = False) -> Tuple[bool, str]:
    """
    Generate WEPP interchange Parquet files.

    Idempotent: regenerates if missing or force=True.

    Args:
        wd: Working directory path
        force: If True, regenerate even if interchange exists
        dry_run: If True, report but don't modify

    Returns:
        (applied, message) tuple
    """
    run_path = Path(wd)

    # Check for required .nodb files
    wepp_nodb = run_path / "wepp.nodb"
    climate_nodb = run_path / "climate.nodb"

    if not wepp_nodb.exists() or not climate_nodb.exists():
        return True, "Missing wepp.nodb or climate.nodb (nothing to migrate)"

    # Locate WEPP output directory
    wepp_output_dir = run_path / "wepp" / "output"

    if not wepp_output_dir.exists():
        return True, "No WEPP output directory (nothing to migrate)"

    # Check for existing interchange
    interchange_dir = wepp_output_dir / "interchange"
    version_file = interchange_dir / "interchange_version.json"

    # Check if the new-format loss files exist (loss_pw0.hill.parquet, loss_pw0.out.parquet)
    # Old interchange may have H.loss.parquet but not the loss_pw0.* files
    loss_hill_file = interchange_dir / "loss_pw0.hill.parquet"
    loss_out_file = interchange_dir / "loss_pw0.out.parquet"
    has_new_format = loss_hill_file.exists() and loss_out_file.exists()

    if interchange_dir.exists() and version_file.exists() and has_new_format and not force:
        return True, "Interchange already exists"

    if interchange_dir.exists() and not has_new_format:
        if dry_run:
            return False, "Interchange has old format (missing loss_pw0.* files), needs regeneration"
        # Old format - will regenerate

    if dry_run:
        return True, "Would generate interchange files"

    # Import wepppy modules
    try:
        from wepppy.nodb.core import Climate, Wepp
        from wepppy.wepp.interchange import (
            run_wepp_hillslope_interchange,
            run_wepp_watershed_interchange,
            run_totalwatsed3,
            generate_interchange_documentation,
        )
    except ImportError as exc:
        return False, f"Failed to import wepppy modules: {exc}"

    # Load NoDb instances
    try:
        climate = Climate.getInstance(str(run_path))
        wepp = Wepp.getInstance(str(run_path))
        start_year = climate.calendar_start_year
        baseflow_opts = wepp.baseflow_opts
        is_single_storm = climate.is_single_storm
        delete_after_interchange = wepp.delete_after_interchange
    except Exception as exc:
        return False, f"Failed to load run configuration: {exc}"

    # Check for watershed outputs
    # Single storm runs don't have soil_pw0.txt or chnwb.txt
    if is_single_storm:
        required_files = ["pass_pw0.txt", "chan.out", "chanwb.out", "ebe_pw0.txt", "loss_pw0.txt"]
    else:
        required_files = [
            "pass_pw0.txt",
            "chan.out",
            "chanwb.out",
            "chnwb.txt",
            "ebe_pw0.txt",
            "soil_pw0.txt",
            "loss_pw0.txt",
        ]
    has_watershed = all(
        (wepp_output_dir / f).exists() or (wepp_output_dir / f"{f}.gz").exists()
        for f in required_files
    )

    # Backup existing interchange if forcing
    if force and interchange_dir.exists():
        backup_dir = interchange_dir.with_suffix(".bak")
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        shutil.move(str(interchange_dir), str(backup_dir))

    generated = []

    # Run hillslope interchange
    # Single storm runs don't produce .loss.dat, .soil.dat, or .wat.dat files
    try:
        run_wepp_hillslope_interchange(
            wepp_output_dir,
            start_year=start_year,
            run_loss_interchange=not is_single_storm,
            run_soil_interchange=not is_single_storm,
            run_wat_interchange=not is_single_storm,
            delete_after_interchange=delete_after_interchange,
        )
        generated.append("hillslope")
    except Exception as exc:
        return False, f"Hillslope interchange failed: {exc}"

    # Run watershed interchange if outputs exist
    if has_watershed:
        try:
            # Single storm runs don't have soil/chnwb outputs
            run_wepp_watershed_interchange(
                wepp_output_dir,
                start_year=start_year,
                run_soil_interchange=not is_single_storm,
                run_chnwb_interchange=not is_single_storm,
                delete_after_interchange=delete_after_interchange,
            )
            generated.append("watershed")
        except Exception:
            pass  # Non-fatal

    # Generate totalwatsed3
    try:
        run_totalwatsed3(interchange_dir, baseflow_opts=baseflow_opts)
        generated.append("totalwatsed3")
    except Exception:
        pass  # Non-fatal

    # Generate documentation
    try:
        generate_interchange_documentation(interchange_dir)
        generated.append("docs")
    except Exception:
        pass  # Non-fatal

    return True, f"Generated interchange: {', '.join(generated)}"


def refresh_query_catalog(wd: str, *, dry_run: bool = False) -> Tuple[bool, str]:
    """
    Refresh the query engine catalog for the working directory.

    The query engine maintains a catalog of available parquet datasets. After
    interchange generation or other migrations create new parquet files, the
    catalog must be refreshed so reports can find them.

    Args:
        wd: Working directory path
        dry_run: If True, report but don't modify

    Returns:
        (applied, message) tuple
    """
    run_path = Path(wd)

    # Check if there are any parquet files that would need cataloging
    interchange_dir = run_path / "wepp" / "output" / "interchange"
    if not interchange_dir.exists():
        return True, "No interchange directory (catalog refresh skipped)"

    parquet_files = list(interchange_dir.glob("*.parquet"))
    if not parquet_files:
        return True, "No parquet files in interchange (catalog refresh skipped)"

    if dry_run:
        return True, f"Would refresh query catalog for {len(parquet_files)} parquet file(s)"

    try:
        from wepppy.query_engine import activate_query_engine
    except ImportError:
        return True, "Query engine not available (catalog refresh skipped)"

    try:
        activate_query_engine(str(run_path), run_interchange=False, force_refresh=True)
        return True, f"Refreshed query catalog ({len(parquet_files)} interchange files)"
    except Exception as exc:
        # Non-fatal - catalog will be refreshed on first query
        return True, f"Catalog refresh deferred: {exc}"
