from __future__ import annotations

from typing import Any

import pyarrow as pa

from .payload import TimeseriesReshapeSpec

class QueryResult:
    records: list[dict[str, Any]]
    schema: list[dict[str, Any]] | None
    row_count: int
    sql: str | None
    formatted: dict[str, Any] | None

def format_table(
    table: pa.Table,
    *,
    include_schema: bool = ...,
    sql: str | None = ...,
    reshape: TimeseriesReshapeSpec | None = ...,
) -> QueryResult: ...
