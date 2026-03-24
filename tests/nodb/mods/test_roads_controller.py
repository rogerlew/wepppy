from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import wepppy.nodb.mods.roads.roads as roads_module
from wepppy.nodb.mods.roads.monotonic_segments import MonotonicConversionSummary
from wepppy.nodb.mods.roads.roads import Roads

pytestmark = [pytest.mark.unit, pytest.mark.nodb]


def _write_roads_geojson(path: Path) -> None:
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
                            },
                        },
                        {
                            "type": "Feature",
                            "geometry": {"type": "LineString", "coordinates": [[1.0, 1.0], [2.0, 2.0]]},
                            "properties": {
                                "segment_id": "roads-seg-000002",
                                "DESIGN": "Outslope",
                                "topaz_id_chn_lowpoint": None,
                                "topaz_id_hill_lowpoint": None,
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
    assert summary["eligible_lowpoint_decision_counts"] == {"unknown": 1}
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
                            "DESIGN": "Outslope",
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

    def _fake_make(years: int, wepp_id_paths, runs_dir: str) -> None:
        captured_make["years"] = years
        captured_make["wepp_id_paths"] = list(wepp_id_paths)
        captured_make["runs_dir"] = runs_dir

    monkeypatch.setattr(roads_module, "make_watershed_omni_contrasts_run", _fake_make)
    monkeypatch.setattr(roads_module, "run_watershed", lambda runs_dir: None)

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
    assert Path(tmp_path / summary["segment_pass_manifest_relpath"]).exists()
    assert (Path(controller.roads_output_dir) / "H1.pass.dat").read_text(encoding="utf-8") == "combined"
    assert summary["roads_log_relpath"] == "wepp/roads/roads.log"
    assert Path(controller.roads_log_path).exists()
    assert captured_make["years"] == 25
    assert captured_make["runs_dir"] == controller.roads_runs_dir


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
