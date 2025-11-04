from __future__ import annotations

import os
import shlex
import shutil
import sys
from pathlib import Path
from typing import Iterable, Optional, Sequence

import typer


def quote_args(args: Sequence[str]) -> str:
    return " ".join(shlex.quote(arg) for arg in args)


def ensure_binary(binary: str, hint: Optional[str] = None) -> None:
    if shutil.which(binary):
        return
    message = f"{binary} is required for this command."
    if hint:
        message = f"{message} {hint}"
    typer.echo(message, err=True)
    raise typer.Exit(127)


def prompt_tty(message: str) -> bool:
    tty_path = Path("/dev/tty")
    if not tty_path.exists() or not os.access(tty_path, os.R_OK | os.W_OK):
        typer.echo("Unable to access /dev/tty for confirmation. Use --force to bypass the prompt.", err=True)
        return False
    with tty_path.open("r+") as tty:
        tty.write(message)
        tty.flush()
        response = tty.readline().strip()
    if response.lower() == "y":
        return True
    typer.echo("Aborting move.", err=True)
    return False


def load_cookie(value: Optional[str], path: Optional[str]) -> Optional[str]:
    if path:
        cookie_path = Path(path)
        if not cookie_path.exists():
            raise typer.BadParameter(f"Cookie file not found: {cookie_path}")
        return cookie_path.read_text().strip()
    if value:
        return value.strip()
    return None
