import importlib
import uuid
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from wepppy.weppcloud.utils import auth_tokens

TestClient = pytest.importorskip("starlette.testclient").TestClient

pytestmark = pytest.mark.microservice


@pytest.fixture
def load_secure_browse(monkeypatch):
    def _loader(run_roots: dict[str, Path], **env):
        monkeypatch.setenv("WEPP_AUTH_JWT_SECRET", "browse-auth-secret")
        auth_tokens.get_jwt_config.cache_clear()
        for key, value in env.items():
            monkeypatch.setenv(key, value)

        import wepppy.microservices.browse._download as download_mod
        import wepppy.microservices.browse.auth as auth_mod
        import wepppy.microservices.browse.dtale as dtale_mod
        import wepppy.microservices.browse.files_api as files_api_mod
        import wepppy.microservices.browse.browse as browse_mod
        import wepppy.microservices._gdalinfo as gdalinfo_mod

        importlib.reload(download_mod)
        importlib.reload(dtale_mod)
        importlib.reload(files_api_mod)
        importlib.reload(gdalinfo_mod)
        browse_mod = importlib.reload(browse_mod)

        def _get_wd(runid: str, prefer_active: bool = False) -> str:
            root = run_roots.get(runid)
            if root is None:
                raise FileNotFoundError(runid)
            return str(root)

        monkeypatch.setattr(browse_mod, "get_wd", _get_wd)
        monkeypatch.setattr(auth_mod, "get_wd", _get_wd)
        monkeypatch.setattr(download_mod, "get_wd", _get_wd)
        monkeypatch.setattr(gdalinfo_mod, "get_wd", _get_wd)
        return browse_mod

    return _loader


def _issue_service_token(
    runid: str,
    *,
    roles: list[str] | None = None,
    runs: list[str] | None = None,
) -> str:
    payload = auth_tokens.issue_token(
        "svc-browse",
        scopes=["rq:status"],
        audience="rq-engine",
        runs=runs if runs is not None else [runid],
        extra_claims={
            "token_class": "service",
            "roles": roles or [],
            "jti": uuid.uuid4().hex,
        },
    )
    return payload["token"]


def _touch(path: Path, text: str = "demo") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_browse_allows_public_run_without_token(tmp_path: Path, load_secure_browse) -> None:
    runid = "run-public"
    config = "cfg"
    run_root = tmp_path / runid
    _touch(run_root / "PUBLIC", "")
    _touch(run_root / "demo.txt", "hello")
    browse = load_secure_browse({runid: run_root}, SITE_PREFIX="/weppcloud")
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(f"/weppcloud/runs/{runid}/{config}/browse/")

    assert response.status_code == 200
    assert "demo.txt" in response.text


def test_browse_private_run_redirects_without_token(tmp_path: Path, load_secure_browse) -> None:
    runid = "run-private"
    config = "cfg"
    run_root = tmp_path / runid
    _touch(run_root / "secret.txt", "shh")
    browse = load_secure_browse({runid: run_root}, SITE_PREFIX="/weppcloud")
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/browse/secret.txt",
            follow_redirects=False,
        )

    assert response.status_code == 302
    parsed = urlparse(response.headers["location"])
    assert parsed.path == f"/weppcloud/runs/{runid}/"
    next_value = parse_qs(parsed.query).get("next", [""])[0]
    assert next_value == f"/weppcloud/runs/{runid}/{config}/browse/secret.txt"


def test_files_requires_auth_even_for_public_run(tmp_path: Path, load_secure_browse) -> None:
    runid = "run-files-public"
    config = "cfg"
    run_root = tmp_path / runid
    _touch(run_root / "PUBLIC", "")
    _touch(run_root / "demo.txt", "hello")
    browse = load_secure_browse({runid: run_root}, SITE_PREFIX="/weppcloud")
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(f"/weppcloud/runs/{runid}/{config}/files/")

    assert response.status_code == 401
    payload = response.json()
    assert payload["error"]["code"] == "unauthorized"


def test_dtale_requires_auth_even_for_public_run(tmp_path: Path, load_secure_browse) -> None:
    runid = "run-dtale-public"
    config = "cfg"
    run_root = tmp_path / runid
    _touch(run_root / "PUBLIC", "")
    _touch(run_root / "table.csv", "a,b\n1,2\n")
    browse = load_secure_browse({runid: run_root}, SITE_PREFIX="/weppcloud")
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/dtale/table.csv",
            follow_redirects=False,
        )

    assert response.status_code == 302
    parsed = urlparse(response.headers["location"])
    assert parsed.path == f"/weppcloud/runs/{runid}/"


def test_private_download_redirects_only_for_navigation(tmp_path: Path, load_secure_browse) -> None:
    runid = "run-download-private"
    config = "cfg"
    run_root = tmp_path / runid
    _touch(run_root / "payload.txt", "hello")
    browse = load_secure_browse({runid: run_root}, SITE_PREFIX="/weppcloud")
    app = browse.create_app()

    with TestClient(app) as client:
        html_response = client.get(
            f"/weppcloud/runs/{runid}/{config}/download/payload.txt",
            headers={"Accept": "text/html"},
            follow_redirects=False,
        )
        api_response = client.get(
            f"/weppcloud/runs/{runid}/{config}/download/payload.txt",
            headers={"Accept": "application/octet-stream"},
            follow_redirects=False,
        )

    assert html_response.status_code == 302
    assert api_response.status_code == 401


def test_private_gdalinfo_returns_401_without_redirect(tmp_path: Path, load_secure_browse) -> None:
    runid = "run-gdal-private"
    config = "cfg"
    run_root = tmp_path / runid
    _touch(run_root / "raster.tif", "not-really-a-raster")
    browse = load_secure_browse({runid: run_root}, SITE_PREFIX="/weppcloud")
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/gdalinfo/raster.tif",
            follow_redirects=False,
        )

    assert response.status_code == 401
    assert "location" not in {key.lower() for key in response.headers}


def test_service_token_run_mismatch_is_forbidden(tmp_path: Path, load_secure_browse) -> None:
    runid = "run-mismatch"
    config = "cfg"
    run_root = tmp_path / runid
    _touch(run_root / "demo.txt", "hello")
    browse = load_secure_browse({runid: run_root}, SITE_PREFIX="/weppcloud")
    app = browse.create_app()
    token = _issue_service_token(runid, runs=["other-run"])

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/browse/demo.txt",
            headers={"Authorization": f"Bearer {token}"},
            follow_redirects=False,
        )

    assert response.status_code == 403


@pytest.mark.parametrize("subpath", ["_logs/profile.events.jsonl", "exceptions.log"])
def test_root_only_paths_require_root_role(
    tmp_path: Path,
    load_secure_browse,
    subpath: str,
) -> None:
    runid = "run-root-only"
    config = "cfg"
    run_root = tmp_path / runid
    _touch(run_root / subpath, "sensitive")
    browse = load_secure_browse({runid: run_root}, SITE_PREFIX="/weppcloud")
    app = browse.create_app()
    user_token = _issue_service_token(runid, roles=["User"])
    root_token = _issue_service_token(runid, roles=["Root"])

    with TestClient(app) as client:
        forbidden = client.get(
            f"/weppcloud/runs/{runid}/{config}/browse/{subpath}",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        allowed = client.get(
            f"/weppcloud/runs/{runid}/{config}/browse/{subpath}",
            headers={"Authorization": f"Bearer {root_token}"},
        )

    assert forbidden.status_code == 403
    assert allowed.status_code == 200
