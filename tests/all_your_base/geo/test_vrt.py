"""Tests for wepppy.all_your_base.geo.vrt module."""

import os
import tempfile

import numpy as np
import pytest
from osgeo import gdal, osr
from pyproj import Transformer

from wepppy.all_your_base.geo.vrt import (
    build_windowed_vrt,
    build_windowed_vrt_from_window,
    calculate_src_window,
)

pytestmark = pytest.mark.integration


def _create_test_geotiff(
    path: str,
    width: int = 100,
    height: int = 100,
    x_origin: float = 500000,
    y_origin: float = 5000000,
    pixel_size: float = 10,
    epsg: int = 32617,
) -> str:
    """Create a simple test GeoTIFF in UTM."""
    driver = gdal.GetDriverByName("GTiff")
    ds = driver.Create(path, width, height, 1, gdal.GDT_Float32)

    ds.SetGeoTransform((x_origin, pixel_size, 0, y_origin, 0, -pixel_size))

    srs = osr.SpatialReference()
    srs.ImportFromEPSG(epsg)
    ds.SetProjection(srs.ExportToWkt())

    data = np.arange(width * height, dtype=np.float32).reshape(height, width)
    ds.GetRasterBand(1).WriteArray(data)
    ds.GetRasterBand(1).SetNoDataValue(-9999)

    ds.FlushCache()
    ds = None
    return path


@pytest.fixture
def test_raster(tmp_path):
    """Create a test raster for use in tests."""
    path = str(tmp_path / "test.tif")
    _create_test_geotiff(
        path,
        width=100,
        height=100,
        x_origin=500000,
        y_origin=5000000,
        pixel_size=10,
    )
    return path


class TestCalculateSrcWindow:
    """Tests for calculate_src_window function."""

    def test_same_crs(self, test_raster):
        """Window calculation when bbox CRS matches raster CRS."""
        bbox = (500200, 4999200, 500800, 4999800)
        bbox_crs = "EPSG:32617"

        xoff, yoff, xsize, ysize = calculate_src_window(test_raster, bbox, bbox_crs)

        assert xoff == 20
        assert yoff == 20
        assert xsize == 60
        assert ysize == 60

    def test_different_crs(self, test_raster):
        """Window calculation with CRS transformation (WGS84 bbox on UTM raster)."""
        transformer = Transformer.from_crs("EPSG:32617", "EPSG:4326", always_xy=True)

        utm_bbox = (500200, 4999200, 500800, 4999800)
        lon_min, lat_min = transformer.transform(utm_bbox[0], utm_bbox[1])
        lon_max, lat_max = transformer.transform(utm_bbox[2], utm_bbox[3])
        wgs84_bbox = (lon_min, lat_min, lon_max, lat_max)

        xoff, yoff, xsize, ysize = calculate_src_window(
            test_raster, wgs84_bbox, "EPSG:4326"
        )

        # Allow minor differences due to transform
        assert 18 <= xoff <= 22
        assert 18 <= yoff <= 22
        assert 58 <= xsize <= 62
        assert 58 <= ysize <= 62

    def test_with_padding(self, test_raster):
        """The pad_px parameter adds pixel padding."""
        bbox = (500200, 4999200, 500800, 4999800)
        bbox_crs = "EPSG:32617"

        xoff, yoff, xsize, ysize = calculate_src_window(
            test_raster, bbox, bbox_crs, pad_px=5
        )

        assert xoff == 15
        assert yoff == 15
        assert xsize == 70
        assert ysize == 70

    def test_clamps_to_bounds(self, test_raster):
        """Window is clamped when bbox extends beyond raster extent."""
        bbox = (499900, 4998900, 501100, 5000100)
        bbox_crs = "EPSG:32617"

        xoff, yoff, xsize, ysize = calculate_src_window(test_raster, bbox, bbox_crs)

        assert xoff == 0
        assert yoff == 0
        assert xsize == 100
        assert ysize == 100

    def test_swapped_bbox_coords(self, test_raster):
        """_coerce_bbox handles swapped min/max coordinates."""
        bbox_swapped = (500800, 4999800, 500200, 4999200)
        bbox_crs = "EPSG:32617"

        xoff, yoff, xsize, ysize = calculate_src_window(
            test_raster, bbox_swapped, bbox_crs
        )

        assert xoff == 20
        assert yoff == 20
        assert xsize == 60
        assert ysize == 60


class TestBuildWindowedVrt:
    """Tests for build_windowed_vrt function."""

    def test_creates_valid_vrt(self, test_raster, tmp_path):
        """Creates valid VRT with correct dimensions and geotransform."""
        vrt_path = str(tmp_path / "output.vrt")
        bbox = (500200, 4999200, 500800, 4999800)
        bbox_crs = "EPSG:32617"

        src_window = build_windowed_vrt(test_raster, vrt_path, bbox, bbox_crs)

        assert os.path.exists(vrt_path)
        assert src_window == (20, 20, 60, 60)

        ds = gdal.Open(vrt_path)
        assert ds is not None
        assert ds.RasterXSize == 60
        assert ds.RasterYSize == 60

        gt = ds.GetGeoTransform()
        assert abs(gt[0] - 500200) < 1
        assert abs(gt[3] - 4999800) < 1
        ds = None

    def test_overwrites_existing(self, test_raster, tmp_path):
        """VRT creation overwrites existing files."""
        vrt_path = str(tmp_path / "output.vrt")

        bbox1 = (500200, 4999200, 500800, 4999800)
        build_windowed_vrt(test_raster, vrt_path, bbox1, "EPSG:32617")

        ds1 = gdal.Open(vrt_path)
        size1 = (ds1.RasterXSize, ds1.RasterYSize)
        ds1 = None

        bbox2 = (500100, 4999100, 500900, 4999900)
        build_windowed_vrt(test_raster, vrt_path, bbox2, "EPSG:32617")

        ds2 = gdal.Open(vrt_path)
        size2 = (ds2.RasterXSize, ds2.RasterYSize)
        ds2 = None

        assert size1 != size2


class TestBuildWindowedVrtFromWindow:
    """Tests for build_windowed_vrt_from_window function."""

    def test_explicit_window(self, test_raster, tmp_path):
        """Creates VRT from explicit pixel window."""
        vrt_path = str(tmp_path / "output.vrt")
        src_window = (10, 10, 50, 50)

        result = build_windowed_vrt_from_window(test_raster, vrt_path, src_window)

        assert os.path.exists(vrt_path)
        assert result == src_window

        ds = gdal.Open(vrt_path)
        assert ds.RasterXSize == 50
        assert ds.RasterYSize == 50
        ds = None

    def test_with_matching_reference(self, test_raster, tmp_path):
        """Reference validation passes for matching geotransform and shape."""
        vrt_path = str(tmp_path / "output.vrt")
        src_window = (10, 10, 50, 50)
        ref_gt = (500000, 10, 0, 5000000, 0, -10)
        ref_shape = (100, 100)

        result = build_windowed_vrt_from_window(
            test_raster,
            vrt_path,
            src_window,
            reference_geotransform=ref_gt,
            reference_shape=ref_shape,
        )

        assert result == src_window

    def test_rejects_mismatched_geotransform(self, test_raster, tmp_path):
        """Raises ValueError for mismatched geotransform."""
        vrt_path = str(tmp_path / "output.vrt")
        src_window = (10, 10, 50, 50)

        with pytest.raises(ValueError, match="geotransform does not match"):
            build_windowed_vrt_from_window(
                test_raster,
                vrt_path,
                src_window,
                reference_geotransform=(600000, 10, 0, 6000000, 0, -10),
            )

    def test_rejects_mismatched_shape(self, test_raster, tmp_path):
        """Raises ValueError for mismatched shape."""
        vrt_path = str(tmp_path / "output.vrt")
        src_window = (10, 10, 50, 50)

        with pytest.raises(ValueError, match="shape does not match"):
            build_windowed_vrt_from_window(
                test_raster,
                vrt_path,
                src_window,
                reference_shape=(200, 200),
            )


class TestDataIntegrity:
    """Tests for VRT data integrity."""

    def test_vrt_data_matches_source(self, test_raster, tmp_path):
        """VRT pixel values match source raster exactly."""
        vrt_path = str(tmp_path / "output.vrt")
        src_window = (20, 30, 40, 50)

        build_windowed_vrt_from_window(test_raster, vrt_path, src_window)

        src_ds = gdal.Open(test_raster)
        src_data = src_ds.GetRasterBand(1).ReadAsArray(
            xoff=src_window[0],
            yoff=src_window[1],
            win_xsize=src_window[2],
            win_ysize=src_window[3],
        )
        src_ds = None

        vrt_ds = gdal.Open(vrt_path)
        vrt_data = vrt_ds.GetRasterBand(1).ReadAsArray()
        vrt_ds = None

        assert src_data.shape == vrt_data.shape
        assert np.array_equal(src_data, vrt_data)


class TestErrorHandling:
    """Tests for error handling."""

    def test_missing_file(self):
        """Raises exception for missing file."""
        with pytest.raises((FileNotFoundError, RuntimeError)):
            calculate_src_window("/nonexistent/path.tif", (0, 0, 1, 1), "EPSG:4326")

    def test_invalid_bbox_length(self, test_raster):
        """Raises ValueError for invalid bbox length."""
        with pytest.raises(ValueError):
            calculate_src_window(test_raster, (0, 0, 1), "EPSG:4326")

    def test_negative_pad_px(self, test_raster):
        """Raises ValueError for negative pad_px."""
        bbox = (500200, 4999200, 500800, 4999800)
        with pytest.raises(ValueError):
            calculate_src_window(test_raster, bbox, "EPSG:32617", pad_px=-1)

    def test_bbox_outside_raster(self, test_raster):
        """Raises ValueError for bbox completely outside raster."""
        bbox = (600000, 6000000, 600100, 6000100)
        with pytest.raises(ValueError):
            calculate_src_window(test_raster, bbox, "EPSG:32617")

    def test_invalid_src_window_length(self, test_raster, tmp_path):
        """Raises ValueError for invalid src_window length."""
        vrt_path = str(tmp_path / "output.vrt")
        with pytest.raises(ValueError):
            build_windowed_vrt_from_window(test_raster, vrt_path, (10, 10, 50))
