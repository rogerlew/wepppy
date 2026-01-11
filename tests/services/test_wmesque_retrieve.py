from __future__ import annotations

import os
from typing import Sequence

import numpy as np
import pytest
from numpy.testing import assert_array_equal

from wepppy.all_your_base.geo import read_arc, read_tif, wmesque_retrieve
from wepppy.all_your_base.geo.webclients import wmesque as wmesque_client

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


@pytest.mark.unit
def test_wmesque_retrieve_appends_bbox_crs(monkeypatch, tmp_path) -> None:
    captured: dict[str, str] = {}

    class _DummyResponse:
        status = 200
        headers: dict[str, str] = {}

        def read(self, _size: int = -1) -> bytes:
            return b""

        def getcode(self) -> int:
            return self.status

        def __enter__(self) -> "_DummyResponse":
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

    def _fake_urlopen(url: str, timeout: int = 0) -> _DummyResponse:
        captured["url"] = url
        return _DummyResponse()

    monkeypatch.setattr(wmesque_client, "urlopen", _fake_urlopen)

    out_fn = tmp_path / "nlcd.tif"
    wmesque_retrieve(
        "nlcd/2019",
        [0.0, 0.0, 1.0, 1.0],
        str(out_fn),
        30.0,
        v=2,
        write_meta=False,
        extent_crs="EPSG:32611",
    )

    assert "bbox_crs=EPSG%3A32611" in captured["url"]


@pytest.mark.unit
def test_wmesque_retrieve_rejects_extent_crs_for_v1(tmp_path) -> None:
    with pytest.raises(ValueError, match="extent_crs"):
        wmesque_retrieve(
            "nlcd/2019",
            [0.0, 0.0, 1.0, 1.0],
            str(tmp_path / "nlcd.tif"),
            30.0,
            v=1,
            write_meta=False,
            extent_crs="EPSG:32611",
        )


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
