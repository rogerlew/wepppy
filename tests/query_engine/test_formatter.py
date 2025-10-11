from __future__ import annotations

import pyarrow as pa

from wepppy.query_engine.formatter import format_table


def test_format_table_converts_binary_columns_to_base64_strings() -> None:
    table = pa.table({"geom": [b"\x00\x01"], "name": ["A"]})

    result = format_table(table, include_schema=True)

    assert result.records == [{"geom": "AAE=", "name": "A"}]
    assert result.schema == [
        {"name": "geom", "type": "binary"},
        {"name": "name", "type": "string"},
    ]
