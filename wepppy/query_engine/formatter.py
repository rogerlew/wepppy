from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pyarrow as pa


@dataclass(slots=True)
class QueryResult:
    records: List[Dict[str, Any]]
    schema: Optional[List[Dict[str, Any]]] = None
    row_count: int = 0


def format_table(table: pa.Table, *, include_schema: bool = False) -> QueryResult:
    records = table.to_pylist()
    schema = None
    if include_schema:
        schema = [
            {"name": field.name, "type": str(field.type)}
            for field in table.schema
        ]
    return QueryResult(records=records, schema=schema, row_count=table.num_rows)
