from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from rasterio.transform import from_origin

from wepppy.nodb.mods.ag_fields import AgFields

geopandas = pytest.importorskip("geopandas")
if getattr(geopandas, "__wepppy_stub__", False):
    pytest.skip("geopandas stubbed", allow_module_level=True)

rasterio = pytest.importorskip("rasterio")

pytestmark = [pytest.mark.unit, pytest.mark.nodb]


def _write_dem(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=20,
        width=20,
        count=1,
        dtype="float32",
        crs="EPSG:32610",
        transform=from_origin(463990.0, 5024010.0, 1.0, 1.0),
        nodata=-9999.0,
    ) as dataset:
        dataset.write(np.ones((1, 20, 20), dtype=np.float32))


def test_rasterize_field_boundaries_geojson_infers_project_crs_when_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = AgFields(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    geojson_path = Path(controller.ag_fields_dir) / "fields.WGS.geojson"
    geojson_path.parent.mkdir(parents=True, exist_ok=True)
    geojson_path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"field_id": 7},
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [
                                [
                                    [464000.0, 5024000.0],
                                    [464000.0, 5024005.0],
                                    [464005.0, 5024005.0],
                                    [464005.0, 5024000.0],
                                    [464000.0, 5024000.0],
                                ]
                            ],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with controller.locked():
        controller._field_boundaries_geojson = "fields.WGS.geojson"
        controller._field_id_key = "field_id"

    dem_path = tmp_path / "dem" / "dem.tif"
    _write_dem(dem_path)

    monkeypatch.setattr(
        AgFields,
        "ron_instance",
        property(lambda self: SimpleNamespace(dem_fn=str(dem_path))),
    )

    controller.rasterize_field_boundaries_geojson()

    with rasterio.open(controller.field_boundaries_tif) as dataset:
        burned = dataset.read(1)
        assert str(dataset.crs) == "EPSG:32610"

    assert burned.max() == 7
    assert np.count_nonzero(burned == 7) > 0
