from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

import wepppy.nodb.mods.roads.roads as roads_module
from wepppy.nodb.mods.roads.roads import Roads

from ._support import (
    _ConstantDemDataset,
    _prepare_raster_paths,
    _ready_report_resources_stub,
    _seed_prepared_state,
    _stub_baseline_wepp,
    _stub_wbt_watershed,
    _write_prepared_segments,
)

pytestmark = [pytest.mark.unit, pytest.mark.nodb]


def _stub_trace_rasters(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    raster_paths = _prepare_raster_paths(tmp_path)
    trace_paths = {**raster_paths, "flovec_path": str(tmp_path / "dem" / "flovec.tif")}
    monkeypatch.setattr(Roads, "_resolve_prepare_raster_paths", lambda self: dict(raster_paths))
    monkeypatch.setattr(Roads, "_resolve_trace_raster_paths", lambda self: dict(trace_paths))

    class _FakeTopazDataset:
        nodata = -9999.0

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        @staticmethod
        def read(_idx, *, masked=False):
            data = np.array(
                [[11.0, 12.0, 14.0], [20.0, 21.0, 24.0], [31.0, 32.0, 34.0]],
                dtype=np.float32,
            )
            if masked:
                return np.ma.array(data, mask=np.zeros_like(data, dtype=bool))
            return data

    def open_raster(path, *_args, **_kwargs):
        if str(path).endswith("subwta.tif"):
            return _FakeTopazDataset()
        return _ConstantDemDataset()

    monkeypatch.setattr(roads_module.rasterio, "open", open_raster)


@pytest.mark.usefixtures("modeled_accounting_stub")
def test_run_roads_wepp_routes_non_channel_routable_segments_with_trace_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")

    _write_prepared_segments(
        controller,
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
    )

    _stub_baseline_wepp(monkeypatch, tmp_path, (1, 2))
    _stub_wbt_watershed(monkeypatch, (1, 2))

    _stub_trace_rasters(monkeypatch, tmp_path)
    controller.set_enabled(True)
    _seed_prepared_state(controller)

    tracer_calls: list[tuple[int, int]] = []
    import wepppyo3.roads_flowpath as roads_flowpath_module

    def _fake_trace(_subwta_path, _flovec_path, _relief_path, seed_row: int, seed_col: int, **_kwargs):
        assert _kwargs["wbt"] is True
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
    monkeypatch.setattr(roads_module, "run_watershed", lambda _runs_dir, *, wepp_bin: None)
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


@pytest.mark.usefixtures("modeled_accounting_stub")
def test_run_roads_wepp_routes_outslope_rutted_non_channel_with_three_ofe_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")

    _write_prepared_segments(
        controller,
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
    )

    _stub_baseline_wepp(monkeypatch, tmp_path, (1,))
    _stub_wbt_watershed(monkeypatch, (1,))

    _stub_trace_rasters(monkeypatch, tmp_path)
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
    monkeypatch.setattr(roads_module, "run_watershed", lambda _runs_dir, *, wepp_bin: None)
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


@pytest.mark.usefixtures("modeled_accounting_stub")
def test_run_roads_wepp_skips_non_channel_routable_segment_when_trace_does_not_reach_channel(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    _write_prepared_segments(
        controller,
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
    )

    _stub_baseline_wepp(monkeypatch, tmp_path, (1, 2))
    _stub_wbt_watershed(monkeypatch, (1, 2))

    _stub_trace_rasters(monkeypatch, tmp_path)
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
    monkeypatch.setattr(roads_module, "run_watershed", lambda _runs_dir, *, wepp_bin: None)
    monkeypatch.setattr(Roads, "_regenerate_roads_report_resources", _ready_report_resources_stub)

    summary = controller.run_roads_wepp()

    assert summary["status"] == "completed"
    assert summary["executed_segment_count"] == 0
    assert summary["trace_invocation_count"] == 1
    assert summary["trace_reached_channel_count"] == 0
    assert summary["trace_termination_reason_counts"] == {"raster_edge": 1}
    assert summary["targeted_hillslope_count"] == 0
    assert summary["skipped_segment_reason_counts"] == {"trace_did_not_reach_channel": 1}
