"""Tests for the download microservice parquet-to-CSV conversion."""

import tempfile
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from wepppy.microservices._download import _parquet_to_dataframe_with_units


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
