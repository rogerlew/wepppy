from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import wepppy.nodb.wepp_nodb_post_utils as post_utils_module
import wepppy.wepp.interchange as interchange_module
from wepppy.nodb.mods.roads.roads import Roads

from ._support import _write_prepared_segments

pytestmark = [pytest.mark.unit, pytest.mark.nodb]


def _write_segment_manifest(controller: Roads, rows: list[dict[str, object]]) -> None:
    path = Path(controller.roads_segment_pass_manifest_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows), encoding="utf-8")


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


def test_build_roads_segment_loss_summary_delegates_execution_calendar(tmp_path: Path, monkeypatch) -> None:
    from wepppy.nodb.mods.roads import _segment_loss_summary

    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    climate = SimpleNamespace(input_years=16, calendar_start_year=2000)
    monkeypatch.setattr(Roads, "wepp_instance", property(lambda self: SimpleNamespace(climate_instance=climate)))
    observed = {}
    def build(root, folder, **kwargs):
        years, start = kwargs["execution_calendar"]()
        observed.update(root=root, folder=folder, expected_years=years, start_year=start)
        return "wepp/roads/output/interchange/roads_segment_loss_summary.parquet"
    monkeypatch.setattr(_segment_loss_summary, "build_segment_loss_summary", build)
    folder = Path(controller.roads_output_dir)/"interchange"
    assert controller._build_roads_segment_loss_summary_parquet(interchange_dir=folder).endswith(".parquet")
    assert observed == dict(root=tmp_path, folder=folder, expected_years=16, start_year=2000)


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

    from tests.roads_lifecycle_fixtures import write_current_roads_fixture
    write_current_roads_fixture(tmp_path)
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
