from pathlib import Path

import pytest


pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_fork_console_exposes_replaceable_progress_region() -> None:
    control = (
        REPO_ROOT
        / "wepppy"
        / "weppcloud"
        / "templates"
        / "controls"
        / "fork_console_control.htm"
    ).read_text(encoding="utf-8")

    assert "data-fork-progress" in control
    assert 'role="status"' in control
    assert 'aria-live="polite"' in control


def test_fork_console_does_not_auto_connect_idle_status_stream() -> None:
    script = (
        REPO_ROOT
        / "wepppy"
        / "weppcloud"
        / "static"
        / "js"
        / "fork_console.js"
    ).read_text(encoding="utf-8")

    assert "autoConnect: false" in script
    assert "restoreTrackedJob();" in script
