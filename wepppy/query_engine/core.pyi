from __future__ import annotations

from .catalog import DatasetCatalog
from .context import RunContext
from .formatter import QueryResult
from .payload import QueryPlan, QueryRequest

def build_query_plan(payload: QueryRequest, catalog: DatasetCatalog) -> QueryPlan: ...

def run_query(run_context: RunContext, payload: QueryRequest) -> QueryResult: ...
