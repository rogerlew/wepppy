"""
Migration utilities for WEPPcloud run directories.

This package provides idempotent migration scripts that normalize legacy run
assets to current schemas and formats.

Usage:
    # Run all migrations on a working directory
    python -m wepppy.tools.migrations.run_migrations /path/to/run

    # Import the runner programmatically
    from wepppy.tools.migrations.runner import run_all_migrations
    result = run_all_migrations("/path/to/run")
"""

from wepppy.tools.migrations.runner import (
    MigrationResult,
    run_all_migrations,
    migrate_observed_nodb,
    migrate_run_paths,
    migrate_interchange,
    migrate_watersheds,
    migrate_wbt_geojson,
    migrate_landuse_parquet,
    migrate_soils_parquet,
    migrate_soils_nodb_meta,
    AVAILABLE_MIGRATIONS,
)

__all__ = [
    "MigrationResult",
    "run_all_migrations",
    "migrate_observed_nodb",
    "migrate_run_paths",
    "migrate_interchange",
    "migrate_watersheds",
    "migrate_wbt_geojson",
    "migrate_landuse_parquet",
    "migrate_soils_parquet",
    "migrate_soils_nodb_meta",
    "AVAILABLE_MIGRATIONS",
]
