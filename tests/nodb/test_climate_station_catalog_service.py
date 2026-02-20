from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from wepppy.nodb.core.climate import ClimateMode, ClimateStationMode
from wepppy.nodb.core.climate_station_catalog_service import ClimateStationCatalogService

pytestmark = pytest.mark.unit


class _Station:
    def __init__(self, station_id: str) -> None:
        self.id = station_id

    def as_dict(self):
        return {"id": self.id}


class _DummyClimate:
    def __init__(self) -> None:
        self._locked = False
        self._closest_stations = None
        self._heuristic_stations = None
        self._climatestation_mode = ClimateStationMode.FindClosestAtRuntime
        self._climatestation = None
        self._climate_mode = ClimateMode.Vanilla
        self._user_station_meta = None
        self._catalog_id = None
        self.locales = ["us"]
        self.ron_instance = SimpleNamespace(mods=[], dem_fn="dem.tif")
        self.watershed_instance = SimpleNamespace(
            centroid=(-116.2, 43.6),
            hillslope_centroid_lnglat=lambda _topaz_id: (-115.9, 43.8),
        )
        self.cligen_db = "ghcn"
        self.logger = SimpleNamespace(warning=lambda *_args, **_kwargs: None)

    @property
    def catalog_id(self):
        return self._catalog_id

    @property
    def climatestation(self):
        return self._climatestation

    @property
    def closest_stations(self):
        if self._closest_stations is None:
            return None
        return [station.as_dict() for station in self._closest_stations]

    @property
    def heuristic_stations(self):
        if self._heuristic_stations is None:
            return None
        return [station.as_dict() for station in self._heuristic_stations]

    def islocked(self):
        return self._locked

    @contextmanager
    def locked(self):
        self._locked = True
        yield
        self._locked = False


def test_find_closest_stations_sets_mode_and_selected_station(monkeypatch: pytest.MonkeyPatch) -> None:
    service = ClimateStationCatalogService()
    climate = _DummyClimate()

    class _Manager:
        def __init__(self, version: str) -> None:
            assert version == "ghcn"

        def get_closest_stations(self, location, num_stations):
            assert location == (-116.2, 43.6)
            assert num_stations == 3
            return [_Station("STA-1"), _Station("STA-2")]

    monkeypatch.setattr("wepppy.nodb.core.climate_station_catalog_service.CligenStationsManager", _Manager)

    stations = service.find_closest_stations(climate, num_stations=3)

    assert stations == [{"id": "STA-1"}, {"id": "STA-2"}]
    assert climate._climatestation_mode == ClimateStationMode.Closest
    assert climate._climatestation == "STA-1"


def test_find_heuristic_stations_uses_locale_specific_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    service = ClimateStationCatalogService()
    climate = _DummyClimate()

    climate.locales = ["eu"]
    monkeypatch.setattr(
        service,
        "find_eu_heuristic_stations",
        lambda _climate, num_stations=10: [{"id": "EU-1"}],
    )
    assert service.find_heuristic_stations(climate, num_stations=4) == [{"id": "EU-1"}]

    climate.locales = ["au"]
    monkeypatch.setattr(
        service,
        "find_au_heuristic_stations",
        lambda _climate, num_stations=None: [{"id": "AU-1"}],
    )
    assert service.find_heuristic_stations(climate, num_stations=4) == [{"id": "AU-1"}]


def test_climatestation_meta_prefers_user_defined_metadata() -> None:
    service = ClimateStationCatalogService()
    climate = _DummyClimate()
    climate._catalog_id = "user_defined_cli"
    climate._climate_mode = ClimateMode.UserDefined
    climate._user_station_meta = {"id": "USER"}

    assert service.climatestation_meta(climate) == {"id": "USER"}


def test_resolve_catalog_dataset_respects_locale_access(monkeypatch: pytest.MonkeyPatch) -> None:
    service = ClimateStationCatalogService()
    climate = _DummyClimate()

    dataset = SimpleNamespace(
        catalog_id="prism_stochastic",
        is_allowed_for=lambda locales, mods, include_hidden=False: False,
    )

    monkeypatch.setattr("wepppy.nodb.locales.get_climate_dataset", lambda catalog_id: dataset)

    assert service.resolve_catalog_dataset(climate, "prism_stochastic") is None
