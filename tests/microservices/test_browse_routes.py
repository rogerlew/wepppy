import importlib
import base64
import json
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlparse

import pytest

TestClient = pytest.importorskip("starlette.testclient").TestClient

pytestmark = pytest.mark.microservice
REPO_ROOT = Path(__file__).resolve().parents[2]


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


def test_run_browse_directory_tree_uses_theme_assets_and_preserves_default_row_colors(
    tmp_path: Path,
    load_run_browse,
):
    runid = "run-tree-theme"
    config = "cfg"
    run_root = tmp_path / runid
    _write_file(run_root / "alpha.txt", "a")
    _write_file(run_root / "bravo.txt", "b")

    browse = load_run_browse(
        {runid: run_root},
        SITE_PREFIX="/weppcloud",
    )
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(f"/weppcloud/runs/{runid}/{config}/browse/")

    assert response.status_code == 200
    body = response.text
    assert 'class="wc-browse-tree-page"' in body
    assert 'id="file-tree" class="wc-browse-tree"' in body
    assert "css/ui-foundation.css" in body
    assert "css/themes/all-themes.css" in body
    assert "js/theme.js" in body
    assert "odd-row" in body
    assert "even-row" in body

    foundation_css = (REPO_ROOT / "wepppy" / "weppcloud" / "static" / "css" / "ui-foundation.css").read_text(
        encoding="utf-8"
    )
    assert "--wc-browse-tree-row-odd-bg: #ffffff;" in foundation_css
    assert "--wc-browse-tree-row-even-bg: #f6f6f6;" in foundation_css
    assert "--wc-browse-tree-row-hover-bg: #d0ebff;" in foundation_css
    assert ":root[data-theme]" in foundation_css
    assert "--wc-browse-tree-row-even-bg: color-mix(in srgb, var(--wc-color-surface-alt) 90%, var(--wc-color-border));" in foundation_css
    assert "--wc-browse-tree-row-hover-bg: color-mix(in srgb, var(--wc-color-surface-alt) 68%, var(--wc-color-border));" in foundation_css


def test_run_browse_not_found_tree_uses_theme_assets(tmp_path: Path, load_run_browse):
    runid = "run-tree-not-found"
    config = "cfg"
    run_root = tmp_path / runid
    run_root.mkdir(parents=True, exist_ok=True)

    browse = load_run_browse(
        {runid: run_root},
        SITE_PREFIX="/weppcloud",
    )
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(f"/weppcloud/runs/{runid}/{config}/browse/missing/")

    assert response.status_code == 404
    body = response.text
    assert 'class="wc-browse-tree-page"' in body
    assert 'class="wc-browse-tree"' in body
    assert "css/ui-foundation.css" in body
    assert "css/themes/all-themes.css" in body
    assert "js/theme.js" in body
    assert "wc-browse-tree-error" in body
    assert "<code>missing/</code>" in body


def test_parquet_preview_fixed_header_warns_preview_is_limited(tmp_path: Path, load_run_browse):
    runid = "run-parquet-preview-banner"
    config = "cfg"
    run_root = tmp_path / runid
    run_root.mkdir(parents=True, exist_ok=True)
    df = pytest.importorskip("pandas").DataFrame(
        {"name": ["first", "second", "third"], "value": [1, 2, 3]}
    )
    df.to_parquet(run_root / "table.parquet")

    browse = load_run_browse(
        {runid: run_root},
        SITE_PREFIX="/weppcloud",
        BROWSE_PARQUET_PREVIEW_LIMIT="2",
    )
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(f"/weppcloud/runs/{runid}/{config}/browse/table.parquet")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert 'class="wc-browse-table-page has-fixed-preview-banner"' in response.text
    assert "data-parquet-preview-banner" in response.text
    assert "css/ui-foundation.css" in response.text
    assert "css/themes/all-themes.css" in response.text
    assert "js/theme.js" in response.text
    assert "Preview Only" in response.text
    assert "HTML preview only; this is not the full parquet file." in response.text
    assert "Showing first 2 of 3 rows" in response.text
    assert "Download Full File" in response.text
    assert "Download Full CSV" in response.text
    assert "first" in response.text
    assert "second" in response.text
    assert "third" not in response.text


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


def test_nodir_markdown_file_uses_markdown_template(tmp_path: Path, load_run_browse):
    runid = "run-nodir-markdown"
    config = "cfg"
    run_root = tmp_path / runid
    _write_file(run_root / "watershed" / "README.md", "# Heading\n\nbody")

    browse = load_run_browse(
        {runid: run_root},
        SITE_PREFIX="/weppcloud",
    )
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(f"/weppcloud/runs/{runid}/{config}/browse/watershed/README.md")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "<article class=\"markdown-body\">" in response.text
    assert "<h1>Heading</h1>" in response.text


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
    assert response.text.count("data-parquet-filter-feedback") == 1
    banner = response.text.split("</header>", 1)[0]
    assert "data-parquet-filter-feedback" in banner
    assert "Parquet filter active" in banner
    body_after_banner = response.text.split("</header>", 1)[1]
    assert "filter-feedback" not in body_after_banner


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
    assert response.text.count("data-parquet-filter-feedback") == 1
    banner = response.text.split("</header>", 1)[0]
    assert "data-parquet-filter-feedback" in banner
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
    assert 'class="wc-browse-tree-filter-builder"' in response.text
    assert 'data-parquet-link="1"' in response.text
    assert 'data-parquet-schema-link="1"' in response.text
    assert f"/weppcloud/runs/{runid}/{config}/schema/table.parquet" in response.text
    assert f"pqf={pqf}" in response.text

    builder_js = (
        REPO_ROOT / "wepppy" / "weppcloud" / "static" / "js" / "parquet_filter_builder.js"
    ).read_text(encoding="utf-8")
    assert '"parquet-filter-builder pure-form"' in builder_js
    assert "wc-field__control parquet-filter-builder__input" in builder_js
    assert "wc-field__control parquet-filter-builder__select" in builder_js
    assert ".style." not in builder_js
    assert "#fafafa" not in builder_js
    assert "#1d6fdc" not in builder_js
    assert "#555" not in builder_js

    foundation_css = (REPO_ROOT / "wepppy" / "weppcloud" / "static" / "css" / "ui-foundation.css").read_text(
        encoding="utf-8"
    )
    assert ".parquet-filter-builder {" in foundation_css
    assert "background: var(--wc-color-surface);" in foundation_css
    assert "color: var(--wc-color-text);" in foundation_css
    assert "border: 1px solid var(--wc-color-border);" in foundation_css
    assert ".wc-browse-tree-filter-builder > details" in foundation_css
    assert ".wc-browse-tree-filter-builder button:not(.pure-button)" in foundation_css


@pytest.mark.parametrize("extension", [".parquet", ".geoparquet"])
def test_parquet_schema_endpoint_returns_column_metadata(tmp_path: Path, load_run_browse, extension: str):
    runid = "run-parquet-schema"
    config = "cfg"
    run_root = tmp_path / runid
    run_root.mkdir(parents=True, exist_ok=True)
    df = pytest.importorskip("pandas").DataFrame({"name": ["A"], "value": [1]})
    file_name = f"table{extension}"
    df.to_parquet(run_root / file_name)

    browse = load_run_browse(
        {runid: run_root},
        SITE_PREFIX="/weppcloud",
    )
    app = browse.create_app()

    with TestClient(app) as client:
        response = client.get(f"/weppcloud/runs/{runid}/{config}/schema/{file_name}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["path"] == file_name
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


def test_retired_and_failed_revegetation_inputs_remain_browsable(tmp_path, load_run_browse):
    from wepppy.nodb.mods.rap.revegetation_inputs import cover_output, publish_revegetation_input

    root = tmp_path / 'revegetation-evidence'
    runs = root / 'wepp' / 'runs'
    runs.mkdir(parents=True)
    (runs / 'firedate.txt').write_text('6 1 2005\n')
    publish_revegetation_input(str(runs), 'firedate.txt', None)
    with pytest.raises(RuntimeError, match='interrupted'):
        with cover_output(str(runs), 'p2.cov') as stream:
            stream.write('2000 2001\n')
            raise RuntimeError('interrupted')
    retired = next(runs.glob('revegetation-input-*/firedate.txt'))
    failed = next(runs.glob('p2.cov.revegetation-*.tmp'))
    browse = load_run_browse({'revegetation-evidence': root}, SITE_PREFIX='/weppcloud')
    base = '/weppcloud/runs/revegetation-evidence/cfg/browse/'
    with TestClient(browse.create_app()) as client:
        listing = client.get(base + 'wepp/runs/')
        assert listing.status_code == 200
        assert retired.parent.name in listing.text
        assert failed.name in listing.text
        for path in (retired, failed):
            response = client.get(base + str(path.relative_to(root)) + '?download')
            assert response.status_code == 200
            assert response.content == path.read_bytes()
            assert 'attachment' in response.headers['content-disposition']


@pytest.mark.parametrize("suffix", [".pkl", ".pickle", ".PkL", ".PiCkLe"])
@pytest.mark.parametrize("mode", ["", "?repr=1"])
def test_pickle_preview_rejected(tmp_path, load_run_browse, monkeypatch, suffix, mode):
    from unittest.mock import Mock

    root = tmp_path / "run"
    root.mkdir()
    name = f"legacy{suffix}"
    (root / name).write_bytes(b"N.")
    browse = load_run_browse({"pickle-test": root}, SITE_PREFIX="/weppcloud")
    reader = Mock(side_effect=AssertionError("pickle reader reached"))
    monkeypatch.setattr(browse.pd, "read_pickle", reader)
    with TestClient(browse.create_app()) as client:
        response = client.get(f"/weppcloud/runs/pickle-test/cfg/browse/{name}{mode}")
        listing = client.get("/weppcloud/runs/pickle-test/cfg/browse/")
    assert response.status_code == 415
    reader.assert_not_called()
    assert listing.status_code == 200
    assert name in listing.text
    assert f"/dtale/{name}" not in listing.text


# Inert corpus: no script execution, only structural HTML assertions.
_OUTPUT_NAME = 'name & <x-probe data-extra="yes">\' #?% café ∕＼'


class _BrowseHTML(HTMLParser):
    def __init__(self, body):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.text = []
        self.feed(body)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def handle_data(self, data):
        self.text.append(data)

    def links(self):
        return [attrs for tag, attrs in self.tags if tag == 'a']

    def assert_inert(self):
        assert not any(tag == 'x-probe' for tag, _ in self.tags)
        assert not any('data-extra' in attrs for _, attrs in self.tags)


def _output_client(load_run_browse, root, monkeypatch, **env):
    browse = load_run_browse({'output-safe': root, 'comparison': root}, SITE_PREFIX='/weppcloud', **env)
    from types import SimpleNamespace
    from wepppy.microservices.browse import _download

    monkeypatch.setattr(_download, 'authorize_run_request', browse.authorize_run_request)
    monkeypatch.setattr(_download, '_resolve_run_context', lambda *args: SimpleNamespace(active_root=root))
    return TestClient(browse.create_app())


_OUTPUT_BASE = '/weppcloud/runs/output-safe/cfg/browse/'


def test_browse_listing_escapes_filename_and_encodes_entry_links(tmp_path, load_run_browse, monkeypatch):
    from urllib.parse import quote

    names = ['ordinary.txt', '日本語.txt', _OUTPUT_NAME + '.txt']
    for name in names:
        _write_file(tmp_path / name, name)
    with _output_client(load_run_browse, tmp_path, monkeypatch) as client:
        response = client.get(_OUTPUT_BASE)
        assert response.status_code == 200
        parsed = _BrowseHTML(response.text)
        parsed.assert_inert()
        for name in names:
            assert name in ''.join(parsed.text)
            for route in ('browse', 'download'):
                href = _OUTPUT_BASE.replace('/browse/', f'/{route}/') + quote(name, safe='')
                assert any(a.get('href') == href for a in parsed.links())
                delivered = client.get(href, params={'raw': '1'})
                assert delivered.status_code == 200
                assert delivered.text == name


def test_browse_directory_breadcrumb_escapes_and_encodes_stored_name(tmp_path, load_run_browse, monkeypatch):
    from urllib.parse import quote

    directory = tmp_path / _OUTPUT_NAME
    (directory / 'child').mkdir(parents=True)
    _write_file(directory / 'literal%23.txt', 'nested')
    href = _OUTPUT_BASE + quote(_OUTPUT_NAME, safe='') + '/'
    with _output_client(load_run_browse, tmp_path, monkeypatch) as client:
        parent = _BrowseHTML(client.get(_OUTPUT_BASE).text)
        parent.assert_inert()
        assert any(a.get('href') == href for a in parent.links())
        nested = client.get(href)
        assert nested.status_code == 200
        parsed = _BrowseHTML(nested.text)
        parsed.assert_inert()
        file_href = href + 'literal%2523.txt'
        assert any(a.get('href') == file_href for a in parsed.links()), parsed.links()
        # Starlette TestClient unquotes HTTPX's already decoded path again.
        # ASGITransport preserves a literal percent escape as a filename.
        import asyncio
        import httpx

        async def read_literal_percent_name():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=client.app), base_url='http://testserver'
            ) as direct:
                delivered = await direct.get(file_href, params={'raw': '1'})
                assert delivered.status_code == 200
                assert delivered.text == 'nested'

        asyncio.run(read_literal_percent_name())
        child = client.get(href + 'child/')
        assert child.status_code == 200
        parsed = _BrowseHTML(child.text)
        parsed.assert_inert()
        assert _OUTPUT_NAME in ''.join(parsed.text)
        assert any(a.get('href') == href for a in parsed.links())
        assert any(a.get('data-copy-path') == str(directory) for _, a in parsed.tags)
        # Empty child retains the normal empty-state presentation.
        assert 'No items to display' in child.text


def test_browse_listing_escapes_symlink_target_text(tmp_path, load_run_browse, monkeypatch):
    import os

    if not hasattr(os, 'symlink'):
        pytest.skip('symlink unavailable')
    _write_file(tmp_path / _OUTPUT_NAME, 'target bytes')
    (tmp_path / 'link.txt').symlink_to(_OUTPUT_NAME)
    with _output_client(load_run_browse, tmp_path, monkeypatch) as client:
        response = client.get(_OUTPUT_BASE)
        assert response.status_code == 200
        parsed = _BrowseHTML(response.text)
        parsed.assert_inert()
        assert '->' + _OUTPUT_NAME in ''.join(parsed.text)
        assert client.get(_OUTPUT_BASE + 'link.txt', params={'raw': '1'}).text == 'target bytes'


@pytest.mark.parametrize('suffix, actions', [
    ('.parquet', {'browse', 'download', 'dtale', 'schema'}),
    ('.tif', {'browse', 'download', 'gdalinfo'}),
    ('.sol', {'browse', 'download', 'diff'}),
    ('.csv', {'browse', 'download', 'dtale', 'diff'}),
])
def test_browse_action_links_encode_filename_and_preserve_query(tmp_path, load_run_browse, monkeypatch, suffix, actions):
    from urllib.parse import quote

    name = _OUTPUT_NAME + suffix
    if suffix == '.parquet':
        pytest.importorskip('pandas').DataFrame({'value': [1]}).to_parquet(tmp_path / name)
    else:
        _write_file(tmp_path / name)
    pqf = _encode_filter_payload({'kind': 'condition', 'field': 'value', 'operator': 'Equals', 'value': 1})
    with _output_client(load_run_browse, tmp_path, monkeypatch, BROWSE_PARQUET_FILTERS_ENABLED='1') as client:
        response = client.get(_OUTPUT_BASE, params={'diff': 'comparison', 'pqf': pqf})
        assert response.status_code == 200
        parsed = _BrowseHTML(response.text)
        parsed.assert_inert()
        entry_links = [a for a in parsed.links() if quote(name, safe='') in a.get('href', '')]
        assert {urlparse(a['href']).path.split('/')[5] for a in entry_links} == actions
        for a in entry_links:
            url = urlparse(a['href'])
            assert url.path.endswith('/' + quote(name, safe=''))
            assert not url.fragment and not url.netloc
            query = parse_qs(url.query)
            if '/diff/' in url.path:
                assert query['diff'] == ['comparison']
            if suffix == '.parquet' and '/schema/' not in url.path:
                assert query['pqf'] == [pqf]
            if 'data-schema-url' in a:
                assert a['data-schema-url'] == a['href']
                assert client.get(a['href']).status_code == 200
        if suffix == '.parquet':
            assert any(parse_qs(urlparse(a['href']).query).get('as_csv') == ['1'] for a in entry_links)
        if suffix == '.sol':
            assert any(parse_qs(urlparse(a['href']).query).get('repr') == ['1'] for a in entry_links)


def test_browse_not_found_breadcrumb_escapes_reflected_path(tmp_path, load_run_browse, monkeypatch):
    from urllib.parse import quote

    (tmp_path / _OUTPUT_NAME).mkdir()
    with _output_client(load_run_browse, tmp_path, monkeypatch) as client:
        response = client.get(_OUTPUT_BASE + quote(_OUTPUT_NAME, safe='') + '/missing/', params={'diff': 'other&"value'})
        assert response.status_code == 404
        parsed = _BrowseHTML(response.text)
        parsed.assert_inert()
        assert _OUTPUT_NAME in ''.join(parsed.text)
        href = _OUTPUT_BASE + quote(_OUTPUT_NAME, safe='') + '/'
        links = [a['href'] for a in parsed.links() if a.get('href', '').startswith(href)]
        assert len(links) == 1
        assert parse_qs(urlparse(links[0]).query) == {'diff': ['other&"value']}
