from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

rasterio = pytest.importorskip("rasterio")
from rasterio.transform import from_origin

from wepppyo3.raster_characteristics import identify_mode_single_raster_key


pytestmark = pytest.mark.unit


def _write_raster(
    path: Path,
    data: np.ndarray,
    transform,
    crs: str,
    *,
    nodata: float | int | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    height, width = data.shape
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype=data.dtype,
        crs=crs,
        transform=transform,
        nodata=nodata,
    ) as dst:
        dst.write(data, 1)


def test_identify_mode_single_raster_key_includes_nodata_keys(tmp_path: Path) -> None:
    key_fn = tmp_path / "subwta.tif"
    param_fn = tmp_path / "nlcd.tif"

    transform = from_origin(0.0, 2.0, 1.0, 1.0)
    keys = np.array([[1, 2], [3, 5]], dtype=np.int32)
    nodata_value = -9999
    params = np.array([[10, 11], [nodata_value, nodata_value]], dtype=np.int16)

    _write_raster(key_fn, keys, transform, "EPSG:32611", nodata=0)
    _write_raster(param_fn, params, transform, "EPSG:32611", nodata=nodata_value)

    result = identify_mode_single_raster_key(
        key_fn=str(key_fn),
        parameter_fn=str(param_fn),
        ignore_channels=True,
        ignore_keys=set(),
    )

    assert {str(key) for key in result.keys()} == {"1", "2", "3", "5"}
