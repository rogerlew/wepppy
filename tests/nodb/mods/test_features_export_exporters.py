from __future__ import annotations

from pathlib import Path
import sqlite3
import zipfile

import pytest

from wepppy.nodb.mods.features_export.catalog_loader import load_layer_catalog
from wepppy.nodb.mods.features_export.contracts import ExportWarning
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
