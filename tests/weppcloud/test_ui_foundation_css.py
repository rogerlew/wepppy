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
