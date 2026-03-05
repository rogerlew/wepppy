from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

import wepppy.topo.wbt.terrain_processor as terrain_processor_module
from wepppy.topo.wbt.terrain_processor import (
    TerrainConfig,
    TerrainProcessor,
    TerrainProcessorRuntimeError,
)
from wepppy.topo.wbt.terrain_processor_helpers import FlowStackArtifacts, GeometryInputError

pytestmark = pytest.mark.unit


def _write_raster(path: Path, data: np.ndarray, *, nodata: float | int | None = None) -> None:
    import rasterio
    from rasterio.transform import from_origin

    profile = {
        "driver": "GTiff",
        "height": data.shape[0],
        "width": data.shape[1],
        "count": 1,
        "dtype": data.dtype,
        "crs": "EPSG:32611",
        "transform": from_origin(0.0, 0.0, 1.0, 1.0),
        "nodata": nodata,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, "w", **profile) as ds:
        ds.write(data, 1)


def _read_raster(path: Path) -> np.ndarray:
    import rasterio

    with rasterio.open(path) as ds:
        return ds.read(1)


def _copy_raster(input_path: str | Path, output_path: str | Path, *, delta: float = 0.0) -> None:
    src_path = Path(input_path)
    dst_path = Path(output_path)
    import rasterio

    with rasterio.open(src_path) as src:
        arr = src.read(1).astype(np.float32)
        profile = src.profile.copy()

    arr = arr + float(delta)
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(dst_path, "w", **profile) as dst:
        dst.write(arr.astype(profile["dtype"]), 1)


def _write_geojson(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


class _WbtStub:
    def feature_preserving_smoothing(self, **kwargs: Any) -> None:
        _copy_raster(kwargs["i"], kwargs["output"], delta=0.1)

    def gaussian_filter(self, **kwargs: Any) -> None:
        _copy_raster(kwargs["i"], kwargs["output"], delta=0.05)

    def mean_filter(self, **kwargs: Any) -> None:
        _copy_raster(kwargs["i"], kwargs["output"], delta=0.02)

    def raise_roads(self, **kwargs: Any) -> None:
        _copy_raster(kwargs["dem"], kwargs["output"], delta=1.0)
        embankment_mask = kwargs.get("embankment_mask")
        if embankment_mask:
            mask = np.zeros((5, 5), dtype=np.uint8)
            mask[2, 2] = 1
            _write_raster(Path(embankment_mask), mask, nodata=0)

    def fill_depressions(self, **kwargs: Any) -> None:
        _copy_raster(kwargs["dem"], kwargs["output"], delta=0.25)

    def breach_depressions(self, **kwargs: Any) -> None:
        _copy_raster(kwargs["dem"], kwargs["output"], delta=-0.5)

    def breach_depressions_least_cost(self, **kwargs: Any) -> None:
        _copy_raster(kwargs["dem"], kwargs["output"], delta=-0.25)

    def burn_streams_at_roads(self, **kwargs: Any) -> None:
        _copy_raster(kwargs["dem"], kwargs["output"], delta=-0.1)

    def find_outlet(self, **kwargs: Any) -> None:
        requested = kwargs.get("requested_outlet_lng_lat")
        if requested is None:
            requested = (1.0, 1.0)
        x, y = requested
        payload = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"column": 1, "row": 1},
                    "geometry": {"type": "Point", "coordinates": [float(x), float(y)]},
                }
            ],
        }
        _write_geojson(Path(kwargs["output"]), payload)

    def watershed(self, **kwargs: Any) -> None:
        output = Path(kwargs["output"])
        mask = np.zeros((5, 5), dtype=np.uint8)
        mask[1:4, 1:4] = 1
        _write_raster(output, mask, nodata=0)

    def unnest_basins(self, **kwargs: Any) -> str:
        output = Path(kwargs["output"])
        hierarchy = Path(kwargs["hierarchy"])
        data = np.zeros((5, 5), dtype=np.int16)
        data[1:3, 1:3] = 1
        data[3:5, 3:5] = 2
        _write_raster(output, data, nodata=0)
        hierarchy.write_text(
            "basin_id,parent_id,outlet_x,outlet_y,area,stream_order\n"
            "1,,100.0,200.0,10.0,2\n"
            "2,1,120.0,220.0,7.5,1\n"
        )
        return str(hierarchy)


class _EmulatorStub:
    def __init__(self, *, wbt_wd: str, dem_fn: str) -> None:
        self.wbt_wd = wbt_wd
        self._dem = dem_fn
        self.wbt = _WbtStub()
        self.cellsize = 1.0
        self.epsg = 32611
        self.flovec = str(Path(wbt_wd) / "flovec.tif")
        self.netful = str(Path(wbt_wd) / "netful.tif")
        self.outlet_geojson = str(Path(wbt_wd) / "outlet.geojson")
        self.bound = str(Path(wbt_wd) / "bound.tif")
        self.bound_json = str(Path(wbt_wd) / "bound.geojson")
        self.bound_wgs_json = str(Path(wbt_wd) / "bound.wgs.geojson")
        _copy_raster(dem_fn, self.flovec)
        _copy_raster(dem_fn, self.netful)

    def _parse_dem(self, dem_fn: str) -> None:
        self._dem = dem_fn

    def set_outlet(self, lng: float, lat: float, pixelcoords: bool = False) -> Any:
        _ = pixelcoords
        self.wbt.find_outlet(
            d8_pntr=self.flovec,
            streams=self.netful,
            output=self.outlet_geojson,
            requested_outlet_lng_lat=(lng, lat),
        )
        return SimpleNamespace(
            requested_loc=(lng, lat),
            actual_loc=(lng, lat),
            distance_from_requested=0.0,
            pixel_coords=(1, 1),
        )

    def set_outlet_from_geojson(self, geojson_path: str) -> Any:
        payload = json.loads(Path(geojson_path).read_text())
        coords = payload["features"][0]["geometry"]["coordinates"]
        return SimpleNamespace(
            requested_loc=(coords[0], coords[1]),
            actual_loc=(coords[0], coords[1]),
            distance_from_requested=0.0,
            pixel_coords=(1, 1),
        )

    def _create_bound(self) -> None:
        self.wbt.watershed(
            d8_pntr=self.flovec,
            pour_pts=self.outlet_geojson,
            output=self.bound,
        )
        boundary_geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"id": 1},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[0, 0], [0, 5], [5, 5], [5, 0], [0, 0]]],
                    },
                }
            ],
        }
        _write_geojson(Path(self.bound_json), boundary_geojson)
        _write_geojson(Path(self.bound_wgs_json), boundary_geojson)


def _make_dem(tmp_path: Path) -> Path:
    dem_path = tmp_path / "dem.tif"
    dem = np.arange(25, dtype=np.float32).reshape((5, 5))
    _write_raster(dem_path, dem, nodata=-9999.0)
    return dem_path


def _make_roads_geojson(tmp_path: Path) -> Path:
    roads_path = tmp_path / "roads.geojson"
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"id": 1},
                "geometry": {"type": "LineString", "coordinates": [[0.0, 1.0], [4.0, 1.0]]},
            }
        ],
    }
    _write_geojson(roads_path, payload)
    return roads_path


def _make_culverts_geojson(tmp_path: Path) -> Path:
    culverts_path = tmp_path / "culverts.geojson"
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"id": 10},
                "geometry": {"type": "Point", "coordinates": [1.0, 1.0]},
            }
        ],
    }
    _write_geojson(culverts_path, payload)
    return culverts_path


@pytest.fixture
def flow_stack_stub(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    def _stub(
        emulator: Any,
        *,
        csa: float,
        mcl: float,
        fill_or_breach: str = "fill",
        blc_dist: int | None = None,
        blc_max_cost: float | None = None,
        blc_fill: bool = True,
        **_: Any,
    ) -> FlowStackArtifacts:
        calls.append(
            {
                "csa": csa,
                "mcl": mcl,
                "fill_or_breach": fill_or_breach,
                "blc_dist": blc_dist,
                "blc_max_cost": blc_max_cost,
                "blc_fill": blc_fill,
            }
        )

        relief = Path(emulator.wbt_wd) / "relief.tif"
        flovec = Path(emulator.wbt_wd) / "flovec.tif"
        floaccum = Path(emulator.wbt_wd) / "floaccum.tif"
        netful = Path(emulator.wbt_wd) / "netful.tif"
        netful_geojson = Path(emulator.wbt_wd) / "netful.geojson"
        chnjnt = Path(emulator.wbt_wd) / "chnjnt.tif"

        _copy_raster(emulator._dem, relief, delta=0.5)
        _copy_raster(relief, flovec, delta=0.1)
        _copy_raster(flovec, floaccum, delta=0.1)
        _copy_raster(floaccum, netful, delta=0.1)
        _copy_raster(netful, chnjnt, delta=0.1)
        _write_geojson(
            netful_geojson,
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"id": len(calls)},
                        "geometry": {
                            "type": "LineString",
                            "coordinates": [[0.0, 0.0], [4.0, 4.0]],
                        },
                    }
                ],
            },
        )

        emulator.flovec = str(flovec)
        emulator.netful = str(netful)

        return FlowStackArtifacts(
            relief_path=str(relief),
            flow_vector_path=str(flovec),
            flow_accumulation_path=str(floaccum),
            stream_raster_path=str(netful),
            stream_geojson_path=str(netful_geojson),
            stream_junctions_path=str(chnjnt),
        )

    monkeypatch.setattr(terrain_processor_module, "derive_flow_stack", _stub)
    return calls


def _build_processor(
    *,
    tmp_path: Path,
    config: TerrainConfig,
) -> TerrainProcessor:
    dem_path = _make_dem(tmp_path)
    emulator = _EmulatorStub(wbt_wd=str(tmp_path), dem_fn=str(dem_path))
    return TerrainProcessor(
        wbt_wd=str(tmp_path),
        dem_path=str(dem_path),
        config=config,
        emulator=emulator,
    )


def test_terrain_processor_phase1_dem_preparation_artifacts(tmp_path: Path) -> None:
    roads_path = _make_roads_geojson(tmp_path)
    processor = _build_processor(
        tmp_path=tmp_path,
        config=TerrainConfig(
            smooth=True,
            roads_source="upload",
            roads_path=str(roads_path),
            outlet_mode="auto",
        ),
    )

    processor._run_phase1_dem_preparation(())
    phase1 = processor.artifacts_by_phase["phase1_dem_preparation"]

    assert Path(phase1["dem_raw"]).exists()
    assert Path(phase1["dem_smoothed"]).exists()
    assert Path(phase1["dem_roads"]).exists()
    assert Path(phase1["embankment_mask"]).exists()
    assert Path(phase1["roads_utm_geojson"]).exists()


def test_terrain_processor_phase2_conditioning_bounded_breach_two_pass(
    tmp_path: Path,
    flow_stack_stub: list[dict[str, Any]],
) -> None:
    roads_path = _make_roads_geojson(tmp_path)
    processor = _build_processor(
        tmp_path=tmp_path,
        config=TerrainConfig(
            smooth=True,
            roads_source="upload",
            roads_path=str(roads_path),
            conditioning="bounded_breach",
            outlet_mode="auto",
        ),
    )

    processor._run_phase1_dem_preparation(())
    processor._run_phase2_conditioning_flow_stack(())
    phase2 = processor.artifacts_by_phase["phase2_conditioning_flow_stack"]

    assert Path(phase2["filled_dem"]).exists()
    assert Path(phase2["composite_dem"]).exists()
    assert Path(phase2["relief"]).exists()
    assert len(flow_stack_stub) == 2
    assert flow_stack_stub[0]["fill_or_breach"] == "fill"
    assert flow_stack_stub[1]["fill_or_breach"] == "breach_least_cost"


def test_terrain_processor_phase2_passes_blc_controls_to_flow_stack(
    tmp_path: Path,
    flow_stack_stub: list[dict[str, Any]],
) -> None:
    roads_path = _make_roads_geojson(tmp_path)
    processor = _build_processor(
        tmp_path=tmp_path,
        config=TerrainConfig(
            roads_source="upload",
            roads_path=str(roads_path),
            conditioning="breach_least_cost",
            blc_dist_m=250.0,
            blc_max_cost=12.5,
            blc_fill=False,
            outlet_mode="auto",
        ),
    )

    processor._run_phase1_dem_preparation(())
    processor._run_phase2_conditioning_flow_stack(())

    assert len(flow_stack_stub) == 1
    assert flow_stack_stub[0]["fill_or_breach"] == "breach_least_cost"
    assert flow_stack_stub[0]["blc_dist"] == 250
    assert flow_stack_stub[0]["blc_max_cost"] == pytest.approx(12.5)
    assert flow_stack_stub[0]["blc_fill"] is False


def test_terrain_processor_phase3_culvert_enforcement_reruns_flow_stack(
    tmp_path: Path,
    flow_stack_stub: list[dict[str, Any]],
) -> None:
    roads_path = _make_roads_geojson(tmp_path)
    culvert_path = _make_culverts_geojson(tmp_path)
    processor = _build_processor(
        tmp_path=tmp_path,
        config=TerrainConfig(
            roads_source="upload",
            roads_path=str(roads_path),
            conditioning="breach",
            enforce_culverts=True,
            culvert_source="upload_points",
            culvert_path=str(culvert_path),
            outlet_mode="auto",
        ),
    )

    processor._run_phase1_dem_preparation(())
    processor._run_phase2_conditioning_flow_stack(())
    processor._run_phase3_culvert_enforcement(())
    phase3 = processor.artifacts_by_phase["phase3_culvert_enforcement"]

    assert Path(phase3["culvert_points_geojson"]).exists()
    assert Path(phase3["relief_burned"]).exists()
    assert Path(phase3["netful_geojson_v2"]).exists()
    assert len(flow_stack_stub) == 2
    assert flow_stack_stub[1]["fill_or_breach"] == "breach"


def test_terrain_processor_phase4_multiple_outlet_hierarchy(tmp_path: Path, flow_stack_stub: list[dict[str, Any]]) -> None:
    roads_path = _make_roads_geojson(tmp_path)
    processor = _build_processor(
        tmp_path=tmp_path,
        config=TerrainConfig(
            roads_source="upload",
            roads_path=str(roads_path),
            outlet_mode="multiple",
            outlets=((1.0, 1.0), (3.0, 3.0)),
        ),
    )

    processor._run_phase1_dem_preparation(())
    processor._run_phase2_conditioning_flow_stack(())
    processor._run_phase4_outlet_resolution(())
    phase4 = processor.artifacts_by_phase["phase4_outlet_resolution"]

    assert Path(phase4["outlets_snapped_geojson"]).exists()
    assert Path(phase4["unnested_tif"]).exists()
    assert Path(phase4["hierarchy_csv"]).exists()
    assert len(processor.basin_summaries) == 2
    _ = flow_stack_stub


def test_terrain_processor_phase4_multiple_outlet_hierarchy_supports_wbt_without_hierarchy_kwarg(
    tmp_path: Path,
    flow_stack_stub: list[dict[str, Any]],
) -> None:
    class _WbtNoHierarchy(_WbtStub):
        def unnest_basins(self, d8_pntr: str, pour_pts: str, output: str, esri_pntr: bool = False) -> None:
            _ = (d8_pntr, pour_pts, esri_pntr)
            output_path = Path(output)
            data = np.zeros((5, 5), dtype=np.int16)
            data[1:3, 1:3] = 1
            data[3:5, 3:5] = 2
            _write_raster(output_path, data, nodata=0)
            output_path.with_suffix(".csv").write_text(
                "basin_id,parent_id,outlet_x,outlet_y,area,stream_order\n"
                "1,,100.0,200.0,10.0,2\n"
                "2,1,120.0,220.0,7.5,1\n"
            )

    roads_path = _make_roads_geojson(tmp_path)
    processor = _build_processor(
        tmp_path=tmp_path,
        config=TerrainConfig(
            roads_source="upload",
            roads_path=str(roads_path),
            outlet_mode="multiple",
            outlets=((1.0, 1.0), (3.0, 3.0)),
        ),
    )
    processor._emulator.wbt = _WbtNoHierarchy()  # type: ignore[attr-defined]

    processor._run_phase1_dem_preparation(())
    processor._run_phase2_conditioning_flow_stack(())
    processor._run_phase4_outlet_resolution(())
    phase4 = processor.artifacts_by_phase["phase4_outlet_resolution"]

    assert Path(phase4["unnested_tif"]).exists()
    assert Path(phase4["hierarchy_csv"]).exists()
    assert phase4["hierarchy_csv"].endswith("unnested.csv")
    assert len(processor.basin_summaries) == 2
    _ = flow_stack_stub


def test_terrain_processor_phase5_visualization_manifest_contract(
    tmp_path: Path,
    flow_stack_stub: list[dict[str, Any]],
) -> None:
    roads_path = _make_roads_geojson(tmp_path)
    processor = _build_processor(
        tmp_path=tmp_path,
        config=TerrainConfig(
            smooth=True,
            roads_source="upload",
            roads_path=str(roads_path),
            outlet_mode="auto",
        ),
    )

    processor._run_phase1_dem_preparation(())
    processor._run_phase2_conditioning_flow_stack(())
    processor._run_phase4_outlet_resolution(())
    processor._run_phase5_visualization_artifacts(())
    phase5 = processor.artifacts_by_phase["phase5_visualization_artifacts"]

    manifest_path = Path(phase5["visualization_manifest_json"])
    benchmark_path = Path(phase5["visualization_benchmarks_json"])
    ui_payload_path = Path(phase5["visualization_ui_payload_json"])
    assert manifest_path.exists()
    assert benchmark_path.exists()
    assert ui_payload_path.exists()
    payload = json.loads(manifest_path.read_text())
    artifact_ids = [entry["artifact_id"] for entry in payload["entries"]]
    assert artifact_ids == sorted(artifact_ids)
    assert "dem_raw_hillshade" in artifact_ids
    assert "dem_raw_to_dem_smoothed_diff" in artifact_ids
    assert "roads_utm_geojson_overlay" in artifact_ids
    hillshade_entry = next(entry for entry in payload["entries"] if entry["artifact_id"] == "dem_raw_hillshade")
    assert "generation_ms" in hillshade_entry.get("metadata", {})

    benchmark_payload = json.loads(benchmark_path.read_text())
    assert benchmark_payload["entries"]
    assert any(entry["operation"] == "hillshade_slope" for entry in benchmark_payload["entries"])
    ui_payload = json.loads(ui_payload_path.read_text())
    assert ui_payload["layer_count"] >= 1
    assert ui_payload["layers"]
    _ = flow_stack_stub


def test_terrain_processor_phase5_rejects_rasters_over_visualization_pixel_limit(
    tmp_path: Path,
    flow_stack_stub: list[dict[str, Any]],
) -> None:
    roads_path = _make_roads_geojson(tmp_path)
    processor = _build_processor(
        tmp_path=tmp_path,
        config=TerrainConfig(
            smooth=True,
            roads_source="upload",
            roads_path=str(roads_path),
            outlet_mode="auto",
            visualization_max_pixels=4,
        ),
    )

    processor._run_phase1_dem_preparation(())
    processor._run_phase2_conditioning_flow_stack(())
    processor._run_phase4_outlet_resolution(())

    with pytest.raises(TerrainProcessorRuntimeError) as exc_info:
        processor._run_phase5_visualization_artifacts(())
    assert exc_info.value.code == "visualization_raster_too_large"
    _ = flow_stack_stub


def test_terrain_processor_phase6_reentry_invalidates_expected_runtime_phases(
    tmp_path: Path,
    flow_stack_stub: list[dict[str, Any]],
) -> None:
    roads_path = _make_roads_geojson(tmp_path)
    config = TerrainConfig(
        smooth=True,
        roads_source="upload",
        roads_path=str(roads_path),
        outlet_mode="auto",
        snap_distance=20.0,
    )
    processor = _build_processor(tmp_path=tmp_path, config=config)

    first_result = processor.run()
    dem_raw = processor.artifacts_by_phase["phase1_dem_preparation"]["dem_raw"]
    dem_raw_mtime = os.path.getmtime(dem_raw)

    second_result = processor.rerun_with_config(replace(config, snap_distance=35.0))

    assert first_result.executed_phases == (
        "phase1_dem_preparation",
        "phase2_conditioning_flow_stack",
        "phase3_culvert_enforcement",
        "phase4_outlet_resolution",
        "phase5_visualization_artifacts",
        "phase6_invalidation_reentry",
    )
    assert second_result.invalidated_phases == (
        "phase4_outlet_resolution",
        "phase5_visualization_artifacts",
        "phase6_invalidation_reentry",
    )
    assert second_result.executed_phases == (
        "phase4_outlet_resolution",
        "phase5_visualization_artifacts",
        "phase6_invalidation_reentry",
    )
    assert os.path.getmtime(dem_raw) == pytest.approx(dem_raw_mtime)
    assert len(flow_stack_stub) == 1


def test_terrain_processor_phase6_run_end_to_end_with_manifest(
    tmp_path: Path,
    flow_stack_stub: list[dict[str, Any]],
) -> None:
    roads_path = _make_roads_geojson(tmp_path)
    processor = _build_processor(
        tmp_path=tmp_path,
        config=TerrainConfig(
            smooth=True,
            roads_source="upload",
            roads_path=str(roads_path),
            enforce_culverts=False,
            outlet_mode="auto",
        ),
    )
    result = processor.run()

    assert result.visualization_manifest_path is not None
    assert Path(result.visualization_manifest_path).exists()
    assert Path(result.current_dem_path).exists()
    assert len(result.provenance) >= 2
    assert len(flow_stack_stub) == 1
    diff_path = Path(tmp_path) / "visualization" / "dem_raw_to_dem_smoothed_diff.tif"
    assert diff_path.exists()
    diff = _read_raster(diff_path)
    assert np.isfinite(diff).any()


@pytest.mark.parametrize(
    ("config_override", "expected_code"),
    [
        ({"road_fill_strategy": "unsupported"}, "invalid_road_fill_strategy"),
        ({"culvert_road_width": 0.0}, "invalid_culvert_road_width"),
        ({"blc_max_cost": 0.0}, "invalid_blc_max_cost"),
        ({"blc_fill": "false"}, "invalid_blc_fill"),
        ({"visualization_max_pixels": 0}, "invalid_visualization_max_pixels"),
    ],
)
def test_terrain_processor_rejects_unsupported_or_invalid_config_options(
    tmp_path: Path,
    flow_stack_stub: list[dict[str, Any]],
    config_override: dict[str, Any],
    expected_code: str,
) -> None:
    roads_path = _make_roads_geojson(tmp_path)
    base = TerrainConfig(
        roads_source="upload",
        roads_path=str(roads_path),
        outlet_mode="auto",
    )
    config = replace(base, **config_override)
    processor = _build_processor(tmp_path=tmp_path, config=config)

    with pytest.raises(TerrainProcessorRuntimeError) as exc_info:
        processor.run()
    assert exc_info.value.code == expected_code
    _ = flow_stack_stub


def test_terrain_processor_translates_helper_intersection_errors(
    tmp_path: Path,
    flow_stack_stub: list[dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    roads_path = _make_roads_geojson(tmp_path)
    processor = _build_processor(
        tmp_path=tmp_path,
        config=TerrainConfig(
            roads_source="upload",
            roads_path=str(roads_path),
            conditioning="breach",
            enforce_culverts=True,
            outlet_mode="auto",
        ),
    )
    processor._run_phase1_dem_preparation(())
    processor._run_phase2_conditioning_flow_stack(())

    def _raise_helper(*args: Any, **kwargs: Any) -> dict[str, Any]:
        _ = (args, kwargs)
        raise GeometryInputError("invalid geojson")

    monkeypatch.setattr(terrain_processor_module, "extract_road_stream_intersections", _raise_helper)

    with pytest.raises(TerrainProcessorRuntimeError) as exc_info:
        processor._run_phase3_culvert_enforcement(())
    assert exc_info.value.code == "helper_culvert_intersection_error"
    assert exc_info.value.context.get("helper_code") == "geometry_input_error"
    _ = flow_stack_stub


def test_terrain_processor_phase1_invalidation_preserves_uploaded_roads_input(
    tmp_path: Path,
    flow_stack_stub: list[dict[str, Any]],
) -> None:
    roads_path = _make_roads_geojson(tmp_path)
    roads_content = roads_path.read_text()
    config = TerrainConfig(
        smooth=True,
        roads_source="upload",
        roads_path=str(roads_path),
        outlet_mode="auto",
        road_fill_margin=2.0,
    )
    processor = _build_processor(tmp_path=tmp_path, config=config)

    processor.run()
    processor.rerun_with_config(replace(config, road_fill_margin=3.0))

    assert roads_path.exists()
    assert roads_path.read_text() == roads_content
    assert len(flow_stack_stub) == 2
