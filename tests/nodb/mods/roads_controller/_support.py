from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import wepppy.nodb.mods.roads.roads as roads_module
from wepppy.nodb.mods.roads.roads import Roads


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
        controller._parameterization = roads_module.roads_parameterization.new_state()
        controller._last_prepare_summary = {
            "uploaded_geojson_sha256": upload_sha,
            "roads_params_signature": controller._params_signature(params),
            "parameterization_hash": roads_module.roads_parameterization.configuration_hash(controller._parameterization),
            "unrutted_geometry_policy": "unrutted_strips_v1",
        }
        controller._status = "prepared"


def _write_prepared_segments(controller: Roads, payload: dict[str, object]) -> None:
    path = Path(controller.roads_monotonic_geojson_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _ready_report_resources_stub(controller: Roads) -> dict[str, object]:
    import pyarrow as pa
    import pyarrow.parquet as pq

    from wepppy.wepp.interchange._roads_lifecycle import mandatory_paths
    paths = sorted(mandatory_paths(False))
    for relative in paths:
        path = Path(controller.wd) / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == '.parquet':
            pq.write_table(pa.table({'stub_value': [1.0]}), path)
        else:
            path.write_text('orchestration fixture')
    return {
        "is_single_storm": False,
        "status": "ready",
        "output_scope": "roads",
        "roads_output_relpath": "wepp/roads/output",
        "interchange_relpath": "wepp/roads/output/interchange",
        "required_relpaths": paths,
        "missing_relpaths": [],
        "generated_at": 1234567890,
    }


def _stub_baseline_wepp(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    hillslope_ids: tuple[int, ...],
    *,
    wepp_bin: str = "wepp_dcc52a6",
    baseline_file: bool = True,
) -> None:
    runs_dir = tmp_path / "wepp" / "runs"
    output_dir = tmp_path / "wepp" / "output"
    runs_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    if baseline_file:
        (runs_dir / "baseline.txt").write_text("baseline", encoding="utf-8")
    (runs_dir / "p1.cli").write_text("climate", encoding="utf-8")
    for wepp_id in hillslope_ids:
        (output_dir / f"H{wepp_id}.pass.dat").write_text(f"h{wepp_id} baseline", encoding="utf-8")

    wepp_instance = SimpleNamespace(
        runs_dir=str(runs_dir),
        output_dir=str(output_dir),
        climate_instance=SimpleNamespace(input_years=25),
        wepp_bin=wepp_bin,
        pass_family="legacy_ascii",
    )
    monkeypatch.setattr(Roads, "wepp_instance", property(lambda self: wepp_instance))


def _stub_wbt_watershed(
    monkeypatch: pytest.MonkeyPatch,
    hillslope_ids: tuple[int, ...],
    **watershed_attributes,
) -> None:
    translator = SimpleNamespace(top2wepp={21: 1}, iter_wepp_sub_ids=lambda: iter(hillslope_ids))
    watershed_instance = SimpleNamespace(
        delineation_backend_is_wbt=True,
        translator_factory=lambda: translator,
        **watershed_attributes,
    )
    monkeypatch.setattr(Roads, "watershed_instance", property(lambda self: watershed_instance))


def _prepare_raster_paths(tmp_path: Path) -> dict[str, str]:
    dem_dir = tmp_path / "dem"
    return {
        "dem_path": str(dem_dir / "relief.tif"),
        "channel_raster_path": str(dem_dir / "netful.tif"),
        "topaz_id_raster_path": str(dem_dir / "subwta.tif"),
    }


class _ConstantDemDataset:
    crs = "EPSG:4326"
    nodata = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    @staticmethod
    def sample(_coords):
        return iter(([100.0],))


def _stub_prepare_rasters(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(Roads, "_resolve_prepare_raster_paths", lambda self: _prepare_raster_paths(tmp_path))
    monkeypatch.setattr(roads_module.rasterio, "open", lambda _path: _ConstantDemDataset())
