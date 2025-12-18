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

    def fake_resolve_context(
        runid_path: str,
        *,
        scenario=None,
        auto_activate: bool = True,
        run_interchange: bool = True,
        force_refresh: bool = False,
    ):
        return SimpleNamespace(
            runid=runid_path,
            base_dir=run_dir,
            scenario=scenario,
            catalog=dummy_catalog,
        )

    def fake_activate_query_engine(path, *, run_interchange: bool = True, force_refresh: bool = False):
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


@pytest.mark.unit
def test_query_endpoint_rejects_garbage_paths_with_pups(monkeypatch, tmp_path):
    """Verify that URLs embedding _pups/omni/scenarios/... in the runid are rejected.

    Scenario queries must use the 'scenario' body parameter, NOT URL
    path manipulation. This test guards against regressions where
    developers might try to append scenario paths to the URL instead
    of using the designed body parameter interface.

    The route pattern is /runs/{runid:path}/query - so _pups would be
    captured as part of the runid parameter. We detect this and return 400.

    See: wepppy/query_engine/README.md "Querying Omni Scenarios"
    """
    from wepppy.query_engine.app import server

    app = server.create_app()
    client = TestClient(app)

    # These garbage paths embed _pups or _outputs in the runid segment
    # Route: /runs/{runid:path}/query captures everything before /query as runid
    garbage_paths = [
        # _pups embedded in what would be the runid
        "/runs/abc123/def/_pups/omni/scenarios/mulch_30/query",
        "/runs/testrun/cfg/_pups/omni/query",
        # _outputs embedded in what would be the runid
        "/runs/testrun/cfg/_outputs/wepp/query",
        "/runs/testrun/cfg/_outputs/query",
    ]

    for garbage_path in garbage_paths:
        # GET request should fail with 400
        response_get = client.get(garbage_path)
        assert response_get.status_code == 400, (
            f"GET {garbage_path} should return 400, got {response_get.status_code}"
        )
        assert "scenario" in response_get.text.lower() or "_pups" in response_get.text.lower()

        # POST request should also fail with 400
        response_post = client.post(garbage_path, json={"datasets": ["test.parquet"]})
        assert response_post.status_code == 400, (
            f"POST {garbage_path} should return 400, got {response_post.status_code}"
        )
        data = response_post.json()
        assert "error" in data
        assert "scenario" in data["error"].lower() or "body" in data["error"].lower()


@pytest.mark.unit
def test_query_endpoint_accepts_scenario_in_body(monkeypatch, tmp_path):
    """Verify that scenario parameter in body is properly passed to resolve_run_context.

    This is the CORRECT way to query scenario data - via the body parameter,
    not URL manipulation.
    """
    from wepppy.query_engine.app import server
    from wepppy.query_engine.formatter import QueryResult

    runid = "sample-run"
    run_dir = tmp_path / runid
    run_dir.mkdir(parents=True, exist_ok=True)

    captured_scenario = []

    class DummyCatalog:
        def entries(self):
            return [SimpleNamespace(path="test.parquet")]

        def has(self, rel_path: str) -> bool:
            return True

        def get_column_type(self, rel_path: str, column: str) -> str:
            return "TEXT"

    def fake_resolve_run_path(runid_param: str):
        if runid_param != runid:
            raise FileNotFoundError(runid_param)
        return run_dir

    def fake_resolve_context(
        runid_path: str,
        *,
        scenario=None,
        auto_activate: bool = True,
        run_interchange: bool = True,
        force_refresh: bool = False,
    ):
        # Capture the scenario parameter to verify it was passed
        captured_scenario.append(scenario)
        return SimpleNamespace(
            runid=runid_path,
            base_dir=run_dir,
            scenario=scenario,
            catalog=DummyCatalog(),
        )

    def fake_run_query(context, payload):
        return QueryResult(records=[{"value": 1}], schema=[], row_count=1, sql="SELECT 1")

    monkeypatch.setattr(server, "resolve_run_path", fake_resolve_run_path)
    monkeypatch.setattr(server, "resolve_run_context", fake_resolve_context)
    monkeypatch.setattr(server, "run_query", fake_run_query)

    app = server.create_app()
    client = TestClient(app)

    # Query with scenario in body - this is the correct approach
    payload = {
        "scenario": "mulch_30_sbs_map",
        "datasets": ["test.parquet"],
        "limit": 1,
    }

    response = client.post(f"/runs/{runid}/query", json=payload)
    assert response.status_code == 200

    # Verify scenario was passed to resolve_run_context
    assert len(captured_scenario) == 1
    assert captured_scenario[0] == "mulch_30_sbs_map"
