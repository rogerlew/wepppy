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
    return _issue_token(
        token_class="service",
        runs=runs if runs is not None else [runid],
        roles=roles,
    )


def _issue_token(
    *,
    token_class: str,
    runs: list[str] | None = None,
    roles: list[str] | None = None,
    subject: str = "svc-browse",
) -> str:
    payload = auth_tokens.issue_token(
        subject,
        scopes=["rq:status"],
        audience="rq-engine",
        runs=runs,
        extra_claims={
            "token_class": token_class,
            "roles": roles or [],
            "jti": uuid.uuid4().hex,
        },
    )
    return payload["token"]


def _touch(path: Path, text: str = "demo") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _mock_dtale_loader(monkeypatch: pytest.MonkeyPatch) -> dict:
    import wepppy.microservices.browse.dtale as dtale_mod

    captured: dict = {}

    class DummyResponse:
        status_code = 200
        text = ""

        @staticmethod
        def json():
            return {"url": "/weppcloud/dtale/main/test"}

    class DummyClient:
        def __init__(self, *args, **kwargs):
            captured["client_kwargs"] = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json=None, headers=None):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return DummyResponse()

    monkeypatch.setattr(
        dtale_mod.httpx,
        "AsyncClient",
        lambda *args, **kwargs: DummyClient(*args, **kwargs),
    )
    return captured


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


@pytest.mark.parametrize(
    "base,root_env",
    [("culverts", "CULVERTS_ROOT"), ("batch", "BATCH_RUNNER_ROOT")],
)
@pytest.mark.parametrize(
    "suffix",
    [
        "browse/",
        "download/runs/1001/shared.txt",
        "gdalinfo/runs/1001/raster.tif",
        "dtale/runs/1001/table.csv",
    ],
)
def test_group_routes_require_auth(
    tmp_path: Path,
    load_secure_browse,
    base: str,
    root_env: str,
    suffix: str,
) -> None:
    identifier = "group-42"
    group_root_root = tmp_path / base
    group_root = group_root_root / identifier
    _touch(group_root / "runs" / "1001" / "shared.txt", "ok")
    _touch(group_root / "runs" / "1001" / "raster.tif", "raster")
    _touch(group_root / "runs" / "1001" / "table.csv", "a,b\n1,2\n")

    browse = load_secure_browse(
        {},
        SITE_PREFIX="/weppcloud",
        **{
            root_env: str(group_root_root),
            "DTALE_SERVICE_URL": "http://dtale-service",
        },
    )
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(f"/weppcloud/{base}/{identifier}/{suffix}", follow_redirects=False)

    assert response.status_code == 401


@pytest.mark.parametrize(
    "base,root_env,config_name",
    [("culverts", "CULVERTS_ROOT", "culvert-batch"), ("batch", "BATCH_RUNNER_ROOT", "batch")],
)
def test_group_routes_accept_scoped_service_token(
    tmp_path: Path,
    load_secure_browse,
    monkeypatch: pytest.MonkeyPatch,
    base: str,
    root_env: str,
    config_name: str,
) -> None:
    identifier = "group-77"
    group_root_root = tmp_path / base
    group_root = group_root_root / identifier
    _touch(group_root / "runs" / "1001" / "shared.txt", "group-ok")
    _touch(group_root / "runs" / "1001" / "raster.tif", "raster")
    _touch(group_root / "runs" / "1001" / "table.csv", "a,b\n1,2\n")

    browse = load_secure_browse(
        {},
        SITE_PREFIX="/weppcloud",
        **{
            root_env: str(group_root_root),
            "DTALE_SERVICE_URL": "http://dtale-service",
        },
    )
    app = browse.create_app()
    token = _issue_service_token(identifier, runs=[identifier], roles=["User"])
    headers = {"Authorization": f"Bearer {token}"}

    import wepppy.microservices._gdalinfo as gdalinfo_mod

    async def _fake_run_shell_command(command: str, cwd: str | None):
        return (0, '{"driver":"GTiff"}', "")

    monkeypatch.setattr(
        gdalinfo_mod,
        "_run_shell_command",
        _fake_run_shell_command,
    )
    captured_dtale = _mock_dtale_loader(monkeypatch)

    with TestClient(app) as client:
        browse_response = client.get(
            f"/weppcloud/{base}/{identifier}/browse/runs/1001/",
            headers=headers,
        )
        download_response = client.get(
            f"/weppcloud/{base}/{identifier}/download/runs/1001/shared.txt",
            headers=headers,
        )
        gdalinfo_response = client.get(
            f"/weppcloud/{base}/{identifier}/gdalinfo/runs/1001/raster.tif",
            headers=headers,
        )
        dtale_response = client.get(
            f"/weppcloud/{base}/{identifier}/dtale/runs/1001/table.csv",
            headers=headers,
            follow_redirects=False,
        )

    assert browse_response.status_code == 200
    assert download_response.status_code == 200
    assert download_response.text == "group-ok"
    assert gdalinfo_response.status_code == 200
    assert gdalinfo_response.json()["driver"] == "GTiff"
    assert dtale_response.status_code == 303
    assert captured_dtale["json"] == {
        "runid": identifier,
        "config": config_name,
        "path": "runs/1001/table.csv",
    }


@pytest.mark.parametrize("base,root_env", [("culverts", "CULVERTS_ROOT"), ("batch", "BATCH_RUNNER_ROOT")])
def test_group_service_token_identifier_mismatch_is_forbidden(
    tmp_path: Path,
    load_secure_browse,
    base: str,
    root_env: str,
) -> None:
    identifier = "group-88"
    group_root_root = tmp_path / base
    _touch(group_root_root / identifier / "runs" / "1001" / "shared.txt", "ok")

    browse = load_secure_browse({}, SITE_PREFIX="/weppcloud", **{root_env: str(group_root_root)})
    app = browse.create_app()
    token = _issue_service_token(identifier, runs=["other-group"])

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/{base}/{identifier}/browse/runs/1001/",
            headers={"Authorization": f"Bearer {token}"},
            follow_redirects=False,
        )

    assert response.status_code == 403


@pytest.mark.parametrize("base,root_env", [("culverts", "CULVERTS_ROOT"), ("batch", "BATCH_RUNNER_ROOT")])
def test_group_routes_reject_session_token_class(
    tmp_path: Path,
    load_secure_browse,
    base: str,
    root_env: str,
) -> None:
    identifier = "group-99"
    group_root_root = tmp_path / base
    _touch(group_root_root / identifier / "runs" / "1001" / "shared.txt", "ok")

    browse = load_secure_browse({}, SITE_PREFIX="/weppcloud", **{root_env: str(group_root_root)})
    app = browse.create_app()
    token = _issue_token(
        token_class="session",
        runs=[identifier],
        subject="sid-123",
    )

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/{base}/{identifier}/browse/runs/1001/",
            headers={"Authorization": f"Bearer {token}"},
            follow_redirects=False,
        )

    assert response.status_code == 403
