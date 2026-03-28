from __future__ import annotations

import io
import json
from pathlib import Path
import sqlite3
import zipfile

import pandas as pd
import pytest

from wepppy.nodb.mods.features_export.catalog_loader import load_layer_catalog
from wepppy.nodb.mods.features_export.contracts import (
    ExportWarning,
    NormalizedExportRequest,
    NormalizedTabularRequest,
    ResolvedExportPlan,
    ResolvedLayerPlan,
)
from wepppy.nodb.mods.features_export.exporters import (
    ExportBackendCapabilityError,
    ExportWriterRequest,
    FeaturesExportWriterError,
    GeodatabaseExportWriter,
    GeoJsonExportWriter,
    GeopackageExportWriter,
    GeoparquetExportWriter,
    KmzExportWriter,
    PreparedLayerPayload,
    deterministic_layer_filename,
    get_export_writer,
)
from wepppy.nodb.mods.features_export.planner import resolve_export_plan

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def catalog():
    return load_layer_catalog()


def _resolved_plan(catalog, format_token: str = "geoparquet"):
    return resolve_export_plan(
        {
            "format": format_token,
            "units": "si",
            "layers": [
                "wepp.summary.hillslopes",
                "watershed.channels",
            ],
            "output_scopes": ["roads", "baseline"],
        },
        catalog,
    )


def _layer_payloads_for_plan(plan) -> dict[str, PreparedLayerPayload]:
    payloads: dict[str, PreparedLayerPayload] = {}
    for idx, layer in enumerate(plan.layers):
        payloads[layer.output_layer_id] = PreparedLayerPayload(
            output_layer_id=layer.output_layer_id,
            payload=f"payload::{layer.output_layer_id}",
            row_count=10 + idx,
            feature_count=100 + idx,
            warnings=(
                ExportWarning(
                    code="unit_pass_through",
                    message=f"unit passthrough for {layer.output_layer_id}",
                    layer_id=layer.layer_id,
                    scope=layer.scope,
                ),
            ),
        )
    return payloads


def test_get_export_writer_dispatches_supported_formats_and_aliases() -> None:
    assert isinstance(get_export_writer("geojson"), GeoJsonExportWriter)
    assert isinstance(get_export_writer("geoparquet"), GeoparquetExportWriter)
    assert isinstance(get_export_writer("kmz"), KmzExportWriter)
    assert isinstance(get_export_writer("geopackage"), GeopackageExportWriter)
    assert isinstance(get_export_writer("geodatabase"), GeodatabaseExportWriter)
    assert isinstance(get_export_writer("f_esri"), GeodatabaseExportWriter)

    with pytest.raises(FeaturesExportWriterError, match="Unsupported export format"):
        get_export_writer("shapezip")


@pytest.mark.parametrize(
    "format_token,expected_extension",
    [
        ("geojson", ".geojson"),
        ("geoparquet", ".parquet"),
        ("kmz", ".kmz"),
    ],
)
def test_single_layer_formats_package_one_file_per_resolved_layer(
    tmp_path: Path,
    catalog,
    format_token: str,
    expected_extension: str,
) -> None:
    plan = _resolved_plan(catalog, format_token)
    request = ExportWriterRequest(
        plan=plan,
        layer_payloads=_layer_payloads_for_plan(plan),
        artifact_dir=tmp_path,
        artifact_basename="features_export",
    )

    writer = get_export_writer(format_token)
    artifact = writer.write(request)

    expected_members = tuple(
        deterministic_layer_filename(layer.output_layer_id, expected_extension)
        for layer in sorted(plan.layers, key=lambda item: item.output_layer_id)
    )

    assert artifact.artifact_relpath == f"features_export.{format_token}.zip"
    assert artifact.packaged_member_relpaths == expected_members
    assert len(artifact.layer_outputs) == len(plan.layers)

    with zipfile.ZipFile(artifact.artifact_path, "r") as zip_handle:
        assert tuple(sorted(zip_handle.namelist())) == expected_members
        for member in expected_members:
            output_layer_id = member[: -len(expected_extension)]
            assert zip_handle.read(member).decode("utf-8") == f"payload::{output_layer_id}"


def test_output_layer_filename_is_deterministic() -> None:
    assert (
        deterministic_layer_filename("baseline__wepp.summary.hillslopes", ".geojson")
        == "baseline__wepp.summary.hillslopes.geojson"
    )


def test_geopackage_writer_emits_single_multilayer_container(tmp_path: Path, catalog) -> None:
    plan = _resolved_plan(catalog, "geopackage")
    request = ExportWriterRequest(
        plan=plan,
        layer_payloads=_layer_payloads_for_plan(plan),
        artifact_dir=tmp_path,
        artifact_basename="features_export",
    )

    writer = get_export_writer("geopackage")
    artifact = writer.write(request)

    assert artifact.artifact_relpath == "features_export.gpkg"
    assert Path(artifact.artifact_path).exists()
    assert artifact.packaged_member_relpaths == ("features_export.gpkg",)
    assert len({entry.relpath for entry in artifact.layer_outputs}) == 1

    with sqlite3.connect(artifact.artifact_path) as conn:
        contents_rows = conn.execute(
            "SELECT identifier, data_type FROM gpkg_contents ORDER BY identifier"
        ).fetchall()

    assert [row[0] for row in contents_rows] == [
        layer.output_layer_id for layer in sorted(plan.layers, key=lambda item: item.output_layer_id)
    ]
    assert {row[1] for row in contents_rows} == {"attributes"}

    ogr_module = pytest.importorskip("osgeo.ogr")
    dataset = ogr_module.Open(artifact.artifact_path)
    assert dataset is not None
    assert dataset.GetLayerCount() == len(plan.layers)


def test_geopackage_writer_materializes_feature_collection_payloads(tmp_path: Path, catalog) -> None:
    plan = _resolved_plan(catalog, "geopackage")
    plan_layers = sorted(plan.layers, key=lambda item: item.output_layer_id)
    first_layer = plan_layers[0]
    second_layer = plan_layers[1]

    feature_payload = {
        "schema": "wepppy.features_export.feature_collection.v1",
        "layer_id": first_layer.layer_id,
        "output_layer_id": first_layer.output_layer_id,
        "scope": first_layer.scope,
        "scope_class": first_layer.scope_class,
        "crs_epsg": 4326,
        "feature_collection": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"TopazID": 1, "label": "alpha"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
                    },
                }
            ],
        },
    }

    payloads: dict[str, PreparedLayerPayload] = {}
    for layer in plan_layers:
        if layer.output_layer_id == first_layer.output_layer_id:
            payloads[layer.output_layer_id] = PreparedLayerPayload(
                output_layer_id=layer.output_layer_id,
                payload=json.dumps(feature_payload, sort_keys=True, separators=(",", ":")),
                row_count=1,
                feature_count=1,
            )
            continue

        payloads[layer.output_layer_id] = PreparedLayerPayload(
            output_layer_id=layer.output_layer_id,
            payload=f"payload::{layer.output_layer_id}",
            row_count=1,
            feature_count=1,
        )

    request = ExportWriterRequest(
        plan=plan,
        layer_payloads=payloads,
        artifact_dir=tmp_path,
        artifact_basename="features_export",
    )

    writer = get_export_writer("geopackage")
    artifact = writer.write(request)

    with sqlite3.connect(artifact.artifact_path) as conn:
        rows = conn.execute(
            "SELECT identifier, table_name, data_type FROM gpkg_contents ORDER BY identifier"
        ).fetchall()

        row_by_identifier = {row[0]: row for row in rows}
        assert row_by_identifier[first_layer.output_layer_id][2] == "features"
        assert row_by_identifier[second_layer.output_layer_id][2] == "attributes"

        spatial_table = row_by_identifier[first_layer.output_layer_id][1]
        geom_count = conn.execute(
            f'SELECT COUNT(*) FROM "{spatial_table}" WHERE geom IS NOT NULL'
        ).fetchone()[0]
        assert geom_count == 1


def test_geopackage_writer_keeps_null_only_property_columns(tmp_path: Path, catalog) -> None:
    plan = _resolved_plan(catalog, "geopackage")
    plan_layers = sorted(plan.layers, key=lambda item: item.output_layer_id)
    first_layer = plan_layers[0]

    feature_payload = {
        "schema": "wepppy.features_export.feature_collection.v1",
        "layer_id": first_layer.layer_id,
        "output_layer_id": first_layer.output_layer_id,
        "scope": first_layer.scope,
        "scope_class": first_layer.scope_class,
        "crs_epsg": 4326,
        "feature_collection": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"nullable_only": None, "count": 1},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
                    },
                }
            ],
        },
    }

    payloads: dict[str, PreparedLayerPayload] = {}
    for layer in plan_layers:
        if layer.output_layer_id == first_layer.output_layer_id:
            payloads[layer.output_layer_id] = PreparedLayerPayload(
                output_layer_id=layer.output_layer_id,
                payload=json.dumps(feature_payload, sort_keys=True, separators=(",", ":")),
                row_count=1,
                feature_count=1,
            )
            continue

        payloads[layer.output_layer_id] = PreparedLayerPayload(
            output_layer_id=layer.output_layer_id,
            payload=f"payload::{layer.output_layer_id}",
            row_count=1,
            feature_count=1,
        )

    request = ExportWriterRequest(
        plan=plan,
        layer_payloads=payloads,
        artifact_dir=tmp_path,
        artifact_basename="features_export",
    )

    writer = get_export_writer("geopackage")
    artifact = writer.write(request)

    with sqlite3.connect(artifact.artifact_path) as conn:
        row = conn.execute(
            "SELECT table_name FROM gpkg_contents WHERE identifier = ?",
            (first_layer.output_layer_id,),
        ).fetchone()
        assert row is not None
        table_name = row[0]
        table_info = conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
        column_types = {entry[1]: str(entry[2]).upper() for entry in table_info}

    assert "nullable_only" in column_types
    assert "INT" in column_types["count"]


def test_geodatabase_writer_uses_f_esri_conversion_boundary(tmp_path: Path, catalog) -> None:
    plan = _resolved_plan(catalog, "geodatabase")
    request = ExportWriterRequest(
        plan=plan,
        layer_payloads=_layer_payloads_for_plan(plan),
        artifact_dir=tmp_path,
        artifact_basename="features_export",
    )

    calls: list[tuple[str, str]] = []

    def converter(gpkg_path: str, gdb_path: str) -> str:
        calls.append((gpkg_path, gdb_path))
        assert gpkg_path.endswith("features_export.geodatabase_source.gpkg")
        assert Path(gpkg_path).read_bytes().startswith(b"SQLite format 3\x00")
        ogr_module = pytest.importorskip("osgeo.ogr")
        dataset = ogr_module.Open(gpkg_path)
        assert dataset is not None
        assert dataset.GetLayerCount() == len(plan.layers)
        gdb_dir = Path(gdb_path)
        gdb_dir.mkdir(parents=True, exist_ok=True)
        (gdb_dir / "a.gdbtable").write_text("stub", encoding="utf-8")
        zip_path = gdb_dir.with_suffix(".gdb.zip")
        zip_path.write_bytes(b"zip")
        return str(gdb_dir)

    writer = GeodatabaseExportWriter(
        backend_available=lambda: True,
        gpkg_to_gdb_converter=converter,
    )
    artifact = writer.write(request)

    assert len(calls) == 1
    assert artifact.artifact_relpath == "features_export.gdb.zip"
    assert Path(artifact.artifact_path).exists()
    assert artifact.packaged_member_relpaths == ("features_export.gdb.zip",)
    assert all(output.relpath == "features_export.gdb.zip" for output in artifact.layer_outputs)


def test_geodatabase_writer_fails_explicitly_when_backend_unavailable(
    tmp_path: Path,
    catalog,
) -> None:
    plan = _resolved_plan(catalog, "geodatabase")
    request = ExportWriterRequest(
        plan=plan,
        layer_payloads=_layer_payloads_for_plan(plan),
        artifact_dir=tmp_path,
        artifact_basename="features_export",
    )

    writer = GeodatabaseExportWriter(backend_available=lambda: False)
    with pytest.raises(ExportBackendCapabilityError, match="f_esri backend capability"):
        writer.write(request)


@pytest.mark.parametrize(
    "format_token,expected_extension",
    [
        ("parquet", ".parquet"),
        ("csv", ".csv"),
    ],
)
def test_geometryless_formats_drop_geometry_and_keep_properties(
    tmp_path: Path,
    catalog,
    format_token: str,
    expected_extension: str,
) -> None:
    plan = resolve_export_plan(
        {
            "format": format_token,
            "units": "si",
            "layers": ["watershed.subcatchments"],
        },
        catalog,
    )
    layer = plan.layers[0]
    tabular_frame = pd.DataFrame(
        [
            {"TopazID": 1, "Name": "A"},
            {"TopazID": 2, "Name": "B"},
        ]
    )
    request = ExportWriterRequest(
        plan=plan,
        layer_payloads={
            layer.output_layer_id: PreparedLayerPayload(
                output_layer_id=layer.output_layer_id,
                payload=b"",
                tabular_frame=tabular_frame,
                row_count=2,
                feature_count=2,
            )
        },
        artifact_dir=tmp_path,
        artifact_basename="features_export",
    )

    artifact = get_export_writer(format_token).write(request)
    expected_member = f"{layer.output_layer_id}{expected_extension}"
    assert artifact.packaged_member_relpaths == (expected_member,)

    with zipfile.ZipFile(artifact.artifact_path, "r") as zip_handle:
        member_bytes = zip_handle.read(expected_member)

    if format_token == "parquet":
        frame = pd.read_parquet(io.BytesIO(member_bytes))
    else:
        frame = pd.read_csv(io.BytesIO(member_bytes))

    assert "TopazID" in frame.columns
    assert "Name" in frame.columns
    assert "geometry" not in frame.columns
    assert frame["TopazID"].tolist() == [1, 2]


@pytest.mark.parametrize("format_token", ["parquet", "csv"])
def test_geometryless_formats_require_tabular_frame_payload(
    tmp_path: Path,
    catalog,
    format_token: str,
) -> None:
    plan = resolve_export_plan(
        {
            "format": format_token,
            "units": "si",
            "layers": ["watershed.subcatchments"],
        },
        catalog,
    )
    layer = plan.layers[0]
    request = ExportWriterRequest(
        plan=plan,
        layer_payloads={
            layer.output_layer_id: PreparedLayerPayload(
                output_layer_id=layer.output_layer_id,
                payload="legacy-feature-collection-json",
                row_count=1,
                feature_count=1,
            )
        },
        artifact_dir=tmp_path,
        artifact_basename="features_export",
    )

    with pytest.raises(FeaturesExportWriterError, match="tabular_frame"):
        get_export_writer(format_token).write(request)


@pytest.mark.parametrize(
    "format_token,member_name",
    [
        ("parquet", "hillslopes.parquet"),
        ("csv", "hillslopes.csv"),
    ],
)
def test_tabular_concatenate_tables_merges_hillslope_layers_with_provenance_columns(
    tmp_path: Path,
    catalog,
    format_token: str,
    member_name: str,
) -> None:
    plan = resolve_export_plan(
        {
            "format": format_token,
            "units": "project",
            "layers": [
                "wepp.summary.hillslopes",
                "wepp.interchange.hill_wat",
            ],
            "tabular": {
                "concatenate_tables": True,
                "temporal_layout": "wide",
            },
        },
        catalog,
    )
    layer_pairs = sorted(plan.layers, key=lambda item: item.output_layer_id)
    payloads: dict[str, PreparedLayerPayload] = {}
    for idx, layer in enumerate(layer_pairs):
        payloads[layer.output_layer_id] = PreparedLayerPayload(
            output_layer_id=layer.output_layer_id,
            payload=b"",
            tabular_frame=pd.DataFrame(
                [
                    {"topaz_id": idx + 1, "metric": float(idx + 10)},
                ]
            ),
            row_count=1,
            feature_count=1,
        )

    request = ExportWriterRequest(
        plan=plan,
        layer_payloads=payloads,
        artifact_dir=tmp_path,
        artifact_basename="features_export",
    )
    artifact = get_export_writer(format_token).write(request)

    assert member_name in artifact.packaged_member_relpaths

    with zipfile.ZipFile(artifact.artifact_path, "r") as zip_handle:
        member_bytes = zip_handle.read(member_name)

    if format_token == "parquet":
        frame = pd.read_parquet(io.BytesIO(member_bytes))
    else:
        frame = pd.read_csv(io.BytesIO(member_bytes))

    assert len(frame.index) == 2
    assert "output_scope" in frame.columns
    assert "omni_scenario" in frame.columns
    assert "omni_contrast_id" in frame.columns


@pytest.mark.parametrize(
    "format_token,member_name",
    [
        ("parquet", "hillslopes.parquet"),
        ("csv", "hillslopes.csv"),
    ],
)
def test_tabular_concatenate_tables_sets_omni_selector_provenance(
    tmp_path: Path,
    format_token: str,
    member_name: str,
) -> None:
    request_payload = NormalizedExportRequest(
        format=format_token,
        units="project",
        layers=("wepp.summary.hillslopes", "omni.scenarios.hillslopes", "omni.contrasts.hillslopes"),
        crs="wgs",
        output_scopes=("baseline",),
        scenarios=("scenario-a",),
        contrast_ids=("contrast-a",),
        swat_run_id="none",
        tabular=NormalizedTabularRequest(concatenate_tables=True, temporal_layout="wide"),
    )
    layer_base = ResolvedLayerPlan(
        layer_id="wepp.summary.hillslopes",
        family="wepp",
        scope_class="scope_aware",
        scope="baseline",
        output_layer_id="baseline__wepp.summary.hillslopes",
        context="base",
        carrier_layer="sbs_map-subcatchments",
    )
    layer_scenario = ResolvedLayerPlan(
        layer_id="omni.scenarios.hillslopes",
        family="omni_scenarios",
        scope_class="scope_invariant",
        scope="shared",
        output_layer_id="scenario-scenario-a__shared__omni.scenarios.hillslopes",
        context="scenario",
        selector_id="scenario-a",
        carrier_layer="sbs_map-subcatchments",
    )
    layer_contrast = ResolvedLayerPlan(
        layer_id="omni.contrasts.hillslopes",
        family="omni_contrasts",
        scope_class="scope_invariant",
        scope="shared",
        output_layer_id="contrast-contrast-a__shared__omni.contrasts.hillslopes",
        context="contrast",
        selector_id="contrast-a",
        carrier_layer="sbs_map-subcatchments",
    )
    plan = ResolvedExportPlan(
        catalog_version="test",
        schema_version=1,
        request=request_payload,
        layers=(layer_base, layer_scenario, layer_contrast),
        warnings=(),
    )
    payloads: dict[str, PreparedLayerPayload] = {}
    for index, layer in enumerate(plan.layers):
        payloads[layer.output_layer_id] = PreparedLayerPayload(
            output_layer_id=layer.output_layer_id,
            payload=b"",
            tabular_frame=pd.DataFrame(
                [
                    {"topaz_id": index + 1, "metric": float(index + 1)},
                ]
            ),
            row_count=1,
            feature_count=1,
        )

    request = ExportWriterRequest(
        plan=plan,
        layer_payloads=payloads,
        artifact_dir=tmp_path,
        artifact_basename="features_export",
    )
    artifact = get_export_writer(format_token).write(request)
    assert member_name in artifact.packaged_member_relpaths

    with zipfile.ZipFile(artifact.artifact_path, "r") as zip_handle:
        member_bytes = zip_handle.read(member_name)

    if format_token == "parquet":
        frame = pd.read_parquet(io.BytesIO(member_bytes))
    else:
        frame = pd.read_csv(io.BytesIO(member_bytes))

    assert sorted(frame["omni_scenario"].dropna().unique().tolist()) == ["scenario-a"]
    assert sorted(frame["omni_contrast_id"].dropna().unique().tolist()) == ["contrast-a"]
