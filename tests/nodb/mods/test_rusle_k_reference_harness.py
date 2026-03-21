from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from wepppy.nodb.mods.rusle.k_reference import (
    DEFAULT_REFERENCE_MODE_PRECEDENCE,
    REFERENCE_MODES,
    resolve_reference_mode,
    run_reference_harness,
    sample_reference_k_points,
)


pytestmark = pytest.mark.unit


def _write_test_raster(path: Path, data: np.ndarray, *, nodata: float = -9999.0) -> None:
    profile = {
        "driver": "GTiff",
        "height": int(data.shape[0]),
        "width": int(data.shape[1]),
        "count": 1,
        "dtype": "float32",
        "crs": "EPSG:4326",
        "transform": from_origin(0.0, 2.0, 1.0, 1.0),
        "nodata": nodata,
    }
    with rasterio.open(path, "w", **profile) as dataset:
        dataset.write(data.astype(np.float32), 1)


def test_reference_modes_contract() -> None:
    assert set(REFERENCE_MODES) == {
        "gnatsgo_kffact",
        "gnatsgo_kwfact",
        "gssurgo_kffact",
        "gssurgo_kwfact",
    }


def test_sample_reference_k_points_reads_values_and_nodata(tmp_path: Path) -> None:
    raster_path = tmp_path / "gssurgo_kffact.tif"
    _write_test_raster(
        raster_path,
        np.asarray(
            [
                [0.10, 0.20],
                [0.30, -9999.0],
            ]
        ),
    )

    points = [
        {"point_id": "p00", "x": 0.5, "y": 1.5},
        {"point_id": "p01", "x": 1.5, "y": 1.5},
        {"point_id": "p10", "x": 0.5, "y": 0.5},
        {"point_id": "p11", "x": 1.5, "y": 0.5},
    ]

    samples = sample_reference_k_points(
        mode="gssurgo_kffact",
        reference_raster=str(raster_path),
        points=points,
    )

    by_id = {sample.point_id: sample for sample in samples}
    assert by_id["p00"].value == pytest.approx(0.10)
    assert by_id["p01"].value == pytest.approx(0.20)
    assert by_id["p10"].value == pytest.approx(0.30)
    assert by_id["p11"].value is None
    assert by_id["p11"].is_nodata is True


def test_resolve_reference_mode_uses_precedence(tmp_path: Path) -> None:
    gnatsgo_path = tmp_path / "gnatsgo_kffact.tif"
    gssurgo_path = tmp_path / "gssurgo_kffact.tif"

    _write_test_raster(gnatsgo_path, np.full((1, 1), 0.2))
    _write_test_raster(gssurgo_path, np.full((1, 1), 0.3))

    mode, path = resolve_reference_mode(
        {
            "gnatsgo_kffact": str(gnatsgo_path),
            "gssurgo_kffact": str(gssurgo_path),
        },
        precedence=DEFAULT_REFERENCE_MODE_PRECEDENCE,
    )

    assert mode == "gssurgo_kffact"
    assert path == str(gssurgo_path)


def test_run_reference_harness_returns_samples(tmp_path: Path) -> None:
    raster_path = tmp_path / "gssurgo_kffact.tif"
    _write_test_raster(raster_path, np.asarray([[0.42]], dtype=np.float32))

    payload = run_reference_harness(
        reference_paths={"gssurgo_kffact": str(raster_path)},
        points=[{"point_id": "p0", "x": 0.5, "y": 1.5}],
    )

    assert payload["mode"] == "gssurgo_kffact"
    assert payload["samples"][0]["point_id"] == "p0"
    assert payload["samples"][0]["value"] == pytest.approx(0.42)
