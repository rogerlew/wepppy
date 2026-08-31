from pathlib import Path

import pytest


pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
UI_FOUNDATION_CSS = REPO_ROOT / "wepppy" / "weppcloud" / "static" / "css" / "ui-foundation.css"


def test_anchor_primary_pure_buttons_use_theme_variables() -> None:
    css = UI_FOUNDATION_CSS.read_text(encoding="utf-8")

    selector = "a.pure-button.pure-button-primary"
    assert selector in css

    rule_start = css.index(selector)
    rule_end = css.index("}", rule_start)
    rule = css[rule_start:rule_end]

    assert "--wc-button-primary-text" in rule
    assert "background-color: var(--wc-button-primary-bg" in rule
    assert "border-color: var(--wc-button-primary-bg" in rule


def test_controlled_error_summary_separates_message_and_metadata() -> None:
    css = UI_FOUNDATION_CSS.read_text(encoding="utf-8")

    assert ".wc-control__error-card" in css
    assert "background: var(--wc-error-bg)" in css
    assert ".wc-control__error-summary" in css
    assert ".wc-control__error-meta" in css
    assert "flex-wrap: wrap" in css
    assert ".wc-control__error-meta dd" in css
    assert "overflow-wrap: anywhere" in css
    assert ".wc-control__error-id" in css


def test_overflowing_table_wrapper_has_hint_and_focus_visible_contract() -> None:
    css = UI_FOUNDATION_CSS.read_text(encoding="utf-8")

    assert ".wc-table-overflow-hint" in css
    assert 'data-wc-horizontal-overflow="true"' in css
    assert ":focus-visible" in css
    assert "outline: 2px solid var(--wc-color-accent)" in css
    assert "outline-offset: 2px" in css
