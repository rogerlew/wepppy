from __future__ import annotations

import json
from importlib import reload
from types import SimpleNamespace
from typing import Any, Sequence

import pytest

pytest.importorskip("starlette")

from starlette.applications import Starlette


def _clear_auth_cache():
    from wepppy.query_engine.app.mcp import auth

    auth.get_auth_config.cache_clear()


def _set_auth_env(monkeypatch):
    monkeypatch.setenv("WEPP_MCP_JWT_SECRET", "unit-test-secret")
    monkeypatch.setenv("WEPP_MCP_JWT_ALGORITHMS", "HS256")
    _clear_auth_cache()


def test_create_mcp_app(monkeypatch):
    _set_auth_env(monkeypatch)

    from wepppy.query_engine.app.mcp import router

    reload(router)
    app = router.create_mcp_app()

    assert isinstance(app, Starlette)
    paths = {route.path for route in app.routes}
    assert "/ping" in paths
    assert "/runs" in paths
    assert "/runs/{run_id:str}" in paths
    assert "/runs/{run_id:str}/catalog" in paths
    assert "/runs/{run_id:str}/queries/validate" in paths
    assert "/runs/{run_id:str}/queries/execute" in paths
    assert "/runs/{run_id:str}/activate" in paths
    assert "/runs/{run_id:str}/presets" in paths
    assert "/runs/{run_id:str}/prompt-template" in paths
    assert "/runs/{run_id:str}/queries/validate" in paths
    assert "/runs/{run_id:str}/queries/execute" in paths


def test_server_mounts_mcp(monkeypatch):
    _set_auth_env(monkeypatch)

    from wepppy.query_engine.app import server

    reload(server)
    app = server.create_app()

    paths = {getattr(route, "path", None) for route in app.router.routes}
    assert "/mcp" in paths


def _bootstrap_run(tmp_path, run_id: str, files: list[dict[str, Any]] | None = None):
    run_dir = tmp_path / run_id
    catalog_dir = run_dir / "_query_engine"
    catalog_dir.mkdir(parents=True)
    catalog_path = catalog_dir / "catalog.json"
    if files is None:
        files = [
            {
                "path": "a.parquet",
                "extension": ".parquet",
                "size_bytes": 1,
                "modified": "2024-01-01T00:00:00Z",
                "schema": {
                    "fields": [
                        {"name": "col_a", "type": "INTEGER"},
                        {"name": "col_b", "type": "TEXT"},
                    ]
                },
            }
        ]
    catalog = {
        "files": files,
        "generated_at": "2024-05-07T16:33:22Z",
        "root": str(run_dir),
    }
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
    return run_dir


def _issue_token(auth_module, run_id: str | None = None, scopes: Sequence[str] | str = ("runs:read",), runs: list[str] | None = None):
    runs_payload: list[str]
    if runs is not None:
        runs_payload = runs
    elif run_id is not None:
        runs_payload = [run_id]
    else:
        runs_payload = []

    if isinstance(scopes, str):
        scope_value = scopes
    else:
        scope_value = " ".join(scopes)

    return auth_module.encode_jwt(
        {
            "sub": "user-123",
            "scope": scope_value,
            "runs": runs_payload,
        },
        "unit-test-secret",
        algorithm="HS256",
    )


def _make_client(monkeypatch, tmp_path, run_id: str, *, files: list[dict[str, Any]] | None = None, create_catalog: bool = True):
    try:
        from starlette.testclient import TestClient
    except (ImportError, RuntimeError) as exc:
        pytest.skip(f"starlette.testclient unavailable: {exc}")

    if create_catalog:
        run_dir = _bootstrap_run(tmp_path, run_id, files=files)
    else:
        run_dir = tmp_path / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

    from wepppy.query_engine.app import helpers

    def fake_resolve(runid: str):
        if runid != run_id:
            raise FileNotFoundError(runid)
        return run_dir

    monkeypatch.setattr(helpers, "resolve_run_path", fake_resolve)

    from wepppy.query_engine.app import server
    from wepppy.query_engine.app.mcp import router

    reload(router)
    reload(server)

    app = server.create_app()
    return app, run_dir


def test_list_runs(monkeypatch, tmp_path):
    _set_auth_env(monkeypatch)

    run_id = "demo-run"
    app, _ = _make_client(monkeypatch, tmp_path, run_id)

    from starlette.testclient import TestClient  # type: ignore
    from wepppy.query_engine.app.mcp import auth

    client = TestClient(app)
    token = _issue_token(auth, run_id)

    response = client.get(
        "/mcp/runs",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "trace_id" in payload["meta"]
    assert payload["meta"]["page"]["total_pages"] == 1
    assert payload["meta"]["total_items"] == 1
    assert len(payload["data"]) == 1
    record = payload["data"][0]
    assert record["id"] == run_id
    assert record["attributes"]["activated"] is True
    assert record["attributes"]["dataset_count"] == 1
    assert record["attributes"]["last_catalog_refresh"] == "2024-05-07T16:33:22Z"
    links = record["links"]
    assert links["query"].endswith(f"/mcp/runs/{run_id}/queries/execute")
    assert links["query_execute"] == links["query"]
    assert links["query_validate"].endswith(f"/mcp/runs/{run_id}/queries/validate")
    page_meta = payload["meta"]["page"]
    assert page_meta["offset"] == 0
    assert "self" in payload["links"]


def test_get_run_success(monkeypatch, tmp_path):
    _set_auth_env(monkeypatch)
    run_id = "sample-run"
    app, _ = _make_client(monkeypatch, tmp_path, run_id)

    from starlette.testclient import TestClient  # type: ignore
    from wepppy.query_engine.app.mcp import auth

    client = TestClient(app)
    token = _issue_token(auth, run_id)
    response = client.get(
        f"/mcp/runs/{run_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["id"] == run_id
    assert payload["meta"]["catalog"]["activated"] is True
    assert payload["meta"]["catalog"]["dataset_count"] == 1
    assert "trace_id" in payload["meta"]


def test_catalog_supports_parameter_aliases(monkeypatch, tmp_path):
    _set_auth_env(monkeypatch)

    run_id = "alias-run"
    app, _ = _make_client(monkeypatch, tmp_path, run_id)

    from starlette.testclient import TestClient  # type: ignore
    from wepppy.query_engine.app.mcp import auth

    client = TestClient(app)
    token = _issue_token(auth, run_id)

    response = client.get(
        f"/mcp/runs/{run_id}/catalog?limit_datasets=1&limit_fields=1&page_size=1&page_number=1",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["data"]) <= 1
    page_meta = payload["meta"]["page"]
    assert page_meta["size"] == 1
    assert page_meta["number"] == 1


def test_get_run_catalog(monkeypatch, tmp_path):
    _set_auth_env(monkeypatch)
    run_id = "catalog-run"
    files = [
        {
            "path": "datasets/one.parquet",
            "extension": ".parquet",
            "size_bytes": 10,
            "modified": "2024-01-01T00:00:00Z",
            "schema": {
                "fields": [
                    {"name": "a", "type": "INTEGER"},
                    {"name": "b", "type": "TEXT"},
                    {"name": "c", "type": "REAL"},
                ]
            },
        },
        {
            "path": "datasets/two.parquet",
            "extension": ".parquet",
            "size_bytes": 5,
            "modified": "2024-01-02T00:00:00Z",
            "schema": {
                "fields": [
                    {"name": "x", "type": "TEXT"},
                    {"name": "y", "type": "INTEGER"},
                ]
            },
        },
    ]
    app, _ = _make_client(monkeypatch, tmp_path, run_id, files=files)

    from starlette.testclient import TestClient  # type: ignore
    from wepppy.query_engine.app.mcp import auth

    client = TestClient(app)
    token = _issue_token(auth, run_id)
    response = client.get(
        f"/mcp/runs/{run_id}/catalog",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["data"]) == 2
    meta = payload["meta"]["catalog"]
    assert meta["total"] == 2
    assert meta["returned"] == 2
    assert meta["generated_at"] == "2024-05-07T16:33:22Z"
    first = payload["data"][0]
    assert "schema" in first
    assert len(first["schema"]["fields"]) == 3
    page_meta = payload["meta"]["page"]
    assert page_meta["number"] == 1
    assert page_meta["total_pages"] == 1
    assert "self" in payload["links"]
    assert "trace_id" in payload["meta"]


def test_get_run_catalog_limits(monkeypatch, tmp_path):
    _set_auth_env(monkeypatch)
    run_id = "catalog-limits"
    files = [
        {
            "path": "datasets/a.parquet",
            "extension": ".parquet",
            "size_bytes": 1,
            "modified": "2024-01-01T00:00:00Z",
            "schema": {
                "fields": [
                    {"name": "a", "type": "INTEGER"},
                    {"name": "b", "type": "TEXT"},
                ]
            },
        },
        {
            "path": "datasets/b.parquet",
            "extension": ".parquet",
            "size_bytes": 2,
            "modified": "2024-01-02T00:00:00Z",
            "schema": {
                "fields": [
                    {"name": "c", "type": "INTEGER"},
                ]
            },
        },
    ]
    app, _ = _make_client(monkeypatch, tmp_path, run_id, files=files)

    from starlette.testclient import TestClient  # type: ignore
    from wepppy.query_engine.app.mcp import auth

    client = TestClient(app)
    token = _issue_token(auth, run_id)
    response = client.get(
        f"/mcp/runs/{run_id}/catalog?limit[fields]=1&page[size]=1&page[number]=2",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["data"]) == 1
    fields = payload["data"][0]["schema"]["fields"]
    assert len(fields) == 1
    assert payload["meta"]["catalog"]["returned"] == 1
    page_meta = payload["meta"]["page"]
    assert page_meta["number"] == 2
    assert page_meta["size"] == 1
    assert page_meta["total_pages"] == 2
    assert "prev" in payload["links"]
    assert "trace_id" in payload["meta"]


def test_get_run_catalog_without_schema(monkeypatch, tmp_path):
    _set_auth_env(monkeypatch)
    run_id = "catalog-nofields"
    app, _ = _make_client(monkeypatch, tmp_path, run_id)

    from starlette.testclient import TestClient  # type: ignore
    from wepppy.query_engine.app.mcp import auth

    client = TestClient(app)
    token = _issue_token(auth, run_id)
    response = client.get(
        f"/mcp/runs/{run_id}/catalog?include_fields=false",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "schema" not in payload["data"][0]
    assert payload["meta"]["page"]["number"] == 1
    assert "trace_id" in payload["meta"]


def test_get_run_catalog_missing(monkeypatch, tmp_path):
    _set_auth_env(monkeypatch)
    run_id = "missing-catalog"
    app, _ = _make_client(monkeypatch, tmp_path, run_id, create_catalog=False)

    from starlette.testclient import TestClient  # type: ignore
    from wepppy.query_engine.app.mcp import auth

    client = TestClient(app)
    token = _issue_token(auth, run_id)
    response = client.get(
        f"/mcp/runs/{run_id}/catalog",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    payload = response.json()
    assert payload["errors"][0]["code"] == "catalog_missing"
    assert "trace_id" in payload["meta"]


def test_validate_query_success(monkeypatch, tmp_path):
    _set_auth_env(monkeypatch)
    run_id = "validate-run"
    files = [
        {
            "path": "datasets/one.parquet",
            "extension": ".parquet",
            "size_bytes": 1,
            "modified": "2024-01-01T00:00:00Z",
        }
    ]
    app, _ = _make_client(monkeypatch, tmp_path, run_id, files=files)

    from starlette.testclient import TestClient  # type: ignore
    from wepppy.query_engine.app.mcp import auth

    client = TestClient(app)
    token = _issue_token(auth, run_id, scopes="runs:read queries:validate")
    payload = {
        "datasets": ["datasets/one.parquet"],
        "limit": 5,
        "include_schema": True,
    }
    response = client.post(
        f"/mcp/runs/{run_id}/queries/validate",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )

    assert response.status_code == 200
    body = response.json()
    attrs = body["data"]["attributes"]
    assert attrs["missing_datasets"] == []
    normalized = attrs["normalized_payload"]
    assert normalized["datasets"][0]["path"] == "datasets/one.parquet"
    assert normalized["limit"] == 5
    assert body["meta"]["catalog"]["dataset_count"] == 1
    assert "trace_id" in body["meta"]


def test_validate_query_missing_dataset(monkeypatch, tmp_path):
    _set_auth_env(monkeypatch)
    run_id = "validate-missing"
    app, _ = _make_client(monkeypatch, tmp_path, run_id)

    from starlette.testclient import TestClient  # type: ignore
    from wepppy.query_engine.app.mcp import auth

    client = TestClient(app)
    token = _issue_token(auth, run_id, scopes="runs:read queries:validate")
    response = client.post(
        f"/mcp/runs/{run_id}/queries/validate",
        headers={"Authorization": f"Bearer {token}"},
        json={"datasets": ["missing.parquet"]},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["errors"][0]["code"] == "dataset_missing"
    assert "trace_id" in body["meta"]


def test_validate_query_requires_scope(monkeypatch, tmp_path):
    _set_auth_env(monkeypatch)
    run_id = "validate-scope"
    app, _ = _make_client(monkeypatch, tmp_path, run_id)

    from starlette.testclient import TestClient  # type: ignore
    from wepppy.query_engine.app.mcp import auth

    client = TestClient(app)
    token = _issue_token(auth, run_id, scopes="runs:read")
    response = client.post(
        f"/mcp/runs/{run_id}/queries/validate",
        headers={"Authorization": f"Bearer {token}"},
        json={"datasets": ["a.parquet"]},
    )

    assert response.status_code == 403
    payload = response.json()
    assert "trace_id" in payload.get("meta", {})


def test_validate_query_invalid_json(monkeypatch, tmp_path):
    _set_auth_env(monkeypatch)
    run_id = "validate-json"
    app, _ = _make_client(monkeypatch, tmp_path, run_id)

    from starlette.testclient import TestClient  # type: ignore
    from wepppy.query_engine.app.mcp import auth

    client = TestClient(app)
    token = _issue_token(auth, run_id, scopes="runs:read queries:validate")
    response = client.post(
        f"/mcp/runs/{run_id}/queries/validate",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "text/plain"},
        data="not-json",
    )

    assert response.status_code == 400
    payload = response.json()
    assert "trace_id" in payload.get("meta", {})


def test_list_runs_with_offset(monkeypatch, tmp_path):
    _set_auth_env(monkeypatch)
    run_ids = ["run-a", "run-b"]
    run_dirs = {run_id: _bootstrap_run(tmp_path, run_id) for run_id in run_ids}

    from wepppy.query_engine.app import helpers

    def fake_resolve(runid: str):
        if runid in run_dirs:
            return run_dirs[runid]
        raise FileNotFoundError(runid)

    monkeypatch.setattr(helpers, "resolve_run_path", fake_resolve)

    from wepppy.query_engine.app import server
    from wepppy.query_engine.app.mcp import router, auth

    reload(router)
    reload(server)

    from starlette.testclient import TestClient  # type: ignore

    app = server.create_app()
    client = TestClient(app)
    token = _issue_token(auth, runs=run_ids)

    response = client.get(
        "/mcp/runs?page[size]=1&page[offset]=1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["data"]) == 1
    assert payload["data"][0]["id"] == "run-b"
    page_meta = payload["meta"]["page"]
    assert page_meta["number"] == 2
    assert page_meta["offset"] == 1
    assert "prev" in payload["links"]
    assert "trace_id" in payload["meta"]


def test_get_run_forbidden(monkeypatch, tmp_path):
    _set_auth_env(monkeypatch)
    run_id = "accessible-run"
    other_run = "other-run"
    _bootstrap_run(tmp_path, run_id)

    from wepppy.query_engine.app import helpers

    def fake_resolve(runid: str):
        if runid == run_id:
            return tmp_path / run_id
        raise FileNotFoundError(runid)

    monkeypatch.setattr(helpers, "resolve_run_path", fake_resolve)

    from wepppy.query_engine.app import server
    from wepppy.query_engine.app.mcp import auth, router

    reload(router)
    reload(server)

    from starlette.testclient import TestClient  # type: ignore

    app = server.create_app()
    client = TestClient(app)
    token = _issue_token(auth, run_id)

    response = client.get(
        f"/mcp/runs/{other_run}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    body = response.json()
    assert body["errors"][0]["code"] == "not_found"
    assert "trace_id" in body.get("meta", {})

def test_activate_run_endpoint(monkeypatch, tmp_path):
    _set_auth_env(monkeypatch)
    run_id = "activate-run"
    app, _ = _make_client(monkeypatch, tmp_path, run_id)

    from starlette.testclient import TestClient  # type: ignore
    from wepppy.query_engine.app.mcp import router, auth

    monkeypatch.setattr(
        router,
        "activate_query_engine",
        lambda path: {"generated_at": "2024-05-07T16:33:22Z", "files": ["datasets/one.parquet"]},
    )

    client = TestClient(app)
    token = _issue_token(auth, run_id, scopes=["runs:read", "runs:activate"])
    response = client.post(
        f"/mcp/runs/{run_id}/activate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["attributes"]["status"] == "completed"
    assert body["data"]["attributes"]["dataset_count"] == 1
    assert "trace_id" in body["meta"]


def test_get_presets(monkeypatch, tmp_path):
    _set_auth_env(monkeypatch)
    run_id = "presets-run"
    app, _ = _make_client(monkeypatch, tmp_path, run_id)

    from starlette.testclient import TestClient  # type: ignore
    from wepppy.query_engine.app.mcp import auth

    client = TestClient(app)
    token = _issue_token(auth, run_id, scopes="runs:read")
    response = client.get(
        f"/mcp/runs/{run_id}/presets",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["data"]["attributes"]["categories"], list)
    assert "trace_id" in body["meta"]


def test_get_prompt_template(monkeypatch, tmp_path):
    _set_auth_env(monkeypatch)
    run_id = "prompt-run"
    app, _ = _make_client(monkeypatch, tmp_path, run_id)

    from starlette.testclient import TestClient  # type: ignore
    from wepppy.query_engine.app.mcp import router, auth

    monkeypatch.setattr(
        router,
        "_load_prompt_template",
        lambda: "Run {{RUN_ID}}\nEndpoint {{QUERY_ENDPOINT}}\n{{SCHEMA_SUMMARY}}",
    )

    client = TestClient(app)
    token = _issue_token(auth, run_id, scopes="runs:read")
    response = client.get(
        f"/mcp/runs/{run_id}/prompt-template",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    markdown = body["data"]["attributes"]["markdown"]
    assert "{{" not in markdown
    assert "trace_id" in body["meta"]


def test_execute_query_dry_run(monkeypatch, tmp_path):
    _set_auth_env(monkeypatch)
    run_id = "execute-dry"
    app, _ = _make_client(
        monkeypatch,
        tmp_path,
        run_id,
        files=[
            {
                "path": "datasets/one.parquet",
                "extension": ".parquet",
                "size_bytes": 1,
                "modified": "2024-01-01T00:00:00Z",
            }
        ],
    )

    from starlette.testclient import TestClient  # type: ignore
    from wepppy.query_engine.app.mcp import router, auth

    called = {"value": False}

    def fake_run_query(context, payload):
        called["value"] = True
        return SimpleNamespace(records=[], schema=None, row_count=0, formatted=None, sql=None)

    monkeypatch.setattr(router, "run_query", fake_run_query)
    monkeypatch.setattr(router, "resolve_run_context", lambda *args, **kwargs: SimpleNamespace())

    client = TestClient(app)
    token = _issue_token(auth, run_id, scopes=["runs:read", "queries:execute"])
    response = client.post(
        f"/mcp/runs/{run_id}/queries/execute?dry_run=true",
        headers={"Authorization": f"Bearer {token}"},
        json={"datasets": ["datasets/one.parquet"], "limit": 5},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["attributes"]["dry_run"] is True
    assert body["meta"]["execution"]["row_count"] == 0
    assert called["value"] is False
    assert "trace_id" in body["meta"]


def test_execute_query_success(monkeypatch, tmp_path):
    _set_auth_env(monkeypatch)
    run_id = "execute-success"
    app, _ = _make_client(
        monkeypatch,
        tmp_path,
        run_id,
        files=[
            {
                "path": "datasets/one.parquet",
                "extension": ".parquet",
                "size_bytes": 1,
                "modified": "2024-01-01T00:00:00Z",
            }
        ],
    )

    from starlette.testclient import TestClient  # type: ignore
    from wepppy.query_engine.app.mcp import router, auth

    monkeypatch.setattr(
        router,
        "run_query",
        lambda context, payload: SimpleNamespace(
            records=[{"soil_loss": 0.42}],
            schema=[{"name": "soil_loss", "type": "double"}],
            row_count=1,
            formatted=None,
            sql="SELECT soil_loss FROM foo",
        ),
    )
    monkeypatch.setattr(router, "resolve_run_context", lambda *args, **kwargs: SimpleNamespace())

    client = TestClient(app)
    token = _issue_token(auth, run_id, scopes=["runs:read", "queries:execute"])
    response = client.post(
        f"/mcp/runs/{run_id}/queries/execute",
        headers={"Authorization": f"Bearer {token}"},
        json={"datasets": ["datasets/one.parquet"], "limit": 10},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["attributes"]["dry_run"] is False
    assert body["data"]["attributes"]["result"]["row_count"] == 1
    assert body["meta"]["execution"]["row_count"] == 1
    assert "trace_id" in body["meta"]


def test_execute_query_requires_scope(monkeypatch, tmp_path):
    _set_auth_env(monkeypatch)
    run_id = "execute-scope"
    app, _ = _make_client(monkeypatch, tmp_path, run_id)

    from starlette.testclient import TestClient  # type: ignore
    from wepppy.query_engine.app.mcp import auth

    client = TestClient(app)
    token = _issue_token(auth, run_id, scopes="runs:read")
    response = client.post(
        f"/mcp/runs/{run_id}/queries/execute",
        headers={"Authorization": f"Bearer {token}"},
        json={"datasets": ["a.parquet"]},
    )

    assert response.status_code == 403
    payload = response.json()
    assert "trace_id" in payload.get("meta", {})
