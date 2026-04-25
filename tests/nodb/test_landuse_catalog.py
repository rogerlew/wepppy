import pytest

pytest.importorskip("rasterio", reason="rasterio required to load landuse catalog module")

import wepppy.nodb.locales.landuse_catalog as landuse_catalog_module
from wepppy.nodb.locales.landuse_catalog import available_landuse_datasets


@pytest.fixture(autouse=True)
def _clear_landuse_catalog_cache():
    landuse_catalog_module._load_catalog.cache_clear()
    yield
    landuse_catalog_module._load_catalog.cache_clear()


def _landcover_keys(locales):
    datasets = available_landuse_datasets(None, [], locales)
    return [dataset.key for dataset in datasets if dataset.kind == "landcover"]


def test_landcover_datasets_default_locale():
    keys = _landcover_keys([])
    assert len(keys) == 114
    assert keys[0] == "nlcd/ever_forest/2024"
    assert keys[40] == "nlcd/2024"
    assert "nlcd/2015" in keys
    assert keys[-1] == "islay.ceoas.oregonstate.edu/v1/landcover/vote/1984"


def test_landcover_datasets_alaska_locale():
    keys = _landcover_keys(["alaska"])
    assert keys == [
        "alaska/nlcd/2001",
        "alaska/nlcd/2011",
        "alaska/nlcd/2016",
    ]


def test_landcover_datasets_earth_locale():
    keys = _landcover_keys(["earth"])
    assert len(keys) == 29
    assert keys[:3] == [
        "locales/earth/C3Slandcover/2020",
        "locales/earth/C3Slandcover/2019",
        "locales/earth/C3Slandcover/2018",
    ]
    assert keys[-1] == "locales/earth/C3Slandcover/1992"


def test_management_catalog_excludes_null_and_dedups_by_description_management_pair(monkeypatch):
    def _fake_load_map(_mapping):
        return {
            "100": {
                "Key": "100",
                "Description": "Open Water",
                "ManagementFile": "GeoWEPP/grass.man",
            },
            "101": {
                "Key": "101",
                "Description": "Open Water Duplicate",
                "ManagementFile": "GeoWEPP/grass.man",
            },
            "102": {
                "Key": "102",
                "Description": "Open Water",
                "ManagementFile": "GeoWEPP/grass.man",
            },
            "110": {
                "Key": "110",
                "Description": "Prescribed Fire",
                "ManagementFile": "UnDisturbed/Prescribed_Fire.man",
                "IsTreatment": True,
            },
            "142": {
                "Key": "142",
                "Description": "Treatment Sentinel",
                "ManagementFile": "UnDisturbed/null.man",
                "IsTreatment": True,
            },
        }

    monkeypatch.setattr(landuse_catalog_module, "load_map", _fake_load_map)

    datasets = available_landuse_datasets(None, [], [])
    mapping_datasets = [dataset for dataset in datasets if dataset.kind == "mapping"]

    assert [dataset.key for dataset in mapping_datasets] == ["100", "101", "110"]
    assert [dataset.description for dataset in mapping_datasets] == [
        "Open Water",
        "Open Water Duplicate",
        "Prescribed Fire",
    ]
    assert [dataset.management_file for dataset in mapping_datasets] == [
        "GeoWEPP/grass.man",
        "GeoWEPP/grass.man",
        "UnDisturbed/Prescribed_Fire.man",
    ]
