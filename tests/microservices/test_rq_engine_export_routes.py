from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import export_routes
from wepppy.runtime_paths.errors import NoDirError

pytestmark = pytest.mark.microservice


def _stub_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(export_routes, "require_jwt", lambda request, required_scopes=None: {})
    monkeypatch.setattr(export_routes, "authorize_run_access", lambda claims, runid: None)


class _AttrShapedError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("attr-shaped runtime error")
        self.http_status = 409
        self.code = "ATTR_SHAPED"
        self.message = "attr-shaped"


def test_export_geopackage_propagates_nodir_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runid = "run-export-nodir"
    run_root = tmp_path / runid
    run_root.mkdir()

    _stub_auth(monkeypatch)
    monkeypatch.setattr(export_routes, "get_wd", lambda runid, prefer_active=False: str(run_root))
    monkeypatch.setattr(
        export_routes,
        "_execute_features_export_profile",
        lambda **kwargs: (_ for _ in ()).throw(
            NoDirError(http_status=503, code="NODIR_LOCKED", message="locked")
        ),
    )

    with TestClient(rq_engine.app) as client:
        response = client.get(f"/api/runs/{runid}/cfg/export/geopackage")

    assert response.status_code == 503
    payload = response.json()
    assert payload["error"]["code"] == "NODIR_LOCKED"
    assert payload["error"]["message"] == "locked"


def test_export_geopackage_attr_shaped_runtime_error_uses_generic_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runid = "run-export-attr-runtime"
    run_root = tmp_path / runid
    run_root.mkdir()

    _stub_auth(monkeypatch)
    monkeypatch.setattr(export_routes, "get_wd", lambda runid, prefer_active=False: str(run_root))
    monkeypatch.setattr(
        export_routes,
        "_execute_features_export_profile",
        lambda **kwargs: (_ for _ in ()).throw(_AttrShapedError()),
    )

    with TestClient(rq_engine.app) as client:
        response = client.get(f"/api/runs/{runid}/cfg/export/geopackage")

    assert response.status_code == 500
    payload = response.json()
    assert payload["error"]["message"] == "Error exporting geopackage"
    assert payload["error"].get("code") != "ATTR_SHAPED"


def test_export_ermit_propagates_nodir_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runid = "run-export-ermit-nodir"
    run_root = tmp_path / runid
    run_root.mkdir()

    _stub_auth(monkeypatch)
    monkeypatch.setattr(export_routes, "get_wd", lambda runid, prefer_active=False: str(run_root))

    import wepppy.export as export_pkg

    monkeypatch.setattr(
        export_pkg,
        "create_ermit_input",
        lambda wd: (_ for _ in ()).throw(
            NoDirError(
                http_status=500,
                code="NODIR_INVALID_ARCHIVE",
                message="invalid archive",
            )
        ),
    )

    with TestClient(rq_engine.app) as client:
        response = client.get(f"/api/runs/{runid}/cfg/export/ermit")

    assert response.status_code == 500
    payload = response.json()
    assert payload["error"]["code"] == "NODIR_INVALID_ARCHIVE"
    assert payload["error"]["message"] == "invalid archive"


def test_export_ermit_submit_enqueues_rq_job(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runid = "run-export-ermit-submit"
    run_root = tmp_path / runid
    run_root.mkdir()
    enqueued: dict[str, object] = {}

    _stub_auth(monkeypatch)
    monkeypatch.setattr(export_routes, "get_wd", lambda runid, prefer_active=False: str(run_root))
    monkeypatch.setattr(export_routes.RedisPrep, "tryGetInstance", lambda wd: None)

    class DummyRedis:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class DummyQueue:
        def __init__(self, connection):
            self.connection = connection

        def enqueue_call(self, func, args, timeout):
            enqueued["func"] = func
            enqueued["args"] = args
            enqueued["timeout"] = timeout
            return SimpleNamespace(id="ermit-job-1")

    monkeypatch.setattr(export_routes.redis, "Redis", DummyRedis)
    monkeypatch.setattr(export_routes, "Queue", DummyQueue)

    with TestClient(rq_engine.app) as client:
        response = client.post(f"/api/runs/{runid}/cfg/export/ermit")

    assert response.status_code == 202
    payload = response.json()
    assert payload["job_id"] == "ermit-job-1"
    assert payload["status_url"] == "/rq-engine/api/jobstatus/ermit-job-1"
    assert payload["download_url"] == f"/rq-engine/api/runs/{runid}/cfg/export/ermit/job/ermit-job-1/download"
    assert enqueued["func"] is export_routes.run_ermit_export_rq
    assert enqueued["args"] == (runid, "cfg", str(run_root))


def test_export_ermit_download_returns_finished_job_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runid = "run-export-ermit-download"
    run_root = tmp_path / runid
    run_root.mkdir()
    artifact_path = run_root / "export" / "ERMiT_input_demo.zip"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_bytes(b"ermit-zip")

    _stub_auth(monkeypatch)
    monkeypatch.setattr(export_routes, "get_wd", lambda runid, prefer_active=False: str(run_root))
    monkeypatch.setattr(
        export_routes,
        "get_wepppy_rq_job_info",
        lambda job_id: {
            "job_id": job_id,
            "runid": runid,
            "status": "finished",
            "result": {
                "artifact_relpath": "export/ERMiT_input_demo.zip",
                "filename": "ERMiT_input_demo.zip",
            },
        },
    )

    with TestClient(rq_engine.app) as client:
        response = client.get(f"/api/runs/{runid}/cfg/export/ermit/job/ermit-job-2/download")

    assert response.status_code == 200
    assert response.content == b"ermit-zip"
    assert "ERMiT_input_demo.zip" in response.headers.get("content-disposition", "")


def test_export_geodatabase_propagates_nodir_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runid = "run-export-gdb-nodir"
    run_root = tmp_path / runid
    run_root.mkdir()

    _stub_auth(monkeypatch)
    monkeypatch.setattr(export_routes, "get_wd", lambda runid, prefer_active=False: str(run_root))
    monkeypatch.setattr(
        export_routes,
        "_execute_features_export_profile",
        lambda **kwargs: (_ for _ in ()).throw(
            NoDirError(http_status=503, code="NODIR_LOCKED", message="locked")
        ),
    )

    with TestClient(rq_engine.app) as client:
        response = client.get(f"/api/runs/{runid}/cfg/export/geodatabase")

    assert response.status_code == 503
    payload = response.json()
    assert payload["error"]["code"] == "NODIR_LOCKED"
    assert payload["error"]["message"] == "locked"


def test_export_geodatabase_prefers_published_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runid = "run-export-gdb-published"
    run_root = tmp_path / runid
    run_root.mkdir()
    artifact_path = run_root / "export" / "features" / "artifacts" / "artifact-1" / "features_export.gdb.zip"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_bytes(b"gdb-zip")

    _stub_auth(monkeypatch)
    monkeypatch.setattr(export_routes, "get_wd", lambda runid, prefer_active=False: str(run_root))
    monkeypatch.setattr(
        export_routes,
        "resolve_published_artifact_path",
        lambda wd, profile: (artifact_path, "export/features/artifacts/artifact-1/features_export.gdb.zip"),
    )
    monkeypatch.setattr(
        export_routes,
        "_execute_features_export_profile",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("unexpected on-demand execution")),
    )

    with TestClient(rq_engine.app) as client:
        response = client.get(f"/api/runs/{runid}/cfg/export/geodatabase")

    assert response.status_code == 200
    assert "zip" in response.headers.get("content-type", "").lower()


def test_export_prep_details_propagates_nodir_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runid = "run-export-prep-nodir"
    run_root = tmp_path / runid
    run_root.mkdir()

    _stub_auth(monkeypatch)
    monkeypatch.setattr(export_routes, "get_wd", lambda runid, prefer_active=False: str(run_root))

    monkeypatch.setattr(
        export_routes,
        "_execute_features_export_profile",
        lambda **kwargs: (_ for _ in ()).throw(
            NoDirError(http_status=409, code="NODIR_MIXED_STATE", message="mixed")
        ),
    )

    with TestClient(rq_engine.app) as client:
        response = client.get(f"/api/runs/{runid}/cfg/export/prep_details")

    assert response.status_code == 409
    payload = response.json()
    assert payload["error"]["code"] == "NODIR_MIXED_STATE"
    assert payload["error"]["message"] == "mixed"
