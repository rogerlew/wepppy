"""Arrow-backed parquet presentation helpers for browse routes."""

from __future__ import annotations

import csv
import html
import io
import json
import os
import time
from collections.abc import Mapping
from typing import Any

import pyarrow as pa


PARQUET_EXTENSIONS = (".parquet", ".geoparquet", ".pq")


def current_rss_kb() -> int | None:
    """Return current resident set size in KiB on Linux, if available."""

    try:
        with open("/proc/self/status", encoding="utf-8") as fp:
            for line in fp:
                if line.startswith("VmRSS:"):
                    parts = line.split()
                    if len(parts) >= 2:
                        return int(parts[1])
    except (OSError, ValueError):
        return None
    return None


def monotonic_ns() -> int:
    return time.monotonic_ns()


def log_parquet_operation(
    logger,
    *,
    operation: str,
    path: str,
    started_ns: int,
    rss_before_kb: int | None,
    rows: int | None = None,
    status: str = "ok",
) -> None:
    """Log bounded parquet operation telemetry without file contents or query payloads."""

    rss_after_kb = current_rss_kb()
    delta_kb = (
        rss_after_kb - rss_before_kb
        if rss_after_kb is not None and rss_before_kb is not None
        else None
    )
    try:
        size_bytes = os.path.getsize(path)
    except OSError:
        size_bytes = None
    duration_ms = (time.monotonic_ns() - started_ns) / 1_000_000
    logger.info(
        "browse parquet operation=%s file=%s size_bytes=%s rows=%s "
        "duration_ms=%.1f rss_before_kb=%s rss_after_kb=%s rss_delta_kb=%s status=%s",
        operation,
        os.path.basename(path),
        size_bytes,
        rows,
        duration_ms,
        rss_before_kb,
        rss_after_kb,
        delta_kb,
        status,
    )


def pandas_index_column_names(schema: pa.Schema) -> set[str]:
    """Return physical parquet columns that pandas metadata marks as index columns."""

    metadata = schema.metadata or {}
    raw = metadata.get(b"pandas")
    if not raw:
        return set()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return set()

    index_names: set[str] = set()
    for entry in payload.get("index_columns", []):
        if isinstance(entry, str):
            index_names.add(entry)
        elif isinstance(entry, Mapping):
            name = entry.get("name")
            if isinstance(name, str):
                index_names.add(name)
    return index_names


def field_label_with_units(field: pa.Field) -> str:
    label = field.name
    metadata = getattr(field, "metadata", None)
    if metadata is None:
        return label
    units_bytes = metadata.get(b"units")
    if units_bytes:
        try:
            units = units_bytes.decode().strip()
        except UnicodeDecodeError:
            units = units_bytes.decode("utf-8", "ignore").strip()
        if units:
            suffix = f"({units})"
            if suffix not in label:
                return f"{label} {suffix}"
    return label


def project_table_for_output(
    table: pa.Table,
    *,
    source_schema: pa.Schema | None = None,
    include_units: bool = False,
    drop_pandas_index: bool = True,
) -> pa.Table:
    """Drop pandas physical index columns and optionally append units to names."""

    schema = source_schema or table.schema
    index_columns = pandas_index_column_names(schema) if drop_pandas_index else set()
    fields_by_name = {field.name: field for field in schema}

    arrays: list[pa.ChunkedArray] = []
    names: list[str] = []
    for name in table.column_names:
        if drop_pandas_index and (name == "__index_level_0__" or name in index_columns):
            continue
        field = fields_by_name.get(name)
        label = field_label_with_units(field) if include_units and field is not None else name
        arrays.append(table.column(name))
        names.append(label)

    return pa.table(arrays, names=names)


def _format_html_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value != value:
        return "NaN"
    return str(value)


def _format_csv_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value != value:
        return ""
    return str(value)


def table_to_html(table: pa.Table) -> str:
    """Render a small Arrow table as pandas-like browse HTML."""

    rows = table.to_pylist()
    parts = [
        '<table border="0" class="dataframe sortable table table-nonfluid">',
        "  <thead>",
        '    <tr style="text-align: left;">',
        "      <th></th>",
    ]
    for column_name in table.column_names:
        parts.append(f"      <th>{html.escape(str(column_name))}</th>")
    parts.extend(
        [
            "    </tr>",
            "  </thead>",
            "  <tbody>",
        ]
    )
    for row_index, row in enumerate(rows):
        parts.append("    <tr>")
        parts.append(f"      <th>{row_index}</th>")
        for column_name in table.column_names:
            parts.append(f"      <td>{html.escape(_format_html_cell(row.get(column_name)))}</td>")
        parts.append("    </tr>")
    parts.extend(["  </tbody>", "</table>"])
    return "\n".join(parts)


def write_table_to_csv_writer(table: pa.Table, writer: csv.writer, *, include_header: bool) -> None:
    """Write an Arrow table to an existing CSV writer."""

    if include_header:
        writer.writerow([str(name) for name in table.column_names])
    for row in table.to_pylist():
        writer.writerow([_format_csv_cell(row.get(column_name)) for column_name in table.column_names])


def make_csv_writer(text_buffer: io.StringIO) -> csv.writer:
    return csv.writer(text_buffer, lineterminator="\n")


def table_to_csv_bytes(table: pa.Table) -> bytes:
    """Serialize an Arrow table to CSV bytes."""

    text_buffer = io.StringIO()
    writer = make_csv_writer(text_buffer)
    write_table_to_csv_writer(table, writer, include_header=True)
    return text_buffer.getvalue().encode("utf-8")
