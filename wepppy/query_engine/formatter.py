from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Dict, List, Mapping, Optional

import pyarrow as pa


@dataclass(slots=True)
class QueryResult:
    records: List[Dict[str, Any]]
    schema: Optional[List[Dict[str, Any]]] = None
    row_count: int = 0
    sql: Optional[str] = None


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


def format_table(
    table: pa.Table,
    *,
    include_schema: bool = False,
    sql: Optional[str] = None,
) -> QueryResult:
    records = [_json_safe(item) for item in table.to_pylist()]
    schema = None
    if include_schema:
        schema = [
            {"name": field.name, "type": str(field.type)}
            for field in table.schema
        ]
    return QueryResult(records=records, schema=schema, row_count=table.num_rows, sql=sql)
