"""Shared execution state across point contributors and unrutted replacements.

Native execution is the injected boundary; coordinators, input writers, strip
planning, manifest construction and summary aggregation run their real code.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from pyproj import CRS, Geod
import pytest
import rasterio
from rasterio.transform import from_origin

from wepppy.nodb.mods.roads import Roads, _execution, _unrutted, parameterization

pytestmark = [pytest.mark.unit, pytest.mark.nodb]


@pytest.mark.parametrize("fail_strip", [False, True])
def test_mixed_contributors_share_sequence_and_retain_both_routing_modes(
    tmp_path, monkeypatch, fail_strip
):
    roads = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    with roads.locked():
        roads._parameterization = parameterization.new_state()

    dem = tmp_path / "terrain.tif"
    with rasterio.open(
        dem, "w", driver="GTiff", height=2, width=2, count=1,
        dtype="float32", crs="EPSG:4326", transform=from_origin(0, 1, 1, 1),
    ) as dataset:
        dataset.write(np.zeros((2, 2), dtype="float32"), 1)
    watershed = SimpleNamespace(
        discha=str(dem), hillslope_length=lambda _topaz: 300.,
        hillslope_width=lambda _topaz: 100.,
    )
    wepp = SimpleNamespace(climate_instance=SimpleNamespace(input_years=1), wepp_bin="test")
    monkeypatch.setattr(Roads, "watershed_instance", property(lambda self: watershed))
    monkeypatch.setattr(Roads, "wepp_instance", property(lambda self: wepp))
    profile = dict(
        segment_length_m=30., raw_slope_pct=5., slope_pct=5.,
        elevation_high_m=20., elevation_low_m=18.5,
        high_point=[0., 0.], low_point=[0.001, 0.],
    )
    monkeypatch.setattr(Roads, "_build_segment_profile", lambda self, **kwargs: dict(profile))

    def feature(identifier, design):
        return {
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": [[0., 0.], [0.001, 0.]]},
            "properties": {
                "segment_id": identifier, "DESIGN": design, "SURFACE": "gravel",
                "TRAFFIC": "low", "SOIL_TEXTURE": "loam", "WIDTH_M": 4.,
                "topaz_id_hill_lowpoint": 21, "topaz_id_chn_lowpoint": 24,
                "_roads_routing_eligibility": "channel_associated",
                "FILL_LENGTH_M": 20., "FILL_SLOPE_PCT": 10.,
                "BUFFER_LENGTH_M": 30., "BUFFER_SLOPE_PCT": 10.,
            },
        }

    point, strip = feature("point", "inslope_bd"), feature("strip", "outslope_unrutted")
    candidate = {
        "segment_hillslope_id": "strip::h21", "source_segment_id": "strip",
        "source_segment_ids": ["strip"], "topaz_id_hill": 21,
        "feature": strip, "properties": strip["properties"],
        "overlap_length_m": 30., "inclusion_ratio": 0.3,
    }

    def select(self, *, pending_segments, **kwargs):
        assert [row["segment_id"] for row in pending_segments] == ["strip"]
        return (
            {1: [candidate]},
            {"outslope_unrutted_hillslope_records": [{
                "topaz_id_hill": 21, "segment_ids_included": ["strip::h21"],
                "segment_ids_excluded": [],
            }]},
            {"strip::h21": {**candidate, "status": "included"}},
        )

    monkeypatch.setattr(Roads, "_select_outslope_unrutted_hillslope_segments", select)
    attempts = []

    def native(self, *, segment_run_id, single_ofe_management_path,
               single_ofe_soil_path, single_ofe_slope_path, **kwargs):
        # Inspect the actual generated writer products before substituting the
        # model invocation. These files are also consumed by provenance assembly.
        assert all(Path(p).is_file() for p in (
            single_ofe_management_path, single_ofe_soil_path, single_ofe_slope_path,
        ))
        attempts.append(segment_run_id)
        if fail_strip and segment_run_id == 900002:
            raise RuntimeError("injected mixed strip execution failure")
        self._record_parameterization_inputs(
            single_ofe_soil_path, single_ofe_slope_path, single_ofe_management_path,
        )
        (Path(self.roads_output_dir) / f"H{segment_run_id}.pass.dat").write_text("native boundary stub\n")

    monkeypatch.setattr(Roads, "_run_segment_hillslope", native)
    params = roads._default_params()
    results = _execution.execute_segments(
        roads=roads, attribute_field_map=params["attribute_field_map"], dem_path=str(dem),
        # Deferral must preserve the common sequence even if unrutted comes first.
        features=[strip, point], geod=Geod(ellps="WGS84"), input_crs=CRS.from_epsg(4326),
        params=params, top2wepp={21: 1}, warning_limit=20,
    )

    assert attempts == [900001, 900002, 900003]
    assert results.segment_sequence == 3
    assert results.eligible_segment_count == results.mapped_segment_count == 2
    assert results.successful_segment_count == (2 if fail_strip else 3)
    assert len(results.failed_segment_records) == int(fail_strip)
    assert [Path(p).name for p in results.segment_pass_paths_by_wepp[1]] == ["H900001.pass.dat"]
    expected_replacements = ["H900003.pass.dat"] if fail_strip else ["H900002.pass.dat", "H900003.pass.dat"]
    assert [Path(p).name for p in results.replacement_pass_paths_by_wepp[1]] == expected_replacements
    assert results.routing_mode_counts["channel_associated"] == 1
    assert results.routing_mode_counts["outslope_unrutted_replacement_remainder"] == 1
    assert results.design_execution_counts["inslope_bd"] == 1
    assert results.design_execution_counts["outslope_unrutted"] == int(not fail_strip)

    _execution.write_execution_manifest(roads, results)
    manifest = json.loads(Path(roads.roads_segment_pass_manifest_path).read_text())
    assert [row["segment_run_id"] for row in manifest] == attempts
    assert [row["design"] for row in manifest] == [
        "inslope_bd", "outslope_unrutted", "outslope_unrutted_remainder",
    ]
    assert manifest[1]["placement_policy"] == _unrutted.PLACEMENT_POLICY
    assert manifest[2]["status"] == "completed"
    common = dict(
        roads=roads, results=results, attribute_field_map=params["attribute_field_map"],
        mapping_warning_count=sum(results.mapping_warning_counts.values()),
        mapping_warning_counts_dict=dict(results.mapping_warning_counts),
        placement_marker={"unrutted_placement_policy": _unrutted.PLACEMENT_POLICY},
        skipped_reason_counts=Counter(row["reason"] for row in results.skipped_segments),
    )
    if fail_strip:
        summary = _execution.build_failed_segment_summary(**common)
        assert summary["status"] == "failed"
        assert summary["failed_segment_count"] == 1
    else:
        summary = _execution.build_run_summary(
            **common, additive_targeted_ids=[1], replacement_targeted_ids=[1],
            targeted_ids=[1], staged_strategy={},
        )
    assert summary["additive_targeted_hillslope_wepp_ids"] == [1]
    assert summary["replacement_targeted_hillslope_wepp_ids"] == [1]
    assert summary["targeted_hillslope_wepp_ids"] == [1]
    assert summary["unrutted_placement_policy"] == _unrutted.PLACEMENT_POLICY
    assert summary["executed_segment_count"] == len(expected_replacements) + 1
