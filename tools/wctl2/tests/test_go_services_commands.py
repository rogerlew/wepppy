from __future__ import annotations

from typing import List, Sequence, Tuple

import pytest
from typer.testing import CliRunner

from tools.wctl2.__main__ import app


class DummyResult:
    returncode = 0


def _run_command(monkeypatch, temp_project, command_args):
    runner = CliRunner()
    recorded: List[Tuple[Sequence[str], bool]] = []

    def fake_run_compose(context, args, check=True):
        recorded.append((tuple(args), check))
        return DummyResult()

    monkeypatch.setattr("tools.wctl2.commands.go_services.run_compose", fake_run_compose)

    result = runner.invoke(app, ["--project-dir", str(temp_project), *command_args])
    return result, recorded


@pytest.mark.parametrize(
    "cli_command,service_name,workdir",
    [
        ("run-preflight-tests", "preflight-build", "/workspace/services/preflight2"),
        ("run-status-tests", "status-build", "/workspace/services/status2"),
    ],
)
def test_go_service_commands_default(monkeypatch, temp_project, cli_command, service_name, workdir):
    result, recorded = _run_command(monkeypatch, temp_project, [cli_command])
    assert result.exit_code == 0
    assert recorded == [
        (
            (
                "run",
                "--rm",
                service_name,
                "sh",
                "-lc",
                f"cd {workdir} && PATH=/usr/local/go/bin:$PATH go test ./...",
            ),
            False,
        )
    ]


def test_go_service_command_with_args(monkeypatch, temp_project):
    result, recorded = _run_command(
        monkeypatch,
        temp_project,
        [
            "run-preflight-tests",
            "-tags=integration",
            "./internal/server",
        ],
    )
    assert result.exit_code == 0
    assert recorded == [
        (
            (
                "run",
                "--rm",
                "preflight-build",
                "sh",
                "-lc",
                "cd /workspace/services/preflight2 && PATH=/usr/local/go/bin:$PATH go test -tags=integration ./internal/server",
            ),
            False,
        )
    ]
