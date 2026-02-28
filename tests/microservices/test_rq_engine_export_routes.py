from __future__ import annotations

from pathlib import Path

import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import export_routes
from wepppy.runtime_paths.errors import NoDirError

pytestmark = pytest.mark.microservice


def _stub_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(export_routes, "require_jwt", lambda request, required_scopes=None: {})
    monkeypatch.setattr(export_routes, "authorize_run_access", lambda claims, runid: None)


class _RonStub:
    def __init__(self, export_arc_dir: str) -> None:
        self.export_arc_dir = export_arc_dir


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
    assert payload["error"]["message"] == "locked"


def test_export_geopackage_attr_shaped_runtime_error_uses_generic_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runid = "run-export-attr-runtime"
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
        lambda wd: (_ for _ in ()).throw(_AttrShapedError()),
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


def test_export_geodatabase_propagates_nodir_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runid = "run-export-gdb-nodir"
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
        response = client.get(f"/api/runs/{runid}/cfg/export/geodatabase")

    assert response.status_code == 503
    payload = response.json()
    assert payload["error"]["code"] == "NODIR_LOCKED"
    assert payload["error"]["message"] == "locked"


def test_export_prep_details_propagates_nodir_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runid = "run-export-prep-nodir"
    run_root = tmp_path / runid
    run_root.mkdir()

    _stub_auth(monkeypatch)
    monkeypatch.setattr(export_routes, "get_wd", lambda runid, prefer_active=False: str(run_root))

    import wepppy.export as export_pkg
    import wepppy.export.prep_details as prep_details_pkg

    monkeypatch.setattr(export_pkg, "archive_project", lambda wd: str(run_root / "prep.zip"))
    monkeypatch.setattr(
        prep_details_pkg,
        "export_hillslopes_prep_details",
        lambda wd: (_ for _ in ()).throw(
            NoDirError(http_status=409, code="NODIR_MIXED_STATE", message="mixed")
        ),
    )
    monkeypatch.setattr(
        prep_details_pkg,
        "export_channels_prep_details",
        lambda wd: str(run_root / "channels.gpkg"),
    )

    with TestClient(rq_engine.app) as client:
        response = client.get(f"/api/runs/{runid}/cfg/export/prep_details")

    assert response.status_code == 409
    payload = response.json()
    assert payload["error"]["code"] == "NODIR_MIXED_STATE"
    assert payload["error"]["message"] == "mixed"
