from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import pytest

from wepppy.nodb.mods.roads.roads import Roads

from ._support import _write_roads_geojson

pytestmark = [pytest.mark.unit, pytest.mark.nodb]


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


def test_set_uploaded_geojson_rolls_back_file_and_persisted_state_on_commit_failure(
    tmp_path: Path,
) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    original = tmp_path / "original.geojson"
    replacement = tmp_path / "replacement.geojson"
    _write_roads_geojson(original)
    _write_roads_geojson(replacement)
    original.write_text(original.read_text().replace('"features":', '"marker":"old","features":'))
    replacement.write_text(replacement.read_text().replace('"features":', '"marker":"new","features":'))
    accepted = controller.set_uploaded_geojson(str(original))
    canonical = tmp_path / accepted["uploaded_geojson_relpath"]
    prior_bytes = canonical.read_bytes()
    prior_state = controller.query_summary()
    prior_completed = Path(controller.roads_log_path).read_bytes().count(b"upload_completed")

    def fail_commit() -> None:
        raise OSError("receipt fsync failed")

    with pytest.raises(OSError, match="receipt fsync failed"):
        controller.set_uploaded_geojson(str(replacement), publication_commit=fail_commit)

    assert canonical.read_bytes() == prior_bytes
    assert Path(controller.roads_log_path).read_bytes().count(b"upload_completed") == prior_completed
    assert controller.query_summary()["uploaded_geojson_sha256"] == prior_state["uploaded_geojson_sha256"]
    reloaded = Roads.load_detached(str(tmp_path))
    assert reloaded.query_summary()["uploaded_geojson_sha256"] == prior_state["uploaded_geojson_sha256"]


def test_set_uploaded_geojson_does_not_rollback_after_publication_commit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    source = tmp_path / "replacement.geojson"
    _write_roads_geojson(source)
    committed: list[bool] = []
    append_log = Roads._append_roads_log

    def interrupt_completion(self, stage, event, details=None):
        if event == "upload_completed":
            raise KeyboardInterrupt()
        return append_log(self, stage, event, details)

    monkeypatch.setattr(Roads, "_append_roads_log", interrupt_completion)

    with pytest.raises(KeyboardInterrupt):
        controller.set_uploaded_geojson(
            str(source),
            publication_commit=lambda: committed.append(True),
        )

    assert committed == [True]
    reloaded = Roads.load_detached(str(tmp_path))
    summary = reloaded.query_summary()
    assert summary["uploaded_geojson_sha256"] == hashlib.sha256(
        (tmp_path / summary["uploaded_geojson_relpath"]).read_bytes()
    ).hexdigest()


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


@pytest.mark.parametrize("invalid", ["bad", "nan", "inf", "-inf"])
def test_segment_invalid_numeric_attributes_use_defaults_in_artifacts(tmp_path, invalid):
    from wepppy.wepp.soils.utils import WeppSoilUtil

    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    params = controller._default_params()
    params.update(rfg_pct_default=12., road_width_m_default=6.,
                  fill_length_default_m=42., fill_slope_default_pct=14.)
    resolved = controller._resolve_segment_run_inputs(
        properties={"RFG_PCT": invalid, "WIDTH_M": invalid,
                    "FILL_LENGTH_M": invalid, "FILL_SLOPE_PCT": invalid,
                    "SOIL_TEXTURE": "peat"}, params=params,
        segment_id="invalid", design="outslope_rutted",
        warning_counts=Counter(), warning_examples=[], warning_limit=10)
    expected = dict(rfg_pct=12., road_width_m=6., fill_length_m=42., fill_slope_pct=14., soil_texture="loam")
    for key, value in expected.items():
        assert resolved[key] == value
        assert resolved["resolution_sources"][key] == "roads_default"
    buffer = controller._derive_buffer_profile_from_feature_or_defaults(
        properties={"BUFFER_LENGTH_M": invalid, "BUFFER_SLOPE_PCT": invalid},
        road_profile={"segment_length_m": 18., "slope_pct": 8.})
    assert buffer == dict(buffer_length_m=18., buffer_slope_pct=4., buffer_slope_fraction=.04,
                          buffer_length_source="derived_default", buffer_slope_source="derived_default")
    fill = controller._derive_fill_profile_from_inputs(
        fill_length_m=resolved["fill_length_m"], fill_slope_pct=resolved["fill_slope_pct"])
    slope = tmp_path / "resolved.slp"
    controller._write_routed_three_ofe_slope_file(
        slope, width_m=resolved["road_width_m"], road_length_m=18., road_slope_pct=8.,
        fill_length_m=fill["fill_length_m"], fill_slope_pct=fill["fill_slope_pct"],
        buffer_length_m=buffer["buffer_length_m"], buffer_slope_pct=buffer["buffer_slope_pct"])
    lines = slope.read_text().splitlines()
    assert float(lines[2].split()[1]) == 6.
    assert [float(lines[i].split()[1]) for i in (3, 5, 7)] == [18., 42., 18.]
    assert "0.140000" in lines[6] and "0.040000" in lines[8]
    soil = tmp_path / "resolved.sol"
    controller._build_routed_three_ofe_soil_file(
        template_path=controller._resolve_legacy_soil_template_path(
            design="outslope_rutted", surface="gravel", soil_texture=resolved["soil_texture"]),
        output_path=soil, traffic="low", surface="gravel", rfg_pct=resolved["rfg_pct"])
    ofes = WeppSoilUtil(str(soil)).obj["ofes"]
    assert [ofe["horizons"][0]["rfg"] for ofe in ofes] == [65., 38.5, 12.]


def test_segment_finite_aliases_clipping_and_fallback_provenance(tmp_path):
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    def resolve(properties):
        return controller._resolve_segment_run_inputs(
            properties=properties, params=controller._default_params(), segment_id="finite",
            design="outslope_rutted", warning_counts=Counter(), warning_examples=[], warning_limit=10)
    valid = resolve({"SOIL_TEXTURE": "sandy loam", "RFG_PCT": 0, "WIDTH_M": .3})
    assert (valid["soil_texture"], valid["rfg_pct"], valid["road_width_m"]) == ("sand", 0., .3)
    assert all(valid["resolution_sources"][key] == "segment_property"
               for key in ("soil_texture", "rfg_pct", "road_width_m"))
    clipped = resolve({"RFG_PCT": 120, "WIDTH_M": 999, "FILL_LENGTH_M": 999, "FILL_SLOPE_PCT": 999})
    assert (clipped["rfg_pct"], clipped["road_width_m"], clipped["fill_length_m"], clipped["fill_slope_pct"]) == (100., 4., 999., 150.)
    assert clipped["resolution_sources"]["road_width_m"] == "roads_default"
    assert clipped["resolution_sources"]["rfg_pct"] == "segment_property"
    assert controller._derive_fill_profile_from_inputs(fill_length_m=999., fill_slope_pct=999.)["fill_length_m"] == 100.


@pytest.mark.parametrize("invalid", ["nan", "inf", "-inf"])
def test_unrutted_required_geometry_still_rejects_nonfinite(invalid):
    controller = object.__new__(Roads)
    fill, buffer, invalid_fields = controller._resolve_outslope_unrutted_required_profiles(
        properties={"FILL_LENGTH_M": invalid, "FILL_SLOPE_PCT": 10,
                    "BUFFER_LENGTH_M": 30, "BUFFER_SLOPE_PCT": invalid})
    assert fill is None and buffer is None
    assert set(invalid_fields) == {"fill_length_m", "buffer_slope_pct"}


def test_buffer_finite_aliases_and_clipping_are_preserved():
    controller = object.__new__(Roads)
    for length, slope, expected_length, expected_slope in ((12., 7., 12., 7.), (999., 999., 300., 100.)):
        result = controller._derive_buffer_profile_from_feature_or_defaults(
            properties={"buffer_len_m": length, "buffer_slope": slope},
            road_profile={"segment_length_m": 18., "slope_pct": 8.})
        assert result["buffer_length_m"] == expected_length
        assert result["buffer_slope_pct"] == expected_slope
        assert result["buffer_length_source"] == result["buffer_slope_source"] == "segment_property"
