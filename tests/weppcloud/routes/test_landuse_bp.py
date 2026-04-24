from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List
from types import SimpleNamespace

import pytest

pytest.importorskip("flask")
from flask import Flask, render_template

import wepppy.weppcloud.routes.nodb_api.landuse_bp as landuse_module

RUN_ID = "test-run"
CONFIG = "cfg"
pytestmark = pytest.mark.routes


@pytest.fixture()
def landuse_client(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Provide a Flask client with landuse blueprint and stubbed dependencies."""

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(landuse_module.landuse_bp)

    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()

    def fake_get_wd(runid: str) -> str:
        assert runid == RUN_ID
        return str(run_dir)

    monkeypatch.setattr(landuse_module, "get_wd", fake_get_wd)
    monkeypatch.setattr(
        landuse_module,
        "load_run_context",
        lambda runid, config: SimpleNamespace(active_root=Path(fake_get_wd(runid)), runid=runid, config=config),
    )

    class DummyLanduse:
        _instances: Dict[str, "DummyLanduse"] = {}
        _mods: tuple[str, ...] = ()

        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.landuseoptions = {"options": []}
            self.report = {"rows": []}
            self.domlc_d = {"1": "Forest"}
            self.subs_summary = [{"topaz_id": 1}]
            self.chns_summary = [{"topaz_id": 2}]
            self.hillslope_cancovs = {"1": {"cover": 45}}
            self.mods = tuple(type(self)._mods)
            self.mapping = "disturbed"
            self._custom_mapping_relpath: str | None = None

        @classmethod
        def getInstance(cls, wd: str) -> "DummyLanduse":
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

        @classmethod
        def load_detached(
            cls,
            wd: str,
            allow_nonexistent: bool = False,
        ) -> "DummyLanduse" | None:
            _ = allow_nonexistent
            return cls.getInstance(wd)

        @contextmanager
        def locked(self):
            yield

        def _resolve_effective_mapping_reference(self, mapping_reference: str | None = None):
            return mapping_reference

        @property
        def custom_mapping_relpath(self) -> str | None:
            return self._custom_mapping_relpath

        @custom_mapping_relpath.setter
        def custom_mapping_relpath(self, value: str | None) -> None:
            self._custom_mapping_relpath = value

    monkeypatch.setattr(landuse_module, "Landuse", DummyLanduse)

    class DummyRon:
        _instances: Dict[str, "DummyRon"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd

        @classmethod
        def getInstance(cls, wd: str) -> "DummyRon":
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

    monkeypatch.setattr(landuse_module, "Ron", DummyRon)

    captured: Dict[str, Any] = {}

    def fake_render_template(template: str, **context: Any) -> str:
        captured["template"] = template
        captured["context"] = context
        return "rendered"

    monkeypatch.setattr(landuse_module, "render_template", fake_render_template)

    with app.test_client() as client:
        yield client, DummyLanduse, captured, str(run_dir)

    DummyLanduse._instances.clear()
    DummyRon._instances.clear()


def test_query_landuse_routes_remain_available(landuse_client) -> None:
    client, _DummyLanduse, _captured, _run_dir = landuse_client

    landuse = client.get(f"/runs/{RUN_ID}/{CONFIG}/query/landuse/")
    subcatchments = client.get(f"/runs/{RUN_ID}/{CONFIG}/query/landuse/subcatchments/")
    channels = client.get(f"/runs/{RUN_ID}/{CONFIG}/query/landuse/channels/")
    covers = client.get(f"/runs/{RUN_ID}/{CONFIG}/query/landuse/cover/subcatchments/")

    assert landuse.status_code == 200
    assert landuse.get_json() == {"1": "Forest"}
    assert subcatchments.status_code == 200
    assert subcatchments.get_json() == [{"topaz_id": 1}]
    assert channels.status_code == 200
    assert channels.get_json() == [{"topaz_id": 2}]
    assert covers.status_code == 200
    assert covers.get_json() == {"1": {"cover": 45}}


def test_report_landuse_renders_template(landuse_client) -> None:
    client, _DummyLanduse, captured, _run_dir = landuse_client

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/report/landuse/")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "rendered"
    assert response.headers["Cache-Control"] == "no-store, no-cache, must-revalidate, max-age=0"
    assert response.headers["Pragma"] == "no-cache"
    assert response.headers["Expires"] == "0"
    assert captured["template"] == "reports/landuse.htm"
    assert captured["context"]["runid"] == RUN_ID
    assert captured["context"]["landuseoptions"] == {"options": []}
    assert captured["context"]["disturbed_preview_available"] is False


def test_report_landuse_prefers_detached_snapshot(
    landuse_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, DummyLanduse, captured, run_dir = landuse_client
    stale = DummyLanduse.getInstance(run_dir)
    fresh = DummyLanduse(run_dir)
    fresh.report = [{"key": "fresh", "pct_coverage": 100.0}]

    def fake_get_instance(cls, wd: str):
        _ = wd
        return stale

    def fake_load_detached(cls, wd: str, allow_nonexistent: bool = False):
        _ = wd
        _ = allow_nonexistent
        return fresh

    monkeypatch.setattr(DummyLanduse, "getInstance", classmethod(fake_get_instance))
    monkeypatch.setattr(DummyLanduse, "load_detached", classmethod(fake_load_detached))

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/report/landuse/")

    assert response.status_code == 200
    assert captured["context"]["landuse"] is fresh


def test_report_landuse_enables_disturbed_preview_context(landuse_client) -> None:
    client, DummyLanduse, captured, _run_dir = landuse_client
    DummyLanduse._mods = ("disturbed",)
    try:
        response = client.get(f"/runs/{RUN_ID}/{CONFIG}/report/landuse/")

        assert response.status_code == 200
        assert captured["context"]["disturbed_preview_available"] is True
        assert captured["context"]["disturbed_preview_textures"] == (
            ("clay", "Clay"),
            ("loam", "Loam"),
            ("sand", "Sand"),
            ("silt", "Silt"),
        )
    finally:
        DummyLanduse._mods = ()


def test_view_landuse_user_defined_renders_rq_engine_routes(landuse_client) -> None:
    client, _DummyLanduse, captured, _run_dir = landuse_client

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/landuse-user-defined")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "rendered"
    assert captured["template"] == "controls/landuse_user_defined.htm"
    context = captured["context"]
    assert context["list_url"] == f"/rq-engine/api/runs/{RUN_ID}/{CONFIG}/landuse-user-defined/catalog"
    assert context["upload_url"] == f"/rq-engine/api/runs/{RUN_ID}/{CONFIG}/landuse-user-defined/upload"
    assert context["delete_url"] == f"/rq-engine/api/runs/{RUN_ID}/{CONFIG}/landuse-user-defined/delete"
    assert context["update_description_url"] == (
        f"/rq-engine/api/runs/{RUN_ID}/{CONFIG}/landuse-user-defined/update-description"
    )
    assert context["session_token_url"] == f"/rq-engine/api/runs/{RUN_ID}/{CONFIG}/session-token"
    assert response.headers["Cache-Control"] == "no-store, no-cache, must-revalidate, max-age=0"


def test_view_landuse_map_renders_rq_engine_routes(
    landuse_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _DummyLanduse, captured, _run_dir = landuse_client

    monkeypatch.setattr(
        landuse_module,
        "load_map",
        lambda _mapping: {
            "21": {
                "Key": 21,
                "Description": "Low Intensity Residential",
                "DisturbedClass": "developed low intensity",
                "ManagementFile": "Developed_Low_Intensity.man",
                "ManagementDir": "/maps",
            }
        },
    )

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/landuse-map")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "rendered"
    assert captured["template"] == "controls/landuse_map.htm"
    context = captured["context"]
    assert context["snapshot_url"] == f"/rq-engine/api/runs/{RUN_ID}/{CONFIG}/landuse-map/snapshot"
    assert context["save_url"] == f"/rq-engine/api/runs/{RUN_ID}/{CONFIG}/landuse-map/save"
    assert context["clear_override_url"] == f"/rq-engine/api/runs/{RUN_ID}/{CONFIG}/landuse-map/clear-override"
    assert context["session_token_url"] == f"/rq-engine/api/runs/{RUN_ID}/{CONFIG}/session-token"
    assert response.headers["Cache-Control"] == "no-store, no-cache, must-revalidate, max-age=0"


def test_view_landuse_map_redacts_mapping_path_errors(
    landuse_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _DummyLanduse, _captured, _run_dir = landuse_client

    def _raise_mapping_error(_landuse: object, _wd: str):
        raise landuse_module.ManagementMapLoadError(
            "Management map file does not exist: /tmp/run-1/landuse/custom-map.json",
            code="management_map_missing",
            map_path="/tmp/run-1/landuse/custom-map.json",
        )

    monkeypatch.setattr(landuse_module, "_build_landuse_map_snapshot_payload", _raise_mapping_error)

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/landuse-map")

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"]["code"] == "management_map_missing"
    assert payload["error"]["message"] == "Management map file does not exist"
    details = payload["error"].get("details")
    assert not details or "map_path" not in details


def test_landuse_template_renders_disturbed_preview_links_conditionally() -> None:
    template_dir = Path(__file__).resolve().parents[3] / "wepppy" / "weppcloud" / "templates"
    app = Flask(__name__, template_folder=str(template_dir))
    app.config["TESTING"] = True
    app.jinja_env.globals["startswith"] = lambda value, prefix: str(value).startswith(str(prefix))

    row = {
        "key": "42",
        "pct_coverage": 57.5,
        "cancov": 0.5,
        "inrcov": 0.4,
        "rilcov": 0.3,
        "cancov_override": None,
        "inrcov_override": None,
        "rilcov_override": None,
    }
    landuse = SimpleNamespace(mods=())
    landuseoptions = [{"Key": "42", "Description": "Forest", "ManagementFile": "forest.man"}]
    textures = (("clay", "Clay"), ("loam", "Loam"), ("sand", "Sand"), ("silt", "Silt"))

    with app.app_context():
        html_without_disturbed = render_template(
            "reports/landuse.htm",
            report=[row],
            landuse=landuse,
            landuseoptions=landuseoptions,
            coverage_percentages=[],
            disturbed_preview_available=False,
            disturbed_preview_textures=textures,
        )
        html_with_disturbed = render_template(
            "reports/landuse.htm",
            report=[row],
            landuse=landuse,
            landuseoptions=landuseoptions,
            coverage_percentages=[],
            disturbed_preview_available=True,
            disturbed_preview_textures=textures,
        )

    assert "view/management_effective/42/clay/" not in html_without_disturbed
    assert "view/management_effective/42/clay/" in html_with_disturbed


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", f"/runs/{RUN_ID}/{CONFIG}/tasks/set_landuse_mode/"),
        ("post", f"/runs/{RUN_ID}/{CONFIG}/tasks/set_landuse_db/"),
        ("post", f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_landuse_coverage"),
        ("post", f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_landuse_coverage/"),
        ("post", f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_landuse_mapping/"),
        ("get", f"/runs/{RUN_ID}/{CONFIG}/api/landuse/user_defined/catalog"),
        ("post", f"/runs/{RUN_ID}/{CONFIG}/tasks/landuse/user_defined/upload"),
        ("post", f"/runs/{RUN_ID}/{CONFIG}/tasks/landuse/user_defined/delete"),
        ("post", f"/runs/{RUN_ID}/{CONFIG}/tasks/landuse/user_defined/update-description"),
        ("get", f"/runs/{RUN_ID}/{CONFIG}/api/landuse/map_snapshot"),
        ("post", f"/runs/{RUN_ID}/{CONFIG}/tasks/landuse/map/save"),
        ("post", f"/runs/{RUN_ID}/{CONFIG}/tasks/landuse/map/clear-override"),
        ("post", f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_landuse/"),
    ],
)
def test_removed_legacy_landuse_compatibility_routes_return_not_found(
    landuse_client,
    method: str,
    path: str,
) -> None:
    client, _DummyLanduse, _captured, _run_dir = landuse_client

    response = getattr(client, method)(path)

    assert response.status_code == 404
