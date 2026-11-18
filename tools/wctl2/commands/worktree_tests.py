"""Run candidate tests without remounting the shared development service."""
from __future__ import annotations

from enum import Enum
from pathlib import Path
import posixpath
import shlex
import subprocess
from typing import Mapping, Optional
import uuid

import typer

from ..checkout_identity import checked_test_command, requested_checkout
from ..context import CLIContext
from ..docker import run_compose


class Profile(str, Enum):
    broad = "broad"
    python = "python"
    browser = "browser"
    native = "native"
    database = "database"


def bind(source: Path, target: str, *, readonly: bool = True) -> list[str]:
    source = source.resolve(strict=True)
    # Compose run uses colon-delimited volumes; reject ambiguous mount fields.
    # Resolve existing sources first so Docker cannot create a missing donor.
    if any(char in str(source) or char in target for char in (':', ',')):
        raise ValueError("Mount paths must not contain colons or commas")
    return ["--volume", f"{source}:{target}" + (":ro" if readonly else "")]


def mounts(checkout: Path, runtime_root: Optional[Path], parsers: dict[str, Optional[Path]],
           environment: Mapping[str, str]) -> list[str]:
    result = bind(checkout, "/workdir/wepppy", readonly=False)
    common = subprocess.run(
        ["git", "-C", str(checkout), "rev-parse", "--path-format=absolute", "--git-common-dir"],
        check=True, capture_output=True, text=True, timeout=10,
        env={key: value for key, value in environment.items() if not key.startswith("GIT_")},
    ).stdout.strip()
    result += bind(Path(common), common)
    if runtime_root is not None:
        # Mount only dependency assets, not another checkout's production source.
        static = runtime_root.resolve(strict=True) / "wepppy/weppcloud/static-src"
        for name in ("package.json", "package-lock.json", "node_modules", ".playwright-browsers"):
            result += bind(static / name, f"/opt/wctl-runtime/{name}")
        result += bind(static / "node_modules", "/workdir/wepppy/wepppy/weppcloud/static-src/node_modules")
        result += bind(static / ".playwright-browsers", "/workdir/wepppy/wepppy/weppcloud/static-src/.playwright-browsers")
    for name, path in parsers.items():
        if path is not None:
            result += bind(path, f"/usr/local/bin/{name}")
            result += bind(Path(f"{path}.json"), f"/usr/local/bin/{name}.json")
    return result


def register(app: typer.Typer) -> None:
    @app.command("run-pytest-worktree", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
    def run_tests(
        ctx: typer.Context,
        checkout: Optional[Path] = typer.Option(None, help="Candidate checkout; defaults to caller checkout."),
        profile: Profile = typer.Option(Profile.broad, help="Prerequisites to check; broad is required for the full suite."),
        runtime_root: Optional[Path] = typer.Option(None, help="Explicit compatible checkout providing read-only Node/browser dependencies."),
        shape_parser: Optional[Path] = typer.Option(None, help="Existing shape_parser_cli binary with adjacent .json provenance."),
        geoparquet_parser: Optional[Path] = typer.Option(None, help="Existing geoparquet_parser_cli binary with adjacent .json provenance."),
        preflight_only: bool = typer.Option(False, help="Check readiness without starting pytest."),
    ) -> None:
        context: CLIContext = ctx.obj
        args = list(ctx.args) or ["tests"]
        if profile != Profile.broad and any(posixpath.normpath(arg) in {"tests", ".", "/workdir/wepppy", "/workdir/wepppy/tests"} for arg in args):
            raise typer.BadParameter("Full-suite selection requires --profile broad; use a narrower test path for other profiles.")
        root = checkout.resolve() if checkout else requested_checkout(
            context.project_dir, context.environment.get("WCTL_CALLER_CWD"),
            explicit=False,  # --project-dir selects Compose configuration; --checkout selects source.
        )
        receipt = f".wctl-test-runs/{uuid.uuid4().hex}/receipt.json"
        invocation = ["/opt/venv/bin/python", "-m", "tools.wctl2.test_runtime", "--profile", profile.value, "--receipt", receipt]
        if runtime_root:
            invocation.append("--borrowed-node")
        if preflight_only:
            invocation.append("--preflight-only")
        invocation += ["--", *args]
        command = "cd /workdir/wepppy && PYTHONPATH=/workdir/wepppy " + shlex.join(invocation)
        try:
            volume_args = mounts(root, runtime_root, {"shape_parser_cli": shape_parser, "geoparquet_parser_cli": geoparquet_parser}, context.environment)
            with checked_test_command(root, command) as checked:
                typer.echo(f"Candidate: {root}\nReceipt: {root / receipt}")
                result = run_compose(context, [
                    "run", "--rm", "--no-deps", "--pull", "never", "-T", *volume_args,
                    "--entrypoint", "/bin/bash", "weppcloud", "-lc", checked,
                ], check=False)
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            typer.echo(f"WCTL_WORKTREE_NOT_READY: {type(exc).__name__}; verify checkout, Git metadata and supplied runtime paths. No successful test result recorded.", err=True)
            raise typer.Exit(2) from None
        raise typer.Exit(result.returncode)
