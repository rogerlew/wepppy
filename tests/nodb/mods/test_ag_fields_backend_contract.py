from __future__ import annotations

import zipfile
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from wepppy.nodb.mods.ag_fields import (
    AgFields,
    PlantFileProcessingError,
    RotationLookupValidationError,
)
from wepppy.nodb.mods.ag_fields import ag_fields as ag_fields_module


pytestmark = [pytest.mark.unit, pytest.mark.nodb]


def _controller(tmp_path: Path) -> AgFields:
    return AgFields(str(tmp_path), "disturbed9002-wbt-mofe.cfg")


def _set_observed_climate(monkeypatch: pytest.MonkeyPatch, start: int = 2001, end: int = 2002) -> None:
    climate = SimpleNamespace(
        climate_mode=ag_fields_module.ClimateMode.Observed,
        observed_start_year=start,
        observed_end_year=end,
    )
    monkeypatch.setattr(AgFields, "climate_instance", property(lambda _self: climate))


def test_confirm_schema_is_atomic_when_rotation_accessor_is_invalid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = _controller(tmp_path)
    _set_observed_climate(monkeypatch)
    with controller.locked():
        controller._field_boundaries_geojson = "fields.WGS.geojson"
        controller._field_columns = ["field_id", "Crop2001", "Crop2002"]
        controller._field_id_key = "field_id"

    with pytest.raises(ValueError, match="Crop2002"):
        controller.confirm_schema("Crop2001", "Missing{}")

    assert controller.field_id_key == "field_id"
    assert controller.rotation_accessor is None


def test_boundary_reupload_clears_schema_and_marks_subfields_stale(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = _controller(tmp_path)
    with controller.locked():
        controller._geojson_hash = "old-hash"
        controller._field_boundaries_geojson = "fields.WGS.geojson"
        controller._field_columns = ["field_id", "Crop2001"]
        controller._field_id_key = "field_id"
        controller._rotation_accessor = "Crop{}"
        controller._sub_field_n = 1
        controller._subfields_source_signature = controller._schema_signature()

    source = tmp_path / "replacement.geojson"
    source.write_text('{"type":"FeatureCollection","features":[]}', encoding="utf-8")
    frame = pd.DataFrame([{"field_id": 7, "Crop2001": "wheat"}])
    import geopandas as geopandas_module

    monkeypatch.setattr(geopandas_module, "read_file", lambda *_args, **_kwargs: frame)
    monkeypatch.setattr(pd.DataFrame, "to_parquet", lambda *_args, **_kwargs: None)

    controller.validate_field_boundary_geojson(source)

    assert controller.field_id_key is None
    assert controller.rotation_accessor is None
    assert controller.get_staleness()["subfields"] is True


def test_invalid_boundary_reupload_preserves_canonical_artifacts_and_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = _controller(tmp_path)
    canonical = Path(controller.ag_fields_dir) / "fields.WGS.geojson"
    canonical.write_text("old-valid-content", encoding="utf-8")
    with controller.locked():
        controller._field_boundaries_geojson = canonical.name
        controller._geojson_is_valid = True
        controller._geojson_hash = "old-hash"
        controller._field_columns = ["field_id", "Crop2001"]
        controller._field_id_key = "field_id"
        controller._rotation_accessor = "Crop{}"

    source = tmp_path / "invalid.geojson"
    source.write_text("new-invalid-content", encoding="utf-8")
    import geopandas as geopandas_module

    monkeypatch.setattr(
        geopandas_module,
        "read_file",
        lambda *_args, **_kwargs: pd.DataFrame([{"not_field_id": 7}]),
    )

    with pytest.raises(ValueError, match="field_id column not found"):
        controller.validate_field_boundary_geojson(source)

    assert canonical.read_text(encoding="utf-8") == "old-valid-content"
    assert controller.geojson_hash == "old-hash"
    assert controller.field_id_key == "field_id"
    assert controller.rotation_accessor == "Crop{}"


def test_plant_upload_normalizes_case_replaces_and_suffixes_archive_collisions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = _controller(tmp_path)

    def _read_management(path: str):
        contents = Path(path).read_text(encoding="utf-8")
        if "invalid" in contents:
            raise ValueError("invalid management")
        return SimpleNamespace(contents=contents)

    monkeypatch.setattr(ag_fields_module, "read_management", _read_management)

    first_zip = Path(controller.ag_fields_dir) / "plants.zip"
    with zipfile.ZipFile(first_zip, "w") as archive:
        archive.writestr("Crop File.MAN", "valid-first")
        archive.writestr("nested/Crop File.man", "valid-second")
        archive.writestr("bad.MAN", "invalid")
        archive.writestr("../escape.man", "valid-unsafe")

    first = controller.handle_plant_file_db_upload(first_zip.name)

    assert first["valid_files"] == ["Crop_File.man", "Crop_File_1.man"]
    assert first["invalid_files"] == [{"filename": "bad.man", "error": "invalid management"}]
    assert not (tmp_path / "escape.man").exists()

    second_zip = Path(controller.ag_fields_dir) / "replacement.zip"
    with zipfile.ZipFile(second_zip, "w") as archive:
        archive.writestr("Crop File.man", "valid-replacement")

    second = controller.handle_plant_file_db_upload(second_zip.name)

    assert second["replaced"] == ["Crop_File.man"]
    assert (Path(controller.plant_files_dir) / "Crop_File.man").read_text(encoding="utf-8") == "valid-replacement"
    assert (Path(controller.plant_files_dir) / "Crop_File_1.man").is_file()

    inventory = controller.delete_plant_file("Crop_File.man")
    assert "Crop_File.man" not in inventory["valid_files"]
    assert not (Path(controller.plant_files_dir) / "Crop_File.man").exists()


def test_unreadable_2017_plant_file_persists_filename_in_failure_inventory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = _controller(tmp_path)
    upload = Path(controller.ag_fields_dir) / "plants-2017.zip"
    with zipfile.ZipFile(upload, "w") as archive:
        archive.writestr("Broken.MAN", "2017.1\nunreadable")

    monkeypatch.setattr(
        ag_fields_module,
        "read_management",
        lambda _path: (_ for _ in ()).throw(ValueError("bad 2017 format")),
    )

    with pytest.raises(PlantFileProcessingError) as exc_info:
        controller.handle_plant_file_db_upload(upload.name)

    assert exc_info.value.filename == "Broken.man"
    assert controller.get_invalid_plant_files() == [
        {"filename": "Broken.man", "error": "bad 2017 format"}
    ]


def test_rotation_lookup_writer_round_trips_partial_mapping_and_rejects_invalid_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = _controller(tmp_path)
    plant_path = Path(controller.plant_files_dir) / "corn.man"
    plant_path.write_text("management", encoding="utf-8")
    monkeypatch.setattr(controller, "get_unique_crops", lambda: {"Corn", "Wheat"})
    monkeypatch.setattr(
        AgFields,
        "landuse_instance",
        property(lambda _self: SimpleNamespace(mapping="default")),
    )

    results = controller.write_rotation_lookup(
        [
            {"crop_name": "Corn", "database": "plant_file_db", "rotation_id": "corn.man"},
            {"crop_name": "Wheat", "database": None, "rotation_id": None},
        ]
    )

    assert [(item["crop_name"], item["status"]) for item in results] == [
        ("Corn", "ok"),
        ("Wheat", "unmapped"),
    ]
    manager = ag_fields_module.CropRotationManager(
        controller.ag_fields_dir,
        "default",
        logger_name=None,
    )
    assert manager.rotation_lookup["Corn"].man_path == str(plant_path)
    before = Path(controller.rotation_lookup_path).read_text(encoding="utf-8")

    with pytest.raises(RotationLookupValidationError) as exc_info:
        controller.write_rotation_lookup(
            [{"crop_name": "Corn", "database": "plant_file_db", "rotation_id": "missing.man"}]
        )

    assert any(item["status"] == "error" for item in exc_info.value.results)
    assert Path(controller.rotation_lookup_path).read_text(encoding="utf-8") == before


def test_readiness_requires_observed_bounds_flovec_and_each_parent_wepp_pair(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = _controller(tmp_path)
    _set_observed_climate(monkeypatch, start=2001, end=2001)
    subfields_path = Path(controller.subfields_parquet_path)
    subfields_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"wepp_id": 11}, {"wepp_id": 12}]).to_parquet(subfields_path)
    flovec = tmp_path / "dem" / "wbt" / "flovec.tif"
    flovec.parent.mkdir(parents=True)
    flovec.touch()
    runs = tmp_path / "wepp" / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    for suffix in ("sol", "cli"):
        (runs / f"p11.{suffix}").touch()

    readiness = controller.get_readiness()

    assert readiness["observed_climate"] is True
    assert readiness["watershed_abstraction"] is True
    assert readiness["parent_wepp"] is False
    assert readiness["missing_parent_wepp_ids"] == [12]

    for suffix in ("sol", "cli"):
        (runs / f"p12.{suffix}").touch()
    assert controller.get_readiness()["parent_wepp"] is True


@pytest.mark.parametrize(
    "mode",
    [
        ag_fields_module.ClimateMode.Observed,
        ag_fields_module.ClimateMode.ObservedPRISM,
        ag_fields_module.ClimateMode.ObservedDb,
        ag_fields_module.ClimateMode.PRISM,
        ag_fields_module.ClimateMode.EOBS,
        ag_fields_module.ClimateMode.AGDC,
        ag_fields_module.ClimateMode.GridMetPRISM,
        ag_fields_module.ClimateMode.DepNexrad,
    ],
)
def test_readiness_accepts_supported_observed_climate_modes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode,
) -> None:
    controller = _controller(tmp_path)
    climate = SimpleNamespace(
        climate_mode=mode,
        observed_start_year="2001",
        observed_end_year="2002",
    )
    monkeypatch.setattr(AgFields, "climate_instance", property(lambda _self: climate))

    assert controller.get_readiness()["observed_climate"] is True


def test_readiness_rejects_future_mode_even_with_integer_year_bounds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = _controller(tmp_path)
    climate = SimpleNamespace(
        climate_mode=ag_fields_module.ClimateMode.Future,
        observed_start_year=2001,
        observed_end_year=2002,
    )
    monkeypatch.setattr(AgFields, "climate_instance", property(lambda _self: climate))

    assert controller.get_readiness()["observed_climate"] is False


@pytest.mark.parametrize("bad_year", [True, 2001.5, "not-a-year"])
def test_readiness_rejects_non_integer_year_bounds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bad_year,
) -> None:
    controller = _controller(tmp_path)
    climate = SimpleNamespace(
        climate_mode=ag_fields_module.ClimateMode.Observed,
        observed_start_year=bad_year,
        observed_end_year=2002,
    )
    monkeypatch.setattr(AgFields, "climate_instance", property(lambda _self: climate))

    assert controller.get_readiness()["observed_climate"] is False


def test_historical_state_without_source_signatures_defaults_to_stale(tmp_path: Path) -> None:
    controller = _controller(tmp_path)
    with controller.locked():
        controller._geojson_hash = "hash"
        controller._field_boundaries_geojson = "fields.WGS.geojson"
        controller._field_columns = ["field_id", "Crop2001"]
        controller._field_id_key = "field_id"
        controller._rotation_accessor = "Crop{}"
        controller._sub_field_n = 1
        del controller._subfields_source_signature
        del controller._wepp_source_signature
    runs_dir = Path(controller.ag_field_wepp_runs_dir)
    (runs_dir / "p1.run").touch()

    assert controller.get_staleness() == {"subfields": True, "wepp_runs": True}
