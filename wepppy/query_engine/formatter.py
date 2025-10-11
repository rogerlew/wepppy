from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Dict, List, Mapping, Optional, Sequence

import pyarrow as pa

from wepppy.query_engine.payload import TimeseriesReshapeSpec, TimeseriesSeriesSpec


@dataclass(slots=True)
class QueryResult:
    records: List[Dict[str, Any]]
    schema: Optional[List[Dict[str, Any]]] = None
    row_count: int = 0
    sql: Optional[str] = None
    formatted: Optional[Dict[str, Any]] = None


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        raw = bytes(value)
        try:
            decoded = raw.decode("utf-8")
        except UnicodeDecodeError:
            return base64.b64encode(raw).decode("ascii")
        if all(32 <= ord(ch) < 127 or ch in "\r\n\t" for ch in decoded):
            return decoded
        return base64.b64encode(raw).decode("ascii")
    return value


def _field_metadata(field: pa.Field) -> Dict[str, str]:
    if not field.metadata:
        return {}
    meta = {}
    for key, value in field.metadata.items():
        try:
            meta[key.decode()] = value.decode()
        except Exception:  # pragma: no cover - defensive
            meta[str(key)] = str(value)
    return meta


def _schema_to_dict(schema: pa.Schema) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    for field in schema:
        entry: Dict[str, Any] = {"name": field.name, "type": str(field.type)}
        entry.update(_field_metadata(field))
        entries.append(entry)
    return entries


def _lookup_field_metadata(schema: pa.Schema) -> Dict[str, Dict[str, str]]:
    lookup: Dict[str, Dict[str, str]] = {}
    for field in schema:
        metadata = _field_metadata(field)
        if metadata:
            lookup[field.name] = metadata
    return lookup


def _filtered_records_by_year(records: Sequence[Dict[str, Any]], *, year_column: Optional[str], excluded_years: set[Any]) -> List[Dict[str, Any]]:
    if not year_column or not excluded_years:
        return list(records)
    filtered: List[Dict[str, Any]] = []
    for row in records:
        year_value = row.get(year_column)
        if year_value in excluded_years:
            continue
        filtered.append(row)
    return filtered


def _excluded_years(records: Sequence[Dict[str, Any]], *, year_column: Optional[str], exclude_indexes: Sequence[int]) -> set[Any]:
    if year_column is None or not exclude_indexes:
        return set()
    years = sorted({row.get(year_column) for row in records if row.get(year_column) is not None})
    excluded: set[Any] = set()
    for idx in exclude_indexes:
        if not years:
            break
        try:
            excluded.add(years[idx])
        except IndexError:
            continue
    return excluded


def _series_metadata(series: TimeseriesSeriesSpec, *, field_metadata: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
    metadata = field_metadata.get(series.column, {})
    return {
        "units": series.units or metadata.get("units"),
        "description": series.description or metadata.get("description"),
    }


def _apply_timeseries_reshape(
    records: List[Dict[str, Any]],
    schema: pa.Schema,
    spec: TimeseriesReshapeSpec,
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    field_meta_lookup = _lookup_field_metadata(schema)
    excluded_years = _excluded_years(records, year_column=spec.year_column, exclude_indexes=spec.exclude_year_indexes)
    filtered_records = _filtered_records_by_year(records, year_column=spec.year_column, excluded_years=excluded_years)

    index_values: List[Any] = []
    series_values: Dict[str, List[Any]] = {series.key: [] for series in spec.series}
    for row in filtered_records:
        index_values.append(row.get(spec.index_column))
        for series in spec.series:
            series_values[series.key].append(row.get(series.column))

    series_output: List[Dict[str, Any]] = []
    for series in spec.series:
        meta = _series_metadata(series, field_metadata=field_meta_lookup)
        series_output.append(
            {
                "id": series.key,
                "column": series.column,
                "label": series.label or series.column,
                "group": series.group,
                "role": series.role,
                "color": series.color,
                "units": meta.get("units"),
                "description": meta.get("description"),
                "values": series_values[series.key],
            }
        )

    formatted = {
        "type": "timeseries",
        "index": {
            "column": spec.index_column,
            "key": spec.index_key,
            "values": index_values,
        },
        "series": series_output,
        "excluded_years": sorted(excluded_years),
    }

    if spec.year_column and spec.year_column not in {spec.index_column}:
        formatted["year_column"] = spec.year_column

    formatted["row_count"] = len(index_values)
    formatted["series_count"] = len(series_output)

    if spec.compact:
        filtered_records = []

    return filtered_records, formatted


def format_table(
    table: pa.Table,
    *,
    include_schema: bool = False,
    sql: Optional[str] = None,
    reshape: TimeseriesReshapeSpec | None = None,
) -> QueryResult:
    pylist = table.to_pylist()
    records = [_json_safe(item) for item in pylist]
    schema = None
    if include_schema:
        schema = _schema_to_dict(table.schema)

    formatted: Optional[Dict[str, Any]] = None
    row_count = table.num_rows

    if reshape is not None:
        filtered_records, formatted = _apply_timeseries_reshape(records, table.schema, reshape)
        if reshape.include_records:
            records = filtered_records
        else:
            records = []
        row_count = formatted.get("row_count", len(filtered_records))
    else:
        row_count = len(records)

    return QueryResult(records=records, schema=schema, row_count=row_count, sql=sql, formatted=formatted)
