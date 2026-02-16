from __future__ import annotations

from pathlib import Path

import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import export_routes
from wepppy.nodir.errors import NoDirError

pytestmark = pytest.mark.microservice


def _stub_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(export_routes, "require_jwt", lambda request, required_scopes=None: {})
    monkeypatch.setattr(export_routes, "authorize_run_access", lambda claims, runid: None)


class _RonStub:
    def __init__(self, export_arc_dir: str) -> None:
        self.export_arc_dir = export_arc_dir


def test_export_geopackage_propagates_nodir_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runid = "run-export-nodir"
    run_root = tmp_path / runid
    run_root.mkdir()
    export_dir = run_root / "export" / "arcmap"
    export_dir.mkdir(parents=True)

    _stub_auth(monkeypatch)
    monkeypatch.setattr(export_routes, "get_wd", lambda runid, prefer_active=False: str(run_root))
    monkeypatch.setattr(export_routes.Ron, "getInstance", lambda wd: _RonStub(str(export_dir)))

    import wepppy.export as export_pkg

    monkeypatch.setattr(
        export_pkg,
        "gpkg_export",
        lambda wd: (_ for _ in ()).throw(
            NoDirError(http_status=503, code="NODIR_LOCKED", message="locked")
        ),
    )

    with TestClient(rq_engine.app) as client:
        response = client.get(f"/api/runs/{runid}/cfg/export/geopackage")

    assert response.status_code == 503
    payload = response.json()
    assert payload["error"]["code"] == "NODIR_LOCKED"


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
