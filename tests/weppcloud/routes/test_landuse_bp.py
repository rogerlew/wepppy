from __future__ import annotations

from typing import Any, Dict, List

import pytest

pytest.importorskip("flask")
from flask import Flask

import wepppy.weppcloud.routes.nodb_api.landuse_bp as landuse_module

RUN_ID = "test-run"
CONFIG = "cfg"


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

    class DummyLanduse:
        _instances: Dict[str, "DummyLanduse"] = {}

        def __init__(self, wd: str) -> None:
            self.wd = wd
            self.mode = landuse_module.LanduseMode.Vanilla
            self.single_selection: str | None = None
            self.nlcd_db: str | None = None
            self.cover_changes: List[tuple[Any, Any, Any]] = []
            self.mapping_changes: List[tuple[Any, Any]] = []
            self.modify_calls: List[tuple[List[str], str]] = []
            self.landuseoptions = {"options": []}
            self.report = {"rows": []}
            self.domlc_d = {"1": "Forest"}
            self.subs_summary = [{"topaz_id": 1}]
            self.chns_summary = [{"topaz_id": 2}]
            self.hillslope_cancovs = {"1": {"cover": 45}}

        @classmethod
        def getInstance(cls, wd: str) -> "DummyLanduse":
            instance = cls._instances.get(wd)
            if instance is None:
                instance = cls(wd)
                cls._instances[wd] = instance
            return instance

        def modify_coverage(self, dom, cover, value) -> None:
            self.cover_changes.append((dom, cover, value))

        def modify_mapping(self, dom, newdom) -> None:
            self.mapping_changes.append((dom, newdom))

        def modify(self, topaz_ids: List[str], lccode: str) -> None:
            self.modify_calls.append((topaz_ids, lccode))

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


def test_set_landuse_mode_updates_controller(landuse_client):
    client, DummyLanduse, _, run_dir = landuse_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_landuse_mode/",
        data={"mode": str(int(landuse_module.LanduseMode.UserDefined)), "landuse_single_selection": "forest"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["Success"] is True

    controller = DummyLanduse.getInstance(run_dir)
    assert controller.mode == landuse_module.LanduseMode.UserDefined
    assert controller.single_selection == "forest"


def test_modify_landuse_coverage_records_change(landuse_client):
    client, DummyLanduse, _, run_dir = landuse_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_landuse_coverage",
        json={"dom": "1", "cover": "forest", "value": 75},
    )
    assert response.status_code == 200
    assert response.get_json()["Success"] is True

    controller = DummyLanduse.getInstance(run_dir)
    assert controller.cover_changes == [("1", "forest", 75.0)]


def test_report_landuse_renders_template(landuse_client):
    client, DummyLanduse, captured, _ = landuse_client

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/report/landuse/")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "rendered"
    assert captured["template"] == "reports/landuse.htm"
    assert captured["context"]["runid"] == RUN_ID
    assert captured["context"]["landuseoptions"] == {"options": []}


def test_task_modify_landuse_parses_ids(landuse_client):
    client, DummyLanduse, _, run_dir = landuse_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_landuse/",
        data={"topaz_ids": "1,2,3", "landuse": "5"},
    )

    assert response.status_code == 200
    assert response.get_json()["Success"] is True

    controller = DummyLanduse.getInstance(run_dir)
    assert controller.modify_calls == [(['1', '2', '3'], '5')]


def test_set_landuse_mode_accepts_json_payload(landuse_client):
    client, DummyLanduse, _, run_dir = landuse_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_landuse_mode/",
        json={"mode": int(landuse_module.LanduseMode.UserDefined), "landuse_single_selection": "riparian"},
    )

    assert response.status_code == 200
    assert response.get_json()["Success"] is True

    controller = DummyLanduse.getInstance(run_dir)
    assert controller.mode == landuse_module.LanduseMode.UserDefined
    assert controller.single_selection == "riparian"


def test_task_modify_landuse_accepts_list_payload(landuse_client):
    client, DummyLanduse, _, run_dir = landuse_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_landuse/",
        json={"topaz_ids": [1, "2", " 3 "], "landuse": 7},
    )

    assert response.status_code == 200
    assert response.get_json()["Success"] is True

    controller = DummyLanduse.getInstance(run_dir)
    assert controller.modify_calls == [(['1', '2', '3'], '7')]


def test_task_modify_landuse_rejects_invalid_ids(landuse_client):
    client, DummyLanduse, _, run_dir = landuse_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_landuse/",
        json={"topaz_ids": ["abc"], "landuse": 7},
    )

    assert response.status_code == 500
    payload = response.get_json()
    assert payload["Success"] is False
    assert "invalid topaz id" in payload["Error"].lower()

    controller = DummyLanduse.getInstance(run_dir)
    assert controller.modify_calls == []


def test_task_modify_landuse_requires_landuse_code(landuse_client):
    client, DummyLanduse, _, run_dir = landuse_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_landuse/",
        json={"topaz_ids": [1]},
    )

    assert response.status_code == 500
    payload = response.get_json()
    assert payload["Success"] is False
    assert "landuse" in payload["Error"].lower()

    controller = DummyLanduse.getInstance(run_dir)
    assert controller.modify_calls == []
