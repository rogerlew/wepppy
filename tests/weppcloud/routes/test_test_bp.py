from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("flask")
from flask import Flask

import wepppy.weppcloud.routes.test_bp as test_bp_module

pytestmark = pytest.mark.routes


def test_create_run_endpoint_seeds_default_nodir_marker(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "ab-run"
    run_dir.mkdir(parents=True, exist_ok=False)

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

    class DummyRon:
        def __init__(self, wd: str, cfg: str) -> None:
            self.wd = wd
            self.cfg = cfg

    monkeypatch.setattr(test_bp_module, "Ron", DummyRon)
    monkeypatch.setattr(test_bp_module, "ensure_readme_on_create", lambda runid, config: None)
    monkeypatch.setattr(
        test_bp_module,
        "url_for_run",
        lambda endpoint, runid, config: f"/weppcloud/runs/{runid}/{config}",
    )

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
    assert marker_path.exists()

    marker_payload = json.loads(marker_path.read_text(encoding="utf-8"))
    assert marker_payload["schema_version"] == 1
    assert sorted(marker_payload["roots"]) == ["climate", "landuse", "soils", "watershed"]
