from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import wepppy.rq.wepp_rq_dss as dss_helpers

pytestmark = pytest.mark.unit


def _feature(topaz_id: int, key: str = "TopazID") -> dict[str, object]:
    return {
        "type": "Feature",
        "properties": {key: topaz_id},
        "geometry": {"type": "LineString", "coordinates": [[0, 0], [1, 1]]},
    }


def test_resolve_downstream_channel_ids_walks_graph_and_filters_invalid_values() -> None:
    network = {
        2: [1],
        3: [2],
        4: [3],
        1: [4],  # cycle should not loop forever
        "bad": [1],
        5: ["oops"],
    }

    resolved = dss_helpers._resolve_downstream_channel_ids(network, [1, "2", 0, -9, "bad"])

    assert resolved == {1, 2, 3, 4}


def test_extract_channel_topaz_id_reads_supported_property_keys() -> None:
    assert dss_helpers._extract_channel_topaz_id({"properties": {"topazId": "21"}}) == 21
    assert dss_helpers._extract_channel_topaz_id({"properties": {"unknown": 3}}) is None
    assert dss_helpers._extract_channel_topaz_id({"properties": None}) is None


def test_write_dss_channel_geojson_writes_filtered_channels_with_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    channels_geojson = tmp_path / "channels.geojson"
    channels_geojson.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    _feature(10, key="TopazID"),
                    _feature(20, key="topaz_id"),
                    _feature(30, key="topaz"),
                    {"type": "Feature", "properties": {"name": "missing-id"}, "geometry": None},
                ],
            }
        ),
        encoding="utf-8",
    )

    watershed = SimpleNamespace(
        channels_shp=str(channels_geojson),
        network={20: [10], 30: [20]},
    )
    monkeypatch.setattr(dss_helpers.Watershed, "getInstance", lambda _wd: watershed)

    expected_boundary_dir = tmp_path / "export" / "dss" / "boundaries"

    def _fake_build_boundary_features(
        _watershed: object,
        target_boundary_ids: list[int],
        boundary_dir: str,
        *,
        boundary_width_m: float,
    ) -> list[dict[str, object]]:
        assert target_boundary_ids == [10, 20, 30]
        assert Path(boundary_dir) == expected_boundary_dir
        assert boundary_width_m == 120.0
        Path(boundary_dir).mkdir(parents=True, exist_ok=True)
        (Path(boundary_dir) / "bc_20.shp").write_text("shape", encoding="utf-8")
        return [_feature(20)]

    monkeypatch.setattr(dss_helpers, "build_boundary_condition_features", _fake_build_boundary_features)

    buffer_calls: list[tuple[list[int], str, set[int] | None]] = []

    def _fake_write_buffer(
        _watershed: object,
        target_boundary_ids: list[int],
        output_dir: str,
        *,
        boundary_channel_ids: set[int] | None = None,
    ) -> dict[str, str]:
        buffer_calls.append((target_boundary_ids, output_dir, boundary_channel_ids))
        return {
            "buffer_gml": "export/dss/hec_buffer.gml",
            "buffer_shapefile": "export/dss/hec_buffer.shp",
        }

    monkeypatch.setattr(dss_helpers, "write_hec_buffer_gml", _fake_write_buffer)

    dss_helpers._write_dss_channel_geojson(str(tmp_path), [10], boundary_width_m=120.0)

    output_path = tmp_path / "export" / "dss" / "dss_channels.geojson"
    assert output_path.exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert len(payload["features"]) == 4  # 3 selected channels + 1 boundary feature
    metadata = payload["metadata"]
    assert metadata["selected_topaz_ids"] == [10]
    assert metadata["downstream_topaz_ids"] == [10, 20, 30]
    assert metadata["boundary_condition_width_m"] == 120.0
    assert metadata["boundary_feature_count"] == 1
    assert metadata["boundary_shapefiles"] == ["export/dss/boundaries/bc_20.shp"]
    assert metadata["floodplain_polygon"] == "export/dss/hec_buffer.gml"
    assert metadata["floodplain_polygon_shp"] == "export/dss/hec_buffer.shp"
    assert buffer_calls == [([10, 20, 30], str(tmp_path / "export" / "dss"), {10})]


def test_write_dss_channel_geojson_removes_output_when_channel_ids_empty(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "export" / "dss" / "dss_channels.geojson"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("stale", encoding="utf-8")

    dss_helpers._write_dss_channel_geojson(str(tmp_path), [])

    assert not output_path.exists()
