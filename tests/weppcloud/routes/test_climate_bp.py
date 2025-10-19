from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("flask")
from flask import Flask

import wepppy.weppcloud.routes.nodb_api.climate_bp as climate_module

RUN_ID = "test-run"
CONFIG = "main"


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

    class DummyRon:
        _instances: dict[str, "DummyRon"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.readonly = False

        @classmethod
        def getInstance(cls, wd: str) -> "DummyRon":
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

    monkeypatch.setattr(climate_module, "Ron", DummyRon)

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
            self.climatestation_par_contents = "PAR DATA"

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

    monkeypatch.setattr(climate_module, "Climate", DummyClimate)

    DummyRon._instances.clear()
    DummyClimate._instances.clear()

    with app.test_client() as client:
        yield client, DummyClimate, run_dir

    DummyRon._instances.clear()
    DummyClimate._instances.clear()


def test_set_climatestation_mode_updates_controller(climate_client):
    client, climate_cls, run_dir = climate_client
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_climatestation_mode/",
        data={"mode": str(int(climate_module.ClimateStationMode.Heuristic))},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Success"] is True

    controller = climate_cls.getInstance(str(run_dir))
    assert controller.climatestation_mode == climate_module.ClimateStationMode.Heuristic


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
    assert payload["Success"] is True

    controller = climate_cls.getInstance(str(run_dir))
    assert controller.use_gridmet_wind_when_applicable is True


def test_task_upload_cli_persists_file(climate_client):
    client, climate_cls, run_dir = climate_client

    payload = {
        "input_upload_cli": (io.BytesIO(b"cli content"), "custom.cli"),
    }
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/upload_cli/",
        data=payload,
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Success"] is True

    controller = climate_cls.getInstance(str(run_dir))
    assert controller.latest_cli_filename == "custom.cli"
    assert controller.set_cli_calls == 1

    saved_file = Path(controller.cli_dir) / "custom.cli"
    assert saved_file.exists()
    assert saved_file.read_bytes() == b"cli content"
