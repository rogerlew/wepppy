from __future__ import annotations

from pathlib import Path

from .context import RunContext
from .formatter import QueryResult
from .payload import QueryRequest

def activate_query_engine(wd: str | Path, *, run_interchange: bool = ...) -> dict[str, object]: ...

def update_catalog_entry(wd: str | Path, asset_path: str) -> dict[str, object] | None: ...

def resolve_run_context(runid: str, *, scenario: str | None = ..., auto_activate: bool = ...) -> RunContext: ...

def run_query(run_context: RunContext, payload: QueryRequest) -> QueryResult: ...
