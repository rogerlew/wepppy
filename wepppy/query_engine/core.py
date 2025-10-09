from __future__ import annotations

from pathlib import Path

from wepppy.query_engine.catalog import DatasetCatalog
from wepppy.query_engine.context import RunContext
from wepppy.query_engine.executor import DuckDBExecutor
from wepppy.query_engine.formatter import QueryResult, format_table
from wepppy.query_engine.payload import QueryPlan, QueryRequest


def build_query_plan(payload: QueryRequest, catalog: DatasetCatalog) -> QueryPlan:
    if not payload.datasets:
        raise ValueError("At least one dataset must be specified")

    dataset = payload.datasets[0]
    entry = catalog.get(dataset)
    if entry is None:
        raise ValueError(f"Dataset {dataset} not found")

    columns = payload.columns or ["*"]
    source_path = (catalog.root / Path(dataset)).as_posix()
    sql = f"SELECT {', '.join(columns)} FROM read_parquet('{source_path}')"
    if payload.limit:
        sql += f" LIMIT {payload.limit}"
    return QueryPlan(sql=sql, params=[])


def run_query(run_context: RunContext, payload: QueryRequest) -> QueryResult:
    plan = build_query_plan(payload, run_context.catalog)
    executor = DuckDBExecutor(run_context.base_dir)
    table = executor.execute(plan.sql, plan.params, use_spatial=plan.requires_spatial)
    return format_table(table, include_schema=payload.include_schema)
