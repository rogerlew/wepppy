from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("flask")
from flask import Flask

import wepppy.weppcloud.routes.test_bp as test_bp_module

pytestmark = pytest.mark.routes


def _configure_create_run_test_app(
    monkeypatch: pytest.MonkeyPatch,
    run_dir: Path,
) -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["TEST_SUPPORT_ENABLED"] = True
    app.register_blueprint(test_bp_module.test_bp)

    monkeypatch.setattr(
        test_bp_module,
        "current_user",
        SimpleNamespace(is_authenticated=True),
        raising=False,
    )
    monkeypatch.setattr(test_bp_module, "create_run_dir", lambda user: ("ab-run", str(run_dir)))
    captured_cfg: list[str] = []

    class DummyRon:
        def __init__(self, wd: str, cfg: str) -> None:
            self.wd = wd
            self.cfg = cfg
            captured_cfg.append(cfg)

        def config_get_bool(self, section: str, option: str, default: bool | None = None) -> bool:
            if section != "nodb" or option != "apply_nodir":
                return False if default is None else bool(default)
            if "?" not in self.cfg:
                return False if default is None else bool(default)
            _, query = self.cfg.split("?", 1)
            for pair in query.split("&"):
                if "=" not in pair:
                    continue
                key, value = pair.split("=", 1)
                if key != "nodb:apply_nodir":
                    continue
                return value.strip().lower().startswith("true")
            return False if default is None else bool(default)

    monkeypatch.setattr(test_bp_module, "Ron", DummyRon)
    monkeypatch.setattr(test_bp_module, "ensure_readme_on_create", lambda runid, config: None)
    monkeypatch.setattr(
        test_bp_module,
        "url_for_run",
        lambda endpoint, runid, config: f"/weppcloud/runs/{runid}/{config}",
    )
    app.config["_captured_ron_cfg"] = captured_cfg
    return app


def test_create_run_endpoint_does_not_seed_default_nodir_marker_without_opt_in(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "ab-run"
    run_dir.mkdir(parents=True, exist_ok=False)

    monkeypatch.delenv("WEPP_NODIR_DEFAULT_NEW_RUNS", raising=False)
    app = _configure_create_run_test_app(monkeypatch, run_dir)

    with app.test_client() as client:
        response = client.post(
            "/tests/api/create-run",
            json={"config": "dev_unit_1"},
        )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload is not None
    assert payload["run"]["runid"] == "ab-run"

    marker_path = run_dir / ".nodir" / "default_archive_roots.json"
    assert not marker_path.exists()


def test_create_run_endpoint_does_not_seed_default_nodir_marker_with_opt_in_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "ab-run"
    run_dir.mkdir(parents=True, exist_ok=False)

    monkeypatch.delenv("WEPP_NODIR_DEFAULT_NEW_RUNS", raising=False)
    app = _configure_create_run_test_app(monkeypatch, run_dir)

    with app.test_client() as client:
        response = client.post(
            "/tests/api/create-run",
            json={"config": "dev_unit_1", "overrides": {"nodb:apply_nodir": "true"}},
        )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload is not None
    assert payload["run"]["runid"] == "ab-run"
    assert app.config["_captured_ron_cfg"][-1] == "dev_unit_1.cfg?nodb:apply_nodir=true"

    marker_path = run_dir / ".nodir" / "default_archive_roots.json"
    assert not marker_path.exists()


def test_create_run_endpoint_opt_in_respects_global_nodir_env_gate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "ab-run"
    run_dir.mkdir(parents=True, exist_ok=False)

    monkeypatch.setenv("WEPP_NODIR_DEFAULT_NEW_RUNS", "0")
    app = _configure_create_run_test_app(monkeypatch, run_dir)

    with app.test_client() as client:
        response = client.post(
            "/tests/api/create-run",
            json={"config": "dev_unit_1", "overrides": {"nodb:apply_nodir": "true"}},
        )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload is not None
    assert payload["run"]["runid"] == "ab-run"
    assert app.config["_captured_ron_cfg"][-1] == "dev_unit_1.cfg?nodb:apply_nodir=true"

    marker_path = run_dir / ".nodir" / "default_archive_roots.json"
    assert not marker_path.exists()
