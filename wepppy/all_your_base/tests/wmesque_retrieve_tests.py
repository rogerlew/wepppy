"""Network-heavy smoke test for the legacy WMesque raster service."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Sequence

import numpy as np
from numpy.testing import assert_array_equal

from wepppy.all_your_base.geo import read_arc, read_tif, wmesque_retrieve

TEST_DIR = Path("wmesque_data")
DEFAULT_EXTENT = (-120.234375, 38.9505984033, -120.05859375, 39.0871695498)


def run_smoke(extent: Sequence[float] | None = None, cellsize: float = 30.0) -> None:
    """Download a handful of rasters and verify the Arc/GeoTIFF readers agree.

    Parameters
    ----------
    extent:
        Optional bounding box (west, south, east, north) in WGS84 degrees.
        The default matches the historical integration region used by WMesque.
    cellsize:
        Target raster resolution in meters.
    """

    bbox = tuple(extent or DEFAULT_EXTENT)
    if len(bbox) != 4:
        raise ValueError("extent must contain four floating point values")

    if TEST_DIR.exists():
        shutil.rmtree(TEST_DIR)
    TEST_DIR.mkdir(parents=True, exist_ok=True)

    nlcd_tif = TEST_DIR / "nlcd.tif"
    nlcd_asc = TEST_DIR / "nlcd.asc"
    ned_asc = TEST_DIR / "ned.asc"

    wmesque_retrieve("nlcd/2011", bbox, str(nlcd_asc), cellsize)
    wmesque_retrieve("nlcd/2011", bbox, str(nlcd_tif), cellsize)
    wmesque_retrieve("ned1/2016", bbox, str(ned_asc), cellsize)

    data, transform, proj = read_arc(str(nlcd_asc))
    data_tif, transform_tif, proj_tif = read_tif(str(nlcd_tif), dtype=np.int32)
    data_arc_int, transform_arc_int, proj_arc_int = read_arc(
        str(nlcd_asc), dtype=np.int32
    )

    assert data.shape == data_tif.shape == data_arc_int.shape

    assert all(v == v2 for v, v2 in zip(transform, transform_tif))
    assert all(v == v2 for v, v2 in zip(transform, transform_arc_int))
    assert proj == proj_tif == proj_arc_int

    assert_array_equal(data, data_tif)


if __name__ == "__main__":
    run_smoke()
