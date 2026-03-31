from __future__ import annotations

import json
import re
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict

import pytest

pytest.importorskip("flask")
from flask import Flask, Response

import wepppy.weppcloud.routes.nodb_api.disturbed_bp as disturbed_module
from wepppy.nodb.redis_prep import TaskEnum
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
    lookup_csv = run_dir / "disturbed_land_soil_lookup.csv"
    lookup_csv.write_text("")
    extended_lookup_csv = run_dir / "disturbed_land_soil_lookup_extended.csv"

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
            "extended_lookup_fn": "",
            "fire_date": None,
            "color_map_updates": [],
            "burn_class_updates": [],
            "sbs_removed": 0,
            "uniform_values": [],
            "validated": [],
            "sbs_mode": 0,
            "uniform_severity": None,
            "active_lookup_variant": None,
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
        controller.extended_lookup_fn = str(extended_lookup_csv)

    monkeypatch.setattr(disturbed_module, "Disturbed", DisturbedStub)
    monkeypatch.setattr(disturbed_module, "Baer", BaerStub)
    monkeypatch.setattr(disturbed_module, "Ron", RonStub)
    monkeypatch.setattr(disturbed_module, "RedisPrep", rq_environment.redis_prep_class, raising=False)

    def fake_render_template(template: str, **context: Any) -> str:
        dispatched["template"] = template
        dispatched["template_context"] = context
        return "rendered"

    monkeypatch.setattr(disturbed_module, "render_template", fake_render_template)

    def fake_send_file(path: str, mimetype: str, **_kwargs: Any) -> Response:
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
    assert response.get_json() == {}
    assert dispatched["reset_called"] == 1


def test_load_extended_lookup_uses_post(disturbed_client):
    client, *_, dispatched, _ = disturbed_client
    response = client.post(f"/runs/{RUN_ID}/{CONFIG}/tasks/load_extended_land_soil_lookup")
    assert response.status_code == 200
    assert response.get_json() == {}
    assert dispatched["extended_lookup"] == 1


def test_sync_base_to_extended_lookup_uses_post(disturbed_client):
    client, *_, dispatched, _ = disturbed_client
    response = client.post(f"/runs/{RUN_ID}/{CONFIG}/tasks/sync_base_to_extended_land_soil_lookup")
    assert response.status_code == 200
    assert response.get_json() == {}
    assert dispatched["extended_lookup"] == 1


@pytest.mark.parametrize(
    "path",
    [
        "tasks/reset_disturbed",
        "tasks/load_extended_land_soil_lookup",
        "tasks/delete_extended_land_soil_lookup",
        "tasks/sync_base_to_extended_land_soil_lookup",
        "tasks/set_lookup_variant",
    ],
)
def test_lookup_mutation_routes_reject_get(disturbed_client, path: str):
    client, *_ = disturbed_client
    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/{path}")
    assert response.status_code == 405


def test_delete_extended_lookup_removes_file_when_present(disturbed_client):
    client, DisturbedStub, _, _, _dispatched, run_dir = disturbed_client
    disturbed = DisturbedStub.getInstance(run_dir)
    extended_path = Path(disturbed.extended_lookup_fn)
    extended_path.write_text("sev_enum,landuse\n0,forest\n")
    assert extended_path.exists()

    response = client.post(f"/runs/{RUN_ID}/{CONFIG}/tasks/delete_extended_land_soil_lookup")

    assert response.status_code == 200
    assert response.get_json() == {}
    assert not extended_path.exists()


def test_delete_extended_lookup_is_idempotent_when_missing(disturbed_client):
    client, DisturbedStub, _, _, _dispatched, run_dir = disturbed_client
    disturbed = DisturbedStub.getInstance(run_dir)
    extended_path = Path(disturbed.extended_lookup_fn)
    if extended_path.exists():
        extended_path.unlink()

    response = client.post(f"/runs/{RUN_ID}/{CONFIG}/tasks/delete_extended_land_soil_lookup")

    assert response.status_code == 200
    assert response.get_json() == {}
    assert not extended_path.exists()


def test_task_modify_disturbed_writes_lookup(disturbed_client):
    client, DisturbedStub, _, _, dispatched, run_dir = disturbed_client
    meta_response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/disturbed/lookup_meta")
    assert meta_response.status_code == 200
    current_sha = meta_response.get_json()["Content"]["lookup_sha256"]
    payload = {
        "rows": [["forest", "loam", "1", "2", "3", "4", "1", "0", "0", "0"]],
        "if_match_sha256": current_sha,
    }
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_disturbed",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.get_json() == {}
    lookup_path, data = dispatched["write_lookup"]
    assert lookup_path == DisturbedStub.getInstance(run_dir).lookup_fn
    assert data == payload["rows"]


def test_modify_disturbed_route_renders_absolute_urls(disturbed_client):
    client, _DisturbedStub, _BaerStub, _RonStub, dispatched, _run_dir = disturbed_client
    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/modify_disturbed")
    assert response.status_code == 200
    assert response.get_data(as_text=True) == "rendered"
    assert dispatched["template"] == "controls/edit_csv.htm"
    template_context = dispatched["template_context"]
    assert template_context["runid"] == RUN_ID
    assert template_context["config"] == CONFIG
    assert template_context["csv_url"] == (
        f"/runs/{RUN_ID}/{CONFIG}/download/disturbed/disturbed_land_soil_lookup.csv"
    )
    assert template_context["save_url"] == f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_disturbed?lookup=base"
    assert template_context["lookup_meta_url"] == (
        f"/runs/{RUN_ID}/{CONFIG}/api/disturbed/lookup_meta?lookup=base"
    )
    assert template_context["lookup_snapshot_url"] == (
        f"/runs/{RUN_ID}/{CONFIG}/api/disturbed/lookup_snapshot?lookup=base"
    )
    assert template_context["lookup_variant"] == "base"
    assert template_context["session_token_url"] == (
        f"/rq-engine/api/runs/{RUN_ID}/{CONFIG}/session-token"
    )


def test_modify_disturbed_route_prefers_extended_lookup_when_present(disturbed_client):
    client, DisturbedStub, _BaerStub, _RonStub, dispatched, run_dir = disturbed_client
    disturbed = DisturbedStub.getInstance(run_dir)
    Path(disturbed.extended_lookup_fn).write_text(
        "sev_enum,landuse,disturbed_class,stext,plant.data.decfct,plant.data.dropfc,plant.data.bb\n"
        "0,forest,forest,loam,1,1,3.6\n"
    )

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/modify_disturbed")
    assert response.status_code == 200
    assert response.get_data(as_text=True) == "rendered"
    template_context = dispatched["template_context"]
    assert template_context["csv_url"] == (
        f"/runs/{RUN_ID}/{CONFIG}/download/disturbed/disturbed_land_soil_lookup_extended.csv"
    )
    assert template_context["save_url"] == f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_disturbed?lookup=extended"
    assert template_context["lookup_meta_url"] == (
        f"/runs/{RUN_ID}/{CONFIG}/api/disturbed/lookup_meta?lookup=extended"
    )
    assert template_context["lookup_snapshot_url"] == (
        f"/runs/{RUN_ID}/{CONFIG}/api/disturbed/lookup_snapshot?lookup=extended"
    )
    assert template_context["lookup_variant"] == "extended"


def test_modify_disturbed_route_errors_when_explicit_extended_missing(disturbed_client):
    client, *_ = disturbed_client
    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/modify_disturbed?lookup=extended")
    assert response.status_code == 409
    payload = response.get_json()
    assert payload["error"]["code"] == "LOOKUP_VARIANT_UNAVAILABLE"


def test_modify_disturbed_page_emits_csrf_token_for_save(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    pytest.importorskip("flask_wtf")
    from flask import jsonify
    from flask_wtf.csrf import CSRFError, CSRFProtect

    template_dir = Path(__file__).resolve().parents[3] / "wepppy" / "weppcloud" / "templates"
    app = Flask(__name__, template_folder=str(template_dir))
    app.config["TESTING"] = True
    app.secret_key = "csrf-test-secret"
    CSRFProtect(app)
    app.register_blueprint(disturbed_module.disturbed_bp)

    @app.errorhandler(CSRFError)
    def csrf_error(_exc):
        return jsonify({"error": {"message": "csrf failed"}}), 400

    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()
    lookup_csv = run_dir / "disturbed_land_soil_lookup.csv"
    lookup_csv.write_text("")
    context = SimpleNamespace(active_root=run_dir)
    monkeypatch.setattr(disturbed_module, "load_run_context", lambda runid, config: context)

    disturbed_instance = SimpleNamespace(lookup_fn=str(lookup_csv))

    class DisturbedStub:
        @classmethod
        def getInstance(cls, wd: str):
            return disturbed_instance

    @contextmanager
    def disturbed_lock():
        yield

    disturbed_instance.locked = disturbed_lock
    disturbed_instance.lock = lambda: None
    disturbed_instance.unlock = lambda flag=None: None
    disturbed_instance.readonly = False

    monkeypatch.setattr(disturbed_module, "Disturbed", DisturbedStub)

    captured: Dict[str, Any] = {}

    def fake_write_lookup(path: str, rows: Any) -> None:
        captured["path"] = path
        captured["rows"] = rows

    monkeypatch.setattr(disturbed_module, "write_disturbed_land_soil_lookup", fake_write_lookup)

    with app.test_client() as client:
        page_response = client.get(f"/runs/{RUN_ID}/{CONFIG}/modify_disturbed")
        assert page_response.status_code == 200
        html = page_response.get_data(as_text=True)
        token_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', html)
        assert token_match is not None
        token = token_match.group(1)
        assert token
        assert "X-CSRFToken" in html
        assert f'data-csv-url="/runs/{RUN_ID}/{CONFIG}/download/disturbed/disturbed_land_soil_lookup.csv"' in html
        assert f'data-save-url="/runs/{RUN_ID}/{CONFIG}/tasks/modify_disturbed?lookup=base"' in html
        assert f'data-lookup-meta-url="/runs/{RUN_ID}/{CONFIG}/api/disturbed/lookup_meta?lookup=base"' in html
        assert f'data-lookup-snapshot-url="/runs/{RUN_ID}/{CONFIG}/api/disturbed/lookup_snapshot?lookup=base"' in html
        assert f'data-session-token-url="/rq-engine/api/runs/{RUN_ID}/{CONFIG}/session-token"' in html
        assert 'id="reload-current"' in html
        assert 'id="refresh-page"' not in html
        assert 'cache: "no-store"' in html
        assert 'recoveryAttempt: true' in html
        assert 'PRECONDITION_REQUIRED' in html
        assert 'LOOKUP_VERSION_UNAVAILABLE' in html

        meta_response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/disturbed/lookup_meta")
        assert meta_response.status_code == 200
        current_sha = meta_response.get_json()["Content"]["lookup_sha256"]

        rejected_response = client.post(
            f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_disturbed",
            json=[["forest", "loam"]],
        )
        assert rejected_response.status_code == 400

        accepted_response = client.post(
            f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_disturbed",
            json=[["forest", "loam"]],
            headers={
                "X-CSRFToken": token,
                "X-If-Match-Sha256": current_sha,
            },
        )
        assert accepted_response.status_code == 200
        assert accepted_response.get_json() == {}

    assert captured["path"] == str(lookup_csv)
    assert captured["rows"] == [["forest", "loam"]]


def test_query_baer_wgs_map_returns_metadata(disturbed_client):
    client, *_ = disturbed_client
    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/query/baer_wgs_map")
    assert response.status_code == 200
    payload = response.get_json()
    content = payload["Content"]
    assert content["imgurl"] == "resources/baer.png"
    assert "bounds" in content


def test_task_modify_disturbed_rejects_empty_rows(disturbed_client):
    client, *_ = disturbed_client
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_disturbed",
        json=[],
    )
    assert response.status_code == 400
    payload = response.get_json()
    assert "non-empty list" in payload["error"]["message"].lower()


def test_lookup_meta_returns_sha_and_shape(disturbed_client):
    client, *_ = disturbed_client
    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/disturbed/lookup_meta")
    assert response.status_code == 200
    assert response.headers["Cache-Control"].startswith("no-store")
    payload = response.get_json()
    content = payload["Content"]
    assert content["lookup_sha256"]
    assert content["has_extended_lookup"] is False
    assert isinstance(content["columns"], int)
    assert isinstance(content["rows"], int)


def test_lookup_meta_reports_extended_available_when_present(disturbed_client):
    client, DisturbedStub, _, _, _dispatched, run_dir = disturbed_client
    disturbed = DisturbedStub.getInstance(run_dir)
    Path(disturbed.extended_lookup_fn).write_text(
        "sev_enum,landuse,disturbed_class,stext\n0,forest,forest,loam\n"
    )

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/disturbed/lookup_meta")
    assert response.status_code == 200
    content = response.get_json()["Content"]
    assert content["has_extended_lookup"] is True


def test_lookup_meta_errors_when_explicit_extended_missing(disturbed_client):
    client, *_ = disturbed_client
    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/disturbed/lookup_meta?lookup=extended")
    assert response.status_code == 409
    payload = response.get_json()
    assert payload["error"]["code"] == "LOOKUP_VARIANT_UNAVAILABLE"


def test_lookup_snapshot_returns_csv_and_sha(disturbed_client):
    client, *_ = disturbed_client
    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/disturbed/lookup_snapshot")
    assert response.status_code == 200
    assert response.headers["Cache-Control"].startswith("no-store")
    payload = response.get_json()
    content = payload["Content"]
    assert isinstance(content["csv_text"], str)
    assert content["lookup_sha256"]
    assert content["lookup_variant"] == "base"
    assert content["has_extended_lookup"] is False
    assert isinstance(content["rows"], int)
    assert isinstance(content["columns"], int)


def test_lookup_snapshot_errors_when_explicit_extended_missing(disturbed_client):
    client, *_ = disturbed_client
    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/disturbed/lookup_snapshot?lookup=extended")
    assert response.status_code == 409
    payload = response.get_json()
    assert payload["error"]["code"] == "LOOKUP_VARIANT_UNAVAILABLE"


def test_lookup_snapshot_prefers_extended_when_present(disturbed_client):
    client, DisturbedStub, _, _, _dispatched, run_dir = disturbed_client
    disturbed = DisturbedStub.getInstance(run_dir)
    Path(disturbed.lookup_fn).write_text("luse,stext,plant.data.decfct,plant.data.dropfc\nforest,loam,1,1\n")
    Path(disturbed.extended_lookup_fn).write_text(
        "sev_enum,landuse,disturbed_class,stext,plant.data.decfct,plant.data.dropfc,plant.data.bb\n"
        "0,forest,forest,loam,1,1,3.6\n"
    )

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/disturbed/lookup_snapshot")
    assert response.status_code == 200
    payload = response.get_json()
    content = payload["Content"]
    assert content["lookup_variant"] == "extended"
    assert content["has_extended_lookup"] is True
    assert content["columns"] == 7
    assert "plant.data.bb" in content["csv_text"].splitlines()[0]


def test_lookup_snapshot_honors_lookup_base_query_when_extended_exists(disturbed_client):
    client, DisturbedStub, _, _, _dispatched, run_dir = disturbed_client
    disturbed = DisturbedStub.getInstance(run_dir)
    Path(disturbed.lookup_fn).write_text("luse,stext,plant.data.decfct,plant.data.dropfc\nforest,loam,1,1\n")
    Path(disturbed.extended_lookup_fn).write_text(
        "sev_enum,landuse,disturbed_class,stext,plant.data.decfct,plant.data.dropfc,plant.data.bb\n"
        "0,forest,forest,loam,1,1,3.6\n"
    )

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/disturbed/lookup_snapshot?lookup=base")
    assert response.status_code == 200
    payload = response.get_json()
    content = payload["Content"]
    assert content["lookup_variant"] == "base"
    assert content["columns"] == 4
    assert "plant.data.bb" not in content["csv_text"].splitlines()[0]


def test_set_lookup_variant_persists_selection_in_controller_state(disturbed_client):
    client, DisturbedStub, _, _, _dispatched, run_dir = disturbed_client
    disturbed = DisturbedStub.getInstance(run_dir)
    Path(disturbed.lookup_fn).write_text("luse,stext,plant.data.decfct,plant.data.dropfc\nforest,loam,1,1\n")
    Path(disturbed.extended_lookup_fn).write_text(
        "sev_enum,landuse,disturbed_class,stext,plant.data.decfct,plant.data.dropfc,plant.data.bb\n"
        "0,forest,forest,loam,1,1,3.6\n"
    )
    disturbed.active_lookup_variant = "base"

    set_response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_lookup_variant",
        json={"lookup_variant": "extended"},
    )
    assert set_response.status_code == 200
    set_payload = set_response.get_json()["Content"]
    assert set_payload["requested_lookup_variant"] == "extended"
    assert set_payload["lookup_variant"] == "extended"
    assert set_payload["has_extended_lookup"] is True
    assert disturbed.active_lookup_variant == "extended"

    meta_response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/disturbed/lookup_meta")
    assert meta_response.status_code == 200
    assert meta_response.get_json()["Content"]["lookup_variant"] == "extended"

    base_response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_lookup_variant",
        json={"lookup_variant": "base"},
    )
    assert base_response.status_code == 200
    assert disturbed.active_lookup_variant == "base"

    snapshot_response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/disturbed/lookup_snapshot")
    assert snapshot_response.status_code == 200
    snapshot_payload = snapshot_response.get_json()["Content"]
    assert snapshot_payload["lookup_variant"] == "base"
    assert snapshot_payload["columns"] == 4


def test_set_lookup_variant_rejects_invalid_payload(disturbed_client):
    client, *_ = disturbed_client
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_lookup_variant",
        json={"lookup_variant": "not-valid"},
    )
    assert response.status_code == 400
    payload = response.get_json()
    assert "lookup_variant" in payload["error"]["message"]


def test_set_lookup_variant_rejects_extended_when_missing(disturbed_client):
    client, *_ = disturbed_client
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_lookup_variant",
        json={"lookup_variant": "extended"},
    )
    assert response.status_code == 409
    payload = response.get_json()
    assert payload["error"]["code"] == "LOOKUP_VARIANT_UNAVAILABLE"


def test_task_modify_disturbed_rejects_missing_if_match(disturbed_client):
    client, *_ = disturbed_client
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_disturbed",
        json={"rows": [["forest", "loam", "1", "2", "3", "4", "1", "0", "0", "0"]]},
    )
    assert response.status_code == 428
    payload = response.get_json()
    assert "if_match_sha256" in payload["error"]["message"]


def test_task_modify_disturbed_accepts_dict_payload_if_match_header(disturbed_client):
    client, DisturbedStub, _, _, dispatched, run_dir = disturbed_client
    meta_response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/disturbed/lookup_meta")
    assert meta_response.status_code == 200
    current_sha = meta_response.get_json()["Content"]["lookup_sha256"]

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_disturbed",
        json={"rows": [["forest", "loam", "1", "2", "3", "4", "1", "0", "0", "0"]]},
        headers={"X-If-Match-Sha256": current_sha},
    )
    assert response.status_code == 200
    assert response.get_json() == {}
    lookup_path, data = dispatched["write_lookup"]
    assert lookup_path == DisturbedStub.getInstance(run_dir).lookup_fn
    assert data == [["forest", "loam", "1", "2", "3", "4", "1", "0", "0", "0"]]


def test_task_modify_disturbed_rejects_stale_if_match(disturbed_client):
    client, *_ = disturbed_client
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_disturbed",
        json={
            "rows": [["forest", "loam", "1", "2", "3", "4", "1", "0", "0", "0"]],
            "if_match_sha256": "stale-hash",
        },
    )
    assert response.status_code == 409
    payload = response.get_json()
    assert payload["error"]["code"] == "STALE_LOOKUP"


def test_task_modify_disturbed_accepts_matching_if_match(disturbed_client):
    client, DisturbedStub, _, _, dispatched, run_dir = disturbed_client
    meta_response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/disturbed/lookup_meta")
    assert meta_response.status_code == 200
    current_sha = meta_response.get_json()["Content"]["lookup_sha256"]

    payload = {
        "rows": [["forest", "loam", "1", "2", "3", "4", "1", "0", "0", "0"]],
        "if_match_sha256": current_sha,
    }
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_disturbed",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.get_json() == {}
    assert response.headers["X-Lookup-Sha256"]
    lookup_path, data = dispatched["write_lookup"]
    assert lookup_path == DisturbedStub.getInstance(run_dir).lookup_fn
    assert data == payload["rows"]


def test_task_modify_disturbed_writes_extended_lookup_when_present(disturbed_client):
    client, DisturbedStub, _, _, dispatched, run_dir = disturbed_client
    disturbed = DisturbedStub.getInstance(run_dir)
    Path(disturbed.extended_lookup_fn).write_text(
        "sev_enum,landuse,disturbed_class,stext,plant.data.decfct,plant.data.dropfc,plant.data.bb\n"
        "0,forest,forest,loam,1,1,3.6\n"
    )

    meta_response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/disturbed/lookup_meta")
    assert meta_response.status_code == 200
    assert meta_response.get_json()["Content"]["lookup_variant"] == "extended"
    current_sha = meta_response.get_json()["Content"]["lookup_sha256"]

    payload = {
        "rows": [["0", "forest", "forest", "loam", "1", "1", "4.1"]],
        "if_match_sha256": current_sha,
    }
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_disturbed",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.get_json() == {}
    assert response.headers["X-Lookup-Variant"] == "extended"
    lookup_path, data = dispatched["write_lookup"]
    assert lookup_path == disturbed.extended_lookup_fn
    assert data == payload["rows"]


def test_task_modify_disturbed_honors_lookup_base_query_when_extended_exists(disturbed_client):
    client, DisturbedStub, _, _, dispatched, run_dir = disturbed_client
    disturbed = DisturbedStub.getInstance(run_dir)
    Path(disturbed.lookup_fn).write_text("luse,stext,plant.data.decfct,plant.data.dropfc\nforest,loam,1,1\n")
    Path(disturbed.extended_lookup_fn).write_text(
        "sev_enum,landuse,disturbed_class,stext,plant.data.decfct,plant.data.dropfc,plant.data.bb\n"
        "0,forest,forest,loam,1,1,3.6\n"
    )

    meta_response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/disturbed/lookup_meta?lookup=base")
    assert meta_response.status_code == 200
    assert meta_response.get_json()["Content"]["lookup_variant"] == "base"
    current_sha = meta_response.get_json()["Content"]["lookup_sha256"]

    payload = {
        "rows": [["forest", "loam", "1", "1"]],
        "if_match_sha256": current_sha,
    }
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_disturbed?lookup=base",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.get_json() == {}
    assert response.headers["X-Lookup-Variant"] == "base"
    lookup_path, data = dispatched["write_lookup"]
    assert lookup_path == disturbed.lookup_fn
    assert data == payload["rows"]


def test_task_modify_disturbed_rejects_when_lookup_sha_unavailable(
    disturbed_client,
    monkeypatch: pytest.MonkeyPatch,
):
    client, *_ = disturbed_client
    monkeypatch.setattr(
        disturbed_module,
        "get_disturbed_land_soil_lookup_sha256",
        lambda _path: None,
    )
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_disturbed",
        json={
            "rows": [["forest", "loam", "1", "2", "3", "4", "1", "0", "0", "0"]],
            "if_match_sha256": "deadbeef",
        },
    )
    assert response.status_code == 409
    payload = response.get_json()
    assert payload["error"]["code"] == "LOOKUP_VERSION_UNAVAILABLE"


def test_task_modify_disturbed_errors_when_explicit_extended_missing(disturbed_client):
    client, *_ = disturbed_client
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_disturbed?lookup=extended",
        json={
            "rows": [["forest", "loam", "1", "2", "3", "4", "1", "0", "0", "0"]],
            "if_match_sha256": "deadbeef",
        },
    )
    assert response.status_code == 409
    payload = response.get_json()
    assert payload["error"]["code"] == "LOOKUP_VARIANT_UNAVAILABLE"


def test_lookup_endpoints_use_non_mutating_lock(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(disturbed_module.disturbed_bp)

    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()
    lookup_csv = run_dir / "lookup.csv"
    lookup_csv.write_text("luse,stext,ki\nforest,loam,1\n")
    context = SimpleNamespace(active_root=run_dir)
    monkeypatch.setattr(disturbed_module, "load_run_context", lambda runid, config: context)

    class DisturbedInstance:
        def __init__(self, lookup_fn: str):
            self.lookup_fn = lookup_fn
            self.readonly = False
            self.lock_calls = 0
            self.unlock_calls = 0
            self.locked_calls = 0

        def lock(self) -> None:
            self.lock_calls += 1

        def unlock(self, flag=None) -> None:
            self.unlock_calls += 1

        def locked(self):
            self.locked_calls += 1
            raise AssertionError("lookup GET routes must not call locked()")

    disturbed_instance = DisturbedInstance(str(lookup_csv))

    class DisturbedStub:
        @classmethod
        def getInstance(cls, wd: str):
            return disturbed_instance

    monkeypatch.setattr(disturbed_module, "Disturbed", DisturbedStub)

    with app.test_client() as client:
        meta_response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/disturbed/lookup_meta")
        assert meta_response.status_code == 200
        snapshot_response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/disturbed/lookup_snapshot")
        assert snapshot_response.status_code == 200

    assert disturbed_instance.lock_calls == 2
    assert disturbed_instance.unlock_calls == 2
    assert disturbed_instance.locked_calls == 0


def test_task_modify_disturbed_rejects_partial_table_payload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(disturbed_module.disturbed_bp)

    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()
    lookup_csv = run_dir / "lookup.csv"
    lookup_csv.write_text(
        "luse,stext,ki,kr\n"
        "forest,loam,100,1\n"
        "shrub,loam,200,2\n"
    )
    before = lookup_csv.read_text()
    context = SimpleNamespace(active_root=run_dir)
    monkeypatch.setattr(disturbed_module, "load_run_context", lambda runid, config: context)

    helpers = __import__("wepppy.weppcloud.utils.helpers", fromlist=["authorize"])
    monkeypatch.setattr(helpers, "authorize", lambda runid, config, require_owner=False: None)

    class DisturbedStub:
        @classmethod
        def getInstance(cls, wd: str):
            instance = SimpleNamespace(lookup_fn=str(lookup_csv))
            instance.locked = disturbed_lock
            instance.lock = lambda: None
            instance.unlock = lambda flag=None: None
            instance.readonly = False
            return instance

    @contextmanager
    def disturbed_lock():
        yield

    monkeypatch.setattr(disturbed_module, "Disturbed", DisturbedStub)
    current_sha = disturbed_module.get_disturbed_land_soil_lookup_sha256(str(lookup_csv))

    with app.test_client() as client:
        response = client.post(
            f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_disturbed",
            json={
                "rows": [["forest", "loam", "999", "9"]],
                "if_match_sha256": current_sha,
            },
        )

    assert response.status_code == 400
    payload = response.get_json()
    assert "missing existing lookup rows" in payload["error"]["message"].lower()
    assert lookup_csv.read_text() == before


def test_task_modify_disturbed_trims_blank_rows_from_table_payload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(disturbed_module.disturbed_bp)

    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()
    lookup_csv = run_dir / "lookup.csv"
    lookup_csv.write_text("luse,stext,ki,kr\nforest,loam,100,1\n")
    context = SimpleNamespace(active_root=run_dir)
    monkeypatch.setattr(disturbed_module, "load_run_context", lambda runid, config: context)

    helpers = __import__("wepppy.weppcloud.utils.helpers", fromlist=["authorize"])
    monkeypatch.setattr(helpers, "authorize", lambda runid, config, require_owner=False: None)

    class DisturbedStub:
        @classmethod
        def getInstance(cls, wd: str):
            instance = SimpleNamespace(lookup_fn=str(lookup_csv))
            instance.locked = disturbed_lock
            instance.lock = lambda: None
            instance.unlock = lambda flag=None: None
            instance.readonly = False
            return instance

    @contextmanager
    def disturbed_lock():
        yield

    monkeypatch.setattr(disturbed_module, "Disturbed", DisturbedStub)
    current_sha = disturbed_module.get_disturbed_land_soil_lookup_sha256(str(lookup_csv))

    with app.test_client() as client:
        response = client.post(
            f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_disturbed",
            json={
                "rows": [
                    ["forest", "loam", "999", "9"],
                    ["", "", "", ""],
                ],
                "if_match_sha256": current_sha,
            },
        )

    assert response.status_code == 200
    assert response.get_json() == {}
    assert lookup_csv.read_text().splitlines() == [
        "luse,stext,ki,kr",
        "forest,loam,999,9",
    ]


def test_task_modify_disturbed_still_rejects_partially_blank_key_rows(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(disturbed_module.disturbed_bp)

    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()
    lookup_csv = run_dir / "lookup.csv"
    lookup_csv.write_text("luse,stext,ki,kr\nforest,loam,100,1\n")
    before = lookup_csv.read_text()
    context = SimpleNamespace(active_root=run_dir)
    monkeypatch.setattr(disturbed_module, "load_run_context", lambda runid, config: context)

    helpers = __import__("wepppy.weppcloud.utils.helpers", fromlist=["authorize"])
    monkeypatch.setattr(helpers, "authorize", lambda runid, config, require_owner=False: None)

    class DisturbedStub:
        @classmethod
        def getInstance(cls, wd: str):
            instance = SimpleNamespace(lookup_fn=str(lookup_csv))
            instance.locked = disturbed_lock
            instance.lock = lambda: None
            instance.unlock = lambda flag=None: None
            instance.readonly = False
            return instance

    @contextmanager
    def disturbed_lock():
        yield

    monkeypatch.setattr(disturbed_module, "Disturbed", DisturbedStub)
    current_sha = disturbed_module.get_disturbed_land_soil_lookup_sha256(str(lookup_csv))

    with app.test_client() as client:
        response = client.post(
            f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_disturbed",
            json={
                "rows": [
                    ["forest", "loam", "999", "9"],
                    ["", "loam", "", ""],
                ],
                "if_match_sha256": current_sha,
            },
        )

    assert response.status_code == 400
    payload = response.get_json()
    assert "non-empty luse/stext" in payload["error"]["message"].lower()
    assert lookup_csv.read_text() == before


def test_task_baer_modify_color_map_converts_keys(disturbed_client):
    client, _, BaerStub, RonStub, _, run_dir = disturbed_client
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_color_map",
        json={"color_map": {"255_0_0": "High"}},
    )
    assert response.status_code == 200
    assert response.get_json() == {}
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
    assert payload == {}
    controller = BaerStub.getInstance(run_dir)
    assert controller.burn_class_updates[-1] == ([1, 2, 3, 4], "999")
    prep = disturbed_module.RedisPrep.getInstance(run_dir)
    assert prep.removed[-1] == TaskEnum.build_rusle


def test_task_baer_modify_class_requires_four_values(disturbed_client):
    client, *_ = disturbed_client
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_burn_class",
        json={"classes": [1, 2, 3]},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert "four" in payload["error"]["message"].lower()


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
    assert payload == {}
    controller = DisturbedStub.getInstance(run_dir)
    assert controller.fire_date == "2024-09-01"


def test_set_firedate_accepts_short_format(disturbed_client):
    client, DisturbedStub, *_rest, run_dir = disturbed_client
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_firedate/",
        json={"fire_date": "8/4"},
    )
    assert response.status_code == 200
    assert response.get_json() == {}
    controller = DisturbedStub.getInstance(run_dir)
    assert controller.fire_date == "8/4"


def test_task_remove_sbs_calls_baer(disturbed_client):
    client, DisturbedStub, BaerStub, RonStub, _, run_dir = disturbed_client
    response = client.post(f"/runs/{RUN_ID}/{CONFIG}/tasks/remove_sbs")
    assert response.status_code == 200
    assert response.get_json() == {}
    controller = BaerStub.getInstance(run_dir)
    assert controller.sbs_removed == 1
    prep = disturbed_module.RedisPrep.getInstance(run_dir)
    assert prep.removed[-1] == TaskEnum.build_rusle


def test_task_build_uniform_sbs_runs_validation(disturbed_client):
    client, DisturbedStub, BaerStub, RonStub, _, run_dir = disturbed_client
    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/build_uniform_sbs",
        json={"value": 7},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Content"]["disturbed_fn"].endswith("uniform_7.tif")
    controller = DisturbedStub.getInstance(run_dir)
    assert controller.uniform_values[-1] == 7
    assert controller.validated[-1].endswith("uniform_7.tif")
    assert controller.sbs_mode == 1
    assert controller.uniform_severity == 7
    baer_controller = BaerStub.getInstance(run_dir)
    assert baer_controller.sbs_mode == 1
    assert baer_controller.uniform_severity == 7
    prep = disturbed_module.RedisPrep.getInstance(run_dir)
    assert prep.removed[-1] == TaskEnum.build_rusle


def test_task_build_uniform_sbs_accepts_path_value(disturbed_client):
    client, DisturbedStub, BaerStub, RonStub, _, run_dir = disturbed_client
    response = client.post(f"/runs/{RUN_ID}/{CONFIG}/tasks/build_uniform_sbs/9")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Content"]["disturbed_fn"].endswith("uniform_9.tif")
    controller = DisturbedStub.getInstance(run_dir)
    assert controller.uniform_values[-1] == 9
    assert controller.validated[-1].endswith("uniform_9.tif")
    assert controller.sbs_mode == 1
    assert controller.uniform_severity == 9
    baer_controller = BaerStub.getInstance(run_dir)
    assert baer_controller.sbs_mode == 1
    assert baer_controller.uniform_severity == 9
    prep = disturbed_module.RedisPrep.getInstance(run_dir)
    assert prep.removed[-1] == TaskEnum.build_rusle
