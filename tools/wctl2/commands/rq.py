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


def _context(ctx: typer.Context) -> CLIContext:
    context = ctx.obj
    if not isinstance(context, CLIContext):
        raise RuntimeError("CLIContext is not initialized.")
    return context


def _exit_from_result(result: subprocess.CompletedProcess) -> None:
    raise typer.Exit(result.returncode)


def register(app: typer.Typer) -> None:
    @app.command(
        "rq-info",
        context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
        help="Show RQ worker and queue stats for default and batch queues.",
    )
    def rq_info(ctx: typer.Context) -> None:
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
        _exit_from_result(result)
