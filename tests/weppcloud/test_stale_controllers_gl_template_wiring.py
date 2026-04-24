from __future__ import annotations

import re
from pathlib import Path

import pytest


pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
WEPPCLOUD_ROOT = REPO_ROOT / "wepppy" / "weppcloud"
TEMPLATE_SUFFIXES = {".htm", ".html", ".j2"}


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


def _iter_template_files() -> list[Path]:
    templates = []
    for scope in ("templates", "routes"):
        base = WEPPCLOUD_ROOT / scope
        for candidate in base.rglob("*"):
            if candidate.is_file() and candidate.suffix in TEMPLATE_SUFFIXES:
                templates.append(candidate)
    return sorted(templates)


def _controllers_gl_template_files() -> list[Path]:
    return [
        candidate
        for candidate in _iter_template_files()
        if "controllers-gl.js" in _read(candidate)
    ]


def _assert_immediate_static_url_pair(contents: str) -> None:
    contents = _strip_template_comments(contents)
    pair_pattern = re.compile(
        r"<script[^>]+static_url\('js/controllers-gl\.js'\)[^>]*></script>\s*"
        r"<script[^>]+static_url\('js/controllers_gl_stale_check\.js'\)[^>]*></script>",
        re.IGNORECASE,
    )
    assert pair_pattern.search(contents), (
        "Expected controllers-gl.js and controllers_gl_stale_check.js to be loaded "
        "via static_url in immediate sequence."
    )


@pytest.mark.parametrize(
    "template_path",
    _controllers_gl_template_files(),
    ids=lambda path: str(path.relative_to(REPO_ROOT)),
)
def test_all_controllers_gl_templates_use_static_url_and_immediate_stale_check(template_path: Path) -> None:
    contents = _read(template_path)
    stripped = _strip_template_comments(contents)

    assert "url_for('static', filename='js/controllers-gl.js')" not in stripped
    assert "/static/js/controllers-gl.js" not in stripped
    _assert_immediate_static_url_pair(stripped)


def test_runs0_pure_wires_stale_check_script() -> None:
    template = WEPPCLOUD_ROOT / "routes" / "run_0" / "templates" / "runs0_pure.htm"
    contents = _read(template)

    _assert_deferred_order(contents)


def test_fork_console_wires_stale_check_script() -> None:
    template = (
        WEPPCLOUD_ROOT
        / "routes"
        / "fork_console"
        / "templates"
        / "rq-fork-console.htm"
    )
    contents = _read(template)

    _assert_deferred_order(contents)


def test_archive_dashboard_wires_stale_check_script() -> None:
    template = (
        WEPPCLOUD_ROOT
        / "routes"
        / "archive_dashboard"
        / "templates"
        / "rq-archive-dashboard.htm"
    )
    contents = _read(template)

    _assert_deferred_order(contents)


def test_readme_editor_wires_stale_check_script() -> None:
    template = (
        WEPPCLOUD_ROOT
        / "routes"
        / "readme_md"
        / "templates"
        / "readme_editor.htm"
    )
    contents = _read(template)

    _assert_deferred_order(contents)


def test_base_report_wires_stale_check_script() -> None:
    template = WEPPCLOUD_ROOT / "templates" / "reports" / "_base_report.htm"
    contents = _read(template)

    _assert_deferred_order(contents)


def test_legacy_report_container_wires_stale_check_script() -> None:
    template = WEPPCLOUD_ROOT / "templates" / "reports" / "_page_container.htm"
    contents = _read(template)

    _assert_deferred_order(contents)
    assert "data-controllers-gl-expected-build-id" in contents


def test_base_pure_exposes_expected_build_id_dataset() -> None:
    template = WEPPCLOUD_ROOT / "templates" / "base_pure.htm"
    contents = _read(template)

    assert "data-controllers-gl-expected-build-id" in contents
