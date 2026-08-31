from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict

import pytest

pytest.importorskip("flask")
from flask import Flask

import wepppy.weppcloud.routes.nodb_api.soils_bp as soils_module

RUN_ID = "test-run"
CONFIG = "cfg"


@pytest.fixture()
def soils_client(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Provide a Flask client with the soils blueprint and stubbed dependencies."""

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(soils_module.soils_bp)

    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()

    def fake_load_run_context(runid: str, config: str) -> SimpleNamespace:
        assert runid == RUN_ID
        assert config == CONFIG
        return SimpleNamespace(active_root=run_dir)

    monkeypatch.setattr(soils_module, "load_run_context", fake_load_run_context)

    class DummySoils:
        _instances: Dict[str, "DummySoils"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.mode = soils_module.SoilsMode.Gridded
            self.single_selection: int | None = None
            self.single_dbselection: str | None = None
            self.ksflag: bool | None = None

        @classmethod
        def getInstance(cls, wd: str) -> "DummySoils":
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

    monkeypatch.setattr(soils_module, "Soils", DummySoils)
    monkeypatch.setattr(soils_module, "soil_capability_modes", lambda soils: None)

    class DummyDisturbed:
        _instances: Dict[str, "DummyDisturbed"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.sol_ver: float | None = None

        @classmethod
        def getInstance(cls, wd: str) -> "DummyDisturbed":
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

    monkeypatch.setattr(soils_module, "Disturbed", DummyDisturbed)

    with app.test_client() as client:
        yield client, DummySoils, DummyDisturbed, str(run_dir)

    DummySoils._instances.clear()
    DummyDisturbed._instances.clear()


def test_set_soil_mode_updates_controller(soils_client):
    client, DummySoils, _, run_dir = soils_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_soil_mode/",
        json={
            "mode": int(soils_module.SoilsMode.UserDefined),
            "soil_single_selection": 404,
            "soil_single_dbselection": "DB1",
        },
    )

    assert response.status_code == 200
    assert response.get_json() == {}

    controller = DummySoils.getInstance(run_dir)
    assert controller.mode == soils_module.SoilsMode.UserDefined
    assert controller.single_selection == 404
    assert controller.single_dbselection == "DB1"


def test_set_soil_mode_rejects_stored_graph_mismatch_before_mutation(
    soils_client, monkeypatch: pytest.MonkeyPatch,
):
    client, DummySoils, _, run_dir = soils_client
    monkeypatch.setattr(
        soils_module,
        "soil_capability_modes",
        lambda soils: frozenset({int(soils_module.SoilsMode.Gridded)}),
    )
    controller = DummySoils.getInstance(run_dir)

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_soil_mode/",
        json={"mode": int(soils_module.SoilsMode.Single)},
    )

    assert response.status_code >= 400
    assert controller.mode == soils_module.SoilsMode.Gridded


def test_set_soil_mode_allows_exact_current_mode_outside_authority(
    soils_client, monkeypatch: pytest.MonkeyPatch,
):
    client, DummySoils, _, run_dir = soils_client
    monkeypatch.setattr(
        soils_module,
        "soil_capability_modes",
        lambda _soils: frozenset({int(soils_module.SoilsMode.Single)}),
    )
    controller = DummySoils.getInstance(run_dir)

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_soil_mode/",
        json={"mode": int(controller.mode)},
    )

    assert response.status_code == 200
    assert controller.mode == soils_module.SoilsMode.Gridded


def test_task_set_soils_ksflag_sets_boolean(soils_client):
    client, DummySoils, _, run_dir = soils_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_soils_ksflag/",
        json={"ksflag": True},
    )

    assert response.status_code == 200
    assert response.get_json() == {}

    controller = DummySoils.getInstance(run_dir)
    assert controller.ksflag is True


def test_task_set_disturbed_sol_ver_updates_controller(soils_client):
    client, _, DummyDisturbed, run_dir = soils_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_disturbed_sol_ver/",
        json={"sol_ver": "9002.0"},
    )

    assert response.status_code == 200
    assert response.get_json() == {}

    controller = DummyDisturbed.getInstance(run_dir)
    assert controller.sol_ver == pytest.approx(9002.0)
