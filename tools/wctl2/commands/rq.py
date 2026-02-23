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
_RQ_SNAPSHOT_MODULE = "wepppy.rq.info_snapshot"
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


def _compose_rq_info_command(extra_args: List[str]) -> str:
    redis_url_command = _compose_rq_redis_url_command()
    rq_args = quote_args([*_RQ_DEFAULT_QUEUES, *extra_args])
    return (
        "set -euo pipefail; "
        f'redis_url="$({redis_url_command})"; '
        f'exec {_RQ_BINARY} info -u "$redis_url" {rq_args}'
    )


def _parse_interval_only(extra_args: List[str]) -> float | None:
    """Return interval seconds when args are exactly ``--interval <seconds>``."""

    if not extra_args:
        return None

    if len(extra_args) == 2 and extra_args[0] == "--interval":
        raw_value = extra_args[1]
    elif len(extra_args) == 1 and extra_args[0].startswith("--interval="):
        raw_value = extra_args[0].split("=", 1)[1]
    else:
        return None

    try:
        interval = float(raw_value)
    except ValueError:
        return None
    if interval <= 0:
        return None
    return interval


def _compose_snapshot_command(interval_seconds: float) -> str:
    args = [
        _PYTHON_BIN,
        "-u",
        "-m",
        _RQ_SNAPSHOT_MODULE,
        "--interval",
        str(interval_seconds),
    ]
    return _compose_python_command(args)


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
        extra_args = list(ctx.args)
        interval_seconds = _parse_interval_only(extra_args)

        if interval_seconds is not None:
            command = _compose_snapshot_command(interval_seconds)
        else:
            command = _compose_rq_info_command(extra_args)

        result = compose_exec(context, "rq-worker", command, check=False)
        if result.returncode != 0:
            _exit_from_result(result)

        if interval_seconds is not None:
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
