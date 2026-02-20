from __future__ import annotations

from dataclasses import dataclass

import pytest

pytest.importorskip("flask")
from flask import Flask

import wepppy.weppcloud.routes.gl_dashboard as gl_dashboard_module

pytestmark = pytest.mark.routes


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (True, True),
        (False, False),
        (1, True),
        (0, False),
        ("true", True),
        ("on", True),
        ("1", True),
        ("false", False),
        ("off", False),
        ("0", False),
        ("unexpected", False),
        (None, False),
    ],
)
def test_coerce_bool_setting(raw: object, expected: bool) -> None:
    assert gl_dashboard_module._coerce_bool_setting(raw, default=False) is expected


@pytest.fixture()
def gl_dashboard_client(monkeypatch: pytest.MonkeyPatch, tmp_path):
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["GL_DASHBOARD_BATCH_ENABLED"] = "true"
    app.register_blueprint(gl_dashboard_module.gl_dashboard_bp)

    run_dir = tmp_path / "run"
    run_dir.mkdir()

    @dataclass
    class DummyContext:
        active_root: str
        pup_relpath: str = ""

    monkeypatch.setattr(gl_dashboard_module, "authorize", lambda runid, config: None)
    monkeypatch.setattr(
        gl_dashboard_module,
        "load_run_context",
        lambda runid, config: DummyContext(active_root=str(run_dir)),
    )
    monkeypatch.setattr(
        gl_dashboard_module,
        "is_omni_child_run",
        lambda runid, wd=None, pup_relpath=None: False,
    )
    monkeypatch.setattr(gl_dashboard_module, "_get_omni_scenarios", lambda wd: None)
    monkeypatch.setattr(gl_dashboard_module, "_get_omni_contrasts", lambda wd: None)

    class DummyRon:
        @staticmethod
        def getInstance(wd: str):
            return type("RonObj", (), {"map": None})()

    class DummyClimate:
        @staticmethod
        def getInstance(wd: str):
            return type("ClimateObj", (), {"has_observed": False, "input_years": 10})()

    monkeypatch.setattr(gl_dashboard_module, "Ron", DummyRon)
    monkeypatch.setattr(gl_dashboard_module, "Climate", DummyClimate)

    captured: dict[str, object] = {}

    def fake_render_template(template_name: str, **kwargs):
        captured["template_name"] = template_name
        captured["kwargs"] = kwargs
        return "ok"

    monkeypatch.setattr(gl_dashboard_module, "render_template", fake_render_template)

    with app.test_client() as client:
        yield client, captured, app


def test_gl_dashboard_context_includes_batch_mode_flag(gl_dashboard_client) -> None:
    client, captured, _app = gl_dashboard_client

    response = client.get("/runs/run-123/cfg/gl-dashboard")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "ok"
    assert captured["template_name"] == "gl_dashboard.htm"
    kwargs = captured["kwargs"]
    assert kwargs["runid"] == "run-123"
    assert kwargs["config"] == "cfg"
    assert kwargs["mode"] == "run"
    assert kwargs["batch"] is None
    assert kwargs["batch_mode_enabled"] is True


def test_gl_dashboard_context_respects_disabled_batch_flag(gl_dashboard_client) -> None:
    client, captured, app = gl_dashboard_client
    app.config["GL_DASHBOARD_BATCH_ENABLED"] = "off"

    response = client.get("/runs/run-456/cfg/gl-dashboard")

    assert response.status_code == 200
    kwargs = captured["kwargs"]
    assert kwargs["batch_mode_enabled"] is False


def test_get_omni_contrasts_returns_only_completed_readme_entries(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path / "run"
    wd.mkdir()
    (wd / "omni.nodb").write_text("{}", encoding="ascii")
    contrasts_root = wd / "_pups" / "omni" / "contrasts"
    (contrasts_root / "1" / "wepp" / "output" / "interchange").mkdir(parents=True)
    (contrasts_root / "2" / "wepp" / "output" / "interchange").mkdir(parents=True)
    (contrasts_root / "3" / "wepp" / "output" / "interchange").mkdir(parents=True)
    (contrasts_root / "1" / "wepp" / "output" / "interchange" / "README.md").write_text(
        "done",
        encoding="ascii",
    )

    class DummyOmni:
        contrast_names = ["contrast-a", None, "contrast-c"]

    monkeypatch.setattr(gl_dashboard_module.Omni, "getInstance", lambda _wd: DummyOmni())

    result = gl_dashboard_module._get_omni_contrasts(str(wd))

    assert result == [
        {"id": 1, "name": "contrast-a", "path": "_pups/omni/contrasts/1"},
    ]


def test_get_omni_contrasts_returns_none_when_omni_load_fails(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path / "run"
    wd.mkdir()
    (wd / "omni.nodb").write_text("{}", encoding="ascii")
    (wd / "_pups" / "omni" / "contrasts").mkdir(parents=True)

    def _raise(_wd: str):
        raise RuntimeError("boom")

    monkeypatch.setattr(gl_dashboard_module.Omni, "getInstance", _raise)

    assert gl_dashboard_module._get_omni_contrasts(str(wd)) is None
