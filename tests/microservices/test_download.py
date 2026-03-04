"""Tests for the download microservice parquet-to-CSV conversion."""

import base64
import asyncio
import json
import tempfile
from io import BytesIO
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from starlette.datastructures import QueryParams
from starlette.exceptions import HTTPException

from wepppy.microservices.browse import _download as download_mod
from wepppy.microservices.browse._download import _parquet_to_dataframe_with_units


def _encode_filter_payload(payload: dict) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


@pytest.mark.unit
def test_parquet_to_dataframe_with_index_column():
    """Test that parquet files with __index_level_0__ column are handled correctly.
    
    This regression test ensures that when converting parquet to CSV, we don't try
    to rename index columns that get converted to the DataFrame index during 
    table.to_pandas().
    
    Reproduces issue: ValueError: Length mismatch: Expected axis has 31 elements, 
    new values have 32 elements
    """
    with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
        tmp_path = tmp.name
        
    try:
        # Create a DataFrame with some data
        df = pd.DataFrame({
            'fire_year (yr)': [2010, 2010, 2010],
            'year': [2010, 2010, 2010],
            'precip (mm)': [0.0, 5.2, 3.1],
            'runoff (mm)': [0.0, 1.2, 0.8]
        })
        
        # Write to parquet WITHOUT index=False (mimics ash model behavior)
        # This creates __index_level_0__ column in the parquet file
        df.to_parquet(tmp_path, index=True)
        
        # Verify the parquet file has the index column
        table = pq.read_table(tmp_path)
        # The exact column name depends on pandas version, but should be 5 columns total
        assert len(table.schema) >= 5  # At least 4 data columns + 1 index column
        
        # Check that when converted to pandas, the index column disappears
        df_roundtrip = table.to_pandas()
        assert len(df_roundtrip.columns) == 4  # Only the 4 data columns remain
        
        # Test the conversion
        result_df = _parquet_to_dataframe_with_units(tmp_path)
        
        # Should have 4 columns (not 5)
        assert len(result_df.columns) == 4
        assert '__index_level_0__' not in result_df.columns
        assert list(result_df.columns) == [
            'fire_year (yr)', 
            'year', 
            'precip (mm)', 
            'runoff (mm)'
        ]
        
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@pytest.mark.unit
def test_parquet_to_dataframe_with_units_metadata():
    """Test that parquet files with units metadata are converted correctly."""
    with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
        tmp_path = tmp.name
        
    try:
        # Create a table with units metadata
        data = {
            'temperature': [20.0, 21.5, 19.8],
            'pressure': [101.3, 101.5, 101.2]
        }
        df = pd.DataFrame(data)
        
        # Create schema with units metadata
        schema = pa.schema([
            pa.field('temperature', pa.float64(), metadata={b'units': b'C'}),
            pa.field('pressure', pa.float64(), metadata={b'units': b'kPa'})
        ])
        
        table = pa.Table.from_pandas(df, schema=schema)
        pq.write_table(table, tmp_path)
        
        # Test the conversion
        result_df = _parquet_to_dataframe_with_units(tmp_path)
        
        # Should have 2 columns with units appended
        assert len(result_df.columns) == 2
        assert list(result_df.columns) == ['temperature (C)', 'pressure (kPa)']
        
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@pytest.mark.unit
def test_parquet_to_dataframe_units_already_in_name():
    """Test that units are not duplicated if already in column name."""
    with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
        tmp_path = tmp.name
        
    try:
        # Create a table where column names already have units
        data = {
            'temperature (C)': [20.0, 21.5, 19.8],
            'pressure (kPa)': [101.3, 101.5, 101.2]
        }
        df = pd.DataFrame(data)
        
        # Create schema with units metadata matching the names
        schema = pa.schema([
            pa.field('temperature (C)', pa.float64(), metadata={b'units': b'C'}),
            pa.field('pressure (kPa)', pa.float64(), metadata={b'units': b'kPa'})
        ])
        
        table = pa.Table.from_pandas(df, schema=schema)
        pq.write_table(table, tmp_path)
        
        # Test the conversion
        result_df = _parquet_to_dataframe_with_units(tmp_path)
        
        # Should keep original names without duplicating units
        assert len(result_df.columns) == 2
        assert list(result_df.columns) == ['temperature (C)', 'pressure (kPa)']
        
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@pytest.mark.unit
def test_download_returns_filtered_parquet_when_pqf_active(monkeypatch):
    with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
        tmp_path = tmp.name

    try:
        df = pd.DataFrame({
            'name': ['Alice', 'bob'],
            'value': [1.0, 2.0],
        })
        df.to_parquet(tmp_path, index=False)

        monkeypatch.setattr(download_mod, "BROWSE_PARQUET_FILTERS_ENABLED", True)
        monkeypatch.setattr(download_mod, "BROWSE_PARQUET_EXPORT_MAX_ROWS", 100)

        pqf = _encode_filter_payload(
            {
                "kind": "condition",
                "field": "name",
                "operator": "Equals",
                "value": "Alice",
            }
        )
        response = asyncio.run(
            download_mod.download_response_file(tmp_path, QueryParams({"pqf": pqf}))
        )
        assert response.status_code == 200
        assert "attachment" in response.headers.get("content-disposition", "")

        table = pq.read_table(BytesIO(response.body))
        result_df = table.to_pandas()
        assert list(result_df["name"]) == ["Alice"]
        assert list(result_df["value"]) == [1.0]
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@pytest.mark.unit
def test_download_filtered_csv_no_rows_returns_structured_error(monkeypatch):
    with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
        tmp_path = tmp.name

    try:
        df = pd.DataFrame({
            'name': ['Alice', 'bob'],
            'value': [1.0, 2.0],
        })
        df.to_parquet(tmp_path, index=False)

        monkeypatch.setattr(download_mod, "BROWSE_PARQUET_FILTERS_ENABLED", True)
        monkeypatch.setattr(download_mod, "BROWSE_PARQUET_EXPORT_MAX_ROWS", 100)

        pqf = _encode_filter_payload(
            {
                "kind": "condition",
                "field": "name",
                "operator": "Equals",
                "value": "missing",
            }
        )

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(
                download_mod.download_response_file(
                    tmp_path,
                    QueryParams({"as_csv": "1", "pqf": pqf}),
                )
            )

        assert exc_info.value.status_code == 422
        payload = exc_info.value.detail
        assert payload["error"]["code"] == "no_rows_matched_filter"
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@pytest.mark.unit
def test_download_filtered_csv_returns_only_matching_rows(monkeypatch):
    with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
        tmp_path = tmp.name

    try:
        df = pd.DataFrame({
            'name': ['Alice', 'bob'],
            'value': [1.0, 2.0],
        })
        df.to_parquet(tmp_path, index=False)

        monkeypatch.setattr(download_mod, "BROWSE_PARQUET_FILTERS_ENABLED", True)
        monkeypatch.setattr(download_mod, "BROWSE_PARQUET_EXPORT_MAX_ROWS", 100)

        pqf = _encode_filter_payload(
            {
                "kind": "condition",
                "field": "name",
                "operator": "Equals",
                "value": "bob",
            }
        )

        response = asyncio.run(
            download_mod.download_response_file(
                tmp_path,
                QueryParams({"as_csv": "1", "pqf": pqf}),
            )
        )

        assert response.status_code == 200
        assert response.headers.get("content-type", "").startswith("text/csv")
        csv_text = response.body.decode("utf-8")
        assert "bob" in csv_text
        assert "Alice" not in csv_text
    finally:
        Path(tmp_path).unlink(missing_ok=True)
