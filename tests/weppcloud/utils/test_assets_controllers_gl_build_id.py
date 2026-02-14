from __future__ import annotations

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

