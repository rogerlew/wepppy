from __future__ import annotations

import os
from typing import Sequence

import numpy as np
import pytest
from numpy.testing import assert_array_equal

from wepppy.all_your_base.geo import read_arc, read_tif, wmesque_retrieve

DEFAULT_EXTENT: Sequence[float] = (
    -120.234375,
    38.9505984033,
    -120.05859375,
    39.0871695498,
)
_RUN_FLAG = "WMESQUE_INTEGRATION"
_TRUE_VALUES = {"1", "true", "yes", "on"}


def _ensure_network_enabled() -> None:
    """Skip the test unless explicitly requested via env flag."""
    if os.getenv(_RUN_FLAG, "").strip().lower() not in _TRUE_VALUES:
        pytest.skip(
            f"Set {_RUN_FLAG}=1 to exercise the remote WMesque raster service."
        )


def _download_fixture(
    bbox: Sequence[float],
    cellsize: float,
    asc_path: str,
    tif_path: str,
    ned_path: str,
) -> None:
    """Invoke the legacy smoke workflow against the remote microservice."""
    try:
        wmesque_retrieve("nlcd/2011", bbox, asc_path, cellsize)
        wmesque_retrieve("nlcd/2011", bbox, tif_path, cellsize)
        wmesque_retrieve("ned1/2016", bbox, ned_path, cellsize)
    except Exception as exc:  # pragma: no cover - network variability
        pytest.skip(f"WMesque service unavailable: {exc}")


@pytest.mark.integration
@pytest.mark.microservice
@pytest.mark.requires_network
@pytest.mark.slow
def test_wmesque_retrieve_aligns_arc_and_tif(tmp_path) -> None:
    """Ensure NLCD rasters agree across ArcGrid and GeoTIFF outputs."""
    _ensure_network_enabled()

    bbox = tuple(DEFAULT_EXTENT)
    cellsize = 30.0

    nlcd_tif = tmp_path / "nlcd.tif"
    nlcd_asc = tmp_path / "nlcd.asc"
    ned_asc = tmp_path / "ned.asc"

    _download_fixture(
        bbox,
        cellsize,
        str(nlcd_asc),
        str(nlcd_tif),
        str(ned_asc),
    )

    data_float, transform_float, proj_float = read_arc(str(nlcd_asc))
    data_tif, transform_tif, proj_tif = read_tif(str(nlcd_tif), dtype=np.int32)
    data_arc_int, transform_arc_int, proj_arc_int = read_arc(
        str(nlcd_asc), dtype=np.int32
    )

    assert data_float.shape == data_tif.shape == data_arc_int.shape
    assert list(transform_float) == list(transform_tif) == list(transform_arc_int)
    assert proj_float == proj_tif == proj_arc_int
    assert ned_asc.exists(), "NED raster retrieval failed"

    assert_array_equal(data_float, data_tif)
