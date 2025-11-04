from __future__ import annotations

from typing import Optional
import sys

import typer

from .commands import passthrough as passthrough_cmd
from .commands import register as register_commands
from .context import CLIContext

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"], "allow_extra_args": True, "ignore_unknown_options": True}
app = typer.Typer(
    add_completion=False,
    context_settings=CONTEXT_SETTINGS,
    help="wctl2 – Python-based control wrapper for the WEPPcloud docker compose stack.",
)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    compose_file: Optional[str] = typer.Option(None, "--compose-file", "-f", help="Compose file relative to project root."),
    project_dir: Optional[str] = typer.Option(None, "--project-dir", help="Override the detected project directory."),
    log_level: str = typer.Option("INFO", "--log-level", help="Logging level (default: INFO)."),
) -> None:
    if ctx.obj is None:
        ctx.obj = CLIContext.from_environ(
            project_dir=project_dir,
            compose_file=compose_file,
            log_level=log_level,
        )
    if ctx.invoked_subcommand is None and ctx.args:
        exit_code = passthrough_cmd.passthrough(ctx.obj, ctx.args)
        raise typer.Exit(exit_code)


register_commands(app)


def run() -> None:
    argv = sys.argv[1:]
    command_names = {info.name for info in app.registered_commands}
    compose_file: Optional[str] = None
    project_dir: Optional[str] = None
    log_level: str = "INFO"
    rest: list[str] = []

    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in ("-f", "--compose-file"):
            if i + 1 < len(argv):
                compose_file = argv[i + 1]
                i += 2
                continue
            break
        if arg == "--project-dir":
            if i + 1 < len(argv):
                project_dir = argv[i + 1]
                i += 2
                continue
            break
        if arg == "--log-level":
            if i + 1 < len(argv):
                log_level = argv[i + 1]
                i += 2
                continue
            break
        rest = argv[i:]
        break
    else:
        rest = []

    if rest and not rest[0].startswith("-") and rest[0] not in command_names:
        compose_args = list(rest)
        if compose_args and compose_args[0] == "docker":
            compose_args = compose_args[1:]
        if compose_args and compose_args[0] == "compose":
            compose_args = compose_args[1:]
        if not compose_args:
            compose_args = rest
        context = CLIContext.from_environ(
            project_dir=project_dir,
            compose_file=compose_file,
            log_level=log_level,
        )
        exit_code = passthrough_cmd.passthrough(context, compose_args)
        raise SystemExit(exit_code)

    app()


if __name__ == "__main__":
    run()
