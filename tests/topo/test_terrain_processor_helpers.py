from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pytest

from wepppy.topo.wbt.terrain_processor_helpers import (
    BasinSummary,
    BurnStreamsAtRoadsValidationError,
    CulvertSnapError,
    GeometryInputError,
    ProvenanceEntry,
    TerrainArtifactRegistry,
    build_outlet_feature_collection,
    burn_streams_at_roads_adapter,
    create_bounded_breach_composite,
    create_masked_dem,
    derive_flow_stack,
    determine_invalidated_phases,
    extract_road_stream_intersections,
    load_culvert_points,
    parse_unnest_basins_hierarchy_csv,
    resolve_bounded_breach_collar_pixels,
    run_bounded_breach_workflow,
    snap_outlets_to_streams,
    snap_uploaded_culvert_points_to_crossings,
)

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

    with rasterio.open(path, "w", **profile) as ds:
        ds.write(data, 1)


def _read_raster(path: Path) -> np.ndarray:
    import rasterio

    with rasterio.open(path) as ds:
        return ds.read(1)


class _FlowStackEmulatorStub:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.csa: float | None = None
        self.mcl: float | None = None
        self.relief = "/tmp/relief.tif"
        self.flovec = "/tmp/flovec.tif"
        self.floaccum = "/tmp/floaccum.tif"
        self.netful = "/tmp/netful.tif"
        self.netful_json = "/tmp/netful.geojson"
        self.chnjnt = "/tmp/chnjnt.tif"

    def _create_relief(
        self,
        *,
        fill_or_breach: str,
        blc_dist: int | None = None,
        blc_max_cost: float | None = None,
        blc_fill: bool = True,
    ) -> None:
        self.calls.append(f"relief:{fill_or_breach}:{blc_dist}:{blc_max_cost}:{blc_fill}")

    def _create_flow_vector(self) -> None:
        self.calls.append("flow_vector")

    def _create_flow_accumulation(self) -> None:
        self.calls.append("flow_accumulation")

    def _extract_streams(self) -> None:
        self.calls.append("extract_streams")

    def _identify_stream_junctions(self) -> None:
        self.calls.append("stream_junctions")


def test_phase1_derive_flow_stack_executes_in_order() -> None:
    emulator = _FlowStackEmulatorStub()
    poly_calls: list[tuple[str, str]] = []
    wgs_calls: list[str] = []

    artifacts = derive_flow_stack(
        emulator,
        csa=5.0,
        mcl=60.0,
        fill_or_breach="breach_least_cost",
        blc_dist=500,
        blc_max_cost=7.5,
        blc_fill=False,
        polygonize_streams=lambda raster_path, geojson_path: poly_calls.append((raster_path, geojson_path)),
        reproject_streams_geojson=lambda geojson_path: wgs_calls.append(geojson_path),
    )

    assert emulator.calls == [
        "relief:breach_least_cost:500:7.5:False",
        "flow_vector",
        "flow_accumulation",
        "extract_streams",
        "stream_junctions",
    ]
    assert poly_calls == [("/tmp/netful.tif", "/tmp/netful.geojson")]
    assert wgs_calls == ["/tmp/netful.geojson"]
    assert artifacts.stream_raster_path == "/tmp/netful.tif"
    assert artifacts.stream_junctions_path == "/tmp/chnjnt.tif"


def test_phase1_derive_flow_stack_rejects_invalid_thresholds() -> None:
    emulator = _FlowStackEmulatorStub()
    with pytest.raises(ValueError, match="csa"):
        derive_flow_stack(emulator, csa=0.0, mcl=60.0)
    with pytest.raises(ValueError, match="mcl"):
        derive_flow_stack(emulator, csa=5.0, mcl=0.0)
    with pytest.raises(ValueError, match="blc_max_cost"):
        derive_flow_stack(emulator, csa=5.0, mcl=60.0, blc_max_cost=0.0)
    with pytest.raises(ValueError, match="blc_fill"):
        derive_flow_stack(
            emulator,
            csa=5.0,
            mcl=60.0,
            blc_fill="false",  # type: ignore[arg-type]
        )


def test_phase1_derive_flow_stack_rejects_missing_emulator_contract() -> None:
    class MissingContract:
        pass

    with pytest.raises(TypeError, match="missing required flow-stack contract members"):
        derive_flow_stack(MissingContract(), csa=5.0, mcl=60.0)


def test_phase2_resolve_bounded_breach_collar_defaults_and_override() -> None:
    assert resolve_bounded_breach_collar_pixels(cellsize_m=2.0, bounded_breach_collar_m=None) == 10
    assert resolve_bounded_breach_collar_pixels(cellsize_m=2.0, bounded_breach_collar_m=6.0) == 3
    assert resolve_bounded_breach_collar_pixels(cellsize_m=2.0, bounded_breach_collar_m=0.0) == 0


def test_phase2_resolve_bounded_breach_collar_rejects_invalid_numeric_inputs() -> None:
    with pytest.raises(ValueError, match="cellsize_m"):
        resolve_bounded_breach_collar_pixels(cellsize_m=0.0, bounded_breach_collar_m=10.0)
    with pytest.raises(ValueError, match="cannot be negative"):
        resolve_bounded_breach_collar_pixels(cellsize_m=2.0, bounded_breach_collar_m=-1.0)


def test_phase2_create_masked_dem_applies_collar(tmp_path: Path) -> None:
    prepared = np.arange(25, dtype=np.float32).reshape(5, 5)
    boundary = np.zeros((5, 5), dtype=np.uint8)
    boundary[2, 2] = 1

    prepared_path = tmp_path / "prepared.tif"
    boundary_path = tmp_path / "boundary.tif"
    masked_path = tmp_path / "masked.tif"

    _write_raster(prepared_path, prepared, nodata=-9999.0)
    _write_raster(boundary_path, boundary, nodata=0)

    create_masked_dem(
        prepared_dem_path=str(prepared_path),
        boundary_mask_path=str(boundary_path),
        output_masked_dem_path=str(masked_path),
        collar_pixels=1,
    )

    masked = _read_raster(masked_path)
    nodata = -9999.0
    assert masked[2, 2] == prepared[2, 2]
    assert masked[1, 1] == prepared[1, 1]
    assert masked[0, 0] == nodata
    assert masked[4, 4] == nodata


def test_phase2_run_bounded_breach_workflow_composites_interior(tmp_path: Path) -> None:
    prepared = np.array(
        [[1, 1, 1], [1, 10, 1], [1, 1, 1]],
        dtype=np.float32,
    )
    filled = np.full((3, 3), 5, dtype=np.float32)
    boundary = np.zeros((3, 3), dtype=np.uint8)
    boundary[1, 1] = 1

    prepared_path = tmp_path / "prepared.tif"
    filled_path = tmp_path / "filled.tif"
    boundary_path = tmp_path / "boundary.tif"
    masked_path = tmp_path / "masked.tif"
    breached_path = tmp_path / "breached.tif"
    composite_path = tmp_path / "composite.tif"

    _write_raster(prepared_path, prepared, nodata=-9999.0)
    _write_raster(filled_path, filled, nodata=-9999.0)
    _write_raster(boundary_path, boundary, nodata=0)

    def breach_runner(masked_input: str, breached_output: str) -> None:
        masked_arr = _read_raster(Path(masked_input))
        breached_arr = masked_arr.copy()
        breached_arr[1, 1] = 3.0
        _write_raster(Path(breached_output), breached_arr, nodata=-9999.0)

    artifacts = run_bounded_breach_workflow(
        prepared_dem_path=str(prepared_path),
        boundary_mask_path=str(boundary_path),
        filled_dem_path=str(filled_path),
        output_masked_dem_path=str(masked_path),
        output_breached_interior_path=str(breached_path),
        output_composite_dem_path=str(composite_path),
        collar_pixels=0,
        breach_runner=breach_runner,
    )

    composite = _read_raster(composite_path)
    assert artifacts.composite_dem_path == str(composite_path)
    assert composite[1, 1] == pytest.approx(3.0)
    assert composite[0, 0] == pytest.approx(5.0)


def test_phase2_create_bounded_breach_composite_rejects_dimension_mismatch(tmp_path: Path) -> None:
    filled_path = tmp_path / "filled.tif"
    breached_path = tmp_path / "breached.tif"
    boundary_path = tmp_path / "boundary.tif"
    output_path = tmp_path / "out.tif"

    _write_raster(filled_path, np.ones((3, 3), dtype=np.float32), nodata=-9999.0)
    _write_raster(breached_path, np.ones((4, 4), dtype=np.float32), nodata=-9999.0)
    _write_raster(boundary_path, np.ones((3, 3), dtype=np.uint8), nodata=0)

    with pytest.raises(ValueError, match="matching dimensions"):
        create_bounded_breach_composite(
            filled_dem_path=str(filled_path),
            breached_interior_path=str(breached_path),
            boundary_mask_path=str(boundary_path),
            output_composite_dem_path=str(output_path),
        )


def test_phase2_run_bounded_breach_workflow_rejects_non_callable_runner(tmp_path: Path) -> None:
    dem = np.ones((2, 2), dtype=np.float32)
    prepared_path = tmp_path / "prepared.tif"
    filled_path = tmp_path / "filled.tif"
    boundary_path = tmp_path / "boundary.tif"
    _write_raster(prepared_path, dem, nodata=-9999.0)
    _write_raster(filled_path, dem, nodata=-9999.0)
    _write_raster(boundary_path, np.ones((2, 2), dtype=np.uint8), nodata=0)

    with pytest.raises(TypeError, match="breach_runner must be callable"):
        run_bounded_breach_workflow(
            prepared_dem_path=str(prepared_path),
            boundary_mask_path=str(boundary_path),
            filled_dem_path=str(filled_path),
            output_masked_dem_path=str(tmp_path / "masked.tif"),
            output_breached_interior_path=str(tmp_path / "breached.tif"),
            output_composite_dem_path=str(tmp_path / "composite.tif"),
            collar_pixels=0,
            breach_runner="not-callable",  # type: ignore[arg-type]
        )


def test_phase2_run_bounded_breach_workflow_rejects_missing_breach_output(tmp_path: Path) -> None:
    dem = np.ones((2, 2), dtype=np.float32)
    prepared_path = tmp_path / "prepared.tif"
    filled_path = tmp_path / "filled.tif"
    boundary_path = tmp_path / "boundary.tif"
    _write_raster(prepared_path, dem, nodata=-9999.0)
    _write_raster(filled_path, dem, nodata=-9999.0)
    _write_raster(boundary_path, np.ones((2, 2), dtype=np.uint8), nodata=0)

    def breach_runner(masked_input: str, breached_output: str) -> None:
        _ = (masked_input, breached_output)

    with pytest.raises(FileNotFoundError, match="did not create interior breach output"):
        run_bounded_breach_workflow(
            prepared_dem_path=str(prepared_path),
            boundary_mask_path=str(boundary_path),
            filled_dem_path=str(filled_path),
            output_masked_dem_path=str(tmp_path / "masked.tif"),
            output_breached_interior_path=str(tmp_path / "breached.tif"),
            output_composite_dem_path=str(tmp_path / "composite.tif"),
            collar_pixels=0,
            breach_runner=breach_runner,
        )


def test_phase3_extract_road_stream_intersections_returns_deduped_points() -> None:
    roads = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"id": 1},
                "geometry": {"type": "LineString", "coordinates": [[0.0, 1.0], [2.0, 1.0]]},
            }
        ],
    }
    streams = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"id": 2},
                "geometry": {"type": "LineString", "coordinates": [[1.0, 0.0], [1.0, 2.0]]},
            }
        ],
    }

    intersections = extract_road_stream_intersections(roads, streams)
    assert len(intersections["features"]) == 1
    assert intersections["features"][0]["geometry"]["coordinates"] == [1.0, 1.0]


def test_phase3_load_culvert_points_rejects_non_point_geometry() -> None:
    bad = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {"type": "LineString", "coordinates": [[0, 0], [1, 1]]},
            }
        ],
    }

    with pytest.raises(GeometryInputError, match="Point/MultiPoint") as exc_info:
        load_culvert_points(bad)
    assert exc_info.value.code == "geometry_input_error"


def test_phase3_extract_road_stream_intersections_rejects_invalid_json_source(tmp_path: Path) -> None:
    bad_json = tmp_path / "bad.geojson"
    bad_json.write_text("{this is invalid json")
    valid = {
        "type": "FeatureCollection",
        "features": [],
    }

    with pytest.raises(GeometryInputError, match="not valid JSON") as exc_info:
        extract_road_stream_intersections(bad_json, valid)
    assert exc_info.value.code == "geometry_input_error"


def test_phase3_snap_uploaded_culvert_points_to_crossings_filters_by_distance() -> None:
    uploads = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"id": 10},
                "geometry": {"type": "Point", "coordinates": [0.2, 0.1]},
            },
            {
                "type": "Feature",
                "properties": {"id": 11},
                "geometry": {"type": "Point", "coordinates": [9.0, 9.0]},
            },
        ],
    }
    crossings = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"id": 1},
                "geometry": {"type": "Point", "coordinates": [0.0, 0.0]},
            }
        ],
    }

    snapped = snap_uploaded_culvert_points_to_crossings(
        uploaded_culvert_points=uploads,
        crossing_points=crossings,
        max_snap_distance_m=1.0,
    )

    assert len(snapped["features"]) == 1
    assert snapped["features"][0]["geometry"]["coordinates"] == [0.0, 0.0]


def test_phase3_snap_uploaded_culvert_points_to_crossings_raises_when_none_snap() -> None:
    uploads = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"id": 10},
                "geometry": {"type": "Point", "coordinates": [5.0, 5.0]},
            }
        ],
    }
    crossings = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"id": 1},
                "geometry": {"type": "Point", "coordinates": [0.0, 0.0]},
            }
        ],
    }

    with pytest.raises(CulvertSnapError, match="No uploaded") as exc_info:
        snap_uploaded_culvert_points_to_crossings(
            uploaded_culvert_points=uploads,
            crossing_points=crossings,
            max_snap_distance_m=1.0,
        )
    assert exc_info.value.code == "culvert_snap_error"


def test_phase3_snap_uploaded_culvert_points_to_crossings_rejects_invalid_max_distance() -> None:
    with pytest.raises(CulvertSnapError, match="max_snap_distance_m") as exc_info:
        snap_uploaded_culvert_points_to_crossings(
            uploaded_culvert_points={"type": "FeatureCollection", "features": []},
            crossing_points={"type": "FeatureCollection", "features": []},
            max_snap_distance_m=0.0,
        )
    assert exc_info.value.code == "culvert_snap_error"


def test_phase3_snap_uploaded_culvert_points_to_crossings_rejects_empty_crossings() -> None:
    uploads = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"id": 1},
                "geometry": {"type": "Point", "coordinates": [0.0, 0.0]},
            }
        ],
    }

    with pytest.raises(CulvertSnapError, match="contained no usable point features") as exc_info:
        snap_uploaded_culvert_points_to_crossings(
            uploaded_culvert_points=uploads,
            crossing_points={"type": "FeatureCollection", "features": []},
            max_snap_distance_m=1.0,
        )
    assert exc_info.value.code == "culvert_snap_error"


def test_phase3_burn_streams_at_roads_adapter_validates_and_calls_runner(tmp_path: Path) -> None:
    dem_path = tmp_path / "dem.tif"
    streams_path = tmp_path / "streams.geojson"
    roads_path = tmp_path / "roads.geojson"
    output_path = tmp_path / "burned.tif"

    dem_path.write_text("dem")
    streams_path.write_text("streams")
    roads_path.write_text("roads")

    called: dict[str, Any] = {}

    class Runner:
        def burn_streams_at_roads(self, **kwargs: Any) -> None:
            called.update(kwargs)
            Path(kwargs["output"]).write_text("ok")

    out = burn_streams_at_roads_adapter(
        wbt=Runner(),
        dem_path=str(dem_path),
        streams_path=str(streams_path),
        roads_path=str(roads_path),
        output_path=str(output_path),
        road_width_m=10.0,
    )

    assert out == str(output_path)
    assert called["dem"] == str(dem_path)
    assert called["width"] == 10.0


def test_phase3_burn_streams_at_roads_adapter_rejects_missing_inputs(tmp_path: Path) -> None:
    with pytest.raises(BurnStreamsAtRoadsValidationError, match="dem_path") as exc_info:
        burn_streams_at_roads_adapter(
            wbt=object(),
            dem_path=str(tmp_path / "missing_dem.tif"),
            streams_path=str(tmp_path / "streams.tif"),
            roads_path=str(tmp_path / "roads.tif"),
            output_path=str(tmp_path / "out.tif"),
            road_width_m=10.0,
        )
    assert exc_info.value.code == "burn_streams_at_roads_validation_error"


def test_phase3_burn_streams_at_roads_adapter_rejects_missing_runner_method(tmp_path: Path) -> None:
    dem_path = tmp_path / "dem.tif"
    streams_path = tmp_path / "streams.geojson"
    roads_path = tmp_path / "roads.geojson"
    dem_path.write_text("dem")
    streams_path.write_text("streams")
    roads_path.write_text("roads")

    with pytest.raises(BurnStreamsAtRoadsValidationError, match="does not expose") as exc_info:
        burn_streams_at_roads_adapter(
            wbt=object(),
            dem_path=str(dem_path),
            streams_path=str(streams_path),
            roads_path=str(roads_path),
            output_path=str(tmp_path / "out.tif"),
            road_width_m=10.0,
        )
    assert exc_info.value.code == "burn_streams_at_roads_validation_error"


def test_phase3_burn_streams_at_roads_adapter_requires_output_creation(tmp_path: Path) -> None:
    dem_path = tmp_path / "dem.tif"
    streams_path = tmp_path / "streams.geojson"
    roads_path = tmp_path / "roads.geojson"
    dem_path.write_text("dem")
    streams_path.write_text("streams")
    roads_path.write_text("roads")

    class Runner:
        def burn_streams_at_roads(self, **kwargs: Any) -> None:
            _ = kwargs

    with pytest.raises(
        BurnStreamsAtRoadsValidationError,
        match="did not create expected output",
    ) as exc_info:
        burn_streams_at_roads_adapter(
            wbt=Runner(),
            dem_path=str(dem_path),
            streams_path=str(streams_path),
            roads_path=str(roads_path),
            output_path=str(tmp_path / "out.tif"),
            road_width_m=10.0,
        )
    assert exc_info.value.code == "burn_streams_at_roads_validation_error"


def test_phase4_snap_outlets_to_streams_dedupes_and_builds_geojson() -> None:
    outlets = [(0.1, 0.2), (0.11, 0.19)]

    def snapper(x: float, y: float) -> tuple[float, float]:
        return (round(x, 1), round(y, 1))

    snapped = snap_outlets_to_streams(outlets, snapper=snapper, dedupe_round_precision=6)
    assert snapped == [(0.1, 0.2)]

    fc = build_outlet_feature_collection(snapped)
    assert fc["features"][0]["geometry"]["coordinates"] == [0.1, 0.2]


def test_phase4_parse_unnest_basins_hierarchy_csv_parses_parent_links(tmp_path: Path) -> None:
    csv_path = tmp_path / "hierarchy.csv"
    csv_path.write_text(
        "basin_id,parent_id,outlet_x,outlet_y,area,stream_order\n"
        "1,,100.0,200.0,10.5,3\n"
        "2,1,110.0,210.0,5.2,2\n"
    )

    parsed = parse_unnest_basins_hierarchy_csv(csv_path)
    assert parsed == [
        BasinSummary(
            basin_id=1,
            parent_basin_id=None,
            outlet_x=100.0,
            outlet_y=200.0,
            area=10.5,
            stream_order=3,
        ),
        BasinSummary(
            basin_id=2,
            parent_basin_id=1,
            outlet_x=110.0,
            outlet_y=210.0,
            area=5.2,
            stream_order=2,
        ),
    ]


def test_phase4_parse_unnest_basins_hierarchy_csv_supports_wbt_outlet_schema(tmp_path: Path) -> None:
    csv_path = tmp_path / "hierarchy.csv"
    csv_path.write_text(
        "outlet_id,parent_outlet_id,row,column\n"
        "1,0,100,200\n"
        "2,1,110,210\n"
    )

    parsed = parse_unnest_basins_hierarchy_csv(csv_path)
    assert parsed == [
        BasinSummary(
            basin_id=1,
            parent_basin_id=None,
            outlet_x=200.0,
            outlet_y=100.0,
            area=None,
            stream_order=None,
        ),
        BasinSummary(
            basin_id=2,
            parent_basin_id=1,
            outlet_x=210.0,
            outlet_y=110.0,
            area=None,
            stream_order=None,
        ),
    ]


def test_phase4_parse_unnest_basins_hierarchy_csv_rejects_orphans(tmp_path: Path) -> None:
    csv_path = tmp_path / "hierarchy.csv"
    csv_path.write_text(
        "basin_id,parent_id,outlet_x,outlet_y\n"
        "2,99,110.0,210.0\n"
    )

    with pytest.raises(ValueError, match="unknown parent basin"):
        parse_unnest_basins_hierarchy_csv(csv_path)


def test_phase4_parse_unnest_basins_hierarchy_csv_rejects_duplicate_ids(tmp_path: Path) -> None:
    csv_path = tmp_path / "hierarchy.csv"
    csv_path.write_text(
        "basin_id,parent_id,outlet_x,outlet_y\n"
        "2,,110.0,210.0\n"
        "2,,111.0,211.0\n"
    )

    with pytest.raises(ValueError, match="duplicate basin_id"):
        parse_unnest_basins_hierarchy_csv(csv_path)


def test_phase4_parse_unnest_basins_hierarchy_csv_rejects_missing_columns(tmp_path: Path) -> None:
    csv_path = tmp_path / "hierarchy.csv"
    csv_path.write_text(
        "basin_id,parent_id,outlet_x\n"
        "2,1,110.0\n"
    )

    with pytest.raises(ValueError, match="required column 'outlet_y'"):
        parse_unnest_basins_hierarchy_csv(csv_path)


def test_phase4_parse_unnest_basins_hierarchy_csv_rejects_negative_stream_order(tmp_path: Path) -> None:
    csv_path = tmp_path / "hierarchy.csv"
    csv_path.write_text(
        "basin_id,parent_id,outlet_x,outlet_y,stream_order\n"
        "1,,100.0,200.0,-2\n"
    )

    with pytest.raises(ValueError, match="stream_order cannot be negative"):
        parse_unnest_basins_hierarchy_csv(csv_path)


def test_phase4_parse_unnest_basins_hierarchy_csv_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="does not exist"):
        parse_unnest_basins_hierarchy_csv(tmp_path / "missing.csv")


def test_phase5_provenance_entry_to_dict_and_registry_roundtrip() -> None:
    entry = ProvenanceEntry(
        step="burn_culverts",
        artifact="relief_burned.tif",
        parameters={"width": 10.0},
        metadata={"culvert_count": 12},
    )

    record = entry.to_dict()
    assert record == {
        "step": "burn_culverts",
        "artifact": "relief_burned.tif",
        "parameters": {"width": 10.0},
        "metadata": {"culvert_count": 12},
    }

    registry = TerrainArtifactRegistry()
    registry.register(
        phase="phase2_bounded_breach",
        artifact_name="composite_dem",
        artifact_path="/tmp/composite_dem.tif",
    )
    assert registry.phase_artifacts("phase2_bounded_breach") == {
        "composite_dem": "/tmp/composite_dem.tif"
    }


def test_phase5_determine_invalidated_phases_applies_rule_mapping() -> None:
    invalidated = determine_invalidated_phases(
        changed_config_keys=["culvert_method", "outlet_mode"],
    )

    assert invalidated == [
        "phase3_culvert_enforcement",
        "phase4_multi_outlet",
        "phase5_provenance",
    ]


def test_phase5_determine_invalidated_phases_includes_phase1_for_flow_stack_inputs() -> None:
    invalidated = determine_invalidated_phases(changed_config_keys=["csa"])
    assert invalidated == [
        "phase1_flow_stack",
        "phase2_bounded_breach",
        "phase3_culvert_enforcement",
        "phase4_multi_outlet",
        "phase5_provenance",
    ]


def test_phase5_determine_invalidated_phases_falls_back_to_all_on_unknown_key() -> None:
    invalidated = determine_invalidated_phases(changed_config_keys=["new_unknown_key"])
    assert invalidated == [
        "phase1_flow_stack",
        "phase2_bounded_breach",
        "phase3_culvert_enforcement",
        "phase4_multi_outlet",
        "phase5_provenance",
    ]


def test_phase5_determine_invalidated_phases_accepts_explicit_empty_rules() -> None:
    invalidated = determine_invalidated_phases(
        changed_config_keys=["culvert_method"],
        invalidation_rules={},
    )
    assert invalidated == [
        "phase1_flow_stack",
        "phase2_bounded_breach",
        "phase3_culvert_enforcement",
        "phase4_multi_outlet",
        "phase5_provenance",
    ]
