"""Helpers to convert Arrow query results into JSON-safe payloads."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from collections.abc import Mapping, Sequence
from typing import Any

import pyarrow as pa

from wepppy.query_engine.payload import TimeseriesReshapeSpec, TimeseriesSeriesSpec


@dataclass(slots=True)
class QueryResult:
    """Structured response emitted by the query engine."""

    records: list[dict[str, Any]]
    schema: list[dict[str, Any]] | None = None
    row_count: int = 0
    sql: str | None = None
    formatted: dict[str, Any] | None = None


def _json_safe(value: Any) -> Any:
    """Convert complex values (bytes, decimals, datetimes) into JSON-friendly data.

    Args:
        value: Arbitrary Python object.

    Returns:
        JSON serialisable representation of `value`.
    """
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


def _field_metadata(field: pa.Field) -> dict[str, str]:
    """Return decoded metadata key/value pairs for a PyArrow field.

    Args:
        field: PyArrow field whose metadata should be inspected.

    Returns:
        Mapping of metadata keys to decoded string values.
    """
    if not field.metadata:
        return {}
    meta = {}
    for key, value in field.metadata.items():
        try:
            meta[key.decode()] = value.decode()
        except Exception:  # pragma: no cover - defensive
            meta[str(key)] = str(value)
    return meta


def _schema_to_dict(schema: pa.Schema) -> list[dict[str, Any]]:
    """Convert a PyArrow schema into a serialisable list of field dicts.

    Args:
        schema: PyArrow schema returned by DuckDB.

    Returns:
        List of dictionaries summarising each field.
    """
    entries: list[dict[str, Any]] = []
    for field in schema:
        entry: dict[str, Any] = {"name": field.name, "type": str(field.type)}
        entry.update(_field_metadata(field))
        entries.append(entry)
    return entries


def _lookup_field_metadata(schema: pa.Schema) -> dict[str, dict[str, str]]:
    """Build a lookup of column name to metadata dict.

    Args:
        schema: PyArrow schema returned by DuckDB.

    Returns:
        Mapping of column name to metadata key/values.
    """
    lookup: dict[str, dict[str, str]] = {}
    for field in schema:
        metadata = _field_metadata(field)
        if metadata:
            lookup[field.name] = metadata
    return lookup


def _filtered_records_by_year(
    records: Sequence[dict[str, Any]],
    *,
    year_column: str | None,
    excluded_years: set[Any],
) -> list[dict[str, Any]]:
    """Remove rows that reference a year present in the excluded_years set.

    Args:
        records: Original record sequence.
        year_column: Column containing the year marker.
        excluded_years: Years that should be removed from the dataset.

    Returns:
        Filtered list of records.
    """
    if not year_column or not excluded_years:
        return list(records)
    filtered: list[dict[str, Any]] = []
    for row in records:
        year_value = row.get(year_column)
        if year_value in excluded_years:
            continue
        filtered.append(row)
    return filtered


def _excluded_years(
    records: Sequence[dict[str, Any]],
    *,
    year_column: str | None,
    exclude_indexes: Sequence[int],
) -> set[Any]:
    """Identify which year values to omit based on index positions.

    Args:
        records: Record sequence that includes a year column.
        year_column: Name of the year column.
        exclude_indexes: Sorted indexes used to pick years to exclude.

    Returns:
        Set of years that should be filtered out.
    """
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


def _series_metadata(series: TimeseriesSeriesSpec, *, field_metadata: dict[str, dict[str, str]]) -> dict[str, Any]:
    """Combine explicit series metadata with schema-derived defaults.

    Args:
        series: Series descriptor from the reshape spec.
        field_metadata: Metadata keyed by column name.

    Returns:
        Dictionary containing the resolved metadata for the output series.
    """
    metadata = field_metadata.get(series.column, {})
    return {
        "units": series.units or metadata.get("units"),
        "description": series.description or metadata.get("description"),
    }


def _apply_timeseries_reshape(
    records: list[dict[str, Any]],
    schema: pa.Schema,
    spec: TimeseriesReshapeSpec,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Aggregate tabular data into a structured timeseries response.

    Args:
        records: JSON-safe records emitted from Arrow.
        schema: PyArrow schema used for metadata lookups.
        spec: Timeseries reshape specification.

    Returns:
        Tuple containing filtered records and the formatted timeseries payload.
    """
    field_meta_lookup = _lookup_field_metadata(schema)
    excluded_years = _excluded_years(records, year_column=spec.year_column, exclude_indexes=spec.exclude_year_indexes)
    filtered_records = _filtered_records_by_year(records, year_column=spec.year_column, excluded_years=excluded_years)

    index_values: list[Any] = []
    series_values: dict[str, list[Any]] = {series.key: [] for series in spec.series}
    for row in filtered_records:
        index_values.append(row.get(spec.index_column))
        for series in spec.series:
            series_values[series.key].append(row.get(series.column))

    series_output: list[dict[str, Any]] = []
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
    sql: str | None = None,
    reshape: TimeseriesReshapeSpec | None = None,
) -> QueryResult:
    """Convert a PyArrow table into a JSON-oriented QueryResult.

    Args:
        table: DuckDB result table.
        include_schema: When True, serialise schema metadata into the result.
        sql: Optional SQL text to attach for debugging.
        reshape: Optional reshape specification for timeseries payloads.

    Returns:
        QueryResult ready for JSON serialisation.
    """
    pylist = table.to_pylist()
    records = [_json_safe(item) for item in pylist]
    schema = None
    if include_schema:
        schema = _schema_to_dict(table.schema)

    formatted: dict[str, Any] | None = None
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
