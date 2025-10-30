from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

pytest.importorskip("starlette")

from starlette.testclient import TestClient

from wepppy.query_engine.formatter import QueryResult


@pytest.mark.unit
def test_query_endpoint_accepts_trailing_slash(monkeypatch, tmp_path):
    from wepppy.query_engine.app import server

    runid = "sample-run"
    run_dir = tmp_path / runid
    run_dir.mkdir(parents=True, exist_ok=True)

    class DummyCatalog:
        def __init__(self) -> None:
            entry = SimpleNamespace(path="datasets/example.parquet")
            self._entries: List[Any] = [entry]

        def entries(self) -> List[Any]:
            return list(self._entries)

        def has(self, rel_path: str) -> bool:
            return True

        def get_column_type(self, rel_path: str, column: str) -> str:
            return "TEXT"

    dummy_catalog = DummyCatalog()

    def fake_resolve_run_path(runid_param: str):
        if runid_param not in {runid, str(run_dir)}:
            raise FileNotFoundError(runid_param)
        return run_dir

    def fake_resolve_context(runid_path: str, *, auto_activate: bool = True):
        return SimpleNamespace(
            runid=runid_path,
            base_dir=run_dir,
            scenario=None,
            catalog=dummy_catalog,
        )

    def fake_activate_query_engine(path, *, run_interchange: bool = True):
        return {}

    def fake_run_query(context, payload):
        return QueryResult(records=[{"value": 1}], schema=[], row_count=1, sql="SELECT 1")

    monkeypatch.setattr(server, "resolve_run_path", fake_resolve_run_path)
    monkeypatch.setattr(server, "resolve_run_context", fake_resolve_context)
    monkeypatch.setattr(server, "activate_query_engine", fake_activate_query_engine)
    monkeypatch.setattr(server, "run_query", fake_run_query)

    app = server.create_app()
    client = TestClient(app)

    # GET console renders without and with trailing slash
    response_no_slash_get = client.get(f"/runs/{runid}/query")
    response_trailing_slash_get = client.get(f"/runs/{runid}/query/")
    assert response_no_slash_get.status_code == 200
    assert response_trailing_slash_get.status_code == 200

    payload: Dict[str, Any] = {
        "datasets": ["datasets/example.parquet"],
        "include_schema": True,
        "limit": 1,
    }

    response_no_slash_post = client.post(f"/runs/{runid}/query", json=payload)
    response_trailing_slash_post = client.post(f"/runs/{runid}/query/", json=payload)

    assert response_no_slash_post.status_code == 200
    assert response_trailing_slash_post.status_code == 200
    assert response_trailing_slash_post.json() == response_no_slash_post.json()
