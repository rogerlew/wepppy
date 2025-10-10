from __future__ import annotations

from pathlib import Path

from wepppy.query_engine.catalog import DatasetCatalog
from wepppy.query_engine.context import RunContext
from wepppy.query_engine.executor import DuckDBExecutor
from wepppy.query_engine.formatter import QueryResult, format_table
from wepppy.query_engine.payload import DatasetSpec, JoinSpec, QueryPlan, QueryRequest


def _escape_sql_literal(value: str) -> str:
    return value.replace("'", "''")


def _dataset_source_sql(root: Path, spec: DatasetSpec) -> str:
    source_path = (root / Path(spec.path)).as_posix()
    escaped = _escape_sql_literal(source_path)
    return f"read_parquet('{escaped}') AS {spec.alias}"


def _build_join_clause(
    join_spec: JoinSpec,
    alias_to_spec: dict[str, DatasetSpec],
    used_aliases: set[str],
    root: Path,
) -> tuple[str, str]:
    if join_spec.left not in used_aliases:
        raise ValueError(f"Join references alias '{join_spec.left}' before it appears in the FROM clause")
    if join_spec.right not in alias_to_spec:
        raise ValueError(f"Join references unknown alias '{join_spec.right}'")
    if join_spec.right in used_aliases:
        raise ValueError(f"Join alias '{join_spec.right}' referenced multiple times in join list")

    right_spec = alias_to_spec[join_spec.right]
    join_source = _dataset_source_sql(root, right_spec)
    used_aliases.add(join_spec.right)

    conditions = [
        f"{join_spec.left}.{left_col} = {join_spec.right}.{right_col}"
        for left_col, right_col in zip(join_spec.left_on, join_spec.right_on)
    ]
    condition_sql = " AND ".join(conditions)
    join_clause = f"{join_spec.join_type} JOIN {join_source} ON {condition_sql}"
    return join_clause, join_spec.right


def build_query_plan(payload: QueryRequest, catalog: DatasetCatalog) -> QueryPlan:
    dataset_specs = payload.dataset_specs
    if not dataset_specs:
        raise ValueError("At least one dataset must be specified")

    catalog_root = catalog.root if isinstance(catalog.root, Path) else Path(catalog.root)

    alias_to_spec = {spec.alias: spec for spec in dataset_specs}
    missing_paths = [spec.path for spec in dataset_specs if not catalog.has(spec.path)]
    if missing_paths:
        raise FileNotFoundError(missing_paths[0])

    base_spec = dataset_specs[0]
    from_clause = _dataset_source_sql(catalog_root, base_spec)
    used_aliases = {base_spec.alias}

    join_clauses: list[str] = []
    for join_spec in payload.join_specs:
        clause, _ = _build_join_clause(join_spec, alias_to_spec, used_aliases, catalog_root)
        join_clauses.append(clause)

    if used_aliases != set(alias_to_spec):
        missing_aliases = sorted(set(alias_to_spec) - used_aliases)
        raise ValueError(f"No join specified for dataset alias(es): {', '.join(missing_aliases)}")

    select_parts: list[str] = []
    group_by = payload.group_by or []

    if payload.columns:
        select_parts.extend(payload.columns)
    elif group_by:
        select_parts.extend(group_by)
    else:
        select_parts.extend([])

    for aggregation in payload.aggregation_specs:
        expression = aggregation.sql
        if aggregation.alias:
            select_parts.append(f"{expression} AS {aggregation.alias}")
        else:
            select_parts.append(expression)

    if not select_parts:
        select_parts.append("*")

    select_sql = ", ".join(select_parts)
    sql_parts = [f"SELECT {select_sql}", "FROM", from_clause]
    if join_clauses:
        sql_parts.extend(join_clauses)

    if group_by and payload.aggregation_specs:
        group_by_sql = ", ".join(group_by)
        sql_parts.append(f"GROUP BY {group_by_sql}")

    sql = " ".join(sql_parts)

    if payload.limit:
        sql += f" LIMIT {payload.limit}"
    return QueryPlan(sql=sql, params=[])


def run_query(run_context: RunContext, payload: QueryRequest) -> QueryResult:
    plan = build_query_plan(payload, run_context.catalog)
    executor = DuckDBExecutor(run_context.base_dir)
    table = executor.execute(plan.sql, plan.params, use_spatial=plan.requires_spatial)
    return format_table(table, include_schema=payload.include_schema)
