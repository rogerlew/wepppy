from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from bs4 import BeautifulSoup
from flask import Flask, url_for
import pytest

from wepppy.weppcloud.routes import weppcloud_site

pytestmark = [pytest.mark.routes, pytest.mark.unit]


@pytest.fixture()
def preview(tmp_path, monkeypatch):
    web_root = Path(weppcloud_site.__file__).resolve().parents[1]
    app = Flask(__name__, template_folder=web_root / "templates", static_folder=web_root / "static")
    app.config.update(TESTING=True, WEPP_ACCESS_LOG_PATH=tmp_path / "access.csv")
    app.register_blueprint(weppcloud_site.weppcloud_site_bp)
    user = SimpleNamespace(is_authenticated=False, email="private@example.test")
    monkeypatch.setattr(weppcloud_site, "current_user", user)
    app.jinja_env.globals.update(
        static_url=lambda filename: url_for("static", filename=filename),
        current_user=user,
    )
    for endpoint, path in {
        "usersum.usersum_index": "/usersum/",
        "usersum.view_doc": "/usersum/doc/<doc_id>",
        "usersum.view_markdown": "/usersum/view/<category>/<path:filename>",
        "user.runs": "/runs",
        "security.login": "/login",
    }.items():
        app.add_url_rule(path, endpoint, lambda **kwargs: "")

    return app.test_client(), tmp_path / "runid-locations.json", user


def _get(client, route="/landing/preview/"):
    response = client.get(route, environ_overrides={"SCRIPT_NAME": "/weppcloud"})
    assert response.status_code == 200, response.text
    return response, BeautifulSoup(response.text, "html.parser")


def test_preview_renders_semantic_content_and_auth_links(preview):
    client, _, user = preview
    response, page = _get(client)
    assert response.headers["Cache-Control"] == "no-store, max-age=0"
    assert response.headers["X-Robots-Tag"] == "noindex"
    assert not page.select('script[src*="ui-lab"]')
    assert page.select_one('link[href="/weppcloud/static/css/landing.css"]')
    assert page.select_one("a[href='#main-content']")
    assert page.select_one("main #main-content").get("tabindex") == "-1"
    assert len(page.select("h1")) == 1
    assert page.select_one("[data-theme-select]")
    assert page.select_one('nav[aria-label="Primary"] a[href="/weppcloud/login"]')
    assert page.select_one('a[href="/weppcloud/usersum/doc/usersum.weppcloud.references"]')
    assert page.select_one('a[href="/weppcloud/usersum/view/weppcloud/accessibility-statement.md"]')
    assert page.select_one('a[href="mailto:Jackson.Nakae@usda.gov"]')
    assert page.select_one("[data-forest-service-credit]")
    assert page.select_one('span[lang="cy"]').text == "Gweddw Crefft Heb Ei Dawn"
    assert "22-IA-11261975-090" in page.get_text()
    assert "simulation outputs are estimates" in page.get_text()
    assert "Run Atlas data is temporarily unavailable." in page.get_text()

    user.is_authenticated = True
    response, page = _get(client)
    assert page.select_one('nav[aria-label="Primary"] a[href="/weppcloud/runs"]').text == "My Runs"
    assert 'href="/weppcloud/login"' not in response.text
    assert user.email not in response.text


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (b"[]", "No projects with recorded locations"),
        (b"\xff", "Run Atlas data is temporarily unavailable"),
        (b'{"runid": "wrong-shape"}', "Run Atlas data is temporarily unavailable"),
        (b"[null]", "Run Atlas data is temporarily unavailable"),
        (b"[", "Run Atlas data is temporarily unavailable"),
        (b"[" * 2000 + b"]" * 2000, "Run Atlas data is temporarily unavailable"),
    ],
)
def test_preview_handles_snapshot_failure_or_empty_state(preview, payload, message):
    client, path, _ = preview
    path.write_bytes(payload)

    _, page = _get(client)

    assert message in page.get_text()
    assert not page.select_one("#atlas-year")
    assert page.select_one("#resources")


def test_preview_reads_and_filters_public_atlas(preview):
    client, path, _ = preview
    rows = [
        {
            "runid": f"run-{day}",
            "run_name": f"<script>{day}</script>",
            "coordinates": [-116.16, 46.5],
            "year": 2026,
            "config": "<b>config</b>",
            "has_sbs": True,
            "hillslopes": "4",
            "access_count": day,
            "last_accessed": f"2026-01-{day:02d}T14:30:00",
            "unexpected_private_field": "private preview field",
        }
        for day in range(1, 27)
    ]
    rows += [{"runid": "older", "coordinates": [-12, 6], "year": 2025}, {"runid": "bad"}]
    path.write_text(json.dumps(rows), encoding="utf-8")

    response, page = _get(client, "/landing/preview/?year=2026")
    assert page.select_one("#atlas-year option[selected]").text == "2026"
    assert page.select_one("form").get("action") == "/weppcloud/landing/preview/#atlas-results"
    assert page.select_one("#atlas-results").text == "Atlas results for 2026"
    count, hillslopes, latest = page.select(".wc-landing__metrics dd")
    assert count.get_text(strip=True) == "27"
    assert hillslopes.get_text(strip=True) == "104"
    assert latest.time["datetime"] == "2026-01-26T14:30:00+00:00"
    assert "26 runs ·" in page.get_text()
    assert "104 recorded hillslopes" in page.get_text()
    project_rows = page.select("tbody tr")
    assert len(project_rows) == 25
    assert "<script>26</script>" in project_rows[0].get_text()
    assert "<b>config</b>" in project_rows[0].get_text()
    assert project_rows[0].select_one("script,b,a") is None
    assert "-116.16" in project_rows[0].get_text()
    assert "private preview field" not in response.text
    assert "older" not in response.text
    assert page.select_one("a[href$='#atlas-results']").get("href") == (
        "/weppcloud/landing/preview/?year=2026&page=2#atlas-results"
    )

    _, page = _get(client, "/landing/preview/?year=2026&page=2")
    assert len(page.select("tbody tr")) == 1
    assert "run-1" in page.select_one("tbody").get_text()
    assert "Previous page" in page.get_text()

    _, page = _get(client, "/landing/preview/?year=unknown&page=999999999999999999999")
    assert page.select_one("#atlas-results").text == "Atlas results"
    assert "Page 1 of 2" in page.get_text()

    _, page = _get(client, "/landing/preview/?year=2025")
    assert "older" in page.select_one("tbody").get_text()
    assert "Unknown" in page.select_one("tbody").get_text()
