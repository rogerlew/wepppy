import json
from pathlib import Path

import numpy as np
import pytest

from wepppy.nodb.culverts_runner import CulvertsRunner


pytestmark = [pytest.mark.integration]

rasterio = pytest.importorskip("rasterio")
pytest.importorskip("geopandas")
from rasterio.transform import from_origin


def _write_raster(path: Path, data: np.ndarray, transform, crs: str) -> None:
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
        nodata=0,
    ) as dst:
        dst.write(data, 1)


def _write_watersheds_geojson(
    path: Path,
    *,
    coords: list[list[list[float]]],
    crs_name: str | None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    feature = {
        "type": "Feature",
        "properties": {"Point_ID": 1},
        "geometry": {
            "type": "Polygon",
            "coordinates": coords,
        },
    }
    payload: dict[str, object] = {
        "type": "FeatureCollection",
        "features": [feature],
    }
    if crs_name is not None:
        payload["crs"] = {"type": "name", "properties": {"name": crs_name}}
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_build_raster_mask_respects_projected_crs(tmp_path: Path) -> None:
    template_path = tmp_path / "template.tif"
    transform = from_origin(500000.0, 4100020.0, 10.0, 10.0)
    data = np.zeros((3, 3), dtype=np.uint8)
    _write_raster(template_path, data, transform, "EPSG:32611")

    watersheds_path = tmp_path / "watersheds.geojson"
    coords = [
        [
            [500000.0, 4100000.0],
            [500020.0, 4100000.0],
            [500020.0, 4100020.0],
            [500000.0, 4100020.0],
            [500000.0, 4100000.0],
        ]
    ]
    _write_watersheds_geojson(
        watersheds_path,
        coords=coords,
        crs_name="EPSG:32611",
    )

    runner = CulvertsRunner(str(tmp_path), "culvert.cfg")
    feature = runner.load_watershed_features(str(watersheds_path))["1"]
    mask_path = tmp_path / "mask.tif"
    feature.build_raster_mask(str(template_path), str(mask_path))

    with rasterio.open(mask_path) as src:
        mask = src.read(1)
    assert int(mask.sum()) == 4


def test_build_raster_mask_defaults_to_wgs84(tmp_path: Path) -> None:
    template_path = tmp_path / "template.tif"
    transform = from_origin(-120.0, 45.02, 0.01, 0.01)
    data = np.zeros((3, 3), dtype=np.uint8)
    _write_raster(template_path, data, transform, "EPSG:4326")

    watersheds_path = tmp_path / "watersheds.geojson"
    coords = [
        [
            [-120.0, 45.0],
            [-119.98, 45.0],
            [-119.98, 45.02],
            [-120.0, 45.02],
            [-120.0, 45.0],
        ]
    ]
    _write_watersheds_geojson(
        watersheds_path,
        coords=coords,
        crs_name=None,
    )

    runner = CulvertsRunner(str(tmp_path), "culvert.cfg")
    feature = runner.load_watershed_features(str(watersheds_path))["1"]
    mask_path = tmp_path / "mask.tif"
    feature.build_raster_mask(str(template_path), str(mask_path))

    with rasterio.open(mask_path) as src:
        mask = src.read(1)
    assert int(mask.sum()) == 4
