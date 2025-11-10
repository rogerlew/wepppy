from __future__ import annotations

import subprocess
from typing import List

import typer

from ..context import CLIContext
from ..docker import compose_exec
from ..util import quote_args


def _context(ctx: typer.Context) -> CLIContext:
    context = ctx.obj
    if not isinstance(context, CLIContext):
        raise RuntimeError("CLIContext is not initialised.")
    return context


def _exit_from_result(result: subprocess.CompletedProcess) -> None:
    raise typer.Exit(result.returncode)


def register(app: typer.Typer) -> None:
    @app.command(
        "run-pytest",
        context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    )
    def run_pytest(ctx: typer.Context) -> None:
        context = _context(ctx)
        args = list(ctx.args) or ["tests"]
        quoted = quote_args(args)
        command = (
            "cd /workdir/wepppy && "
            "PYTHONPATH=/workdir/wepppy "
            "MYPY_CACHE_DIR=/tmp/mypy_cache "
            f"/opt/venv/bin/pytest {quoted}"
        )
        result = compose_exec(context, "weppcloud", command, check=False)
        _exit_from_result(result)

    @app.command(
        "run-python",
        context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    )
    def run_python(ctx: typer.Context) -> None:
        context = _context(ctx)
        args = list(ctx.args)
        quoted = quote_args(args)
        python_invocation = "/opt/venv/bin/python"
        if quoted:
            python_invocation = f"{python_invocation} {quoted}"
        command = (
            "cd /workdir/wepppy && "
            "PYTHONPATH=/workdir/wepppy "
            "MYPY_CACHE_DIR=/tmp/mypy_cache "
            f"{python_invocation}"
        )
        result = compose_exec(context, "weppcloud", command, check=False)
        _exit_from_result(result)

    @app.command(
        "run-stubtest",
        context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    )
    def run_stubtest(ctx: typer.Context) -> None:
        context = _context(ctx)
        args = list(ctx.args) or ["wepppy.nodb.core"]
        quoted = quote_args(args)
        command = (
            "cd /tmp && "
            "PYTHONPATH=/workdir/wepppy "
            "MYPY_CACHE_DIR=/tmp/mypy_cache "
            f"/opt/venv/bin/stubtest {quoted}"
        )
        result = compose_exec(context, "weppcloud", command, check=False)
        _exit_from_result(result)

    @app.command(
        "run-stubgen",
        context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    )
    def run_stubgen(ctx: typer.Context) -> None:
        context = _context(ctx)
        command = ["python", "tools/sync_stubs.py", *ctx.args]
        result = subprocess.run(command, cwd=str(context.project_dir), env=context.environment)
        raise typer.Exit(result.returncode)

    @app.command("check-test-stubs")
    def check_test_stubs(ctx: typer.Context) -> None:
        context = _context(ctx)
        command = "cd /workdir/wepppy && python tools/check_stubs.py"
        result = compose_exec(context, "weppcloud", command, check=False)
        _exit_from_result(result)

    @app.command(
        "check-test-isolation",
        context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    )
    def check_test_isolation(ctx: typer.Context) -> None:
        context = _context(ctx)
        quoted = quote_args(list(ctx.args))
        command = "cd /workdir/wepppy && python tools/check_test_isolation.py"
        if quoted:
            command = f"{command} {quoted}"
        result = compose_exec(context, "weppcloud", command, check=False)
        _exit_from_result(result)
