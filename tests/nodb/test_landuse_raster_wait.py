from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

rasterio = pytest.importorskip("rasterio")
from rasterio.transform import from_origin

from wepppy.nodb.core.landuse import _wait_for_gdal_openable_raster


pytestmark = pytest.mark.unit


def _write_raster(path: Path, data: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    transform = from_origin(0.0, 2.0, 1.0, 1.0)
    height, width = data.shape
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype=data.dtype,
        crs="EPSG:32611",
        transform=transform,
        nodata=0,
    ) as dst:
        dst.write(data, 1)


def test_wait_for_gdal_openable_raster_returns_when_present(tmp_path: Path) -> None:
    raster_fn = tmp_path / "raster.tif"
    _write_raster(raster_fn, np.array([[1, 2], [3, 4]], dtype=np.int16))

    _wait_for_gdal_openable_raster(str(raster_fn), timeout_s=0.0, poll_s=0.01, logger=None)


def test_wait_for_gdal_openable_raster_raises_when_missing(tmp_path: Path) -> None:
    raster_fn = tmp_path / "missing.tif"

    with pytest.raises(FileNotFoundError):
        _wait_for_gdal_openable_raster(str(raster_fn), timeout_s=0.0, poll_s=0.01, logger=None)

