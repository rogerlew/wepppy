from __future__ import annotations

import re
from pathlib import Path

from wepppy.query_engine.catalog import DatasetCatalog
from wepppy.query_engine.context import RunContext
from wepppy.query_engine.executor import DuckDBExecutor
from wepppy.query_engine.formatter import QueryResult, format_table
from wepppy.query_engine.payload import DatasetSpec, JoinSpec, QueryPlan, QueryRequest


_GEO_READ_EXTENSIONS = {".geojson", ".fgb", ".gpkg", ".shp"}


def _escape_sql_literal(value: str) -> str:
    return value.replace("'", "''")


def _format_value(value: object) -> str:
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    return f"'{_escape_sql_literal(str(value))}'"


def _coerce_filter_value(value: object, column_type: str | None, *, operator: str) -> object:
    if column_type is None:
        return value

    normalized = column_type.lower()

    if operator in {"LIKE", "ILIKE"}:
        return str(value)

    try:
        if any(name in normalized for name in ("int", "long")):
            return int(value)
        if any(name in normalized for name in ("float", "double", "real", "decimal")):
            return float(value)
        if "bool" in normalized:
            if isinstance(value, bool):
                return value
            text = str(value).strip().lower()
            if text in {"true", "t", "1", "yes"}:
                return True
            if text in {"false", "f", "0", "no"}:
                return False
            raise ValueError(f"Cannot coerce '{value}' to boolean")
        # default to string for utf8 or unknown types
        return str(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Unable to coerce filter value '{value}' to type '{column_type}'") from exc


def _dataset_source_sql(root: Path, spec: DatasetSpec) -> tuple[str, bool]:
    dataset_path = root / Path(spec.path)
    source_path = dataset_path.as_posix()
    escaped = _escape_sql_literal(source_path)
    suffix = dataset_path.suffix.lower()

    if suffix in _GEO_READ_EXTENSIONS:
        reader = f"ST_Read('{escaped}')"
        requires_spatial = True
    else:
        reader = f"read_parquet('{escaped}')"
        requires_spatial = False

    return f"{reader} AS {spec.alias}", requires_spatial


_SIMPLE_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _qualify_join_column(alias: str, column: str) -> str:
    """Return a qualified column suitable for a join condition."""
    column = column.strip()
    if not column:
        raise ValueError("Join column name cannot be empty")

    if "." in column:
        # Assume already qualified or expression-based; leave unchanged.
        return column

    if column.startswith('"') and column.endswith('"'):
        return f"{alias}.{column}"

    if _SIMPLE_IDENTIFIER_RE.match(column):
        return f"{alias}.{column}"

    escaped = column.replace('"', '""')
    return f'{alias}."{escaped}"'


def _build_join_clause(
    join_spec: JoinSpec,
    alias_to_spec: dict[str, DatasetSpec],
    used_aliases: set[str],
    root: Path,
) -> tuple[str, str, bool]:
    if join_spec.left not in used_aliases:
        raise ValueError(f"Join references alias '{join_spec.left}' before it appears in the FROM clause")
    if join_spec.right not in alias_to_spec:
        raise ValueError(f"Join references unknown alias '{join_spec.right}'")
    if join_spec.right in used_aliases:
        raise ValueError(f"Join alias '{join_spec.right}' referenced multiple times in join list")

    right_spec = alias_to_spec[join_spec.right]
    join_source, requires_spatial = _dataset_source_sql(root, right_spec)
    used_aliases.add(join_spec.right)

    conditions = [
        f"{_qualify_join_column(join_spec.left, left_col)} = {_qualify_join_column(join_spec.right, right_col)}"
        for left_col, right_col in zip(join_spec.left_on, join_spec.right_on)
    ]
    condition_sql = " AND ".join(conditions)
    join_clause = f"{join_spec.join_type} JOIN {join_source} ON {condition_sql}"
    return join_clause, join_spec.right, requires_spatial


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
    from_clause, requires_spatial = _dataset_source_sql(catalog_root, base_spec)
    used_aliases = {base_spec.alias}

    join_clauses: list[str] = []
    for join_spec in payload.join_specs:
        clause, _, join_requires_spatial = _build_join_clause(join_spec, alias_to_spec, used_aliases, catalog_root)
        join_clauses.append(clause)
        requires_spatial = requires_spatial or join_requires_spatial

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

    for computed in payload.computed_column_specs:
        select_parts.append(f"{computed.sql} AS {computed.alias}")

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

    if payload.filters:
        filter_clauses = []
        for filt in payload.filters:
            column = filt["column"]
            operator = filt["operator"]
            value = filt.get("value")

            if "." in column:
                alias_part, column_name = column.split(".", 1)
            else:
                alias_part, column_name = base_spec.alias, column

            if alias_part not in alias_to_spec:
                raise ValueError(f"Filter references unknown dataset alias '{alias_part}'")
            dataset_spec = alias_to_spec[alias_part]
            column_type = catalog.get_column_type(dataset_spec.path, column_name)

            if operator in {"IS NULL", "IS NOT NULL"}:
                filter_clauses.append(f"{column} {operator}")
                continue

            if operator == "BETWEEN":
                low, high = value  # type: ignore
                low_cast = _coerce_filter_value(low, column_type, operator=operator)
                high_cast = _coerce_filter_value(high, column_type, operator=operator)
                filter_clauses.append(
                    f"{column} BETWEEN {_format_value(low_cast)} AND {_format_value(high_cast)}"
                )
                continue

            if operator in {"IN", "NOT IN"}:
                values = value  # type: ignore
                cast_values = [
                    _format_value(_coerce_filter_value(item, column_type, operator=operator))
                    for item in values
                ]
                filter_clauses.append(f"{column} {operator} ({', '.join(cast_values)})")
                continue

            typed_value = _coerce_filter_value(value, column_type, operator=operator)
            formatted_value = _format_value(typed_value)
            filter_clauses.append(f"{column} {operator} {formatted_value}")

        sql_parts.append("WHERE " + " AND ".join(filter_clauses))

    if payload.order_by:
        order_by_sql = ", ".join(payload.order_by)
        sql_parts.append(f"ORDER BY {order_by_sql}")

    sql = " ".join(sql_parts)

    if payload.limit:
        sql += f" LIMIT {payload.limit}"
    return QueryPlan(sql=sql, params=[], requires_spatial=requires_spatial)


def run_query(run_context: RunContext, payload: QueryRequest) -> QueryResult:
    plan = build_query_plan(payload, run_context.catalog)
    executor = DuckDBExecutor(run_context.base_dir)
    table = executor.execute(plan.sql, plan.params, use_spatial=plan.requires_spatial)
    return format_table(
        table,
        include_schema=payload.include_schema,
        sql=plan.sql if payload.include_sql else None,
        reshape=payload.reshape_spec,
    )
