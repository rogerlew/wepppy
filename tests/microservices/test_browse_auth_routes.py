import importlib
import uuid
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from wepppy.weppcloud.utils import auth_tokens
from wepppy.weppcloud.utils.auth_tokens import JWTConfigurationError
from wepppy.weppcloud.utils.browse_cookie import browse_cookie_name

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
    service_groups: list[str] | None = None,
) -> str:
    extra_claims = None
    if service_groups is not None:
        extra_claims = {"service_groups": service_groups}
    return _issue_token(
        token_class="service",
        runs=runs if runs is not None else [runid],
        roles=roles,
        extra_claims=extra_claims,
    )


def _issue_token(
    *,
    token_class: str,
    runs: list[str] | None = None,
    roles: list[str] | None = None,
    subject: str = "svc-browse",
    extra_claims: dict | None = None,
) -> str:
    merged_claims = {
        "token_class": token_class,
        "roles": roles or [],
        "jti": uuid.uuid4().hex,
    }
    if extra_claims:
        merged_claims.update(extra_claims)

    payload = auth_tokens.issue_token(
        subject,
        scopes=["rq:status"],
        audience="rq-engine",
        runs=runs,
        extra_claims=merged_claims,
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


def _mock_gdalinfo_shell(monkeypatch: pytest.MonkeyPatch, *, payload: str = '{"driver":"GTiff"}') -> None:
    import wepppy.microservices._gdalinfo as gdalinfo_mod

    async def _fake_run_shell_command(command: str, cwd: str | None):
        return (0, payload, "")

    monkeypatch.setattr(
        gdalinfo_mod,
        "_run_shell_command",
        _fake_run_shell_command,
    )


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


def test_browse_grouped_omni_run_uses_parent_public_flag(
    tmp_path: Path,
    load_secure_browse,
) -> None:
    parent_runid = "run-parent"
    grouped_runid = f"{parent_runid};;omni;;treated"
    config = "cfg"

    parent_root = tmp_path / parent_runid
    child_root = tmp_path / grouped_runid

    _touch(parent_root / "PUBLIC", "")
    _touch(child_root / "demo.txt", "hello")

    browse = load_secure_browse(
        {parent_runid: parent_root, grouped_runid: child_root},
        SITE_PREFIX="/weppcloud",
    )
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{grouped_runid}/{config}/browse/demo.txt",
            follow_redirects=False,
        )

    assert response.status_code == 200
    assert "hello" in response.text


def test_browse_grouped_batch_omni_run_uses_parent_public_flag(
    tmp_path: Path,
    load_secure_browse,
) -> None:
    parent_runid = "batch;;spring-2025;;run-001"
    grouped_runid = f"{parent_runid};;omni;;treated"
    config = "cfg"

    parent_root = tmp_path / "batch-parent"
    child_root = tmp_path / "batch-child"

    _touch(parent_root / "PUBLIC", "")
    _touch(child_root / "demo.txt", "hello")

    browse = load_secure_browse(
        {parent_runid: parent_root, grouped_runid: child_root},
        SITE_PREFIX="/weppcloud",
    )
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{grouped_runid}/{config}/browse/demo.txt",
            follow_redirects=False,
        )

    assert response.status_code == 200
    assert "hello" in response.text


def test_public_browse_ignores_invalid_cookie_without_bearer(
    tmp_path: Path,
    load_secure_browse,
) -> None:
    runid = "run-public-cookie"
    config = "cfg"
    run_root = tmp_path / runid
    _touch(run_root / "PUBLIC", "")
    _touch(run_root / "demo.txt", "hello")
    browse = load_secure_browse({runid: run_root}, SITE_PREFIX="/weppcloud")
    app = browse.create_app()

    with TestClient(app) as client:
        client.cookies.set("wepp_browse_jwt", "not-a-jwt")
        response = client.get(f"/weppcloud/runs/{runid}/{config}/browse/")

    assert response.status_code == 200
    assert "demo.txt" in response.text


def test_public_browse_surfaces_jwt_config_errors(
    tmp_path: Path,
    load_secure_browse,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runid = "run-public-cookie-config-error"
    config = "cfg"
    run_root = tmp_path / runid
    _touch(run_root / "PUBLIC", "")
    _touch(run_root / "demo.txt", "hello")
    browse = load_secure_browse({runid: run_root}, SITE_PREFIX="/weppcloud")
    app = browse.create_app()

    import wepppy.microservices.browse.auth as auth_mod

    monkeypatch.setattr(
        auth_mod.auth_tokens,
        "decode_token",
        lambda token, audience=None: (_ for _ in ()).throw(JWTConfigurationError("broken jwt settings")),
    )

    with TestClient(app) as client:
        client.cookies.set("wepp_browse_jwt", "any-token")
        response = client.get(f"/weppcloud/runs/{runid}/{config}/browse/")

    assert response.status_code == 500
    assert "JWT configuration error" in response.text


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


def test_private_browse_invalid_cookie_without_bearer_still_redirects(
    tmp_path: Path,
    load_secure_browse,
) -> None:
    runid = "run-private-invalid-cookie"
    config = "cfg"
    run_root = tmp_path / runid
    _touch(run_root / "secret.txt", "shh")
    browse = load_secure_browse({runid: run_root}, SITE_PREFIX="/weppcloud")
    app = browse.create_app()

    with TestClient(app) as client:
        client.cookies.set("wepp_browse_jwt", "invalid-token")
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/browse/secret.txt",
            follow_redirects=False,
        )

    assert response.status_code == 302
    parsed = urlparse(response.headers["location"])
    assert parsed.path == f"/weppcloud/runs/{runid}/"
    next_value = parse_qs(parsed.query).get("next", [""])[0]
    assert next_value == f"/weppcloud/runs/{runid}/{config}/browse/secret.txt"


def test_private_browse_falls_back_to_bearer_when_cookie_invalid(
    tmp_path: Path,
    load_secure_browse,
) -> None:
    runid = "run-private-bearer-fallback"
    config = "cfg"
    run_root = tmp_path / runid
    _touch(run_root / "secret.txt", "shh")
    browse = load_secure_browse({runid: run_root}, SITE_PREFIX="/weppcloud")
    app = browse.create_app()
    token = _issue_service_token(runid, runs=[runid], roles=["User"])

    with TestClient(app) as client:
        client.cookies.set("wepp_browse_jwt", "expired-or-invalid")
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/browse/secret.txt",
            headers={"Authorization": f"Bearer {token}"},
            follow_redirects=False,
        )

    assert response.status_code == 200
    assert "shh" in response.text


def test_private_browse_uses_bearer_when_cookie_run_scope_mismatch(
    tmp_path: Path,
    load_secure_browse,
) -> None:
    runid = "run-private-cookie-mismatch"
    config = "cfg"
    run_root = tmp_path / runid
    _touch(run_root / "secret.txt", "shh")
    browse = load_secure_browse({runid: run_root}, SITE_PREFIX="/weppcloud")
    app = browse.create_app()

    cookie_token = _issue_token(
        token_class="session",
        subject="sid-cookie",
        extra_claims={"runid": "other-run", "session_id": "sid-cookie"},
    )
    bearer_token = _issue_service_token(runid, runs=[runid], roles=["User"])

    with TestClient(app) as client:
        client.cookies.set("wepp_browse_jwt", cookie_token)
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/browse/secret.txt",
            headers={"Authorization": f"Bearer {bearer_token}"},
            follow_redirects=False,
        )

    assert response.status_code == 200
    assert "shh" in response.text


def test_private_browse_accepts_grouped_run_scoped_cookie_name(
    tmp_path: Path,
    load_secure_browse,
) -> None:
    runid = "run-private;;omni;;treated"
    config = "cfg"
    run_root = tmp_path / runid
    _touch(run_root / "secret.txt", "shh")
    browse = load_secure_browse({runid: run_root}, SITE_PREFIX="/weppcloud")
    app = browse.create_app()

    cookie_token = _issue_service_token(runid, runs=[runid], roles=["User"])
    cookie_name = browse_cookie_name("wepp_browse_jwt", runid, config)

    with TestClient(app) as client:
        client.cookies.set(cookie_name, cookie_token)
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/browse/secret.txt",
            follow_redirects=False,
        )

    assert response.status_code == 200
    assert "shh" in response.text


def test_private_browse_accepts_legacy_base_cookie_name_for_grouped_runid(
    tmp_path: Path,
    load_secure_browse,
) -> None:
    runid = "run-private;;omni;;treated"
    config = "cfg"
    run_root = tmp_path / runid
    _touch(run_root / "secret.txt", "shh")
    browse = load_secure_browse({runid: run_root}, SITE_PREFIX="/weppcloud")
    app = browse.create_app()

    legacy_cookie_token = _issue_service_token(runid, runs=[runid], roles=["User"])

    with TestClient(app) as client:
        client.cookies.set("wepp_browse_jwt", legacy_cookie_token)
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/browse/secret.txt",
            follow_redirects=False,
        )

    assert response.status_code == 200
    assert "shh" in response.text


def test_private_browse_falls_back_to_legacy_cookie_when_grouped_cookie_invalid(
    tmp_path: Path,
    load_secure_browse,
) -> None:
    runid = "run-private;;omni;;treated"
    config = "cfg"
    run_root = tmp_path / runid
    _touch(run_root / "secret.txt", "shh")
    browse = load_secure_browse({runid: run_root}, SITE_PREFIX="/weppcloud")
    app = browse.create_app()

    derived_cookie_name = browse_cookie_name("wepp_browse_jwt", runid, config)
    legacy_cookie_token = _issue_service_token(runid, runs=[runid], roles=["User"])

    with TestClient(app) as client:
        client.cookies.set(derived_cookie_name, "invalid-token")
        client.cookies.set("wepp_browse_jwt", legacy_cookie_token)
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/browse/secret.txt",
            follow_redirects=False,
        )

    assert response.status_code == 200
    assert "shh" in response.text


def test_private_browse_uses_bearer_when_cookie_token_revoked(
    tmp_path: Path,
    load_secure_browse,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runid = "run-private-cookie-revoked"
    config = "cfg"
    run_root = tmp_path / runid
    _touch(run_root / "secret.txt", "shh")
    browse = load_secure_browse({runid: run_root}, SITE_PREFIX="/weppcloud")
    app = browse.create_app()

    import wepppy.microservices.browse.auth as auth_mod

    def _check_revocation(jti: str) -> None:
        if jti == "revoked-cookie-jti":
            raise auth_mod.BrowseAuthError("Token has been revoked", status_code=403, code="forbidden")

    monkeypatch.setattr(auth_mod, "_check_revocation", _check_revocation)

    bearer_token = _issue_token(
        token_class="service",
        runs=[runid],
        roles=["User"],
        extra_claims={"jti": "ok-bearer-jti"},
    )
    # Override cookie token with deterministic revoked JTI.
    cookie_token = _issue_token(
        token_class="service",
        runs=[runid],
        roles=["User"],
        extra_claims={"jti": "revoked-cookie-jti"},
    )

    with TestClient(app) as client:
        client.cookies.set("wepp_browse_jwt", cookie_token)
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/browse/secret.txt",
            headers={"Authorization": f"Bearer {bearer_token}"},
            follow_redirects=False,
        )

    assert response.status_code == 200
    assert "shh" in response.text


def test_private_browse_prefers_valid_cookie_over_bearer(
    tmp_path: Path,
    load_secure_browse,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runid = "run-private-cookie-precedence"
    config = "cfg"
    run_root = tmp_path / runid
    _touch(run_root / "secret.txt", "shh")
    browse = load_secure_browse({runid: run_root}, SITE_PREFIX="/weppcloud")
    app = browse.create_app()

    import wepppy.microservices.browse.auth as auth_mod

    def _unexpected_bearer_resolution(request):
        raise AssertionError("bearer fallback should not run when cookie auth succeeds")

    monkeypatch.setattr(auth_mod, "resolve_bearer_context", _unexpected_bearer_resolution)

    cookie_token = _issue_service_token(runid, runs=[runid], roles=["User"])
    bearer_token = _issue_service_token(runid, runs=[runid], roles=["Root"])

    with TestClient(app) as client:
        client.cookies.set("wepp_browse_jwt", cookie_token)
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/browse/secret.txt",
            headers={"Authorization": f"Bearer {bearer_token}"},
            follow_redirects=False,
        )

    assert response.status_code == 200
    assert "shh" in response.text


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


def test_files_public_run_invalid_cookie_still_requires_auth(
    tmp_path: Path,
    load_secure_browse,
) -> None:
    runid = "run-files-invalid-cookie"
    config = "cfg"
    run_root = tmp_path / runid
    _touch(run_root / "PUBLIC", "")
    _touch(run_root / "demo.txt", "hello")
    browse = load_secure_browse({runid: run_root}, SITE_PREFIX="/weppcloud")
    app = browse.create_app()

    with TestClient(app) as client:
        client.cookies.set("wepp_browse_jwt", "invalid-token")
        response = client.get(f"/weppcloud/runs/{runid}/{config}/files/")

    assert response.status_code == 401
    payload = response.json()
    assert payload["error"]["code"] == "unauthorized"


def test_files_surfaces_internal_error_on_jwt_config_failure(
    tmp_path: Path,
    load_secure_browse,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runid = "run-files-config-error"
    config = "cfg"
    run_root = tmp_path / runid
    _touch(run_root / "PUBLIC", "")
    _touch(run_root / "demo.txt", "hello")
    browse = load_secure_browse({runid: run_root}, SITE_PREFIX="/weppcloud")
    app = browse.create_app()

    import wepppy.microservices.browse.auth as auth_mod

    monkeypatch.setattr(
        auth_mod.auth_tokens,
        "decode_token",
        lambda token, audience=None: (_ for _ in ()).throw(JWTConfigurationError("broken jwt settings")),
    )

    with TestClient(app) as client:
        client.cookies.set("wepp_browse_jwt", "any-token")
        response = client.get(f"/weppcloud/runs/{runid}/{config}/files/")

    assert response.status_code == 500
    payload = response.json()
    assert payload["error"]["code"] == "internal_error"
    assert "JWT configuration error" in payload["error"]["details"]


def test_files_use_bearer_when_cookie_token_class_not_allowed(
    tmp_path: Path,
    load_secure_browse,
) -> None:
    runid = "run-files-cookie-class-mismatch"
    config = "cfg"
    run_root = tmp_path / runid
    _touch(run_root / "PUBLIC", "")
    _touch(run_root / "demo.txt", "hello")
    browse = load_secure_browse({runid: run_root}, SITE_PREFIX="/weppcloud")
    app = browse.create_app()

    cookie_token = _issue_token(
        token_class="session",
        subject="sid-files",
        extra_claims={"runid": runid, "session_id": "sid-files"},
    )
    bearer_token = _issue_service_token(runid, runs=[runid], roles=["User"])

    with TestClient(app) as client:
        client.cookies.set("wepp_browse_jwt", cookie_token)
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/files/",
            headers={"Authorization": f"Bearer {bearer_token}"},
            follow_redirects=False,
        )

    assert response.status_code == 200
    payload = response.json()
    assert any(entry["name"] == "demo.txt" for entry in payload["entries"])


def test_files_use_bearer_when_cookie_token_revoked(
    tmp_path: Path,
    load_secure_browse,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runid = "run-files-cookie-revoked"
    config = "cfg"
    run_root = tmp_path / runid
    _touch(run_root / "PUBLIC", "")
    _touch(run_root / "demo.txt", "hello")
    browse = load_secure_browse({runid: run_root}, SITE_PREFIX="/weppcloud")
    app = browse.create_app()

    import wepppy.microservices.browse.auth as auth_mod

    def _check_revocation(jti: str) -> None:
        if jti == "revoked-cookie-jti":
            raise auth_mod.BrowseAuthError("Token has been revoked", status_code=403, code="forbidden")

    monkeypatch.setattr(auth_mod, "_check_revocation", _check_revocation)

    cookie_token = _issue_token(
        token_class="service",
        runs=[runid],
        roles=["User"],
        extra_claims={"jti": "revoked-cookie-jti"},
    )
    bearer_token = _issue_token(
        token_class="service",
        runs=[runid],
        roles=["User"],
        extra_claims={"jti": "ok-bearer-jti"},
    )

    with TestClient(app) as client:
        client.cookies.set("wepp_browse_jwt", cookie_token)
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/files/",
            headers={"Authorization": f"Bearer {bearer_token}"},
            follow_redirects=False,
        )

    assert response.status_code == 200
    payload = response.json()
    assert any(entry["name"] == "demo.txt" for entry in payload["entries"])


def test_files_root_only_path_requires_root_role(
    tmp_path: Path,
    load_secure_browse,
) -> None:
    runid = "run-files-root-only"
    config = "cfg"
    run_root = tmp_path / runid
    subpath = "_logs/profile.events.jsonl"
    _touch(run_root / "PUBLIC", "")
    _touch(run_root / subpath, "sensitive")
    browse = load_secure_browse({runid: run_root}, SITE_PREFIX="/weppcloud")
    app = browse.create_app()

    user_token = _issue_service_token(runid, roles=["User"], runs=[runid])
    root_token = _issue_service_token(runid, roles=["Root"], runs=[runid])

    with TestClient(app) as client:
        forbidden = client.get(
            f"/weppcloud/runs/{runid}/{config}/files/{subpath}?meta=true",
            headers={"Authorization": f"Bearer {user_token}"},
            follow_redirects=False,
        )
        allowed = client.get(
            f"/weppcloud/runs/{runid}/{config}/files/{subpath}?meta=true",
            headers={"Authorization": f"Bearer {root_token}"},
            follow_redirects=False,
        )

    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "forbidden"
    assert allowed.status_code == 200
    assert allowed.json()["name"] == "profile.events.jsonl"


def test_files_root_only_path_uses_bearer_when_cookie_lacks_root_role(
    tmp_path: Path,
    load_secure_browse,
) -> None:
    runid = "run-files-root-fallback"
    config = "cfg"
    run_root = tmp_path / runid
    subpath = "_logs/profile.events.jsonl"
    _touch(run_root / "PUBLIC", "")
    _touch(run_root / subpath, "sensitive")
    browse = load_secure_browse({runid: run_root}, SITE_PREFIX="/weppcloud")
    app = browse.create_app()

    cookie_token = _issue_service_token(runid, roles=["User"], runs=[runid])
    bearer_token = _issue_service_token(runid, roles=["Root"], runs=[runid])

    with TestClient(app) as client:
        client.cookies.set("wepp_browse_jwt", cookie_token)
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/files/{subpath}?meta=true",
            headers={"Authorization": f"Bearer {bearer_token}"},
            follow_redirects=False,
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "profile.events.jsonl"


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


def test_private_download_uses_bearer_when_cookie_run_scope_mismatch(
    tmp_path: Path,
    load_secure_browse,
) -> None:
    runid = "run-download-cookie-mismatch"
    config = "cfg"
    run_root = tmp_path / runid
    _touch(run_root / "payload.txt", "hello")
    browse = load_secure_browse({runid: run_root}, SITE_PREFIX="/weppcloud")
    app = browse.create_app()

    cookie_token = _issue_token(
        token_class="session",
        subject="sid-download",
        extra_claims={"runid": "other-run", "session_id": "sid-download"},
    )
    bearer_token = _issue_service_token(runid, runs=[runid], roles=["User"])

    with TestClient(app) as client:
        client.cookies.set("wepp_browse_jwt", cookie_token)
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/download/payload.txt",
            headers={"Authorization": f"Bearer {bearer_token}"},
            follow_redirects=False,
        )

    assert response.status_code == 200
    assert response.text == "hello"


def test_aria2c_private_run_returns_401_without_redirect(
    tmp_path: Path,
    load_secure_browse,
) -> None:
    runid = "run-aria2c-private"
    config = "cfg"
    run_root = tmp_path / runid
    _touch(run_root / "report.txt", "hello")
    browse = load_secure_browse({runid: run_root}, SITE_PREFIX="/weppcloud")
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/aria2c.spec",
            follow_redirects=False,
        )

    assert response.status_code == 401
    assert "location" not in {key.lower() for key in response.headers}


def test_aria2c_uses_bearer_when_cookie_run_scope_mismatch(
    tmp_path: Path,
    load_secure_browse,
) -> None:
    runid = "run-aria2c-cookie-mismatch"
    config = "cfg"
    run_root = tmp_path / runid
    _touch(run_root / "report.txt", "hello")
    browse = load_secure_browse({runid: run_root}, SITE_PREFIX="/weppcloud")
    app = browse.create_app()

    cookie_token = _issue_token(
        token_class="session",
        subject="sid-aria2c",
        extra_claims={"runid": "other-run", "session_id": "sid-aria2c"},
    )
    bearer_token = _issue_service_token(runid, runs=[runid], roles=["User"])

    with TestClient(app) as client:
        client.cookies.set("wepp_browse_jwt", cookie_token)
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/aria2c.spec",
            headers={"Authorization": f"Bearer {bearer_token}"},
            follow_redirects=False,
        )

    assert response.status_code == 200
    assert "report.txt" in response.text


def test_aria2c_public_run_allows_anonymous_access(
    tmp_path: Path,
    load_secure_browse,
) -> None:
    runid = "run-aria2c-public"
    config = "cfg"
    run_root = tmp_path / runid
    _touch(run_root / "PUBLIC", "")
    _touch(run_root / "report.txt", "hello")
    browse = load_secure_browse({runid: run_root}, SITE_PREFIX="/weppcloud")
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(f"/weppcloud/runs/{runid}/{config}/aria2c.spec")

    assert response.status_code == 200
    assert "report.txt" in response.text


def test_aria2c_root_only_entries_visible_only_to_root(
    tmp_path: Path,
    load_secure_browse,
) -> None:
    runid = "run-aria2c-root-only"
    config = "cfg"
    run_root = tmp_path / runid
    _touch(run_root / "report.txt", "hello")
    _touch(run_root / "exceptions.log", "traceback")
    _touch(run_root / "nested" / "exception_factory.log", "traceback")
    browse = load_secure_browse({runid: run_root}, SITE_PREFIX="/weppcloud")
    app = browse.create_app()
    user_token = _issue_service_token(runid, runs=[runid], roles=["User"])
    root_token = _issue_service_token(runid, runs=[runid], roles=["Root"])

    with TestClient(app) as client:
        user_response = client.get(
            f"/weppcloud/runs/{runid}/{config}/aria2c.spec",
            headers={"Authorization": f"Bearer {user_token}"},
            follow_redirects=False,
        )
        root_response = client.get(
            f"/weppcloud/runs/{runid}/{config}/aria2c.spec",
            headers={"Authorization": f"Bearer {root_token}"},
            follow_redirects=False,
        )

    assert user_response.status_code == 200
    assert root_response.status_code == 200
    assert "report.txt" in user_response.text
    assert "exceptions.log" not in user_response.text
    assert "exception_factory.log" not in user_response.text
    assert "exceptions.log" in root_response.text
    assert "nested/exception_factory.log" in root_response.text


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


def test_private_gdalinfo_uses_bearer_when_cookie_run_scope_mismatch(
    tmp_path: Path,
    load_secure_browse,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runid = "run-gdal-cookie-mismatch"
    config = "cfg"
    run_root = tmp_path / runid
    _touch(run_root / "raster.tif", "raster")
    browse = load_secure_browse({runid: run_root}, SITE_PREFIX="/weppcloud")
    app = browse.create_app()
    _mock_gdalinfo_shell(monkeypatch)

    cookie_token = _issue_token(
        token_class="session",
        subject="sid-gdal",
        extra_claims={"runid": "other-run", "session_id": "sid-gdal"},
    )
    bearer_token = _issue_service_token(runid, runs=[runid], roles=["User"])

    with TestClient(app) as client:
        client.cookies.set("wepp_browse_jwt", cookie_token)
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/gdalinfo/raster.tif",
            headers={"Authorization": f"Bearer {bearer_token}"},
            follow_redirects=False,
        )

    assert response.status_code == 200
    assert response.json()["driver"] == "GTiff"


def test_private_dtale_uses_bearer_when_cookie_run_scope_mismatch(
    tmp_path: Path,
    load_secure_browse,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runid = "run-dtale-cookie-mismatch"
    config = "cfg"
    run_root = tmp_path / runid
    _touch(run_root / "table.csv", "a,b\n1,2\n")
    browse = load_secure_browse(
        {runid: run_root},
        SITE_PREFIX="/weppcloud",
        DTALE_SERVICE_URL="http://dtale-service",
    )
    app = browse.create_app()
    captured_dtale = _mock_dtale_loader(monkeypatch)

    cookie_token = _issue_token(
        token_class="session",
        subject="sid-dtale",
        extra_claims={"runid": "other-run", "session_id": "sid-dtale"},
    )
    bearer_token = _issue_service_token(runid, runs=[runid], roles=["User"])

    with TestClient(app) as client:
        client.cookies.set("wepp_browse_jwt", cookie_token)
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/dtale/table.csv",
            headers={"Authorization": f"Bearer {bearer_token}"},
            follow_redirects=False,
        )

    assert response.status_code == 303
    assert captured_dtale["json"] == {
        "runid": runid,
        "config": config,
        "path": "table.csv",
    }


def test_private_browse_session_token_runid_mismatch_is_forbidden(
    tmp_path: Path,
    load_secure_browse,
) -> None:
    runid = "run-session-mismatch"
    config = "cfg"
    run_root = tmp_path / runid
    _touch(run_root / "secret.txt", "hello")
    browse = load_secure_browse({runid: run_root}, SITE_PREFIX="/weppcloud")
    app = browse.create_app()
    token = _issue_token(
        token_class="session",
        subject="sid-1",
        extra_claims={"runid": "other-run", "session_id": "sid-1"},
    )

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/browse/secret.txt",
            headers={"Authorization": f"Bearer {token}"},
            follow_redirects=False,
        )

    assert response.status_code == 403
    assert "location" not in {key.lower() for key in response.headers}


def test_files_reject_session_token_class(
    tmp_path: Path,
    load_secure_browse,
) -> None:
    runid = "run-files-session-class"
    config = "cfg"
    run_root = tmp_path / runid
    _touch(run_root / "PUBLIC", "")
    _touch(run_root / "demo.txt", "hello")
    browse = load_secure_browse({runid: run_root}, SITE_PREFIX="/weppcloud")
    app = browse.create_app()
    token = _issue_token(
        token_class="session",
        subject="sid-2",
        extra_claims={"runid": runid, "session_id": "sid-2"},
    )

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/files/",
            headers={"Authorization": f"Bearer {token}"},
            follow_redirects=False,
        )

    assert response.status_code == 403
    payload = response.json()
    assert payload["error"]["code"] == "forbidden"


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


@pytest.mark.parametrize(
    "subpath",
    [
        "_logs/profile.events.jsonl",
        "exceptions.log",
        "exception_factory.log",
    ],
)
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


def test_root_only_path_uses_bearer_when_cookie_lacks_root_role(
    tmp_path: Path,
    load_secure_browse,
) -> None:
    runid = "run-root-fallback"
    config = "cfg"
    run_root = tmp_path / runid
    subpath = "_logs/profile.events.jsonl"
    _touch(run_root / subpath, "sensitive")
    browse = load_secure_browse({runid: run_root}, SITE_PREFIX="/weppcloud")
    app = browse.create_app()

    cookie_token = _issue_service_token(runid, roles=["User"], runs=[runid])
    bearer_token = _issue_service_token(runid, roles=["Root"], runs=[runid])

    with TestClient(app) as client:
        client.cookies.set("wepp_browse_jwt", cookie_token)
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/browse/{subpath}",
            headers={"Authorization": f"Bearer {bearer_token}"},
            follow_redirects=False,
        )

    assert response.status_code == 200


def test_run_download_root_only_path_uses_bearer_when_cookie_lacks_root_role(
    tmp_path: Path,
    load_secure_browse,
) -> None:
    runid = "run-download-root-fallback"
    config = "cfg"
    run_root = tmp_path / runid
    subpath = "_logs/profile.events.jsonl"
    _touch(run_root / subpath, "sensitive")
    browse = load_secure_browse({runid: run_root}, SITE_PREFIX="/weppcloud")
    app = browse.create_app()

    cookie_token = _issue_service_token(runid, roles=["User"], runs=[runid])
    bearer_token = _issue_service_token(runid, roles=["Root"], runs=[runid])

    with TestClient(app) as client:
        client.cookies.set("wepp_browse_jwt", cookie_token)
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/download/{subpath}",
            headers={"Authorization": f"Bearer {bearer_token}"},
            follow_redirects=False,
        )

    assert response.status_code == 200
    assert response.text == "sensitive"


def test_run_gdalinfo_root_only_path_uses_bearer_when_cookie_lacks_root_role(
    tmp_path: Path,
    load_secure_browse,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runid = "run-gdal-root-fallback"
    config = "cfg"
    run_root = tmp_path / runid
    subpath = "_logs/raster.tif"
    _touch(run_root / subpath, "raster")
    browse = load_secure_browse({runid: run_root}, SITE_PREFIX="/weppcloud")
    app = browse.create_app()
    _mock_gdalinfo_shell(monkeypatch)

    cookie_token = _issue_service_token(runid, roles=["User"], runs=[runid])
    bearer_token = _issue_service_token(runid, roles=["Root"], runs=[runid])

    with TestClient(app) as client:
        client.cookies.set("wepp_browse_jwt", cookie_token)
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/gdalinfo/{subpath}",
            headers={"Authorization": f"Bearer {bearer_token}"},
            follow_redirects=False,
        )

    assert response.status_code == 200
    assert response.json()["driver"] == "GTiff"


def test_run_dtale_root_only_path_uses_bearer_when_cookie_lacks_root_role(
    tmp_path: Path,
    load_secure_browse,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runid = "run-dtale-root-fallback"
    config = "cfg"
    run_root = tmp_path / runid
    subpath = "_logs/table.csv"
    _touch(run_root / subpath, "a,b\n1,2\n")
    browse = load_secure_browse(
        {runid: run_root},
        SITE_PREFIX="/weppcloud",
        DTALE_SERVICE_URL="http://dtale-service",
    )
    app = browse.create_app()
    captured_dtale = _mock_dtale_loader(monkeypatch)

    cookie_token = _issue_service_token(runid, roles=["User"], runs=[runid])
    bearer_token = _issue_service_token(runid, roles=["Root"], runs=[runid])

    with TestClient(app) as client:
        client.cookies.set("wepp_browse_jwt", cookie_token)
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/dtale/{subpath}",
            headers={"Authorization": f"Bearer {bearer_token}"},
            follow_redirects=False,
        )

    assert response.status_code == 303
    assert captured_dtale["json"] == {
        "runid": runid,
        "config": config,
        "path": subpath,
    }


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

    if base == "batch" and suffix == "browse/":
        assert response.status_code == 302
        parsed = urlparse(response.headers["location"])
        assert parsed.path == f"/weppcloud/runs/batch;;{identifier};;_base/"
        next_value = parse_qs(parsed.query).get("next", [""])[0]
        assert next_value == f"/weppcloud/batch/{identifier}/browse/"
        return

    assert response.status_code == 401


@pytest.mark.parametrize("base,root_env", [("culverts", "CULVERTS_ROOT"), ("batch", "BATCH_RUNNER_ROOT")])
def test_group_service_token_missing_identifier_scope_is_forbidden(
    tmp_path: Path,
    load_secure_browse,
    base: str,
    root_env: str,
) -> None:
    identifier = "group-no-scope"
    group_root_root = tmp_path / base
    _touch(group_root_root / identifier / "runs" / "1001" / "shared.txt", "ok")

    browse = load_secure_browse({}, SITE_PREFIX="/weppcloud", **{root_env: str(group_root_root)})
    app = browse.create_app()
    token = _issue_token(
        token_class="service",
        roles=["User"],
    )

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/{base}/{identifier}/browse/runs/1001/",
            headers={"Authorization": f"Bearer {token}"},
            follow_redirects=False,
        )

    assert response.status_code == 403
    assert "Token missing run scope" in response.text


@pytest.mark.parametrize("base,root_env", [("culverts", "CULVERTS_ROOT"), ("batch", "BATCH_RUNNER_ROOT")])
def test_group_user_token_without_privileged_role_is_forbidden(
    tmp_path: Path,
    load_secure_browse,
    base: str,
    root_env: str,
) -> None:
    identifier = "group-user-role-forbidden"
    group_root_root = tmp_path / base
    _touch(group_root_root / identifier / "runs" / "1001" / "shared.txt", "ok")

    browse = load_secure_browse({}, SITE_PREFIX="/weppcloud", **{root_env: str(group_root_root)})
    app = browse.create_app()
    token = _issue_token(
        token_class="user",
        roles=["User"],
        subject="42",
    )

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/{base}/{identifier}/browse/runs/1001/",
            headers={"Authorization": f"Bearer {token}"},
            follow_redirects=False,
        )

    assert response.status_code == 403
    assert "User token requires Admin, PowerUser, Dev, or Root role" in response.text


@pytest.mark.parametrize("base,root_env", [("culverts", "CULVERTS_ROOT"), ("batch", "BATCH_RUNNER_ROOT")])
def test_group_user_token_with_privileged_role_is_allowed(
    tmp_path: Path,
    load_secure_browse,
    base: str,
    root_env: str,
) -> None:
    identifier = "group-user-role-allowed"
    group_root_root = tmp_path / base
    _touch(group_root_root / identifier / "runs" / "1001" / "shared.txt", "ok")

    browse = load_secure_browse({}, SITE_PREFIX="/weppcloud", **{root_env: str(group_root_root)})
    app = browse.create_app()
    token = _issue_token(
        token_class="user",
        roles=["PowerUser"],
        subject="42",
    )

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/{base}/{identifier}/browse/runs/1001/",
            headers={"Authorization": f"Bearer {token}"},
            follow_redirects=False,
        )

    assert response.status_code == 200


def test_culvert_download_rejects_user_token_even_with_privileged_role(
    tmp_path: Path,
    load_secure_browse,
) -> None:
    identifier = "culverts-user-download-forbidden"
    culverts_root = tmp_path / "culverts"
    _touch(culverts_root / identifier / "runs" / "1001" / "shared.txt", "ok")

    browse = load_secure_browse({}, SITE_PREFIX="/weppcloud", CULVERTS_ROOT=str(culverts_root))
    app = browse.create_app()
    token = _issue_token(
        token_class="user",
        roles=["PowerUser"],
        subject="42",
    )

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/culverts/{identifier}/download/runs/1001/shared.txt",
            headers={"Authorization": f"Bearer {token}"},
            follow_redirects=False,
        )

    assert response.status_code == 403
    assert "Token class is not allowed" in response.text


def test_culvert_download_requires_service_group_claim(
    tmp_path: Path,
    load_secure_browse,
) -> None:
    identifier = "culverts-service-groups-required"
    culverts_root = tmp_path / "culverts"
    _touch(culverts_root / identifier / "runs" / "1001" / "shared.txt", "ok")

    browse = load_secure_browse({}, SITE_PREFIX="/weppcloud", CULVERTS_ROOT=str(culverts_root))
    app = browse.create_app()
    token = _issue_service_token(identifier, roles=["User"], runs=[identifier])

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/culverts/{identifier}/download/runs/1001/shared.txt",
            headers={"Authorization": f"Bearer {token}"},
            follow_redirects=False,
        )

    assert response.status_code == 403
    assert "Service token missing required group scope" in response.text


@pytest.mark.parametrize("base,root_env", [("culverts", "CULVERTS_ROOT"), ("batch", "BATCH_RUNNER_ROOT")])
def test_group_routes_ignore_invalid_cookie_and_still_require_auth(
    tmp_path: Path,
    load_secure_browse,
    base: str,
    root_env: str,
) -> None:
    identifier = "group-invalid-cookie"
    group_root_root = tmp_path / base
    group_root = group_root_root / identifier
    _touch(group_root / "runs" / "1001" / "shared.txt", "ok")

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
        client.cookies.set("wepp_browse_jwt", "invalid-token")
        response = client.get(
            f"/weppcloud/{base}/{identifier}/browse/runs/1001/",
            follow_redirects=False,
        )

    if base == "batch":
        assert response.status_code == 302
        parsed = urlparse(response.headers["location"])
        assert parsed.path == f"/weppcloud/runs/batch;;{identifier};;_base/"
        next_value = parse_qs(parsed.query).get("next", [""])[0]
        assert next_value == f"/weppcloud/batch/{identifier}/browse/runs/1001/"
        return

    assert response.status_code == 401


@pytest.mark.parametrize("base,root_env", [("culverts", "CULVERTS_ROOT"), ("batch", "BATCH_RUNNER_ROOT")])
def test_group_routes_use_bearer_when_cookie_token_class_not_allowed(
    tmp_path: Path,
    load_secure_browse,
    base: str,
    root_env: str,
) -> None:
    identifier = "group-cookie-class-mismatch"
    group_root_root = tmp_path / base
    group_root = group_root_root / identifier
    _touch(group_root / "runs" / "1001" / "shared.txt", "ok")

    browse = load_secure_browse(
        {},
        SITE_PREFIX="/weppcloud",
        **{
            root_env: str(group_root_root),
        },
    )
    app = browse.create_app()

    cookie_token = _issue_token(
        token_class="session",
        subject="sid-group",
        extra_claims={"runid": identifier, "session_id": "sid-group"},
    )
    bearer_token = _issue_service_token(identifier, runs=[identifier], roles=["User"])

    with TestClient(app) as client:
        client.cookies.set("wepp_browse_jwt", cookie_token)
        response = client.get(
            f"/weppcloud/{base}/{identifier}/browse/runs/1001/",
            headers={"Authorization": f"Bearer {bearer_token}"},
            follow_redirects=False,
        )

    assert response.status_code == 200


@pytest.mark.parametrize("base,root_env", [("culverts", "CULVERTS_ROOT"), ("batch", "BATCH_RUNNER_ROOT")])
def test_group_routes_use_bearer_when_cookie_token_revoked(
    tmp_path: Path,
    load_secure_browse,
    monkeypatch: pytest.MonkeyPatch,
    base: str,
    root_env: str,
) -> None:
    identifier = "group-cookie-revoked"
    group_root_root = tmp_path / base
    group_root = group_root_root / identifier
    _touch(group_root / "runs" / "1001" / "shared.txt", "ok")

    browse = load_secure_browse(
        {},
        SITE_PREFIX="/weppcloud",
        **{
            root_env: str(group_root_root),
        },
    )
    app = browse.create_app()

    import wepppy.microservices.browse.auth as auth_mod

    def _check_revocation(jti: str) -> None:
        if jti == "revoked-cookie-jti":
            raise auth_mod.BrowseAuthError("Token has been revoked", status_code=403, code="forbidden")

    monkeypatch.setattr(auth_mod, "_check_revocation", _check_revocation)

    cookie_token = _issue_token(
        token_class="service",
        runs=[identifier],
        roles=["User"],
        extra_claims={"jti": "revoked-cookie-jti"},
    )
    bearer_token = _issue_token(
        token_class="service",
        runs=[identifier],
        roles=["User"],
        extra_claims={"jti": "ok-bearer-jti"},
    )

    with TestClient(app) as client:
        client.cookies.set("wepp_browse_jwt", cookie_token)
        response = client.get(
            f"/weppcloud/{base}/{identifier}/browse/runs/1001/",
            headers={"Authorization": f"Bearer {bearer_token}"},
            follow_redirects=False,
        )

    assert response.status_code == 200


@pytest.mark.parametrize(
    "base,root_env",
    [("culverts", "CULVERTS_ROOT"), ("batch", "BATCH_RUNNER_ROOT")],
)
def test_group_download_uses_bearer_when_cookie_identifier_mismatch(
    tmp_path: Path,
    load_secure_browse,
    base: str,
    root_env: str,
) -> None:
    identifier = "group-download-cookie-mismatch"
    group_root_root = tmp_path / base
    group_root = group_root_root / identifier
    _touch(group_root / "runs" / "1001" / "shared.txt", "ok")

    browse = load_secure_browse(
        {},
        SITE_PREFIX="/weppcloud",
        **{root_env: str(group_root_root)},
    )
    app = browse.create_app()

    service_groups = ["culverts"] if base == "culverts" else None
    cookie_token = _issue_service_token(
        identifier,
        roles=["User"],
        runs=["other-group"],
        service_groups=service_groups,
    )
    bearer_token = _issue_service_token(
        identifier,
        roles=["User"],
        runs=[identifier],
        service_groups=service_groups,
    )

    with TestClient(app) as client:
        client.cookies.set("wepp_browse_jwt", cookie_token)
        response = client.get(
            f"/weppcloud/{base}/{identifier}/download/runs/1001/shared.txt",
            headers={"Authorization": f"Bearer {bearer_token}"},
            follow_redirects=False,
        )

    assert response.status_code == 200
    assert response.text == "ok"


@pytest.mark.parametrize(
    "base,root_env",
    [("culverts", "CULVERTS_ROOT"), ("batch", "BATCH_RUNNER_ROOT")],
)
def test_group_gdalinfo_uses_bearer_when_cookie_identifier_mismatch(
    tmp_path: Path,
    load_secure_browse,
    monkeypatch: pytest.MonkeyPatch,
    base: str,
    root_env: str,
) -> None:
    identifier = "group-gdal-cookie-mismatch"
    group_root_root = tmp_path / base
    group_root = group_root_root / identifier
    _touch(group_root / "runs" / "1001" / "raster.tif", "raster")

    browse = load_secure_browse(
        {},
        SITE_PREFIX="/weppcloud",
        **{root_env: str(group_root_root)},
    )
    app = browse.create_app()
    _mock_gdalinfo_shell(monkeypatch)

    cookie_token = _issue_service_token(identifier, roles=["User"], runs=["other-group"])
    bearer_token = _issue_service_token(identifier, roles=["User"], runs=[identifier])

    with TestClient(app) as client:
        client.cookies.set("wepp_browse_jwt", cookie_token)
        response = client.get(
            f"/weppcloud/{base}/{identifier}/gdalinfo/runs/1001/raster.tif",
            headers={"Authorization": f"Bearer {bearer_token}"},
            follow_redirects=False,
        )

    assert response.status_code == 200
    assert response.json()["driver"] == "GTiff"


@pytest.mark.parametrize(
    "base,root_env,config_name",
    [("culverts", "CULVERTS_ROOT", "culvert-batch"), ("batch", "BATCH_RUNNER_ROOT", "batch")],
)
def test_group_dtale_uses_bearer_when_cookie_identifier_mismatch(
    tmp_path: Path,
    load_secure_browse,
    monkeypatch: pytest.MonkeyPatch,
    base: str,
    root_env: str,
    config_name: str,
) -> None:
    identifier = "group-dtale-cookie-mismatch"
    group_root_root = tmp_path / base
    group_root = group_root_root / identifier
    _touch(group_root / "runs" / "1001" / "table.csv", "a,b\n1,2\n")

    browse = load_secure_browse(
        {},
        SITE_PREFIX="/weppcloud",
        DTALE_SERVICE_URL="http://dtale-service",
        **{root_env: str(group_root_root)},
    )
    app = browse.create_app()
    captured_dtale = _mock_dtale_loader(monkeypatch)

    cookie_token = _issue_service_token(identifier, roles=["User"], runs=["other-group"])
    bearer_token = _issue_service_token(identifier, roles=["User"], runs=[identifier])

    with TestClient(app) as client:
        client.cookies.set("wepp_browse_jwt", cookie_token)
        response = client.get(
            f"/weppcloud/{base}/{identifier}/dtale/runs/1001/table.csv",
            headers={"Authorization": f"Bearer {bearer_token}"},
            follow_redirects=False,
        )

    assert response.status_code == 303
    assert captured_dtale["json"] == {
        "runid": identifier,
        "config": config_name,
        "path": "runs/1001/table.csv",
    }


@pytest.mark.parametrize("base,root_env", [("culverts", "CULVERTS_ROOT"), ("batch", "BATCH_RUNNER_ROOT")])
def test_group_root_only_path_uses_bearer_when_cookie_lacks_root_role(
    tmp_path: Path,
    load_secure_browse,
    base: str,
    root_env: str,
) -> None:
    identifier = "group-root-fallback"
    group_root_root = tmp_path / base
    group_root = group_root_root / identifier
    subpath = "runs/1001/_logs/profile.events.jsonl"
    _touch(group_root / subpath, "sensitive")

    browse = load_secure_browse(
        {},
        SITE_PREFIX="/weppcloud",
        **{
            root_env: str(group_root_root),
        },
    )
    app = browse.create_app()

    service_groups = ["culverts"] if base == "culverts" else None
    cookie_token = _issue_service_token(
        identifier,
        roles=["User"],
        runs=[identifier],
        service_groups=service_groups,
    )
    bearer_token = _issue_service_token(
        identifier,
        roles=["Root"],
        runs=[identifier],
        service_groups=service_groups,
    )

    with TestClient(app) as client:
        client.cookies.set("wepp_browse_jwt", cookie_token)
        response = client.get(
            f"/weppcloud/{base}/{identifier}/browse/{subpath}",
            headers={"Authorization": f"Bearer {bearer_token}"},
            follow_redirects=False,
        )

    assert response.status_code == 200


@pytest.mark.parametrize("base,root_env", [("culverts", "CULVERTS_ROOT"), ("batch", "BATCH_RUNNER_ROOT")])
def test_group_download_root_only_path_uses_bearer_when_cookie_lacks_root_role(
    tmp_path: Path,
    load_secure_browse,
    base: str,
    root_env: str,
) -> None:
    identifier = "group-download-root-fallback"
    group_root_root = tmp_path / base
    group_root = group_root_root / identifier
    subpath = "runs/1001/_logs/profile.events.jsonl"
    _touch(group_root / subpath, "sensitive")

    browse = load_secure_browse(
        {},
        SITE_PREFIX="/weppcloud",
        **{
            root_env: str(group_root_root),
        },
    )
    app = browse.create_app()

    service_groups = ["culverts"] if base == "culverts" else None
    cookie_token = _issue_service_token(
        identifier,
        roles=["User"],
        runs=[identifier],
        service_groups=service_groups,
    )
    bearer_token = _issue_service_token(
        identifier,
        roles=["Root"],
        runs=[identifier],
        service_groups=service_groups,
    )

    with TestClient(app) as client:
        client.cookies.set("wepp_browse_jwt", cookie_token)
        response = client.get(
            f"/weppcloud/{base}/{identifier}/download/{subpath}",
            headers={"Authorization": f"Bearer {bearer_token}"},
            follow_redirects=False,
        )

    assert response.status_code == 200
    assert response.text == "sensitive"


@pytest.mark.parametrize("base,root_env", [("culverts", "CULVERTS_ROOT"), ("batch", "BATCH_RUNNER_ROOT")])
def test_group_gdalinfo_root_only_path_uses_bearer_when_cookie_lacks_root_role(
    tmp_path: Path,
    load_secure_browse,
    monkeypatch: pytest.MonkeyPatch,
    base: str,
    root_env: str,
) -> None:
    identifier = "group-gdal-root-fallback"
    group_root_root = tmp_path / base
    group_root = group_root_root / identifier
    subpath = "runs/1001/_logs/raster.tif"
    _touch(group_root / subpath, "raster")

    browse = load_secure_browse(
        {},
        SITE_PREFIX="/weppcloud",
        **{
            root_env: str(group_root_root),
        },
    )
    app = browse.create_app()
    _mock_gdalinfo_shell(monkeypatch)

    cookie_token = _issue_service_token(identifier, roles=["User"], runs=[identifier])
    bearer_token = _issue_service_token(identifier, roles=["Root"], runs=[identifier])

    with TestClient(app) as client:
        client.cookies.set("wepp_browse_jwt", cookie_token)
        response = client.get(
            f"/weppcloud/{base}/{identifier}/gdalinfo/{subpath}",
            headers={"Authorization": f"Bearer {bearer_token}"},
            follow_redirects=False,
        )

    assert response.status_code == 200
    assert response.json()["driver"] == "GTiff"


@pytest.mark.parametrize(
    "base,root_env,config_name",
    [("culverts", "CULVERTS_ROOT", "culvert-batch"), ("batch", "BATCH_RUNNER_ROOT", "batch")],
)
def test_group_dtale_root_only_path_uses_bearer_when_cookie_lacks_root_role(
    tmp_path: Path,
    load_secure_browse,
    monkeypatch: pytest.MonkeyPatch,
    base: str,
    root_env: str,
    config_name: str,
) -> None:
    identifier = "group-dtale-root-fallback"
    group_root_root = tmp_path / base
    group_root = group_root_root / identifier
    subpath = "runs/1001/_logs/table.csv"
    _touch(group_root / subpath, "a,b\n1,2\n")

    browse = load_secure_browse(
        {},
        SITE_PREFIX="/weppcloud",
        DTALE_SERVICE_URL="http://dtale-service",
        **{
            root_env: str(group_root_root),
        },
    )
    app = browse.create_app()
    captured_dtale = _mock_dtale_loader(monkeypatch)

    cookie_token = _issue_service_token(identifier, roles=["User"], runs=[identifier])
    bearer_token = _issue_service_token(identifier, roles=["Root"], runs=[identifier])

    with TestClient(app) as client:
        client.cookies.set("wepp_browse_jwt", cookie_token)
        response = client.get(
            f"/weppcloud/{base}/{identifier}/dtale/{subpath}",
            headers={"Authorization": f"Bearer {bearer_token}"},
            follow_redirects=False,
        )

    assert response.status_code == 303
    assert captured_dtale["json"] == {
        "runid": identifier,
        "config": config_name,
        "path": subpath,
    }


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
    token = _issue_service_token(
        identifier,
        runs=[identifier],
        roles=["User"],
        service_groups=["culverts"] if base == "culverts" else None,
    )
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


def test_culvert_group_routes_reject_session_token_class(
    tmp_path: Path,
    load_secure_browse,
) -> None:
    identifier = "group-99"
    group_root_root = tmp_path / "culverts"
    _touch(group_root_root / identifier / "runs" / "1001" / "shared.txt", "ok")

    browse = load_secure_browse({}, SITE_PREFIX="/weppcloud", CULVERTS_ROOT=str(group_root_root))
    app = browse.create_app()
    token = _issue_token(
        token_class="session",
        runs=[identifier],
        subject="sid-123",
    )

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/culverts/{identifier}/browse/runs/1001/",
            headers={"Authorization": f"Bearer {token}"},
            follow_redirects=False,
        )

    assert response.status_code == 403


def test_batch_group_routes_accept_session_token_scoped_to_base_run(
    tmp_path: Path,
    load_secure_browse,
) -> None:
    identifier = "group-session-allowed"
    group_root_root = tmp_path / "batch"
    _touch(group_root_root / identifier / "runs" / "1001" / "shared.txt", "ok")

    browse = load_secure_browse({}, SITE_PREFIX="/weppcloud", BATCH_RUNNER_ROOT=str(group_root_root))
    app = browse.create_app()
    base_runid = f"batch;;{identifier};;_base"
    token = _issue_token(
        token_class="session",
        runs=[base_runid],
        subject="sid-123",
        extra_claims={"runid": base_runid, "session_id": "sid-123"},
    )

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/batch/{identifier}/browse/runs/1001/",
            headers={"Authorization": f"Bearer {token}"},
            follow_redirects=False,
        )

    assert response.status_code == 200


def test_private_browse_stale_session_cookie_redirects_for_reauth(
    tmp_path: Path,
    load_secure_browse,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runid = "run-private-stale-session"
    config = "cfg"
    run_root = tmp_path / runid
    _touch(run_root / "secret.txt", "shh")
    browse = load_secure_browse({runid: run_root}, SITE_PREFIX="/weppcloud")
    app = browse.create_app()

    import wepppy.microservices.rq_engine.auth as rq_auth

    class MissingMarkerRedis:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def exists(self, key: str) -> bool:
            return False

    monkeypatch.setattr(rq_auth.redis, "Redis", lambda **kwargs: MissingMarkerRedis())

    token = _issue_token(
        token_class="session",
        subject="sid-stale",
        runs=[runid],
        extra_claims={"runid": runid, "session_id": "sid-stale"},
    )

    with TestClient(app) as client:
        client.cookies.set("wepp_browse_jwt", token)
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/browse/secret.txt",
            follow_redirects=False,
        )

    assert response.status_code == 302
    parsed = urlparse(response.headers["location"])
    assert parsed.path == f"/weppcloud/runs/{runid}/"
    next_value = parse_qs(parsed.query).get("next", [""])[0]
    assert next_value == f"/weppcloud/runs/{runid}/{config}/browse/secret.txt"
