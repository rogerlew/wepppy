from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

pytest.importorskip("flask")
from flask import Flask

try:
    import wepppy.weppcloud.routes.nodb_api.climate_bp as climate_module
    from wepppy.nodb.core.climate import ClimateMode
except ImportError:
    pytest.skip("Climate blueprint dependencies missing", allow_module_level=True)

RUN_ID = "test-run"
CONFIG = "main"
pytestmark = pytest.mark.routes


@pytest.fixture()
def climate_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Provide a Flask test client with the climate blueprint registered."""

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(climate_module.climate_bp)

    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()
    cli_dir = run_dir / "cli"
    cli_dir.mkdir()

    def fake_get_wd(runid: str) -> str:
        assert runid == RUN_ID
        return str(run_dir)

    monkeypatch.setattr(climate_module, "get_wd", fake_get_wd)

    class DummyClimate:
        _instances: dict[str, "DummyClimate"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.cli_dir = str(cli_dir)
            self.climatestation_mode = climate_module.ClimateStationMode.Closest
            self.climatestation = "STA-1"
            self.has_observed = True
            self.readonly = False
            self.closest_calls = 0
            self.closest_stations = [
                {
                    "id": "STA-1",
                    "desc": "Station One",
                    "distance_to_query_location": 12.345,
                    "years": 8,
                }
            ]
            self.heuristic_stations: list[dict[str, Any]] | None = None
            self.latest_cli_filename: str | None = None
            self.set_cli_calls = 0
            self.use_gridmet_wind_when_applicable = False
            self.adjust_mx_pt5 = False
            self.climatestation_par_contents = "PAR DATA"
            self.climate_mode = ClimateMode.Vanilla
            self.catalog_id = "dataset_a"
            self._datasets = {
                "dataset_a": SimpleNamespace(catalog_id="dataset_a"),
                "dataset_b": SimpleNamespace(catalog_id="dataset_b")
            }

        @classmethod
        def getInstance(cls, wd: str, ignore_lock: bool = False) -> "DummyClimate":
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

        def set_user_defined_cli(self, filename: str) -> dict[str, str]:
            self.set_cli_calls += 1
            self.latest_cli_filename = filename
            return {"filename": filename}

        def find_closest_stations(self) -> list[dict[str, Any]]:
            self.closest_calls += 1
            return list(self.closest_stations)

        def find_heuristic_stations(self) -> list[dict[str, Any]]:
            return list(self.closest_stations)

        def _resolve_catalog_dataset(self, catalog_id: str, include_hidden: bool = False):
            return self._datasets.get(catalog_id)

    monkeypatch.setattr(climate_module, "Climate", DummyClimate)

    DummyClimate._instances.clear()

    with app.test_client() as client:
        yield client, DummyClimate, run_dir

    DummyClimate._instances.clear()


def test_set_climatestation_mode_updates_controller(climate_client):
    client, climate_cls, run_dir = climate_client
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_climatestation_mode/",
        data={"mode": str(int(climate_module.ClimateStationMode.Heuristic))},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {}

    controller = climate_cls.getInstance(str(run_dir))
    assert controller.climatestation_mode == climate_module.ClimateStationMode.Heuristic


def test_set_climatestation_mode_accepts_json(climate_client):
    client, climate_cls, run_dir = climate_client
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_climatestation_mode/",
        json={"mode": int(climate_module.ClimateStationMode.EUHeuristic)},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {}

    controller = climate_cls.getInstance(str(run_dir))
    assert controller.climatestation_mode == climate_module.ClimateStationMode.EUHeuristic


def test_set_climatestation_accepts_json(climate_client):
    client, climate_cls, run_dir = climate_client
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_climatestation/",
        json={"station": "STA-42"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {}

    controller = climate_cls.getInstance(str(run_dir))
    assert controller.climatestation == "STA-42"


def test_set_climate_mode_updates_catalog_from_json(climate_client):
    client, climate_cls, run_dir = climate_client
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_climate_mode/",
        json={"mode": int(ClimateMode.Future), "catalog_id": "dataset_b"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {}

    controller = climate_cls.getInstance(str(run_dir))
    assert controller.climate_mode == ClimateMode.Future
    assert controller.catalog_id == "dataset_b"


def test_set_climate_spatialmode_accepts_json(climate_client):
    client, climate_cls, run_dir = climate_client
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_climate_spatialmode/",
        json={"spatialmode": 1},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {}

    controller = climate_cls.getInstance(str(run_dir))
    assert controller.climate_spatialmode == 1


def test_view_closest_stations_generates_options(climate_client):
    client, climate_cls, run_dir = climate_client

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/view/closest_stations/")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'value="STA-1"' in html
    assert "Station One" in html

    controller = climate_cls.getInstance(str(run_dir))
    assert controller.closest_calls == 1


def test_task_set_use_gridmet_wind_when_applicable_updates_flag(climate_client):
    client, climate_cls, run_dir = climate_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_use_gridmet_wind_when_applicable/",
        json={"state": True},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {}

    controller = climate_cls.getInstance(str(run_dir))
    assert controller.use_gridmet_wind_when_applicable is True


def test_task_set_adjust_mx_pt5_updates_flag(climate_client):
    client, climate_cls, run_dir = climate_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_adjust_mx_pt5/",
        json={"state": True},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {}

    controller = climate_cls.getInstance(str(run_dir))
    assert controller.adjust_mx_pt5 is True

