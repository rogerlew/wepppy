from __future__ import annotations

from pathlib import Path
from collections.abc import Callable, Iterable

from .context import RunContext
from .formatter import QueryResult
from .payload import QueryRequest

def activate_query_engine(
    wd: str | Path,
    *,
    run_interchange: bool = ...,
    force_refresh: bool = ...,
    mutation_checkpoint: Callable[[], None] | None = ...,
) -> dict[str, object]: ...

def update_catalog_entry(wd: str | Path, asset_path: str) -> dict[str, object] | None: ...

def resolve_run_context(
    runid: str,
    *,
    scenario: str | None = ...,
    auto_activate: bool = ...,
    run_interchange: bool = ...,
    force_refresh: bool = ...,
) -> RunContext: ...

def run_query(run_context: RunContext, payload: QueryRequest, *, authorize: Callable[[RunContext], None] | None = None) -> QueryResult: ...

def request_catalog_refresh(wd: str | Path, asset_path: str | None = ...) -> dict[str, object]: ...

def ensure_catalog_fresh(wd: str | Path, required_paths: Iterable[str] | None = ...) -> dict[str, object]: ...
