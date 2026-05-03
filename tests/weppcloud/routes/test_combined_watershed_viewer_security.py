from __future__ import annotations

import importlib
import json
from types import SimpleNamespace

import pytest

pytest.importorskip("flask")
pytest.importorskip("flask_security")
from flask import Flask

pytestmark = pytest.mark.routes


def _load_module():
    return importlib.reload(importlib.import_module("wepppy.weppcloud.routes.combined_watershed_viewer"))


def _build_app(module) -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(module.combined_watershed_viewer_bp)
    return app


def _install_template_stub(monkeypatch: pytest.MonkeyPatch, module) -> None:
    def _render(template_name: str, **ctx):
        ctx.pop("user", None)
        return module.jsonify({"template_name": template_name, **ctx})

    monkeypatch.setattr(
        module,
        "render_template",
        _render,
    )


def _install_public_stub(monkeypatch: pytest.MonkeyPatch, module, public_runids: set[str]) -> None:
    monkeypatch.setattr(module, "get_wd", lambda runid, prefer_active=False: f"/mock/{runid}")

    class _Ron:
        @staticmethod
        def ispublic(wd: str) -> bool:
            runid = wd.rsplit("/", 1)[-1]
            return runid in public_runids

    monkeypatch.setattr(module, "Ron", _Ron)


def test_url_generator_rejects_private_run_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    app = _build_app(module)
    _install_template_stub(monkeypatch, module)
    _install_public_stub(monkeypatch, module, {"public-run"})
    monkeypatch.setattr(module, "current_user", SimpleNamespace(is_authenticated=False), raising=False)

    with app.test_client() as client:
        response = client.post(
            "/combined_ws_viewer/url_generator",
            data={"title": "test", "runids": "public-run private-run"},
        )

    assert response.status_code == 403
    payload = response.get_json()
    assert payload is not None
    assert payload["error"]["message"] == "Forbidden"


def test_url_generator_accepts_all_public_run_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    app = _build_app(module)
    _install_template_stub(monkeypatch, module)
    _install_public_stub(monkeypatch, module, {"run-a", "run-b"})
    monkeypatch.setattr(module, "current_user", SimpleNamespace(is_authenticated=False), raising=False)

    captured: dict[str, object] = {}

    def _fake_generator(runids: list[str], title: str) -> str:
        captured["runids"] = list(runids)
        captured["title"] = title
        return "/mock/generated-url"

    gen_module = importlib.import_module("wepppy.weppcloud.combined_watershed_viewer_generator")
    monkeypatch.setattr(gen_module, "combined_watershed_viewer_generator", _fake_generator)

    with app.test_client() as client:
        response = client.post(
            "/combined_ws_viewer/url_generator",
            data={"title": "public runs", "runids": "run-a, run-b"},
        )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload is not None
    assert payload["template_name"] == "combined_ws_viewer_url_gen.htm"
    assert payload["url"] == "/mock/generated-url"
    assert payload["runids"] == "run-a, run-b"
    assert captured == {"runids": ["run-a", "run-b"], "title": "public runs"}


def test_combined_ws_viewer_rejects_malformed_ws(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    app = _build_app(module)
    _install_template_stub(monkeypatch, module)
    monkeypatch.setattr(module, "current_user", SimpleNamespace(is_authenticated=False), raising=False)
    monkeypatch.setattr(module, "get_wd", lambda *_args, **_kwargs: pytest.fail("get_wd should not be called"))

    with app.test_client() as client:
        response = client.get("/combined_ws_viewer?ws=not-json")

    assert response.status_code == 400
    payload = response.get_json()
    assert payload is not None
    assert payload["error"]["message"] == "Invalid request"


def test_combined_ws_viewer_rejects_private_ws_run(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    app = _build_app(module)
    _install_template_stub(monkeypatch, module)
    _install_public_stub(monkeypatch, module, {"public-run"})
    monkeypatch.setattr(module, "current_user", SimpleNamespace(is_authenticated=False), raising=False)

    ws = json.dumps([{"runid": "public-run"}, {"runid": "private-run"}])
    with app.test_client() as client:
        response = client.get(f"/combined_ws_viewer2?ws={ws}")

    assert response.status_code == 403
    payload = response.get_json()
    assert payload is not None
    assert payload["error"]["message"] == "Forbidden"


def test_bounds_ws_viewer_accepts_only_public_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    app = _build_app(module)
    _install_template_stub(monkeypatch, module)
    _install_public_stub(monkeypatch, module, {"run-a", "run-b"})
    monkeypatch.setattr(module, "current_user", SimpleNamespace(is_authenticated=False), raising=False)

    ws = json.dumps([{"runid": "run-a"}, {"runid": "run-b"}])
    with app.test_client() as client:
        response = client.get(f"/bounds_ws_viewer?ws={ws}")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload is not None
    assert payload["template_name"] == "bounds_ws_viewer.htm"


def test_combined_ws_viewer_omitted_ws_keeps_existing_behavior(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    app = _build_app(module)
    _install_template_stub(monkeypatch, module)
    monkeypatch.setattr(module, "current_user", SimpleNamespace(is_authenticated=False), raising=False)
    monkeypatch.setattr(module, "get_wd", lambda *_args, **_kwargs: pytest.fail("get_wd should not be called"))

    with app.test_client() as client:
        response = client.get("/combined_ws_viewer")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload is not None
    assert payload["template_name"] == "combined_ws_viewer.htm"
