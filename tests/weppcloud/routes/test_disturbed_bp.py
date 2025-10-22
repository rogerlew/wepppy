from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Tuple

import pytest

pytest.importorskip("flask")
from flask import Flask, Response

import wepppy.weppcloud.routes.nodb_api.disturbed_bp as disturbed_module

RUN_ID = "test-run"
CONFIG = "cfg"


@pytest.fixture()
def disturbed_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Provide a Flask client with stubbed disturbed/BAER controllers."""

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(disturbed_module.disturbed_bp)

    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()

    context = SimpleNamespace(active_root=run_dir)

    monkeypatch.setattr(
        disturbed_module,
        "load_run_context",
        lambda runid, config: context,
    )

    helpers = __import__("wepppy.weppcloud.utils.helpers", fromlist=["authorize"])
    monkeypatch.setattr(helpers, "authorize", lambda runid, config, require_owner=False: None)

    dispatched: Dict[str, Any] = {}

    class DummyDisturbed:
        _instances: Dict[str, "DummyDisturbed"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.has_sbs = True
            self.has_map = True
            self.bounds = {"xmin": 0, "xmax": 1}
            self.classes = {"low": 1, "high": 4}
            self.baer_rgb_png = str(run_dir / "baer.png")
            Path(self.baer_rgb_png).write_bytes(b"png")
            self.baer_dir = str(run_dir / "baer")
            Path(self.baer_dir).mkdir(exist_ok=True)
            self.lookup_fn = str(run_dir / "lookup.csv")
            Path(self.lookup_fn).write_text("")
            self.fire_date = None
            self.color_map_updates: List[Dict[Tuple[int, int, int], Any]] = []
            self.burn_class_updates: List[Tuple[Any, Any]] = []
            self.sbs_removed = 0
            self.uniform_values: List[int] = []
            self.validated: List[str] = []

        @classmethod
        def getInstance(cls, wd: str) -> "DummyDisturbed":
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

        def reset_land_soil_lookup(self) -> None:
            dispatched["reset_called"] = True

        def build_extended_land_soil_lookup(self) -> None:
            dispatched["extended_lookup"] = True

        def modify_burn_class(self, classes, nodata_vals) -> None:
            self.burn_class_updates.append((classes, nodata_vals))

        def modify_color_map(self, color_map) -> None:
            self.color_map_updates.append(color_map)

        def validate(self, filename: str) -> Dict[str, str]:
            self.validated.append(filename)
            return {"validated": filename}

        def build_uniform_sbs(self, value: int) -> str:
            self.uniform_values.append(value)
            output = Path(self.baer_dir) / f"uniform_{value}.tif"
            output.write_text("sbs")
            return str(output)

        def remove_sbs(self) -> None:
            self.sbs_removed += 1

    class DummyBaer(DummyDisturbed):
        pass

    class DummyRon:
        _instances: Dict[str, "DummyRon"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.mods = ["baer"]

        @classmethod
        def getInstance(cls, wd: str) -> "DummyRon":
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

    monkeypatch.setattr(disturbed_module, "Disturbed", DummyDisturbed)
    monkeypatch.setattr(disturbed_module, "Baer", DummyBaer)
    monkeypatch.setattr(disturbed_module, "Ron", DummyRon)

    def fake_render_template(template: str, **context: Any) -> str:
        dispatched["template"] = template
        dispatched["template_context"] = context
        return "rendered"

    monkeypatch.setattr(disturbed_module, "render_template", fake_render_template)

    def fake_send_file(path: str, mimetype: str) -> Response:
        dispatched["send_file"] = (path, mimetype)
        return Response("file", mimetype=mimetype)

    monkeypatch.setattr(disturbed_module, "send_file", fake_send_file)

    def fake_write_lookup(path: str, data: Any) -> None:
        dispatched["write_lookup"] = (path, data)

    monkeypatch.setattr(disturbed_module, "write_disturbed_land_soil_lookup", fake_write_lookup)

    with app.test_client() as client:
        yield client, DummyDisturbed, DummyBaer, DummyRon, dispatched, str(run_dir)

    DummyDisturbed._instances.clear()
    DummyBaer._instances.clear()
    DummyRon._instances.clear()


def test_has_sbs_endpoint(disturbed_client):
    client, *_ = disturbed_client
    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/disturbed/has_sbs")
    assert response.status_code == 200
    assert response.get_json() == {"has_sbs": True}


def test_task_modify_disturbed_writes_lookup(disturbed_client):
    client, DummyDisturbed, _, _, dispatched, run_dir = disturbed_client
    payload = {"rows": [{"id": 1}]}
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_disturbed",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.get_json()["Success"] is True
    lookup_path, data = dispatched["write_lookup"]
    assert lookup_path == DummyDisturbed.getInstance(run_dir).lookup_fn
    assert data == payload


def test_query_baer_wgs_map_returns_metadata(disturbed_client):
    client, *_ = disturbed_client
    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/query/baer_wgs_map")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Success"] is True
    content = payload["Content"]
    assert content["imgurl"] == "resources/baer.png"
    assert "bounds" in content


def test_task_baer_modify_color_map_converts_keys(disturbed_client):
    client, _, DummyBaer, DummyRon, _, run_dir = disturbed_client
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_color_map",
        json={"color_map": {"255_0_0": "High"}},
    )
    assert response.status_code == 200
    assert response.get_json()["Success"] is True
    controller = DummyBaer.getInstance(run_dir)
    assert controller.color_map_updates[-1] == {(255, 0, 0): "High"}


def test_task_baer_modify_class_parses_integers(disturbed_client):
    client, _, DummyBaer, DummyRon, _, run_dir = disturbed_client
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_burn_class",
        json={"classes": ["1", "2", "3", "4"], "nodata_vals": "999"},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Success"] is True
    controller = DummyBaer.getInstance(run_dir)
    assert controller.burn_class_updates[-1] == ([1, 2, 3, 4], "999")


def test_task_baer_modify_class_requires_four_values(disturbed_client):
    client, *_ = disturbed_client
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_burn_class",
        json={"classes": [1, 2, 3]},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Success"] is False
    assert "four" in payload["Error"].lower()


def test_resources_baer_sbs_uses_send_file(disturbed_client):
    client, DummyDisturbed, DummyBaer, DummyRon, dispatched, run_dir = disturbed_client
    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/resources/baer.png")
    assert response.status_code == 200
    assert response.get_data(as_text=True) == "file"
    path, mimetype = dispatched["send_file"]
    assert path == DummyBaer.getInstance(run_dir).baer_rgb_png
    assert mimetype == "image/png"


def test_set_firedate_updates_controller(disturbed_client):
    client, DummyDisturbed, *_ , run_dir = disturbed_client
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_firedate/",
        json={"fire_date": "2024-09-01"},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Success"] is True
    controller = DummyDisturbed.getInstance(run_dir)
    assert controller.fire_date == "2024-09-01"


def test_set_firedate_updates_controller(disturbed_client):
    client, DummyDisturbed, *_rest, run_dir = disturbed_client
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_firedate/",
        json={"fire_date": "8/4"},
    )
    assert response.status_code == 200
    assert response.get_json()["Success"] is True
    controller = DummyDisturbed.getInstance(run_dir)
    assert controller.fire_date == "8/4"


def test_task_remove_sbs_calls_baer(disturbed_client):
    client, DummyDisturbed, DummyBaer, DummyRon, _, run_dir = disturbed_client
    response = client.post(f"/runs/{RUN_ID}/{CONFIG}/tasks/remove_sbs")
    assert response.status_code == 200
    assert response.get_json()["Success"] is True
    controller = DummyBaer.getInstance(run_dir)
    assert controller.sbs_removed == 1


def test_task_build_uniform_sbs_runs_validation(disturbed_client):
    client, DummyDisturbed, DummyBaer, DummyRon, _, run_dir = disturbed_client
    response = client.post(f"/runs/{RUN_ID}/{CONFIG}/tasks/build_uniform_sbs/7")
    assert response.status_code == 200
    assert response.get_json()["Success"] is True
    controller = DummyDisturbed.getInstance(run_dir)
    assert controller.uniform_values[-1] == 7
    assert controller.validated[-1].endswith("uniform_7.tif")
