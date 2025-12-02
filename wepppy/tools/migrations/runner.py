"""
Core migration runner for single working directories.

This module provides idempotent migration functions that can be used both
from CLI scripts and RQ tasks. Each migration operates on a single run
working directory (wd) and returns a result indicating what was changed.

Usage:
    from wepppy.tools.migrations.runner import run_all_migrations, MigrationResult

    result = run_all_migrations("/wc1/runs/bi/biogeographic-six")
    if result.success:
        print(f"Migrations applied: {result.applied}")
    else:
        print(f"Migration failed: {result.errors}")
"""

from __future__ import annotations

import json
import pickle
import shutil
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

__all__ = [
    "MigrationResult",
    "run_all_migrations",
    "check_migrations_needed",
    "migrate_observed_nodb",
    "migrate_run_paths",
    "migrate_interchange",
    "migrate_watersheds",
    "migrate_watershed_nodb_slim",
    "migrate_wbt_geojson",
    "migrate_landuse_parquet",
    "migrate_soils_parquet",
    "refresh_query_catalog",
    "invalidate_redis_cache",
    "AVAILABLE_MIGRATIONS",
    "MIGRATION_DESCRIPTIONS",
]


@dataclass
class MigrationResult:
    """Result from running migrations on a single working directory."""
    
    wd: str
    success: bool = True
    applied: List[str] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)
    errors: Dict[str, str] = field(default_factory=dict)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize result to a dictionary."""
        return {
            "wd": self.wd,
            "success": self.success,
            "applied": self.applied,
            "skipped": self.skipped,
            "errors": self.errors,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


def _is_valid_run_directory(wd: Path) -> bool:
    """Check if a path is a valid run working directory."""
    # Must contain at least one .nodb file
    nodb_files = list(wd.glob("*.nodb"))
    return len(nodb_files) > 0


# ---------------------------------------------------------------------------
# Individual migration functions
# Each returns (applied: bool, message: str)
# All migrations are idempotent - safe to run multiple times
# applied=True means migration ran successfully (even if no changes needed)
# ---------------------------------------------------------------------------

def migrate_observed_nodb(wd: str, *, dry_run: bool = False) -> Tuple[bool, str]:
    """
    Migrate observed.nodb from legacy module path to new path.
    
    Idempotent: safe to run multiple times.
    
    Args:
        wd: Working directory path
        dry_run: If True, report but don't modify
        
    Returns:
        (applied, message) tuple
    """
    run_path = Path(wd)
    observed_nodb = run_path / "observed.nodb"
    
    if not observed_nodb.exists():
        return True, "No observed.nodb found (nothing to migrate)"
    
    try:
        with open(observed_nodb, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, f"Failed to parse JSON: {e}"
    
    py_object = data.get("py/object", "")
    
    # Already migrated - idempotent success
    if py_object == "wepppy.nodb.mods.observed.observed.Observed":
        return True, "Already migrated"
    
    # Unknown format - can't migrate
    if py_object != "wepppy.nodb.observed.Observed":
        return True, f"Unknown py/object type: {py_object} (skipped)"
    
    if dry_run:
        return True, "Would migrate observed.nodb module path"
    
    # Update the module path
    data["py/object"] = "wepppy.nodb.mods.observed.observed.Observed"
    
    with open(observed_nodb, 'w') as f:
        json.dump(data, f, indent=2)
    
    return True, "Migrated observed.nodb module path"


def migrate_run_paths(
    wd: str,
    *,
    dry_run: bool = False,
) -> Tuple[bool, str]:
    """
    Migrate hardcoded paths in .nodb files to match the current working directory.
    
    This migration is idempotent - it transforms all legacy path formats to the
    current working directory path. Running it multiple times has no effect if
    paths are already correct.
    
    Legacy formats handled:
    - /geodata/wc1/runs/<prefix>/<runid> -> current wd
    - /geodata/wc1/<runid> -> current wd  
    - /geodata/weppcloud_runs/<runid> -> current wd (wepp.cloud format)
    
    Args:
        wd: Working directory path
        dry_run: If True, report what would change but don't modify
        
    Returns:
        (applied, message) tuple - applied is True if any changes were made
    """
    import re
    
    run_path = Path(wd)
    nodb_files = sorted(run_path.glob("*.nodb"))
    
    if not nodb_files:
        return True, "No .nodb files found (nothing to migrate)"
    
    wd_abs = str(run_path.resolve())
    runid = Path(wd_abs).name
    
    # Build regex patterns for all legacy path formats
    patterns = [
        # /geodata/wc1/runs/<prefix>/<runid>
        (re.compile(r'/geodata/wc1/runs/[^/]+/' + re.escape(runid) + r'(?=/|$)'), wd_abs),
        # /geodata/wc1/<runid>
        (re.compile(r'/geodata/wc1/' + re.escape(runid) + r'(?=/|$)'), wd_abs),
        # /geodata/weppcloud_runs/<runid>
        (re.compile(r'/geodata/weppcloud_runs/' + re.escape(runid) + r'(?=/|$)'), wd_abs),
    ]
    
    def _migrate_string(s: str) -> str:
        for pattern, replacement in patterns:
            s = pattern.sub(replacement, s)
        return s
    
    def _migrate_recursive(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: _migrate_recursive(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [_migrate_recursive(item) for item in obj]
        elif isinstance(obj, str):
            return _migrate_string(obj)
        return obj
    
    total_replacements = 0
    files_processed = 0
    
    for nodb_file in nodb_files:
        try:
            with open(nodb_file, 'r') as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        
        files_processed += 1
        original_str = json.dumps(data)
        migrated_data = _migrate_recursive(data)
        migrated_str = json.dumps(migrated_data)
        
        # Count actual changes
        if original_str != migrated_str:
            count = sum(len(p.findall(original_str)) for p, _ in patterns)
            total_replacements += count
            
            if not dry_run:
                with open(nodb_file, 'w') as f:
                    json.dump(migrated_data, f, indent=2)
    
    if total_replacements == 0:
        return True, f"Processed {files_processed} file(s), no legacy paths found"
    
    action = "Would migrate" if dry_run else "Migrated"
    return True, f"{action} {total_replacements} path(s) in {files_processed} file(s)"


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
    
    if interchange_dir.exists() and version_file.exists() and not force:
        return True, "Interchange already exists"
    
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
    except ImportError as e:
        return False, f"Failed to import wepppy modules: {e}"
    
    # Load NoDb instances
    try:
        climate = Climate.getInstance(str(run_path))
        wepp = Wepp.getInstance(str(run_path))
        start_year = climate.calendar_start_year
        baseflow_opts = wepp.baseflow_opts
        is_single_storm = climate.is_single_storm
    except Exception as e:
        return False, f"Failed to load run configuration: {e}"
    
    # Check for watershed outputs
    # Single storm runs don't have soil_pw0.txt or chnwb.txt
    if is_single_storm:
        required_files = ["pass_pw0.txt", "chan.out", "chanwb.out", "ebe_pw0.txt", "loss_pw0.txt"]
    else:
        required_files = ["pass_pw0.txt", "chan.out", "chanwb.out", "chnwb.txt", "ebe_pw0.txt", "soil_pw0.txt", "loss_pw0.txt"]
    has_watershed = all(
        (wepp_output_dir / f).exists() or (wepp_output_dir / f"{f}.gz").exists()
        for f in required_files
    )
    
    # Backup existing interchange if forcing
    if force and interchange_dir.exists():
        backup_dir = interchange_dir.with_suffix('.bak')
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
        )
        generated.append("hillslope")
    except Exception as e:
        return False, f"Hillslope interchange failed: {e}"
    
    # Run watershed interchange if outputs exist
    if has_watershed:
        try:
            # Single storm runs don't have soil/chnwb outputs
            run_wepp_watershed_interchange(
                wepp_output_dir,
                start_year=start_year,
                run_soil_interchange=not is_single_storm,
                run_chnwb_interchange=not is_single_storm,
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


def migrate_watersheds(wd: str, *, dry_run: bool = False, keep_csv: bool = False) -> Tuple[bool, str]:
    """
    Normalize watershed parquet schemas (Peridot tables).
    
    Converts legacy CSV files to Parquet and normalizes ID columns.
    Idempotent: safe to run multiple times.
    
    Args:
        wd: Working directory path
        dry_run: If True, report but don't modify
        keep_csv: If True, don't delete legacy CSV files
        
    Returns:
        (applied, message) tuple
    """
    run_path = Path(wd)
    watershed_dir = run_path / "watershed"
    
    if not watershed_dir.exists():
        return True, "No watershed directory (nothing to migrate)"
    
    # Check if any parquet OR csv files exist (CSVs are converted to parquet)
    parquet_files = list(watershed_dir.glob("*.parquet"))
    csv_files = list(watershed_dir.glob("*.csv"))
    
    if not parquet_files and not csv_files:
        return True, "No watershed data files (nothing to migrate)"
    
    # Check if CSV files need conversion
    needs_csv_conversion = bool(csv_files)
    
    # Check if parquet files need schema normalization
    needs_normalization = False
    if parquet_files and not needs_csv_conversion:
        try:
            import pyarrow.parquet as pq
            for pf in parquet_files[:3]:  # Sample first few files
                try:
                    schema = pq.read_schema(pf)
                    col_names = [f.name for f in schema]
                    # Check for legacy uppercase ID columns
                    if any(c in col_names for c in ['TOPAZ_ID', 'TopazID', 'Topaz_ID', 'WEPP_ID', 'WeppID', 'Wepp_ID']):
                        needs_normalization = True
                        break
                except Exception:
                    continue
        except ImportError:
            # Can't check without pyarrow, assume normalization needed
            needs_normalization = True
    
    if dry_run:
        if needs_csv_conversion:
            return True, f"Would convert {len(csv_files)} CSV file(s) to Parquet"
        if needs_normalization:
            return True, f"Would normalize {len(parquet_files)} watershed parquet file(s)"
        return True, "Watershed tables already normalized (nothing to migrate)"
    
    try:
        from wepppy.topo.peridot.peridot_runner import migrate_watershed_outputs
        changed = migrate_watershed_outputs(str(run_path), remove_csv=not keep_csv, verbose=False)
    except ImportError:
        return True, "Peridot migration not available (skipped)"
    except Exception as e:
        return False, f"Watershed migration failed: {e}"
    
    if changed:
        return True, "Normalized watershed tables (CSV to Parquet conversion)"
    return True, "Watershed tables already normalized"


def migrate_watershed_nodb_slim(wd: str, *, dry_run: bool = False) -> Tuple[bool, str]:
    """
    Remove legacy summary dictionaries from watershed.nodb and externalize structure.
    
    After parquet files exist (hillslopes.parquet, flowpaths.parquet, channels.parquet),
    the _subs_summary, _fps_summary, and _chns_summary dictionaries are no longer needed
    in watershed.nodb. Removing them reduces file size dramatically for large watersheds.
    
    Also migrates inline _structure data to structure.pkl file if not already externalized.
    
    Idempotent: safe to run multiple times.
    
    Args:
        wd: Working directory path
        dry_run: If True, report but don't modify
        
    Returns:
        (applied, message) tuple
    """
    run_path = Path(wd)
    watershed_nodb = run_path / "watershed.nodb"
    watershed_dir = run_path / "watershed"
    
    if not watershed_nodb.exists():
        return True, "No watershed.nodb (nothing to migrate)"
    
    # Check that required parquet files exist
    required_parquets = ["hillslopes.parquet", "flowpaths.parquet", "channels.parquet"]
    missing_parquets = [p for p in required_parquets if not (watershed_dir / p).exists()]
    
    if missing_parquets:
        return True, f"Missing parquet files: {', '.join(missing_parquets)} (skipped)"
    
    # Load watershed.nodb
    try:
        with open(watershed_nodb, 'r') as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        return False, f"Failed to read watershed.nodb: {e}"
    
    # The nodb format stores state under py/state for jsonpickle serialization
    state = data.get("py/state", data)
    
    # Track what we're changing
    changes = []
    
    # Check for legacy summary dictionaries
    legacy_keys = ["_subs_summary", "_fps_summary", "_chns_summary"]
    found_keys = [k for k in legacy_keys if k in state and state[k] is not None]
    
    # Check for inline _structure that needs to be externalized
    structure_pkl_path = watershed_dir / "structure.pkl"
    structure_data = state.get("_structure")
    needs_structure_migration = (
        structure_data is not None 
        and not isinstance(structure_data, str)  # Not already a path
        and not structure_pkl_path.exists()  # Pickle doesn't exist yet
    )
    
    if not found_keys and not needs_structure_migration:
        return True, "No legacy summaries or inline structure in watershed.nodb"
    
    # Calculate size savings
    original_size = len(json.dumps(data))
    
    if dry_run:
        msgs = []
        if found_keys:
            msgs.append(f"remove {len(found_keys)} legacy summary dict(s)")
        if needs_structure_migration:
            msgs.append("externalize _structure to structure.pkl")
        return True, f"Would {' and '.join(msgs)}"
    
    # Remove the legacy dictionaries (set to None to preserve schema)
    for key in found_keys:
        state[key] = None
        changes.append(f"removed {key}")
    
    # Externalize _structure to pickle file if needed
    if needs_structure_migration:
        try:
            # The structure data from JSON needs to be decoded via jsonpickle
            import jsonpickle
            structure_json = json.dumps(structure_data)
            structure_obj = jsonpickle.decode(structure_json)
            
            # Write to pickle file
            with open(structure_pkl_path, 'wb') as f:
                pickle.dump(structure_obj, f)
            
            # Update _structure to be the path string
            state["_structure"] = str(structure_pkl_path)
            changes.append("externalized _structure to structure.pkl")
        except Exception as e:
            # Non-fatal - structure migration can be skipped
            changes.append(f"_structure migration skipped: {e}")
    
    # Write updated watershed.nodb
    try:
        with open(watershed_nodb, 'w') as f:
            json.dump(data, f, indent=2)
    except OSError as e:
        return False, f"Failed to write watershed.nodb: {e}"
    
    # Calculate new size
    new_size = len(json.dumps(data))
    saved_mb = (original_size - new_size) / (1024 * 1024)
    
    return True, f"{', '.join(changes)}, saved {saved_mb:.1f} MB"


def migrate_wbt_geojson(wd: str, *, dry_run: bool = False) -> Tuple[bool, str]:
    """
    Normalize TopazID/WeppID in WhiteboxTools GeoJSON files.
    
    Idempotent: safe to run multiple times.
    
    Args:
        wd: Working directory path
        dry_run: If True, report but don't modify
        
    Returns:
        (applied, message) tuple
    """
    run_path = Path(wd)
    wbt_dir = run_path / "dem" / "wbt"
    
    if not wbt_dir.exists():
        return True, "No WBT directory (nothing to migrate)"
    
    target_files = [
        "channels.geojson",
        "channels.WGS.geojson",
        "subcatchments.geojson",
        "subcatchments.WGS.geojson",
    ]
    
    existing_files = [wbt_dir / f for f in target_files if (wbt_dir / f).exists()]
    if not existing_files:
        return True, "No WBT GeoJSON files (nothing to migrate)"
    
    def _coerce_int(value) -> Tuple[bool, Any]:
        try:
            ivalue = int(value)
        except (TypeError, ValueError):
            try:
                ivalue = int(str(value))
            except (TypeError, ValueError):
                return False, value
        return (ivalue != value), ivalue
    
    def _normalize_feature(props: Dict[str, Any]) -> bool:
        changed = False
        for key in ("TopazID", "WeppID", "Order"):
            if key in props:
                delta, coerced = _coerce_int(props[key])
                if delta:
                    props[key] = coerced
                    changed = True
        return changed
    
    total_changed = 0
    files_modified = 0
    
    for geojson_path in existing_files:
        try:
            with open(geojson_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        
        features = data.get("features", [])
        file_changed = False
        
        for feature in features:
            props = feature.get("properties") if isinstance(feature, dict) else None
            if isinstance(props, dict) and _normalize_feature(props):
                total_changed += 1
                file_changed = True
        
        if file_changed:
            files_modified += 1
            if not dry_run:
                with open(geojson_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, allow_nan=False)
    
    if total_changed == 0:
        return True, "WBT GeoJSON already normalized"
    
    action = "Would normalize" if dry_run else "Normalized"
    return True, f"{action} {total_changed} feature(s) in {files_modified} file(s)"


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
    landuse_parquet = run_path / "landuse" / "landuse.parquet"
    
    if not landuse_parquet.exists():
        return True, "No landuse parquet file (nothing to migrate)"
    
    try:
        import pyarrow.parquet as pq
        import pandas as pd
    except ImportError:
        return False, "PyArrow/Pandas not available"
    
    try:
        meta = pq.read_metadata(landuse_parquet)
        schema = meta.schema.to_arrow_schema()
        field_names = [f.name for f in schema]
    except Exception as e:
        return False, f"Failed to read parquet metadata: {e}"
    
    # Check if migration needed (has uppercase columns)
    # Note: wepp_id is optional - not all landuse files have it
    needs_migration = (
        "TopazID" in field_names or
        "WeppID" in field_names or
        ("topaz_id" not in field_names and "TopazID" not in field_names)
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
        
        # Ensure types
        if "topaz_id" in df.columns:
            df["topaz_id"] = df["topaz_id"].astype("Int32")
        if "wepp_id" in df.columns:
            df["wepp_id"] = df["wepp_id"].astype("Int32")
        
        # Drop uppercase columns
        df = df.drop(columns=["TopazID", "WeppID"], errors="ignore")
        
        # Write back
        df.to_parquet(landuse_parquet)
        return True, "Normalized landuse parquet schema"
    except Exception as e:
        return False, f"Failed to normalize landuse parquet: {e}"


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
    soils_parquet = run_path / "soils" / "soils.parquet"
    
    if not soils_parquet.exists():
        return True, "No soils parquet file (nothing to migrate)"
    
    try:
        import pyarrow.parquet as pq
        import pandas as pd
    except ImportError:
        return False, "PyArrow/Pandas not available"
    
    try:
        meta = pq.read_metadata(soils_parquet)
        schema = meta.schema.to_arrow_schema()
        field_names = [f.name for f in schema]
    except Exception as e:
        return False, f"Failed to read parquet metadata: {e}"
    
    # Check if migration needed (has uppercase columns)
    # Note: wepp_id is optional - not all soils files have it
    needs_migration = (
        "TopazID" in field_names or
        "WeppID" in field_names or
        ("topaz_id" not in field_names and "TopazID" not in field_names)
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
        
        # Ensure types
        if "topaz_id" in df.columns:
            df["topaz_id"] = df["topaz_id"].astype("Int32")
        if "wepp_id" in df.columns:
            df["wepp_id"] = df["wepp_id"].astype("Int32")
        
        # Drop uppercase columns
        df = df.drop(columns=["TopazID", "WeppID"], errors="ignore")
        
        # Write back
        df.to_parquet(soils_parquet)
        return True, "Normalized soils parquet schema"
    except Exception as e:
        return False, f"Failed to normalize soils parquet: {e}"


def invalidate_redis_cache(wd: str, *, dry_run: bool = False) -> Tuple[bool, str]:
    """
    Invalidate Redis DB 13 cache for all .nodb files in the working directory.
    
    NoDb instances are cached in Redis DB 13 with a 72-hour TTL. After migrations
    modify .nodb files on disk, the cache must be invalidated to prevent the
    Flask app from reading stale objects.
    
    Args:
        wd: Working directory path
        dry_run: If True, report what would be deleted but don't modify
        
    Returns:
        (applied, message) tuple
    """
    run_path = Path(wd)
    wd_abs = str(run_path.resolve())
    
    try:
        import redis
    except ImportError:
        return True, "Redis not available (cache invalidation skipped)"
    
    try:
        r = redis.Redis(host='redis', port=6379, db=13)
        r.ping()  # Verify connection
    except redis.ConnectionError:
        return True, "Redis not reachable (cache invalidation skipped)"
    except Exception as e:
        return True, f"Redis connection failed: {e} (cache invalidation skipped)"
    
    # Find all cached .nodb keys for this working directory
    pattern = f"{wd_abs}/*.nodb"
    keys = r.keys(pattern)
    
    if not keys:
        return True, "No cached .nodb files found in Redis"
    
    if dry_run:
        return True, f"Would invalidate {len(keys)} cached .nodb file(s) from Redis"
    
    # Delete all cached .nodb files
    deleted_count = 0
    for key in keys:
        try:
            r.delete(key)
            deleted_count += 1
        except Exception:
            pass  # Best effort
    
    return True, f"Invalidated {deleted_count} cached .nodb file(s) from Redis DB 13"


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
        activate_query_engine(str(run_path), run_interchange=False)
        return True, f"Refreshed query catalog ({len(parquet_files)} interchange files)"
    except Exception as e:
        # Non-fatal - catalog will be refreshed on first query
        return True, f"Catalog refresh deferred: {e}"


# Registry of available migrations in execution order
AVAILABLE_MIGRATIONS: List[Tuple[str, Callable[..., Tuple[bool, str]]]] = [
    ("observed_nodb", migrate_observed_nodb),
    ("run_paths", migrate_run_paths),
    ("watersheds", migrate_watersheds),
    ("watershed_nodb_slim", migrate_watershed_nodb_slim),  # After watersheds ensures parquets exist
    ("wbt_geojson", migrate_wbt_geojson),
    ("landuse_parquet", migrate_landuse_parquet),
    ("soils_parquet", migrate_soils_parquet),
    ("interchange", migrate_interchange),
    ("query_catalog", refresh_query_catalog),  # After interchange, before redis_cache
    ("redis_cache", invalidate_redis_cache),  # Always run last
]

# Human-readable descriptions for each migration
MIGRATION_DESCRIPTIONS: Dict[str, str] = {
    "observed_nodb": "Update observed.nodb module path for new package structure",
    "run_paths": "Fix hardcoded paths in .nodb files to match current location",
    "watersheds": "Generate parquet files for watershed data (hillslopes, channels, flowpaths)",
    "watershed_nodb_slim": "Slim watershed.nodb by externalizing structure data (reduces file size)",
    "wbt_geojson": "Normalize GeoJSON identifiers for WhiteboxTools delineation",
    "landuse_parquet": "Generate parquet files for landuse data",
    "soils_parquet": "Generate parquet files for soils data",
    "interchange": "Migrate WEPP interchange files to parquet format",
    "query_catalog": "Refresh query engine catalog for parquet files",
    "redis_cache": "Invalidate Redis cache for this run",
}


def check_migrations_needed(wd: str) -> Dict[str, Any]:
    """
    Check which migrations are needed for a working directory (dry run).
    
    Returns a dict with:
        - needs_migration: bool - True if any migration would make changes
        - migrations: list of dicts with name, description, would_apply, message
    """
    run_path = Path(wd)
    result = {
        "needs_migration": False,
        "migrations": [],
    }
    
    if not run_path.exists():
        return result
    
    # Migrations that are always informational (always run but never block loading)
    INFORMATIONAL_MIGRATIONS = {"redis_cache", "query_catalog", "interchange"}
    
    # Keywords that indicate no actual work needed
    NO_WORK_KEYWORDS = [
        "Already", 
        "already", 
        "No ", 
        "No ", 
        "nothing to migrate",
        "no legacy", 
        "skipped",
        "not found",
        "not available",
    ]
    
    # Check each migration with dry_run=True
    for name, migrate_fn in AVAILABLE_MIGRATIONS:
        try:
            applied, message = migrate_fn(wd, dry_run=True)
            
            # Informational migrations never require user action
            if name in INFORMATIONAL_MIGRATIONS:
                would_apply = False
            else:
                # Check if this migration indicates actual work is needed
                would_apply = applied and "Would " in message
                
                # Also check for keywords indicating no work needed
                for keyword in NO_WORK_KEYWORDS:
                    if keyword in message:
                        would_apply = False
                        break
            
            if would_apply:
                result["needs_migration"] = True
            
            result["migrations"].append({
                "name": name,
                "description": MIGRATION_DESCRIPTIONS.get(name, ""),
                "would_apply": would_apply,
                "message": message,
            })
        except Exception as e:
            result["migrations"].append({
                "name": name,
                "description": MIGRATION_DESCRIPTIONS.get(name, ""),
                "would_apply": False,
                "message": f"Error checking: {e}",
                "error": True,
            })
    
    return result


def run_all_migrations(
    wd: str,
    *,
    dry_run: bool = False,
    migrations: Optional[List[str]] = None,
    on_progress: Optional[Callable[[str, str], None]] = None,
) -> MigrationResult:
    """
    Run all applicable migrations on a single working directory.
    
    Args:
        wd: Working directory path
        dry_run: If True, check but don't modify
        migrations: Optional list of migration names to run (defaults to all)
        on_progress: Optional callback(migration_name, message) for progress updates
        
    Returns:
        MigrationResult with details of what was applied/skipped/failed
    """
    result = MigrationResult(wd=wd)
    run_path = Path(wd)
    
    if not run_path.exists():
        result.success = False
        result.errors["validation"] = f"Directory not found: {wd}"
        result.completed_at = datetime.now(timezone.utc)
        return result
    
    if not _is_valid_run_directory(run_path):
        result.success = False
        result.errors["validation"] = f"Not a valid run directory (no .nodb files): {wd}"
        result.completed_at = datetime.now(timezone.utc)
        return result
    
    # Filter migrations if specific ones requested
    to_run = AVAILABLE_MIGRATIONS
    if migrations:
        migrations_set = set(migrations)
        to_run = [(name, fn) for name, fn in AVAILABLE_MIGRATIONS if name in migrations_set]
    
    for name, migrate_fn in to_run:
        if on_progress:
            on_progress(name, f"Running migration: {name}")
        
        try:
            applied, message = migrate_fn(wd, dry_run=dry_run)
            
            if applied:
                result.applied.append(name)
            else:
                result.skipped.append(name)
            
            if on_progress:
                status = "applied" if applied else "skipped"
                on_progress(name, f"{name}: {status} - {message}")
                
        except Exception as e:
            result.success = False
            result.errors[name] = str(e)
            if on_progress:
                on_progress(name, f"{name}: ERROR - {e}")
    
    result.completed_at = datetime.now(timezone.utc)
    return result
