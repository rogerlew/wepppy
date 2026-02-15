from __future__ import annotations

from pathlib import Path

def activate_query_engine(
    wd: str | Path,
    *,
    run_interchange: bool = ...,
    force_refresh: bool = ...,
) -> dict[str, object]: ...

def update_catalog_entry(wd: str | Path, asset_path: str) -> dict[str, object] | None: ...
