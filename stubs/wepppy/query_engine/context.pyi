from __future__ import annotations

from pathlib import Path

from .catalog import DatasetCatalog

class RunContext:
    runid: str
    base_dir: Path
    scenario: str | None
    catalog: DatasetCatalog

def resolve_run_context(
    runid: str,
    *,
    scenario: str | None = ...,
    auto_activate: bool = ...,
    run_interchange: bool = ...,
    force_refresh: bool = ...,
) -> RunContext: ...
