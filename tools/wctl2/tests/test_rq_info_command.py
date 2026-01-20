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


def test_rq_info_uses_password_from_env(monkeypatch: pytest.MonkeyPatch, temp_project) -> None:
    docker_env = temp_project / "docker" / ".env"
    docker_env.write_text(docker_env.read_text() + "REDIS_PASSWORD=sekret\n")

    result, recorded = _run_command(monkeypatch, temp_project, ["rq-info"])

    assert result.exit_code == 0
    assert recorded == [
        (
            "rq-worker",
            "/opt/venv/bin/rq info -u redis://:sekret@redis:6379/9 default batch",
            True,
            False,
        )
    ]


def test_rq_info_detail_runs_summary(monkeypatch: pytest.MonkeyPatch, temp_project) -> None:
    result, recorded = _run_command(monkeypatch, temp_project, ["rq-info", "--detail"])

    assert result.exit_code == 0
    assert recorded == [
        (
            "rq-worker",
            "/opt/venv/bin/rq info -u redis://redis:6379/9 default batch",
            True,
            False,
        ),
        (
            "rq-worker",
            "cd /workdir/wepppy && PYTHONPATH=/workdir/wepppy /opt/venv/bin/python -m wepppy.rq.job_summary --queues default,batch --limit 50",
            True,
            False,
        ),
    ]


def test_rq_info_detail_limit(monkeypatch: pytest.MonkeyPatch, temp_project) -> None:
    result, recorded = _run_command(
        monkeypatch,
        temp_project,
        ["rq-info", "--detail", "--detail-limit", "10"],
    )

    assert result.exit_code == 0
    assert recorded[-1] == (
        "rq-worker",
        "cd /workdir/wepppy && PYTHONPATH=/workdir/wepppy /opt/venv/bin/python -m wepppy.rq.job_summary --queues default,batch --limit 10",
        True,
        False,
    )
