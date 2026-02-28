from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("flask")
from flask import Flask

from tests.factories.singleton import singleton_factory
from wepppy.runtime_paths.errors import NoDirError

import wepppy.weppcloud.routes.nodb_api.watar_bp as watar_module

import wepppy.climates.cligen as cligen_module
import wepppy.nodb.mods.ash_transport.ash_multi_year_model as ash_models
import wepppy.weppcloud.utils.helpers as helpers

pytestmark = pytest.mark.routes

RUN_ID = "test-run"
CONFIG = "cfg"


@pytest.fixture()
def watar_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    run_dir = tmp_path / RUN_ID
    climate_dir = run_dir / "climate"
    climate_dir.mkdir(parents=True)
    cli_path = climate_dir / "station.cli"
    cli_path.write_text("station\n", encoding="ascii")

    monkeypatch.setattr(helpers, "authorize", lambda *args, **kwargs: None)
    monkeypatch.setattr(watar_module, "get_wd", lambda runid: str(run_dir))
    monkeypatch.setattr(watar_module, "get_run_owners_lazy", lambda runid: [])
    monkeypatch.setattr(watar_module, "current_user", SimpleNamespace(has_role=lambda _role: False))

    RonStub = singleton_factory("RonWatarStub", attrs={"public": True})
    UnitizerStub = singleton_factory("UnitizerWatarStub", attrs={})
    WeppStub = singleton_factory("WeppWatarStub", attrs={"output_dir": str(run_dir / "wepp_output")})
    AshStub = singleton_factory("AshWatarStub", attrs={})

    class ClimateStub:
        _instances: dict[str, "ClimateStub"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.cli_path = str(cli_path)

        @classmethod
        def getInstance(cls, wd: str) -> "ClimateStub":
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

        @classmethod
        def reset_instances(cls) -> None:
            cls._instances.clear()

    class WatershedStub:
        _instances: dict[str, "WatershedStub"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd

        @classmethod
        def getInstance(cls, wd: str) -> "WatershedStub":
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

        @classmethod
        def reset_instances(cls) -> None:
            cls._instances.clear()

        def translator_factory(self):
            return SimpleNamespace(wepp=lambda top: 17)

        def sub_summary(self, top):
            return {"topaz_id": str(top)}

    monkeypatch.setattr(watar_module, "Ron", RonStub)
    monkeypatch.setattr(watar_module, "Unitizer", UnitizerStub)
    monkeypatch.setattr(watar_module, "Watershed", WatershedStub)
    monkeypatch.setattr(watar_module, "Climate", ClimateStub)
    monkeypatch.setattr(watar_module, "Wepp", WeppStub)
    monkeypatch.setattr(watar_module, "Ash", AshStub)

    monkeypatch.setattr(watar_module, "load_hill_wat_dataframe", lambda *args, **kwargs: {"daily": True})
    monkeypatch.setattr(watar_module, "render_template", lambda template, **context: "rendered")
    monkeypatch.setattr(watar_module.wepppy.nodb.unitizer, "precisions", {"depth": 2}, raising=False)

    climate_file_paths: list[str] = []

    class DummyClimateFile:
        def __init__(self, src_path: str) -> None:
            self._src_path = src_path
            climate_file_paths.append(src_path)

        def as_dataframe(self):
            return {"src_path": self._src_path}

    monkeypatch.setattr(cligen_module, "ClimateFile", DummyClimateFile)

    class DummyBlackAshModel:
        def run_model(self, *_args, **_kwargs):
            return None, [{"status": "ok"}], [{"year": 1}]

    class DummyWhiteAshModel:
        def run_model(self, *_args, **_kwargs):
            return None, [{"status": "ok"}], [{"year": 1}]

    monkeypatch.setattr(ash_models, "BlackAshModel", DummyBlackAshModel)
    monkeypatch.setattr(ash_models, "WhiteAshModel", DummyWhiteAshModel)

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(watar_module.watar_bp)

    with app.test_client() as client:
        yield client, run_dir, climate_file_paths

    RonStub.reset_instances()
    UnitizerStub.reset_instances()
    WeppStub.reset_instances()
    AshStub.reset_instances()
    ClimateStub.reset_instances()
    WatershedStub.reset_instances()


def test_hillslope0_ash_uses_projected_cli_path(
    watar_client,
    monkeypatch: pytest.MonkeyPatch,
):
    client, run_dir, climate_file_paths = watar_client

    projection_calls: list[tuple[str, str, str]] = []
    projected_path = str(run_dir / "_proj" / "station.cli")

    @contextmanager
    def _with_input_file_path(wd: str, rel: str, *, purpose: str):
        projection_calls.append((wd, rel, purpose))
        yield projected_path

    monkeypatch.setattr(watar_module, "with_input_file_path", _with_input_file_path)

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/hillslope/11/ash/")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "rendered"
    assert projection_calls == [
        (str(run_dir), "climate/station.cli", "ash-hillslope-climate-cli"),
    ]
    assert climate_file_paths == [projected_path]


def test_hillslope0_ash_handles_nodir_locked(
    watar_client,
    monkeypatch: pytest.MonkeyPatch,
):
    client, _run_dir, climate_file_paths = watar_client

    @contextmanager
    def _raise_locked(_wd: str, _rel: str, *, purpose: str):
        raise NoDirError(http_status=423, code="NODIR_LOCKED", message="root is locked")
        yield purpose

    monkeypatch.setattr(watar_module, "with_input_file_path", _raise_locked)

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/hillslope/11/ash/")

    assert response.status_code == 423
    payload = response.get_json()
    assert payload["error"]["code"] == "NODIR_LOCKED"
    assert payload["error"]["message"] == "root is locked"
    assert climate_file_paths == []
