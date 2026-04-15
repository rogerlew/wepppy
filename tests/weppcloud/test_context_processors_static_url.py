from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from flask import Flask

from wepppy.weppcloud._context_processors import register_context_processors

pytestmark = pytest.mark.unit


def _collect_template_context(app: Flask) -> dict[str, object]:
    context: dict[str, object] = {}
    for processor in app.template_context_processors[None]:
        context.update(processor())
    return context


def _write_controllers_gl(sync_root: Path, build_id: str) -> None:
    target = sync_root / "js" / "controllers-gl.js"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "\n".join(
            [
                "/* controllers-gl bundle */",
                f"Build date: {build_id}",
            ]
        ),
        encoding="utf-8",
    )


def test_static_url_appends_controllers_build_id_for_bundle_assets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_id = "2099-01-02T03:04:05Z"
    sync_root = tmp_path / "sync-assets"
    _write_controllers_gl(sync_root, build_id)
    monkeypatch.setenv("STATIC_ASSET_SYNC_DIR", str(sync_root))

    app = Flask(__name__)
    app.config["ASSET_VERSION"] = "testsha"
    register_context_processors(app, get_all_runs=lambda: [], user_model=None, run_model=None)

    with app.test_request_context("/"):
        context = _collect_template_context(app)
        static_url = context["static_url"]
        assert callable(static_url)

        controllers_url = static_url("js/controllers-gl.js")
        stale_check_url = static_url("js/controllers_gl_stale_check.js")
        theme_url = static_url("js/theme.js")

    controllers_qs = parse_qs(urlparse(controllers_url).query)
    stale_check_qs = parse_qs(urlparse(stale_check_url).query)
    theme_qs = parse_qs(urlparse(theme_url).query)

    assert controllers_qs.get("v") == ["testsha"]
    assert stale_check_qs.get("v") == ["testsha"]
    assert theme_qs.get("v") == ["testsha"]

    assert controllers_qs.get("cg") == [build_id]
    assert stale_check_qs.get("cg") == [build_id]
    assert "cg" not in theme_qs

    assert context["controllers_gl_expected_build_id"] == build_id


def test_static_url_skips_controllers_build_id_when_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sync_root = tmp_path / "sync-assets"
    sync_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("STATIC_ASSET_SYNC_DIR", str(sync_root))

    app = Flask(__name__)
    app.config["ASSET_VERSION"] = "testsha"
    register_context_processors(app, get_all_runs=lambda: [], user_model=None, run_model=None)

    with app.test_request_context("/"):
        context = _collect_template_context(app)
        static_url = context["static_url"]
        assert callable(static_url)

        controllers_url = static_url("js/controllers-gl.js")
    controllers_qs = parse_qs(urlparse(controllers_url).query)

    assert controllers_qs.get("v") == ["testsha"]
    assert "cg" not in controllers_qs
    assert context["controllers_gl_expected_build_id"] is None
