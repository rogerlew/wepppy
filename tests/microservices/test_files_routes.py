import importlib
import os
import zipfile
from pathlib import Path

import pytest

TestClient = pytest.importorskip("starlette.testclient").TestClient

pytestmark = pytest.mark.microservice


@pytest.fixture
def load_browse(monkeypatch):
    def _allow_auth(*args, **kwargs):
        import wepppy.microservices.browse.auth as auth_mod

        return auth_mod.AuthContext(
            claims={"token_class": "user", "roles": ["User"], "sub": "1"},
            token_class="user",
            roles=frozenset({"user"}),
        )

    def _loader(**env):
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        import wepppy.microservices.browse._download as download_mod
        import wepppy.microservices.browse.dtale as dtale_mod
        import wepppy.microservices.browse.files_api as files_api_mod
        import wepppy.microservices.browse.browse as browse_mod
        import wepppy.microservices._gdalinfo as gdalinfo_mod

        importlib.reload(download_mod)
        importlib.reload(dtale_mod)
        importlib.reload(files_api_mod)
        importlib.reload(gdalinfo_mod)
        browse_mod = importlib.reload(browse_mod)

        monkeypatch.setattr(download_mod, "authorize_run_request", _allow_auth)
        monkeypatch.setattr(download_mod, "authorize_group_request", _allow_auth)
        monkeypatch.setattr(dtale_mod, "authorize_run_request", _allow_auth)
        monkeypatch.setattr(dtale_mod, "authorize_group_request", _allow_auth)
        monkeypatch.setattr(files_api_mod, "authorize_run_request", _allow_auth)
        monkeypatch.setattr(gdalinfo_mod, "authorize_run_request", _allow_auth)
        monkeypatch.setattr(gdalinfo_mod, "authorize_group_request", _allow_auth)
        monkeypatch.setattr(browse_mod, "authorize_run_request", _allow_auth)
        monkeypatch.setattr(browse_mod, "authorize_group_request", _allow_auth)
        return browse_mod

    return _loader


def _write_file(path: Path, contents: str = "demo") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents)


def _write_nodir_zip(path: Path, entries: dict[str, bytes | str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, content in entries.items():
            data = content.encode("utf-8") if isinstance(content, str) else content
            zf.writestr(name, data)


def _make_auth(roles: tuple[str, ...] = ("user",)):
    import wepppy.microservices.browse.auth as auth_mod

    normalized_roles = tuple(role.lower() for role in roles)
    return auth_mod.AuthContext(
        claims={"token_class": "user", "roles": list(normalized_roles), "sub": "1"},
        token_class="user",
        roles=frozenset(normalized_roles),
    )


def _mock_dtale_loader(monkeypatch, *, target_url: str = "/weppcloud/dtale/main/demo") -> dict:
    import wepppy.microservices.browse.dtale as dtale_mod

    captured: dict = {}

    class DummyResponse:
        status_code = 200
        text = ""

        @staticmethod
        def json():
            return {"url": target_url}

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


def test_files_list_root(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-123"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()

    _write_file(run_root / "foo.txt", "hello")
    _write_file(run_root / "wepp" / "output" / "loss.txt", "loss")
    _write_file(run_root / "plots" / "plot-a.txt", "plot")

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(f"/weppcloud/runs/{runid}/{config}/files/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["runid"] == runid
    assert payload["config"] == config
    names = {entry["name"] for entry in payload["entries"]}
    assert "foo.txt" in names
    assert "plots" in names

    file_entry = next(entry for entry in payload["entries"] if entry["name"] == "foo.txt")
    assert file_entry["type"] == "file"
    assert "size_bytes" in file_entry
    assert file_entry["download_url"].endswith(
        f"/weppcloud/runs/{runid}/{config}/download/foo.txt"
    )

    dir_entry = next(entry for entry in payload["entries"] if entry["name"] == "plots")
    assert dir_entry["type"] == "directory"
    assert dir_entry.get("child_count") == 1


def test_files_meta_response(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-456"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()

    _write_file(run_root / "foo.txt", "hello")

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(f"/weppcloud/runs/{runid}/{config}/files/foo.txt?meta=true")

    assert response.status_code == 200
    payload = response.json()
    assert payload["type"] == "file"
    assert payload["name"] == "foo.txt"
    assert "size_bytes" in payload
    assert payload["preview_available"] is True
    assert payload["content_type"].startswith("text/")


def test_files_meta_directory_response(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-456a"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()

    _write_file(run_root / "plots" / "plot-a.txt", "plot")

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(f"/weppcloud/runs/{runid}/{config}/files/plots?meta=true")

    assert response.status_code == 200
    payload = response.json()
    assert payload["type"] == "directory"
    assert payload["name"] == "plots"
    assert payload.get("child_count") == 1


def test_files_rejects_non_json_accept(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-789"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()
    _write_file(run_root / "foo.txt", "hello")

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/files/",
            headers={"Accept": "text/html"},
        )

    assert response.status_code == 406
    payload = response.json()
    assert payload["error"]["code"] == "not_acceptable"
    assert payload["error"]["details"]


def test_files_accepts_json_application_wildcard(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-791a"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()
    _write_file(run_root / "foo.txt", "hello")

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/files/",
            headers={"Accept": "application/*;q=0.5"},
        )

    assert response.status_code == 200


def test_files_accepts_json_suffix_type(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-791b"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()
    _write_file(run_root / "foo.txt", "hello")

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/files/",
            headers={"Accept": "application/vnd.wepp+json;q=0.2"},
        )

    assert response.status_code == 200


def test_files_rejects_json_q_zero(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-791"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()
    _write_file(run_root / "foo.txt", "hello")

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/files/",
            headers={"Accept": "application/json;q=0, text/html"},
        )

    assert response.status_code == 406
    payload = response.json()
    assert payload["error"]["code"] == "not_acceptable"
    assert payload["error"]["details"]


def test_files_accepts_json_with_positive_q(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-792"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()
    _write_file(run_root / "foo.txt", "hello")

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/files/",
            headers={"Accept": "application/json;q=0.1, text/html"},
        )

    assert response.status_code == 200


def test_files_accepts_json_with_wildcard_override(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-793"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()
    _write_file(run_root / "foo.txt", "hello")

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/files/",
            headers={"Accept": "application/json;q=0, */*;q=1"},
        )

    assert response.status_code == 200


def test_files_run_not_found(tmp_path: Path, monkeypatch, load_browse):
    runid = "missing-run"
    config = "disturbed9002_wbt"
    missing_root = tmp_path / "missing"

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(missing_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(f"/weppcloud/runs/{runid}/{config}/files/")

    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "run_not_found"
    assert payload["error"]["details"]


def test_files_rejects_path_traversal(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-999"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(f"/weppcloud/runs/{runid}/{config}/files/%2e%2e/secret")

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "path_outside_root"
    assert payload["error"]["details"]


@pytest.mark.parametrize(
    "subpath",
    [
        "_logs",
        "_logs/profile.events.jsonl",
        "wepp/output/profile.events.jsonl",
    ],
)
def test_files_blocks_recorder_log_paths(tmp_path: Path, monkeypatch, load_browse, subpath: str):
    runid = "run-logs-files"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()
    _write_file(run_root / "_logs" / "profile.events.jsonl", '{"ok":true}\n')

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(f"/weppcloud/runs/{runid}/{config}/files/{subpath}?meta=true")

    assert response.status_code == 403
    payload = response.json()
    assert payload["error"]["code"] == "forbidden_path"
    assert "recorder log artifacts" in payload["error"]["details"]


@pytest.mark.parametrize(
    "subpath",
    [
        "_logs/",
        "_logs/profile.events.jsonl",
        "wepp/output/profile.events.jsonl",
    ],
)
def test_browse_blocks_recorder_log_paths(tmp_path: Path, monkeypatch, load_browse, subpath: str):
    runid = "run-logs-browse"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()
    _write_file(run_root / "_logs" / "profile.events.jsonl", '{"ok":true}\n')
    _write_file(run_root / "wepp" / "output" / "profile.events.jsonl", '{"ok":true}\n')

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(f"/weppcloud/runs/{runid}/{config}/browse/{subpath}")

    assert response.status_code == 403
    assert "recorder log artifacts" in response.text


@pytest.mark.parametrize(
    "subpath",
    [
        "_logs/profile.events.jsonl",
        "wepp/output/profile.events.jsonl",
    ],
)
def test_download_blocks_recorder_log_paths(tmp_path: Path, monkeypatch, load_browse, subpath: str):
    runid = "run-logs-download"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()
    _write_file(run_root / "_logs" / "profile.events.jsonl", '{"ok":true}\n')
    _write_file(run_root / "wepp" / "output" / "profile.events.jsonl", '{"ok":true}\n')

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    import wepppy.microservices.browse._download as download_mod
    monkeypatch.setattr(download_mod, "get_wd", lambda _runid, prefer_active=False: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(f"/weppcloud/runs/{runid}/{config}/download/{subpath}")

    assert response.status_code == 403
    assert "recorder log artifacts" in response.text


def test_aria2c_spec_excludes_hidden_and_recorder_artifacts(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-aria2c"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()

    _write_file(run_root / "visible.txt", "ok")
    _write_file(run_root / "watershed.nodir", "archive-bytes")
    _write_file(run_root / "nested" / "table.csv", "a,b\n1,2\n")
    _write_file(run_root / ".secret", "hidden")
    _write_file(run_root / "nested" / ".secret2", "hidden")
    _write_file(run_root / "_logs" / "profile.events.jsonl", '{"ok":true}\n')
    _write_file(run_root / "wepp" / "output" / "profile.events.jsonl", '{"ok":true}\n')
    _write_file(run_root / "exceptions.log", "traceback")
    _write_file(run_root / "nested" / "exception_factory.log", "traceback")

    browse = load_browse(SITE_PREFIX="/weppcloud")
    import wepppy.microservices.browse._download as download_mod
    monkeypatch.setattr(download_mod, "get_wd", lambda _runid, prefer_active=False: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(f"/weppcloud/runs/{runid}/{config}/aria2c.spec")

    assert response.status_code == 200
    spec = response.text
    assert "visible.txt" in spec
    assert "watershed.nodir" not in spec
    assert "nested/table.csv" in spec
    assert ".secret" not in spec
    assert "profile.events.jsonl" not in spec
    assert "exceptions.log" not in spec
    assert "exception_factory.log" not in spec


def test_aria2c_spec_uses_external_host_and_site_prefix(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-aria2c-host"
    config = "cfg"
    run_root = tmp_path / "run"
    run_root.mkdir()

    _write_file(run_root / "visible.txt", "ok")

    browse = load_browse(
        SITE_PREFIX="/weppcloud-alt",
        EXTERNAL_HOST="example.test",
        OAUTH_REDIRECT_SCHEME="https",
    )
    import wepppy.microservices.browse._download as download_mod
    monkeypatch.setattr(download_mod, "get_wd", lambda _runid, prefer_active=False: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(f"/weppcloud-alt/runs/{runid}/{config}/aria2c.spec")

    assert response.status_code == 200
    assert (
        "https://example.test/weppcloud-alt/runs/"
        f"{runid}/{config}/download/visible.txt"
    ) in response.text



@pytest.mark.parametrize(
    "endpoint",
    [
        "files/watershed.nodir/hillslopes/",
        "files/watershed.nodir?meta=true",
        "download/watershed.nodir/hillslopes/h001.slp",
        "download/watershed.nodir",
    ],
)
def test_archive_boundary_paths_rejected_in_directory_mode(
    tmp_path: Path,
    monkeypatch,
    load_browse,
    endpoint: str,
):
    runid = "run-nodir-retired"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()
    _write_nodir_zip(run_root / "watershed.nodir", {"hillslopes/h001.slp": "alpha"})

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))

    import wepppy.microservices.browse._download as download_mod

    monkeypatch.setattr(download_mod, "get_wd", lambda _runid, prefer_active=False: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(f"/weppcloud/runs/{runid}/{config}/{endpoint}")

    assert response.status_code == 400
    if endpoint.startswith("files/"):
        payload = response.json()
        assert payload["error"]["code"] == "path_outside_root"
        assert "archive boundary paths are retired" in payload["error"]["details"]
    else:
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            assert response.json()["detail"] == "Invalid path."
        else:
            assert response.text == "Invalid path."


def test_dtale_archive_boundary_rejected_in_directory_mode(
    tmp_path: Path,
    monkeypatch,
    load_browse,
):
    runid = "run-nodir-dtale-retired"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()
    _write_nodir_zip(run_root / "watershed.nodir", {"maps/table.csv": "a,b\n1,2\n"})

    browse = load_browse(
        SITE_PREFIX="/weppcloud",
        DTALE_SERVICE_URL="http://dtale-service",
    )
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))

    app = browse.create_app()
    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/dtale/watershed.nodir/maps/table.csv",
            follow_redirects=False,
        )

    assert response.status_code == 400
    if "application/json" in response.headers.get("content-type", ""):
        assert response.json()["detail"] == "Invalid path."
    else:
        assert response.text == "Invalid path."


def test_gdalinfo_archive_boundary_rejected_in_directory_mode(
    tmp_path: Path,
    monkeypatch,
    load_browse,
):
    runid = "run-nodir-gdalinfo-retired"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()
    _write_nodir_zip(run_root / "watershed.nodir", {"raster/dem.tif": b"abc"})

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))

    import wepppy.microservices._gdalinfo as gdalinfo_mod

    monkeypatch.setattr(gdalinfo_mod, "get_wd", lambda _runid, prefer_active=False: str(run_root))

    async def _should_not_run(*args, **kwargs):  # noqa: ARG001
        raise AssertionError("gdalinfo shell command should not run for retired archive-boundary paths")

    monkeypatch.setattr(gdalinfo_mod, "_run_shell_command", _should_not_run)

    app = browse.create_app()
    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/gdalinfo/watershed.nodir/raster/dem.tif"
        )

    assert response.status_code == 400
    if "application/json" in response.headers.get("content-type", ""):
        assert response.json()["detail"] == "Invalid path."
    else:
        assert response.text == "Invalid path."
@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink not supported")
def test_files_symlink_target_outside_root(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-321"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    outside = tmp_path / "outside"
    run_root.mkdir()
    outside.mkdir()

    os.symlink(str(outside), run_root / "external")

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(f"/weppcloud/runs/{runid}/{config}/files/")

    assert response.status_code == 200
    payload = response.json()
    entry = next(item for item in payload["entries"] if item["name"] == "external")
    assert entry["type"] == "symlink"
    assert entry.get("symlink_is_dir") is True
    assert "symlink_target" not in entry


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink not supported")
def test_files_rejects_symlink_traversal(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-654"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    outside = tmp_path / "outside"
    run_root.mkdir()
    outside.mkdir()

    os.symlink(str(outside), run_root / "external")

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(f"/weppcloud/runs/{runid}/{config}/files/external/")

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "not_a_directory"
    assert payload["error"]["details"]


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink not supported")
def test_files_meta_rejects_symlink_outside_allowed_roots(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-987"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    outside = tmp_path / "outside"
    run_root.mkdir()
    outside.mkdir()

    os.symlink(str(outside), run_root / "external")

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/files/external?meta=true"
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "path_outside_root"
    assert payload["error"]["details"]


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink not supported")
def test_runs_routes_allow_symlink_to_parent_maps(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-parent-maps"
    config = "disturbed9002_wbt"
    group_root = tmp_path / "culvert-group"
    run_root = group_root / "runs" / "1001"
    run_root.mkdir(parents=True)

    _write_file(group_root / "maps" / "layer.txt", "parent-map")
    _write_file(group_root / "maps" / "table.csv", "a,b\n1,2\n")
    os.symlink("../../maps", run_root / "maps")

    browse = load_browse(
        SITE_PREFIX="/weppcloud",
        DTALE_SERVICE_URL="http://dtale-service",
        DTALE_INTERNAL_TOKEN="internal-token",
    )
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))

    import wepppy.microservices.browse._download as download_mod

    monkeypatch.setattr(download_mod, "get_wd", lambda _runid, prefer_active=False: str(run_root))
    captured = _mock_dtale_loader(monkeypatch)

    app = browse.create_app()
    with TestClient(app) as client:
        files_response = client.get(f"/weppcloud/runs/{runid}/{config}/files/maps/")
        browse_response = client.get(f"/weppcloud/runs/{runid}/{config}/browse/maps/")
        download_response = client.get(
            f"/weppcloud/runs/{runid}/{config}/download/maps/layer.txt"
        )
        dtale_response = client.get(
            f"/weppcloud/runs/{runid}/{config}/dtale/maps/table.csv",
            follow_redirects=False,
        )

    assert files_response.status_code == 200
    names = {entry["name"] for entry in files_response.json()["entries"]}
    assert names == {"layer.txt", "table.csv"}

    assert browse_response.status_code == 200
    assert "layer.txt" in browse_response.text

    assert download_response.status_code == 200
    assert download_response.text == "parent-map"

    assert dtale_response.status_code == 303
    assert dtale_response.headers["location"] == "/weppcloud/dtale/main/demo"
    assert captured["url"] == "http://dtale-service/internal/load"
    assert captured["json"] == {
        "runid": runid,
        "config": config,
        "path": "maps/table.csv",
    }
    assert captured["headers"] == {"X-DTALE-TOKEN": "internal-token"}


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink not supported")
def test_omni_scenario_allows_symlink_to_parent_run_root(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-omni"
    config = "disturbed9002_wbt"
    parent_run_root = tmp_path / "runs" / "ab" / runid
    scenario_root = parent_run_root / "_pups" / "omni" / "scenarios" / "scenario-1"
    scenario_root.mkdir(parents=True)

    _write_file(parent_run_root / "maps" / "omni.txt", "omni-parent-map")
    os.symlink("../../../../maps", scenario_root / "shared_maps")

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(scenario_root))

    import wepppy.microservices.browse._download as download_mod

    monkeypatch.setattr(download_mod, "get_wd", lambda _runid, prefer_active=False: str(scenario_root))
    app = browse.create_app()

    with TestClient(app) as client:
        files_response = client.get(f"/weppcloud/runs/{runid}/{config}/files/shared_maps/")
        browse_response = client.get(f"/weppcloud/runs/{runid}/{config}/browse/shared_maps/")
        download_response = client.get(
            f"/weppcloud/runs/{runid}/{config}/download/shared_maps/omni.txt"
        )

    assert files_response.status_code == 200
    entries = {entry["name"] for entry in files_response.json()["entries"]}
    assert entries == {"omni.txt"}

    assert browse_response.status_code == 200
    assert "omni.txt" in browse_response.text

    assert download_response.status_code == 200
    assert download_response.text == "omni-parent-map"


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink not supported")
def test_omni_scenario_blocks_restricted_symlink_targets(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-omni-logs"
    config = "disturbed9002_wbt"
    parent_run_root = tmp_path / "runs" / "cd" / runid
    scenario_root = parent_run_root / "_pups" / "omni" / "scenarios" / "scenario-2"
    scenario_root.mkdir(parents=True)

    _write_file(parent_run_root / "_logs" / "events.csv", "a,b\n1,2\n")
    os.symlink("../../../../_logs", scenario_root / "shared_logs")

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(scenario_root))

    import wepppy.microservices.browse._download as download_mod

    monkeypatch.setattr(download_mod, "get_wd", lambda _runid, prefer_active=False: str(scenario_root))
    app = browse.create_app()

    with TestClient(app) as client:
        files_response = client.get(
            f"/weppcloud/runs/{runid}/{config}/files/shared_logs?meta=true"
        )
        browse_response = client.get(f"/weppcloud/runs/{runid}/{config}/browse/shared_logs/")
        download_response = client.get(
            f"/weppcloud/runs/{runid}/{config}/download/shared_logs/events.csv"
        )
        dtale_response = client.get(
            f"/weppcloud/runs/{runid}/{config}/dtale/shared_logs/events.csv",
            follow_redirects=False,
        )

    assert files_response.status_code == 403
    files_payload = files_response.json()
    assert files_payload["error"]["code"] == "forbidden_path"

    assert browse_response.status_code == 403
    assert "recorder log artifacts" in browse_response.text

    assert download_response.status_code == 403
    assert "recorder log artifacts" in download_response.text

    assert dtale_response.status_code == 403
    assert "recorder log artifacts" in dtale_response.text


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink not supported")
def test_culvert_routes_allow_symlink_to_parent_maps(tmp_path: Path, monkeypatch, load_browse):
    batch_uuid = "culvert-batch-42"
    culverts_root = tmp_path / "culverts"
    batch_root = culverts_root / batch_uuid
    run_root = batch_root / "runs" / "1001"
    run_root.mkdir(parents=True)

    _write_file(batch_root / "maps" / "culvert.txt", "culvert-map")
    _write_file(batch_root / "maps" / "culvert.csv", "a,b\n1,2\n")
    os.symlink("../../maps", run_root / "shared_maps")

    browse = load_browse(
        SITE_PREFIX="/weppcloud",
        CULVERTS_ROOT=str(culverts_root),
        DTALE_SERVICE_URL="http://dtale-service",
    )
    captured = _mock_dtale_loader(monkeypatch)
    app = browse.create_app()

    with TestClient(app) as client:
        browse_response = client.get(
            f"/weppcloud/culverts/{batch_uuid}/browse/runs/1001/shared_maps/"
        )
        download_response = client.get(
            f"/weppcloud/culverts/{batch_uuid}/download/runs/1001/shared_maps/culvert.txt"
        )
        dtale_response = client.get(
            f"/weppcloud/culverts/{batch_uuid}/dtale/runs/1001/shared_maps/culvert.csv",
            follow_redirects=False,
        )

    assert browse_response.status_code == 200
    assert "culvert.txt" in browse_response.text

    assert download_response.status_code == 200
    assert download_response.text == "culvert-map"

    assert dtale_response.status_code == 303
    assert captured["json"] == {
        "runid": batch_uuid,
        "config": "culvert-batch",
        "path": "runs/1001/shared_maps/culvert.csv",
    }


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink not supported")
def test_batch_routes_allow_symlink_to_parent_maps(tmp_path: Path, monkeypatch, load_browse):
    batch_name = "batch-alpha"
    batch_root_root = tmp_path / "batch"
    batch_root = batch_root_root / batch_name
    run_root = batch_root / "runs" / "1001"
    run_root.mkdir(parents=True)

    _write_file(batch_root / "maps" / "batch.txt", "batch-map")
    _write_file(batch_root / "maps" / "batch.csv", "a,b\n1,2\n")
    os.symlink("../../maps", run_root / "shared_maps")

    browse = load_browse(
        SITE_PREFIX="/weppcloud",
        BATCH_RUNNER_ROOT=str(batch_root_root),
        DTALE_SERVICE_URL="http://dtale-service",
    )
    captured = _mock_dtale_loader(monkeypatch)
    app = browse.create_app()

    with TestClient(app) as client:
        browse_response = client.get(
            f"/weppcloud/batch/{batch_name}/browse/runs/1001/shared_maps/"
        )
        download_response = client.get(
            f"/weppcloud/batch/{batch_name}/download/runs/1001/shared_maps/batch.txt"
        )
        dtale_response = client.get(
            f"/weppcloud/batch/{batch_name}/dtale/runs/1001/shared_maps/batch.csv",
            follow_redirects=False,
        )

    assert browse_response.status_code == 200
    assert "batch.txt" in browse_response.text

    assert download_response.status_code == 200
    assert download_response.text == "batch-map"

    assert dtale_response.status_code == 303
    assert captured["json"] == {
        "runid": batch_name,
        "config": "batch",
        "path": "runs/1001/shared_maps/batch.csv",
    }


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink not supported")
def test_batch_routes_reject_symlink_to_outside_root(tmp_path: Path, load_browse):
    batch_name = "batch-outside"
    batch_root_root = tmp_path / "batch"
    batch_root = batch_root_root / batch_name
    run_root = batch_root / "runs" / "1001"
    outside = tmp_path / "outside"
    run_root.mkdir(parents=True)
    outside.mkdir()

    _write_file(outside / "outside.txt", "outside")
    _write_file(outside / "outside.csv", "a,b\n1,2\n")
    os.symlink(str(outside), run_root / "external")

    browse = load_browse(
        SITE_PREFIX="/weppcloud",
        BATCH_RUNNER_ROOT=str(batch_root_root),
    )
    app = browse.create_app()

    with TestClient(app) as client:
        browse_response = client.get(
            f"/weppcloud/batch/{batch_name}/browse/runs/1001/external/"
        )
        download_response = client.get(
            f"/weppcloud/batch/{batch_name}/download/runs/1001/external/outside.txt"
        )
        dtale_response = client.get(
            f"/weppcloud/batch/{batch_name}/dtale/runs/1001/external/outside.csv",
            follow_redirects=False,
        )

    assert browse_response.status_code == 403
    assert download_response.status_code == 403
    assert dtale_response.status_code == 403


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink not supported")
def test_dtale_rejects_symlink_outside_allowed_roots_for_runs(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-dtale-outside"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    outside = tmp_path / "outside"
    run_root.mkdir()
    outside.mkdir()

    _write_file(outside / "table.csv", "a,b\n1,2\n")
    os.symlink(str(outside), run_root / "external")

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/dtale/external/table.csv",
            follow_redirects=False,
        )

    assert response.status_code == 403


@pytest.mark.parametrize(
    "endpoint,subpath",
    [
        ("browse", "_LoGs/PROFILE.EVENTS.JSONL"),
        ("browse", "_LoGs%5CPROFILE.EVENTS.JSONL"),
        ("download", "_LoGs/PROFILE.EVENTS.JSONL"),
        ("download", "_LoGs%5CPROFILE.EVENTS.JSONL"),
        ("dtale", "_LoGs/PROFILE.EVENTS.JSONL"),
        ("dtale", "_LoGs%5CPROFILE.EVENTS.JSONL"),
    ],
)
def test_runs_routes_block_case_and_mixed_separator_variants(
    tmp_path: Path,
    monkeypatch,
    load_browse,
    endpoint: str,
    subpath: str,
):
    runid = "run-case-variants"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()
    _write_file(run_root / "_logs" / "profile.events.jsonl", '{"ok":true}\n')

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    import wepppy.microservices.browse._download as download_mod
    monkeypatch.setattr(download_mod, "get_wd", lambda _runid, prefer_active=False: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/{endpoint}/{subpath}",
            follow_redirects=False,
        )

    assert response.status_code == 403


@pytest.mark.parametrize(
    "endpoint,subpath",
    [
        ("browse", "%2e%2e/secret"),
        ("download", "%2e%2e/secret"),
        ("dtale", "%2e%2e/secret.csv"),
    ],
)
def test_runs_routes_reject_encoded_dotdot_paths(
    tmp_path: Path,
    monkeypatch,
    load_browse,
    endpoint: str,
    subpath: str,
):
    runid = "run-encoded-dotdot"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    import wepppy.microservices.browse._download as download_mod
    monkeypatch.setattr(download_mod, "get_wd", lambda _runid, prefer_active=False: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/{endpoint}/{subpath}",
            follow_redirects=False,
        )

    assert 400 <= response.status_code < 500


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink not supported")
def test_runs_routes_allow_symlink_chain_to_parent_maps(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-chain"
    config = "disturbed9002_wbt"
    group_root = tmp_path / "group"
    run_root = group_root / "runs" / "1001"
    run_root.mkdir(parents=True)

    _write_file(group_root / "maps" / "chain.txt", "chain-map")
    _write_file(group_root / "maps" / "chain.csv", "a,b\n1,2\n")
    os.symlink("maps_target", run_root / "maps_link")
    os.symlink("../../maps", run_root / "maps_target")

    browse = load_browse(
        SITE_PREFIX="/weppcloud",
        DTALE_SERVICE_URL="http://dtale-service",
    )
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    import wepppy.microservices.browse._download as download_mod
    monkeypatch.setattr(download_mod, "get_wd", lambda _runid, prefer_active=False: str(run_root))
    captured = _mock_dtale_loader(monkeypatch)
    app = browse.create_app()

    with TestClient(app) as client:
        files_response = client.get(
            f"/weppcloud/runs/{runid}/{config}/files/maps_link/"
        )
        browse_response = client.get(
            f"/weppcloud/runs/{runid}/{config}/browse/maps_link/"
        )
        download_response = client.get(
            f"/weppcloud/runs/{runid}/{config}/download/maps_link/chain.txt"
        )
        dtale_response = client.get(
            f"/weppcloud/runs/{runid}/{config}/dtale/maps_link/chain.csv",
            follow_redirects=False,
        )

    assert files_response.status_code == 200
    assert browse_response.status_code == 200
    assert download_response.status_code == 200
    assert download_response.text == "chain-map"
    assert dtale_response.status_code == 303
    assert captured["json"]["path"] == "maps_link/chain.csv"


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink not supported")
def test_symlink_loops_fail_closed_without_server_errors(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-loop"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()
    os.symlink("loop_dir", run_root / "loop_dir")
    os.symlink("loop.csv", run_root / "loop.csv")

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    import wepppy.microservices.browse._download as download_mod
    monkeypatch.setattr(download_mod, "get_wd", lambda _runid, prefer_active=False: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        files_response = client.get(
            f"/weppcloud/runs/{runid}/{config}/files/loop_dir?meta=true"
        )
        browse_response = client.get(
            f"/weppcloud/runs/{runid}/{config}/browse/loop_dir/",
            follow_redirects=False,
        )
        download_response = client.get(
            f"/weppcloud/runs/{runid}/{config}/download/loop_dir",
            follow_redirects=False,
        )
        dtale_response = client.get(
            f"/weppcloud/runs/{runid}/{config}/dtale/loop.csv",
            follow_redirects=False,
        )

    assert files_response.status_code == 400
    assert browse_response.status_code == 403
    assert download_response.status_code == 403
    assert dtale_response.status_code == 403


@pytest.mark.parametrize(
    "route_prefix,env_key",
    [
        ("culverts", "CULVERTS_ROOT"),
        ("batch", "BATCH_RUNNER_ROOT"),
    ],
)
@pytest.mark.parametrize("endpoint", ["browse", "download", "dtale"])
@pytest.mark.parametrize(
    "subpath",
    [
        "_LoGs/PROFILE.EVENTS.JSONL",
        "_LoGs%5CPROFILE.EVENTS.JSONL",
    ],
)
def test_culvert_and_batch_routes_block_direct_restricted_paths(
    tmp_path: Path,
    load_browse,
    route_prefix: str,
    env_key: str,
    endpoint: str,
    subpath: str,
):
    bucket_root = tmp_path / route_prefix
    identifier = f"{route_prefix}-case"
    run_root = bucket_root / identifier
    run_root.mkdir(parents=True)
    _write_file(run_root / "_logs" / "profile.events.jsonl", '{"ok":true}\n')

    browse = load_browse(
        SITE_PREFIX="/weppcloud",
        **{env_key: str(bucket_root)},
    )
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/{route_prefix}/{identifier}/{endpoint}/{subpath}",
            follow_redirects=False,
        )

    assert response.status_code == 403


@pytest.mark.parametrize(
    "endpoint,subpath",
    [
        ("files", ".secret?meta=true"),
        ("browse", ".secret"),
        ("download", ".secret"),
        ("dtale", ".secret.csv"),
    ],
)
def test_runs_routes_block_direct_hidden_paths(
    tmp_path: Path,
    monkeypatch,
    load_browse,
    endpoint: str,
    subpath: str,
):
    runid = "run-hidden-direct"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()
    _write_file(run_root / ".secret", "hidden")
    _write_file(run_root / ".secret.csv", "a,b\n1,2\n")

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    import wepppy.microservices.browse._download as download_mod
    monkeypatch.setattr(download_mod, "get_wd", lambda _runid, prefer_active=False: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/{endpoint}/{subpath}",
            follow_redirects=False,
        )

    assert response.status_code == 403


@pytest.mark.parametrize(
    "route_prefix,env_key",
    [
        ("culverts", "CULVERTS_ROOT"),
        ("batch", "BATCH_RUNNER_ROOT"),
    ],
)
@pytest.mark.parametrize(
    "endpoint,subpath",
    [
        ("browse", ".secret"),
        ("download", ".secret"),
        ("dtale", ".secret.csv"),
    ],
)
def test_culvert_and_batch_routes_block_direct_hidden_paths(
    tmp_path: Path,
    load_browse,
    route_prefix: str,
    env_key: str,
    endpoint: str,
    subpath: str,
):
    bucket_root = tmp_path / route_prefix
    identifier = f"{route_prefix}-hidden"
    run_root = bucket_root / identifier
    run_root.mkdir(parents=True)
    _write_file(run_root / ".secret", "hidden")
    _write_file(run_root / ".secret.csv", "a,b\n1,2\n")

    browse = load_browse(
        SITE_PREFIX="/weppcloud",
        **{env_key: str(bucket_root)},
    )
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/{route_prefix}/{identifier}/{endpoint}/{subpath}",
            follow_redirects=False,
        )

    assert response.status_code == 403


def test_files_validation_errors_include_details(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-555"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()
    _write_file(run_root / "foo.txt", "hello")

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/files/?limit=0&offset=-1&pattern=foo/bar&sort=bad&order=down&meta=maybe"
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["details"]
    assert payload.get("errors")


def test_files_limit_over_max_rejected(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-559b"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()
    _write_file(run_root / "foo.txt", "hello")

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/files/?limit=10001"
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"


def test_files_pattern_allows_dash_prefix(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-555a"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()

    _write_file(run_root / "-R", "hello")
    _write_file(run_root / "alpha.txt", "a")

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/files/?pattern=-*"
        )

    assert response.status_code == 200
    payload = response.json()
    names = {entry["name"] for entry in payload["entries"]}
    assert names == {"-R"}


def test_files_pattern_allows_negation(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-555b"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()

    _write_file(run_root / "alpha.txt", "a")
    _write_file(run_root / "beta.txt", "b")

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/files/?pattern=[!a]*.txt"
        )

    assert response.status_code == 200
    payload = response.json()
    names = {entry["name"] for entry in payload["entries"]}
    assert names == {"beta.txt"}


def test_files_pattern_filtering(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-556"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()

    _write_file(run_root / "alpha.txt", "a")
    _write_file(run_root / "beta.txt", "b")
    _write_file(run_root / "alpha.log", "c")

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/files/?pattern=*.txt"
        )

    assert response.status_code == 200
    payload = response.json()
    names = {entry["name"] for entry in payload["entries"]}
    assert names == {"alpha.txt", "beta.txt"}


def test_files_pattern_allows_dotdot(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-557"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()

    _write_file(run_root / "alpha.txt", "a")
    _write_file(tmp_path / "parent.txt", "p")

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/files/?pattern=.."
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["entries"] == []


def test_files_pattern_literal_underscore_percent(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-557b"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()
    data_dir = run_root / "data"
    data_dir.mkdir()

    _write_file(data_dir / "file_name.txt", "a")
    _write_file(data_dir / "filename.txt", "b")
    _write_file(data_dir / "file%name.txt", "c")

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/files/data/?pattern=file_name*"
        )

    assert response.status_code == 200
    payload = response.json()
    names = {entry["name"] for entry in payload["entries"]}
    assert names == {"file_name.txt"}

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/files/data/?pattern=file%25name*"
        )

    assert response.status_code == 200
    payload = response.json()
    names = {entry["name"] for entry in payload["entries"]}
    assert names == {"file%name.txt"}

    browse.create_manifest(str(run_root))
    app = browse.create_app()
    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/files/data/?pattern=file_name*"
        )

    assert response.status_code == 200
    payload = response.json()
    names = {entry["name"] for entry in payload["entries"]}
    assert names == {"file_name.txt"}

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/files/data/?pattern=file%25name*"
        )

    assert response.status_code == 200
    payload = response.json()
    names = {entry["name"] for entry in payload["entries"]}
    assert names == {"file%name.txt"}


def test_files_pattern_rejects_backslash(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-557a"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()
    _write_file(run_root / "alpha.txt", "a")

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/files/?pattern=foo%5Cbar"
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"


def test_files_handles_dash_filenames(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-558"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()

    _write_file(run_root / "-R", "hello")
    _write_file(run_root / "alpha.txt", "a")

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(f"/weppcloud/runs/{runid}/{config}/files/?pattern=*")

    assert response.status_code == 200
    payload = response.json()
    names = {entry["name"] for entry in payload["entries"]}
    assert "-R" in names


def test_files_not_a_directory(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-559"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()
    _write_file(run_root / "foo.txt", "hello")

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(f"/weppcloud/runs/{runid}/{config}/files/foo.txt")

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "not_a_directory"
    assert payload["error"]["details"]


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink not supported")
def test_files_meta_symlink_inside_root(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-559a"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()

    _write_file(run_root / "data" / "alpha.txt", "a")
    os.symlink("data/alpha.txt", run_root / "link.txt")

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/files/link.txt?meta=true"
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["type"] == "symlink"
    assert payload.get("symlink_is_dir") is False
    assert payload.get("symlink_target") == "data/alpha.txt"


def test_files_path_not_found(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-560"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(f"/weppcloud/runs/{runid}/{config}/files/missing")

    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "path_not_found"
    assert payload["error"]["details"]


def test_files_pagination_and_sort(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-561"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()

    _write_file(run_root / "a.txt", "a")
    _write_file(run_root / "b.txt", "bb")
    _write_file(run_root / "c.txt", "ccc")

    os.utime(run_root / "a.txt", (1, 1))
    os.utime(run_root / "b.txt", (2, 2))
    os.utime(run_root / "c.txt", (3, 3))

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/files/?limit=2&offset=1&sort=name&order=asc"
        )

    assert response.status_code == 200
    payload = response.json()
    names = [entry["name"] for entry in payload["entries"]]
    assert names == ["b.txt", "c.txt"]
    assert payload["total"] == 3
    assert payload["has_more"] is False

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/files/?sort=size&order=desc"
        )

    assert response.status_code == 200
    payload = response.json()
    names = [entry["name"] for entry in payload["entries"]]
    assert names[0] == "c.txt"


def test_files_offset_beyond_total(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-561b"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()

    _write_file(run_root / "a.txt", "a")
    _write_file(run_root / "b.txt", "bb")

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/files/?limit=2&offset=10"
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["entries"] == []
    assert payload["total"] == 2
    assert payload["has_more"] is False


def test_files_has_more_boundary(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-561c"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()

    _write_file(run_root / "a.txt", "a")
    _write_file(run_root / "b.txt", "bb")
    _write_file(run_root / "c.txt", "ccc")

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/files/?limit=1&offset=0"
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["has_more"] is True

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/files/?limit=1&offset=2"
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["has_more"] is False


def test_files_empty_directory(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-561d"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()
    (run_root / "empty").mkdir()

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/files/empty/"
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["entries"] == []
    assert payload["total"] == 0
    assert payload["has_more"] is False


def test_files_sort_stability_matches_manifest(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-561a"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()

    data_dir = run_root / "data"
    data_dir.mkdir()
    _write_file(data_dir / "Alpha.txt", "x")
    _write_file(data_dir / "alpha.txt", "x")
    _write_file(data_dir / "beta.txt", "x")

    os.utime(data_dir / "Alpha.txt", (1, 1))
    os.utime(data_dir / "alpha.txt", (1, 1))
    os.utime(data_dir / "beta.txt", (1, 1))

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/files/data/?sort=size&order=desc"
        )

    assert response.status_code == 200
    payload = response.json()
    names_full = [entry["name"] for entry in payload["entries"]]
    assert names_full == ["Alpha.txt", "alpha.txt", "beta.txt"]

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/files/data/?limit=2&offset=1&sort=size&order=desc"
        )
    assert response.status_code == 200
    payload = response.json()
    names_offset = [entry["name"] for entry in payload["entries"]]
    assert names_offset == ["alpha.txt", "beta.txt"]

    browse.create_manifest(str(run_root))
    app = browse.create_app()
    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/files/data/?sort=size&order=desc"
        )

    assert response.status_code == 200
    payload = response.json()
    names_manifest = [entry["name"] for entry in payload["entries"]]
    assert names_manifest == names_full


def test_files_manifest_cached_flag(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-562"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()

    _write_file(run_root / "foo.txt", "hello")

    browse = load_browse(SITE_PREFIX="/weppcloud")
    browse.create_manifest(str(run_root))
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(f"/weppcloud/runs/{runid}/{config}/files/")

    assert response.status_code == 200
    payload = response.json()
    assert payload.get("cached") is True


def test_files_meta_skips_cached_flag(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-562a"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()

    _write_file(run_root / "foo.txt", "hello")

    browse = load_browse(SITE_PREFIX="/weppcloud")
    browse.create_manifest(str(run_root))
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/files/foo.txt?meta=true"
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload.get("cached") is None


def test_files_manifest_pattern_filtering(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-563"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()

    _write_file(run_root / "alpha.txt", "a")
    _write_file(run_root / "beta.txt", "b")
    _write_file(run_root / "alpha.log", "c")

    browse = load_browse(SITE_PREFIX="/weppcloud")
    browse.create_manifest(str(run_root))
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/files/?pattern=*.txt"
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload.get("cached") is True
    names = {entry["name"] for entry in payload["entries"]}
    assert names == {"alpha.txt", "beta.txt"}


def test_files_dotfiles_hidden_by_default(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-564"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()

    _write_file(run_root / ".secret", "hidden")
    _write_file(run_root / "alpha.txt", "a")

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(f"/weppcloud/runs/{runid}/{config}/files/")

    assert response.status_code == 200
    payload = response.json()
    names = {entry["name"] for entry in payload["entries"]}
    assert ".secret" not in names

    with TestClient(app) as client:
        response = client.get(f"/weppcloud/runs/{runid}/{config}/files/?include_hidden=1")

    assert response.status_code == 200
    payload = response.json()
    names = {entry["name"] for entry in payload["entries"]}
    assert ".secret" not in names

    browse.create_manifest(str(run_root))
    app = browse.create_app()
    with TestClient(app) as client:
        response = client.get(f"/weppcloud/runs/{runid}/{config}/files/")

    assert response.status_code == 200
    payload = response.json()
    names = {entry["name"] for entry in payload["entries"]}
    assert ".secret" not in names

    with TestClient(app) as client:
        response = client.get(f"/weppcloud/runs/{runid}/{config}/files/?include_hidden=1")

    assert response.status_code == 200
    payload = response.json()
    names = {entry["name"] for entry in payload["entries"]}
    assert ".secret" not in names


def test_browse_error_with_files_segment_stays_html(tmp_path: Path, monkeypatch, load_browse):
    runid = "run-111"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    run_root.mkdir()

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/browse/files/missing"
        )

    assert response.status_code == 404
    assert "text/html" in response.headers.get("content-type", "")
    assert "Directory Not Found" in response.text


def test_files_nodir_list_handles_listdir_file_not_found_as_404(
    tmp_path: Path,
    monkeypatch,
    load_browse,
):
    runid = "run-nodir-list-race"
    config = "disturbed9002_wbt"
    run_root = tmp_path / "run"
    (run_root / "landuse").mkdir(parents=True, exist_ok=True)

    browse = load_browse(SITE_PREFIX="/weppcloud")
    monkeypatch.setattr(browse, "get_wd", lambda _runid: str(run_root))

    import wepppy.microservices.browse.files_api as files_api_mod

    monkeypatch.setattr(
        files_api_mod,
        "nodir_listdir",
        lambda _target: (_ for _ in ()).throw(FileNotFoundError("gone")),
    )

    app = browse.create_app()
    with TestClient(app) as client:
        response = client.get(f"/weppcloud/runs/{runid}/{config}/files/landuse/")

    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "path_not_found"
