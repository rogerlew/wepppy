import pytest

pytest.importorskip("rasterio", reason="rasterio required to load landuse catalog module")

from wepppy.nodb.locales.landuse_catalog import available_landuse_datasets


def _landcover_keys(locales):
    datasets = available_landuse_datasets(None, [], locales)
    return [dataset.key for dataset in datasets if dataset.kind == "landcover"]


def test_landcover_datasets_default_locale():
    keys = _landcover_keys([])
    assert len(keys) == 114
    assert keys[0] == "nlcd/ever_forest/2024"
    assert keys[40] == "nlcd/2015"
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
