from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("flask")
pytest.importorskip("flask_security")
from flask import Flask
from werkzeug.exceptions import Forbidden

pytestmark = pytest.mark.routes


def _load_module():
    return importlib.reload(importlib.import_module("wepppy.weppcloud.routes.weppcloudr"))


def _build_app(module) -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(module.weppcloudr_bp)
    return app


def _install_user_datastore_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    app_module = types.ModuleType("wepppy.weppcloud.app")
    app_module.user_datastore = SimpleNamespace(add_role_to_user=lambda *_args, **_kwargs: None)
    monkeypatch.setitem(sys.modules, "wepppy.weppcloud.app", app_module)


def _stub_nodb(monkeypatch: pytest.MonkeyPatch, module, *, marker: str = "safe") -> None:
    class _Ron:
        @staticmethod
        def getInstance(_wd: str):
            return SimpleNamespace(
                name=f"name-{marker}",
                scenario="scenario",
                config_stem="cfg",
                location_hash="hash",
            )

    class _Wepp:
        @staticmethod
        def getInstance(_wd: str):
            return SimpleNamespace()

    class _Watershed:
        @staticmethod
        def getInstance(_wd: str):
            return SimpleNamespace()

    monkeypatch.setattr(module, "Ron", _Ron)
    monkeypatch.setattr(module, "Wepp", _Wepp)
    monkeypatch.setattr(module, "Watershed", _Watershed)


def test_weppcloudr_proxy_rejects_anonymous_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    app = _build_app(module)
    monkeypatch.setattr(
        module,
        "current_user",
        SimpleNamespace(is_authenticated=False),
        raising=False,
    )

    with app.test_client() as client:
        response = client.get("/WEPPcloudR/proxy/report.Rmd?runids=run-a")

    assert response.status_code == 401


def test_weppcloudr_proxy_requires_non_empty_runids(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    app = _build_app(module)
    monkeypatch.setattr(
        module,
        "current_user",
        SimpleNamespace(is_authenticated=True, roles=[SimpleNamespace(name="User")], email="user@example.test"),
        raising=False,
    )
    monkeypatch.setattr(module, "authorize", lambda *_args, **_kwargs: pytest.fail("authorize should not be called"))

    with app.test_client() as client:
        missing = client.get("/WEPPcloudR/proxy/report.Rmd")
        empty = client.get("/WEPPcloudR/proxy/report.Rmd?runids=,")

    assert missing.status_code == 400
    assert empty.status_code == 400


def test_weppcloudr_proxy_rejects_unauthorized_runid(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    app = _build_app(module)
    monkeypatch.setattr(
        module,
        "current_user",
        SimpleNamespace(is_authenticated=True, roles=[SimpleNamespace(name="User")], email="user@example.test"),
        raising=False,
    )

    def _authorize(runid: str, _config: str) -> None:
        if runid == "blocked-run":
            raise Forbidden()

    monkeypatch.setattr(module, "authorize", _authorize)

    with app.test_client() as client:
        response = client.get("/WEPPcloudR/proxy/report.Rmd?runids=allowed-run,blocked-run")

    assert response.status_code == 403


def test_weppcloudr_proxy_authorized_request_executes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module = _load_module()
    app = _build_app(module)
    _install_user_datastore_stub(monkeypatch)
    _stub_nodb(monkeypatch, module)

    runids = ["run-a", "run-b"]
    run_dirs = {}
    for runid in runids:
        run_root = tmp_path / runid
        (run_root / "export").mkdir(parents=True, exist_ok=True)
        run_dirs[runid] = run_root

    monkeypatch.setattr(module, "get_wd", lambda runid: str(run_dirs[runid]))
    script_path = tmp_path / "report.Rmd"
    script_path.write_text("---\ntitle: test\n---\n", encoding="utf-8")
    monkeypatch.setattr(module, "_weppcloudr_script_locator", lambda routine, user=None: str(script_path))

    authorize_calls: list[tuple[str, str]] = []
    monkeypatch.setattr(module, "authorize", lambda runid, config: authorize_calls.append((runid, config)))
    monkeypatch.setattr(
        module,
        "current_user",
        SimpleNamespace(is_authenticated=True, roles=[SimpleNamespace(name="User")], email="user@example.test"),
        raising=False,
    )

    class _FakePopen:
        def __init__(self, cmd, stdout=None, stderr=None):
            self.cmd = cmd

        def communicate(self):
            args_index = self.cmd.index("--args")
            output_file = Path(self.cmd[args_index + 3])
            output_file.write_text("<html>ok</html>", encoding="utf-8")
            return b"stdout", b"stderr"

    monkeypatch.setattr(module, "Popen", _FakePopen)

    with app.test_client() as client:
        response = client.get("/WEPPcloudR/proxy/report.Rmd?runids=run-a,run-b")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "<html>ok</html>"
    assert authorize_calls == [
        ("run-a", "__weppcloudr_proxy__"),
        ("run-b", "__weppcloudr_proxy__"),
    ]


def test_weppcloudr_proxy_rmd_command_uses_args_without_ws_interpolation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_module()
    app = _build_app(module)
    _install_user_datastore_stub(monkeypatch)
    _stub_nodb(monkeypatch, module, marker="INJECT_MARKER")

    run_root = tmp_path / "run-a"
    (run_root / "export").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(module, "get_wd", lambda _runid: str(run_root))
    monkeypatch.setattr(module, "authorize", lambda _runid, _config: None)
    monkeypatch.setattr(
        module,
        "current_user",
        SimpleNamespace(is_authenticated=True, roles=[SimpleNamespace(name="User")], email="user@example.test"),
        raising=False,
    )

    script_path = tmp_path / "report.Rmd"
    script_path.write_text("---\ntitle: test\n---\n", encoding="utf-8")
    monkeypatch.setattr(module, "_weppcloudr_script_locator", lambda routine, user=None: str(script_path))

    captured_cmd: list[str] = []

    class _FakePopen:
        def __init__(self, cmd, stdout=None, stderr=None):
            captured_cmd[:] = cmd

        def communicate(self):
            args_index = captured_cmd.index("--args")
            output_file = Path(captured_cmd[args_index + 3])
            output_file.write_text("<html>ok</html>", encoding="utf-8")
            return b"stdout", b"stderr"

    monkeypatch.setattr(module, "Popen", _FakePopen)

    with app.test_client() as client:
        response = client.get("/WEPPcloudR/proxy/report.Rmd?runids=run-a")

    assert response.status_code == 200
    assert captured_cmd[0:3] == ["R", "-e", module.R_PROXY_RMD_RENDER_EXPR]
    args_index = captured_cmd.index("--args")
    ws_payload = captured_cmd[args_index + 2]
    assert "INJECT_MARKER" in ws_payload
    assert "INJECT_MARKER" not in captured_cmd[2]
    assert captured_cmd[args_index + 1] == str(script_path)
    assert captured_cmd[args_index + 3].endswith("report.Rmd.htm")
