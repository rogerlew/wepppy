from __future__ import annotations

import json
import shlex
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from typing import TYPE_CHECKING, List, Literal, Optional

import typer

from ..context import CLIContext

if TYPE_CHECKING:
    EnvironmentPreset = Literal["local", "local-direct", "dev", "staging", "prod", "custom"]
    SuitePreset = Literal["full", "smoke", "controllers"]
else:
    EnvironmentPreset = str
    SuitePreset = str

_ENV_URLS = {
    "dev": "https://wc.bearhive.duckdns.org/weppcloud",
    "local": "http://localhost:8080",
    "local-direct": "http://localhost:8000/weppcloud",
}

DEFAULT_PROJECT = "runs0"

SUITE_PATTERNS: dict[str, Optional[str]] = {
    "full": None,
    "smoke": "page load",
    "controllers": "controller regression",
}


def _context(ctx: typer.Context) -> CLIContext:
    context = ctx.obj
    if not isinstance(context, CLIContext):
        raise RuntimeError("CLIContext is not initialised.")
    return context


def _resolve_base_url(context: CLIContext, env: EnvironmentPreset, base_url: Optional[str]) -> str:
    """
    Determine which base URL to use, prioritising explicit overrides and
    falling back to preset defaults or environment-defined overrides.
    """

    if base_url:
        return base_url

    env = str(env).lower()

    if env == "staging":
        url = context.env_value("PLAYWRIGHT_STAGING_URL")
        if not url:
            typer.echo("PLAYWRIGHT_STAGING_URL not set in environment.", err=True)
            raise typer.Exit(1)
        return url

    if env == "prod":
        url = context.env_value("PLAYWRIGHT_PROD_URL")
        if not url:
            typer.echo("PLAYWRIGHT_PROD_URL not set in environment.", err=True)
            raise typer.Exit(1)
        return url

    if env == "custom":
        typer.echo("--env=custom requires --base-url to be specified.", err=True)
        raise typer.Exit(1)

    env_var_name = f"PLAYWRIGHT_{env.upper().replace('-', '_')}_URL"
    override = context.env_value(env_var_name)
    if override:
        return override

    return _ENV_URLS.get(env, _ENV_URLS["dev"])


def _resolve_project(
    context: CLIContext,
    env: EnvironmentPreset,
    project: Optional[str],
) -> str:
    if project:
        return project

    env_var_name = f"PLAYWRIGHT_{str(env).upper().replace('-', '_')}_PROJECT"
    override = context.env_value(env_var_name)
    if override:
        return override
    return DEFAULT_PROJECT


def _ping_test_support(base_url: str) -> None:
    """Ensure /tests/api/ping is reachable before running Playwright."""

    prefix = base_url if base_url.endswith("/") else f"{base_url}/"
    ping_url = urllib.parse.urljoin(prefix, "tests/api/ping")
    try:
        request = urllib.request.Request(ping_url, method="GET")
        with urllib.request.urlopen(request, timeout=5) as response:  # nosec B310 - controlled URL
            if response.status != 200:
                typer.echo(
                    f"[wctl2] Test support endpoint returned {response.status}. "
                    "Ensure TEST_SUPPORT_ENABLED=true in backend.",
                    err=True,
                )
                raise typer.Exit(1)
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        typer.echo(
            f"[wctl2] Cannot reach {ping_url}: {reason}. "
            "Is the backend running?",
            err=True,
        )
        raise typer.Exit(1)
    except Exception as exc:  # pragma: no cover - defensive catch-all
        typer.echo(f"[wctl2] Ping check failed: {exc}", err=True)
        raise typer.Exit(1)


def _build_overrides_json(overrides: List[str]) -> Optional[str]:
    if not overrides:
        return None

    payload: dict[str, str] = {}
    for item in overrides:
        if "=" not in item:
            typer.echo(f"[wctl2] Invalid override '{item}'. Use key=value syntax.", err=True)
            raise typer.Exit(1)
        key, value = item.split("=", 1)
        payload[key] = value
    return json.dumps(payload)


def register(app: typer.Typer) -> None:
    @app.command(
        "run-playwright",
        help="Run Playwright smoke tests against WEPPcloud environments.",
    )
    def run_playwright(
        ctx: typer.Context,
        env: EnvironmentPreset = typer.Option(
            "dev",
            "--env",
            "-e",
            help="Environment preset (dev, local, local-direct, staging, prod, custom).",
        ),
        base_url: Optional[str] = typer.Option(
            None,
            "--base-url",
            help="Override base URL (implies --env=custom).",
        ),
        config: str = typer.Option(
            "disturbed9002_wbt",
            "--config",
            "-c",
            help="WEPPcloud config slug for provisioning.",
        ),
        run_path: Optional[str] = typer.Option(
            None,
            "--run-path",
            help="Reuse existing run path (skips provisioning).",
        ),
        create_run: bool = typer.Option(
            True,
            "--create-run/--no-create-run",
            help="Auto-provision run via test-support API.",
        ),
        keep_run: bool = typer.Option(
            False,
            "--keep-run",
            help="Preserve provisioned run after tests complete.",
        ),
        run_root: Optional[str] = typer.Option(
            None,
            "--run-root",
            help="Optional root directory for provisioning.",
        ),
        suite: SuitePreset = typer.Option(
            "full",
            "--suite",
            "-s",
            help="Suite preset: full (default), smoke, controllers.",
        ),
        project: Optional[str] = typer.Option(
            None,
            "--project",
            "-p",
            show_default=DEFAULT_PROJECT,
            help="Playwright project name.",
        ),
        workers: int = typer.Option(
            1,
            "--workers",
            "-w",
            min=1,
            help="Number of parallel workers.",
        ),
        headed: bool = typer.Option(
            False,
            "--headed",
            help="Run in headed mode (visible browser).",
        ),
        grep: Optional[str] = typer.Option(
            None,
            "--grep",
            "-g",
            help="Filter tests by pattern.",
        ),
        debug: bool = typer.Option(
            False,
            "--debug",
            help="Run Playwright in debug mode.",
        ),
        ui: bool = typer.Option(
            False,
            "--ui",
            help="Launch Playwright UI mode.",
        ),
        report: bool = typer.Option(
            False,
            "--report",
            help="Generate HTML report and open it after a successful run.",
        ),
        report_path: str = typer.Option(
            "playwright-report",
            "--report-path",
            help="Destination directory for HTML reports.",
        ),
        playwright_args: Optional[str] = typer.Option(
            None,
            "--playwright-args",
            help="Additional Playwright CLI arguments (quoted string).",
        ),
        overrides: List[str] = typer.Option(
            [],
            "--overrides",
            help="Repeatable key=value overrides converted to SMOKE_RUN_OVERRIDES JSON.",
        ),
    ) -> None:
        """
        Run Playwright smoke tests against WEPPcloud environments.
        """

        context = _context(ctx)
        env_value = str(env).lower()
        suite_value = str(suite).lower()

        effective_env = "custom" if base_url else env_value
        resolved_url = _resolve_base_url(context, effective_env, base_url)
        _ping_test_support(resolved_url)

        if suite_value not in SUITE_PATTERNS:
            typer.echo(f"[wctl2] Unknown suite preset '{suite}'.", err=True)
            raise typer.Exit(1)

        suite_pattern = SUITE_PATTERNS[suite_value]
        overrides_json = _build_overrides_json(overrides)

        project_value = _resolve_project(context, effective_env, project)

        env_vars = dict(context.environment)
        env_vars["SMOKE_BASE_URL"] = resolved_url
        env_vars["SMOKE_RUN_CONFIG"] = config
        env_vars["SMOKE_HEADLESS"] = "false" if headed else "true"
        env_vars["SMOKE_KEEP_RUN"] = "true" if keep_run else "false"

        final_create_run = create_run and not run_path
        env_vars["SMOKE_CREATE_RUN"] = "true" if final_create_run else "false"

        if run_path:
            env_vars["SMOKE_RUN_PATH"] = run_path
        if run_root:
            env_vars["SMOKE_RUN_ROOT"] = run_root
        if overrides_json:
            env_vars["SMOKE_RUN_OVERRIDES"] = overrides_json

        effective_workers = 1 if headed else workers
        cli_args: List[str] = ["--project", project_value, "--workers", str(effective_workers)]

        active_grep = grep or suite_pattern
        if active_grep:
            cli_args.extend(["--grep", active_grep])
        if debug:
            cli_args.append("--debug")
        if ui:
            cli_args.append("--ui")
        if report:
            cli_args.extend(["--reporter", "html", "--output", report_path])

        if playwright_args:
            cli_args.extend(shlex.split(playwright_args))

        static_src = context.project_dir / "wepppy" / "weppcloud" / "static-src"
        npm_cmd = ["npm", "run", "test:playwright", "--", *cli_args]

        typer.echo(f"[wctl2] Running Playwright tests against {resolved_url}")
        typer.echo(
            f"[wctl2] Config: {config}, Project: {project_value}, Workers: {effective_workers}, Suite: {suite_value}"
        )

        result = subprocess.run(
            npm_cmd,
            cwd=str(static_src),
            env=env_vars,
        )

        if report and result.returncode == 0:
            typer.echo(f"[wctl2] Opening report from {report_path}")
            subprocess.run(
                ["npx", "playwright", "show-report", report_path],
                cwd=str(static_src),
                env=env_vars,
            )

        raise typer.Exit(result.returncode)
