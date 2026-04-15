from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict

import pytest

pytest.importorskip("flask")
from flask import Flask

import wepppy.weppcloud.routes.nodb_api.geneva_bp as geneva_module
from wepppy.nodb.mods.geneva import Geneva


pytestmark = pytest.mark.routes

RUN_ID = "geneva-run"
CONFIG = "0"


@pytest.fixture()
def geneva_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Any:
    Geneva.cleanup_all_instances()

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(geneva_module.geneva_bp)

    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()
    context = SimpleNamespace(active_root=run_dir)

    monkeypatch.setattr(geneva_module, "load_run_context", lambda runid, config: context)

    helpers = __import__("wepppy.weppcloud.utils.helpers", fromlist=["authorize"])
    monkeypatch.setattr(helpers, "authorize", lambda runid, config, require_owner=False: None)

    captured: Dict[str, Any] = {}

    def fake_render_template(template: str, **context: Any) -> str:
        captured["template"] = template
        captured["template_context"] = context
        return "rendered"

    monkeypatch.setattr(geneva_module, "render_template", fake_render_template)

    with app.test_client() as client:
        yield client, captured, run_dir

    Geneva.cleanup_all_instances()


def test_modify_geneva_cn_table_route_renders_edit_csv_context(geneva_client: Any) -> None:
    client, captured, _ = geneva_client

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/modify_geneva_cn_table")

    assert response.status_code == 200
    assert captured["template"] == "controls/edit_csv.htm"
    template_context = captured["template_context"]
    assert template_context["runid"] == RUN_ID
    assert template_context["config"] == CONFIG
    assert template_context["page_title"] == "Edit Geneva CN Table"
    assert template_context["editor_title"] == "Geneva CN Table"
    assert template_context["csv_url"] == f"/runs/{RUN_ID}/{CONFIG}/download/geneva/data/cn_table.csv"
    assert template_context["save_url"] == f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_geneva_cn_table"
    assert template_context["lookup_meta_url"] == f"/runs/{RUN_ID}/{CONFIG}/api/geneva/cn_table_meta"
    assert template_context["lookup_snapshot_url"] == (
        f"/runs/{RUN_ID}/{CONFIG}/api/geneva/cn_table_snapshot"
    )


def test_cn_table_meta_and_snapshot_are_available(geneva_client: Any) -> None:
    client, _, _ = geneva_client

    meta_response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/geneva/cn_table_meta")
    assert meta_response.status_code == 200
    meta = meta_response.get_json()["Content"]
    assert meta["path"] == "geneva/data/cn_table.csv"
    assert meta["schema_version"] == 1
    assert meta["exists"] is True
    assert meta["lookup_sha256"]

    snapshot_response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/geneva/cn_table_snapshot")
    assert snapshot_response.status_code == 200
    snapshot = snapshot_response.get_json()["Content"]
    assert snapshot["meta"]["schema_version"] == 1
    assert snapshot["lookup_sha256"] == meta["lookup_sha256"]
    assert snapshot["rows"]
    assert "csv_text" in snapshot


def test_task_modify_geneva_cn_table_accepts_matching_if_match(geneva_client: Any) -> None:
    client, _, _ = geneva_client

    snapshot_response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/geneva/cn_table_snapshot")
    baseline = snapshot_response.get_json()["Content"]

    rows = list(baseline["rows"])
    rows[0] = dict(rows[0])
    rows[0]["cn_arc_ii"] = "89"
    rows[0]["antecedent_condition_source"] = "user_override"

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_geneva_cn_table",
        json={
            "if_match_sha256": baseline["lookup_sha256"],
            "rows": rows,
        },
    )

    assert response.status_code == 200
    updated_sha = response.headers.get("X-Lookup-Sha256")
    assert updated_sha
    assert updated_sha != baseline["lookup_sha256"]

    refreshed_snapshot_response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/geneva/cn_table_snapshot")
    refreshed = refreshed_snapshot_response.get_json()["Content"]
    assert refreshed["lookup_sha256"] == updated_sha
    assert refreshed["rows"][0]["cn_arc_ii"] == "89"


def test_task_modify_geneva_cn_table_rejects_missing_if_match(geneva_client: Any) -> None:
    client, _, _ = geneva_client

    snapshot_response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/geneva/cn_table_snapshot")
    rows = snapshot_response.get_json()["Content"]["rows"]

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_geneva_cn_table",
        json={"rows": rows},
    )

    assert response.status_code == 428
    payload = response.get_json()
    assert payload["error"]["code"] == "PRECONDITION_REQUIRED"


def test_task_modify_geneva_cn_table_rejects_stale_if_match(geneva_client: Any) -> None:
    client, _, _ = geneva_client

    snapshot_response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/geneva/cn_table_snapshot")
    rows = snapshot_response.get_json()["Content"]["rows"]

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_geneva_cn_table",
        json={
            "if_match_sha256": "stale-token",
            "rows": rows,
        },
    )

    assert response.status_code == 409
    payload = response.get_json()
    assert payload["error"]["code"] == "STALE_LOOKUP"


def test_task_reset_geneva_cn_table_requires_confirm_and_resets(
    geneva_client: Any,
) -> None:
    client, _, run_dir = geneva_client

    meta_response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/geneva/cn_table_meta")
    assert meta_response.status_code == 200

    table_path = run_dir / "geneva" / "data" / "cn_table.csv"
    assert table_path.exists()
    table_path.unlink()

    recreated_meta_response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/geneva/cn_table_meta")
    recreated_meta = recreated_meta_response.get_json()["Content"]
    assert recreated_meta["exists"] is True

    missing_confirm = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/reset_geneva_cn_table",
        json={"confirm": False},
    )
    assert missing_confirm.status_code == 400

    reset_response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/reset_geneva_cn_table",
        json={
            "schema_version": 1,
            "confirm": True,
        },
    )
    assert reset_response.status_code == 200
    content = reset_response.get_json()["Content"]
    assert content["schema_version"] == 1
    assert content["lookup_sha256"]
