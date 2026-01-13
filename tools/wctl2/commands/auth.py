from __future__ import annotations

import subprocess
from typing import List, Optional

import typer

from ..context import CLIContext
from ..docker import compose_exec
from ..util import quote_args

_PYTHON_BIN = "/opt/venv/bin/python"
_ISSUE_SCRIPT = "wepppy/weppcloud/_scripts/issue_auth_token.py"
_REVOKE_SCRIPT = "wepppy/weppcloud/_scripts/revoke_auth_token.py"


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


def _compose_exec_with_input(
    context: CLIContext,
    service: str,
    exec_command: str,
    *,
    input_data: str,
    check: bool = True,
) -> subprocess.CompletedProcess:
    args: List[str] = [
        "docker",
        "compose",
        *context.compose_base_args(),
        "exec",
        "-T",
        service,
        "bash",
        "-lc",
        exec_command,
    ]
    context.logger.info("docker compose exec %s bash -lc %s", service, exec_command)
    return subprocess.run(
        args,
        check=check,
        cwd=str(context.project_dir),
        env=context.environment,
        input=input_data,
        text=True,
    )


def register(app: typer.Typer) -> None:
    @app.command(
        "issue-auth-token",
        help="Issue a WEPPcloud JWT using the container config.",
    )
    def issue_auth_token(
        ctx: typer.Context,
        subject: str = typer.Argument(..., help="Subject claim (user or service identifier)."),
        scope: Optional[List[str]] = typer.Option(
            None,
            "--scope",
            "-s",
            help="Scope value (repeatable).",
        ),
        runs: Optional[str] = typer.Option(
            None,
            "--runs",
            help="Comma-separated list of run IDs to embed in the token.",
        ),
        audience: Optional[List[str]] = typer.Option(
            None,
            "--audience",
            "-a",
            help="Audience value (repeatable).",
        ),
        expires_in: Optional[int] = typer.Option(
            None,
            "--expires-in",
            help="Override token lifetime in seconds.",
        ),
        claim: Optional[List[str]] = typer.Option(
            None,
            "--claim",
            help="Additional claim in key=value form (repeatable).",
        ),
        json_out: bool = typer.Option(
            False,
            "--json",
            help="Output token and claims as JSON.",
        ),
    ) -> None:
        context = _context(ctx)
        args: List[str] = [_PYTHON_BIN, _ISSUE_SCRIPT, subject]
        if scope:
            for value in scope:
                args.extend(["--scope", value])
        if runs:
            args.extend(["--runs", runs])
        if audience:
            for value in audience:
                args.extend(["--audience", value])
        if expires_in is not None:
            args.extend(["--expires-in", str(expires_in)])
        if claim:
            for value in claim:
                args.extend(["--claim", value])
        if json_out:
            args.append("--json")

        command = _compose_python_command(args)
        result = compose_exec(context, "weppcloud", command, check=False)
        _exit_from_result(result)

    @app.command(
        "revoke-auth-token",
        help="Revoke a WEPPcloud JWT by writing its jti to the Redis denylist.",
    )
    def revoke_auth_token(
        ctx: typer.Context,
        token: Optional[str] = typer.Option(
            None,
            "--token",
            help="JWT string to revoke.",
        ),
        token_file: Optional[str] = typer.Option(
            None,
            "--token-file",
            help="Path to a file containing the JWT string.",
        ),
        jti: Optional[str] = typer.Option(
            None,
            "--jti",
            help="Token identifier to revoke (required if no token is supplied).",
        ),
        expires_at: Optional[int] = typer.Option(
            None,
            "--expires-at",
            help="Epoch timestamp of token expiration (when revoking by jti).",
        ),
        expires_in: Optional[int] = typer.Option(
            None,
            "--expires-in",
            help="TTL in seconds to use when revoking by jti.",
        ),
        audience: Optional[List[str]] = typer.Option(
            None,
            "--audience",
            "-a",
            help="Audience override used when validating the token.",
        ),
        subject: Optional[str] = typer.Option(
            None,
            "--subject",
            help="Subject value stored with the revocation record.",
        ),
        token_class: Optional[str] = typer.Option(
            None,
            "--token-class",
            help="token_class value stored with the revocation record.",
        ),
        reason: Optional[str] = typer.Option(
            None,
            "--reason",
            help="Reason stored with the revocation record.",
        ),
        json_out: bool = typer.Option(
            False,
            "--json",
            help="Output the revocation payload as JSON.",
        ),
    ) -> None:
        context = _context(ctx)
        if token and token_file:
            raise typer.BadParameter("--token and --token-file are mutually exclusive")

        args: List[str] = [_PYTHON_BIN, _REVOKE_SCRIPT]
        token_input = None
        if token:
            args.extend(["--token-file", "/dev/stdin"])
            token_input = token
        if token_file:
            args.extend(["--token-file", token_file])
        if jti:
            args.extend(["--jti", jti])
        if expires_at is not None:
            args.extend(["--expires-at", str(expires_at)])
        if expires_in is not None:
            args.extend(["--expires-in", str(expires_in)])
        if audience:
            for value in audience:
                args.extend(["--audience", value])
        if subject:
            args.extend(["--subject", subject])
        if token_class:
            args.extend(["--token-class", token_class])
        if reason:
            args.extend(["--reason", reason])
        if json_out:
            args.append("--json")

        command = _compose_python_command(args)
        if token_input is not None:
            result = _compose_exec_with_input(
                context,
                "weppcloud",
                command,
                input_data=token_input,
                check=False,
            )
        else:
            result = compose_exec(context, "weppcloud", command, check=False)
        _exit_from_result(result)
