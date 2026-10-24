from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .catalog import DatasetCatalog
from .context import RunContext
from .formatter import QueryResult
from .payload import QueryPlan, QueryRequest

def build_query_plan(payload: QueryRequest, catalog: DatasetCatalog) -> QueryPlan: ...

def run_query(run_context: RunContext, payload: QueryRequest, *, authorize: Callable[[RunContext], None] | None = None) -> QueryResult: ...

def _find_parent_run_root(base: Path) -> Path | None: ...

def _resolve_dataset_path(root: Path, fs_path: str, logical_path: str) -> Path: ...
