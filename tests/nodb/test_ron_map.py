"""
Unit tests for Map class raster_intersection method.

Tests edge cases where small extents cause pixel coordinate rounding issues.
"""
import json
import os
import tempfile
from typing import List

import numpy as np
import pytest

try:
    from osgeo import gdal, osr
    GDAL_AVAILABLE = True
except ImportError:
    GDAL_AVAILABLE = False

from wepppy.nodb.core.map_object import Map


@pytest.fixture
def mock_raster(tmp_path):
    """Create a simple test raster with known values."""
    if not GDAL_AVAILABLE:
        pytest.skip("GDAL not available")
    
    # Create a 100x100 raster with subcatchment IDs
    raster_file = str(tmp_path / "test_subwta.tif")
    
    # Define the extent in lat/lon (roughly Idaho)
    # This matches the typical extent used in wepppy runs
    ul_lon, ul_lat = -116.1, 44.0
    lr_lon, lr_lat = -116.0, 43.9
    
    width, height = 100, 100
    cellsize = (lr_lon - ul_lon) / width
    
    # Create a raster with subcatchment IDs 1-10
    data = np.zeros((height, width), dtype=np.int32)
    for i in range(10):
        y_start = i * 10
        y_end = (i + 1) * 10
        data[y_start:y_end, :] = i + 1
    
    # Write raster
    driver = gdal.GetDriverByName('GTiff')
    dataset = driver.Create(raster_file, width, height, 1, gdal.GDT_Int32)
    
    # Set geotransform: (ul_x, pixel_width, 0, ul_y, 0, -pixel_height)
    geotransform = (ul_lon, cellsize, 0, ul_lat, 0, -cellsize)
    dataset.SetGeoTransform(geotransform)
    
    # Set projection to WGS84
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    dataset.SetProjection(srs.ExportToWkt())
    
    # Write data
    band = dataset.GetRasterBand(1)
    band.WriteArray(data)
    band.FlushCache()
    
    dataset = None  # Close file
    
    return {
        'path': raster_file,
        'extent': [ul_lon, lr_lat, lr_lon, ul_lat],
        'center': [(ul_lon + lr_lon) / 2, (lr_lat + ul_lat) / 2],
        'cellsize': cellsize,
        'data': data
    }


@pytest.mark.unit
def test_raster_intersection_small_extent(mock_raster):
    """Test that small extents don't cause assertion errors."""
    # Create a Map instance
    map_obj = Map(
        extent=mock_raster['extent'],
        center=mock_raster['center'],
        zoom=13,
        cellsize=30.0
    )
    
    # Create a very small extent (similar to the bug report)
    # This is roughly 25-30 meters across, which could round to the same pixel
    small_extent = [
        -116.07141068867118,  # left (min lng)
        43.944975389627174,   # bottom (min lat)
        -116.07115314630451,  # right (max lng)
        43.94553168338225     # top (max lat)
    ]
    
    # This should not raise an AssertionError anymore
    result = map_obj.raster_intersection(
        extent=small_extent,
        raster_fn=mock_raster['path'],
        discard=(0,)
    )
    
    # Result should be a list (even if empty or contains just one subcatchment)
    assert isinstance(result, list)


@pytest.mark.unit
@pytest.mark.skip(reason="Test needs raster in UTM projection matching Map's UTM zone")
def test_raster_intersection_normal_extent(mock_raster):
    """Test that normal-sized extents work correctly."""
    map_obj = Map(
        extent=mock_raster['extent'],
        center=mock_raster['center'],
        zoom=13,
        cellsize=30.0
    )
    
    # Create a normal extent that covers part of the raster
    ul_lon, lr_lat, lr_lon, ul_lat = mock_raster['extent']
    mid_lon = (ul_lon + lr_lon) / 2
    mid_lat = (lr_lat + ul_lat) / 2
    
    normal_extent = [
        ul_lon + 0.01,       # left
        mid_lat - 0.01,      # bottom
        mid_lon + 0.01,      # right
        mid_lat + 0.01       # top
    ]
    
    result = map_obj.raster_intersection(
        extent=normal_extent,
        raster_fn=mock_raster['path'],
        discard=(0,)
    )
    
    # Should return subcatchment IDs
    assert isinstance(result, list)
    assert len(result) > 0
    # Values should be sorted
    assert result == sorted(result)


@pytest.mark.unit
@pytest.mark.skip(reason="Test needs raster in UTM projection matching Map's UTM zone")
def test_raster_intersection_single_pixel(mock_raster):
    """Test intersection that resolves to a single pixel."""
    map_obj = Map(
        extent=mock_raster['extent'],
        center=mock_raster['center'],
        zoom=13,
        cellsize=30.0
    )
    
    # Create an extent that's exactly one pixel
    ul_lon, lr_lat, lr_lon, ul_lat = mock_raster['extent']
    cellsize = mock_raster['cellsize']
    
    single_pixel_extent = [
        ul_lon + cellsize * 10,           # left
        ul_lat - cellsize * 10,           # bottom
        ul_lon + cellsize * 10.1,         # right (tiny offset)
        ul_lat - cellsize * 9.9           # top (tiny offset)
    ]
    
    result = map_obj.raster_intersection(
        extent=single_pixel_extent,
        raster_fn=mock_raster['path'],
        discard=(0,)
    )
    
    # Should return at least one value
    assert isinstance(result, list)
    assert len(result) >= 1


@pytest.mark.unit
def test_raster_intersection_missing_file():
    """Test that missing raster file returns empty list."""
    map_obj = Map(
        extent=[-116.1, 43.9, -116.0, 44.0],
        center=[-116.05, 43.95],
        zoom=13,
        cellsize=30.0
    )
    
    result = map_obj.raster_intersection(
        extent=[-116.07, 43.94, -116.06, 43.95],
        raster_fn="/nonexistent/path/to/raster.tif",
        discard=(0,)
    )
    
    assert result == []


@pytest.mark.unit
def test_map_to_payload_preserves_legacy_object_path():
    map_obj = Map(
        extent=[-116.1, 43.9, -116.0, 44.0],
        center=[-116.05, 43.95],
        zoom=13,
        cellsize=30.0,
    )

    payload = map_obj.to_payload()

    assert payload["py/object"] == "wepppy.nodb.core.ron.Map"


@pytest.mark.unit
def test_map_from_payload_accepts_legacy_py_tuple_payload():
    seed = Map(
        extent=[-116.1, 43.9, -116.0, 44.0],
        center=[-116.05, 43.95],
        zoom=13,
        cellsize=30.0,
    ).to_payload()

    payload = {
        "extent": {"py/tuple": seed["extent"]},
        "center": {"py/tuple": seed["center"]},
        "zoom": seed["zoom"],
        "cellsize": seed["cellsize"],
        "utm": seed["utm"],
        "_ul_x": seed["_ul_x"],
        "_ul_y": seed["_ul_y"],
        "_lr_x": seed["_lr_x"],
        "_lr_y": seed["_lr_y"],
        "_num_cols": seed["_num_cols"],
        "_num_rows": seed["_num_rows"],
    }

    hydrated = Map.from_payload(payload)

    assert hydrated.extent == pytest.approx(seed["extent"])
    assert hydrated.center == pytest.approx(seed["center"])
    assert hydrated.cellsize == pytest.approx(seed["cellsize"])
    assert hydrated.utm[0] == pytest.approx(seed["utm"]["py/tuple"][0])
    assert hydrated.utm[1] == pytest.approx(seed["utm"]["py/tuple"][1])
    assert hydrated.utm[2] == seed["utm"]["py/tuple"][2]
    assert hydrated.utm[3] == seed["utm"]["py/tuple"][3]
    assert hydrated.num_cols == seed["_num_cols"]
    assert hydrated.num_rows == seed["_num_rows"]


@pytest.mark.unit
def test_map_from_payload_uses_default_cellsize_when_missing():
    payload = {
        "extent": [-116.1, 43.9, -116.0, 44.0],
        "center": [-116.05, 43.95],
        "zoom": 13,
        "cellsize": "",
    }

    hydrated = Map.from_payload(payload, default_cellsize=42.0)

    assert hydrated.cellsize == pytest.approx(42.0)

    payload_text = json.dumps(
        {
            "extent": payload["extent"],
            "center": payload["center"],
            "zoom": payload["zoom"],
            "cellsize": 0.0,
        }
    )
    with pytest.raises(ValueError, match="cellsize must be positive"):
        Map.from_payload(payload_text, default_cellsize=42.0)


@pytest.mark.unit
def test_ron_module_still_exports_map_class():
    from wepppy.nodb.core.ron import Map as RonMap

    assert RonMap is Map


@pytest.mark.unit
def test_map_jsonpickle_uses_map_object_module_path():
    import jsonpickle

    encoded = jsonpickle.encode(
        Map(
            extent=[-116.1, 43.9, -116.0, 44.0],
            center=[-116.05, 43.95],
            zoom=13,
            cellsize=30.0,
        )
    )

    assert "wepppy.nodb.core.map_object.Map" in encoded


@pytest.mark.unit
@pytest.mark.skip(reason="Test needs raster in UTM projection matching Map's UTM zone")
def test_raster_intersection_discard_values(mock_raster):
    """Test that discard parameter filters out specified values."""
    map_obj = Map(
        extent=mock_raster['extent'],
        center=mock_raster['center'],
        zoom=13,
        cellsize=30.0
    )
    
    # Get all values
    all_result = map_obj.raster_intersection(
        extent=mock_raster['extent'],
        raster_fn=mock_raster['path'],
        discard=None
    )
    
    # Get values with discard
    filtered_result = map_obj.raster_intersection(
        extent=mock_raster['extent'],
        raster_fn=mock_raster['path'],
        discard=(0, 1, 2)
    )
    
    # Filtered result should not contain discarded values
    assert 0 not in filtered_result
    assert 1 not in filtered_result
    assert 2 not in filtered_result
    
    # But might contain other values
    assert all(v >= 3 for v in filtered_result)
