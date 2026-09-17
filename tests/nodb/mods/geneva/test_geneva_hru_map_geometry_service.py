from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from wepppy.nodb.mods.geneva.collaborators.artifact_io import GenevaArtifactIO
from wepppy.nodb.mods.geneva.collaborators.hru_map_geometry_service import (
    HRU_MAP_FEATURES_RELPATH,
    GenevaHruMapGeometryService,
)


pytestmark = pytest.mark.unit


def _geneva_stub(tmp_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        wd=str(tmp_path),
        artifact_io=GenevaArtifactIO(),
    )


def _write_legend(geneva: SimpleNamespace) -> None:
    geneva.artifact_io.write_json(
        geneva.wd,
        "hru_map_legend.json",
        {
            "schema_version": 1,
            "rows": [
                {
                    "hru_value": 7,
                    "hru_id": "hru_7",
                    "landuse_class": 42,
                    "hsg_group": "C",
                    "burn_severity_class": "moderate",
                    "hydrophobic_class": False,
                    "is_water": False,
                }
            ],
        },
    )


def test_query_feature_collection_returns_unavailable_when_hru_map_missing(tmp_path: Path) -> None:
    service = GenevaHruMapGeometryService()
    geneva = _geneva_stub(tmp_path)

    payload = service.query_feature_collection(geneva)

    assert payload["availability"]["status"] == "unavailable"
    assert payload["availability"]["reason_code"] == "hru_map_missing"
    assert payload["feature_count"] == 0
    assert payload["feature_collection"]["features"] == []


def test_query_feature_collection_returns_cached_geojson(tmp_path: Path) -> None:
    service = GenevaHruMapGeometryService()
    geneva = _geneva_stub(tmp_path)

    _write_legend(geneva)
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin

    source = geneva.artifact_io.resolve_path(geneva.wd, "hru_map.tif")
    with rasterio.open(source, "w", driver="GTiff", width=1, height=1,
                       count=1, dtype="int16", nodata=0, crs="EPSG:4326",
                       transform=from_origin(-116.5, 45.3, 0.1, 0.1)) as dataset:
        dataset.write(np.array([[7]], dtype="int16"), 1)
    service.query_feature_collection(geneva)
    cached = geneva.artifact_io.resolve_path(geneva.wd, HRU_MAP_FEATURES_RELPATH)
    original_version = cached.stat().st_mtime_ns

    payload = service.query_feature_collection(geneva)

    assert payload["availability"]["status"] == "available"
    assert payload["feature_count"] == 1
    assert payload["join_keys"]["primary"] == "hru_value"
    assert payload["feature_collection"]["features"][0]["properties"]["hru_id"] == "hru_7"
    assert payload["bounds_wgs84"] == [-116.5, 45.2, -116.4, 45.3]
    assert cached.stat().st_mtime_ns == original_version


def test_query_feature_collection_materializes_when_cache_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = GenevaHruMapGeometryService()
    geneva = _geneva_stub(tmp_path)

    _write_legend(geneva)
    geneva.artifact_io.write_text(geneva.wd, "hru_map.tif", "placeholder")

    calls: list[dict[str, Any]] = []

    def _fake_materialize(_geneva: Any, *, source_path: Path) -> dict[str, Any]:
        calls.append({"source_path": str(source_path)})
        _geneva.artifact_io.write_json(
            _geneva.wd,
            HRU_MAP_FEATURES_RELPATH,
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"hru_value": 7, "hru_id": "hru_7"},
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[[-116.5, 45.2], [-116.4, 45.2], [-116.4, 45.3], [-116.5, 45.3], [-116.5, 45.2]]],
                        },
                    }
                ],
            },
        )

        return _geneva.artifact_io.read_json(_geneva.wd, HRU_MAP_FEATURES_RELPATH)

    monkeypatch.setattr(
        service,
        "_materialize_feature_collection_from_raster",
        _fake_materialize,
    )

    payload = service.query_feature_collection(geneva)

    assert payload["availability"]["status"] == "available"
    assert payload["feature_count"] == 1
    assert len(calls) == 1
