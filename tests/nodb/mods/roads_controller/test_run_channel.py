from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

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


def _stub_single_ofe_inputs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
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


@pytest.mark.usefixtures("modeled_accounting_stub")
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


@pytest.mark.usefixtures("modeled_accounting_stub")
def test_run_roads_wepp_maps_hillslopes_and_runs_watershed(
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
    )

    (tmp_path / "dem").mkdir(parents=True, exist_ok=True)
    _stub_baseline_wepp(monkeypatch, tmp_path, (1, 2))
    _stub_wbt_watershed(monkeypatch, (1, 2))

    _stub_prepare_rasters(monkeypatch, tmp_path)

    controller.set_enabled(True)
    _seed_prepared_state(controller)

    _stub_single_ofe_inputs(monkeypatch, tmp_path)
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
    captured_run: dict[str, object] = {}

    def _fake_run(runs_dir: str, *, wepp_bin: str | None = None) -> None:
        captured_run.update(runs_dir=runs_dir, wepp_bin=wepp_bin)

    monkeypatch.setattr(roads_module, "run_watershed", _fake_run)
    monkeypatch.setattr(Roads, "_regenerate_roads_report_resources", _ready_report_resources_stub)

    summary = controller.run_roads_wepp()
    status = controller.query_status()

    assert status["status"] == "completed"
    assert summary["eligible_segment_count"] == 1
    assert summary["mapped_segment_count"] == 1
    assert summary["executed_segment_count"] == 1
    assert summary["targeted_hillslope_wepp_ids"] == [1]
    assert summary["pass_staging_strategy"]["1"] == "additive"
    assert summary["pass_staging_strategy"]["2"] == "unchanged"
    assert summary["skipped_segment_reason_counts"] == {"design_not_eligible": 1}
    assert summary["segment_pass_count"] == 1
    assert len(summary["segment_execution_records"]) == 1
    assert summary["segment_execution_records"][0]["status"] == "completed"
    assert summary["roads_report_resources"]["status"] == "ready"
    assert Path(tmp_path / summary["segment_pass_manifest_relpath"]).exists()
    assert (Path(controller.roads_output_dir) / "H1.pass.dat").read_text(encoding="utf-8") == "combined"
    assert summary["roads_log_relpath"] == "wepp/roads/roads.log"
    assert Path(controller.roads_log_path).exists()
    assert captured_run == {
        "runs_dir": controller.roads_runs_dir,
        "wepp_bin": controller.wepp_instance.wepp_bin,
    }
    assert captured_make["wepp_bin"] == captured_run["wepp_bin"]
    assert captured_make["years"] == 25
    assert captured_make["runs_dir"] == controller.roads_runs_dir


@pytest.mark.usefixtures("modeled_accounting_stub")
def test_run_roads_wepp_runs_outslope_rutted_channel_associated_with_fill_defaults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    controller.set_params({"fill_length_default_m": 33.0, "fill_slope_default_pct": 11.0})

    _write_prepared_segments(
        controller,
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
    )

    _stub_baseline_wepp(monkeypatch, tmp_path, (1,))
    _stub_wbt_watershed(monkeypatch, (1,))

    _stub_prepare_rasters(monkeypatch, tmp_path)
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
    monkeypatch.setattr(roads_module, "run_watershed", lambda _runs_dir, *, wepp_bin: None)
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


@pytest.mark.usefixtures("modeled_accounting_stub")
def test_run_roads_wepp_persists_failed_summary_on_watershed_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tests.observability.canaries import install_canary
    canary = install_canary(monkeypatch, tmp_path)
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
                        "segment_id": "roads-seg-000001",
                        "DESIGN": "Inslope_rd",
                        "topaz_id_chn_lowpoint": 24,
                        "topaz_id_hill_lowpoint": 21,
                    },
                }
            ],
        }
    )

    (tmp_path / "dem").mkdir(parents=True, exist_ok=True)
    _stub_baseline_wepp(monkeypatch, tmp_path, (1,))
    _stub_wbt_watershed(monkeypatch, (1,))

    _stub_prepare_rasters(monkeypatch, tmp_path)
    controller.set_enabled(True)
    _seed_prepared_state(controller)

    _stub_single_ofe_inputs(monkeypatch, tmp_path)
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
    monkeypatch.setattr(roads_module, "run_watershed", lambda _runs_dir, *, wepp_bin: (_ for _ in ()).throw(Exception("watershed boom " + canary)))

    with pytest.raises(Exception, match="watershed boom"):
        controller.run_roads_wepp()

    status = controller.query_status()
    summary = controller.query_summary()
    last_run = summary["last_run_summary"]

    assert status["status"] == "failed"
    assert status["errors"] == ["watershed boom [REDACTED]"]
    assert last_run is not None
    assert last_run["status"] == "failed"
    assert last_run["failed_stage"] == "watershed_rerun"
    assert last_run["executed_segment_count"] == 1
    assert last_run["targeted_hillslope_wepp_ids"] == [1]
    assert last_run["segment_pass_count"] == 1

    persisted = Path(controller._nodb).read_text()
    assert canary not in persisted and "watershed boom [REDACTED]" in persisted
    for artifact in tmp_path.rglob("*.json"):
        assert canary not in artifact.read_text()


@pytest.mark.usefixtures("modeled_accounting_stub")
def test_run_roads_wepp_fails_when_segment_execution_fails(
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
                        "segment_id": "roads-seg-000001",
                        "DESIGN": "Inslope_rd",
                        "topaz_id_chn_lowpoint": 24,
                        "topaz_id_hill_lowpoint": 21,
                    },
                }
            ],
        }
    )

    (tmp_path / "dem").mkdir(parents=True, exist_ok=True)
    _stub_baseline_wepp(monkeypatch, tmp_path, (1,), baseline_file=False)
    _stub_wbt_watershed(monkeypatch, (1,))

    _stub_prepare_rasters(monkeypatch, tmp_path)
    controller.set_enabled(True)
    _seed_prepared_state(controller)

    _stub_single_ofe_inputs(monkeypatch, tmp_path)
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
