from __future__ import annotations

from typing import List, Tuple

import pytest
from typer.testing import CliRunner

from tools.wctl2.__main__ import app
from tools.wctl2.util import quote_args


pytestmark = pytest.mark.unit


class DummyResult:
    returncode = 0


def test_migrate_run_with_runid(monkeypatch, temp_project) -> None:
    runner = CliRunner()
    recorded: List[Tuple[str, str, bool, bool]] = []

    def fake_compose_exec(context, service, exec_command, tty=True, check=True):
        recorded.append((service, exec_command, tty, check))
        return DummyResult()

    monkeypatch.setattr("tools.wctl2.commands.migrations.compose_exec", fake_compose_exec)

    result = runner.invoke(
        app,
        [
            "--project-dir",
            str(temp_project),
            "migrate-run",
            "lt_202012_demo",
            "--dry-run",
            "--force",
            "--only",
            "run_paths",
            "--only",
            "landuse_parquet",
            "--verbose",
        ],
    )

    assert result.exit_code == 0
    python_args = [
        "/opt/venv/bin/python",
        "-m",
        "wepppy.tools.migrations.migrate_run",
        "--runid",
        "lt_202012_demo",
        "--dry-run",
        "--force",
        "--verbose",
        "--only",
        "run_paths",
        "--only",
        "landuse_parquet",
    ]
    expected = (
        "cd /workdir/wepppy && "
        "PYTHONPATH=/workdir/wepppy "
        "MYPY_CACHE_DIR=/tmp/mypy_cache "
        f"{quote_args(python_args)}"
    )
    assert recorded == [("weppcloud", expected, False, False)]


def test_migrate_run_with_wd(monkeypatch, temp_project) -> None:
    runner = CliRunner()
    recorded: List[Tuple[str, str, bool, bool]] = []

    def fake_compose_exec(context, service, exec_command, tty=True, check=True):
        recorded.append((service, exec_command, tty, check))
        return DummyResult()

    monkeypatch.setattr("tools.wctl2.commands.migrations.compose_exec", fake_compose_exec)

    result = runner.invoke(
        app,
        [
            "--project-dir",
            str(temp_project),
            "migrate-run",
            "--wd",
            "/wc1/runs/lt/lt_202012_demo",
        ],
    )

    assert result.exit_code == 0
    python_args = [
        "/opt/venv/bin/python",
        "-m",
        "wepppy.tools.migrations.migrate_run",
        "--wd",
        "/wc1/runs/lt/lt_202012_demo",
    ]
    expected = (
        "cd /workdir/wepppy && "
        "PYTHONPATH=/workdir/wepppy "
        "MYPY_CACHE_DIR=/tmp/mypy_cache "
        f"{quote_args(python_args)}"
    )
    assert recorded == [("weppcloud", expected, False, False)]
