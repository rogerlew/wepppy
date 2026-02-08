from __future__ import annotations

from typing import List, Tuple

import pytest
from typer.testing import CliRunner

from tools.wctl2.__main__ import app


pytestmark = pytest.mark.unit


class DummyResult:
    returncode = 0


def test_check_rq_contracts_runs_guard_scripts(monkeypatch: pytest.MonkeyPatch, temp_project) -> None:
    runner = CliRunner()
    recorded: List[Tuple[str, str, bool, bool]] = []

    def fake_compose_exec(context, service, exec_command, tty=True, check=True):
        recorded.append((service, exec_command, tty, check))
        return DummyResult()

    monkeypatch.setattr("tools.wctl2.commands.python_tasks.compose_exec", fake_compose_exec)

    result = runner.invoke(
        app,
        [
            "--project-dir",
            str(temp_project),
            "check-rq-contracts",
        ],
    )

    assert result.exit_code == 0
    assert recorded == [
        (
            "weppcloud",
            "cd /workdir/wepppy && "
            "/opt/venv/bin/python tools/check_endpoint_inventory.py && "
            "/opt/venv/bin/python tools/check_route_contract_checklist.py",
            True,
            False,
        )
    ]
