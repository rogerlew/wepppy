from __future__ import annotations

import asyncio
import re
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

pytest.importorskip("starlette")

from starlette.testclient import TestClient

from wepppy.query_engine.formatter import QueryResult

_CORRELATION_HEADER = "X-Correlation-ID"
_CORRELATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


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
    correlation_id = "cid-query-console-1"
    response_no_slash_get = client.get(f"/runs/{runid}/query")
    response_trailing_slash_get = client.get(
        f"/runs/{runid}/query/",
        headers={_CORRELATION_HEADER: correlation_id},
    )
    assert response_no_slash_get.status_code == 200
    assert response_trailing_slash_get.status_code == 200
    assert _CORRELATION_HEADER in response_no_slash_get.headers
    assert _CORRELATION_ID_PATTERN.match(response_no_slash_get.headers[_CORRELATION_HEADER])
    assert response_trailing_slash_get.headers[_CORRELATION_HEADER] == correlation_id

    payload: Dict[str, Any] = {
        "datasets": ["datasets/example.parquet"],
        "include_schema": True,
        "limit": 1,
    }

    response_no_slash_post = client.post(
        f"/runs/{runid}/query",
        json=payload,
        headers={_CORRELATION_HEADER: correlation_id},
    )
    response_trailing_slash_post = client.post(
        f"/runs/{runid}/query/",
        json=payload,
        headers={_CORRELATION_HEADER: correlation_id},
    )

    assert response_no_slash_post.status_code == 200
    assert response_trailing_slash_post.status_code == 200
    assert response_trailing_slash_post.json() == response_no_slash_post.json()
    assert response_trailing_slash_post.headers[_CORRELATION_HEADER] == correlation_id


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
        assert _CORRELATION_HEADER in response_get.headers
        assert _CORRELATION_ID_PATTERN.match(response_get.headers[_CORRELATION_HEADER])

        # POST request should also fail with 400
        response_post = client.post(garbage_path, json={"datasets": ["test.parquet"]})
        assert response_post.status_code == 400, (
            f"POST {garbage_path} should return 400, got {response_post.status_code}"
        )
        data = response_post.json()
        assert "error" in data
        assert "scenario" in data["error"].lower() or "body" in data["error"].lower()
        assert _CORRELATION_HEADER in response_post.headers
        assert _CORRELATION_ID_PATTERN.match(response_post.headers[_CORRELATION_HEADER])


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
    assert _CORRELATION_HEADER in response.headers
    assert _CORRELATION_ID_PATTERN.match(response.headers[_CORRELATION_HEADER])

    # Verify scenario was passed to resolve_run_context
    assert len(captured_scenario) == 1
    assert captured_scenario[0] == "mulch_30_sbs_map"


@pytest.mark.unit
@pytest.mark.parametrize("exc_cls", [ValueError, TypeError])
def test_query_endpoint_invalid_payload_returns_422_with_expected_envelope(monkeypatch, tmp_path, exc_cls):
    from wepppy.query_engine.app import server

    runid = "sample-run"
    run_dir = tmp_path / runid
    run_dir.mkdir(parents=True, exist_ok=True)

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
        return SimpleNamespace(runid=runid_path, base_dir=run_dir, scenario=scenario)

    def fake_query_request(**_body):
        raise exc_cls("boom")

    monkeypatch.setattr(server, "resolve_run_path", fake_resolve_run_path)
    monkeypatch.setattr(server, "resolve_run_context", fake_resolve_context)
    monkeypatch.setattr(server, "QueryRequest", fake_query_request)

    app = server.create_app()
    client = TestClient(app)

    response = client.post(f"/runs/{runid}/query", json={"datasets": ["test.parquet"]})
    assert response.status_code == 422
    assert _CORRELATION_HEADER in response.headers
    assert _CORRELATION_ID_PATTERN.match(response.headers[_CORRELATION_HEADER])

    data = response.json()
    assert set(data.keys()) == {"error", "stacktrace", "exc_info", "status_code"}
    assert data["status_code"] == 422
    assert data["stacktrace"] == data["exc_info"]
    assert "Invalid query payload:" in data["error"]


@pytest.mark.unit
def test_query_engine_preflight_emits_correlation_id_header() -> None:
    from wepppy.query_engine.app import server

    app = server.create_app()
    client = TestClient(app)

    response = client.options(
        "/runs/demo/query",
        headers={
            "Origin": "https://example.test",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert _CORRELATION_HEADER in response.headers
    assert _CORRELATION_ID_PATTERN.match(response.headers[_CORRELATION_HEADER])


def _reset_bandwidth_rate_limit_state(server_module) -> None:
    with server_module._BANDWIDTH_RATE_LIMIT_LOCK:
        server_module._BANDWIDTH_RATE_LIMIT_BUCKETS.clear()


@pytest.mark.unit
def test_diagnostics_bandwidth_download_returns_deterministic_payload() -> None:
    from wepppy.query_engine.app import server

    _reset_bandwidth_rate_limit_state(server)

    app = server.create_app()
    client = TestClient(app)

    response = client.get("/diagnostics/bandwidth/download?bytes=4096")

    assert response.status_code == 200
    assert response.headers.get("Cache-Control") == "no-store"
    assert response.headers.get("Content-Length") == "4096"
    assert response.headers.get("content-type", "").startswith("application/octet-stream")
    assert len(response.content) == 4096
    assert response.content.startswith(server._BANDWIDTH_PATTERN)


@pytest.mark.unit
def test_diagnostics_bandwidth_download_blocks_cross_origin() -> None:
    from wepppy.query_engine.app import server

    _reset_bandwidth_rate_limit_state(server)

    app = server.create_app()
    client = TestClient(app)

    response = client.get(
        "/diagnostics/bandwidth/download?bytes=1024",
        headers={"Origin": "https://evil.example", "Host": "query.example"},
    )

    assert response.status_code == 403
    assert response.headers.get("Cache-Control") == "no-store"
    assert response.json()["error"]["code"] == "cross_origin_blocked"


@pytest.mark.unit
def test_diagnostics_bandwidth_download_rejects_invalid_bytes() -> None:
    from wepppy.query_engine.app import server

    _reset_bandwidth_rate_limit_state(server)

    app = server.create_app()
    client = TestClient(app)

    invalid_response = client.get("/diagnostics/bandwidth/download?bytes=zero")
    assert invalid_response.status_code == 400
    assert invalid_response.headers.get("Cache-Control") == "no-store"
    assert invalid_response.json()["error"]["code"] == "invalid_probe_size"

    too_large = server._BANDWIDTH_MAX_BYTES + 1
    too_large_response = client.get(f"/diagnostics/bandwidth/download?bytes={too_large}")
    assert too_large_response.status_code == 413
    assert too_large_response.headers.get("Cache-Control") == "no-store"
    assert too_large_response.json()["error"]["code"] == "probe_too_large"


@pytest.mark.unit
def test_diagnostics_bandwidth_download_busy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    from wepppy.query_engine.app import server

    _reset_bandwidth_rate_limit_state(server)
    monkeypatch.setattr(server, "_BANDWIDTH_SEMAPHORE_WAIT_SECONDS", 0)
    monkeypatch.setattr(server, "_BANDWIDTH_SEMAPHORE", asyncio.Semaphore(0))

    app = server.create_app()
    client = TestClient(app)

    response = client.get("/diagnostics/bandwidth/download?bytes=1024")
    assert response.status_code == 503
    assert response.headers.get("Cache-Control") == "no-store"
    assert response.json()["error"]["code"] == "busy"


@pytest.mark.unit
def test_diagnostics_bandwidth_upload_reports_bytes_received() -> None:
    from wepppy.query_engine.app import server

    _reset_bandwidth_rate_limit_state(server)

    app = server.create_app()
    client = TestClient(app)

    payload = b"x" * 2048
    response = client.post(
        "/diagnostics/bandwidth/upload",
        content=payload,
        headers={"content-type": "application/octet-stream"},
    )

    assert response.status_code == 200
    assert response.headers.get("Cache-Control") == "no-store"
    data = response.json()
    assert data["ok"] is True
    assert data["bytes_received"] == len(payload)
    assert data["elapsed_ms"] >= 0


@pytest.mark.unit
def test_diagnostics_bandwidth_upload_blocks_cross_origin() -> None:
    from wepppy.query_engine.app import server

    _reset_bandwidth_rate_limit_state(server)

    app = server.create_app()
    client = TestClient(app)

    response = client.post(
        "/diagnostics/bandwidth/upload",
        content=b"abc",
        headers={
            "Origin": "https://evil.example",
            "Host": "query.example",
            "content-type": "application/octet-stream",
        },
    )

    assert response.status_code == 403
    assert response.headers.get("Cache-Control") == "no-store"
    assert response.json()["error"]["code"] == "cross_origin_blocked"


@pytest.mark.unit
def test_diagnostics_bandwidth_upload_rejects_oversized_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    from wepppy.query_engine.app import server

    _reset_bandwidth_rate_limit_state(server)
    monkeypatch.setattr(server, "_BANDWIDTH_MAX_BYTES", 1024)

    app = server.create_app()
    client = TestClient(app)

    response = client.post(
        "/diagnostics/bandwidth/upload",
        content=(b"y" * 2048),
        headers={"content-type": "application/octet-stream"},
    )

    assert response.status_code == 413
    assert response.headers.get("Cache-Control") == "no-store"
    assert response.json()["error"]["code"] == "upload_too_large"


@pytest.mark.unit
def test_diagnostics_bandwidth_upload_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    from wepppy.query_engine.app import server

    _reset_bandwidth_rate_limit_state(server)
    monkeypatch.setattr(server, "_BANDWIDTH_REQUEST_TIMEOUT_SECONDS", 0)

    app = server.create_app()
    client = TestClient(app)

    response = client.post(
        "/diagnostics/bandwidth/upload",
        content=(b"x" * 1024),
        headers={"content-type": "application/octet-stream"},
    )

    assert response.status_code == 408
    assert response.headers.get("Cache-Control") == "no-store"
    assert response.json()["error"]["code"] == "upload_timeout"


@pytest.mark.unit
def test_diagnostics_bandwidth_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    from wepppy.query_engine.app import server

    _reset_bandwidth_rate_limit_state(server)
    monkeypatch.setattr(server, "_BANDWIDTH_RATE_LIMIT_MAX_REQUESTS", 1)
    monkeypatch.setattr(server, "_BANDWIDTH_RATE_LIMIT_WINDOW_SECONDS", 60)

    app = server.create_app()
    client = TestClient(app)

    first = client.get("/diagnostics/bandwidth/download?bytes=1024")
    second = client.get("/diagnostics/bandwidth/download?bytes=1024")

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.headers.get("Cache-Control") == "no-store"
    assert second.json()["error"]["code"] == "rate_limited"
    assert int(second.headers.get("Retry-After", "0")) >= 1


@pytest.mark.unit
def test_diagnostics_bandwidth_upload_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    from wepppy.query_engine.app import server

    _reset_bandwidth_rate_limit_state(server)
    monkeypatch.setattr(server, "_BANDWIDTH_RATE_LIMIT_MAX_REQUESTS", 1)
    monkeypatch.setattr(server, "_BANDWIDTH_RATE_LIMIT_WINDOW_SECONDS", 60)

    app = server.create_app()
    client = TestClient(app)

    first = client.post(
        "/diagnostics/bandwidth/upload",
        content=b"a",
        headers={"content-type": "application/octet-stream"},
    )
    second = client.post(
        "/diagnostics/bandwidth/upload",
        content=b"b",
        headers={"content-type": "application/octet-stream"},
    )

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.headers.get("Cache-Control") == "no-store"
    assert second.json()["error"]["code"] == "rate_limited"


@pytest.mark.unit
def test_bandwidth_rate_limit_key_uses_rightmost_forwarded_for() -> None:
    from wepppy.query_engine.app import server

    request = SimpleNamespace(
        headers={"X-Forwarded-For": "198.51.100.11, 203.0.113.7"},
        client=SimpleNamespace(host="10.0.0.9"),
        url=SimpleNamespace(path="/diagnostics/bandwidth/download"),
    )
    key = server._bandwidth_rate_limit_key(request)
    assert key.startswith("203.0.113.7:")


@pytest.mark.unit
def test_read_positive_int_env_invalid_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    from wepppy.query_engine.app import server

    monkeypatch.setenv("QUERY_ENGINE_TEST_INT_VALUE", "not-an-int")
    value = server._read_positive_int_env("QUERY_ENGINE_TEST_INT_VALUE", 9, 1)
    assert value == 9
