from __future__ import annotations

import shlex
import subprocess
from typing import Iterable, List, Mapping, Sequence

from .context import CLIContext


def _format_args(args: Iterable[str]) -> str:
    return " ".join(shlex.quote(str(arg)) for arg in args)


def _compose_prefix(context: CLIContext) -> List[str]:
    return [
        "docker",
        "compose",
        *context.compose_base_args(),
    ]


def run_compose(context: CLIContext, args: Sequence[str], check: bool = True) -> subprocess.CompletedProcess:
    command = _compose_prefix(context) + list(args)
    context.logger.info("docker compose %s", _format_args(args))
    return subprocess.run(
        command,
        check=check,
        cwd=str(context.project_dir),
        env=context.environment,
    )


def compose_exec(
    context: CLIContext,
    service: str,
    exec_command: str,
    *,
    tty: bool = True,
    check: bool = True,
) -> subprocess.CompletedProcess:
    exec_args: List[str] = ["exec"]
    if not tty:
        exec_args.append("-T")
    exec_args.extend([service, "bash", "-lc", exec_command])
    command = _compose_prefix(context) + exec_args
    context.logger.info("docker compose exec %s bash -lc %s", service, exec_command)
    return subprocess.run(
        command,
        check=check,
        cwd=str(context.project_dir),
        env=context.environment,
    )
