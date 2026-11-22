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
        notification_inbox_available=True,
    )
    for endpoint, path in {
        "usersum.usersum_index": "/usersum/",
        "usersum.view_doc": "/usersum/doc/<doc_id>",
        "usersum.view_markdown": "/usersum/view/<category>/<path:filename>",
        "user.runs": "/runs",
        "security.login": "/login",
        "notifications.index": "/notifications/",
        "notifications.unread_count": "/notifications/unread-count",
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
    hero = page.select_one("#hero")
    assert hero.select_one("h1").text == "WEPPcloud"
    assert hero.select_one("h1 + p").text == "Water Erosion Prediction Project"
    assert hero.select_one("h2").text == "Data-driven watershed hydrology and erosion modeling to support decision-making."
    assert not hero.select("a, button, img")
    assert [section.get("aria-labelledby") for section in page.select(".wc-landing > section")] == [
        "landing-title", "about-heading", "atlas-heading", "resources-heading",
        "contacts-heading", "collaborators-heading", "sponsors-heading",
        "contributors-heading", "attributions-heading", "disclaimer-heading",
    ]
    assert page.select_one("[data-theme-select]")
    assert page.select_one('nav[aria-label="Primary"] a[href="/weppcloud/login"]')
    assert page.select_one('a[href="/weppcloud/usersum/doc/usersum.weppcloud.references"]')
    assert page.select_one('a[href="/weppcloud/usersum/view/weppcloud/accessibility-statement.md"]')
    assert page.select_one('a[href="mailto:Jackson.Nakae@usda.gov"]')
    assert page.select_one("[data-forest-service-credit]")
    assert page.select_one('a[href="https://www.swansea.ac.uk/"]').get_text(strip=True) == "Swansea University"
    assert "Jim Frankenberger" in page.get_text()
    header = page.select_one("header.wc-header > .wc-header__inner.wc-container")
    assert header.select_one(".wc-brand").get_text(strip=True) == "WEPPcloud"
    assert not header.select_one(".wc-brand img, [data-notification-bell]")
    assert header.select_one(".wc-nav__link[href='/weppcloud/login']")
    assert header.select_one(".wc-header__tools [data-theme-select]")
    assert header.select_one("details summary").get_text(strip=True) == "Menu"
    for group in header.select(".wc-landing__desktop-links, .wc-landing__mobile-links"):
        assert [link.text for link in group.select("a.wc-nav__link")] == [
            "Interfaces", "Docs", "Research", "Login",
        ]
    assert "22-IA-11261975-090" in page.get_text()
    assert "simulation outputs are estimates" in page.get_text()
    assert "Run Atlas data is temporarily unavailable." in page.get_text()

    user.is_authenticated = True
    response, page = _get(client)
    assert page.select_one('.wc-header__tools [data-notification-bell]')
    assert page.select_one('.wc-nav__link[href="/weppcloud/runs"]').text == "My Runs"
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


def test_preview_maps_the_full_public_atlas_without_year_controls(preview):
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

    response, page = _get(client, "/landing/preview/?year=2025")
    assert not page.select("#map details, #map table, #map form, select[name=year]")
    assert page.select_one("#map a[href='https://carto.com/attributions']").text == "CARTO"
    assert page.select_one("#map > .wc-landing__metrics + [data-run-atlas]")
    assert "Larger markers indicate more hillslopes." in page.select_one("#map figcaption").get_text()
    assert {button["aria-label"] for button in page.select("#map button")} == {
        "Zoom map in", "Zoom map out", "Reset map view",
    }
    assert "North of the equator, west of Greenwich: 27." in page.select_one("#atlas-geography").get_text()
    assert "Use the arrow keys to pan." in page.select_one("#atlas-keyboard").get_text()
    assert not page.select(".wc-landing__atlas-inspection")
    assert page.select_one('script[src*="deck.gl"]')
    assert page.select_one('script[type=module][src$="landing-atlas.js"]')

    count, hillslopes, latest = page.select(".wc-landing__metrics dd")
    assert count.get_text(strip=True) == "27"
    assert hillslopes.get_text(strip=True) == "104"
    assert latest.time["datetime"] == "2026-01-26T14:30:00+00:00"
    rows = json.loads(page.select_one("[data-atlas-rows]").string)
    assert len(rows) == 27
    assert rows[0]["name"] == "<script>26</script>"
    assert rows[-1]["run_id"] == "older"
    assert all("year" not in row for row in rows)

    assert rows[0]["hillslopes"] == 4
    assert rows[-1]["hillslopes"] is None
    assert "<script>26</script>" not in response.text
    assert "<b>config</b>" not in response.text
    assert "private preview field" not in response.text

    _, page = _get(client, "/landing/preview/?page=2&year=1900")
    assert json.loads(page.select_one("[data-atlas-rows]").string) == rows


def test_preview_keeps_polar_projects_in_summary(preview):
    client, path, _ = preview
    locations = [
        [-180, 90], [180, -90], [0, 0], [180, 45], [-180, 45],
        [181, 20], [float("nan"), 20], [True, 20],
    ]
    path.write_text(json.dumps([
        {"runid": f"run-{index}", "coordinates": coordinates, "hillslopes": 0}
        for index, coordinates in enumerate(locations)
    ]), encoding="utf-8")

    _, page = _get(client)
    assert page.select_one(".wc-landing__metrics dd").get_text(strip=True) == "5"
    assert "North of the equator, west of Greenwich: 2." in page.select_one("#atlas-geography").get_text()
    rows = json.loads(page.select_one("[data-atlas-rows]").string)
    assert [row["run_id"] for row in rows] == ["run-2", "run-3", "run-4"]
    assert [row["longitude"] for row in rows] == [0, 180, -180]
    assert all(row["hillslopes"] == 0 for row in rows)
