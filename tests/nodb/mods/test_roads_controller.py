from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from pyproj import CRS, Geod

import pytest

import wepppy.nodb.wepp_nodb_post_utils as post_utils_module
import wepppy.nodb.mods.roads.roads as roads_module
import wepppy.wepp.interchange as interchange_module
import wepppyo3.wepp_interchange as wepp_interchange_module
from wepppy.nodb.mods.roads.monotonic_segments import MonotonicConversionSummary
from wepppy.nodb.mods.roads.roads import Roads

pytestmark = [pytest.mark.unit, pytest.mark.nodb]


def _write_roads_geojson(path: Path, *, crs: dict[str, object] | None = None) -> None:
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[-116.0, 45.0], [-116.0005, 45.0005]],
                },
                "properties": {"DESIGN": "Inslope_bd"},
            }
        ],
    }
    if crs is not None:
        payload["crs"] = crs
    path.write_text(json.dumps(payload), encoding="utf-8")


def _seed_prepared_state(controller: Roads, *, upload_sha: str = "seed-upload-sha") -> None:
    params = dict(getattr(controller, "_roads_params", controller._default_params()))
    with controller.locked():
        controller._uploaded_geojson_sha256 = upload_sha
        controller._last_prepare_summary = {
            "uploaded_geojson_sha256": upload_sha,
            "roads_params_signature": controller._params_signature(params),
        }
        controller._status = "prepared"


def _write_prepared_segments(controller: Roads, payload: dict[str, object]) -> None:
    path = Path(controller.roads_monotonic_geojson_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_segment_manifest(controller: Roads, rows: list[dict[str, object]]) -> None:
    path = Path(controller.roads_segment_pass_manifest_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows), encoding="utf-8")


def _write_minimal_pass(path: Path, *, climate_token: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                climate_token,
                "   16      2000",
                ".44409E+04",
                "  5    0.20000E-05 0.10000E-04 0.30000E-04 0.30600E-03 0.20000E-03",
                "    0.00     0.00     0.00     0.00",
                "NO EVENT   2000     1      0.64000E-01 0.00000E+00",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _ready_report_resources_stub(controller: Roads) -> dict[str, object]:
    relpath = "wepp/roads/output/interchange/README.md"
    return {
        "status": "ready",
        "output_scope": "roads",
        "roads_output_relpath": "wepp/roads/output",
        "interchange_relpath": "wepp/roads/output/interchange",
        "required_relpaths": [relpath],
        "missing_relpaths": [],
        "generated_at": 1234567890,
    }


def test_set_uploaded_geojson_stages_file_and_checksum(tmp_path: Path) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    source_path = tmp_path / "input.geojson"
    _write_roads_geojson(source_path)

    summary = controller.set_uploaded_geojson(str(source_path))

    staged_path = tmp_path / summary["uploaded_geojson_relpath"]
    assert staged_path.exists()
    assert staged_path.read_text(encoding="utf-8") == source_path.read_text(encoding="utf-8")
    assert summary["uploaded_geojson_sha256"] == hashlib.sha256(staged_path.read_bytes()).hexdigest()
    assert summary["feature_count"] == 1


def test_set_uploaded_geojson_uses_geojson_crs_when_present(tmp_path: Path) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    source_path = tmp_path / "input.geojson"
    _write_roads_geojson(
        source_path,
        crs={"type": "name", "properties": {"name": "EPSG:32610"}},
    )

    summary = controller.set_uploaded_geojson(str(source_path))
    state = controller.query_summary()

    assert summary["configured_input_crs"] == "EPSG:4326"
    assert summary["source_crs"] == "EPSG:32610"
    assert summary["effective_input_crs"] == "EPSG:32610"
    assert summary["input_crs_source"] == "geojson_crs"
    assert state["roads_params"]["input_crs"] == "EPSG:32610"


def test_set_uploaded_geojson_discovers_attributes_and_auto_maps(tmp_path: Path) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    source_path = tmp_path / "input.geojson"
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": [[-116.0, 45.0], [-116.0005, 45.0005]]},
                "properties": {
                    "DESIGN": "Inslope_bd",
                    "SURFACE": "gravel",
                    "ROAD_SURFACE": "asphalt",
                    "TRAFFIC": "low",
                    "CONDITION": "year round",
                },
            }
        ],
    }
    source_path.write_text(json.dumps(payload), encoding="utf-8")

    summary = controller.set_uploaded_geojson(str(source_path))

    assert summary["attribute_field_map"]["design"] == "DESIGN"
    assert summary["attribute_field_map"]["surface"] == "SURFACE"
    assert summary["attribute_field_map"]["traffic"] == "TRAFFIC"
    catalog = summary["discovered_attribute_catalog"]
    assert "DESIGN" in catalog["field_names"]
    assert "ROAD_SURFACE" in catalog["field_names"]
    assert catalog["field_count"] == 5

    query = controller.query_summary()
    assert query["discovered_attribute_catalog"]["field_count"] == 5
    assert query["attribute_field_map"]["traffic"] == "TRAFFIC"


def test_set_params_updates_state_and_clears_stale_summaries(tmp_path: Path) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")

    with controller.locked():
        controller._last_prepare_summary = {"prepared": True}
        controller._last_run_summary = {"completed": True}
        controller._status = "completed"
        controller._errors = ["old error"]

    params = controller.set_params({"tolerance_m": 0.25, "soil_texture_default": "CLAY"})
    state = controller.query_summary()

    assert params["tolerance_m"] == pytest.approx(0.25)
    assert params["soil_texture_default"] == "clay"
    assert state["last_prepare_summary"] is None
    assert state["last_run_summary"] is None
    assert state["status"] == "idle"
    assert state["errors"] == []


def test_set_params_validates_attribute_field_map_against_discovered_fields(tmp_path: Path) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    source_path = tmp_path / "input.geojson"
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": [[-116.0, 45.0], [-116.0005, 45.0005]]},
                "properties": {"ROADTYPE": "Inslope_bd", "TRAF_VALUE": "high"},
            }
        ],
    }
    source_path.write_text(json.dumps(payload), encoding="utf-8")
    controller.set_uploaded_geojson(str(source_path))

    params = controller.set_params({"attribute_field_map": {"design": "ROADTYPE", "traffic": "TRAF_VALUE"}})
    assert params["attribute_field_map"]["design"] == "ROADTYPE"
    assert params["attribute_field_map"]["traffic"] == "TRAF_VALUE"

    with pytest.raises(ValueError, match="not present in discovered attributes"):
        controller.set_params({"attribute_field_map": {"design": "MISSING_FIELD"}})


def test_resolve_segment_run_inputs_uses_user_defaults_when_mapped_fields_are_missing(tmp_path: Path) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    controller.set_params(
        {
            "attribute_field_map": {
                "surface": "SURFACE_MAIN",
                "traffic": "TRAFFIC_MAIN",
            },
            "surface_default": "paved",
            "traffic_default": "high",
        }
    )
    params = controller.query_summary()["roads_params"]
    warning_counts: Counter[str] = Counter()
    warning_examples: list[dict[str, object]] = []

    resolved = controller._resolve_segment_run_inputs(
        properties={
            "SURFACE": "gravel",
            "TRAFFIC": "none",
            "SOIL_TEXTURE": "loam",
            "RFG_PCT": 12,
            "WIDTH_M": 6.0,
        },
        params=params,
        segment_id="roads-seg-000001",
        design="inslope_bd",
        warning_counts=warning_counts,
        warning_examples=warning_examples,
        warning_limit=10,
    )

    assert resolved["surface"] == "paved"
    assert resolved["traffic"] == "high"
    assert resolved["resolution_sources"]["surface"] == "mapped_default_value"
    assert resolved["resolution_sources"]["traffic"] == "mapped_default_value"
    assert warning_counts["surface_mapped_primary_missing"] == 1
    assert warning_counts["traffic_mapped_primary_missing"] == 1


def test_resolve_segment_run_inputs_supports_outslope_rutted_fill_defaults_and_overrides(tmp_path: Path) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    controller.set_params(
        {
            "fill_length_default_m": 42.0,
            "fill_slope_default_pct": 14.0,
        }
    )
    params = controller.query_summary()["roads_params"]

    warning_counts: Counter[str] = Counter()
    warning_examples: list[dict[str, object]] = []
    resolved_default = controller._resolve_segment_run_inputs(
        properties={"DESIGN": "outslope_rutted"},
        params=params,
        segment_id="roads-seg-000900",
        design="outslope_rutted",
        warning_counts=warning_counts,
        warning_examples=warning_examples,
        warning_limit=10,
    )

    assert resolved_default["fill_length_m"] == pytest.approx(42.0)
    assert resolved_default["fill_slope_pct"] == pytest.approx(14.0)
    assert resolved_default["resolution_sources"]["fill_length_m"] == "roads_default"
    assert resolved_default["resolution_sources"]["fill_slope_pct"] == "roads_default"

    resolved_override = controller._resolve_segment_run_inputs(
        properties={
            "DESIGN": "outslope_rutted",
            "FILL_LENGTH_M": 18.0,
            "FILL_SLOPE_PCT": 9.5,
        },
        params=params,
        segment_id="roads-seg-000901",
        design="outslope_rutted",
        warning_counts=warning_counts,
        warning_examples=warning_examples,
        warning_limit=10,
    )

    assert resolved_override["fill_length_m"] == pytest.approx(18.0)
    assert resolved_override["fill_slope_pct"] == pytest.approx(9.5)
    assert resolved_override["resolution_sources"]["fill_length_m"] == "segment_property"
    assert resolved_override["resolution_sources"]["fill_slope_pct"] == "segment_property"


def test_set_enabled_requires_wbt_backend(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    monkeypatch.setattr(
        Roads,
        "watershed_instance",
        property(lambda self: SimpleNamespace(delineation_backend_is_wbt=False)),
    )

    with pytest.raises(ValueError, match="requires WBT delineation backend"):
        controller.set_enabled(True)


def test_set_params_rejects_invalid_enum_defaults(tmp_path: Path) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")

    with pytest.raises(ValueError, match="soil_texture_default"):
        controller.set_params({"soil_texture_default": "peat"})
    with pytest.raises(ValueError, match="surface_default"):
        controller.set_params({"surface_default": "ice"})
    with pytest.raises(ValueError, match="traffic_default"):
        controller.set_params({"traffic_default": "medium"})


def test_set_params_rejects_invalid_fill_defaults(tmp_path: Path) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")

    with pytest.raises(ValueError, match="fill_length_default_m"):
        controller.set_params({"fill_length_default_m": 0})
    with pytest.raises(ValueError, match="fill_slope_default_pct"):
        controller.set_params({"fill_slope_default_pct": "nan-text"})


def test_set_params_enforces_phase4_numeric_bounds(tmp_path: Path) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")

    assert controller.query_summary()["roads_params"]["rfg_pct_default"] == pytest.approx(20.0)

    with pytest.raises(ValueError, match="rfg_pct_default"):
        controller.set_params({"rfg_pct_default": 101})
    with pytest.raises(ValueError, match="road_width_m_default"):
        controller.set_params({"road_width_m_default": 0.2})
    with pytest.raises(ValueError, match="fill_length_default_m"):
        controller.set_params({"fill_length_default_m": 101})
    with pytest.raises(ValueError, match="fill_slope_default_pct"):
        controller.set_params({"fill_slope_default_pct": 151})


def test_resolve_outslope_unrutted_required_profiles_validates_bounds(tmp_path: Path) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")

    fill_profile, buffer_profile, errors = controller._resolve_outslope_unrutted_required_profiles(
        properties={
            "FILL_LENGTH_M": 20.0,
            "FILL_SLOPE_PCT": 120.0,
            "BUFFER_LENGTH_M": 50.0,
            "BUFFER_SLOPE_PCT": 80.0,
        }
    )

    assert errors == []
    assert fill_profile is not None
    assert buffer_profile is not None
    assert fill_profile["fill_slope_pct"] == pytest.approx(120.0)
    assert buffer_profile["buffer_slope_pct"] == pytest.approx(80.0)

    fill_profile, buffer_profile, errors = controller._resolve_outslope_unrutted_required_profiles(
        properties={
            "FILL_LENGTH_M": 120.0,
            "FILL_SLOPE_PCT": "not-a-number",
            "BUFFER_LENGTH_M": 50.0,
            "BUFFER_SLOPE_PCT": 120.0,
        }
    )

    assert fill_profile is None
    assert buffer_profile is None
    assert set(errors) == {"fill_length_m", "fill_slope_pct", "buffer_slope_pct"}


def test_run_roads_wepp_rejects_stale_prepare_summary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    monkeypatch.setattr(
        Roads,
        "watershed_instance",
        property(lambda self: SimpleNamespace(delineation_backend_is_wbt=True)),
    )
    controller.set_enabled(True)
    with controller.locked():
        controller._uploaded_geojson_sha256 = "current-upload"
        controller._last_prepare_summary = {
            "uploaded_geojson_sha256": "old-upload",
            "roads_params_signature": controller._params_signature(controller._roads_params),
        }
        controller._status = "completed"

    with pytest.raises(ValueError, match="upload changed after prepare_segments"):
        controller.run_roads_wepp()


def test_build_single_ofe_soil_file_keeps_only_road_ofe(tmp_path: Path) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    template_path = Path(controller.roads_legacy_soils_dir) / "3gloam2.sol"
    output_path = tmp_path / "roads" / "single_ofe.sol"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    controller._build_single_ofe_soil_file(
        template_path=template_path,
        output_path=output_path,
        traffic="low",
        surface="gravel",
        rfg_pct=20.0,
    )

    text = output_path.read_text(encoding="utf-8")
    assert "1 0" in text
    assert "'Road'" in text
    assert "'Fill'" not in text
    assert "'Forest'" not in text
    assert "urr" not in text
    assert "ufr" not in text
    assert "ubr" not in text


def test_build_single_ofe_management_file_keeps_only_ofe_1(tmp_path: Path) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    template_path = Path(controller.roads_legacy_managements_dir) / "3inslope.man"
    output_path = tmp_path / "roads" / "single_ofe.man"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    controller._build_single_ofe_management_file(
        template_path=template_path,
        output_path=output_path,
    )

    text = output_path.read_text(encoding="utf-8")
    assert "# number of OFEs" in text
    assert "Plant scenario 2" not in text
    assert "Initial Conditions scenario 2" not in text
    assert "Yearly scenario 2" not in text
    assert "OFE : 2" not in text
    assert "OFE : 3" not in text


def test_build_routed_two_ofe_soil_file_keeps_road_and_buffer_ofes(tmp_path: Path) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    template_path = Path(controller.roads_legacy_soils_dir) / "3gloam2.sol"
    output_path = tmp_path / "roads" / "routed_two_ofe.sol"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    controller._build_routed_two_ofe_soil_file(
        template_path=template_path,
        output_path=output_path,
        traffic="low",
        surface="gravel",
        rfg_pct=20.0,
    )

    text = output_path.read_text(encoding="utf-8")
    assert "2 0" in text
    assert "'Road'" in text
    assert "'Forest'" in text
    assert "'Fill'" not in text
    assert "urr" not in text
    assert "ufr" not in text
    assert "ubr" not in text


def test_build_routed_three_ofe_soil_file_keeps_road_fill_and_buffer_ofes(tmp_path: Path) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    template_path = Path(controller.roads_legacy_soils_dir) / "3gloam2.sol"
    output_path = tmp_path / "roads" / "routed_three_ofe.sol"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    controller._build_routed_three_ofe_soil_file(
        template_path=template_path,
        output_path=output_path,
        traffic="low",
        surface="gravel",
        rfg_pct=20.0,
    )

    text = output_path.read_text(encoding="utf-8")
    assert "3 0" in text
    assert "'Road'" in text
    assert "'Fill'" in text
    assert "'Forest'" in text
    assert "urr" not in text
    assert "ufr" not in text
    assert "ubr" not in text


def test_write_routed_three_ofe_slope_file_writes_three_ofes(tmp_path: Path) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    output_path = tmp_path / "roads" / "routed_three_ofe.slp"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    controller._write_routed_three_ofe_slope_file(
        output_path,
        width_m=4.0,
        road_length_m=120.0,
        road_slope_pct=8.0,
        fill_length_m=18.0,
        fill_slope_pct=12.0,
        buffer_length_m=30.0,
        buffer_slope_pct=6.0,
    )

    text = output_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    assert lines[0] == "97.3"
    assert lines[1] == "3"
    assert lines[3] == "2 120.000"
    assert lines[5] == "3 18.000"
    assert lines[7] == "3 30.000"
    assert lines[4].count(",") == 2
    assert lines[6].count(",") == 3
    assert lines[8].count(",") == 3


def test_build_routed_two_ofe_management_file_keeps_road_and_buffer(tmp_path: Path) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    template_path = Path(controller.roads_legacy_managements_dir) / "3inslope.man"
    output_path = tmp_path / "roads" / "routed_two_ofe.man"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    controller._build_routed_two_ofe_management_file(
        template_path=template_path,
        output_path=output_path,
    )

    text = output_path.read_text(encoding="utf-8")
    assert "3\t# number of OFEs" not in text
    assert "2\t# number of OFEs" in text
    assert "Plant scenario 2 of 3" not in text
    assert "Initial Conditions scenario 2 of 3" not in text
    assert "Yearly scenario 2 of 3" not in text
    assert "OFE : 3" not in text
    assert "OFE : 2" in text
    assert "Initial Conditions indx' - <FILL>" not in text
    assert "3       # `itype' - <FOREST>" not in text
    assert "2       # `itype' - <FOREST>" in text


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


def test_run_roads_wepp_maps_hillslopes_and_runs_watershed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")

    Path(controller.roads_monotonic_geojson_path).parent.mkdir(parents=True, exist_ok=True)
    Path(controller.roads_monotonic_geojson_path).write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 1.0]]},
                        "properties": {
                            "segment_id": "roads-seg-000001",
                            "DESIGN": "Inslope_rd",
                            "topaz_id_chn_lowpoint": 24,
                            "topaz_id_hill_lowpoint": 21,
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
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    baseline_runs_dir = tmp_path / "wepp" / "runs"
    baseline_output_dir = tmp_path / "wepp" / "output"
    baseline_runs_dir.mkdir(parents=True, exist_ok=True)
    baseline_output_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "dem").mkdir(parents=True, exist_ok=True)
    (baseline_runs_dir / "baseline.txt").write_text("baseline", encoding="utf-8")
    (baseline_runs_dir / "p1.cli").write_text("climate", encoding="utf-8")
    (baseline_output_dir / "H1.pass.dat").write_text("h1 baseline", encoding="utf-8")
    (baseline_output_dir / "H2.pass.dat").write_text("h2 baseline", encoding="utf-8")

    translator = SimpleNamespace(
        top2wepp={21: 1},
        iter_wepp_sub_ids=lambda: iter([1, 2]),
    )
    watershed_instance = SimpleNamespace(
        delineation_backend_is_wbt=True,
        translator_factory=lambda: translator,
    )
    wepp_instance = SimpleNamespace(
        runs_dir=str(baseline_runs_dir),
        output_dir=str(baseline_output_dir),
        climate_instance=SimpleNamespace(input_years=25),
        wepp_bin="wepp_dcc52a6",
        pass_family="legacy_ascii",
    )

    monkeypatch.setattr(
        Roads,
        "_resolve_prepare_raster_paths",
        lambda self: {
            "dem_path": str(tmp_path / "dem" / "relief.tif"),
            "channel_raster_path": str(tmp_path / "dem" / "netful.tif"),
            "topaz_id_raster_path": str(tmp_path / "dem" / "subwta.tif"),
        },
    )

    class _FakeDataset:
        crs = "EPSG:4326"
        nodata = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        @staticmethod
        def sample(_coords):
            return iter(([100.0],))

    monkeypatch.setattr(roads_module.rasterio, "open", lambda _path: _FakeDataset())

    monkeypatch.setattr(Roads, "watershed_instance", property(lambda self: watershed_instance))
    monkeypatch.setattr(Roads, "wepp_instance", property(lambda self: wepp_instance))
    controller.set_enabled(True)
    _seed_prepared_state(controller)

    def _fake_combine(self, *, base_pass_path: str, road_pass_paths, output_pass_path: str) -> None:
        assert Path(base_pass_path).exists()
        road_pass_paths = list(road_pass_paths)
        assert len(road_pass_paths) == 1
        assert Path(road_pass_paths[0]).exists()
        Path(output_pass_path).write_text("combined", encoding="utf-8")

    monkeypatch.setattr(Roads, "_combine_target_hillslope_pass", _fake_combine)
    monkeypatch.setattr(
        Roads,
        "_build_segment_profile",
        lambda self, **_kwargs: {
            "segment_length_m": 120.0,
            "elevation_high_m": 1400.0,
            "elevation_low_m": 1360.0,
            "raw_slope_pct": 33.333,
            "slope_pct": 33.333,
            "high_point": [0.0, 1.0],
            "low_point": [1.0, 0.0],
        },
    )

    management_template_path = tmp_path / "roads" / "3inslope.single_ofe.man"
    management_template_path.parent.mkdir(parents=True, exist_ok=True)
    management_template_path.write_text("management", encoding="utf-8")
    monkeypatch.setattr(
        Roads,
        "_materialize_single_ofe_management_template",
        lambda self, **_kwargs: management_template_path,
    )

    soil_template_path = tmp_path / "roads" / "3gloam2.sol"
    soil_template_path.write_text("soil template", encoding="utf-8")
    monkeypatch.setattr(
        Roads,
        "_resolve_legacy_soil_template_path",
        lambda self, **_kwargs: soil_template_path,
    )
    monkeypatch.setattr(
        Roads,
        "_build_single_ofe_soil_file",
        lambda self, *, output_path, **_kwargs: Path(output_path).write_text("single ofe soil", encoding="utf-8"),
    )
    monkeypatch.setattr(
        Roads,
        "_write_single_ofe_slope_file",
        lambda self, path, **_kwargs: Path(path).write_text("single ofe slope", encoding="utf-8"),
    )
    monkeypatch.setattr(
        Roads,
        "_run_segment_hillslope",
        lambda self, *, segment_run_id, **_kwargs: (Path(self.roads_output_dir) / f"H{segment_run_id}.pass.dat").write_text(
            "segment pass",
            encoding="utf-8",
        ),
    )
    monkeypatch.setattr(
        Roads,
        "_combine_target_hillslope_pass",
        lambda self, *, output_pass_path, **_kwargs: Path(output_pass_path).write_text("combined", encoding="utf-8"),
    )

    captured_make: dict[str, object] = {}

    def _fake_make(
        years: int,
        wepp_id_paths,
        runs_dir: str,
        *,
        pass_family: str,
        wepp_bin: str | None = None,
    ) -> None:
        captured_make["years"] = years
        captured_make["wepp_id_paths"] = list(wepp_id_paths)
        captured_make["runs_dir"] = runs_dir
        captured_make["pass_family"] = pass_family
        captured_make["wepp_bin"] = wepp_bin

    monkeypatch.setattr(roads_module, "make_watershed_omni_contrasts_run", _fake_make)
    monkeypatch.setattr(roads_module, "run_watershed", lambda runs_dir: None)
    monkeypatch.setattr(Roads, "_regenerate_roads_report_resources", _ready_report_resources_stub)

    summary = controller.run_roads_wepp()
    status = controller.query_status()

    assert status["status"] == "completed"
    assert summary["eligible_segment_count"] == 1
    assert summary["mapped_segment_count"] == 1
    assert summary["executed_segment_count"] == 1
    assert summary["targeted_hillslope_wepp_ids"] == [1]
    assert summary["pass_staging_strategy"]["1"] == "combined"
    assert summary["pass_staging_strategy"]["2"] in {"copy", "symlink"}
    assert summary["skipped_segment_reason_counts"] == {"design_not_eligible": 1}
    assert summary["segment_pass_count"] == 1
    assert len(summary["segment_execution_records"]) == 1
    assert summary["segment_execution_records"][0]["status"] == "completed"
    assert summary["roads_report_resources"]["status"] == "ready"
    assert Path(tmp_path / summary["segment_pass_manifest_relpath"]).exists()
    assert (Path(controller.roads_output_dir) / "H1.pass.dat").read_text(encoding="utf-8") == "combined"
    assert summary["roads_log_relpath"] == "wepp/roads/roads.log"
    assert Path(controller.roads_log_path).exists()
    assert captured_make["years"] == 25
    assert captured_make["runs_dir"] == controller.roads_runs_dir


def test_run_roads_wepp_routes_non_channel_routable_segments_with_trace_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")

    Path(controller.roads_monotonic_geojson_path).parent.mkdir(parents=True, exist_ok=True)
    Path(controller.roads_monotonic_geojson_path).write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 1.0]]},
                        "properties": {
                            "segment_id": "roads-seg-009001",
                            "DESIGN": "Inslope_bd",
                            "topaz_id_chn_lowpoint": None,
                            "topaz_id_hill_lowpoint": None,
                            "_roads_non_channel_routable": True,
                            "_roads_routing_eligibility": "non_channel_routable",
                            "_roads_lowpoint_row": 1,
                            "_roads_lowpoint_col": 0,
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    baseline_runs_dir = tmp_path / "wepp" / "runs"
    baseline_output_dir = tmp_path / "wepp" / "output"
    baseline_runs_dir.mkdir(parents=True, exist_ok=True)
    baseline_output_dir.mkdir(parents=True, exist_ok=True)
    (baseline_runs_dir / "baseline.txt").write_text("baseline", encoding="utf-8")
    (baseline_runs_dir / "p1.cli").write_text("climate", encoding="utf-8")
    (baseline_output_dir / "H1.pass.dat").write_text("h1 baseline", encoding="utf-8")
    (baseline_output_dir / "H2.pass.dat").write_text("h2 baseline", encoding="utf-8")

    translator = SimpleNamespace(
        top2wepp={21: 1},
        iter_wepp_sub_ids=lambda: iter([1, 2]),
    )
    watershed_instance = SimpleNamespace(
        delineation_backend_is_wbt=True,
        translator_factory=lambda: translator,
    )
    wepp_instance = SimpleNamespace(
        runs_dir=str(baseline_runs_dir),
        output_dir=str(baseline_output_dir),
        climate_instance=SimpleNamespace(input_years=25),
        wepp_bin="wepp_dcc52a6",
        pass_family="legacy_ascii",
    )

    relief_path = str(tmp_path / "dem" / "relief.tif")
    netful_path = str(tmp_path / "dem" / "netful.tif")
    subwta_path = str(tmp_path / "dem" / "subwta.tif")
    flovec_path = str(tmp_path / "dem" / "flovec.tif")
    monkeypatch.setattr(
        Roads,
        "_resolve_prepare_raster_paths",
        lambda self: {
            "dem_path": relief_path,
            "channel_raster_path": netful_path,
            "topaz_id_raster_path": subwta_path,
        },
    )
    monkeypatch.setattr(
        Roads,
        "_resolve_trace_raster_paths",
        lambda self: {
            "dem_path": relief_path,
            "channel_raster_path": netful_path,
            "topaz_id_raster_path": subwta_path,
            "flovec_path": flovec_path,
        },
    )

    topaz_values = np.array(
        [
            [11.0, 12.0, 14.0],
            [20.0, 21.0, 24.0],
            [31.0, 32.0, 34.0],
        ],
        dtype=np.float32,
    )

    class _FakeDemDataset:
        crs = "EPSG:4326"
        nodata = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        @staticmethod
        def sample(_coords):
            return iter(([100.0],))

    class _FakeTopazDataset:
        nodata = -9999.0

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        @staticmethod
        def read(_idx, *, masked=False):
            if masked:
                return np.ma.array(topaz_values, mask=np.zeros_like(topaz_values, dtype=bool))
            return np.array(topaz_values, copy=True)

    def _fake_raster_open(path: str, *args, **kwargs):
        if str(path).endswith("subwta.tif"):
            return _FakeTopazDataset()
        return _FakeDemDataset()

    monkeypatch.setattr(roads_module.rasterio, "open", _fake_raster_open)
    monkeypatch.setattr(Roads, "watershed_instance", property(lambda self: watershed_instance))
    monkeypatch.setattr(Roads, "wepp_instance", property(lambda self: wepp_instance))
    controller.set_enabled(True)
    _seed_prepared_state(controller)

    tracer_calls: list[tuple[int, int]] = []
    import wepppyo3.roads_flowpath as roads_flowpath_module

    def _fake_trace(_subwta_path, _flovec_path, _relief_path, seed_row: int, seed_col: int, **_kwargs):
        tracer_calls.append((seed_row, seed_col))
        return {
            "seed_row": seed_row,
            "seed_col": seed_col,
            "seed_topaz_id": 11,
            "reaches_channel": True,
            "channel_row": 1,
            "channel_col": 2,
            "channel_topaz_id": 24,
            "termination_reason": "hit_channel",
            "rows": [1, 1, 2],
            "cols": [0, 1, 2],
            "indices": [3, 4, 5],
            "distance_m": [0.0, 20.0, 45.0],
            "elevation_m": [100.0, 98.0, 94.0],
            "segment_slope": [0.1, 0.2],
            "path_length_m": 45.0,
            "drop_m": 6.0,
            "mean_slope": 0.1333333333,
            "max_slope": 0.2,
        }

    monkeypatch.setattr(roads_flowpath_module, "trace_downslope_flowpath", _fake_trace)

    monkeypatch.setattr(
        Roads,
        "_build_segment_profile",
        lambda self, **_kwargs: {
            "segment_length_m": 120.0,
            "elevation_high_m": 1400.0,
            "elevation_low_m": 1360.0,
            "raw_slope_pct": 33.333,
            "slope_pct": 33.333,
            "high_point": [0.0, 1.0],
            "low_point": [1.0, 0.0],
        },
    )
    routed_build_calls: dict[str, int] = {"management": 0, "soil": 0, "slope": 0}
    routed_management_path = tmp_path / "roads" / "routed_two_ofe.man"
    routed_management_path.parent.mkdir(parents=True, exist_ok=True)
    routed_management_path.write_text("routed management", encoding="utf-8")

    def _fake_materialize_routed_management(self, *, traffic: str) -> Path:
        assert traffic in {"high", "low", "none"}
        routed_build_calls["management"] += 1
        return routed_management_path

    def _fake_build_routed_soil(self, *, output_path: Path, **_kwargs) -> None:
        routed_build_calls["soil"] += 1
        Path(output_path).write_text("routed soil", encoding="utf-8")

    def _fake_write_routed_slope(self, path: Path, **_kwargs) -> None:
        routed_build_calls["slope"] += 1
        Path(path).write_text("routed slope", encoding="utf-8")

    monkeypatch.setattr(Roads, "_materialize_routed_two_ofe_management_template", _fake_materialize_routed_management)
    monkeypatch.setattr(Roads, "_build_routed_two_ofe_soil_file", _fake_build_routed_soil)
    monkeypatch.setattr(Roads, "_write_routed_two_ofe_slope_file", _fake_write_routed_slope)

    monkeypatch.setattr(
        Roads,
        "_run_segment_hillslope",
        lambda self, *, segment_run_id, **_kwargs: (Path(self.roads_output_dir) / f"H{segment_run_id}.pass.dat").write_text(
            "segment pass",
            encoding="utf-8",
        ),
    )
    monkeypatch.setattr(
        Roads,
        "_combine_target_hillslope_pass",
        lambda self, *, output_pass_path, **_kwargs: Path(output_pass_path).write_text("combined", encoding="utf-8"),
    )
    monkeypatch.setattr(roads_module, "make_watershed_omni_contrasts_run", lambda *args, **kwargs: None)
    monkeypatch.setattr(roads_module, "run_watershed", lambda _runs_dir: None)
    monkeypatch.setattr(Roads, "_regenerate_roads_report_resources", _ready_report_resources_stub)

    summary = controller.run_roads_wepp()

    assert tracer_calls == [(1, 0)]
    assert summary["status"] == "completed"
    assert summary["executed_segment_count"] == 1
    assert summary["executed_channel_associated_segment_count"] == 0
    assert summary["executed_non_channel_routed_segment_count"] == 1
    assert summary["trace_invocation_count"] == 1
    assert summary["trace_reached_channel_count"] == 1
    assert summary["trace_termination_reason_counts"] == {"hit_channel": 1}
    assert summary["segment_routing_mode_counts"] == {"non_channel_routed": 1}
    assert summary["targeted_hillslope_wepp_ids"] == [1]
    assert summary["segment_execution_records"][0]["routing_mode"] == "non_channel_routed"
    assert summary["segment_execution_records"][0]["topaz_id_hill_lowpoint"] == 21
    assert summary["segment_execution_records"][0]["trace_reaches_channel"] is True
    assert summary["segment_execution_records"][0]["trace_termination_reason"] == "hit_channel"
    assert summary["segment_execution_records"][0]["buffer_length_m"] == pytest.approx(45.0)
    assert routed_build_calls == {"management": 1, "soil": 1, "slope": 1}


def test_run_roads_wepp_runs_outslope_rutted_channel_associated_with_fill_defaults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    controller.set_params({"fill_length_default_m": 33.0, "fill_slope_default_pct": 11.0})

    Path(controller.roads_monotonic_geojson_path).parent.mkdir(parents=True, exist_ok=True)
    Path(controller.roads_monotonic_geojson_path).write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 1.0]]},
                        "properties": {
                            "segment_id": "roads-seg-009201",
                            "DESIGN": "Outslope_rutted",
                            "topaz_id_chn_lowpoint": 24,
                            "topaz_id_hill_lowpoint": 21,
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    baseline_runs_dir = tmp_path / "wepp" / "runs"
    baseline_output_dir = tmp_path / "wepp" / "output"
    baseline_runs_dir.mkdir(parents=True, exist_ok=True)
    baseline_output_dir.mkdir(parents=True, exist_ok=True)
    (baseline_runs_dir / "baseline.txt").write_text("baseline", encoding="utf-8")
    (baseline_runs_dir / "p1.cli").write_text("climate", encoding="utf-8")
    (baseline_output_dir / "H1.pass.dat").write_text("h1 baseline", encoding="utf-8")

    translator = SimpleNamespace(top2wepp={21: 1}, iter_wepp_sub_ids=lambda: iter([1]))
    watershed_instance = SimpleNamespace(
        delineation_backend_is_wbt=True,
        translator_factory=lambda: translator,
    )
    wepp_instance = SimpleNamespace(
        runs_dir=str(baseline_runs_dir),
        output_dir=str(baseline_output_dir),
        climate_instance=SimpleNamespace(input_years=25),
        wepp_bin="wepp_dcc52a6",
        pass_family="legacy_ascii",
    )

    monkeypatch.setattr(
        Roads,
        "_resolve_prepare_raster_paths",
        lambda self: {
            "dem_path": str(tmp_path / "dem" / "relief.tif"),
            "channel_raster_path": str(tmp_path / "dem" / "netful.tif"),
            "topaz_id_raster_path": str(tmp_path / "dem" / "subwta.tif"),
        },
    )

    class _FakeDataset:
        crs = "EPSG:4326"
        nodata = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        @staticmethod
        def sample(_coords):
            return iter(([100.0],))

    monkeypatch.setattr(roads_module.rasterio, "open", lambda _path: _FakeDataset())
    monkeypatch.setattr(Roads, "watershed_instance", property(lambda self: watershed_instance))
    monkeypatch.setattr(Roads, "wepp_instance", property(lambda self: wepp_instance))
    controller.set_enabled(True)
    _seed_prepared_state(controller)

    monkeypatch.setattr(
        Roads,
        "_build_segment_profile",
        lambda self, **_kwargs: {
            "segment_length_m": 120.0,
            "elevation_high_m": 1400.0,
            "elevation_low_m": 1360.0,
            "raw_slope_pct": 12.0,
            "slope_pct": 12.0,
            "high_point": [0.0, 1.0],
            "low_point": [1.0, 0.0],
        },
    )

    calls = {"management": 0, "soil": 0, "slope": 0}
    routed_management_path = tmp_path / "roads" / "routed_three_ofe.man"
    routed_management_path.parent.mkdir(parents=True, exist_ok=True)
    routed_management_path.write_text("routed three ofe management", encoding="utf-8")

    def _fake_materialize_routed_three_management(self, *, traffic: str) -> Path:
        assert traffic in {"high", "low", "none"}
        calls["management"] += 1
        return routed_management_path

    def _fake_build_routed_three_soil(self, *, output_path: Path, **_kwargs) -> None:
        calls["soil"] += 1
        Path(output_path).write_text("routed three ofe soil", encoding="utf-8")

    def _fake_write_routed_three_slope(self, path: Path, **_kwargs) -> None:
        calls["slope"] += 1
        Path(path).write_text("routed three ofe slope", encoding="utf-8")

    monkeypatch.setattr(Roads, "_materialize_routed_three_ofe_management_template", _fake_materialize_routed_three_management)
    monkeypatch.setattr(Roads, "_build_routed_three_ofe_soil_file", _fake_build_routed_three_soil)
    monkeypatch.setattr(Roads, "_write_routed_three_ofe_slope_file", _fake_write_routed_three_slope)
    monkeypatch.setattr(
        Roads,
        "_run_segment_hillslope",
        lambda self, *, segment_run_id, **_kwargs: (Path(self.roads_output_dir) / f"H{segment_run_id}.pass.dat").write_text(
            "segment pass",
            encoding="utf-8",
        ),
    )
    monkeypatch.setattr(
        Roads,
        "_combine_target_hillslope_pass",
        lambda self, *, output_pass_path, **_kwargs: Path(output_pass_path).write_text("combined", encoding="utf-8"),
    )
    monkeypatch.setattr(roads_module, "make_watershed_omni_contrasts_run", lambda *args, **kwargs: None)
    monkeypatch.setattr(roads_module, "run_watershed", lambda _runs_dir: None)
    monkeypatch.setattr(Roads, "_regenerate_roads_report_resources", _ready_report_resources_stub)

    summary = controller.run_roads_wepp()

    assert summary["status"] == "completed"
    assert summary["executed_segment_count"] == 1
    assert summary["executed_outslope_rutted_segment_count"] == 1
    assert summary["fill_default_usage_counts"] == {"fill_length_m": 1, "fill_slope_pct": 1}
    assert summary["segment_execution_records"][0]["routing_mode"] == "channel_associated"
    assert summary["segment_execution_records"][0]["design"] == "outslope_rutted"
    assert summary["segment_execution_records"][0]["fill_length_m"] == pytest.approx(33.0)
    assert summary["segment_execution_records"][0]["fill_slope_pct"] == pytest.approx(11.0)
    assert calls == {"management": 1, "soil": 1, "slope": 1}


def test_run_roads_wepp_routes_outslope_rutted_non_channel_with_three_ofe_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")

    Path(controller.roads_monotonic_geojson_path).parent.mkdir(parents=True, exist_ok=True)
    Path(controller.roads_monotonic_geojson_path).write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 1.0]]},
                        "properties": {
                            "segment_id": "roads-seg-009301",
                            "DESIGN": "Outslope_rutted",
                            "FILL_LENGTH_M": 18.0,
                            "FILL_SLOPE_PCT": 9.5,
                            "topaz_id_chn_lowpoint": None,
                            "topaz_id_hill_lowpoint": None,
                            "_roads_non_channel_routable": True,
                            "_roads_routing_eligibility": "non_channel_routable",
                            "_roads_lowpoint_row": 1,
                            "_roads_lowpoint_col": 0,
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    baseline_runs_dir = tmp_path / "wepp" / "runs"
    baseline_output_dir = tmp_path / "wepp" / "output"
    baseline_runs_dir.mkdir(parents=True, exist_ok=True)
    baseline_output_dir.mkdir(parents=True, exist_ok=True)
    (baseline_runs_dir / "baseline.txt").write_text("baseline", encoding="utf-8")
    (baseline_runs_dir / "p1.cli").write_text("climate", encoding="utf-8")
    (baseline_output_dir / "H1.pass.dat").write_text("h1 baseline", encoding="utf-8")

    translator = SimpleNamespace(top2wepp={21: 1}, iter_wepp_sub_ids=lambda: iter([1]))
    watershed_instance = SimpleNamespace(
        delineation_backend_is_wbt=True,
        translator_factory=lambda: translator,
    )
    wepp_instance = SimpleNamespace(
        runs_dir=str(baseline_runs_dir),
        output_dir=str(baseline_output_dir),
        climate_instance=SimpleNamespace(input_years=25),
        wepp_bin="wepp_dcc52a6",
        pass_family="legacy_ascii",
    )

    relief_path = str(tmp_path / "dem" / "relief.tif")
    netful_path = str(tmp_path / "dem" / "netful.tif")
    subwta_path = str(tmp_path / "dem" / "subwta.tif")
    flovec_path = str(tmp_path / "dem" / "flovec.tif")
    monkeypatch.setattr(
        Roads,
        "_resolve_prepare_raster_paths",
        lambda self: {
            "dem_path": relief_path,
            "channel_raster_path": netful_path,
            "topaz_id_raster_path": subwta_path,
        },
    )
    monkeypatch.setattr(
        Roads,
        "_resolve_trace_raster_paths",
        lambda self: {
            "dem_path": relief_path,
            "channel_raster_path": netful_path,
            "topaz_id_raster_path": subwta_path,
            "flovec_path": flovec_path,
        },
    )

    class _FakeDemDataset:
        crs = "EPSG:4326"
        nodata = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        @staticmethod
        def sample(_coords):
            return iter(([100.0],))

    class _FakeTopazDataset:
        nodata = -9999.0

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        @staticmethod
        def read(_idx, *, masked=False):
            data = np.array([[11.0, 12.0, 14.0], [20.0, 21.0, 24.0], [31.0, 32.0, 34.0]], dtype=np.float32)
            if masked:
                return np.ma.array(data, mask=np.zeros_like(data, dtype=bool))
            return data

    def _fake_raster_open(path: str, *args, **kwargs):
        if str(path).endswith("subwta.tif"):
            return _FakeTopazDataset()
        return _FakeDemDataset()

    monkeypatch.setattr(roads_module.rasterio, "open", _fake_raster_open)
    monkeypatch.setattr(Roads, "watershed_instance", property(lambda self: watershed_instance))
    monkeypatch.setattr(Roads, "wepp_instance", property(lambda self: wepp_instance))
    controller.set_enabled(True)
    _seed_prepared_state(controller)

    import wepppyo3.roads_flowpath as roads_flowpath_module

    monkeypatch.setattr(
        roads_flowpath_module,
        "trace_downslope_flowpath",
        lambda _subwta_path, _flovec_path, _relief_path, seed_row, seed_col, **_kwargs: {
            "seed_row": seed_row,
            "seed_col": seed_col,
            "seed_topaz_id": 11,
            "reaches_channel": True,
            "channel_row": 1,
            "channel_col": 2,
            "channel_topaz_id": 24,
            "termination_reason": "hit_channel",
            "rows": [1, 1, 2],
            "cols": [0, 1, 2],
            "indices": [3, 4, 5],
            "distance_m": [0.0, 20.0, 45.0],
            "elevation_m": [100.0, 98.0, 94.0],
            "segment_slope": [0.1, 0.2],
            "path_length_m": 45.0,
            "drop_m": 6.0,
            "mean_slope": 0.1333333333,
            "max_slope": 0.2,
        },
    )

    monkeypatch.setattr(
        Roads,
        "_build_segment_profile",
        lambda self, **_kwargs: {
            "segment_length_m": 120.0,
            "elevation_high_m": 1400.0,
            "elevation_low_m": 1360.0,
            "raw_slope_pct": 33.333,
            "slope_pct": 33.333,
            "high_point": [0.0, 1.0],
            "low_point": [1.0, 0.0],
        },
    )

    calls = {"management": 0, "soil": 0, "slope": 0}
    routed_management_path = tmp_path / "roads" / "routed_three_ofe.man"
    routed_management_path.parent.mkdir(parents=True, exist_ok=True)
    routed_management_path.write_text("routed three ofe management", encoding="utf-8")

    def _fake_materialize_routed_three_management(self, *, traffic: str) -> Path:
        calls["management"] += 1
        return routed_management_path

    def _fake_build_routed_three_soil(self, *, output_path: Path, **_kwargs) -> None:
        calls["soil"] += 1
        Path(output_path).write_text("routed three ofe soil", encoding="utf-8")

    def _fake_write_routed_three_slope(self, path: Path, **_kwargs) -> None:
        calls["slope"] += 1
        Path(path).write_text("routed three ofe slope", encoding="utf-8")

    monkeypatch.setattr(Roads, "_materialize_routed_three_ofe_management_template", _fake_materialize_routed_three_management)
    monkeypatch.setattr(Roads, "_build_routed_three_ofe_soil_file", _fake_build_routed_three_soil)
    monkeypatch.setattr(Roads, "_write_routed_three_ofe_slope_file", _fake_write_routed_three_slope)

    monkeypatch.setattr(
        Roads,
        "_run_segment_hillslope",
        lambda self, *, segment_run_id, **_kwargs: (Path(self.roads_output_dir) / f"H{segment_run_id}.pass.dat").write_text(
            "segment pass",
            encoding="utf-8",
        ),
    )
    monkeypatch.setattr(
        Roads,
        "_combine_target_hillslope_pass",
        lambda self, *, output_pass_path, **_kwargs: Path(output_pass_path).write_text("combined", encoding="utf-8"),
    )
    monkeypatch.setattr(roads_module, "make_watershed_omni_contrasts_run", lambda *args, **kwargs: None)
    monkeypatch.setattr(roads_module, "run_watershed", lambda _runs_dir: None)
    monkeypatch.setattr(Roads, "_regenerate_roads_report_resources", _ready_report_resources_stub)

    summary = controller.run_roads_wepp()

    assert summary["status"] == "completed"
    assert summary["executed_non_channel_routed_segment_count"] == 1
    assert summary["executed_outslope_rutted_segment_count"] == 1
    assert summary["fill_default_usage_counts"] == {}
    assert summary["trace_invocation_count"] == 1
    assert summary["trace_reached_channel_count"] == 1
    assert summary["segment_execution_records"][0]["routing_mode"] == "non_channel_routed"
    assert summary["segment_execution_records"][0]["design"] == "outslope_rutted"
    assert summary["segment_execution_records"][0]["fill_length_m"] == pytest.approx(18.0)
    assert summary["segment_execution_records"][0]["fill_slope_pct"] == pytest.approx(9.5)
    assert calls == {"management": 1, "soil": 1, "slope": 1}


def test_run_roads_wepp_skips_non_channel_routable_segment_when_trace_does_not_reach_channel(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    Path(controller.roads_monotonic_geojson_path).parent.mkdir(parents=True, exist_ok=True)
    Path(controller.roads_monotonic_geojson_path).write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 1.0]]},
                        "properties": {
                            "segment_id": "roads-seg-009101",
                            "DESIGN": "Inslope_bd",
                            "topaz_id_chn_lowpoint": None,
                            "topaz_id_hill_lowpoint": None,
                            "_roads_non_channel_routable": True,
                            "_roads_routing_eligibility": "non_channel_routable",
                            "_roads_lowpoint_row": 1,
                            "_roads_lowpoint_col": 0,
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    baseline_runs_dir = tmp_path / "wepp" / "runs"
    baseline_output_dir = tmp_path / "wepp" / "output"
    baseline_runs_dir.mkdir(parents=True, exist_ok=True)
    baseline_output_dir.mkdir(parents=True, exist_ok=True)
    (baseline_runs_dir / "baseline.txt").write_text("baseline", encoding="utf-8")
    (baseline_runs_dir / "p1.cli").write_text("climate", encoding="utf-8")
    (baseline_output_dir / "H1.pass.dat").write_text("h1 baseline", encoding="utf-8")
    (baseline_output_dir / "H2.pass.dat").write_text("h2 baseline", encoding="utf-8")

    translator = SimpleNamespace(
        top2wepp={21: 1},
        iter_wepp_sub_ids=lambda: iter([1, 2]),
    )
    watershed_instance = SimpleNamespace(
        delineation_backend_is_wbt=True,
        translator_factory=lambda: translator,
    )
    wepp_instance = SimpleNamespace(
        runs_dir=str(baseline_runs_dir),
        output_dir=str(baseline_output_dir),
        climate_instance=SimpleNamespace(input_years=25),
        wepp_bin="wepp_dcc52a6",
        pass_family="legacy_ascii",
    )

    relief_path = str(tmp_path / "dem" / "relief.tif")
    netful_path = str(tmp_path / "dem" / "netful.tif")
    subwta_path = str(tmp_path / "dem" / "subwta.tif")
    flovec_path = str(tmp_path / "dem" / "flovec.tif")
    monkeypatch.setattr(
        Roads,
        "_resolve_prepare_raster_paths",
        lambda self: {
            "dem_path": relief_path,
            "channel_raster_path": netful_path,
            "topaz_id_raster_path": subwta_path,
        },
    )
    monkeypatch.setattr(
        Roads,
        "_resolve_trace_raster_paths",
        lambda self: {
            "dem_path": relief_path,
            "channel_raster_path": netful_path,
            "topaz_id_raster_path": subwta_path,
            "flovec_path": flovec_path,
        },
    )

    class _FakeDemDataset:
        crs = "EPSG:4326"
        nodata = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        @staticmethod
        def sample(_coords):
            return iter(([100.0],))

    class _FakeTopazDataset:
        nodata = -9999.0

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        @staticmethod
        def read(_idx, *, masked=False):
            data = np.array([[11.0, 12.0, 14.0], [20.0, 21.0, 24.0], [31.0, 32.0, 34.0]], dtype=np.float32)
            if masked:
                return np.ma.array(data, mask=np.zeros_like(data, dtype=bool))
            return data

    def _fake_raster_open(path: str, *args, **kwargs):
        if str(path).endswith("subwta.tif"):
            return _FakeTopazDataset()
        return _FakeDemDataset()

    monkeypatch.setattr(roads_module.rasterio, "open", _fake_raster_open)
    monkeypatch.setattr(Roads, "watershed_instance", property(lambda self: watershed_instance))
    monkeypatch.setattr(Roads, "wepp_instance", property(lambda self: wepp_instance))
    controller.set_enabled(True)
    _seed_prepared_state(controller)

    import wepppyo3.roads_flowpath as roads_flowpath_module

    monkeypatch.setattr(
        roads_flowpath_module,
        "trace_downslope_flowpath",
        lambda _subwta_path, _flovec_path, _relief_path, seed_row, seed_col, **_kwargs: {
            "seed_row": seed_row,
            "seed_col": seed_col,
            "seed_topaz_id": 11,
            "reaches_channel": False,
            "channel_row": None,
            "channel_col": None,
            "channel_topaz_id": None,
            "termination_reason": "raster_edge",
            "rows": [1, 1, 0],
            "cols": [0, 1, 1],
            "indices": [3, 4, 1],
            "distance_m": [0.0, 20.0, 30.0],
            "elevation_m": [100.0, 98.0, 97.0],
            "segment_slope": [0.1, 0.05],
            "path_length_m": 30.0,
            "drop_m": 3.0,
            "mean_slope": 0.1,
            "max_slope": 0.1,
        },
    )

    monkeypatch.setattr(
        Roads,
        "_build_segment_profile",
        lambda self, **_kwargs: {
            "segment_length_m": 120.0,
            "elevation_high_m": 1400.0,
            "elevation_low_m": 1360.0,
            "raw_slope_pct": 33.333,
            "slope_pct": 33.333,
            "high_point": [0.0, 1.0],
            "low_point": [1.0, 0.0],
        },
    )
    monkeypatch.setattr(
        Roads,
        "_run_segment_hillslope",
        lambda self, **_kwargs: (_ for _ in ()).throw(RuntimeError("should not run")),
    )
    monkeypatch.setattr(
        Roads,
        "_combine_target_hillslope_pass",
        lambda self, **_kwargs: (_ for _ in ()).throw(RuntimeError("should not combine")),
    )
    monkeypatch.setattr(roads_module, "make_watershed_omni_contrasts_run", lambda *args, **kwargs: None)
    monkeypatch.setattr(roads_module, "run_watershed", lambda _runs_dir: None)
    monkeypatch.setattr(Roads, "_regenerate_roads_report_resources", _ready_report_resources_stub)

    summary = controller.run_roads_wepp()

    assert summary["status"] == "completed"
    assert summary["executed_segment_count"] == 0
    assert summary["trace_invocation_count"] == 1
    assert summary["trace_reached_channel_count"] == 0
    assert summary["trace_termination_reason_counts"] == {"raster_edge": 1}
    assert summary["targeted_hillslope_count"] == 0
    assert summary["skipped_segment_reason_counts"] == {"trace_did_not_reach_channel": 1}


def test_run_roads_wepp_persists_failed_summary_on_watershed_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")

    Path(controller.roads_monotonic_geojson_path).parent.mkdir(parents=True, exist_ok=True)
    Path(controller.roads_monotonic_geojson_path).write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 1.0]]},
                        "properties": {
                            "segment_id": "roads-seg-000001",
                            "DESIGN": "Inslope_rd",
                            "topaz_id_chn_lowpoint": 24,
                            "topaz_id_hill_lowpoint": 21,
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    baseline_runs_dir = tmp_path / "wepp" / "runs"
    baseline_output_dir = tmp_path / "wepp" / "output"
    baseline_runs_dir.mkdir(parents=True, exist_ok=True)
    baseline_output_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "dem").mkdir(parents=True, exist_ok=True)
    (baseline_runs_dir / "baseline.txt").write_text("baseline", encoding="utf-8")
    (baseline_runs_dir / "p1.cli").write_text("climate", encoding="utf-8")
    (baseline_output_dir / "H1.pass.dat").write_text("h1 baseline", encoding="utf-8")
    translator = SimpleNamespace(
        top2wepp={21: 1},
        iter_wepp_sub_ids=lambda: iter([1]),
    )
    watershed_instance = SimpleNamespace(
        delineation_backend_is_wbt=True,
        translator_factory=lambda: translator,
    )
    wepp_instance = SimpleNamespace(
        runs_dir=str(baseline_runs_dir),
        output_dir=str(baseline_output_dir),
        climate_instance=SimpleNamespace(input_years=25),
        wepp_bin="wepp_dcc52a6",
        pass_family="legacy_ascii",
    )

    monkeypatch.setattr(
        Roads,
        "_resolve_prepare_raster_paths",
        lambda self: {
            "dem_path": str(tmp_path / "dem" / "relief.tif"),
            "channel_raster_path": str(tmp_path / "dem" / "netful.tif"),
            "topaz_id_raster_path": str(tmp_path / "dem" / "subwta.tif"),
        },
    )

    class _FakeDataset:
        crs = "EPSG:4326"
        nodata = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        @staticmethod
        def sample(_coords):
            return iter(([100.0],))

    monkeypatch.setattr(roads_module.rasterio, "open", lambda _path: _FakeDataset())
    monkeypatch.setattr(Roads, "watershed_instance", property(lambda self: watershed_instance))
    monkeypatch.setattr(Roads, "wepp_instance", property(lambda self: wepp_instance))
    controller.set_enabled(True)
    _seed_prepared_state(controller)
    monkeypatch.setattr(
        Roads,
        "_build_segment_profile",
        lambda self, **_kwargs: {
            "segment_length_m": 120.0,
            "elevation_high_m": 1400.0,
            "elevation_low_m": 1360.0,
            "raw_slope_pct": 33.333,
            "slope_pct": 33.333,
            "high_point": [0.0, 1.0],
            "low_point": [1.0, 0.0],
        },
    )

    management_template_path = tmp_path / "roads" / "3inslope.single_ofe.man"
    management_template_path.parent.mkdir(parents=True, exist_ok=True)
    management_template_path.write_text("management", encoding="utf-8")
    monkeypatch.setattr(
        Roads,
        "_materialize_single_ofe_management_template",
        lambda self, **_kwargs: management_template_path,
    )
    soil_template_path = tmp_path / "roads" / "3gloam2.sol"
    soil_template_path.write_text("soil template", encoding="utf-8")
    monkeypatch.setattr(
        Roads,
        "_resolve_legacy_soil_template_path",
        lambda self, **_kwargs: soil_template_path,
    )
    monkeypatch.setattr(
        Roads,
        "_build_single_ofe_soil_file",
        lambda self, *, output_path, **_kwargs: Path(output_path).write_text("single ofe soil", encoding="utf-8"),
    )
    monkeypatch.setattr(
        Roads,
        "_write_single_ofe_slope_file",
        lambda self, path, **_kwargs: Path(path).write_text("single ofe slope", encoding="utf-8"),
    )
    monkeypatch.setattr(
        Roads,
        "_run_segment_hillslope",
        lambda self, *, segment_run_id, **_kwargs: (Path(self.roads_output_dir) / f"H{segment_run_id}.pass.dat").write_text(
            "segment pass",
            encoding="utf-8",
        ),
    )
    monkeypatch.setattr(
        Roads,
        "_combine_target_hillslope_pass",
        lambda self, *, output_pass_path, **_kwargs: Path(output_pass_path).write_text("combined", encoding="utf-8"),
    )
    monkeypatch.setattr(roads_module, "make_watershed_omni_contrasts_run", lambda *args, **kwargs: None)
    monkeypatch.setattr(roads_module, "run_watershed", lambda _runs_dir: (_ for _ in ()).throw(Exception("watershed boom")))

    with pytest.raises(Exception, match="watershed boom"):
        controller.run_roads_wepp()

    status = controller.query_status()
    summary = controller.query_summary()
    last_run = summary["last_run_summary"]

    assert status["status"] == "failed"
    assert status["errors"] == ["watershed boom"]
    assert last_run is not None
    assert last_run["status"] == "failed"
    assert last_run["failed_stage"] == "watershed_rerun"
    assert last_run["executed_segment_count"] == 1
    assert last_run["targeted_hillslope_wepp_ids"] == [1]
    assert last_run["segment_pass_count"] == 1


def test_run_roads_wepp_fails_when_segment_execution_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    Path(controller.roads_monotonic_geojson_path).parent.mkdir(parents=True, exist_ok=True)
    Path(controller.roads_monotonic_geojson_path).write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 1.0]]},
                        "properties": {
                            "segment_id": "roads-seg-000001",
                            "DESIGN": "Inslope_rd",
                            "topaz_id_chn_lowpoint": 24,
                            "topaz_id_hill_lowpoint": 21,
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    baseline_runs_dir = tmp_path / "wepp" / "runs"
    baseline_output_dir = tmp_path / "wepp" / "output"
    baseline_runs_dir.mkdir(parents=True, exist_ok=True)
    baseline_output_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "dem").mkdir(parents=True, exist_ok=True)
    (baseline_runs_dir / "p1.cli").write_text("climate", encoding="utf-8")
    (baseline_output_dir / "H1.pass.dat").write_text("h1 baseline", encoding="utf-8")

    translator = SimpleNamespace(top2wepp={21: 1}, iter_wepp_sub_ids=lambda: iter([1]))
    watershed_instance = SimpleNamespace(
        delineation_backend_is_wbt=True,
        translator_factory=lambda: translator,
    )
    wepp_instance = SimpleNamespace(
        runs_dir=str(baseline_runs_dir),
        output_dir=str(baseline_output_dir),
        climate_instance=SimpleNamespace(input_years=25),
        wepp_bin="wepp_dcc52a6",
        pass_family="legacy_ascii",
    )

    monkeypatch.setattr(
        Roads,
        "_resolve_prepare_raster_paths",
        lambda self: {
            "dem_path": str(tmp_path / "dem" / "relief.tif"),
            "channel_raster_path": str(tmp_path / "dem" / "netful.tif"),
            "topaz_id_raster_path": str(tmp_path / "dem" / "subwta.tif"),
        },
    )

    class _FakeDataset:
        crs = "EPSG:4326"
        nodata = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        @staticmethod
        def sample(_coords):
            return iter(([100.0],))

    monkeypatch.setattr(roads_module.rasterio, "open", lambda _path: _FakeDataset())
    monkeypatch.setattr(Roads, "watershed_instance", property(lambda self: watershed_instance))
    monkeypatch.setattr(Roads, "wepp_instance", property(lambda self: wepp_instance))
    controller.set_enabled(True)
    _seed_prepared_state(controller)

    management_template_path = tmp_path / "roads" / "3inslope.single_ofe.man"
    management_template_path.parent.mkdir(parents=True, exist_ok=True)
    management_template_path.write_text("management", encoding="utf-8")
    soil_template_path = tmp_path / "roads" / "3gloam2.sol"
    soil_template_path.write_text("soil template", encoding="utf-8")
    monkeypatch.setattr(
        Roads,
        "_materialize_single_ofe_management_template",
        lambda self, **_kwargs: management_template_path,
    )
    monkeypatch.setattr(
        Roads,
        "_resolve_legacy_soil_template_path",
        lambda self, **_kwargs: soil_template_path,
    )
    monkeypatch.setattr(
        Roads,
        "_build_single_ofe_soil_file",
        lambda self, *, output_path, **_kwargs: Path(output_path).write_text("single ofe soil", encoding="utf-8"),
    )
    monkeypatch.setattr(
        Roads,
        "_write_single_ofe_slope_file",
        lambda self, path, **_kwargs: Path(path).write_text("single ofe slope", encoding="utf-8"),
    )
    monkeypatch.setattr(
        Roads,
        "_build_segment_profile",
        lambda self, **_kwargs: {
            "segment_length_m": 120.0,
            "elevation_high_m": 1400.0,
            "elevation_low_m": 1360.0,
            "raw_slope_pct": 33.333,
            "slope_pct": 33.333,
            "high_point": [0.0, 1.0],
            "low_point": [1.0, 0.0],
        },
    )
    monkeypatch.setattr(
        Roads,
        "_run_segment_hillslope",
        lambda self, **_kwargs: (_ for _ in ()).throw(RuntimeError("segment boom")),
    )

    with pytest.raises(RuntimeError, match="segment execution failed"):
        controller.run_roads_wepp()

    summary = controller.query_summary()
    last_run = summary["last_run_summary"]
    assert last_run is not None
    assert last_run["status"] == "failed"
    assert last_run["failed_stage"] == "segment_runs"
    assert last_run["failed_segment_count"] == 1


def test_regenerate_roads_report_resources_uses_roads_scope_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    climate = SimpleNamespace(is_single_storm=False, calendar_start_year=1995)
    wepp_instance = SimpleNamespace(
        wd=str(tmp_path),
        climate_instance=climate,
        baseflow_opts=SimpleNamespace(gwstorage=0.0, bfcoeff=0.0, dscoeff=0.0, bfthreshold=0.0),
        output_dir=str(tmp_path / "wepp" / "output"),
        pass_family="legacy_ascii",
    )
    monkeypatch.setattr(Roads, "wepp_instance", property(lambda self: wepp_instance))

    output_dir = Path(controller.roads_output_dir)
    interchange_dir = output_dir / "interchange"
    calls: list[tuple[str, str]] = []

    def _fake_hillslope(wepp_output_dir: Path, **_kwargs):
        calls.append(("hillslope", str(wepp_output_dir)))
        interchange_dir.mkdir(parents=True, exist_ok=True)
        (interchange_dir / "H.pass.parquet").write_text("pass", encoding="utf-8")
        (interchange_dir / "H.wat.parquet").write_text("wat", encoding="utf-8")

    def _fake_totalwatsed3(path: Path, **_kwargs):
        calls.append(("totalwatsed3", str(path)))
        (interchange_dir / "totalwatsed3.parquet").write_text("tw3", encoding="utf-8")

    def _fake_watershed(wepp_output_dir: Path, **_kwargs):
        calls.append(("watershed", str(wepp_output_dir)))
        (interchange_dir / "loss_pw0.out.parquet").write_text("loss out", encoding="utf-8")
        (interchange_dir / "loss_pw0.hill.parquet").write_text("loss hill", encoding="utf-8")
        (interchange_dir / "loss_pw0.chn.parquet").write_text("loss chn", encoding="utf-8")
        (interchange_dir / "ebe_pw0.parquet").write_text("ebe", encoding="utf-8")
        (interchange_dir / "chnwb.parquet").write_text("chnwb", encoding="utf-8")

    def _fake_docs(path: Path):
        calls.append(("docs", str(path)))
        (interchange_dir / "README.md").write_text("readme", encoding="utf-8")

    def _fake_activate(wepp_obj):
        calls.append(("activate", str(getattr(wepp_obj, "wd", ""))))

    def _fake_segment_summary(self: Roads, *, interchange_dir: Path) -> str:
        calls.append(("segment-summary", str(interchange_dir)))
        relpath = "wepp/roads/output/interchange/roads_segment_loss_summary.parquet"
        (Path(self.wd) / relpath).write_text("segment summary", encoding="utf-8")
        return relpath

    monkeypatch.setattr(interchange_module, "run_wepp_hillslope_interchange", _fake_hillslope)
    monkeypatch.setattr(interchange_module, "run_totalwatsed3", _fake_totalwatsed3)
    monkeypatch.setattr(interchange_module, "run_wepp_watershed_interchange", _fake_watershed)
    monkeypatch.setattr(interchange_module, "generate_interchange_documentation", _fake_docs)
    monkeypatch.setattr("wepppy.wepp.interchange.run_wepp_hillslope_interchange", _fake_hillslope)
    monkeypatch.setattr("wepppy.wepp.interchange.run_totalwatsed3", _fake_totalwatsed3)
    monkeypatch.setattr("wepppy.wepp.interchange.run_wepp_watershed_interchange", _fake_watershed)
    monkeypatch.setattr("wepppy.wepp.interchange.generate_interchange_documentation", _fake_docs)
    monkeypatch.setattr(post_utils_module, "activate_query_engine_for_run", _fake_activate)
    monkeypatch.setattr(Roads, "_build_roads_segment_loss_summary_parquet", _fake_segment_summary)

    resources = controller._regenerate_roads_report_resources()

    assert resources["status"] == "ready"
    assert resources["output_scope"] == "roads"
    assert resources["missing_relpaths"] == []
    assert "wepp/roads/output/interchange/totalwatsed3.parquet" in resources["required_relpaths"]
    assert "wepp/roads/output/interchange/roads_segment_loss_summary.parquet" in resources["required_relpaths"]
    assert resources["roads_segment_loss_summary_relpath"] == "wepp/roads/output/interchange/roads_segment_loss_summary.parquet"
    assert calls[0] == ("hillslope", str(output_dir))
    assert ("watershed", str(output_dir)) in calls
    assert ("totalwatsed3", str(interchange_dir)) in calls
    assert ("segment-summary", str(interchange_dir)) in calls


def test_regenerate_roads_report_resources_fails_when_segment_summary_generation_raises(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    climate = SimpleNamespace(is_single_storm=False, calendar_start_year=1995)
    wepp_instance = SimpleNamespace(
        wd=str(tmp_path),
        climate_instance=climate,
        baseflow_opts=SimpleNamespace(gwstorage=0.0, bfcoeff=0.0, dscoeff=0.0, bfthreshold=0.0),
        output_dir=str(tmp_path / "wepp" / "output"),
        pass_family="legacy_ascii",
    )
    monkeypatch.setattr(Roads, "wepp_instance", property(lambda self: wepp_instance))

    output_dir = Path(controller.roads_output_dir)
    interchange_dir = output_dir / "interchange"

    def _fake_hillslope(wepp_output_dir: Path, **_kwargs):
        assert wepp_output_dir == output_dir
        interchange_dir.mkdir(parents=True, exist_ok=True)
        (interchange_dir / "H.pass.parquet").write_text("pass", encoding="utf-8")
        (interchange_dir / "H.wat.parquet").write_text("wat", encoding="utf-8")

    def _fake_totalwatsed3(path: Path, **_kwargs):
        assert path == interchange_dir
        (interchange_dir / "totalwatsed3.parquet").write_text("tw3", encoding="utf-8")

    def _fake_watershed(wepp_output_dir: Path, **_kwargs):
        assert wepp_output_dir == output_dir
        (interchange_dir / "loss_pw0.out.parquet").write_text("loss out", encoding="utf-8")
        (interchange_dir / "loss_pw0.hill.parquet").write_text("loss hill", encoding="utf-8")
        (interchange_dir / "loss_pw0.chn.parquet").write_text("loss chn", encoding="utf-8")
        (interchange_dir / "ebe_pw0.parquet").write_text("ebe", encoding="utf-8")
        (interchange_dir / "chnwb.parquet").write_text("chnwb", encoding="utf-8")

    def _fake_docs(path: Path):
        assert path == interchange_dir
        (interchange_dir / "README.md").write_text("readme", encoding="utf-8")

    def _fake_segment_summary(self: Roads, *, interchange_dir: Path) -> str:
        raise RuntimeError(f"segment summary failed at {interchange_dir}")

    monkeypatch.setattr(interchange_module, "run_wepp_hillslope_interchange", _fake_hillslope)
    monkeypatch.setattr(interchange_module, "run_totalwatsed3", _fake_totalwatsed3)
    monkeypatch.setattr(interchange_module, "run_wepp_watershed_interchange", _fake_watershed)
    monkeypatch.setattr(interchange_module, "generate_interchange_documentation", _fake_docs)
    monkeypatch.setattr("wepppy.wepp.interchange.run_wepp_hillslope_interchange", _fake_hillslope)
    monkeypatch.setattr("wepppy.wepp.interchange.run_totalwatsed3", _fake_totalwatsed3)
    monkeypatch.setattr("wepppy.wepp.interchange.run_wepp_watershed_interchange", _fake_watershed)
    monkeypatch.setattr("wepppy.wepp.interchange.generate_interchange_documentation", _fake_docs)
    monkeypatch.setattr(post_utils_module, "activate_query_engine_for_run", lambda _wepp_obj: None)
    monkeypatch.setattr(Roads, "_build_roads_segment_loss_summary_parquet", _fake_segment_summary)

    with pytest.raises(RuntimeError, match="segment summary failed"):
        controller._regenerate_roads_report_resources()


def test_build_roads_segment_loss_summary_parquet_joins_manifest_and_loss_hill(tmp_path: Path) -> None:
    import duckdb

    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    interchange_dir = Path(controller.roads_output_dir) / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = Path(controller.roads_segment_pass_manifest_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            [
                {
                    "segment_id": "seg-a",
                    "segment_run_id": 900001,
                    "target_hillslope_wepp_id": 123,
                    "topaz_id_hill_lowpoint": 456,
                    "topaz_id_chn_lowpoint": 789,
                    "design": "inslope_bd",
                    "surface": "gravel",
                    "traffic": "high",
                    "soil_texture": "clay",
                    "rfg_pct": 20.0,
                    "road_width_m": 4.0,
                    "segment_length_m": 200.0,
                    "slope_pct_clamped": 5.0,
                    "status": "completed",
                },
                {
                    "segment_id": "seg-b",
                    "segment_run_id": 900002,
                    "status": "skipped",
                },
            ]
        ),
        encoding="utf-8",
    )

    loss_hill_path = interchange_dir / "loss_pw0.hill.parquet"
    loss_hill_path_sql = str(loss_hill_path).replace("'", "''")
    with duckdb.connect(database=":memory:") as con:
        con.execute(
            f"""
            COPY (
                SELECT * FROM (
                    SELECT
                        'Hill' AS "Type",
                        123 AS wepp_id,
                        120.0 AS "Runoff Volume",
                        10.0 AS "Subrunoff Volume",
                        5.0 AS "Baseflow Volume",
                        40.0 AS "Soil Loss",
                        1.0 AS "Sediment Deposition",
                        15.0 AS "Sediment Yield",
                        0.5 AS "Hillslope Area",
                        0.0 AS "Solub. React. Pollutant",
                        0.0 AS "Particulate Pollutant",
                        0.0 AS "Total Pollutant"
                    UNION ALL
                    SELECT
                        'Hill' AS "Type",
                        900001 AS wepp_id,
                        999.0 AS "Runoff Volume",
                        999.0 AS "Subrunoff Volume",
                        999.0 AS "Baseflow Volume",
                        999.0 AS "Soil Loss",
                        999.0 AS "Sediment Deposition",
                        999.0 AS "Sediment Yield",
                        1.0 AS "Hillslope Area",
                        0.0 AS "Solub. React. Pollutant",
                        0.0 AS "Particulate Pollutant",
                        0.0 AS "Total Pollutant"
                )
            ) TO '{loss_hill_path_sql}' (FORMAT PARQUET)
            """,
        )

    relpath = controller._build_roads_segment_loss_summary_parquet(interchange_dir=interchange_dir)
    assert relpath == "wepp/roads/output/interchange/roads_segment_loss_summary.parquet"
    summary_path = tmp_path / relpath
    assert summary_path.exists()

    with duckdb.connect(database=":memory:") as con:
        rows = con.execute(
            """
            SELECT
                segment_id,
                segment_run_id,
                loss_match_key,
                road_prism_erosion_kg,
                sediment_leaving_buffer_kg,
                soil_loss_density_kg_m2,
                runoff_depth_mm,
                loss_row_missing
            FROM read_parquet(?)
            """,
            [str(summary_path)],
        ).fetchall()

    assert len(rows) == 1
    (
        segment_id,
        segment_run_id,
        loss_match_key,
        road_prism_erosion_kg,
        sediment_leaving_buffer_kg,
        soil_loss_density,
        runoff_depth_mm,
        loss_row_missing,
    ) = rows[0]
    assert segment_id == "seg-a"
    assert segment_run_id == 900001
    assert loss_match_key == "target_hillslope_wepp_id"
    assert road_prism_erosion_kg == pytest.approx(40.0)
    assert sediment_leaving_buffer_kg == pytest.approx(15.0)
    assert soil_loss_density == pytest.approx(0.008)
    assert runoff_depth_mm == pytest.approx(24.0)
    assert loss_row_missing is False


def test_build_roads_segment_loss_summary_parquet_falls_back_to_segment_run_id(tmp_path: Path) -> None:
    import duckdb

    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    interchange_dir = Path(controller.roads_output_dir) / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = Path(controller.roads_segment_pass_manifest_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            [
                {
                    "segment_id": "seg-fallback",
                    "segment_run_id": 900001,
                    "target_hillslope_wepp_id": 12345,
                    "status": "completed",
                }
            ]
        ),
        encoding="utf-8",
    )

    loss_hill_path = interchange_dir / "loss_pw0.hill.parquet"
    loss_hill_path_sql = str(loss_hill_path).replace("'", "''")
    with duckdb.connect(database=":memory:") as con:
        con.execute(
            f"""
            COPY (
                SELECT * FROM (
                    VALUES
                        ('Hill', 900001, 80.0, 5.0, 2.0, 20.0, 0.5, 9.0, 0.4, 0.0, 0.0, 0.0)
                )
                AS t(
                    "Type",
                    wepp_id,
                    "Runoff Volume",
                    "Subrunoff Volume",
                    "Baseflow Volume",
                    "Soil Loss",
                    "Sediment Deposition",
                    "Sediment Yield",
                    "Hillslope Area",
                    "Solub. React. Pollutant",
                    "Particulate Pollutant",
                    "Total Pollutant"
                )
            ) TO '{loss_hill_path_sql}' (FORMAT PARQUET)
            """,
        )

    relpath = controller._build_roads_segment_loss_summary_parquet(interchange_dir=interchange_dir)
    summary_path = tmp_path / relpath

    with duckdb.connect(database=":memory:") as con:
        row = con.execute(
            """
            SELECT loss_match_key, road_prism_erosion_kg, sediment_leaving_buffer_kg, loss_row_missing
            FROM read_parquet(?)
            """,
            [str(summary_path)],
        ).fetchone()

    assert row is not None
    loss_match_key, road_prism_erosion_kg, sediment_leaving_buffer_kg, loss_row_missing = row
    assert loss_match_key == "segment_run_id"
    assert road_prism_erosion_kg == pytest.approx(20.0)
    assert sediment_leaving_buffer_kg == pytest.approx(9.0)
    assert loss_row_missing is False


def test_build_roads_segment_loss_summary_parquet_marks_missing_loss_rows(tmp_path: Path) -> None:
    import duckdb

    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    interchange_dir = Path(controller.roads_output_dir) / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = Path(controller.roads_segment_pass_manifest_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            [
                {
                    "segment_id": "seg-missing",
                    "segment_run_id": 900002,
                    "target_hillslope_wepp_id": 22222,
                    "status": "completed",
                }
            ]
        ),
        encoding="utf-8",
    )

    loss_hill_path = interchange_dir / "loss_pw0.hill.parquet"
    loss_hill_path_sql = str(loss_hill_path).replace("'", "''")
    with duckdb.connect(database=":memory:") as con:
        con.execute(
            f"""
            COPY (
                SELECT * FROM (
                    VALUES
                        ('Hill', 700000, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.1, 0.0, 0.0, 0.0)
                )
                AS t(
                    "Type",
                    wepp_id,
                    "Runoff Volume",
                    "Subrunoff Volume",
                    "Baseflow Volume",
                    "Soil Loss",
                    "Sediment Deposition",
                    "Sediment Yield",
                    "Hillslope Area",
                    "Solub. React. Pollutant",
                    "Particulate Pollutant",
                    "Total Pollutant"
                )
            ) TO '{loss_hill_path_sql}' (FORMAT PARQUET)
            """,
        )

    relpath = controller._build_roads_segment_loss_summary_parquet(interchange_dir=interchange_dir)
    summary_path = tmp_path / relpath

    with duckdb.connect(database=":memory:") as con:
        row = con.execute(
            """
            SELECT loss_match_key, road_prism_erosion_kg, sediment_leaving_buffer_kg, loss_row_missing
            FROM read_parquet(?)
            """,
            [str(summary_path)],
        ).fetchone()

    assert row is not None
    loss_match_key, road_prism_erosion_kg, sediment_leaving_buffer_kg, loss_row_missing = row
    assert loss_match_key is None
    assert road_prism_erosion_kg == pytest.approx(0.0)
    assert sediment_leaving_buffer_kg == pytest.approx(0.0)
    assert loss_row_missing is True


def test_build_roads_segment_loss_summary_parquet_rejects_non_list_manifest(tmp_path: Path) -> None:
    import duckdb

    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    interchange_dir = Path(controller.roads_output_dir) / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = Path(controller.roads_segment_pass_manifest_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({"segment_id": "not-a-list"}), encoding="utf-8")

    loss_hill_path = interchange_dir / "loss_pw0.hill.parquet"
    loss_hill_path_sql = str(loss_hill_path).replace("'", "''")
    with duckdb.connect(database=":memory:") as con:
        con.execute(
            f"""
            COPY (
                SELECT * FROM (
                    VALUES
                        ('Hill', 1, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.1, 0.0, 0.0, 0.0)
                )
                AS t(
                    "Type",
                    wepp_id,
                    "Runoff Volume",
                    "Subrunoff Volume",
                    "Baseflow Volume",
                    "Soil Loss",
                    "Sediment Deposition",
                    "Sediment Yield",
                    "Hillslope Area",
                    "Solub. React. Pollutant",
                    "Particulate Pollutant",
                    "Total Pollutant"
                )
            ) TO '{loss_hill_path_sql}' (FORMAT PARQUET)
            """,
        )

    with pytest.raises(ValueError, match="must be a JSON list"):
        controller._build_roads_segment_loss_summary_parquet(interchange_dir=interchange_dir)


def test_query_map_segments_geojson_returns_roads_feature_collection(tmp_path: Path) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    controller.set_params({"attribute_field_map": {"design": "DESIGN"}})
    _write_prepared_segments(
        controller,
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "LineString", "coordinates": [[-117.1, 46.1], [-117.0, 46.0]]},
                    "properties": {
                        "segment_id": "roads-seg-000501",
                        "DESIGN": "Inslope_bd",
                        "_roads_routing_eligibility": "channel_associated",
                        "_roads_non_channel_routable": False,
                    },
                },
                {
                    "type": "Feature",
                    "geometry": {"type": "LineString", "coordinates": [[-117.2, 46.2], [-117.1, 46.1]]},
                    "properties": {
                        "DESIGN": "Inslope_rd",
                        "_roads_routing_eligibility": "non_channel_routable",
                        "_roads_non_channel_routable": True,
                    },
                },
            ],
        },
    )

    payload = controller.query_map_segments_geojson()

    assert payload["type"] == "FeatureCollection"
    assert len(payload["features"]) == 2
    first = payload["features"][0]["properties"]
    second = payload["features"][1]["properties"]
    assert first["segment_id"] == "roads-seg-000501"
    assert first["design"] == "inslope_bd"
    assert first["routing_mode_hint"] == "channel_associated"
    assert second["segment_id"] == "roads-seg-missing-000002"
    assert second["routing_mode_hint"] == "non_channel_routed"
    assert second["non_channel_routable"] is True


def test_query_segment_detail_returns_manifest_and_wepp_fields(tmp_path: Path) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    controller.set_params({"attribute_field_map": {"design": "DESIGN"}})
    _write_prepared_segments(
        controller,
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "LineString", "coordinates": [[-117.0, 46.0], [-117.002, 46.003]]},
                    "properties": {
                        "segment_id": "roads-seg-000601",
                        "DESIGN": "Inslope_bd",
                        "SURFACE": "Gravel",
                        "TRAFFIC": "low",
                        "SOIL_TEXTURE": "Loam",
                        "RFG_PCT": 18.0,
                        "WIDTH_M": 4.2,
                        "buffer_length_m": 32.0,
                        "buffer_slope_pct": 7.2,
                        "fill_length_m": 12.0,
                        "_roads_routing_eligibility": "channel_associated",
                        "topaz_id_chn_lowpoint": 33,
                        "topaz_id_hill_lowpoint": 331,
                    },
                }
            ],
        },
    )
    _write_segment_manifest(
        controller,
        [
            {
                "segment_id": "roads-seg-000601",
                "status": "completed",
                "segment_run_id": 9012,
                "target_hillslope_wepp_id": 331,
                "routing_mode": "channel_associated",
                "segment_length_m": 250.5,
                "slope_pct_raw": 8.4,
                "slope_pct_clamped": 8.4,
                "elevation_high_m": 1410.0,
                "elevation_low_m": 1389.0,
                "surface": "gravel",
                "traffic": "low",
                "soil_texture": "loam",
                "rfg_pct": 18.0,
                "road_width_m": 4.2,
            }
        ],
    )

    detail = controller.query_segment_detail("roads-seg-000601")

    assert detail["segment_id"] == "roads-seg-000601"
    assert detail["design"] == "inslope_bd"
    assert detail["surface"] == "gravel"
    assert detail["traffic"] == "low"
    assert detail["soil_texture"] == "loam"
    assert detail["rfg_pct"] == pytest.approx(18.0)
    assert detail["road_width_m"] == pytest.approx(4.2)
    assert detail["segment_length_m"] == pytest.approx(250.5)
    assert detail["slope_pct_raw"] == pytest.approx(8.4)
    assert detail["slope_pct_clamped"] == pytest.approx(8.4)
    assert detail["routing_mode"] == "channel_associated"
    assert detail["execution_status"] == "completed"
    assert detail["buffer_length_m"] == pytest.approx(32.0)
    assert detail["buffer_slope_pct"] == pytest.approx(7.2)
    assert detail["fill_length_m"] == pytest.approx(12.0)
    assert detail["segment_run_id"] == 9012
    assert detail["target_hillslope_wepp_id"] == 331


def test_query_segment_detail_uses_unique_fallback_segment_ids_for_missing_ids(tmp_path: Path) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    _write_prepared_segments(
        controller,
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "LineString", "coordinates": [[-117.0, 46.0], [-117.01, 46.02]]},
                    "properties": {
                        "DESIGN": "Inslope_rd",
                        "SURFACE": "paved",
                        "TRAFFIC": "high",
                        "_roads_routing_eligibility": "non_channel_routable",
                        "_roads_non_channel_routable": True,
                    },
                },
                {
                    "type": "Feature",
                    "geometry": {"type": "LineString", "coordinates": [[-117.2, 46.2], [-117.21, 46.23]]},
                    "properties": {
                        "DESIGN": "Inslope_rd",
                        "SURFACE": "gravel",
                        "TRAFFIC": "low",
                        "_roads_routing_eligibility": "non_channel_routable",
                        "_roads_non_channel_routable": True,
                    },
                }
            ],
        },
    )
    _write_segment_manifest(
        controller,
        [
            {
                "segment_id": "roads-seg-missing-000001",
                "status": "completed",
                "routing_mode": "non_channel_routed",
                "segment_length_m": 100.0,
                "slope_pct_raw": 4.0,
                "slope_pct_clamped": 4.0,
                "surface": "paved",
            },
            {
                "segment_id": "roads-seg-missing-000002",
                "status": "completed",
                "routing_mode": "non_channel_routed",
                "segment_length_m": 120.0,
                "slope_pct_raw": 5.0,
                "slope_pct_clamped": 5.0,
                "surface": "gravel",
            }
        ],
    )

    detail = controller.query_segment_detail("roads-seg-missing-000002")

    assert detail["segment_id"] == "roads-seg-missing-000002"
    assert detail["routing_mode"] == "non_channel_routed"
    assert detail["non_channel_routable"] is True
    assert detail["surface"] == "gravel"


def test_select_outslope_unrutted_hillslope_segments_applies_minimum_ratio_and_cap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")

    hillslope_geojson_path = tmp_path / "watershed" / "subwta.geojson"
    hillslope_geojson_path.parent.mkdir(parents=True, exist_ok=True)
    hillslope_geojson_path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"TopazID": 21},
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [
                                [
                                    [-0.0002, -0.0005],
                                    [0.0012, -0.0005],
                                    [0.0012, 0.0005],
                                    [-0.0002, 0.0005],
                                    [-0.0002, -0.0005],
                                ]
                            ],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    watershed_instance = SimpleNamespace(
        subwta_shp=str(hillslope_geojson_path),
        hillslope_width=lambda _topaz_id: 100.0,
    )
    monkeypatch.setattr(Roads, "watershed_instance", property(lambda self: watershed_instance))

    def _pending(segment_id: str, x_end: float) -> dict[str, object]:
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [[0.0, 0.0], [x_end, 0.0]],
            },
            "properties": {
                "segment_id": segment_id,
                "DESIGN": "outslope_unrutted",
                "FILL_LENGTH_M": 20.0,
                "FILL_SLOPE_PCT": 12.0,
                "BUFFER_LENGTH_M": 30.0,
                "BUFFER_SLOPE_PCT": 6.0,
            },
        }
        return {
            "segment_id": segment_id,
            "feature": feature,
            "properties": feature["properties"],
            "design_source": "DESIGN",
        }

    pending_segments = [
        _pending("seg-a", 0.0010),
        _pending("seg-b", 0.0009),
        _pending("seg-c", 0.0008),
        _pending("seg-d", 0.0007),
        _pending("seg-short", 0.00004),
    ]

    selected_by_wepp, diagnostics, candidate_status = controller._select_outslope_unrutted_hillslope_segments(
        pending_segments=pending_segments,
        input_crs=CRS.from_epsg(4326),
        geod=Geod(ellps="WGS84"),
        top2wepp={21: 1},
    )

    assert sorted(selected_by_wepp) == [1]
    included_ids = {row["segment_hillslope_id"] for row in selected_by_wepp[1]}
    assert included_ids == {"seg-a::h21", "seg-b::h21", "seg-c::h21"}

    assert candidate_status["seg-d::h21"]["status"] == "excluded_cap_limit"
    assert candidate_status["seg-short::h21"]["status"] == "excluded_overlap_length_min"

    assert diagnostics["outslope_unrutted_targeted_hillslope_count"] == 1
    assert diagnostics["outslope_unrutted_included_segment_count"] == 3
    assert diagnostics["outslope_unrutted_excluded_segment_count"] == 1
    assert diagnostics["outslope_unrutted_capped_segment_count"] == 1

    record = diagnostics["outslope_unrutted_hillslope_records"][0]
    assert record["topaz_id_hill"] == 21
    assert record["wepp_id_hill"] == 1
    assert set(record["segment_ids_included"]) == {"seg-a::h21", "seg-b::h21", "seg-c::h21"}
    assert record["segment_ids_capped"] == ["seg-d::h21"]


def test_run_roads_wepp_stages_outslope_unrutted_replacement_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")

    monotonic_feature = {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": [[0.0, 0.0], [0.001, 0.0]],
        },
        "properties": {
            "segment_id": "roads-seg-007001",
            "DESIGN": "outslope_unrutted",
            "SURFACE": "gravel",
            "TRAFFIC": "low",
            "SOIL_TEXTURE": "loam",
            "RFG_PCT": 20.0,
            "WIDTH_M": 4.0,
            "FILL_LENGTH_M": 20.0,
            "FILL_SLOPE_PCT": 12.0,
            "BUFFER_LENGTH_M": 30.0,
            "BUFFER_SLOPE_PCT": 6.0,
        },
    }
    Path(controller.roads_monotonic_geojson_path).parent.mkdir(parents=True, exist_ok=True)
    Path(controller.roads_monotonic_geojson_path).write_text(
        json.dumps({"type": "FeatureCollection", "features": [monotonic_feature]}),
        encoding="utf-8",
    )

    baseline_runs_dir = tmp_path / "wepp" / "runs"
    baseline_output_dir = tmp_path / "wepp" / "output"
    baseline_runs_dir.mkdir(parents=True, exist_ok=True)
    baseline_output_dir.mkdir(parents=True, exist_ok=True)
    (baseline_runs_dir / "baseline.txt").write_text("baseline", encoding="utf-8")
    (baseline_runs_dir / "p1.cli").write_text("climate", encoding="utf-8")
    (baseline_output_dir / "H1.pass.dat").write_text("h1 baseline", encoding="utf-8")
    (baseline_output_dir / "H2.pass.dat").write_text("h2 baseline", encoding="utf-8")

    translator = SimpleNamespace(top2wepp={21: 1}, iter_wepp_sub_ids=lambda: iter([1, 2]))
    discha_path = tmp_path / "dem" / "discha.tif"
    discha_path.parent.mkdir(parents=True, exist_ok=True)
    discha_path.write_text("stub", encoding="utf-8")
    watershed_instance = SimpleNamespace(
        delineation_backend_is_wbt=True,
        translator_factory=lambda: translator,
        hillslope_length=lambda _topaz_id: 300.0,
        hillslope_width=lambda _topaz_id: 100.0,
        discha=str(discha_path),
    )
    wepp_instance = SimpleNamespace(
        runs_dir=str(baseline_runs_dir),
        output_dir=str(baseline_output_dir),
        climate_instance=SimpleNamespace(input_years=25),
        wepp_bin="wepp",
        pass_family="legacy_ascii",
    )

    monkeypatch.setattr(Roads, "watershed_instance", property(lambda self: watershed_instance))
    monkeypatch.setattr(Roads, "wepp_instance", property(lambda self: wepp_instance))
    monkeypatch.setattr(
        Roads,
        "_resolve_prepare_raster_paths",
        lambda self: {
            "dem_path": str(tmp_path / "dem" / "relief.tif"),
            "channel_raster_path": str(tmp_path / "dem" / "netful.tif"),
            "topaz_id_raster_path": str(tmp_path / "dem" / "subwta.tif"),
        },
    )

    class _FakeDataset:
        crs = "EPSG:4326"
        nodata = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        @staticmethod
        def sample(_coords):
            return iter(([100.0],))

    monkeypatch.setattr(roads_module.rasterio, "open", lambda _path: _FakeDataset())

    def _fake_select(self, *, pending_segments, **_kwargs):
        pending = pending_segments[0]
        segment_hillslope_id = f"{pending['segment_id']}::h21"
        candidate = {
            "segment_hillslope_id": segment_hillslope_id,
            "source_segment_id": pending["segment_id"],
            "topaz_id_hill": 21,
            "hillslope_wepp_id": 1,
            "overlap_length_m": 111.0,
            "hillslope_width_m": 100.0,
            "inclusion_ratio": 1.11,
            "overlap_geometry_wgs84": pending["feature"]["geometry"],
            "feature": pending["feature"],
            "properties": pending["properties"],
        }
        diagnostics = {
            "outslope_unrutted_targeted_hillslope_count": 1,
            "outslope_unrutted_included_segment_count": 1,
            "outslope_unrutted_excluded_segment_count": 0,
            "outslope_unrutted_capped_segment_count": 0,
            "outslope_unrutted_hillslope_records": [
                {
                    "topaz_id_hill": 21,
                    "wepp_id_hill": 1,
                    "segment_ids_included": [segment_hillslope_id],
                    "segment_ids_excluded": [],
                    "segment_ids_capped": [],
                    "inclusion_ratio_by_segment": {segment_hillslope_id: 1.11},
                    "top_ofe_compensation_m": 0.0,
                    "area_error_before_compensation_m2": 0.0,
                    "area_error_after_compensation_m2": 0.0,
                }
            ],
        }
        status_map = {segment_hillslope_id: {**candidate, "status": "included"}}
        return {1: [candidate]}, diagnostics, status_map

    monkeypatch.setattr(Roads, "_select_outslope_unrutted_hillslope_segments", _fake_select)
    monkeypatch.setattr(
        Roads,
        "_build_segment_profile",
        lambda self, **_kwargs: {
            "segment_length_m": 111.0,
            "elevation_high_m": 1400.0,
            "elevation_low_m": 1391.0,
            "raw_slope_pct": 8.0,
            "slope_pct": 8.0,
            "high_point": [0.0, 0.0],
            "low_point": [0.001, 0.0],
        },
    )

    monkeypatch.setattr(
        Roads,
        "_apply_outslope_unrutted_geometry_parity",
        lambda self, **_kwargs: {
            "sim_length_m": 80.0,
            "sim_width_m": 100.0,
            "road_slope_fraction": 0.04,
            "road_slope_pct": 4.0,
            "geometry_scale": 1.0,
        },
    )
    monkeypatch.setattr(
        Roads,
        "_sample_discha_median_from_wgs84_geometry",
        lambda self, *_args, **_kwargs: 100.0,
    )

    management_template_path = tmp_path / "roads" / "3inslope.man"
    management_template_path.parent.mkdir(parents=True, exist_ok=True)
    management_template_path.write_text("management template", encoding="utf-8")
    monkeypatch.setattr(
        Roads,
        "_resolve_legacy_management_template_path",
        lambda self, **_kwargs: management_template_path,
    )

    soil_template_path = tmp_path / "roads" / "3gloam2.sol"
    soil_template_path.write_text("soil template", encoding="utf-8")
    monkeypatch.setattr(
        Roads,
        "_resolve_legacy_soil_template_path",
        lambda self, **_kwargs: soil_template_path,
    )
    monkeypatch.setattr(
        Roads,
        "_build_routed_mofe_management_file",
        lambda self, *, output_path, **_kwargs: Path(output_path).write_text("management", encoding="utf-8"),
    )
    monkeypatch.setattr(
        Roads,
        "_build_routed_mofe_soil_file",
        lambda self, *, output_path, **_kwargs: Path(output_path).write_text("soil", encoding="utf-8"),
    )
    monkeypatch.setattr(
        Roads,
        "_write_routed_three_ofe_landuse_road_fill_slope_file",
        lambda self, path, **_kwargs: Path(path).write_text("slope", encoding="utf-8"),
    )
    monkeypatch.setattr(
        Roads,
        "_write_routed_four_ofe_landuse_road_fill_hill_slope_file",
        lambda self, path, **_kwargs: Path(path).write_text("slope", encoding="utf-8"),
    )
    monkeypatch.setattr(
        Roads,
        "_run_segment_hillslope",
        lambda self, *, segment_run_id, **_kwargs: (Path(self.roads_output_dir) / f"H{segment_run_id}.pass.dat").write_text(
            "replacement pass",
            encoding="utf-8",
        ),
    )
    monkeypatch.setattr(
        Roads,
        "_combine_target_hillslope_pass",
        lambda self, **_kwargs: (_ for _ in ()).throw(AssertionError("combine should not run for single replacement pass")),
    )

    monkeypatch.setattr(roads_module, "make_watershed_omni_contrasts_run", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(roads_module, "run_watershed", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(Roads, "_regenerate_roads_report_resources", _ready_report_resources_stub)

    controller.set_enabled(True)
    _seed_prepared_state(controller)

    summary = controller.run_roads_wepp()

    assert summary["executed_outslope_unrutted_segment_count"] == 1
    assert summary["segment_design_counts"]["outslope_unrutted"] == 1
    assert summary["replacement_targeted_hillslope_wepp_ids"] == [1]
    assert summary["additive_targeted_hillslope_wepp_ids"] == []
    assert summary["pass_staging_strategy"]["1"] in {"replacement_copy", "replacement_symlink"}
    assert summary["outslope_unrutted_targeted_hillslope_count"] == 1
    assert summary["outslope_unrutted_included_segment_count"] == 1
    assert summary["outslope_unrutted_excluded_segment_count"] == 0
    assert summary["outslope_unrutted_capped_segment_count"] == 0
    assert (Path(controller.roads_output_dir) / "H1.pass.dat").read_text(encoding="utf-8") == "replacement pass"


def test_run_roads_wepp_outslope_unrutted_replacement_combines_phase4(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")

    monotonic_feature = {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": [[0.0, 0.0], [0.001, 0.0]],
        },
        "properties": {
            "segment_id": "roads-seg-007002",
            "DESIGN": "outslope_unrutted",
            "SURFACE": "gravel",
            "TRAFFIC": "low",
            "SOIL_TEXTURE": "loam",
            "RFG_PCT": 20.0,
            "WIDTH_M": 4.0,
            "FILL_LENGTH_M": 20.0,
            "FILL_SLOPE_PCT": 12.0,
            "BUFFER_LENGTH_M": 30.0,
            "BUFFER_SLOPE_PCT": 6.0,
        },
    }
    Path(controller.roads_monotonic_geojson_path).parent.mkdir(parents=True, exist_ok=True)
    Path(controller.roads_monotonic_geojson_path).write_text(
        json.dumps({"type": "FeatureCollection", "features": [monotonic_feature]}),
        encoding="utf-8",
    )

    baseline_runs_dir = tmp_path / "wepp" / "runs"
    baseline_output_dir = tmp_path / "wepp" / "output"
    baseline_runs_dir.mkdir(parents=True, exist_ok=True)
    baseline_output_dir.mkdir(parents=True, exist_ok=True)
    (baseline_runs_dir / "baseline.txt").write_text("baseline", encoding="utf-8")
    (baseline_runs_dir / "p1.cli").write_text("climate", encoding="utf-8")
    (baseline_output_dir / "H1.pass.dat").write_text("h1 baseline", encoding="utf-8")
    (baseline_output_dir / "H2.pass.dat").write_text("h2 baseline", encoding="utf-8")

    translator = SimpleNamespace(top2wepp={21: 1}, iter_wepp_sub_ids=lambda: iter([1, 2]))
    discha_path = tmp_path / "dem" / "discha.tif"
    discha_path.parent.mkdir(parents=True, exist_ok=True)
    discha_path.write_text("stub", encoding="utf-8")
    watershed_instance = SimpleNamespace(
        delineation_backend_is_wbt=True,
        translator_factory=lambda: translator,
        hillslope_length=lambda _topaz_id: 300.0,
        hillslope_width=lambda _topaz_id: 100.0,
        discha=str(discha_path),
    )
    wepp_instance = SimpleNamespace(
        runs_dir=str(baseline_runs_dir),
        output_dir=str(baseline_output_dir),
        climate_instance=SimpleNamespace(input_years=25),
        wepp_bin="wepp",
        pass_family="legacy_ascii",
    )

    monkeypatch.setattr(Roads, "watershed_instance", property(lambda self: watershed_instance))
    monkeypatch.setattr(Roads, "wepp_instance", property(lambda self: wepp_instance))
    monkeypatch.setattr(
        Roads,
        "_resolve_prepare_raster_paths",
        lambda self: {
            "dem_path": str(tmp_path / "dem" / "relief.tif"),
            "channel_raster_path": str(tmp_path / "dem" / "netful.tif"),
            "topaz_id_raster_path": str(tmp_path / "dem" / "subwta.tif"),
        },
    )

    class _FakeDataset:
        crs = "EPSG:4326"
        nodata = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        @staticmethod
        def sample(_coords):
            return iter(([100.0],))

    monkeypatch.setattr(roads_module.rasterio, "open", lambda _path: _FakeDataset())

    expected_segment_order: list[str] = []

    def _fake_select(self, *, pending_segments, **_kwargs):
        pending = pending_segments[0]
        seg_a = f"{pending['segment_id']}::h21::a"
        seg_b = f"{pending['segment_id']}::h21::b"
        expected_segment_order[:] = [seg_b, seg_a]
        candidate_a = {
            "segment_hillslope_id": seg_a,
            "source_segment_id": pending["segment_id"],
            "topaz_id_hill": 21,
            "hillslope_wepp_id": 1,
            "overlap_length_m": 90.0,
            "hillslope_width_m": 100.0,
            "inclusion_ratio": 0.90,
            "overlap_geometry_wgs84": pending["feature"]["geometry"],
            "feature": pending["feature"],
            "properties": pending["properties"],
        }
        candidate_b = {
            "segment_hillslope_id": seg_b,
            "source_segment_id": pending["segment_id"],
            "topaz_id_hill": 21,
            "hillslope_wepp_id": 1,
            "overlap_length_m": 80.0,
            "hillslope_width_m": 100.0,
            "inclusion_ratio": 0.80,
            "overlap_geometry_wgs84": pending["feature"]["geometry"],
            "feature": pending["feature"],
            "properties": pending["properties"],
        }
        diagnostics = {
            "outslope_unrutted_targeted_hillslope_count": 1,
            "outslope_unrutted_included_segment_count": 2,
            "outslope_unrutted_excluded_segment_count": 0,
            "outslope_unrutted_capped_segment_count": 0,
            "outslope_unrutted_hillslope_records": [
                {
                    "topaz_id_hill": 21,
                    "wepp_id_hill": 1,
                    "segment_ids_included": [seg_a, seg_b],
                    "segment_ids_excluded": [],
                    "segment_ids_capped": [],
                    "inclusion_ratio_by_segment": {seg_a: 0.90, seg_b: 0.80},
                    "top_ofe_compensation_m": 0.0,
                    "area_error_before_compensation_m2": 0.0,
                    "area_error_after_compensation_m2": 0.0,
                }
            ],
        }
        status_map = {
            seg_a: {**candidate_a, "status": "included"},
            seg_b: {**candidate_b, "status": "included"},
        }
        return {1: [candidate_a, candidate_b]}, diagnostics, status_map

    monkeypatch.setattr(Roads, "_select_outslope_unrutted_hillslope_segments", _fake_select)
    monkeypatch.setattr(
        Roads,
        "_build_segment_profile",
        lambda self, **_kwargs: {
            "segment_length_m": 100.0,
            "elevation_high_m": 1400.0,
            "elevation_low_m": 1392.0,
            "raw_slope_pct": 8.0,
            "slope_pct": 8.0,
            "high_point": [0.0, 0.0],
            "low_point": [0.001, 0.0],
        },
    )
    monkeypatch.setattr(
        Roads,
        "_apply_outslope_unrutted_geometry_parity",
        lambda self, **_kwargs: {
            "sim_length_m": 80.0,
            "sim_width_m": 50.0,
            "road_slope_fraction": 0.04,
            "road_slope_pct": 4.0,
            "geometry_scale": 1.0,
        },
    )
    monkeypatch.setattr(
        Roads,
        "_sample_discha_median_from_wgs84_geometry",
        (lambda _values=iter([50.0, 150.0]): (lambda self, *_args, **_kwargs: next(_values)))(),
    )

    management_template_path = tmp_path / "roads" / "3inslope.man"
    management_template_path.parent.mkdir(parents=True, exist_ok=True)
    management_template_path.write_text("management template", encoding="utf-8")
    monkeypatch.setattr(
        Roads,
        "_resolve_legacy_management_template_path",
        lambda self, **_kwargs: management_template_path,
    )

    soil_template_path = tmp_path / "roads" / "3gloam2.sol"
    soil_template_path.write_text("soil template", encoding="utf-8")
    monkeypatch.setattr(
        Roads,
        "_resolve_legacy_soil_template_path",
        lambda self, **_kwargs: soil_template_path,
    )
    monkeypatch.setattr(
        Roads,
        "_build_routed_mofe_management_file",
        lambda self, *, output_path, **_kwargs: Path(output_path).write_text("management", encoding="utf-8"),
    )
    monkeypatch.setattr(
        Roads,
        "_build_routed_mofe_soil_file",
        lambda self, *, output_path, **_kwargs: Path(output_path).write_text("soil", encoding="utf-8"),
    )
    monkeypatch.setattr(
        Roads,
        "_write_routed_three_ofe_landuse_road_fill_slope_file",
        lambda self, path, **_kwargs: Path(path).write_text("slope", encoding="utf-8"),
    )
    monkeypatch.setattr(
        Roads,
        "_write_routed_four_ofe_landuse_road_fill_hill_slope_file",
        lambda self, path, **_kwargs: Path(path).write_text("slope", encoding="utf-8"),
    )

    monkeypatch.setattr(
        Roads,
        "_run_segment_hillslope",
        lambda self, *, segment_run_id, **_kwargs: (Path(self.roads_output_dir) / f"H{segment_run_id}.pass.dat").write_text(
            f"replacement pass {segment_run_id}",
            encoding="utf-8",
        ),
    )

    combine_calls = []

    def _fake_combine(self, *, base_pass_path, road_pass_paths, output_pass_path, strategy="phase1"):
        combine_calls.append(
            {
                "base_pass_path": str(base_pass_path),
                "road_pass_paths": list(road_pass_paths),
                "output_pass_path": str(output_pass_path),
                "strategy": strategy,
            }
        )
        Path(output_pass_path).write_text("combined replacement pass", encoding="utf-8")

    monkeypatch.setattr(Roads, "_combine_target_hillslope_pass", _fake_combine)
    monkeypatch.setattr(roads_module, "make_watershed_omni_contrasts_run", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(roads_module, "run_watershed", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(Roads, "_regenerate_roads_report_resources", _ready_report_resources_stub)

    controller.set_enabled(True)
    _seed_prepared_state(controller)

    summary = controller.run_roads_wepp()

    assert summary["executed_outslope_unrutted_segment_count"] == 2
    assert summary["segment_design_counts"]["outslope_unrutted"] == 2
    assert summary["pass_staging_strategy"]["1"] == "replacement_combined"
    assert len(combine_calls) == 1
    assert combine_calls[0]["strategy"] == "phase4"
    assert (Path(controller.roads_output_dir) / "H1.pass.dat").read_text(encoding="utf-8") == "combined replacement pass"
    executed_outslope_segments = [
        record["segment_hillslope_id"]
        for record in summary["segment_execution_records"]
        if record.get("design") == "outslope_unrutted" and record.get("status") == "completed"
    ]
    assert executed_outslope_segments[:2] == expected_segment_order


def test_run_roads_wepp_outslope_unrutted_missing_discha_with_no_selected_candidates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")

    monotonic_feature = {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": [[0.0, 0.0], [0.001, 0.0]],
        },
        "properties": {
            "segment_id": "roads-seg-007003",
            "DESIGN": "outslope_unrutted",
            "SURFACE": "gravel",
            "TRAFFIC": "low",
            "SOIL_TEXTURE": "loam",
            "RFG_PCT": 20.0,
            "WIDTH_M": 4.0,
            "FILL_LENGTH_M": 20.0,
            "FILL_SLOPE_PCT": 12.0,
            "BUFFER_LENGTH_M": 30.0,
            "BUFFER_SLOPE_PCT": 6.0,
        },
    }
    Path(controller.roads_monotonic_geojson_path).parent.mkdir(parents=True, exist_ok=True)
    Path(controller.roads_monotonic_geojson_path).write_text(
        json.dumps({"type": "FeatureCollection", "features": [monotonic_feature]}),
        encoding="utf-8",
    )

    baseline_runs_dir = tmp_path / "wepp" / "runs"
    baseline_output_dir = tmp_path / "wepp" / "output"
    baseline_runs_dir.mkdir(parents=True, exist_ok=True)
    baseline_output_dir.mkdir(parents=True, exist_ok=True)
    (baseline_runs_dir / "baseline.txt").write_text("baseline", encoding="utf-8")
    (baseline_runs_dir / "p1.cli").write_text("climate", encoding="utf-8")
    (baseline_output_dir / "H1.pass.dat").write_text("h1 baseline", encoding="utf-8")
    (baseline_output_dir / "H2.pass.dat").write_text("h2 baseline", encoding="utf-8")

    translator = SimpleNamespace(top2wepp={21: 1}, iter_wepp_sub_ids=lambda: iter([1, 2]))
    watershed_instance = SimpleNamespace(
        delineation_backend_is_wbt=True,
        translator_factory=lambda: translator,
        hillslope_length=lambda _topaz_id: 300.0,
        hillslope_width=lambda _topaz_id: 100.0,
        discha=None,
    )
    wepp_instance = SimpleNamespace(
        runs_dir=str(baseline_runs_dir),
        output_dir=str(baseline_output_dir),
        climate_instance=SimpleNamespace(input_years=25),
        wepp_bin="wepp",
        pass_family="legacy_ascii",
    )

    monkeypatch.setattr(Roads, "watershed_instance", property(lambda self: watershed_instance))
    monkeypatch.setattr(Roads, "wepp_instance", property(lambda self: wepp_instance))
    monkeypatch.setattr(
        Roads,
        "_resolve_prepare_raster_paths",
        lambda self: {
            "dem_path": str(tmp_path / "dem" / "relief.tif"),
            "channel_raster_path": str(tmp_path / "dem" / "netful.tif"),
            "topaz_id_raster_path": str(tmp_path / "dem" / "subwta.tif"),
        },
    )

    class _FakeDataset:
        crs = "EPSG:4326"
        nodata = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        @staticmethod
        def sample(_coords):
            return iter(([100.0],))

    monkeypatch.setattr(roads_module.rasterio, "open", lambda _path: _FakeDataset())

    def _fake_select(self, *, pending_segments, **_kwargs):
        pending = pending_segments[0]
        segment_hillslope_id = f"{pending['segment_id']}::h21"
        diagnostics = {
            "outslope_unrutted_targeted_hillslope_count": 0,
            "outslope_unrutted_included_segment_count": 0,
            "outslope_unrutted_excluded_segment_count": 1,
            "outslope_unrutted_capped_segment_count": 0,
            "outslope_unrutted_hillslope_records": [
                {
                    "topaz_id_hill": 21,
                    "wepp_id_hill": 1,
                    "segment_ids_included": [],
                    "segment_ids_excluded": [segment_hillslope_id],
                    "segment_ids_capped": [],
                    "inclusion_ratio_by_segment": {segment_hillslope_id: 0.1},
                    "top_ofe_compensation_m": 0.0,
                    "area_error_before_compensation_m2": 0.0,
                    "area_error_after_compensation_m2": 0.0,
                }
            ],
        }
        status_map = {
            segment_hillslope_id: {
                "segment_hillslope_id": segment_hillslope_id,
                "source_segment_id": pending["segment_id"],
                "topaz_id_hill": 21,
                "hillslope_wepp_id": 1,
                "overlap_length_m": 5.0,
                "hillslope_width_m": 100.0,
                "inclusion_ratio": 0.1,
                "feature": pending["feature"],
                "properties": pending["properties"],
                "status": "excluded_inclusion_ratio",
            }
        }
        return {}, diagnostics, status_map

    monkeypatch.setattr(Roads, "_select_outslope_unrutted_hillslope_segments", _fake_select)
    monkeypatch.setattr(
        Roads,
        "_combine_target_hillslope_pass",
        lambda self, **_kwargs: (_ for _ in ()).throw(AssertionError("combine should not run when no replacements are selected")),
    )
    monkeypatch.setattr(roads_module, "make_watershed_omni_contrasts_run", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(roads_module, "run_watershed", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(Roads, "_regenerate_roads_report_resources", _ready_report_resources_stub)

    controller.set_enabled(True)
    _seed_prepared_state(controller)

    summary = controller.run_roads_wepp()

    assert summary["executed_outslope_unrutted_segment_count"] == 0
    assert summary["outslope_unrutted_targeted_hillslope_count"] == 0
    assert summary["outslope_unrutted_included_segment_count"] == 0
    assert summary["outslope_unrutted_excluded_segment_count"] == 1
    assert summary["outslope_unrutted_capped_segment_count"] == 0
    assert (Path(controller.roads_output_dir) / "H1.pass.dat").read_text(encoding="utf-8") == "h1 baseline"


def test_combine_target_hillslope_pass_normalizes_alias_climate_tokens(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")

    base_pass_path = tmp_path / "wepp" / "output" / "H15.pass.dat"
    road_pass_path = tmp_path / "wepp" / "roads" / "output" / "H900003.pass.dat"
    out_pass_path = tmp_path / "wepp" / "roads" / "output" / "H15.combined.pass.dat"
    base_cli_path = tmp_path / "wepp" / "runs" / "p15.cli"
    road_cli_path = tmp_path / "wepp" / "roads" / "runs" / "p900003.cli"

    base_cli_path.parent.mkdir(parents=True, exist_ok=True)
    road_cli_path.parent.mkdir(parents=True, exist_ok=True)
    base_cli_path.write_text("shared-climate", encoding="utf-8")
    road_cli_path.symlink_to(base_cli_path)

    _write_minimal_pass(base_pass_path, climate_token="p15.cli")
    _write_minimal_pass(road_pass_path, climate_token="p900003.cli")

    captured: dict[str, object] = {}

    def _fake_combine(**kwargs) -> None:
        captured.update(kwargs)
        Path(kwargs["out_pass"]).write_text("combined", encoding="utf-8")

    monkeypatch.setattr(wepp_interchange_module, "combine_hillslope_pass_files", _fake_combine)

    controller._combine_target_hillslope_pass(
        base_pass_path=str(base_pass_path),
        road_pass_paths=[str(road_pass_path)],
        output_pass_path=str(out_pass_path),
    )

    assert captured["base_pass"] == str(base_pass_path)
    assert captured["road_passes"] == [str(road_pass_path)]
    assert captured["strategy"] == "phase1"
    assert road_pass_path.read_text(encoding="utf-8").splitlines()[0] == "p15.cli"
    assert out_pass_path.read_text(encoding="utf-8") == "combined"


def test_combine_target_hillslope_pass_rejects_distinct_climate_tokens(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")

    base_pass_path = tmp_path / "wepp" / "output" / "H15.pass.dat"
    road_pass_path = tmp_path / "wepp" / "roads" / "output" / "H900003.pass.dat"
    out_pass_path = tmp_path / "wepp" / "roads" / "output" / "H15.combined.pass.dat"
    base_cli_path = tmp_path / "wepp" / "runs" / "p15.cli"
    road_cli_path = tmp_path / "wepp" / "roads" / "runs" / "p900003.cli"

    base_cli_path.parent.mkdir(parents=True, exist_ok=True)
    road_cli_path.parent.mkdir(parents=True, exist_ok=True)
    base_cli_path.write_text("base-climate", encoding="utf-8")
    road_cli_path.write_text("different-climate", encoding="utf-8")

    _write_minimal_pass(base_pass_path, climate_token="p15.cli")
    _write_minimal_pass(road_pass_path, climate_token="p900003.cli")

    monkeypatch.setattr(
        wepp_interchange_module,
        "combine_hillslope_pass_files",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("combine should not be called")),
    )

    with pytest.raises(ValueError, match="could not be normalized"):
        controller._combine_target_hillslope_pass(
            base_pass_path=str(base_pass_path),
            road_pass_paths=[str(road_pass_path)],
            output_pass_path=str(out_pass_path),
        )

    assert road_pass_path.read_text(encoding="utf-8").splitlines()[0] == "p900003.cli"
