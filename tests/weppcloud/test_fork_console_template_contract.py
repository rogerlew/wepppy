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


def test_fork_and_archive_consoles_explain_serial_queue_wait() -> None:
    controls = REPO_ROOT / "wepppy" / "weppcloud" / "templates" / "controls"
    fork = (controls / "fork_console_control.htm").read_text(encoding="utf-8")
    archive = (controls / "archive_console_control.htm").read_text(encoding="utf-8")

    assert "Your accepted fork may remain queued before it starts" in fork
    assert "source project state available when the worker begins" in fork
    assert "An accepted request may remain queued before it starts" in archive
    assert "do not edit the project while a restore is queued or running" in archive
