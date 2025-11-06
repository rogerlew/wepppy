from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict

import pytest

pytest.importorskip("flask")
from flask import Flask, Response

import wepppy.weppcloud.routes.nodb_api.disturbed_bp as disturbed_module
from tests.factories.singleton import LockedMixin, singleton_factory

pytestmark = pytest.mark.routes

RUN_ID = "test-run"
CONFIG = "cfg"


@pytest.fixture()
def disturbed_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    rq_environment,
):
    """Provide a Flask client with stubbed disturbed/BAER controllers."""

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(disturbed_module.disturbed_bp)

    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()

    baer_dir = run_dir / "baer"
    baer_dir.mkdir()
    baer_png = run_dir / "baer.png"
    baer_png.write_bytes(b"png")
    lookup_csv = run_dir / "lookup.csv"
    lookup_csv.write_text("")

    context = SimpleNamespace(active_root=run_dir)

    monkeypatch.setattr(
        disturbed_module,
        "load_run_context",
        lambda runid, config: context,
    )

    helpers = __import__("wepppy.weppcloud.utils.helpers", fromlist=["authorize"])
    monkeypatch.setattr(helpers, "authorize", lambda runid, config, require_owner=False: None)

    dispatched: Dict[str, Any] = {"reset_called": 0, "extended_lookup": 0}

    def make_controller_stub(name: str):
        def reset_land_soil_lookup(self) -> None:
            dispatched["reset_called"] = dispatched.get("reset_called", 0) + 1

        def build_extended_land_soil_lookup(self) -> None:
            dispatched["extended_lookup"] = dispatched.get("extended_lookup", 0) + 1

        def modify_burn_class(self, classes, nodata_vals) -> None:
            self.burn_class_updates.append((classes, nodata_vals))

        def modify_color_map(self, color_map) -> None:
            self.color_map_updates.append(color_map)

        def validate(self, filename: str, *args: Any, **kwargs: Any) -> Dict[str, str]:
            mode = kwargs.get("mode")
            severity = kwargs.get("uniform_severity")
            if mode is not None:
                self.sbs_mode = mode
                if mode == 0 and severity is None:
                    self.uniform_severity = None
            if severity is not None:
                self.uniform_severity = severity
            if hasattr(self, "disturbed_fn"):
                self.disturbed_fn = filename
            if hasattr(self, "baer_fn"):
                self.baer_fn = filename
            self.validated.append(filename)
            return {"validated": filename}

        def build_uniform_sbs(self, severity: int) -> str:
            self.uniform_values.append(severity)
            output = Path(self.baer_dir) / f"uniform_{severity}.tif"
            output.write_text("sbs")
            return str(output)

        def remove_sbs(self) -> None:
            self.sbs_removed += 1

        methods = {
            "reset_land_soil_lookup": reset_land_soil_lookup,
            "build_extended_land_soil_lookup": build_extended_land_soil_lookup,
            "modify_burn_class": modify_burn_class,
            "modify_color_map": modify_color_map,
            "validate": validate,
            "build_uniform_sbs": build_uniform_sbs,
            "remove_sbs": remove_sbs,
        }

        attrs = {
            "has_sbs": True,
            "has_map": True,
            "bounds": {"xmin": 0, "xmax": 1},
            "classes": {"low": 1, "high": 4},
            "baer_rgb_png": "",
            "baer_dir": "",
            "lookup_fn": "",
            "fire_date": None,
            "color_map_updates": [],
            "burn_class_updates": [],
            "sbs_removed": 0,
            "uniform_values": [],
            "validated": [],
            "sbs_mode": 0,
            "uniform_severity": None,
            "disturbed_fn": None,
            "baer_fn": None,
        }

        return singleton_factory(name, attrs=attrs, methods=methods, mixins=(LockedMixin,))

    DisturbedStub = make_controller_stub("DisturbedStub")
    BaerStub = make_controller_stub("BaerStub")
    RonStub = singleton_factory(
        "RonStub",
        attrs={"mods": ["baer"]},
    )

    disturbed_instance = DisturbedStub.getInstance(str(run_dir))
    baer_instance = BaerStub.getInstance(str(run_dir))

    for controller in (disturbed_instance, baer_instance):
        controller.baer_rgb_png = str(baer_png)
        controller.baer_dir = str(baer_dir)
        controller.lookup_fn = str(lookup_csv)

    monkeypatch.setattr(disturbed_module, "Disturbed", DisturbedStub)
    monkeypatch.setattr(disturbed_module, "Baer", BaerStub)
    monkeypatch.setattr(disturbed_module, "Ron", RonStub)
    monkeypatch.setattr(disturbed_module, "RedisPrep", rq_environment.redis_prep_class, raising=False)

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
        yield client, DisturbedStub, BaerStub, RonStub, dispatched, str(run_dir)

    DisturbedStub.reset_instances()
    BaerStub.reset_instances()
    RonStub.reset_instances()


def test_has_sbs_endpoint(disturbed_client):
    client, *_ = disturbed_client
    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/disturbed/has_sbs")
    assert response.status_code == 200
    assert response.get_json() == {"has_sbs": True}


def test_reset_disturbed_parameters_uses_post(disturbed_client):
    client, *_, dispatched, _ = disturbed_client
    response = client.post(f"/runs/{RUN_ID}/{CONFIG}/tasks/reset_disturbed")
    assert response.status_code == 200
    assert response.get_json()["Success"] is True
    assert dispatched["reset_called"] == 1


def test_load_extended_lookup_uses_post(disturbed_client):
    client, *_, dispatched, _ = disturbed_client
    response = client.post(f"/runs/{RUN_ID}/{CONFIG}/tasks/load_extended_land_soil_lookup")
    assert response.status_code == 200
    assert response.get_json()["Success"] is True
    assert dispatched["extended_lookup"] == 1


def test_task_modify_disturbed_writes_lookup(disturbed_client):
    client, DisturbedStub, _, _, dispatched, run_dir = disturbed_client
    payload = {"rows": [{"id": 1}]}
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_disturbed",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.get_json()["Success"] is True
    lookup_path, data = dispatched["write_lookup"]
    assert lookup_path == DisturbedStub.getInstance(run_dir).lookup_fn
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
    client, _, BaerStub, RonStub, _, run_dir = disturbed_client
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_color_map",
        json={"color_map": {"255_0_0": "High"}},
    )
    assert response.status_code == 200
    assert response.get_json()["Success"] is True
    controller = BaerStub.getInstance(run_dir)
    assert controller.color_map_updates[-1] == {(255, 0, 0): "High"}


def test_task_baer_modify_class_parses_integers(disturbed_client):
    client, _, BaerStub, RonStub, _, run_dir = disturbed_client
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_burn_class",
        json={"classes": ["1", "2", "3", "4"], "nodata_vals": "999"},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Success"] is True
    controller = BaerStub.getInstance(run_dir)
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
    client, DisturbedStub, BaerStub, RonStub, dispatched, run_dir = disturbed_client
    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/resources/baer.png")
    assert response.status_code == 200
    assert response.get_data(as_text=True) == "file"
    path, mimetype = dispatched["send_file"]
    assert path == BaerStub.getInstance(run_dir).baer_rgb_png
    assert mimetype == "image/png"


def test_set_firedate_updates_controller(disturbed_client):
    client, DisturbedStub, *_ , run_dir = disturbed_client
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_firedate/",
        json={"fire_date": "2024-09-01"},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Success"] is True
    controller = DisturbedStub.getInstance(run_dir)
    assert controller.fire_date == "2024-09-01"


def test_set_firedate_accepts_short_format(disturbed_client):
    client, DisturbedStub, *_rest, run_dir = disturbed_client
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_firedate/",
        json={"fire_date": "8/4"},
    )
    assert response.status_code == 200
    assert response.get_json()["Success"] is True
    controller = DisturbedStub.getInstance(run_dir)
    assert controller.fire_date == "8/4"


def test_task_remove_sbs_calls_baer(disturbed_client):
    client, DisturbedStub, BaerStub, RonStub, _, run_dir = disturbed_client
    response = client.post(f"/runs/{RUN_ID}/{CONFIG}/tasks/remove_sbs")
    assert response.status_code == 200
    assert response.get_json()["Success"] is True
    controller = BaerStub.getInstance(run_dir)
    assert controller.sbs_removed == 1


def test_task_build_uniform_sbs_runs_validation(disturbed_client):
    client, DisturbedStub, BaerStub, RonStub, _, run_dir = disturbed_client
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/build_uniform_sbs",
        json={"value": 7},
    )
    assert response.status_code == 200
    assert response.get_json()["Success"] is True
    controller = DisturbedStub.getInstance(run_dir)
    assert controller.uniform_values[-1] == 7
    assert controller.validated[-1].endswith("uniform_7.tif")
    assert controller.sbs_mode == 1
    assert controller.uniform_severity == 7
    baer_controller = BaerStub.getInstance(run_dir)
    assert baer_controller.sbs_mode == 1
    assert baer_controller.uniform_severity == 7


def test_task_build_uniform_sbs_accepts_path_value(disturbed_client):
    client, DisturbedStub, BaerStub, RonStub, _, run_dir = disturbed_client
    response = client.post(f"/runs/{RUN_ID}/{CONFIG}/tasks/build_uniform_sbs/9")
    assert response.status_code == 200
    assert response.get_json()["Success"] is True
    controller = DisturbedStub.getInstance(run_dir)
    assert controller.uniform_values[-1] == 9
    assert controller.validated[-1].endswith("uniform_9.tif")
    assert controller.sbs_mode == 1
    assert controller.uniform_severity == 9
    baer_controller = BaerStub.getInstance(run_dir)
    assert baer_controller.sbs_mode == 1
    assert baer_controller.uniform_severity == 9


def test_task_upload_sbs_renames_conflicting_basename(disturbed_client, monkeypatch):
    client, DisturbedStub, BaerStub, RonStub, _, run_dir = disturbed_client
    baer_dir = Path(run_dir) / "baer"
    expected_path = baer_dir / "_baer.cropped.tif"
    assert not expected_path.exists()

    def fake_sanity_check(path: str) -> tuple[int, str]:
        assert path == str(expected_path)
        return 0, "ok"

    monkeypatch.setattr(
        "wepppy.nodb.mods.baer.sbs_map.sbs_map_sanity_check",
        fake_sanity_check,
    )

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/upload_sbs/",
        data={"input_upload_sbs": (BytesIO(b"sbs"), "baer.cropped.tif")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Success"] is True
    assert expected_path.exists()
    controller = BaerStub.getInstance(run_dir)
    assert controller.validated[-1] == expected_path.name
