from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Tuple

import pytest

pytest.importorskip("flask")
from flask import Flask
import importlib

run_0_module = importlib.import_module("wepppy.weppcloud.routes.run_0.run_0_bp")
import wepppy.weppcloud.routes.readme_md as readme_module
import wepppy.weppcloud.utils.cap_verify as cap_verify_module

pytestmark = pytest.mark.routes

RUN_ID = "cap-run"
CONFIG = "disturbed9002"


@pytest.fixture()
def run_0_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Tuple[Any, Dict[str, Any]]:
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SITE_PREFIX"] = "/weppcloud"
    app.register_blueprint(run_0_module.run_0_bp, url_prefix="/weppcloud")

    stub_user = SimpleNamespace(is_anonymous=True, email="")
    monkeypatch.setattr(run_0_module, "current_user", stub_user)

    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()

    def fake_create_run_dir(current_user: Any) -> Tuple[str, str]:
        return RUN_ID, str(run_dir)

    monkeypatch.setattr(run_0_module, "create_run_dir", fake_create_run_dir)

    captured: Dict[str, Any] = {}

    class DummyRon:
        def __init__(self, wd: str, cfg: str) -> None:
            captured["wd"] = wd
            captured["cfg"] = cfg

    monkeypatch.setattr(run_0_module, "Ron", DummyRon)
    monkeypatch.setattr(readme_module, "ensure_readme_on_create", lambda runid, config: None)

    with app.test_client() as client:
        yield client, captured


@pytest.fixture()
def run_0_client_authenticated(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Tuple[Any, Dict[str, Any]]:
    import sys

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SITE_PREFIX"] = "/weppcloud"
    app.register_blueprint(run_0_module.run_0_bp, url_prefix="/weppcloud")

    stub_user = SimpleNamespace(is_anonymous=False, email="tester@example.com")
    monkeypatch.setattr(run_0_module, "current_user", stub_user)

    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()

    def fake_create_run_dir(current_user: Any) -> Tuple[str, str]:
        return RUN_ID, str(run_dir)

    monkeypatch.setattr(run_0_module, "create_run_dir", fake_create_run_dir)

    captured: Dict[str, Any] = {}

    class DummyRon:
        def __init__(self, wd: str, cfg: str) -> None:
            captured["wd"] = wd
            captured["cfg"] = cfg

    class DummyUserDatastore:
        def create_run(self, runid: str, config: str, user: Any) -> None:
            captured["create_run"] = (runid, config, user.email)

    monkeypatch.setattr(run_0_module, "Ron", DummyRon)
    monkeypatch.setattr(readme_module, "ensure_readme_on_create", lambda runid, config: None)

    original_app_module = sys.modules.get("wepppy.weppcloud.app")
    sys.modules["wepppy.weppcloud.app"] = SimpleNamespace(user_datastore=DummyUserDatastore())

    try:
        with app.test_client() as client:
            yield client, captured
    finally:
        if original_app_module is not None:
            sys.modules["wepppy.weppcloud.app"] = original_app_module
        else:
            sys.modules.pop("wepppy.weppcloud.app", None)


def test_create_requires_cap_token(run_0_client):
    client, captured = run_0_client

    response = client.post(f"/weppcloud/create/{CONFIG}", data={})

    assert response.status_code == 403
    assert response.get_json()["Error"] == "CAPTCHA token is required."
    assert "cfg" not in captured


def test_create_rejects_invalid_token(run_0_client, monkeypatch: pytest.MonkeyPatch):
    client, captured = run_0_client

    monkeypatch.setattr(
        cap_verify_module,
        "verify_cap_token",
        lambda token: {"success": False, "error-codes": ["invalid"]},
    )

    response = client.post(
        f"/weppcloud/create/{CONFIG}",
        data={"cap_token": "bad-token"},
    )

    assert response.status_code == 403
    assert response.get_json()["Error"] == "CAPTCHA verification failed."
    assert "cfg" not in captured


def test_create_accepts_valid_token(run_0_client, monkeypatch: pytest.MonkeyPatch):
    client, captured = run_0_client

    monkeypatch.setattr(
        cap_verify_module,
        "verify_cap_token",
        lambda token: {"success": True},
    )

    response = client.post(
        f"/weppcloud/create/{CONFIG}",
        data={"cap_token": "good-token", "unitizer:is_english": ""},
    )

    assert response.status_code == 303
    location = response.headers["Location"].rstrip("/")
    assert location.endswith(f"/runs/{RUN_ID}/{CONFIG}")
    assert captured["cfg"] == f"{CONFIG}.cfg"


def test_create_allows_get_for_authenticated_user(run_0_client_authenticated):
    client, captured = run_0_client_authenticated

    response = client.get(f"/weppcloud/create/{CONFIG}?unitizer:is_english=true")

    assert response.status_code == 303
    location = response.headers["Location"].rstrip("/")
    assert location.endswith(f"/runs/{RUN_ID}/{CONFIG}")
    assert captured["cfg"] == f"{CONFIG}.cfg?unitizer:is_english=true"
    assert captured["create_run"][0] == RUN_ID
