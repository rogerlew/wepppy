"""Regression tests for raster_stacker VRT matching behavior."""

from pathlib import Path

import numpy as np
import pytest
import rasterio
from osgeo import gdal
from rasterio.transform import from_origin

from wepppy.all_your_base.geo import raster_stacker

pytestmark = pytest.mark.integration


def _write_test_tif(path: Path, data: np.ndarray, *, pixel_size: float) -> None:
    transform = from_origin(0.0, 2.0, pixel_size, pixel_size)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=data.shape[0],
        width=data.shape[1],
        count=1,
        dtype=data.dtype,
        crs="EPSG:4326",
        transform=transform,
        nodata=0,
    ) as ds:
        ds.write(data, 1)


def test_raster_stacker_writes_geotiff_when_match_is_vrt(tmp_path: Path) -> None:
    src_fn = tmp_path / "source.tif"
    match_tif = tmp_path / "match.tif"
    match_vrt = tmp_path / "match.vrt"
    dst_fn = tmp_path / "stacked.tif"

    src_data = np.array([[1, 2], [3, 4]], dtype=np.uint8)
    match_data = np.zeros((4, 4), dtype=np.uint8)

    _write_test_tif(src_fn, src_data, pixel_size=1.0)
    _write_test_tif(match_tif, match_data, pixel_size=0.5)

    vrt_ds = gdal.BuildVRT(str(match_vrt), [str(match_tif)])
    assert vrt_ds is not None
    vrt_ds = None

    raster_stacker(str(src_fn), str(match_vrt), str(dst_fn), resample="near")

    with rasterio.open(dst_fn) as dst:
        assert dst.driver == "GTiff"
        assert (dst.width, dst.height) == (4, 4)
        data = dst.read(1)

    assert set(np.unique(data)) == {1, 2, 3, 4}
