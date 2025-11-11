from __future__ import annotations

import typer

from ..context import CLIContext
from ..docker import run_compose
from ..util import quote_args


def _context(ctx: typer.Context) -> CLIContext:
    context = ctx.obj
    if not isinstance(context, CLIContext):
        raise RuntimeError("CLIContext is not initialised.")
    return context


def _register_go_test_command(
    app: typer.Typer,
    command_name: str,
    service_name: str,
    service_workdir: str,
) -> None:
    @app.command(
        command_name,
        context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    )
    def run_go_tests(ctx: typer.Context) -> None:
        context = _context(ctx)
        args = list(ctx.args) or ["./..."]
        quoted = quote_args(args)
        go_command = f"cd {service_workdir} && PATH=/usr/local/go/bin:$PATH go test"
        if quoted:
            go_command = f"{go_command} {quoted}"
        compose_args = ["run", "--rm", service_name, "sh", "-lc", go_command]
        result = run_compose(context, compose_args, check=False)
        raise typer.Exit(result.returncode)


def register(app: typer.Typer) -> None:
    _register_go_test_command(
        app,
        command_name="run-preflight-tests",
        service_name="preflight-build",
        service_workdir="/workspace/services/preflight2",
    )
    _register_go_test_command(
        app,
        command_name="run-status-tests",
        service_name="status-build",
        service_workdir="/workspace/services/status2",
    )
