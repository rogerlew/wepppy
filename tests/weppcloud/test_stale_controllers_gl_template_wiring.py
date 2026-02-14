from __future__ import annotations

import re
from pathlib import Path

import pytest


pytestmark = pytest.mark.unit


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _strip_template_comments(contents: str) -> str:
    """Remove HTML + Jinja comments to avoid matching commented-out script tags."""
    without_html_comments = re.sub(r"<!--.*?-->", "", contents, flags=re.DOTALL)
    return re.sub(r"{#.*?#}", "", without_html_comments, flags=re.DOTALL)


def _find_deferred_static_url_script(contents: str, asset: str) -> int:
    pattern = re.compile(
        r"<script[^>]+static_url\('"
        + re.escape(asset)
        + r"'\)[^>]*>",
        re.IGNORECASE,
    )
    match = pattern.search(contents)
    assert match, f"Missing script tag for static_url('{asset}')"

    tag = match.group(0).lower()
    assert "defer" in tag, f"script tag for static_url('{asset}') must include defer"
    return match.start()


def _assert_deferred_order(contents: str) -> None:
    contents = _strip_template_comments(contents)
    controllers_pos = _find_deferred_static_url_script(contents, "js/controllers-gl.js")
    stale_check_pos = _find_deferred_static_url_script(contents, "js/controllers_gl_stale_check.js")
    assert controllers_pos < stale_check_pos, "controllers-gl.js must be loaded before controllers_gl_stale_check.js"


def test_runs0_pure_wires_stale_check_script() -> None:
    root = Path(__file__).resolve().parents[2]
    template = root / "wepppy" / "weppcloud" / "routes" / "run_0" / "templates" / "runs0_pure.htm"
    contents = _read(template)

    _assert_deferred_order(contents)


def test_fork_console_wires_stale_check_script() -> None:
    root = Path(__file__).resolve().parents[2]
    template = (
        root
        / "wepppy"
        / "weppcloud"
        / "routes"
        / "fork_console"
        / "templates"
        / "rq-fork-console.htm"
    )
    contents = _read(template)

    _assert_deferred_order(contents)


def test_archive_dashboard_wires_stale_check_script() -> None:
    root = Path(__file__).resolve().parents[2]
    template = (
        root
        / "wepppy"
        / "weppcloud"
        / "routes"
        / "archive_dashboard"
        / "templates"
        / "rq-archive-dashboard.htm"
    )
    contents = _read(template)

    _assert_deferred_order(contents)


def test_readme_editor_wires_stale_check_script() -> None:
    root = Path(__file__).resolve().parents[2]
    template = (
        root
        / "wepppy"
        / "weppcloud"
        / "routes"
        / "readme_md"
        / "templates"
        / "readme_editor.htm"
    )
    contents = _read(template)

    _assert_deferred_order(contents)


def test_base_report_wires_stale_check_script() -> None:
    root = Path(__file__).resolve().parents[2]
    template = root / "wepppy" / "weppcloud" / "templates" / "reports" / "_base_report.htm"
    contents = _read(template)

    _assert_deferred_order(contents)


def test_legacy_report_container_wires_stale_check_script() -> None:
    root = Path(__file__).resolve().parents[2]
    template = root / "wepppy" / "weppcloud" / "templates" / "reports" / "_page_container.htm"
    contents = _read(template)

    _assert_deferred_order(contents)
    assert "data-controllers-gl-expected-build-id" in contents


def test_base_pure_exposes_expected_build_id_dataset() -> None:
    root = Path(__file__).resolve().parents[2]
    template = root / "wepppy" / "weppcloud" / "templates" / "base_pure.htm"
    contents = _read(template)

    assert "data-controllers-gl-expected-build-id" in contents
