"""Tests for the PATH-CE inline report routes (subtree restriction + CSP)."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

TestClient = pytest.importorskip("starlette.testclient").TestClient

pytestmark = pytest.mark.microservice

RUNID = "demo-run"
CONFIG = "cfg"
BASE = f"/weppcloud/runs/{RUNID}/{CONFIG}/report/path_ce"


def _allow_auth(*args, **kwargs):
    import wepppy.microservices.browse.auth as auth_mod

    return auth_mod.AuthContext(
        claims={"token_class": "user", "roles": ["User"], "sub": "1"},
        token_class="user",
        roles=frozenset({"user"}),
    )


@pytest.fixture
def report_client(monkeypatch, tmp_path):
    import wepppy.microservices.browse.report as report_mod
    import wepppy.microservices.browse.browse as browse_mod

    # Nearby browse tests reload auth to vary process configuration. Reload this
    # dependent module so its imported BrowseAuthError remains the current class.
    report_mod = importlib.reload(report_mod)

    run_root = tmp_path / RUNID
    report_dir = run_root / "path" / "report"
    (report_dir / "static" / "js" / "vendor").mkdir(parents=True)
    (report_dir / "static" / "downloads").mkdir(parents=True)
    (report_dir / "PATH_CE_Report.html").write_text("<html><body>report</body></html>")
    (report_dir / "static" / "js" / "vendor" / "plotly.min.js").write_text("window.Plotly={};")
    (report_dir / "static" / "downloads" / "PATH_hillslope_treatment_summary.csv").write_text("a,b\n1,2\n")
    (report_dir / "static" / "subcatchments.WGS.geojson").write_text('{"type":"FeatureCollection","features":[]}')
    # sensitive file OUTSIDE the report subtree
    (run_root / "path" / "path_ce_final_data.parquet").write_bytes(b"secret")
    (run_root / "watershed").mkdir(parents=True)
    (run_root / "watershed" / "hillslopes.parquet").write_bytes(b"secret")

    monkeypatch.setattr(report_mod, "authorize_run_request", _allow_auth)
    monkeypatch.setattr(report_mod, "get_wd", lambda _runid, prefer_active=False: str(run_root))

    app = browse_mod.create_app()
    with TestClient(app) as client:
        yield client, run_root


def test_serves_report_document_inline_with_csp(report_client):
    client, _ = report_client
    response = client.get(f"{BASE}/")
    assert response.status_code == 200
    assert response.text == "<html><body>report</body></html>"
    assert response.headers["content-type"].startswith("text/html")
    csp = response.headers["content-security-policy"]
    assert "sandbox" in csp
    assert "allow-same-origin" not in csp, "sandbox must keep the report in an opaque origin"
    assert "allow-popups" not in csp, "popups are an outbound channel connect-src cannot govern"
    assert "base-uri 'none'" in csp
    assert "form-action 'none'" in csp
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "private, no-store"
    assert "attachment" not in response.headers.get("content-disposition", "")


def test_active_document_types_download_instead_of_render(report_client):
    """Scripted SVG/XHTML would execute in the service origin — force download."""
    client, run_root = report_client
    report_dir = run_root / "path" / "report"
    (report_dir / "figure.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>')
    (report_dir / "page.xhtml").write_text('<html xmlns="http://www.w3.org/1999/xhtml"><script>alert(1)</script></html>')

    for name in ("figure.svg", "page.xhtml"):
        response = client.get(f"{BASE}/{name}")
        assert response.status_code == 200, name
        assert response.headers["content-type"] == "application/octet-stream", name
        assert "attachment" in response.headers.get("content-disposition", ""), name


def test_rejects_symlinked_report_root(report_client, tmp_path):
    """A symlinked path/ or path/report/ must not bless a foreign tree."""
    client, run_root = report_client
    outside = tmp_path / "outside-tree"
    outside.mkdir()
    (outside / "PATH_CE_Report.html").write_text("<html>foreign</html>")

    report_dir = run_root / "path" / "report"
    import shutil as _shutil

    _shutil.rmtree(report_dir)
    report_dir.symlink_to(outside)
    response = client.get(f"{BASE}/")
    assert response.status_code == 403
    assert b"foreign" not in response.content

    report_dir.unlink()
    path_dir = run_root / "path"
    _shutil.rmtree(path_dir)
    replacement = tmp_path / "outside-path"
    (replacement / "report").mkdir(parents=True)
    (replacement / "report" / "PATH_CE_Report.html").write_text("<html>foreign</html>")
    path_dir.symlink_to(replacement)
    response = client.get(f"{BASE}/")
    assert response.status_code == 403
    assert b"foreign" not in response.content


def test_serves_assets_with_correct_types(report_client):
    client, _ = report_client
    js = client.get(f"{BASE}/static/js/vendor/plotly.min.js")
    assert js.status_code == 200
    assert js.headers["content-type"].startswith("text/javascript")
    assert "content-security-policy" not in js.headers  # CSP only on documents

    csv = client.get(f"{BASE}/static/downloads/PATH_hillslope_treatment_summary.csv")
    assert csv.status_code == 200
    assert csv.headers["content-type"].startswith("text/csv")

    geojson = client.get(f"{BASE}/static/subcatchments.WGS.geojson")
    assert geojson.status_code == 200
    assert geojson.headers["content-type"].startswith("application/geo+json")


def test_rejects_traversal_out_of_subtree(report_client):
    client, _ = report_client
    for attempt in (
        "../path_ce_final_data.parquet",
        "../../watershed/hillslopes.parquet",
        "..%2f..%2fwatershed%2fhillslopes.parquet",
        "static/../../path_ce_final_data.parquet",
    ):
        response = client.get(f"{BASE}/{attempt}")
        assert response.status_code in (403, 404), attempt
        assert b"secret" not in response.content, attempt


def test_rejects_symlink_escape(report_client):
    client, run_root = report_client
    link = run_root / "path" / "report" / "leak.parquet"
    link.symlink_to(run_root / "path" / "path_ce_final_data.parquet")
    response = client.get(f"{BASE}/leak.parquet")
    assert response.status_code == 403
    assert b"secret" not in response.content


def test_rejects_hidden_paths(report_client):
    client, run_root = report_client
    hidden = run_root / "path" / "report" / ".env"
    hidden.write_text("SECRET=1")
    response = client.get(f"{BASE}/.env")
    assert response.status_code == 403


def test_missing_report_404s_with_guidance(report_client, monkeypatch, tmp_path):
    import wepppy.microservices.browse.report as report_mod

    bare_root = tmp_path / "bare-run"
    bare_root.mkdir()
    monkeypatch.setattr(report_mod, "get_wd", lambda _runid, prefer_active=False: str(bare_root))
    client, _ = report_client
    response = client.get(f"{BASE}/")
    assert response.status_code == 404


def test_missing_asset_404s(report_client):
    client, _ = report_client
    assert client.get(f"{BASE}/static/nope.js").status_code == 404


def test_auth_denied_is_propagated(report_client, monkeypatch):
    import wepppy.microservices.browse.report as report_mod
    import wepppy.microservices.browse.auth as auth_mod

    def _deny(*args, **kwargs):
        raise auth_mod.BrowseAuthError("denied", status_code=403)

    monkeypatch.setattr(report_mod, "authorize_run_request", _deny)
    client, _ = report_client
    response = client.get(f"{BASE}/")
    # 403 never redirects (handle_auth_error only redirects 401 html requests)
    assert response.status_code == 403
    assert b"report</body>" not in response.content
