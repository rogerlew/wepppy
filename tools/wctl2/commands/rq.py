from __future__ import annotations

import subprocess
from typing import List

import typer

from ..context import CLIContext
from ..docker import compose_exec
from ..util import quote_args

_RQ_BINARY = "/opt/venv/bin/rq"
_RQ_REDIS_URL = "redis://redis:6379/9"
_RQ_DEFAULT_QUEUES = ("default", "batch")
_PYTHON_BIN = "/opt/venv/bin/python"
_RQ_DETAIL_MODULE = "wepppy.rq.job_summary"


def _context(ctx: typer.Context) -> CLIContext:
    context = ctx.obj
    if not isinstance(context, CLIContext):
        raise RuntimeError("CLIContext is not initialized.")
    return context


def _exit_from_result(result: subprocess.CompletedProcess) -> None:
    raise typer.Exit(result.returncode)


def _compose_python_command(args: List[str]) -> str:
    quoted = quote_args(args)
    return f"cd /workdir/wepppy && PYTHONPATH=/workdir/wepppy {quoted}"


def register(app: typer.Typer) -> None:
    @app.command(
        "rq-info",
        context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
        help="Show RQ worker and queue stats for default and batch queues.",
    )
    def rq_info(
        ctx: typer.Context,
        detail: bool = typer.Option(
            False,
            "--detail",
            help="Append job details (runid, description, auth actor) after rq info output.",
        ),
        detail_limit: int = typer.Option(
            50,
            "--detail-limit",
            help="Maximum jobs per state and queue for --detail (0 for unlimited).",
        ),
    ) -> None:
        context = _context(ctx)
        args: List[str] = [
            _RQ_BINARY,
            "info",
            "-u",
            _RQ_REDIS_URL,
            *_RQ_DEFAULT_QUEUES,
            *list(ctx.args),
        ]
        command = quote_args(args)
        result = compose_exec(context, "rq-worker", command, check=False)
        if result.returncode != 0:
            _exit_from_result(result)
        if detail:
            detail_args = [
                _PYTHON_BIN,
                "-m",
                _RQ_DETAIL_MODULE,
                "--queues",
                ",".join(_RQ_DEFAULT_QUEUES),
                "--limit",
                str(detail_limit),
            ]
            detail_command = _compose_python_command(detail_args)
            detail_result = compose_exec(context, "rq-worker", detail_command, check=False)
            _exit_from_result(detail_result)
        _exit_from_result(result)
