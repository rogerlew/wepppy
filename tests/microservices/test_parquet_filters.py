import base64
import json
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from wepppy.microservices.parquet_filters import (
    ParquetFilterError,
    compile_filter,
    compile_filter_payload_for_path,
    decode_filter_payload,
    query_export,
    query_preview,
    validate_filter_tree,
)

pytestmark = pytest.mark.microservice


def _encode_payload(payload: dict) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _write_parquet(path: Path) -> None:
    df = pd.DataFrame(
        {
            "name": ["Alice", "bob", "CHARLIE", None],
            "value": [1.0, 2.0, float("nan"), 5.0],
            "category": ["x", "y", "z", "x"],
        }
    )
    table = pa.Table.from_pandas(df)
    pq.write_table(table, path)


def test_decode_filter_payload_rejects_invalid_base64() -> None:
    with pytest.raises(ParquetFilterError) as exc_info:
        decode_filter_payload("not a payload")

    err = exc_info.value
    assert err.code == "validation_error"
    assert err.node_path == "pqf"


def test_validate_filter_tree_enforces_depth_limit() -> None:
    payload = {"kind": "condition", "field": "name", "operator": "Equals", "value": "alice"}
    for _ in range(6):
        payload = {"kind": "group", "logic": "AND", "children": [payload]}

    with pytest.raises(ParquetFilterError) as exc_info:
        validate_filter_tree(payload)

    assert "max depth" in (exc_info.value.details or "")


def test_compile_filter_rejects_unknown_field() -> None:
    schema = pa.schema([pa.field("name", pa.string())])
    normalized = validate_filter_tree(
        {
            "kind": "condition",
            "field": "missing",
            "operator": "Equals",
            "value": "x",
        }
    )

    with pytest.raises(ParquetFilterError) as exc_info:
        compile_filter(normalized, schema)

    assert "does not exist" in (exc_info.value.details or "")


def test_compile_filter_rejects_numeric_operators_for_non_numeric_fields() -> None:
    schema = pa.schema([pa.field("name", pa.string())])
    normalized = validate_filter_tree(
        {
            "kind": "condition",
            "field": "name",
            "operator": "GreaterThan",
            "value": "1",
        }
    )

    with pytest.raises(ParquetFilterError) as exc_info:
        compile_filter(normalized, schema)

    assert "numeric-only" in (exc_info.value.details or "")


def test_compile_filter_rejects_non_numeric_equals_value_for_numeric_field() -> None:
    schema = pa.schema([pa.field("value", pa.float64())])
    normalized = validate_filter_tree(
        {
            "kind": "condition",
            "field": "value",
            "operator": "Equals",
            "value": "not-a-number",
        }
    )

    with pytest.raises(ParquetFilterError) as exc_info:
        compile_filter(normalized, schema)

    assert "must be numeric" in (exc_info.value.details or "")


def test_query_preview_contains_case_insensitive_and_numeric_gt(tmp_path: Path) -> None:
    parquet_path = tmp_path / "sample.parquet"
    _write_parquet(parquet_path)

    payload = {
        "kind": "group",
        "logic": "AND",
        "children": [
            {
                "kind": "condition",
                "field": "name",
                "operator": "Contains",
                "value": "AL",
            },
            {
                "kind": "condition",
                "field": "value",
                "operator": "GreaterThan",
                "value": "0.5",
            },
        ],
    }

    compiled = compile_filter_payload_for_path(parquet_path, _encode_payload(payload))
    assert compiled is not None

    preview = query_preview(parquet_path, compiled, limit=100)
    assert list(preview["name"]) == ["Alice"]


def test_query_export_returns_no_rows_error_code(tmp_path: Path) -> None:
    parquet_path = tmp_path / "sample.parquet"
    _write_parquet(parquet_path)

    payload = {
        "kind": "condition",
        "field": "category",
        "operator": "Equals",
        "value": "missing",
    }
    compiled = compile_filter_payload_for_path(parquet_path, _encode_payload(payload))
    assert compiled is not None

    with pytest.raises(ParquetFilterError) as exc_info:
        query_export(parquet_path, compiled, max_rows=100)

    assert exc_info.value.code == "no_rows_matched_filter"
