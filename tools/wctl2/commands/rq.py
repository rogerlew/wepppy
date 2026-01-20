from __future__ import annotations

import subprocess
from typing import List
from urllib.parse import quote, urlparse, urlunparse

import typer

from ..context import CLIContext
from ..docker import compose_exec
from ..util import quote_args

_RQ_BINARY = "/opt/venv/bin/rq"
_RQ_DEFAULT_DB = "9"
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


def _resolve_rq_redis_url(context: CLIContext) -> str:
    raw_url = context.env_value("RQ_REDIS_URL") or context.env_value("REDIS_URL")
    password = (context.env_value("REDIS_PASSWORD") or "").strip()

    if raw_url:
        parsed = urlparse(raw_url)
        if parsed.scheme and parsed.hostname:
            netloc = parsed.netloc
            if password and parsed.password is None:
                username = parsed.username or ""
                password_enc = quote(password, safe="")
                host = parsed.hostname
                port = f":{parsed.port}" if parsed.port else ""
                if username:
                    netloc = f"{username}:{password_enc}@{host}{port}"
                else:
                    netloc = f":{password_enc}@{host}{port}"
            return urlunparse(parsed._replace(netloc=netloc, path=f"/{_RQ_DEFAULT_DB}"))
        return raw_url

    host = context.env_value("REDIS_HOST") or "redis"
    port = context.env_value("REDIS_PORT") or "6379"
    if password:
        password_enc = quote(password, safe="")
        return f"redis://:{password_enc}@{host}:{port}/{_RQ_DEFAULT_DB}"
    return f"redis://{host}:{port}/{_RQ_DEFAULT_DB}"


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
        redis_url = _resolve_rq_redis_url(context)
        args: List[str] = [
            _RQ_BINARY,
            "info",
            "-u",
            redis_url,
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
