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

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from wepppy.nodb.version import CURRENT_VERSION, read_version
from wepppy.tools.migrations.cache import invalidate_redis_cache
from wepppy.tools.migrations.interchange import migrate_interchange, refresh_query_catalog
from wepppy.tools.migrations.landuse import migrate_landuse_parquet
from wepppy.tools.migrations.nodb import (
    migrate_nodb_jsonpickle_format,
    migrate_observed_nodb,
    migrate_run_paths,
)
from wepppy.tools.migrations.soils import (
    migrate_soils_dir_paths,
    migrate_soils_nodb_meta,
    migrate_soils_parquet,
)
from wepppy.tools.migrations.watershed import (
    migrate_watershed_nodb_slim,
    migrate_watersheds,
    migrate_wbt_geojson,
)

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
    "migrate_soils_nodb_meta",
    "migrate_soils_dir_paths",
    "migrate_nodb_jsonpickle_format",
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


# Registry of available migrations in execution order
AVAILABLE_MIGRATIONS: List[Tuple[str, Callable[..., Tuple[bool, str]]]] = [
    ("observed_nodb", migrate_observed_nodb),
    ("run_paths", migrate_run_paths),
    ("nodb_jsonpickle_format", migrate_nodb_jsonpickle_format),  # After run_paths, before other nodb operations
    ("watersheds", migrate_watersheds),
    ("watershed_nodb_slim", migrate_watershed_nodb_slim),  # After watersheds ensures parquets exist
    ("wbt_geojson", migrate_wbt_geojson),
    ("landuse_parquet", migrate_landuse_parquet),
    ("soils_parquet", migrate_soils_parquet),
    ("soils_nodb_meta", migrate_soils_nodb_meta),
    ("soils_dir_paths", migrate_soils_dir_paths),  # After soils_nodb_meta, fixes relative paths
    ("interchange", migrate_interchange),
    ("query_catalog", refresh_query_catalog),  # After interchange, before redis_cache
    ("redis_cache", invalidate_redis_cache),  # Always run last
]

# Human-readable descriptions for each migration
MIGRATION_DESCRIPTIONS: Dict[str, str] = {
    "nodb_version": "Update NoDb schema version marker",
    "observed_nodb": "Update observed.nodb module path for new package structure",
    "run_paths": "Fix hardcoded paths in .nodb files to match current location",
    "nodb_jsonpickle_format": "Convert old flat jsonpickle format to new py/state format",
    "watersheds": "Generate parquet files for watershed data (hillslopes, channels, flowpaths)",
    "watershed_nodb_slim": "Slim watershed.nodb by externalizing structure data (reduces file size)",
    "wbt_geojson": "Normalize GeoJSON identifiers for WhiteboxTools delineation",
    "landuse_parquet": "Generate parquet files for landuse data",
    "soils_parquet": "Generate parquet files for soils data",
    "soils_nodb_meta": "Clear legacy _meta_fn attributes from soils.nodb (fixes numpy deserialization)",
    "soils_dir_paths": "Fix relative soils_dir paths in soils.nodb to use absolute paths",
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

    nodb_version = read_version(run_path)
    version_outdated = nodb_version < CURRENT_VERSION

    result.update(
        {
            "nodb_version": nodb_version,
            "current_version": CURRENT_VERSION,
            "version_outdated": version_outdated,
        }
    )

    version_message = (
        f"NoDb schema version {nodb_version} is below current {CURRENT_VERSION}"
        if version_outdated
        else f"NoDb schema version {nodb_version} is current"
    )
    result["migrations"].append(
        {
            "name": "nodb_version",
            "description": MIGRATION_DESCRIPTIONS.get("nodb_version", ""),
            "would_apply": version_outdated,
            "message": version_message,
        }
    )
    if version_outdated:
        result["needs_migration"] = True

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

            # Informational migrations never require user action (unless they explicitly
            # return applied=False indicating work is needed)
            if name in INFORMATIONAL_MIGRATIONS and applied:
                would_apply = False
            else:
                # Check if this migration indicates actual work is needed
                # applied=False means migration was NOT skipped (i.e., work needed)
                # applied=True with "Would" means work would happen
                would_apply = (not applied) or (applied and "Would " in message)

                # Also check for keywords indicating no work needed
                for keyword in NO_WORK_KEYWORDS:
                    if keyword in message:
                        would_apply = False
                        break

            if would_apply:
                result["needs_migration"] = True

            result["migrations"].append(
                {
                    "name": name,
                    "description": MIGRATION_DESCRIPTIONS.get(name, ""),
                    "would_apply": would_apply,
                    "message": message,
                }
            )
        except Exception as exc:
            result["migrations"].append(
                {
                    "name": name,
                    "description": MIGRATION_DESCRIPTIONS.get(name, ""),
                    "would_apply": False,
                    "message": f"Error checking: {exc}",
                    "error": True,
                }
            )

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

        except Exception as exc:
            result.success = False
            result.errors[name] = str(exc)
            if on_progress:
                on_progress(name, f"{name}: ERROR - {exc}")

    result.completed_at = datetime.now(timezone.utc)
    return result
