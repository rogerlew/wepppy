import importlib
import base64
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

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
        import wepppy.microservices.browse.browse as browse_mod

        browse_mod = importlib.reload(browse_mod)
        monkeypatch.setattr(browse_mod, "authorize_run_request", _allow_auth)
        monkeypatch.setattr(browse_mod, "authorize_group_request", _allow_auth)
        return browse_mod

    return _loader


def _write_file(path: Path, contents: str = "demo") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents)


def _encode_filter_payload(payload: dict) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


@pytest.fixture
def load_run_browse(monkeypatch, load_browse):
    def _loader(run_roots: dict[str, Path], **env):
        browse_mod = load_browse(**env)

        def _get_wd(runid: str, prefer_active: bool = False) -> str:
            root = run_roots.get(runid)
            if root is None:
                raise FileNotFoundError(runid)
            return str(root)

        monkeypatch.setattr(browse_mod, "get_wd", _get_wd)
        return browse_mod

    return _loader


def test_culvert_browse_root_lists_runs(tmp_path: Path, load_browse):
    culverts_root = tmp_path / "culverts"
    batch_uuid = "culvert-1234"
    _write_file(culverts_root / batch_uuid / "runs" / "1001" / "run_metadata.json", "{}")

    browse = load_browse(
        SITE_PREFIX="/weppcloud",
        CULVERTS_ROOT=str(culverts_root),
    )
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(f"/weppcloud/culverts/{batch_uuid}/browse/")

    assert response.status_code == 200
    body = response.text
    assert f'href="/weppcloud/culverts/{batch_uuid}/browse/"' in body
    assert f"/weppcloud/culverts/{batch_uuid}/browse/runs/" in body


def test_batch_browse_root_lists_runs(tmp_path: Path, load_browse):
    batch_root = tmp_path / "batch"
    batch_name = "batch-alpha"
    _write_file(batch_root / batch_name / "runs" / "_175" / "run_metadata.json", "{}")

    browse = load_browse(
        SITE_PREFIX="/weppcloud",
        BATCH_RUNNER_ROOT=str(batch_root),
    )
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(f"/weppcloud/batch/{batch_name}/browse/")

    assert response.status_code == 200
    body = response.text
    assert f'href="/weppcloud/batch/{batch_name}/browse/"' in body
    assert f"/weppcloud/batch/{batch_name}/browse/runs/" in body


def test_run_browse_raw_and_download_contracts(tmp_path: Path, load_run_browse):
    runid = "run-contracts"
    config = "cfg"
    run_root = tmp_path / runid
    _write_file(run_root / "secret.txt", "hello")

    browse = load_run_browse(
        {runid: run_root},
        SITE_PREFIX="/weppcloud",
    )
    app = browse.create_app()

    with TestClient(app) as client:
        raw_response = client.get(f"/weppcloud/runs/{runid}/{config}/browse/secret.txt?raw")
        download_response = client.get(f"/weppcloud/runs/{runid}/{config}/browse/secret.txt?download")

    assert raw_response.status_code == 200
    assert raw_response.text == "hello"
    assert raw_response.headers["content-type"].startswith("text/plain")

    assert download_response.status_code == 200
    content_disposition = download_response.headers.get("content-disposition", "")
    assert "attachment" in content_disposition
    assert "secret.txt" in content_disposition


def test_run_browse_repr_unknown_extension_returns_not_found(tmp_path: Path, load_run_browse):
    runid = "run-repr"
    config = "cfg"
    run_root = tmp_path / runid
    _write_file(run_root / "plain.txt", "no repr parser")

    browse = load_run_browse(
        {runid: run_root},
        SITE_PREFIX="/weppcloud",
    )
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(f"/weppcloud/runs/{runid}/{config}/browse/plain.txt?repr=1")

    assert response.status_code == 404


@pytest.mark.parametrize("page_value,expected_page", [("0", "1"), ("99", "1")])
def test_run_browse_page_clamp_preserves_diff_sort_order_query(
    tmp_path: Path,
    load_run_browse,
    page_value: str,
    expected_page: str,
):
    runid = "run-pagination"
    diff_runid = "run-pagination-diff"
    config = "cfg"
    run_root = tmp_path / runid
    diff_root = tmp_path / diff_runid
    _write_file(run_root / "alpha.txt", "1")
    _write_file(diff_root / "alpha.txt", "1")

    browse = load_run_browse(
        {
            runid: run_root,
            diff_runid: diff_root,
        },
        SITE_PREFIX="/weppcloud",
    )
    app = browse.create_app()
    query = f"page={page_value}&diff={diff_runid}&sort=size&order=desc"

    with TestClient(app) as client:
        response = client.get(
            f"/weppcloud/runs/{runid}/{config}/browse/?{query}",
            follow_redirects=False,
        )

    assert response.status_code == 302
    parsed = urlparse(response.headers["location"])
    assert parsed.path == f"/weppcloud/runs/{runid}/{config}/browse/"
    query_values = parse_qs(parsed.query)
    assert query_values["page"] == [expected_page]
    assert query_values["diff"] == [diff_runid]
    assert query_values["sort"] == ["size"]
    assert query_values["order"] == ["desc"]


def test_markdown_renderer_failure_falls_back_to_text_template(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    load_run_browse,
):
    runid = "run-markdown-fallback"
    config = "cfg"
    run_root = tmp_path / runid
    _write_file(run_root / "notes.md", "# Heading\n\nbody")

    browse = load_run_browse(
        {runid: run_root},
        SITE_PREFIX="/weppcloud",
    )
    monkeypatch.setattr(browse, "markdown_to_html", lambda text: (_ for _ in ()).throw(RuntimeError("boom")))
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(f"/weppcloud/runs/{runid}/{config}/browse/notes.md")

    assert response.status_code == 200
    assert "<article class=\"markdown-body\">" not in response.text
    assert "<pre>" in response.text
    assert "# Heading" in response.text


def test_parquet_preview_contains_case_insensitive_filter(tmp_path: Path, load_run_browse):
    runid = "run-parquet-filter-contains"
    config = "cfg"
    run_root = tmp_path / runid
    run_root.mkdir(parents=True, exist_ok=True)
    df = pytest.importorskip("pandas").DataFrame({"name": ["Alice", "bob"], "value": [1, 2]})
    df.to_parquet(run_root / "table.parquet")

    browse = load_run_browse(
        {runid: run_root},
        SITE_PREFIX="/weppcloud",
        BROWSE_PARQUET_FILTERS_ENABLED="1",
    )
    app = browse.create_app()

    pqf = _encode_filter_payload(
        {
            "kind": "condition",
            "field": "name",
            "operator": "Contains",
            "value": "AL",
        }
    )
    with TestClient(app) as client:
        response = client.get(f"/weppcloud/runs/{runid}/{config}/browse/table.parquet?pqf={pqf}")

    assert response.status_code == 200
    assert "Alice" in response.text
    assert "bob" not in response.text
    assert "Parquet filter active" in response.text


def test_parquet_preview_under_nodir_root_renders_html_table(tmp_path: Path, load_run_browse):
    runid = "run-parquet-filter-nodir-root"
    config = "cfg"
    run_root = tmp_path / runid
    parquet_dir = run_root / "watershed"
    parquet_dir.mkdir(parents=True, exist_ok=True)
    df = pytest.importorskip("pandas").DataFrame({"topaz_id": [23, 24], "value": [1, 2]})
    df.to_parquet(parquet_dir / "hillslopes.parquet")

    browse = load_run_browse(
        {runid: run_root},
        SITE_PREFIX="/weppcloud",
        BROWSE_PARQUET_FILTERS_ENABLED="1",
    )
    app = browse.create_app()

    pqf = _encode_filter_payload(
        {
            "kind": "condition",
            "field": "topaz_id",
            "operator": "Equals",
            "value": "23",
        }
    )
    with TestClient(app) as client:
        response = client.get(f"/weppcloud/runs/{runid}/{config}/browse/watershed/hillslopes.parquet?pqf={pqf}")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "content-disposition" not in response.headers
    assert "Parquet filter active" in response.text
    assert ">23<" in response.text
    assert ">24<" not in response.text


def test_parquet_preview_numeric_filter_rejects_text_field(tmp_path: Path, load_run_browse):
    runid = "run-parquet-filter-invalid"
    config = "cfg"
    run_root = tmp_path / runid
    run_root.mkdir(parents=True, exist_ok=True)
    df = pytest.importorskip("pandas").DataFrame({"name": ["Alice", "bob"], "value": [1, 2]})
    df.to_parquet(run_root / "table.parquet")

    browse = load_run_browse(
        {runid: run_root},
        SITE_PREFIX="/weppcloud",
        BROWSE_PARQUET_FILTERS_ENABLED="1",
    )
    app = browse.create_app()

    pqf = _encode_filter_payload(
        {
            "kind": "condition",
            "field": "name",
            "operator": "GreaterThan",
            "value": "1",
        }
    )
    with TestClient(app) as client:
        response = client.get(f"/weppcloud/runs/{runid}/{config}/browse/table.parquet?pqf={pqf}")

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"
    assert "numeric-only" in payload["error"]["details"]


def test_directory_includes_parquet_filter_builder_and_parquet_link_attrs(tmp_path: Path, load_run_browse):
    runid = "run-parquet-filter-ui"
    config = "cfg"
    run_root = tmp_path / runid
    _write_file(run_root / "notes.txt", "hello")
    df = pytest.importorskip("pandas").DataFrame({"name": ["A"], "value": [1]})
    df.to_parquet(run_root / "table.parquet")

    browse = load_run_browse(
        {runid: run_root},
        SITE_PREFIX="/weppcloud",
        BROWSE_PARQUET_FILTERS_ENABLED="1",
    )
    app = browse.create_app()

    pqf = _encode_filter_payload(
        {
            "kind": "condition",
            "field": "name",
            "operator": "Equals",
            "value": "A",
        }
    )
    with TestClient(app) as client:
        response = client.get(f"/weppcloud/runs/{runid}/{config}/browse/?pqf={pqf}")

    assert response.status_code == 200
    assert "parquet_filter_builder.js" in response.text
    assert 'data-parquet-link="1"' in response.text
    assert 'data-parquet-schema-link="1"' in response.text
    assert f"/weppcloud/runs/{runid}/{config}/schema/table.parquet" in response.text
    assert f"pqf={pqf}" in response.text


def test_parquet_schema_endpoint_returns_column_metadata(tmp_path: Path, load_run_browse):
    runid = "run-parquet-schema"
    config = "cfg"
    run_root = tmp_path / runid
    run_root.mkdir(parents=True, exist_ok=True)
    df = pytest.importorskip("pandas").DataFrame({"name": ["A"], "value": [1]})
    df.to_parquet(run_root / "table.parquet")

    browse = load_run_browse(
        {runid: run_root},
        SITE_PREFIX="/weppcloud",
    )
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(f"/weppcloud/runs/{runid}/{config}/schema/table.parquet")

    assert response.status_code == 200
    payload = response.json()
    assert payload["path"] == "table.parquet"
    assert [column["name"] for column in payload["columns"]] == ["name", "value"]
    assert all(column.get("type") for column in payload["columns"])


def test_parquet_schema_endpoint_rejects_non_parquet_paths(tmp_path: Path, load_run_browse):
    runid = "run-parquet-schema-invalid"
    config = "cfg"
    run_root = tmp_path / runid
    _write_file(run_root / "notes.txt", "hello")

    browse = load_run_browse(
        {runid: run_root},
        SITE_PREFIX="/weppcloud",
    )
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(f"/weppcloud/runs/{runid}/{config}/schema/notes.txt")

    assert response.status_code == 400
    assert "only available for parquet files" in response.text
