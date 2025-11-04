from __future__ import annotations

import subprocess
from typing import List, Sequence

import typer

from ..context import CLIContext
from ..util import ensure_binary, prompt_tty

DOC_TOOL_HINT = "Install the markdown-doc toolkit to enable documentation workflows."
DOC_BENCH_HINT = "Install the markdown-doc bench binary to run documentation benchmarks."


def _context(ctx: typer.Context) -> CLIContext:
    context = ctx.obj
    if not isinstance(context, CLIContext):
        raise RuntimeError("CLIContext is not initialised.")
    return context


def _run_command(context: CLIContext, command: Sequence[str]) -> int:
    result = subprocess.run(
        list(command),
        cwd=str(context.project_dir),
        env=context.environment,
    )
    return result.returncode


def _has_help_flag(args: Sequence[str]) -> bool:
    return any(arg in ("-h", "--help", "-V", "--version") for arg in args)


def _prepare_doc_toc_args(args: List[str]) -> List[str]:
    forwarded: List[str] = []
    targets: List[str] = []
    positional_mode = False
    index = 0
    length = len(args)

    while index < length:
        arg = args[index]
        index += 1

        if positional_mode:
            targets.append(arg)
            forwarded.extend(["--path", arg])
            continue

        if arg == "--":
            positional_mode = True
            continue

        if arg == "--path":
            if index >= length:
                typer.echo("doc-toc requires a value after --path.", err=True)
                raise typer.Exit(1)
            value = args[index]
            index += 1
            if not value:
                typer.echo("doc-toc requires a non-empty value for --path.", err=True)
                raise typer.Exit(1)
            targets.append(value)
            forwarded.extend(["--path", value])
            continue

        if arg.startswith("--path="):
            value = arg[len("--path=") :]
            if not value:
                typer.echo("doc-toc requires a non-empty value for --path.", err=True)
                raise typer.Exit(1)
            targets.append(value)
            forwarded.append(arg)
            continue

        if arg.startswith("-"):
            forwarded.append(arg)
            continue

        targets.append(arg)
        forwarded.extend(["--path", arg])

    if not targets:
        typer.echo(
            "doc-toc requires at least one Markdown file or --path argument. Example: wctl doc-toc README.md --update",
            err=True,
        )
        raise typer.Exit(1)

    return forwarded


def _parse_doc_mv_args(args: List[str]) -> tuple[bool, bool, List[str]]:
    dry_run_only = False
    force = False
    doc_args: List[str] = []

    for arg in args:
        if arg == "--dry-run-only":
            dry_run_only = True
        elif arg == "--force":
            force = True
        else:
            doc_args.append(arg)

    if len(doc_args) < 2:
        typer.echo(
            "doc-mv requires source and destination arguments. Example: wctl doc-mv docs/src.md docs/dest.md",
            err=True,
        )
        raise typer.Exit(1)

    return dry_run_only, force, doc_args


def register(app: typer.Typer) -> None:
    @app.command(
        "doc-lint",
        context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    )
    def doc_lint(ctx: typer.Context) -> None:
        context = _context(ctx)
        ensure_binary("markdown-doc", DOC_TOOL_HINT)
        args = list(ctx.args)
        if not args:
            typer.echo("Running default: markdown-doc lint --staged --format json", err=True)
            args = ["--staged", "--format", "json"]
        exit_code = _run_command(context, ["markdown-doc", "lint", *args])
        raise typer.Exit(exit_code)

    @app.command(
        "doc-catalog",
        context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    )
    def doc_catalog(ctx: typer.Context) -> None:
        context = _context(ctx)
        ensure_binary("markdown-doc", DOC_TOOL_HINT)
        exit_code = _run_command(context, ["markdown-doc", "catalog", *ctx.args])
        raise typer.Exit(exit_code)

    @app.command(
        "doc-toc",
        context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    )
    def doc_toc(ctx: typer.Context) -> None:
        context = _context(ctx)
        ensure_binary("markdown-doc", DOC_TOOL_HINT)
        args = list(ctx.args)
        if _has_help_flag(args):
            exit_code = _run_command(context, ["markdown-doc", "toc", *args])
            raise typer.Exit(exit_code)
        forwarded = _prepare_doc_toc_args(args)
        exit_code = _run_command(context, ["markdown-doc", "toc", *forwarded])
        raise typer.Exit(exit_code)

    @app.command(
        "doc-mv",
        context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    )
    def doc_mv(ctx: typer.Context) -> None:
        context = _context(ctx)
        ensure_binary("markdown-doc", DOC_TOOL_HINT)
        args = list(ctx.args)
        dry_run_only, force, doc_args = _parse_doc_mv_args(args)

        dry_cmd = ["markdown-doc", "mv", "--dry-run", *doc_args]
        exit_code = _run_command(context, dry_cmd)
        if exit_code != 0:
            raise typer.Exit(exit_code)
        if dry_run_only:
            raise typer.Exit(0)

        if not force and not prompt_tty("Proceed with move? [y/N] "):
            raise typer.Exit(1)

        live_cmd = ["markdown-doc", "mv", *doc_args]
        exit_code = _run_command(context, live_cmd)
        raise typer.Exit(exit_code)

    @app.command(
        "doc-refs",
        context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    )
    def doc_refs(ctx: typer.Context) -> None:
        context = _context(ctx)
        ensure_binary("markdown-doc", DOC_TOOL_HINT)
        exit_code = _run_command(context, ["markdown-doc", "refs", *ctx.args])
        raise typer.Exit(exit_code)

    @app.command(
        "doc-bench",
        context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    )
    def doc_bench(ctx: typer.Context) -> None:
        context = _context(ctx)
        ensure_binary("markdown-doc-bench", DOC_BENCH_HINT)
        exit_code = _run_command(context, ["markdown-doc-bench", *ctx.args])
        raise typer.Exit(exit_code)
