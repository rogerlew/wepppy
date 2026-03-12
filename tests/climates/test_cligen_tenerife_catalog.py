from __future__ import annotations

import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from wepppy.climates.cligen import CligenStationsManager
from wepppy.climates.cligen._scripts.build_tenerife_station_db import build_tenerife_catalog


pytestmark = pytest.mark.integration
_REPO_ROOT = Path(__file__).resolve().parents[2]
_CLIGEN_DIR = _REPO_ROOT / "wepppy/climates/cligen"
_CONFIGS = (
    _REPO_ROOT / "wepppy/nodb/configs/tenerife-disturbed.cfg",
    _REPO_ROOT / "wepppy/nodb/configs/tenerife-5m-disturbed.cfg",
)


def test_tenerife_catalog_manager_loads_station_metadata() -> None:
    manager = CligenStationsManager(version="tenerife_stations.db")

    assert len(manager.stations) == 62
    assert manager.states == {"TF": "Tenerife"}

    station = manager.get_station_fromid("Estacion_7_OROTAV01")
    assert station is not None
    assert station.state == "TF"
    assert station.par == "Estacion_7_OROTAV01.par"
    assert station.desc.startswith("OROTAV01")
    assert Path(station.parpath).exists()
    assert station.latitude == pytest.approx(28.40657674111988)
    assert station.longitude == pytest.approx(-16.514323028739682)
    assert station.elevation == pytest.approx(702.0)


def test_tenerife_catalog_manager_returns_exact_station_for_its_coordinates() -> None:
    manager = CligenStationsManager(version="tenerife_stations.db")
    station = manager.get_station_fromid("Estacion_7_OROTAV01")

    assert station is not None

    nearest = manager.get_closest_station((station.longitude, station.latitude))

    assert nearest.id == "Estacion_7_OROTAV01"
    assert nearest.par == "Estacion_7_OROTAV01.par"
    assert nearest.state == "TF"
    assert nearest.distance == pytest.approx(0.0)


def test_tenerife_catalog_builder_rebuilds_database_from_repo_assets() -> None:
    with TemporaryDirectory() as td:
        output_dir = Path(td)
        db_path, par_dir = build_tenerife_catalog(_CLIGEN_DIR, output_dir)

        assert db_path.exists()
        assert par_dir.exists()
        assert len(list(par_dir.glob("*.par"))) == 62

        conn = sqlite3.connect(db_path)
        try:
            station_count = conn.execute("select count(*) from stations").fetchone()[0]
            state_rows = conn.execute("select state_code, state_name from states").fetchall()
        finally:
            conn.close()

        assert station_count == 62
        assert state_rows == [("TF", "Tenerife")]


def test_active_tenerife_configs_use_dedicated_station_database() -> None:
    for config_path in _CONFIGS:
        text = config_path.read_text(encoding="utf-8")
        assert 'cligen_db = "tenerife_stations.db"' in text
        assert 'cligen_db = "ghcn_stations.db"' not in text
        assert 'delineation_backend = "wbt"' in text
        assert 'fill_or_breach = "breach_least_cost"' in text
