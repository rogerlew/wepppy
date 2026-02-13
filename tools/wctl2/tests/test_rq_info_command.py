from __future__ import annotations

from typing import List, Tuple

import pytest
from typer.testing import CliRunner

from tools.wctl2.__main__ import app


pytestmark = pytest.mark.unit


class DummyResult:
    returncode = 0


def _expected_rq_info_command(extra: str = "") -> str:
    base = (
        "set -euo pipefail; "
        "redis_url=\"$(cd /workdir/wepppy && PYTHONPATH=/workdir/wepppy "
        "/opt/venv/bin/python -c "
        "'from wepppy.config.redis_settings import redis_url, RedisDB; print(redis_url(RedisDB.RQ))')\"; "
        "exec /opt/venv/bin/rq info -u \"$redis_url\" default batch"
    )
    if extra:
        return f"{base} {extra}"
    return base


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
            _expected_rq_info_command(),
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
            _expected_rq_info_command("--interval 1"),
            True,
            False,
        )
    ]


def test_rq_info_uses_password_from_env(monkeypatch: pytest.MonkeyPatch, temp_project) -> None:
    docker_env = temp_project / "docker" / ".env"
    docker_env.write_text(docker_env.read_text() + "REDIS_PASSWORD=sekret\n")

    result, recorded = _run_command(monkeypatch, temp_project, ["rq-info"])

    assert result.exit_code == 0
    assert recorded == [("rq-worker", _expected_rq_info_command(), True, False)]
    assert "sekret" not in recorded[0][1]


def test_rq_info_detail_runs_summary(monkeypatch: pytest.MonkeyPatch, temp_project) -> None:
    result, recorded = _run_command(monkeypatch, temp_project, ["rq-info", "--detail"])

    assert result.exit_code == 0
    assert recorded == [
        (
            "rq-worker",
            _expected_rq_info_command(),
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
