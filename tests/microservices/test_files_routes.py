import importlib
import os
from pathlib import Path

import pytest

TestClient = pytest.importorskip("starlette.testclient").TestClient

pytestmark = pytest.mark.microservice


@pytest.fixture
def load_browse(monkeypatch):
    def _loader(**env):
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        import wepppy.microservices.browse as browse_mod

        return importlib.reload(browse_mod)

    return _loader


def _write_file(path: Path, contents: str = "demo") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents)


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
def test_files_meta_allows_symlink(tmp_path: Path, monkeypatch, load_browse):
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

    assert response.status_code == 200
    payload = response.json()
    assert payload["type"] == "symlink"
    assert payload.get("symlink_is_dir") is True
    assert "symlink_target" not in payload


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


def test_files_dotfiles_consistent_with_manifest(tmp_path: Path, monkeypatch, load_browse):
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
    assert ".secret" in names

    browse.create_manifest(str(run_root))
    app = browse.create_app()
    with TestClient(app) as client:
        response = client.get(f"/weppcloud/runs/{runid}/{config}/files/")

    assert response.status_code == 200
    payload = response.json()
    names = {entry["name"] for entry in payload["entries"]}
    assert ".secret" in names


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
