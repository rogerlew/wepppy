"""Type stubs for wepppy.tools.migrations.runner."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

@dataclass
class MigrationResult:
    wd: str
    success: bool
    applied: List[str]
    skipped: List[str]
    errors: Dict[str, str]
    started_at: datetime
    completed_at: Optional[datetime]
    
    def to_dict(self) -> Dict[str, Any]: ...

def migrate_observed_nodb(wd: str, *, dry_run: bool = ...) -> Tuple[bool, str]: ...
def migrate_run_paths(
    wd: str,
    *,
    old_prefix: str = ...,
    new_prefix: str = ...,
    dry_run: bool = ...,
) -> Tuple[bool, str]: ...
def migrate_interchange(wd: str, *, force: bool = ..., dry_run: bool = ...) -> Tuple[bool, str]: ...
def migrate_watersheds(wd: str, *, dry_run: bool = ..., keep_csv: bool = ...) -> Tuple[bool, str]: ...
def migrate_wbt_geojson(wd: str, *, dry_run: bool = ...) -> Tuple[bool, str]: ...
def migrate_landuse_parquet(wd: str, *, dry_run: bool = ...) -> Tuple[bool, str]: ...
def migrate_soils_parquet(wd: str, *, dry_run: bool = ...) -> Tuple[bool, str]: ...

AVAILABLE_MIGRATIONS: List[Tuple[str, Callable[..., Tuple[bool, str]]]]

def run_all_migrations(
    wd: str,
    *,
    dry_run: bool = ...,
    migrations: Optional[List[str]] = ...,
    on_progress: Optional[Callable[[str, str], None]] = ...,
) -> MigrationResult: ...
