from __future__ import annotations

import importlib
import inspect
import os
from pathlib import Path
import stat
import subprocess
from types import SimpleNamespace
import zipfile

from osgeo import gdal, ogr, osr
import pytest

from wepppy.nodb.mods.features_export.exporters.base import (
    ExportBackendCapabilityError,
    FeaturesExportWriterError,
)
from wepppy.nodb.mods.features_export.exporters import geodatabase

def _has_required_bits(path: Path, required_bits: int) -> bool:
    return (path.lstat().st_mode & required_bits) == required_bits


def _create_source_geopackage(path: Path) -> None:
    driver = ogr.GetDriverByName("GPKG")
    assert driver is not None
    dataset = driver.CreateDataSource(str(path))
    assert dataset is not None
    spatial_ref = osr.SpatialReference()
    spatial_ref.ImportFromEPSG(4326)
    layer = dataset.CreateLayer("sample_points", srs=spatial_ref, geom_type=ogr.wkbPoint)
    assert layer is not None
    assert layer.CreateField(ogr.FieldDefn("name", ogr.OFTString)) == ogr.OGRERR_NONE
    assert layer.CreateField(ogr.FieldDefn("large_id", ogr.OFTInteger64)) == ogr.OGRERR_NONE
    feature = ogr.Feature(layer.GetLayerDefn())
    feature.SetField("name", "sample")
    feature.SetField("large_id", 2**40)
    geometry = ogr.Geometry(ogr.wkbPoint)
    geometry.SetPoint_2D(0, -116.0, 46.0)
    feature.SetGeometry(geometry)
    assert layer.CreateFeature(feature) == ogr.OGRERR_NONE

    empty_layer = dataset.CreateLayer(
        "empty_points",
        srs=spatial_ref,
        geom_type=ogr.wkbPoint,
    )
    assert empty_layer is not None
    assert empty_layer.CreateField(ogr.FieldDefn("name", ogr.OFTString)) == ogr.OGRERR_NONE

    table = dataset.CreateLayer("attributes", geom_type=ogr.wkbNone)
    assert table is not None
    assert table.CreateField(ogr.FieldDefn("name", ogr.OFTString)) == ogr.OGRERR_NONE
    assert table.CreateField(ogr.FieldDefn("nullable", ogr.OFTString)) == ogr.OGRERR_NONE
    table_feature = ogr.Feature(table.GetLayerDefn())
    table_feature.SetField("name", "table-row")
    assert table.CreateFeature(table_feature) == ogr.OGRERR_NONE
    dataset = None


@pytest.mark.unit
def test_openfilegdb_default_timeout_honors_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENFILEGDB_COMMAND_TIMEOUT", "2400")
    module = importlib.reload(geodatabase)

    assert module.DEFAULT_OPENFILEGDB_TIMEOUT == 2400
    assert inspect.signature(module.convert_geopackage_to_openfilegdb).parameters["timeout"].default == 2400

    monkeypatch.delenv("OPENFILEGDB_COMMAND_TIMEOUT", raising=False)
    importlib.reload(module)


@pytest.mark.unit
def test_conversion_selects_openfilegdb_and_sets_output_permissions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path = tmp_path / "input.gpkg"
    source_path.write_bytes(b"gpkg")
    target_path = tmp_path / "features_export.gdb"
    captured: dict[str, object] = {}

    monkeypatch.setattr(geodatabase, "openfilegdb_create_available", lambda: True)

    def _fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        inner_path = target_path / "inner"
        inner_path.mkdir(parents=True)
        table_path = inner_path / "table.gdbtable"
        table_path.write_text("stub", encoding="utf-8")
        os.chmod(target_path, 0o500)
        os.chmod(inner_path, 0o500)
        os.chmod(table_path, 0o400)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(geodatabase.subprocess, "run", _fake_run)

    result = geodatabase.convert_geopackage_to_openfilegdb(
        str(source_path),
        str(target_path),
        timeout=42,
    )

    assert result == str(target_path.resolve())
    assert captured["command"] == [
        "ogr2ogr",
        "-f",
        "OpenFileGDB",
        str(target_path.resolve()),
        str(source_path.resolve()),
    ]
    assert captured["kwargs"] == {
        "check": False,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "timeout": 42,
    }
    assert _has_required_bits(target_path, geodatabase._DIR_PERMISSION_BITS)
    assert _has_required_bits(target_path / "inner", geodatabase._DIR_PERMISSION_BITS)
    assert _has_required_bits(target_path / "inner" / "table.gdbtable", geodatabase._FILE_PERMISSION_BITS)
    assert _has_required_bits(target_path.with_suffix(".gdb.zip"), geodatabase._FILE_PERMISSION_BITS)


@pytest.mark.unit
def test_conversion_fails_before_execution_without_create_capability(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path = tmp_path / "input.gpkg"
    source_path.write_bytes(b"gpkg")
    monkeypatch.setattr(geodatabase, "openfilegdb_create_available", lambda: False)

    with pytest.raises(ExportBackendCapabilityError, match="OpenFileGDB vector-create capability"):
        geodatabase.convert_geopackage_to_openfilegdb(
            str(source_path),
            str(tmp_path / "output.gdb"),
        )


@pytest.mark.unit
def test_conversion_timeout_removes_partial_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path = tmp_path / "input.gpkg"
    source_path.write_bytes(b"gpkg")
    target_path = tmp_path / "output.gdb"
    monkeypatch.setattr(geodatabase, "openfilegdb_create_available", lambda: True)

    def _timeout(command, **kwargs):
        target_path.mkdir()
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(geodatabase.subprocess, "run", _timeout)

    with pytest.raises(FeaturesExportWriterError, match="42-second timeout"):
        geodatabase.convert_geopackage_to_openfilegdb(
            str(source_path),
            str(target_path),
            timeout=42,
        )
    assert not target_path.exists()


@pytest.mark.unit
def test_conversion_failure_reports_diagnostics_and_removes_partial_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path = tmp_path / "input.gpkg"
    source_path.write_bytes(b"gpkg")
    target_path = tmp_path / "output.gdb"
    monkeypatch.setattr(geodatabase, "openfilegdb_create_available", lambda: True)

    def _fail(_command, **_kwargs):
        target_path.mkdir()
        return SimpleNamespace(returncode=1, stdout="conversion output", stderr="invalid layer")

    monkeypatch.setattr(geodatabase.subprocess, "run", _fail)

    with pytest.raises(FeaturesExportWriterError, match="invalid layer"):
        geodatabase.convert_geopackage_to_openfilegdb(
            str(source_path),
            str(target_path),
        )
    assert not target_path.exists()


@pytest.mark.integration
def test_real_openfilegdb_conversion_preserves_representative_values(tmp_path: Path) -> None:
    if not geodatabase.openfilegdb_create_available():
        pytest.skip("GDAL OpenFileGDB vector-create capability is unavailable")

    source_path = tmp_path / "input.gpkg"
    target_path = tmp_path / "output.gdb"
    _create_source_geopackage(source_path)

    geodatabase.convert_geopackage_to_openfilegdb(str(source_path), str(target_path))

    output = gdal.OpenEx(str(target_path), gdal.OF_VECTOR)
    assert output is not None
    layer = output.GetLayerByName("sample_points")
    assert layer is not None
    assert layer.GetFeatureCount() == 1
    feature = layer.GetNextFeature()
    assert feature.GetField("name") == "sample"
    assert feature.GetField("large_id") == float(2**40)
    assert feature.GetGeometryRef().ExportToWkt() == "POINT (-116 46)"
    assert output.GetLayerByName("empty_points").GetFeatureCount() == 0
    table = output.GetLayerByName("attributes")
    assert table.GetGeomType() == ogr.wkbNone
    table_feature = table.GetNextFeature()
    assert table_feature.GetField("name") == "table-row"
    assert table_feature.IsFieldNull("nullable")
    output = None
    zip_path = target_path.with_suffix(".gdb.zip")
    assert zip_path.is_file()
    with zipfile.ZipFile(zip_path) as archive:
        assert archive.namelist()
        assert all(member.startswith("output.gdb/") for member in archive.namelist())

    zipped_output = gdal.OpenEx(str(zip_path), gdal.OF_VECTOR)
    assert zipped_output is not None
    assert zipped_output.GetLayerByName("sample_points").GetFeatureCount() == 1
    zipped_output = None
