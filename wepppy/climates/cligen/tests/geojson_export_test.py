from __future__ import annotations

from pathlib import Path

import pytest

from wepppy.climates.cligen import CligenStationsManager
from wepppy.climates.cligen import cligen as _cligen_module

_SQLITE_MAGIC = b"SQLite format 3\x00"


def _has_sqlite_header(db_path: Path) -> bool:
    try:
        with db_path.open("rb") as handle:
            return handle.read(len(_SQLITE_MAGIC)) == _SQLITE_MAGIC
    except OSError:
        return False


def collection_error(tmp_path: Path) -> None:
    db_path = Path(_cligen_module._db)
    if not _has_sqlite_header(db_path):
        pytest.skip("Cligen station database is unavailable (Git LFS asset not fetched).")

    station_manager = CligenStationsManager(bbox=[-120, 47, -115, 42])
    assert station_manager.stations, "No stations found in the bounding box"

    export_path = tmp_path / "stations.geojson"
    station_manager.export_to_geojson(str(export_path))
    assert export_path.exists(), "GeoJSON export failed to create output file"
    assert "KS" in station_manager.states, "Expected Kansas (KS) metadata in station states"
