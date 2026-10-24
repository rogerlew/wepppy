from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from collections.abc import Iterable

from .catalog import DatasetCatalog

@dataclass(slots=True)
class RunContext:
    runid: str
    base_dir: Path
    scenario: str | None
    catalog: DatasetCatalog

def refresh_run_context(context: RunContext, required_paths: Iterable[str] | None = ...) -> RunContext: ...

def resolve_run_context(
    runid: str,
    *,
    scenario: str | None = ...,
    auto_activate: bool = ...,
    run_interchange: bool = ...,
    force_refresh: bool = ...,
) -> RunContext: ...
