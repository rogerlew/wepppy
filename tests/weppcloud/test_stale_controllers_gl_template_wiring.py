from __future__ import annotations

from pathlib import Path

import pytest


pytestmark = pytest.mark.unit


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_runs0_pure_wires_stale_check_script() -> None:
    root = Path(__file__).resolve().parents[2]
    template = root / "wepppy" / "weppcloud" / "routes" / "run_0" / "templates" / "runs0_pure.htm"
    contents = _read(template)

    assert "static_url('js/controllers-gl.js')" in contents
    assert "static_url('js/controllers_gl_stale_check.js')" in contents


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

    assert "static_url('js/controllers-gl.js')" in contents
    assert "static_url('js/controllers_gl_stale_check.js')" in contents


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

    assert "static_url('js/controllers-gl.js')" in contents
    assert "static_url('js/controllers_gl_stale_check.js')" in contents


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

    assert "static_url('js/controllers-gl.js')" in contents
    assert "static_url('js/controllers_gl_stale_check.js')" in contents


def test_base_report_wires_stale_check_script() -> None:
    root = Path(__file__).resolve().parents[2]
    template = root / "wepppy" / "weppcloud" / "templates" / "reports" / "_base_report.htm"
    contents = _read(template)

    assert "static_url('js/controllers-gl.js')" in contents
    assert "static_url('js/controllers_gl_stale_check.js')" in contents


def test_legacy_report_container_wires_stale_check_script() -> None:
    root = Path(__file__).resolve().parents[2]
    template = root / "wepppy" / "weppcloud" / "templates" / "reports" / "_page_container.htm"
    contents = _read(template)

    assert "static_url('js/controllers-gl.js')" in contents
    assert "static_url('js/controllers_gl_stale_check.js')" in contents
    assert "data-controllers-gl-expected-build-id" in contents


def test_base_pure_exposes_expected_build_id_dataset() -> None:
    root = Path(__file__).resolve().parents[2]
    template = root / "wepppy" / "weppcloud" / "templates" / "base_pure.htm"
    contents = _read(template)

    assert "data-controllers-gl-expected-build-id" in contents

