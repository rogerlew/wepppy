from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import wepppy.nodb.mods.roads.roads as roads_module
from wepppy.nodb.mods.roads.monotonic_segments import MonotonicConversionSummary
from wepppy.nodb.mods.roads.roads import Roads

from ._support import _write_roads_geojson

pytestmark = [pytest.mark.unit, pytest.mark.nodb]


def test_prepare_segments_writes_summary_and_marks_prepared(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    source_path = tmp_path / "input.geojson"
    _write_roads_geojson(source_path)

    relief_path = tmp_path / "dem" / "wbt" / "relief.tif"
    netful_path = tmp_path / "dem" / "wbt" / "netful.tif"
    subwta_path = tmp_path / "dem" / "wbt" / "subwta.tif"
    relief_path.parent.mkdir(parents=True, exist_ok=True)
    relief_path.write_text("relief", encoding="utf-8")
    netful_path.write_text("netful", encoding="utf-8")
    subwta_path.write_text("subwta", encoding="utf-8")

    monkeypatch.setattr(
        Roads,
        "ron_instance",
        property(lambda self: SimpleNamespace(dem_fn=str(tmp_path / "dem" / "dem.vrt"))),
    )
    monkeypatch.setattr(
        Roads,
        "watershed_instance",
        property(
            lambda self: SimpleNamespace(
                delineation_backend_is_wbt=True,
                relief=str(relief_path),
                netful=str(netful_path),
                subwta=str(subwta_path),
            )
        ),
    )
    controller.set_enabled(True)
    controller.set_uploaded_geojson(str(source_path))

    def _fake_convert(**kwargs):
        assert tuple(kwargs["design_property_keys"]) == ("DESIGN", "design")
        output_geojson_path = Path(kwargs["output_geojson_path"])
        output_geojson_path.parent.mkdir(parents=True, exist_ok=True)
        output_geojson_path.write_text(
            json.dumps(
                {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 1.0]]},
                            "properties": {
                                "segment_id": "roads-seg-000001",
                                "DESIGN": "Inslope_bd",
                                "topaz_id_chn_lowpoint": 24,
                                "topaz_id_hill_lowpoint": 21,
                                "_roads_routing_eligibility": "channel_associated",
                                "_roads_non_channel_routable": False,
                            },
                        },
                        {
                            "type": "Feature",
                            "geometry": {"type": "LineString", "coordinates": [[1.0, 1.0], [2.0, 2.0]]},
                            "properties": {
                                "segment_id": "roads-seg-000002",
                                "DESIGN": "NotEligible",
                                "topaz_id_chn_lowpoint": None,
                                "topaz_id_hill_lowpoint": None,
                                "_roads_routing_eligibility": "design_not_eligible",
                                "_roads_non_channel_routable": False,
                            },
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        Path(kwargs["low_points_output_geojson_path"]).write_text(
            json.dumps({"type": "FeatureCollection", "features": []}),
            encoding="utf-8",
        )
        return MonotonicConversionSummary(
            input_feature_count=1,
            output_feature_count=2,
            split_feature_count=1,
            low_point_feature_count=2,
            sample_step_m=1.0,
            tolerance_m=0.5,
        )

    monkeypatch.setattr(roads_module, "convert_geojson_file_to_monotonic_segments", _fake_convert)

    summary = controller.prepare_segments()
    status = controller.query_status()

    assert summary["eligible_segment_count"] == 1
    assert summary["eligible_with_lowpoint_ids"] == 1
    assert summary["eligible_channel_associated_count"] == 1
    assert summary["eligible_non_channel_routable_count"] == 0
    assert summary["eligible_non_routable_count"] == 0
    assert summary["eligible_lowpoint_decision_counts"] == {"unknown": 1}
    assert summary["eligible_routing_eligibility_counts"] == {"channel_associated": 1}
    assert summary["design_property_keys"] == ["DESIGN", "design"]
    assert summary["mapping_warning_count"] == 0
    assert summary["prepare_raster_paths"] == {
        "dem_path": "dem/wbt/relief.tif",
        "channel_raster_path": "dem/wbt/netful.tif",
        "topaz_id_raster_path": "dem/wbt/subwta.tif",
    }
    assert summary["roads_log_relpath"] == "wepp/roads/roads.log"
    assert status["status"] == "prepared"
    assert Path(controller.roads_summary_path).exists()
    assert Path(controller.roads_monotonic_geojson_path).exists()
    assert Path(controller.roads_low_points_geojson_path).exists()
    assert Path(controller.roads_log_path).exists()


def test_prepare_segments_counts_non_channel_routable_segments(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    source_path = tmp_path / "input.geojson"
    _write_roads_geojson(source_path)

    relief_path = tmp_path / "dem" / "wbt" / "relief.tif"
    netful_path = tmp_path / "dem" / "wbt" / "netful.tif"
    subwta_path = tmp_path / "dem" / "wbt" / "subwta.tif"
    relief_path.parent.mkdir(parents=True, exist_ok=True)
    relief_path.write_text("relief", encoding="utf-8")
    netful_path.write_text("netful", encoding="utf-8")
    subwta_path.write_text("subwta", encoding="utf-8")

    monkeypatch.setattr(
        Roads,
        "ron_instance",
        property(lambda self: SimpleNamespace(dem_fn=str(tmp_path / "dem" / "dem.vrt"))),
    )
    monkeypatch.setattr(
        Roads,
        "watershed_instance",
        property(
            lambda self: SimpleNamespace(
                delineation_backend_is_wbt=True,
                relief=str(relief_path),
                netful=str(netful_path),
                subwta=str(subwta_path),
            )
        ),
    )
    controller.set_enabled(True)
    controller.set_uploaded_geojson(str(source_path))

    def _fake_convert(**kwargs):
        Path(kwargs["output_geojson_path"]).parent.mkdir(parents=True, exist_ok=True)
        Path(kwargs["output_geojson_path"]).write_text(
            json.dumps(
                {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 1.0]]},
                            "properties": {
                                "segment_id": "roads-seg-000101",
                                "DESIGN": "Inslope_bd",
                                "topaz_id_chn_lowpoint": None,
                                "topaz_id_hill_lowpoint": None,
                                "_roads_lowpoint_decision": "non_channel_hillslope_routable",
                                "_roads_routing_eligibility": "non_channel_routable",
                                "_roads_non_channel_routable": True,
                                "_roads_lowpoint_row": 1,
                                "_roads_lowpoint_col": 2,
                            },
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        Path(kwargs["low_points_output_geojson_path"]).write_text(
            json.dumps({"type": "FeatureCollection", "features": []}),
            encoding="utf-8",
        )
        return MonotonicConversionSummary(
            input_feature_count=1,
            output_feature_count=1,
            split_feature_count=0,
            low_point_feature_count=1,
            sample_step_m=1.0,
            tolerance_m=0.5,
        )

    monkeypatch.setattr(roads_module, "convert_geojson_file_to_monotonic_segments", _fake_convert)

    summary = controller.prepare_segments()

    assert summary["eligible_segment_count"] == 1
    assert summary["eligible_with_lowpoint_ids"] == 0
    assert summary["eligible_channel_associated_count"] == 0
    assert summary["eligible_non_channel_routable_count"] == 1
    assert summary["eligible_non_routable_count"] == 0
    assert summary["eligible_lowpoint_decision_counts"] == {"non_channel_hillslope_routable": 1}
    assert summary["eligible_routing_eligibility_counts"] == {"non_channel_routable": 1}


def test_prepare_segments_infers_project_crs_for_projected_geojson_without_crs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    source_path = tmp_path / "input.geojson"
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[464000.0, 5024000.0], [464010.0, 5024010.0]],
                },
                "properties": {"DESIGN": "Inslope_bd"},
            }
        ],
    }
    source_path.write_text(json.dumps(payload), encoding="utf-8")

    relief_path = tmp_path / "dem" / "wbt" / "relief.tif"
    netful_path = tmp_path / "dem" / "wbt" / "netful.tif"
    subwta_path = tmp_path / "dem" / "wbt" / "subwta.tif"
    relief_path.parent.mkdir(parents=True, exist_ok=True)
    relief_path.write_text("relief", encoding="utf-8")
    netful_path.write_text("netful", encoding="utf-8")
    subwta_path.write_text("subwta", encoding="utf-8")

    monkeypatch.setattr(
        Roads,
        "ron_instance",
        property(lambda self: SimpleNamespace(dem_fn=str(tmp_path / "dem" / "dem.vrt"))),
    )
    monkeypatch.setattr(
        Roads,
        "watershed_instance",
        property(
            lambda self: SimpleNamespace(
                delineation_backend_is_wbt=True,
                relief=str(relief_path),
                netful=str(netful_path),
                subwta=str(subwta_path),
            )
        ),
    )

    class _FakeDataset:
        crs = "EPSG:32610"
        bounds = SimpleNamespace(
            left=463900.0,
            bottom=5023900.0,
            right=464200.0,
            top=5024200.0,
        )

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(roads_module.rasterio, "open", lambda *_args, **_kwargs: _FakeDataset())

    controller.set_enabled(True)
    controller.set_uploaded_geojson(str(source_path))

    attempted_input_crs: list[str] = []

    def _fake_convert(**kwargs):
        attempted_input_crs.append(str(kwargs["input_crs"]))
        if kwargs["input_crs"] == "EPSG:4326":
            raise ValueError(
                "Road feature at index 0 part 0 transformed to non-finite DEM coordinates at vertex 0. "
                "This usually means the uploaded road coordinates do not match roads input_crs='EPSG:4326'."
            )

        Path(kwargs["output_geojson_path"]).parent.mkdir(parents=True, exist_ok=True)
        Path(kwargs["output_geojson_path"]).write_text(
            json.dumps(
                {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 1.0]]},
                            "properties": {
                                "segment_id": "roads-seg-000201",
                                "DESIGN": "Inslope_bd",
                                "topaz_id_chn_lowpoint": 24,
                                "topaz_id_hill_lowpoint": 21,
                                "_roads_lowpoint_decision": "mapped",
                                "_roads_routing_eligibility": "channel_associated",
                                "_roads_non_channel_routable": False,
                            },
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        Path(kwargs["low_points_output_geojson_path"]).write_text(
            json.dumps({"type": "FeatureCollection", "features": []}),
            encoding="utf-8",
        )
        return MonotonicConversionSummary(
            input_feature_count=1,
            output_feature_count=1,
            split_feature_count=0,
            low_point_feature_count=1,
            sample_step_m=1.0,
            tolerance_m=0.5,
        )

    monkeypatch.setattr(roads_module, "convert_geojson_file_to_monotonic_segments", _fake_convert)

    summary = controller.prepare_segments()
    state = controller.query_summary()

    assert attempted_input_crs == ["EPSG:32610"]
    assert summary["configured_input_crs"] == "EPSG:32610"
    assert summary["source_crs"] is None
    assert summary["input_crs"] == "EPSG:32610"
    assert summary["input_crs_source"] == "inferred_project_utm_coordinates"
    assert state["roads_params"]["input_crs"] == "EPSG:32610"


def test_prepare_segments_infers_wgs_for_degree_coordinates_without_crs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    source_path = tmp_path / "input.geojson"
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[-123.45, 45.12], [-123.44, 45.11]],
                },
                "properties": {"DESIGN": "Inslope_bd"},
            }
        ],
    }
    source_path.write_text(json.dumps(payload), encoding="utf-8")

    relief_path = tmp_path / "dem" / "wbt" / "relief.tif"
    netful_path = tmp_path / "dem" / "wbt" / "netful.tif"
    subwta_path = tmp_path / "dem" / "wbt" / "subwta.tif"
    relief_path.parent.mkdir(parents=True, exist_ok=True)
    relief_path.write_text("relief", encoding="utf-8")
    netful_path.write_text("netful", encoding="utf-8")
    subwta_path.write_text("subwta", encoding="utf-8")

    monkeypatch.setattr(
        Roads,
        "ron_instance",
        property(lambda self: SimpleNamespace(dem_fn=str(tmp_path / "dem" / "dem.vrt"))),
    )
    monkeypatch.setattr(
        Roads,
        "watershed_instance",
        property(
            lambda self: SimpleNamespace(
                delineation_backend_is_wbt=True,
                relief=str(relief_path),
                netful=str(netful_path),
                subwta=str(subwta_path),
            )
        ),
    )

    class _FakeDataset:
        crs = "EPSG:32610"
        bounds = SimpleNamespace(
            left=463900.0,
            bottom=5023900.0,
            right=464200.0,
            top=5024200.0,
        )

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(roads_module.rasterio, "open", lambda *_args, **_kwargs: _FakeDataset())

    controller.set_enabled(True)
    controller.set_uploaded_geojson(str(source_path))

    attempted_input_crs: list[str] = []

    def _fake_convert(**kwargs):
        attempted_input_crs.append(str(kwargs["input_crs"]))
        Path(kwargs["output_geojson_path"]).parent.mkdir(parents=True, exist_ok=True)
        Path(kwargs["output_geojson_path"]).write_text(
            json.dumps(
                {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 1.0]]},
                            "properties": {
                                "segment_id": "roads-seg-000202",
                                "DESIGN": "Inslope_bd",
                                "topaz_id_chn_lowpoint": 24,
                                "topaz_id_hill_lowpoint": 21,
                                "_roads_lowpoint_decision": "mapped",
                                "_roads_routing_eligibility": "channel_associated",
                                "_roads_non_channel_routable": False,
                            },
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        Path(kwargs["low_points_output_geojson_path"]).write_text(
            json.dumps({"type": "FeatureCollection", "features": []}),
            encoding="utf-8",
        )
        return MonotonicConversionSummary(
            input_feature_count=1,
            output_feature_count=1,
            split_feature_count=0,
            low_point_feature_count=1,
            sample_step_m=1.0,
            tolerance_m=0.5,
        )

    monkeypatch.setattr(roads_module, "convert_geojson_file_to_monotonic_segments", _fake_convert)

    summary = controller.prepare_segments()
    state = controller.query_summary()

    assert attempted_input_crs == ["EPSG:4326"]
    assert summary["input_crs"] == "EPSG:4326"
    assert summary["input_crs_source"] == "inferred_wgs84_coordinates"
    assert state["roads_params"]["input_crs"] == "EPSG:4326"
