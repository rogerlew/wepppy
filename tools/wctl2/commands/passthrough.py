from __future__ import annotations

from typing import Sequence

import typer

from ..context import CLIContext
from ..docker import run_compose


def passthrough(context: CLIContext, args: Sequence[str]) -> int:
    if not args:
        typer.echo("No command provided; specify a docker compose subcommand.", err=True)
        return 1
    result = run_compose(context, list(args), check=False)
    return result.returncode
