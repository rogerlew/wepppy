from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from pyproj import CRS, Geod

import wepppy.nodb.mods.roads.roads as roads_module
from wepppy.nodb.mods.roads.roads import Roads

from ._support import (
    _ready_report_resources_stub,
    _seed_prepared_state,
    _stub_baseline_wepp,
    _stub_prepare_rasters,
    _stub_wbt_watershed,
    _write_prepared_segments,
)

pytestmark = [pytest.mark.unit, pytest.mark.nodb]


def test_select_outslope_unrutted_hillslope_segments_applies_minimum_and_cap_without_ratio(
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

    offsets = {name: i * 0.00005 for i, name in enumerate(["seg-a", "seg-b", "seg-c", "seg-d", "seg-short"])}

    def _pending(segment_id: str, x_end: float) -> dict[str, object]:
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [[0.0, offsets[segment_id]], [x_end, offsets[segment_id]]],
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


def _write_unrutted_segment(controller: Roads, segment_id: str) -> None:
    monotonic_feature = {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": [[0.0, 0.0], [0.001, 0.0]],
        },
        "properties": {
            "segment_id": segment_id,
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
    _write_prepared_segments(controller, {"type": "FeatureCollection", "features": [monotonic_feature]})


def _stub_unrutted_run(
    controller: Roads,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    segment_id: str,
    *,
    hill_length: float = 300.0,
    has_discha: bool = True,
) -> None:
    _write_unrutted_segment(controller, segment_id)
    _stub_baseline_wepp(monkeypatch, tmp_path, (1, 2), wepp_bin="wepp")
    discha = None
    if has_discha:
        discha_path = tmp_path / "dem" / "discha.tif"
        discha_path.parent.mkdir(parents=True, exist_ok=True)
        discha_path.write_text("stub", encoding="utf-8")
        discha = str(discha_path)
    _stub_wbt_watershed(
        monkeypatch,
        (1, 2),
        hillslope_length=lambda _topaz_id: hill_length,
        hillslope_width=lambda _topaz_id: 100.0,
        discha=discha,
    )
    _stub_prepare_rasters(monkeypatch, tmp_path)


def _stub_unrutted_inputs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, write_management) -> None:
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
    monkeypatch.setattr(Roads, "_build_routed_mofe_management_file", write_management)
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


def _select_single_candidate(self, *, pending_segments, **_kwargs):
    pending = pending_segments[0]
    segment_hillslope_id = f"{pending['segment_id']}::h21"
    candidate = {
        "segment_hillslope_id": segment_hillslope_id,
        "source_segment_id": pending["segment_id"],
        "source_segment_ids": [pending["segment_id"]],
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


def _assert_stale_prepare_rejected(controller: Roads, monkeypatch: pytest.MonkeyPatch) -> None:
    with controller.locked():
        controller._last_prepare_summary.pop("unrutted_geometry_policy")
    monkeypatch.setattr(roads_module.roads_lifecycle, "retain",
        lambda *_a, **_k: pytest.fail("stale admission must not retain/reset workspace"))
    monkeypatch.setattr(Roads, "_run_segment_hillslope",
        lambda *_a, **_k: pytest.fail("stale admission must not execute model"))
    with pytest.raises(ValueError, match="Prepare and run Roads again"):
        controller.run_roads_wepp()


def _assert_road_fill_exceeds_hillslope(controller: Roads, hill_length: float, emitted_roles: list) -> None:
    with pytest.raises(RuntimeError, match="1 segment"):
        controller.run_roads_wepp()
    failure = controller._last_run_summary["segment_execution_records"][0]
    assert failure["reason"] == "failed_road_fill_exceeds_hillslope"
    assert failure["hillslope_length_m"] == hill_length
    assert failure["fill_length_m"] == 20.
    assert failure["road_width_m"] == 4.
    assert not emitted_roles


def _assert_native_placement_failure(controller: Roads, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_native(*_args, **_kwargs):
        raise RuntimeError("native probe failed")

    monkeypatch.setattr(Roads, "_run_segment_hillslope", fail_native)
    with pytest.raises(RuntimeError, match="1 segment"):
        controller.run_roads_wepp()
    failure = controller._last_run_summary["segment_execution_records"][0]
    assert failure["reason"] == "segment_run_failed"
    assert failure["placement_adjustment"] == "top_of_hillslope"
    assert failure["placement_source"] == "distance_to_channel_median"
    assert failure["discha_median_m"] == 100.
    assert failure["top_landuse_length_m"] == 0.
    assert failure["bottom_landuse_length_m"] == 1.
    assert failure["original_top_landuse_length_m"] == -79.


@pytest.mark.usefixtures("modeled_accounting_stub")
@pytest.mark.parametrize("legacy_prepare", [False, True])
@pytest.mark.parametrize("hill_length,expected_roles,native_failure", [(300., (3, 1, 2, 3), False), (25., (1, 2, 3), False), (24., (1, 2), False), (23., None, False), (25., (1, 2, 3), True)])
def test_run_roads_wepp_stages_outslope_unrutted_replacement_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    legacy_prepare: bool,
    hill_length: float,
    expected_roles,
    native_failure,
) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")

    _stub_unrutted_run(controller, monkeypatch, tmp_path, "roads-seg-007001", hill_length=hill_length)

    monkeypatch.setattr(Roads, "_select_outslope_unrutted_hillslope_segments", _select_single_candidate)
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

    emitted_roles = []

    def write_management(self, *, output_path, ofe_order, **_kwargs):
        emitted_roles.append(ofe_order)
        Path(output_path).write_text("management", encoding="utf-8")

    _stub_unrutted_inputs(monkeypatch, tmp_path, write_management)

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

    if legacy_prepare:
        _assert_stale_prepare_rejected(controller, monkeypatch)
        return
    if expected_roles is None:
        _assert_road_fill_exceeds_hillslope(controller, hill_length, emitted_roles)
        return
    if native_failure:
        _assert_native_placement_failure(controller, monkeypatch)
        return
    summary = controller.run_roads_wepp()
    record = summary["segment_execution_records"][0]
    assert emitted_roles == [expected_roles]
    assert record["contributor_ofe_count"] == len(expected_roles)
    assert record["placement_policy"] == "unrutted_top_placement_v1"
    assert summary["unrutted_placement_policy"] == "unrutted_top_placement_v1"
    assert record["upslope_runon_assumed_zero"] == (hill_length < 300)
    assert record["top_landuse_length_m"] == (196. if hill_length == 300 else 0.)
    slope_lines = (Path(controller.roads_runs_dir) / "p900001.slp").read_text().splitlines()
    assert int(slope_lines[1]) == len(expected_roles)
    assert record["sim_length_m"] == 4.0
    assert record["road_target_area_m2"] == pytest.approx(444.0)
    assert record["road_modeled_area_m2"] == pytest.approx(400.0)
    assert record["road_area_deficit_m2"] == pytest.approx(44.0)
    assert record["strip_width_factor"] == pytest.approx(100.0 / 111.0)
    hill = summary["outslope_unrutted_hillslope_records"][0]
    assert hill["reference_area_m2"] == pytest.approx(100. * hill_length)
    assert abs(hill["emitted_area_residual_m2"]) <= 1e-6

    assert summary["executed_outslope_unrutted_segment_count"] == 1
    assert summary["segment_design_counts"]["outslope_unrutted"] == 1
    assert summary["replacement_targeted_hillslope_wepp_ids"] == [1]
    assert summary["additive_targeted_hillslope_wepp_ids"] == []
    assert summary["pass_staging_strategy"]["1"] == "replacement"
    assert summary["outslope_unrutted_targeted_hillslope_count"] == 1
    assert summary["outslope_unrutted_included_segment_count"] == 1
    assert summary["outslope_unrutted_excluded_segment_count"] == 0
    assert summary["outslope_unrutted_capped_segment_count"] == 0
    assert (Path(controller.roads_output_dir) / "H1.pass.dat").read_text(encoding="utf-8") == "replacement pass"


@pytest.mark.usefixtures("modeled_accounting_stub")
def test_run_roads_wepp_outslope_unrutted_replacement_combines_phase4(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")

    _stub_unrutted_run(controller, monkeypatch, tmp_path, "roads-seg-007002")

    expected_segment_order: list[str] = []

    def _fake_select(self, *, pending_segments, **_kwargs):
        pending = pending_segments[0]
        seg_a = f"{pending['segment_id']}::h21::a"
        seg_b = f"{pending['segment_id']}::h21::b"
        expected_segment_order[:] = [seg_b, seg_a]
        candidate_a = {
            "segment_hillslope_id": seg_a,
            "source_segment_id": pending["segment_id"],
            "source_segment_ids": [pending["segment_id"]],
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
            "source_segment_ids": [pending["segment_id"]],
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

    def write_management(self, *, output_path, **_kwargs):
        Path(output_path).write_text("management", encoding="utf-8")

    _stub_unrutted_inputs(monkeypatch, tmp_path, write_management)

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
    assert summary["pass_staging_strategy"]["1"] == "replacement"
    assert len(combine_calls) == 1
    assert combine_calls[0]["strategy"] == "phase4"
    assert (Path(controller.roads_output_dir) / "H1.pass.dat").read_text(encoding="utf-8") == "combined replacement pass"
    executed_outslope_segments = [
        record["segment_hillslope_id"]
        for record in summary["segment_execution_records"]
        if record.get("design") == "outslope_unrutted" and record.get("status") == "completed"
    ]
    assert executed_outslope_segments[:2] == expected_segment_order


@pytest.mark.usefixtures("modeled_accounting_stub")
def test_run_roads_wepp_outslope_unrutted_missing_discha_with_no_selected_candidates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")

    _stub_unrutted_run(controller, monkeypatch, tmp_path, "roads-seg-007003", has_discha=False)

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
                "source_segment_ids": [pending["segment_id"]],
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
