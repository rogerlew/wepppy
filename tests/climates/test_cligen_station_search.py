from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from wepppy.climates.cligen import CligenStationsManager
from wepppy.climates.cligen import cligen as _cligen_module

pytestmark = pytest.mark.unit


class _FakeStation:
    def __init__(
        self,
        station_id: str,
        *,
        latitude: float,
        longitude: float,
        elevation: float,
        monthly_ppts: np.ndarray,
    ) -> None:
        self.id = station_id
        self.latitude = latitude
        self.longitude = longitude
        self.elevation = elevation
        self._monthly_ppts = monthly_ppts
        self.distance = None
        self.lat_distance = None
        self.rank = None

    def get_station(self) -> SimpleNamespace:
        return SimpleNamespace(monthly_ppts=self._monthly_ppts)

    def calculate_distance(self, location: tuple[float, float]) -> None:
        self.distance = abs(self.longitude - location[0]) + abs(self.latitude - location[1])

    def calculate_lat_distance(self, latitude: float) -> None:
        self.lat_distance = abs(self.latitude - latitude)


def test_get_stations_heuristic_search_survives_query_elevation_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = CligenStationsManager.__new__(CligenStationsManager)
    stations = [
        _FakeStation(
            "STA-1",
            latitude=43.60,
            longitude=-116.20,
            elevation=1200.0,
            monthly_ppts=np.ones(12, dtype=float),
        ),
        _FakeStation(
            "STA-2",
            latitude=43.62,
            longitude=-116.18,
            elevation=1300.0,
            monthly_ppts=np.full(12, 2.0, dtype=float),
        ),
    ]

    monkeypatch.setattr(manager, "get_closest_stations", lambda _location, pool: stations[:pool])

    def _raise_elevation_timeout(*_args, **_kwargs):
        raise RuntimeError('Elevation service returned HTTP 504: {"message":"timeout"}')

    monkeypatch.setattr(_cligen_module, "elevationquery", _raise_elevation_timeout)
    monkeypatch.setattr(
        _cligen_module,
        "get_prism_monthly_ppt",
        lambda *_args, **_kwargs: np.zeros(12, dtype=float),
    )

    ranked = manager.get_stations_heuristic_search((-116.2, 43.6), pool=2)

    assert [station.id for station in ranked] == ["STA-1", "STA-2"]
    assert ranked[0].rank is not None
    assert ranked[1].rank is not None
    assert ranked[0].distance is not None
    assert ranked[1].distance is not None
