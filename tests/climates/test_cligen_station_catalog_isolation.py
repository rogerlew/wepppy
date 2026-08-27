from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest

from wepppy.climates.cligen.cligen import CligenStationsManager


pytestmark = pytest.mark.unit

_BBOX = (-101.0, 41.0, -99.0, 39.0)
_CATALOGS = (
    ("legacy", "stations.db", "stations"),
    ("2015_stations.db", "2015_stations.db", "2015_par_files"),
    (
        "ghcn_stations.db",
        "ghcn_stations.db",
        "GHCN_Intl_Stations/all_years",
    ),
)


def test_real_concurrent_station_catalogs_keep_database_and_par_roots_paired() -> None:
    """Exercise real SQLite rows and PAR files without mocks or call assertions."""

    start = Barrier(len(_CATALOGS))

    def load_catalog(selector: str, db_name: str, root_name: str) -> tuple[int, Path]:
        start.wait(timeout=10)
        root: Path | None = None
        station_count = 0
        for _iteration in range(8):
            manager = CligenStationsManager(selector, bbox=_BBOX)
            assert Path(manager.db_path).name == db_name
            root = Path(manager.stations_dir).absolute()
            assert root.as_posix().endswith(root_name)
            assert manager.stations
            for station in manager.stations:
                # Keep the catalog-root path lexical: GHCN all_years entries
                # intentionally symlink into record-length subdirectories.
                parpath = Path(station.parpath).absolute()
                assert parpath.is_relative_to(root)
                assert parpath.is_file()
            station_count += len(manager.stations)
        assert root is not None
        return station_count, root

    with ThreadPoolExecutor(max_workers=len(_CATALOGS)) as executor:
        futures = [
            executor.submit(load_catalog, selector, db_name, root_name)
            for selector, db_name, root_name in _CATALOGS
        ]
        results = [future.result(timeout=30) for future in futures]

    assert all(station_count > 0 for station_count, _root in results)
    assert len({root for _station_count, root in results}) == len(_CATALOGS)
