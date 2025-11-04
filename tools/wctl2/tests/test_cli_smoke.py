from __future__ import annotations

import sys
from typing import List, Sequence, Tuple

import pytest
from typer.testing import CliRunner

from tools.wctl2.__main__ import app, run


def test_run_npm_help(temp_project) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--project-dir", str(temp_project), "run-npm", "--help"])
    assert result.exit_code == 0
    assert "Usage" in result.stdout
    assert "run-npm" in result.stdout


def test_passthrough_delegates_to_docker_compose(monkeypatch: pytest.MonkeyPatch, temp_project) -> None:
    runner = CliRunner()
    recorded: List[Tuple[Sequence[str], bool]] = []

    class DummyResult:
        returncode = 0

    def fake_run_compose(context, args, check=True):
        recorded.append((tuple(args), check))
        return DummyResult()

    monkeypatch.setattr("tools.wctl2.commands.passthrough.run_compose", fake_run_compose)

    original_argv = sys.argv
    sys.argv = ["wctl2", "--project-dir", str(temp_project), "docker", "compose", "ps"]
    try:
        with pytest.raises(SystemExit) as exc:
            run()
    finally:
        sys.argv = original_argv

    assert exc.value.code == 0
    assert recorded == [(("ps",), False)]
