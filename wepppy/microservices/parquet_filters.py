"""Shared parquet filter payload parsing, validation, and execution helpers."""

from __future__ import annotations

import base64
import binascii
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


MAX_FILTER_DEPTH = 6
MAX_FILTER_NODES = 50
MAX_FILTER_FIELD_LEN = 128
MAX_FILTER_VALUE_LEN = 512

_ALLOWED_GROUP_LOGIC = frozenset({"AND", "OR"})
_ALLOWED_OPERATORS = frozenset({"Equals", "NotEquals", "Contains", "GreaterThan", "LessThan"})


@dataclass(frozen=True)
class CompiledParquetFilter:
    """Prepared SQL filter fragment with positional parameters."""

    normalized_tree: dict[str, Any]
    where_sql: str
    params: tuple[Any, ...]
    summary: str


@dataclass(frozen=True)
class ParquetFilterError(ValueError):
    """Structured filter error for browse/download/D-Tale surfaces."""

    message: str
    code: str = "validation_error"
    status_code: int = 422
    node_path: str | None = None
    details: str | None = None

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "error": {
                "message": self.message,
                "code": self.code,
                "details": self.details or self.message,
            }
        }
        if self.node_path:
            payload["errors"] = [
                {
                    "code": self.code,
                    "message": self.message,
                    "path": self.node_path,
                }
            ]
        return payload


def _quote_identifier(name: str) -> str:
    escaped = name.replace('"', '""')
    return f'"{escaped}"'


def _decode_payload_bytes(raw: str) -> bytes:
    padded = raw + ("=" * (-len(raw) % 4))
    try:
        return base64.urlsafe_b64decode(padded.encode("ascii"))
    except (UnicodeEncodeError, ValueError, binascii.Error) as exc:
        raise ParquetFilterError(
            "Invalid parquet filter payload.",
            node_path="pqf",
            details="Payload must be base64url-encoded JSON.",
        ) from exc


def decode_filter_payload(raw: str | None) -> dict[str, Any] | None:
    """Decode ``pqf`` payload into a JSON object tree."""

    if raw is None:
        return None
    trimmed = raw.strip()
    if not trimmed:
        return None

    decoded = _decode_payload_bytes(trimmed)
    try:
        parsed = json.loads(decoded.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ParquetFilterError(
            "Invalid parquet filter payload.",
            node_path="pqf",
            details="Payload must decode to a JSON object.",
        ) from exc

    if not isinstance(parsed, dict):
        raise ParquetFilterError(
            "Invalid parquet filter payload.",
            node_path="pqf",
            details="Root filter node must be an object.",
        )

    return parsed


def _validate_expected_keys(node: dict[str, Any], expected: set[str], *, node_path: str) -> None:
    extra_keys = sorted(set(node.keys()) - expected)
    if extra_keys:
        raise ParquetFilterError(
            "Invalid parquet filter payload.",
            node_path=node_path,
            details=f"Unexpected keys: {', '.join(extra_keys)}",
        )


def _validate_condition(
    node: dict[str, Any],
    *,
    node_path: str,
    field_max_len: int,
    value_max_len: int,
) -> dict[str, Any]:
    _validate_expected_keys(node, {"kind", "field", "operator", "value"}, node_path=node_path)

    field = node.get("field")
    if not isinstance(field, str) or not field.strip():
        raise ParquetFilterError(
            "Invalid parquet filter payload.",
            node_path=f"{node_path}.field",
            details="Condition field must be a non-empty string.",
        )
    field = field.strip()
    if len(field) > field_max_len:
        raise ParquetFilterError(
            "Invalid parquet filter payload.",
            node_path=f"{node_path}.field",
            details=f"Condition field exceeds max length ({field_max_len}).",
        )

    operator = node.get("operator")
    if not isinstance(operator, str) or operator not in _ALLOWED_OPERATORS:
        raise ParquetFilterError(
            "Invalid parquet filter payload.",
            node_path=f"{node_path}.operator",
            details=(
                "Condition operator must be one of: "
                + ", ".join(sorted(_ALLOWED_OPERATORS))
            ),
        )

    value = node.get("value")
    if not isinstance(value, str):
        raise ParquetFilterError(
            "Invalid parquet filter payload.",
            node_path=f"{node_path}.value",
            details="Condition value must be a string.",
        )
    if len(value) > value_max_len:
        raise ParquetFilterError(
            "Invalid parquet filter payload.",
            node_path=f"{node_path}.value",
            details=f"Condition value exceeds max length ({value_max_len}).",
        )

    return {
        "kind": "condition",
        "field": field,
        "operator": operator,
        "value": value,
    }


def _validate_node(
    node: Any,
    *,
    depth: int,
    counter: list[int],
    node_path: str,
    max_depth: int,
    max_nodes: int,
    field_max_len: int,
    value_max_len: int,
) -> dict[str, Any]:
    if not isinstance(node, dict):
        raise ParquetFilterError(
            "Invalid parquet filter payload.",
            node_path=node_path,
            details="Each filter node must be an object.",
        )

    if depth > max_depth:
        raise ParquetFilterError(
            "Invalid parquet filter payload.",
            node_path=node_path,
            details=f"Filter tree exceeds max depth ({max_depth}).",
        )

    counter[0] += 1
    if counter[0] > max_nodes:
        raise ParquetFilterError(
            "Invalid parquet filter payload.",
            node_path=node_path,
            details=f"Filter tree exceeds max node count ({max_nodes}).",
        )

    kind = node.get("kind")
    if kind == "group":
        _validate_expected_keys(node, {"kind", "logic", "children"}, node_path=node_path)
        logic = node.get("logic")
        if not isinstance(logic, str):
            raise ParquetFilterError(
                "Invalid parquet filter payload.",
                node_path=f"{node_path}.logic",
                details="Group logic must be a string.",
            )
        logic_normalized = logic.strip().upper()
        if logic_normalized not in _ALLOWED_GROUP_LOGIC:
            raise ParquetFilterError(
                "Invalid parquet filter payload.",
                node_path=f"{node_path}.logic",
                details="Group logic must be AND or OR.",
            )

        children = node.get("children")
        if not isinstance(children, list) or not children:
            raise ParquetFilterError(
                "Invalid parquet filter payload.",
                node_path=f"{node_path}.children",
                details="Group node must contain at least one child node.",
            )

        normalized_children = [
            _validate_node(
                child,
                depth=depth + 1,
                counter=counter,
                node_path=f"{node_path}.children[{idx}]",
                max_depth=max_depth,
                max_nodes=max_nodes,
                field_max_len=field_max_len,
                value_max_len=value_max_len,
            )
            for idx, child in enumerate(children)
        ]
        return {
            "kind": "group",
            "logic": logic_normalized,
            "children": normalized_children,
        }

    if kind == "condition":
        return _validate_condition(
            node,
            node_path=node_path,
            field_max_len=field_max_len,
            value_max_len=value_max_len,
        )

    raise ParquetFilterError(
        "Invalid parquet filter payload.",
        node_path=f"{node_path}.kind",
        details="Node kind must be either 'group' or 'condition'.",
    )


def validate_filter_tree(
    node: dict[str, Any],
    *,
    max_depth: int = MAX_FILTER_DEPTH,
    max_nodes: int = MAX_FILTER_NODES,
    field_max_len: int = MAX_FILTER_FIELD_LEN,
    value_max_len: int = MAX_FILTER_VALUE_LEN,
) -> dict[str, Any]:
    """Validate and normalize a filter tree."""

    counter = [0]
    return _validate_node(
        node,
        depth=1,
        counter=counter,
        node_path="$",
        max_depth=max_depth,
        max_nodes=max_nodes,
        field_max_len=field_max_len,
        value_max_len=value_max_len,
    )


def _is_numeric_type(data_type: pa.DataType) -> bool:
    return (
        pa.types.is_integer(data_type)
        or pa.types.is_floating(data_type)
        or pa.types.is_decimal(data_type)
    )


def _compile_condition(
    node: dict[str, Any],
    schema_fields: dict[str, pa.Field],
    *,
    node_path: str,
) -> tuple[str, list[Any], str]:
    field_name = node["field"]
    field = schema_fields.get(field_name)
    if field is None:
        raise ParquetFilterError(
            "Unknown parquet filter field.",
            node_path=f"{node_path}.field",
            details=f"Field '{field_name}' does not exist in the parquet schema.",
        )

    quoted = _quote_identifier(field_name)
    operator = node["operator"]
    value = node["value"]

    if operator in {"Equals", "NotEquals"}:
        comparator = "=" if operator == "Equals" else "!="
        if _is_numeric_type(field.type):
            try:
                numeric_value = float(value)
            except ValueError as exc:
                raise ParquetFilterError(
                    "Invalid parquet filter value.",
                    node_path=f"{node_path}.value",
                    details=(
                        f"Value '{value}' must be numeric for operator '{operator}' "
                        f"on field '{field_name}'."
                    ),
                ) from exc
            if not math.isfinite(numeric_value):
                raise ParquetFilterError(
                    "Invalid parquet filter value.",
                    node_path=f"{node_path}.value",
                    details="Numeric filter values must be finite (not NaN/inf).",
                )

            cast_expr = f"TRY_CAST({quoted} AS DOUBLE)"
            sql = (
                f"({cast_expr} IS NOT NULL AND NOT isnan({cast_expr}) "
                f"AND {cast_expr} {comparator} ?)"
            )
            return sql, [numeric_value], f"{field_name} {comparator} {numeric_value}"

        return (
            f"CAST({quoted} AS VARCHAR) {comparator} ?",
            [value],
            f"{field_name} {comparator} '{value}'",
        )

    if operator == "Contains":
        return (
            f"INSTR(LOWER(CAST({quoted} AS VARCHAR)), LOWER(?)) > 0",
            [value],
            f"{field_name} contains '{value}' (case-insensitive)",
        )

    if operator in {"GreaterThan", "LessThan"}:
        if not _is_numeric_type(field.type):
            raise ParquetFilterError(
                "Invalid parquet filter operator for field type.",
                node_path=f"{node_path}.operator",
                details=(
                    f"Operator '{operator}' is numeric-only; field '{field_name}' "
                    f"has type '{field.type}'."
                ),
            )
        try:
            numeric_value = float(value)
        except ValueError as exc:
            raise ParquetFilterError(
                "Invalid parquet filter value.",
                node_path=f"{node_path}.value",
                details=f"Value '{value}' must be numeric for operator '{operator}'.",
            ) from exc
        if not math.isfinite(numeric_value):
            raise ParquetFilterError(
                "Invalid parquet filter value.",
                node_path=f"{node_path}.value",
                details="Numeric filter values must be finite (not NaN/inf).",
            )

        cast_expr = f"TRY_CAST({quoted} AS DOUBLE)"
        comparator = ">" if operator == "GreaterThan" else "<"
        sql = (
            f"({cast_expr} IS NOT NULL AND NOT isnan({cast_expr}) "
            f"AND {cast_expr} {comparator} ?)"
        )
        return sql, [numeric_value], f"{field_name} {comparator} {numeric_value}"

    raise ParquetFilterError(
        "Invalid parquet filter payload.",
        node_path=f"{node_path}.operator",
        details=f"Unsupported operator '{operator}'.",
    )


def _compile_node(
    node: dict[str, Any],
    schema_fields: dict[str, pa.Field],
    *,
    node_path: str,
) -> tuple[str, list[Any], str]:
    kind = node["kind"]
    if kind == "condition":
        return _compile_condition(node, schema_fields, node_path=node_path)

    logic = node["logic"]
    child_sqls: list[str] = []
    params: list[Any] = []
    summaries: list[str] = []
    for idx, child in enumerate(node["children"]):
        child_sql, child_params, child_summary = _compile_node(
            child,
            schema_fields,
            node_path=f"{node_path}.children[{idx}]",
        )
        child_sqls.append(f"({child_sql})")
        params.extend(child_params)
        summaries.append(child_summary)

    joined_sql = f" {logic} ".join(child_sqls)
    summary = f" ({f' {logic} '.join(summaries)}) "
    return joined_sql, params, summary


def compile_filter(node: dict[str, Any], schema: pa.Schema) -> CompiledParquetFilter:
    """Compile a validated tree into a DuckDB-safe WHERE fragment."""

    schema_fields = {field.name: field for field in schema}
    where_sql, params, summary = _compile_node(node, schema_fields, node_path="$")
    normalized_summary = " ".join(summary.split()).strip()
    return CompiledParquetFilter(
        normalized_tree=node,
        where_sql=where_sql,
        params=tuple(params),
        summary=normalized_summary,
    )


def compile_filter_payload_for_path(path: str | Path, raw_payload: str | None) -> CompiledParquetFilter | None:
    """Decode + validate + compile a ``pqf`` payload for a parquet file path."""

    raw_node = decode_filter_payload(raw_payload)
    if raw_node is None:
        return None
    normalized_node = validate_filter_tree(raw_node)
    schema = pq.read_schema(path)
    return compile_filter(normalized_node, schema)


def _base_select_sql(compiled: CompiledParquetFilter | None) -> tuple[str, list[Any]]:
    sql = "SELECT * FROM read_parquet(?)"
    params: list[Any] = []
    if compiled is not None:
        sql = f"{sql} WHERE {compiled.where_sql}"
        params.extend(compiled.params)
    return sql, params


def query_preview(
    path: str | Path,
    compiled: CompiledParquetFilter | None,
    *,
    limit: int,
) -> pd.DataFrame:
    """Return a preview dataframe with optional parquet filter applied."""

    if limit <= 0:
        raise ValueError("Preview limit must be > 0")

    sql, params = _base_select_sql(compiled)
    sql = f"{sql} LIMIT ?"
    bind_params = [str(path), *params, int(limit)]
    with duckdb.connect() as conn:
        return conn.execute(sql, bind_params).df()


def count_rows(path: str | Path, compiled: CompiledParquetFilter | None) -> int:
    """Count rows for a parquet path with optional compiled filter."""

    from_sql = "FROM read_parquet(?)"
    params: list[Any] = []
    if compiled is not None:
        from_sql = f"{from_sql} WHERE {compiled.where_sql}"
        params.extend(compiled.params)
    sql = f"SELECT COUNT(*) {from_sql}"
    with duckdb.connect() as conn:
        return int(conn.execute(sql, [str(path), *params]).fetchone()[0])


def query_export(
    path: str | Path,
    compiled: CompiledParquetFilter | None,
    *,
    max_rows: int,
) -> pa.Table:
    """Return an Arrow table for export, enforcing no-row and row-limit contracts."""

    row_count = count_rows(path, compiled)
    if row_count == 0:
        raise ParquetFilterError(
            "No rows matched the active parquet filter.",
            code="no_rows_matched_filter",
            status_code=422,
        )
    if max_rows > 0 and row_count > max_rows:
        raise ParquetFilterError(
            "Filtered parquet export exceeds configured row limit.",
            code="parquet_filter_row_limit_exceeded",
            status_code=413,
            details=(
                f"Filtered row count ({row_count}) exceeds export max ({max_rows})."
            ),
        )

    sql, params = _base_select_sql(compiled)
    with duckdb.connect() as conn:
        return conn.execute(sql, [str(path), *params]).fetch_arrow_table()


__all__ = [
    "CompiledParquetFilter",
    "MAX_FILTER_DEPTH",
    "MAX_FILTER_NODES",
    "MAX_FILTER_FIELD_LEN",
    "MAX_FILTER_VALUE_LEN",
    "ParquetFilterError",
    "decode_filter_payload",
    "validate_filter_tree",
    "compile_filter",
    "compile_filter_payload_for_path",
    "query_preview",
    "count_rows",
    "query_export",
]
