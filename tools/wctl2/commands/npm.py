from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import typer

from ..context import CLIContext

_DIRECT_COMMANDS = {
    "install",
    "ci",
    "update",
    "exec",
    "run",
    "init",
    "publish",
    "link",
    "login",
    "logout",
    "cache",
    "config",
    "set",
    "get",
    "rebuild",
    "outdated",
    "dedupe",
    "audit",
    "doctor",
    "fund",
}


def _context(ctx: typer.Context) -> CLIContext:
    context = ctx.obj
    if not isinstance(context, CLIContext):
        raise RuntimeError("CLIContext is not initialised.")
    return context


def register(app: typer.Typer) -> None:
    @app.command(
        "run-npm",
        context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    )
    def run_npm(ctx: typer.Context) -> None:
        context = _context(ctx)
        if shutil.which("npm") is None:
            typer.echo("npm is required for run-npm.", err=True)
            raise typer.Exit(1)

        prefix = Path(context.project_dir / "wepppy" / "weppcloud" / "static-src")
        args = list(ctx.args)

        if not args:
            command = ["npm", "--prefix", str(prefix)]
        else:
            first = args[0]
            if first in _DIRECT_COMMANDS:
                command = ["npm", "--prefix", str(prefix), *args]
            else:
                command = ["npm", "--prefix", str(prefix), "run", *args]

        result = subprocess.run(command, cwd=str(context.project_dir), env=context.environment)
        raise typer.Exit(result.returncode)
