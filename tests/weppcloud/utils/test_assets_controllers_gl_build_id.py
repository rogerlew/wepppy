from __future__ import annotations

import os
from pathlib import Path

import pytest

from wepppy.weppcloud.utils.assets import resolve_controllers_gl_build_id


pytestmark = pytest.mark.unit


def test_resolve_controllers_gl_build_id_parses_build_date(tmp_path: Path) -> None:
    target = tmp_path / "controllers-gl.js"
    target.write_text(
        "\n".join(
            [
                "/* ----------------------------------------------------------------------------",
                " * Controllers (controllers-gl.js)",
                " * NOTE: Generated via build_controllers_js.py from",
                " *       wepppy/weppcloud/controllers_js/templates/*.js",
                " * Build date: 2026-02-14T04:40:41Z",
                " * ----------------------------------------------------------------------------",
                " */",
            ]
        ),
        encoding="utf-8",
    )

    assert resolve_controllers_gl_build_id(target) == "2026-02-14T04:40:41Z"


def test_resolve_controllers_gl_build_id_returns_none_when_missing(tmp_path: Path) -> None:
    target = tmp_path / "controllers-gl.js"
    target.write_text("/* no build date header */\n", encoding="utf-8")

    assert resolve_controllers_gl_build_id(target) is None



@pytest.mark.parametrize("replace", [False, True])
def test_build_id_tracks_restored_time_changes(tmp_path, replace):
    target = tmp_path / "controllers-gl.js"
    target.write_text("Build date: 2026-09-16T00:00:00Z\n")
    before = target.stat()
    assert resolve_controllers_gl_build_id(target) == "2026-09-16T00:00:00Z"
    destination = tmp_path / "replacement" if replace else target
    destination.write_text("Build date: 2026-09-17T00:00:00Z\n")
    os.utime(destination, ns=(before.st_atime_ns, before.st_mtime_ns))
    if replace:
        os.replace(destination, target)
    assert target.stat().st_size == before.st_size
    assert resolve_controllers_gl_build_id(target) == "2026-09-17T00:00:00Z"
    target.unlink()
    assert resolve_controllers_gl_build_id(target) is None


@pytest.mark.parametrize("payload, expected", [
    (b"", None),
    (b"Build date: \nBuild date: later\n", None),
    (b"\n" * 80 + b"Build date: later\n", None),
    (b"\xff Build date:  current  \n", "current"),
])
def test_header_parser_compatibility(tmp_path, payload, expected):
    target = tmp_path / "controllers-gl.js"
    target.write_bytes(payload)
    assert resolve_controllers_gl_build_id(target) == expected


def test_prior_success_does_not_bypass_read_error(tmp_path, monkeypatch):
    target = tmp_path / "controllers-gl.js"
    target.write_text("Build date: current\n")
    assert resolve_controllers_gl_build_id(target) == "current"
    def denied(*args, **kwargs):
        raise PermissionError("read denied")
    monkeypatch.setattr(Path, "open", denied)
    assert resolve_controllers_gl_build_id(target) is None
