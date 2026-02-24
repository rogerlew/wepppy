from __future__ import annotations

import subprocess
from typing import List

import typer

from ..context import CLIContext
from ..docker import compose_exec
from ..util import quote_args

_RQ_BINARY = "/opt/venv/bin/rq"
_RQ_DEFAULT_QUEUES = ("default", "batch")
_PYTHON_BIN = "/opt/venv/bin/python"
_RQ_DETAIL_MODULE = "wepppy.rq.job_summary"
_RQ_REGISTRY_SYNC_MODULE = "tools.wctl2.rq_worker_registry_sync"
_RQ_REDIS_URL_SNIPPET = (
    "from wepppy.config.redis_settings import redis_url, RedisDB; "
    "print(redis_url(RedisDB.RQ))"
)


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


def _compose_rq_redis_url_command() -> str:
    """
    Resolve the RQ Redis URL inside the container.

    We intentionally avoid constructing an authenticated URL on the host so the
    password never appears in the host command line. The wepppy config helper
    supports both legacy env vars (REDIS_PASSWORD) and secret files
    (REDIS_PASSWORD_FILE).
    """
    args = [_PYTHON_BIN, "-c", _RQ_REDIS_URL_SNIPPET]
    return _compose_python_command(args)


def _compose_rq_registry_sync_command() -> str:
    args = [_PYTHON_BIN, "-m", _RQ_REGISTRY_SYNC_MODULE]
    return _compose_python_command(args)


def _compose_rq_info_command(extra_args: List[str]) -> str:
    registry_sync_command = _compose_rq_registry_sync_command()
    redis_url_command = _compose_rq_redis_url_command()
    rq_args = quote_args([*_RQ_DEFAULT_QUEUES, *extra_args])
    return (
        "set -euo pipefail; "
        f"{registry_sync_command}; "
        f'redis_url="$({redis_url_command})"; '
        f'exec {_RQ_BINARY} info -u "$redis_url" {rq_args}'
    )


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
        command = _compose_rq_info_command(list(ctx.args))
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
