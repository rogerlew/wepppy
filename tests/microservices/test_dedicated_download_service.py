import importlib
import uuid
from pathlib import Path

import pytest

from wepppy.weppcloud.utils import auth_tokens

TestClient = pytest.importorskip("starlette.testclient").TestClient

pytestmark = pytest.mark.microservice


@pytest.fixture
def load_download(monkeypatch):
    def _loader(run_roots: dict[str, Path], **env):
        monkeypatch.setenv("WEPP_AUTH_JWT_SECRET", "download-auth-secret")
        auth_tokens.get_jwt_config.cache_clear()
        for key, value in env.items():
            monkeypatch.setenv(key, value)

        import wepppy.microservices.browse.auth as auth_mod

        auth_mod = importlib.reload(auth_mod)
        download_mod = importlib.import_module("wepppy.microservices.download.app")
        download_mod = importlib.reload(download_mod)

        def _get_wd(runid: str, prefer_active: bool = False) -> str:
            root = run_roots.get(runid)
            if root is None:
                raise FileNotFoundError(runid)
            return str(root)

        monkeypatch.setattr(auth_mod, "get_wd", _get_wd)
        monkeypatch.setattr(download_mod, "get_wd", _get_wd)
        monkeypatch.setattr(auth_mod, "_check_revocation", lambda _jti: None)
        return download_mod

    return _loader


def _write_archive(run_root: Path, relpath: str = "archives/result.zip", payload: bytes = b"0123456789") -> Path:
    archive = run_root / relpath
    archive.parent.mkdir(parents=True, exist_ok=True)
    archive.write_bytes(payload)
    return archive


def _make_public(run_root: Path) -> None:
    run_root.mkdir(parents=True, exist_ok=True)
    (run_root / "PUBLIC").write_text("")


def _issue_service_token(runid: str, *, roles: list[str] | None = None) -> str:
    payload = auth_tokens.issue_token(
        "download-test",
        scopes=["rq:status"],
        audience="rq-engine",
        runs=[runid],
        extra_claims={
            "token_class": "service",
            "roles": roles or ["User"],
            "jti": uuid.uuid4().hex,
        },
    )
    return payload["token"]


def test_public_archive_full_get_serves_zip_with_download_headers(
    tmp_path: Path,
    load_download,
) -> None:
    runid = "run-public-archive"
    config = "cfg"
    run_root = tmp_path / runid
    _make_public(run_root)
    _write_archive(run_root, payload=b"zip-bytes")
    download_mod = load_download({runid: run_root}, SITE_PREFIX="/weppcloud")

    with TestClient(download_mod.create_app()) as client:
        response = client.get(f"/weppcloud/runs/{runid}/{config}/download/archives/result.zip")

    assert response.status_code == 200
    assert response.content == b"zip-bytes"
    assert response.headers["accept-ranges"] == "bytes"
    assert response.headers["content-length"] == "9"
    assert 'filename="result.zip"' in response.headers["content-disposition"]
    assert response.headers["x-request-id"]


def test_public_archive_head_returns_metadata_without_body(
    tmp_path: Path,
    load_download,
) -> None:
    runid = "run-public-head"
    config = "cfg"
    run_root = tmp_path / runid
    _make_public(run_root)
    _write_archive(run_root, payload=b"0123456789")
    download_mod = load_download({runid: run_root}, SITE_PREFIX="/weppcloud")

    with TestClient(download_mod.create_app()) as client:
        response = client.head(f"/weppcloud/runs/{runid}/{config}/download/archives/result.zip")

    assert response.status_code == 200
    assert response.content == b""
    assert response.headers["accept-ranges"] == "bytes"
    assert response.headers["content-length"] == "10"
    assert "content-range" not in response.headers


@pytest.mark.parametrize(
    ("range_header", "expected_body", "expected_content_range"),
    [
        ("bytes=2-5", b"2345", "bytes 2-5/10"),
        ("bytes=7-", b"789", "bytes 7-9/10"),
        ("bytes=-4", b"6789", "bytes 6-9/10"),
    ],
)
def test_archive_range_requests_return_partial_content(
    tmp_path: Path,
    load_download,
    range_header: str,
    expected_body: bytes,
    expected_content_range: str,
) -> None:
    runid = "run-public-range"
    config = "cfg"
    run_root = tmp_path / runid
    _make_public(run_root)
    _write_archive(run_root)
    download_mod = load_download({runid: run_root}, SITE_PREFIX="/weppcloud")

    with TestClient(download_mod.create_app()) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/download/archives/result.zip",
            headers={"Range": range_header},
        )

    assert response.status_code == 206
    assert response.content == expected_body
    assert response.headers["accept-ranges"] == "bytes"
    assert response.headers["content-range"] == expected_content_range
    assert response.headers["content-length"] == str(len(expected_body))


def test_archive_invalid_range_returns_416(
    tmp_path: Path,
    load_download,
) -> None:
    runid = "run-public-invalid-range"
    config = "cfg"
    run_root = tmp_path / runid
    _make_public(run_root)
    _write_archive(run_root)
    download_mod = load_download({runid: run_root}, SITE_PREFIX="/weppcloud")

    with TestClient(download_mod.create_app()) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/download/archives/result.zip",
            headers={"Range": "bytes=20-30"},
        )

    assert response.status_code == 416
    assert response.headers["accept-ranges"] == "bytes"
    assert response.headers["content-range"] == "bytes */10"


def test_private_archive_redirects_only_for_navigation(
    tmp_path: Path,
    load_download,
) -> None:
    runid = "run-private-archive"
    config = "cfg"
    run_root = tmp_path / runid
    _write_archive(run_root)
    download_mod = load_download({runid: run_root}, SITE_PREFIX="/weppcloud")

    with TestClient(download_mod.create_app()) as client:
        html_response = client.get(
            f"/weppcloud/runs/{runid}/{config}/download/archives/result.zip",
            headers={"Accept": "text/html"},
            follow_redirects=False,
        )
        api_response = client.get(
            f"/weppcloud/runs/{runid}/{config}/download/archives/result.zip",
            headers={"Accept": "application/octet-stream"},
            follow_redirects=False,
        )

    assert html_response.status_code == 302
    assert api_response.status_code == 401


def test_private_archive_accepts_bearer_token(
    tmp_path: Path,
    load_download,
) -> None:
    runid = "run-private-token"
    config = "cfg"
    run_root = tmp_path / runid
    _write_archive(run_root, payload=b"private-zip")
    download_mod = load_download({runid: run_root}, SITE_PREFIX="/weppcloud")
    token = _issue_service_token(runid)

    with TestClient(download_mod.create_app()) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/download/archives/result.zip",
            headers={"Authorization": f"Bearer {token}"},
            follow_redirects=False,
        )

    assert response.status_code == 200
    assert response.content == b"private-zip"


@pytest.mark.parametrize(
    "subpath",
    [
        "%2e%2e/secret.zip",
        "nested/%2e%2e/result.zip",
        ".hidden.zip",
        "nested//result.zip",
        "readme.txt",
    ],
)
def test_archive_service_rejects_paths_outside_exact_archive_contract(
    tmp_path: Path,
    load_download,
    subpath: str,
) -> None:
    runid = "run-path-safety"
    config = "cfg"
    run_root = tmp_path / runid
    _make_public(run_root)
    _write_archive(run_root)
    (run_root / "secret.zip").write_bytes(b"secret")
    download_mod = load_download({runid: run_root}, SITE_PREFIX="/weppcloud")

    with TestClient(download_mod.create_app()) as client:
        response = client.get(f"/weppcloud/runs/{runid}/{config}/download/archives/{subpath}")

    assert response.status_code in {403, 404}


def test_archive_download_logs_range_completion_without_full_path_or_token(
    tmp_path: Path,
    load_download,
    caplog: pytest.LogCaptureFixture,
) -> None:
    runid = "run-log-archive"
    config = "cfg"
    run_root = tmp_path / runid
    _make_public(run_root)
    _write_archive(run_root)
    download_mod = load_download({runid: run_root}, SITE_PREFIX="/weppcloud")
    caplog.set_level("INFO", logger="wepppy.microservices.download.app")

    with TestClient(download_mod.create_app()) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/download/archives/result.zip",
            headers={"Range": "bytes=2-5", "User-Agent": "pytest-download"},
        )

    assert response.status_code == 206
    messages = "\n".join(record.getMessage() for record in caplog.records)
    assert "download.complete" in messages
    assert "route_family=run_archive" in messages
    assert "path_category=archives" in messages
    assert "basename=result.zip" in messages
    assert "range_start=2" in messages
    assert "range_end=5" in messages
    assert "bytes_sent=4" in messages
    assert "pytest-download" in messages
    assert str(run_root) not in messages
    assert "Authorization" not in messages
