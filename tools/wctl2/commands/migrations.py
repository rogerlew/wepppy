from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List, Optional

import typer

from ..context import CLIContext
from ..docker import compose_exec
from ..util import quote_args


def _context(ctx: typer.Context) -> CLIContext:
    context = ctx.obj
    if not isinstance(context, CLIContext):
        raise RuntimeError("CLIContext is not initialized.")
    return context


def _exit_from_result(result: subprocess.CompletedProcess) -> None:
    raise typer.Exit(result.returncode)


def register(app: typer.Typer) -> None:
    @app.command("migrate-run", help="Run migrations for a run id or working directory.")
    def migrate_run(
        ctx: typer.Context,
        runid: Optional[str] = typer.Argument(None, help="Run identifier to migrate."),
        wd: Optional[Path] = typer.Option(
            None,
            "--wd",
            help="Working directory to migrate (cannot be combined with runid).",
        ),
        dry_run: bool = typer.Option(
            False,
            "--dry-run",
            help="Check what migrations would run without making changes.",
        ),
        archive_before: bool = typer.Option(
            False,
            "--archive-before",
            help="Create an archive backup before running migrations.",
        ),
        force: bool = typer.Option(
            False,
            "--force",
            help="Run migrations even if nothing appears to be needed.",
        ),
        only: Optional[List[str]] = typer.Option(
            None,
            "--only",
            help="Run only specific migration(s). Can be specified multiple times.",
        ),
        verbose: bool = typer.Option(
            False,
            "--verbose",
            "-v",
            help="Print detailed progress information.",
        ),
    ) -> None:
        context = _context(ctx)
        if runid and wd is not None:
            raise typer.BadParameter("Use either runid or --wd, not both.")
        if not runid and wd is None:
            raise typer.BadParameter("Provide a runid or --wd.")

        args: List[str] = [
            "cd",
            "/workdir/wepppy",
            "&&",
            "PYTHONPATH=/workdir/wepppy",
            "MYPY_CACHE_DIR=/tmp/mypy_cache",
            "/opt/venv/bin/python",
            "-m",
            "wepppy.tools.migrations.migrate_run",
        ]

        if wd is not None:
            args.extend(["--wd", str(wd)])
        else:
            args.extend(["--runid", runid])

        if dry_run:
            args.append("--dry-run")
        if archive_before:
            args.append("--archive-before")
        if force:
            args.append("--force")
        if verbose:
            args.append("--verbose")
        if only:
            for migration in only:
                args.extend(["--only", migration])

        command = quote_args(args)
        result = compose_exec(context, "weppcloud", command, tty=False, check=False)
        _exit_from_result(result)
