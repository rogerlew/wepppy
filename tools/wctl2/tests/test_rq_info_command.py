from __future__ import annotations

from typing import List, Tuple

import pytest
from typer.testing import CliRunner

from tools.wctl2.__main__ import app


pytestmark = pytest.mark.unit


class DummyResult:
    returncode = 0


def _run_command(monkeypatch: pytest.MonkeyPatch, temp_project, command_args):
    runner = CliRunner()
    recorded: List[Tuple[str, str, bool, bool]] = []

    def fake_compose_exec(context, service, exec_command, tty=True, check=True):
        recorded.append((service, exec_command, tty, check))
        return DummyResult()

    monkeypatch.setattr("tools.wctl2.commands.rq.compose_exec", fake_compose_exec)

    result = runner.invoke(app, ["--project-dir", str(temp_project), *command_args])
    return result, recorded


def test_rq_info_defaults(monkeypatch: pytest.MonkeyPatch, temp_project) -> None:
    result, recorded = _run_command(monkeypatch, temp_project, ["rq-info"])

    assert result.exit_code == 0
    assert recorded == [
        (
            "rq-worker",
            "/opt/venv/bin/rq info -u redis://redis:6379/9 default batch",
            True,
            False,
        )
    ]


def test_rq_info_appends_args(monkeypatch: pytest.MonkeyPatch, temp_project) -> None:
    result, recorded = _run_command(monkeypatch, temp_project, ["rq-info", "--interval", "1"])

    assert result.exit_code == 0
    assert recorded == [
        (
            "rq-worker",
            "/opt/venv/bin/rq info -u redis://redis:6379/9 default batch --interval 1",
            True,
            False,
        )
    ]
