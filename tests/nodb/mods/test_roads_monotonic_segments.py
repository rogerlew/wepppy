from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("rasterio")
import rasterio
from rasterio.transform import from_origin

from wepppy.nodb.mods.roads import convert_geojson_file_to_monotonic_segments

pytestmark = [pytest.mark.unit, pytest.mark.nodb]


def _write_dem(tmp_path: Path, values: list[float]) -> Path:
    dem_path = tmp_path / "dem.tif"
    array = np.asarray(values, dtype=np.float32)[np.newaxis, :]
    with rasterio.open(
        dem_path,
        "w",
        driver="GTiff",
        height=1,
        width=array.shape[1],
        count=1,
        dtype="float32",
        crs="EPSG:32610",
        transform=from_origin(0.0, 1.0, 1.0, 1.0),
        nodata=-9999.0,
    ) as dataset:
        dataset.write(array, 1)
    return dem_path


def _write_dem_grid(tmp_path: Path, values: list[list[float]]) -> Path:
    dem_path = tmp_path / "dem.tif"
    array = np.asarray(values, dtype=np.float32)
    assert array.ndim == 2
    with rasterio.open(
        dem_path,
        "w",
        driver="GTiff",
        height=array.shape[0],
        width=array.shape[1],
        count=1,
        dtype="float32",
        crs="EPSG:32610",
        transform=from_origin(0.0, float(array.shape[0]), 1.0, 1.0),
        nodata=-9999.0,
    ) as dataset:
        dataset.write(array, 1)
    return dem_path


def _write_line_geojson(tmp_path: Path, line_coords: list[list[float]], properties: dict[str, object]) -> Path:
    roads_path = tmp_path / "roads.geojson"
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": line_coords},
                "properties": properties,
            }
        ],
    }
    roads_path.write_text(json.dumps(payload), encoding="utf-8")
    return roads_path


def _write_channel_topaz_rasters(
    tmp_path: Path, channel_values: list[float] | list[list[float]], topaz_values: list[float] | list[list[float]]
) -> tuple[Path, Path]:
    channel_path = tmp_path / "channel.tif"
    topaz_path = tmp_path / "subwta.tif"

    channel_array = np.asarray(channel_values, dtype=np.float32)
    if channel_array.ndim == 1:
        channel_array = channel_array[np.newaxis, :]
    assert channel_array.ndim == 2
    with rasterio.open(
        channel_path,
        "w",
        driver="GTiff",
        height=channel_array.shape[0],
        width=channel_array.shape[1],
        count=1,
        dtype="float32",
        crs="EPSG:32610",
        transform=from_origin(0.0, float(channel_array.shape[0]), 1.0, 1.0),
        nodata=0.0,
    ) as dataset:
        dataset.write(channel_array, 1)

    topaz_array = np.asarray(topaz_values, dtype=np.float32)
    if topaz_array.ndim == 1:
        topaz_array = topaz_array[np.newaxis, :]
    assert topaz_array.shape == channel_array.shape
    with rasterio.open(
        topaz_path,
        "w",
        driver="GTiff",
        height=topaz_array.shape[0],
        width=topaz_array.shape[1],
        count=1,
        dtype="float32",
        crs="EPSG:32610",
        transform=from_origin(0.0, float(topaz_array.shape[0]), 1.0, 1.0),
        nodata=-9999.0,
    ) as dataset:
        dataset.write(topaz_array, 1)

    return channel_path, topaz_path


def test_converter_splits_non_monotonic_line_and_preserves_properties(tmp_path: Path) -> None:
    dem_path = _write_dem(tmp_path, [0.0, 1.0, 2.0, 1.0, 0.0])
    roads_path = _write_line_geojson(
        tmp_path,
        line_coords=[[0.5, 0.5], [4.5, 0.5]],
        properties={"road_id": "A1", "surface": "gravel"},
    )
    output_path = tmp_path / "roads.monotonic.geojson"

    summary = convert_geojson_file_to_monotonic_segments(
        input_geojson_path=roads_path,
        dem_path=dem_path,
        output_geojson_path=output_path,
        input_crs="EPSG:32610",
        sample_step_m=1.0,
        tolerance_m=0.0,
    )

    output = json.loads(output_path.read_text(encoding="utf-8"))
    features = output["features"]

    assert summary.input_feature_count == 1
    assert summary.output_feature_count == 2
    assert summary.split_feature_count == 1
    assert summary.low_point_feature_count == 2
    assert len(features) == 2
    for feature in features:
        props = feature["properties"]
        assert props["road_id"] == "A1"
        assert props["surface"] == "gravel"
        assert isinstance(props["segment_id"], str)
        assert props["segment_id"].startswith("roads-seg-")
        assert "_roads_low_point_x" in props
        assert "_roads_low_point_y" in props
        assert "_roads_low_point_elevation_m" in props
        assert props["topaz_id_chn_lowpoint"] is None
        assert props["topaz_id_hill_lowpoint"] is None

    first_coords = features[0]["geometry"]["coordinates"]
    second_coords = features[1]["geometry"]["coordinates"]
    assert first_coords[0] == pytest.approx([0.5, 0.5])
    assert first_coords[-1] == pytest.approx([2.5, 0.5])
    assert second_coords[0] == pytest.approx([2.5, 0.5])
    assert second_coords[-1] == pytest.approx([4.5, 0.5])


@pytest.mark.parametrize(
    ("tolerance_m", "expected_output_features"),
    [
        (0.0, 2),
        (0.1, 1),
    ],
)
def test_converter_tolerance_controls_split_count(
    tmp_path: Path, tolerance_m: float, expected_output_features: int
) -> None:
    dem_path = _write_dem(tmp_path, [10.0, 10.05, 10.02])
    roads_path = _write_line_geojson(
        tmp_path,
        line_coords=[[0.5, 0.5], [2.5, 0.5]],
        properties={"road_id": "B1"},
    )
    output_path = tmp_path / f"roads.monotonic.tol-{tolerance_m}.geojson"

    summary = convert_geojson_file_to_monotonic_segments(
        input_geojson_path=roads_path,
        dem_path=dem_path,
        output_geojson_path=output_path,
        input_crs="EPSG:32610",
        sample_step_m=1.0,
        tolerance_m=tolerance_m,
    )

    output = json.loads(output_path.read_text(encoding="utf-8"))
    assert len(output["features"]) == expected_output_features
    assert summary.output_feature_count == expected_output_features
    assert summary.low_point_feature_count == expected_output_features


def test_converter_trims_edge_nodata_samples(tmp_path: Path) -> None:
    dem_path = _write_dem(tmp_path, [-9999.0, 1.0, 2.0, 1.0])
    roads_path = _write_line_geojson(
        tmp_path,
        line_coords=[[0.5, 0.5], [3.5, 0.5]],
        properties={"road_id": "C1"},
    )
    output_path = tmp_path / "roads.monotonic.nodata.geojson"

    summary = convert_geojson_file_to_monotonic_segments(
        input_geojson_path=roads_path,
        dem_path=dem_path,
        output_geojson_path=output_path,
        input_crs="EPSG:32610",
        sample_step_m=1.0,
        tolerance_m=0.0,
    )

    output = json.loads(output_path.read_text(encoding="utf-8"))
    features = output["features"]

    assert summary.output_feature_count == 2
    assert summary.low_point_feature_count == 2
    assert len(features) == 2
    assert features[0]["geometry"]["coordinates"][0] == pytest.approx([1.5, 0.5])


def test_converter_writes_low_point_feature_collection(tmp_path: Path) -> None:
    dem_path = _write_dem(tmp_path, [0.0, 1.0, 2.0, 1.0, 0.0])
    roads_path = _write_line_geojson(
        tmp_path,
        line_coords=[[0.5, 0.5], [4.5, 0.5]],
        properties={"road_id": "D1"},
    )
    output_path = tmp_path / "roads.monotonic.geojson"
    low_points_output_path = tmp_path / "roads.low_points.geojson"

    summary = convert_geojson_file_to_monotonic_segments(
        input_geojson_path=roads_path,
        dem_path=dem_path,
        output_geojson_path=output_path,
        low_points_output_geojson_path=low_points_output_path,
        input_crs="EPSG:32610",
        sample_step_m=1.0,
        tolerance_m=0.0,
    )

    low_points = json.loads(low_points_output_path.read_text(encoding="utf-8"))
    features = low_points["features"]

    assert summary.low_point_feature_count == 2
    assert len(features) == 2
    assert all(feature["geometry"]["type"] == "Point" for feature in features)
    assert all(feature["properties"]["_roads_feature_type"] == "segment_low_point" for feature in features)
    assert all(feature["properties"]["segment_id"].startswith("roads-seg-") for feature in features)


def test_inslope_segments_get_channel_topaz_id_at_low_point_or_neighbor(tmp_path: Path) -> None:
    dem_path = _write_dem(tmp_path, [0.0, 1.0, 2.0, 1.0, 0.0])
    channel_path, topaz_path = _write_channel_topaz_rasters(
        tmp_path,
        channel_values=[0.0, 0.0, 0.0, 1.0, 0.0],
        topaz_values=[11.0, 12.0, 13.0, 24.0, 15.0],
    )
    roads_path = _write_line_geojson(
        tmp_path,
        line_coords=[[0.5, 0.5], [4.5, 0.5]],
        properties={"road_id": "E1", "DESIGN": "Inslope_bd"},
    )
    output_path = tmp_path / "roads.monotonic.geojson"

    summary = convert_geojson_file_to_monotonic_segments(
        input_geojson_path=roads_path,
        dem_path=dem_path,
        output_geojson_path=output_path,
        input_crs="EPSG:32610",
        sample_step_m=1.0,
        tolerance_m=0.0,
        channel_raster_path=channel_path,
        topaz_id_raster_path=topaz_path,
    )

    output = json.loads(output_path.read_text(encoding="utf-8"))
    values = [feature["properties"]["topaz_id_chn_lowpoint"] for feature in output["features"]]
    hill_values = [feature["properties"]["topaz_id_hill_lowpoint"] for feature in output["features"]]
    decisions = [feature["properties"]["_roads_lowpoint_decision"] for feature in output["features"]]

    assert summary.output_feature_count == 2
    assert values.count(24) == 1
    assert values.count(None) == 1
    assert hill_values.count(None) == 2
    assert decisions.count("no_channel_pixel_near_lowpoint") == 1
    assert decisions.count("no_receiving_hillslope_candidate_near_lowpoint") == 1


def test_inslope_rd_segments_get_channel_and_hillslope_lowpoint_ids(tmp_path: Path) -> None:
    dem_path = _write_dem(tmp_path, [0.0, 1.0, 2.0, 1.0, 0.0])
    channel_path, topaz_path = _write_channel_topaz_rasters(
        tmp_path,
        channel_values=[0.0, 0.0, 0.0, 1.0, 0.0],
        topaz_values=[11.0, 12.0, 13.0, 24.0, 21.0],
    )
    roads_path = _write_line_geojson(
        tmp_path,
        line_coords=[[0.5, 0.5], [4.5, 0.5]],
        properties={"road_id": "E2", "DESIGN": "Inslope_rd"},
    )
    output_path = tmp_path / "roads.monotonic.geojson"

    convert_geojson_file_to_monotonic_segments(
        input_geojson_path=roads_path,
        dem_path=dem_path,
        output_geojson_path=output_path,
        input_crs="EPSG:32610",
        sample_step_m=1.0,
        tolerance_m=0.0,
        channel_raster_path=channel_path,
        topaz_id_raster_path=topaz_path,
    )

    output = json.loads(output_path.read_text(encoding="utf-8"))
    rows = [feature["properties"] for feature in output["features"]]
    by_segment = {row["segment_id"]: row for row in rows}

    assert len(by_segment) == 2
    assert sum(1 for row in rows if row["topaz_id_chn_lowpoint"] == 24) == 1
    assert sum(1 for row in rows if row["topaz_id_hill_lowpoint"] == 21) == 1
    assert sum(1 for row in rows if row["_roads_lowpoint_decision"] == "mapped") == 1
    assert all("_roads_channel_search_rank" in row for row in rows)
    assert all("_roads_channel_lookup_available" in row for row in rows)
    assert all(
        row["topaz_id_hill_lowpoint"] is None or str(row["topaz_id_hill_lowpoint"]).endswith(("1", "2", "3"))
        for row in rows
    )


def test_custom_design_property_keys_control_inslope_eligibility(tmp_path: Path) -> None:
    dem_path = _write_dem(tmp_path, [0.0, 1.0, 2.0, 1.0, 0.0])
    channel_path, topaz_path = _write_channel_topaz_rasters(
        tmp_path,
        channel_values=[0.0, 0.0, 0.0, 1.0, 0.0],
        topaz_values=[11.0, 12.0, 13.0, 24.0, 21.0],
    )
    roads_path = _write_line_geojson(
        tmp_path,
        line_coords=[[0.5, 0.5], [4.5, 0.5]],
        properties={"road_id": "E3", "ROADTYPE": "Inslope_bd"},
    )
    output_path = tmp_path / "roads.monotonic.geojson"

    convert_geojson_file_to_monotonic_segments(
        input_geojson_path=roads_path,
        dem_path=dem_path,
        output_geojson_path=output_path,
        input_crs="EPSG:32610",
        sample_step_m=1.0,
        tolerance_m=0.0,
        channel_raster_path=channel_path,
        topaz_id_raster_path=topaz_path,
        design_property_keys=("ROADTYPE", "DESIGN", "design"),
    )

    output = json.loads(output_path.read_text(encoding="utf-8"))
    rows = [feature["properties"] for feature in output["features"]]

    assert any(row.get("topaz_id_chn_lowpoint") == 24 for row in rows)
    assert any(row.get("topaz_id_hill_lowpoint") == 21 for row in rows)
    assert any(row.get("_roads_design_source_key") == "ROADTYPE" for row in rows)


def test_hillslope_lowpoint_tie_break_prefers_center_then_right_then_left(tmp_path: Path) -> None:
    dem_path = _write_dem_grid(
        tmp_path,
        [
            [2.0, 2.0, 2.0],
            [2.0, 0.0, 2.0],
            [2.0, 2.0, 2.0],
        ],
    )
    channel_path, topaz_path = _write_channel_topaz_rasters(
        tmp_path,
        channel_values=[
            [0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0],
        ],
        topaz_values=[
            [0.0, 21.0, 0.0],
            [23.0, 24.0, 22.0],
            [0.0, 0.0, 0.0],
        ],
    )
    roads_path = _write_line_geojson(
        tmp_path,
        line_coords=[[0.5, 1.5], [2.5, 1.5]],
        properties={"road_id": "E3", "DESIGN": "Inslope_bd"},
    )
    output_path = tmp_path / "roads.monotonic.geojson"

    convert_geojson_file_to_monotonic_segments(
        input_geojson_path=roads_path,
        dem_path=dem_path,
        output_geojson_path=output_path,
        input_crs="EPSG:32610",
        sample_step_m=1.0,
        tolerance_m=0.0,
        channel_raster_path=channel_path,
        topaz_id_raster_path=topaz_path,
    )

    output = json.loads(output_path.read_text(encoding="utf-8"))
    hillslope_ids = [feature["properties"]["topaz_id_hill_lowpoint"] for feature in output["features"]]
    chn_ids = [feature["properties"]["topaz_id_chn_lowpoint"] for feature in output["features"]]
    decisions = [feature["properties"]["_roads_lowpoint_decision"] for feature in output["features"]]

    assert all(value == 24 for value in chn_ids)
    assert all(value == 21 for value in hillslope_ids)
    assert all(value == "mapped" for value in decisions)
