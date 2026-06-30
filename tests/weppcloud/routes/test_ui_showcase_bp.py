from __future__ import annotations

from importlib import import_module
from pathlib import Path

import pytest

pytest.importorskip("flask")
from flask import Flask

try:
    ui_showcase_module = import_module("wepppy.weppcloud.routes.ui_showcase.ui_showcase_bp")
except ImportError:
    pytest.skip("UI showcase blueprint dependencies missing", allow_module_level=True)


pytestmark = pytest.mark.routes
REPO_ROOT = Path(__file__).resolve().parents[3]
COMPONENT_GALLERY_TEMPLATE = REPO_ROOT / "wepppy" / "weppcloud" / "templates" / "ui_showcase" / "component_gallery.htm"


def test_component_gallery_registers_return_period_theme_lab_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_render_template(template_name: str, **context: object) -> str:
        captured["template_name"] = template_name
        captured["context"] = context
        return "rendered"

    monkeypatch.setattr(ui_showcase_module, "render_template", fake_render_template)

    app = Flask(__name__)
    app.config["CAP_BASE_URL"] = "/cap"
    app.config["CAP_SITE_KEY"] = "demo"

    with app.app_context():
        result = ui_showcase_module.component_gallery()

    assert result == "rendered"
    assert captured["template_name"] == "ui_showcase/component_gallery.htm"

    context = captured["context"]
    assert isinstance(context, dict)
    theme_targets = context["theme_contrast_targets"]
    assert isinstance(theme_targets, list)

    target = next((entry for entry in theme_targets if entry.get("id") == "wc-return-period-measure"), None)
    assert target is not None
    assert {pair["name"] for pair in target["pairs"]} == {
        "header_text_vs_highlight",
        "value_text_vs_highlight",
    }

    template_source = COMPONENT_GALLERY_TEMPLATE.read_text(encoding="utf-8")
    assert 'data-contrast-id="wc-return-period-measure"' in template_source
    assert 'id="theme_lab_return_period_measure_header"' in template_source
    assert 'id="theme_lab_return_period_measure_value"' in template_source


def test_component_gallery_registers_jexcel_theme_lab_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_render_template(template_name: str, **context: object) -> str:
        captured["template_name"] = template_name
        captured["context"] = context
        return "rendered"

    monkeypatch.setattr(ui_showcase_module, "render_template", fake_render_template)

    app = Flask(__name__)
    app.config["CAP_BASE_URL"] = "/cap"
    app.config["CAP_SITE_KEY"] = "demo"

    with app.app_context():
        result = ui_showcase_module.component_gallery()

    assert result == "rendered"
    assert captured["template_name"] == "ui_showcase/component_gallery.htm"

    context = captured["context"]
    assert isinstance(context, dict)
    theme_targets = context["theme_contrast_targets"]
    assert isinstance(theme_targets, list)

    target = next((entry for entry in theme_targets if entry.get("id") == "wc_jexcel_table"), None)
    assert target is not None
    assert target.get("aa_exempt") is True
    assert {pair["name"] for pair in target["pairs"]} == {
        "thead_selected_text_vs_background",
        "tbody_selected_text_vs_background",
        "tbody_row_index_text_vs_background",
        "tbody_regular_text_vs_background",
    }

    template_source = COMPONENT_GALLERY_TEMPLATE.read_text(encoding="utf-8")
    assert 'data-contrast-id="wc-jexcel-table"' in template_source
    assert 'id="theme_lab_jexcel_header_selected"' in template_source
    assert 'id="theme_lab_jexcel_selected_cell"' in template_source
    assert 'id="theme_lab_jexcel_row_index"' in template_source
    assert 'id="theme_lab_jexcel_regular_cell"' in template_source


def test_component_gallery_registers_geneva_marker_theme_lab_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_render_template(template_name: str, **context: object) -> str:
        captured["template_name"] = template_name
        captured["context"] = context
        return "rendered"

    monkeypatch.setattr(ui_showcase_module, "render_template", fake_render_template)

    app = Flask(__name__)
    app.config["CAP_BASE_URL"] = "/cap"
    app.config["CAP_SITE_KEY"] = "demo"

    with app.app_context():
        result = ui_showcase_module.component_gallery()

    assert result == "rendered"
    assert captured["template_name"] == "ui_showcase/component_gallery.htm"

    context = captured["context"]
    assert isinstance(context, dict)
    marker_combinations = context["geneva_marker_combinations"]
    assert isinstance(marker_combinations, list)
    assert len(marker_combinations) == 60

    theme_targets = context["theme_contrast_targets"]
    assert isinstance(theme_targets, list)
    target = next((entry for entry in theme_targets if entry.get("id") == "geneva_summary_marker_labels"), None)
    assert target is not None
    assert len(target["pairs"]) == 60
    assert {pair["name"] for pair in target["pairs"]} == {
        marker["id"] for marker in marker_combinations
    }
    assert all(pair["foreground_mode"] == "fill" for pair in target["pairs"])
    assert all(pair["background_mode"] == "fill" for pair in target["pairs"])

    template_source = COMPONENT_GALLERY_TEMPLATE.read_text(encoding="utf-8")
    assert 'data-contrast-id="geneva-summary-marker-labels"' in template_source
    assert "theme_lab_geneva_marker_{{ marker.id }}_circle" in template_source
    assert "theme_lab_geneva_marker_{{ marker.id }}_label" in template_source


def test_component_gallery_registers_browse_parquet_preview_banner_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_render_template(template_name: str, **context: object) -> str:
        captured["template_name"] = template_name
        captured["context"] = context
        return "rendered"

    monkeypatch.setattr(ui_showcase_module, "render_template", fake_render_template)

    app = Flask(__name__)
    app.config["CAP_BASE_URL"] = "/cap"
    app.config["CAP_SITE_KEY"] = "demo"

    with app.app_context():
        result = ui_showcase_module.component_gallery()

    assert result == "rendered"
    assert captured["template_name"] == "ui_showcase/component_gallery.htm"

    context = captured["context"]
    assert isinstance(context, dict)
    theme_targets = context["theme_contrast_targets"]
    assert isinstance(theme_targets, list)

    target = next((entry for entry in theme_targets if entry.get("id") == "browse_parquet_preview_banner"), None)
    assert target is not None
    assert {pair["name"] for pair in target["pairs"]} == {
        "preview_title_vs_banner",
        "preview_message_vs_banner",
        "filter_title_vs_banner",
        "filter_summary_vs_banner",
        "filter_code_vs_code_background",
        "action_text_vs_background",
        "action_border_vs_background",
    }

    template_source = COMPONENT_GALLERY_TEMPLATE.read_text(encoding="utf-8")
    assert 'data-contrast-id="browse-parquet-preview-banner"' in template_source
    assert 'id="theme_lab_browse_preview_banner"' in template_source
    assert 'id="theme_lab_browse_filter_feedback"' in template_source
    assert 'id="theme_lab_browse_preview_action"' in template_source
