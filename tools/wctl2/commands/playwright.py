from __future__ import annotations

import json
import shlex
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import re
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, List, Literal, Optional
from uuid import uuid4

import typer

from ..context import CLIContext
if TYPE_CHECKING:
    EnvironmentPreset = Literal["local", "local-direct", "dev", "staging", "prod", "custom"]
    SuitePreset = Literal["full", "smoke", "controllers", "mods-menu"]
else:
    EnvironmentPreset = str
    SuitePreset = str

_ENV_URLS = {
    "dev": "https://wc.bearhive.duckdns.org/weppcloud",
    "local": "http://localhost:8080",
    "local-direct": "http://localhost:8000/weppcloud",
}

DEFAULT_PROJECT = "runs0"
DEFAULT_REPORT_PATH = "playwright-report"

SUITE_PATTERNS: dict[str, Optional[str]] = {
    "full": None,
    "smoke": "page load",
    "controllers": "controller regression",
    "theme-metrics": "theme contrast metrics",
    "mods-menu": "run header mods menu",
}

RUN_ID_PATTERN = re.compile(r"/runs/([^/]+)/")


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


def _profile_root(context: CLIContext) -> Path:
    candidate = context.env_value("PROFILE_PLAYBACK_ROOT") or context.environment.get("PROFILE_PLAYBACK_ROOT")
    return Path(candidate or "/workdir/wepppy-test-engine-data/profiles")


def _playback_run_root(context: CLIContext) -> Path:
    base = context.env_value("PROFILE_PLAYBACK_BASE") or context.environment.get("PROFILE_PLAYBACK_BASE")
    base_path = Path(base or "/workdir/wepppy-test-engine-data/playback")
    override = context.env_value("PROFILE_PLAYBACK_RUN_ROOT") or context.environment.get("PROFILE_PLAYBACK_RUN_ROOT")
    return Path(override) if override else base_path / "runs"


def _read_active_config(run_dir: Path) -> str:
    marker = run_dir / "active_config.txt"
    if marker.exists():
        value = marker.read_text(encoding="utf-8").strip()
        if value:
            return value
    return "0"


def _detect_profile_run_id(profile_root: Path) -> str:
    events_path = profile_root / "capture" / "events.jsonl"
    if not events_path.exists():
        raise typer.Exit(f"[wctl2] Capture log missing: {events_path}")

    with events_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            endpoint = str(payload.get("endpoint") or payload.get("path") or "")
            match = RUN_ID_PATTERN.search(endpoint)
            if match:
                return match.group(1)
    raise typer.Exit(f"[wctl2] Unable to detect run id from {events_path}")


def _clone_profile_run(context: CLIContext, profile: str) -> dict:
    profile_root = _profile_root(context) / profile
    if not profile_root.exists():
        raise typer.Exit(f"[wctl2] Profile not found: {profile_root}")

    source_run_dir = profile_root / "run"
    if not source_run_dir.exists():
        raise typer.Exit(f"[wctl2] Profile run snapshot missing: {source_run_dir}")

    run_id = _detect_profile_run_id(profile_root)
    sandbox_uuid = uuid4().hex
    sandbox_run_id = f"profile;;tmp;;{sandbox_uuid}"

    run_root = _playback_run_root(context)
    run_root.mkdir(parents=True, exist_ok=True)
    sandbox_dir = run_root / sandbox_uuid
    shutil.rmtree(sandbox_dir, ignore_errors=True)
    shutil.copytree(source_run_dir, sandbox_dir)

    config_slug = _read_active_config(sandbox_dir)
    return {
        "run_id": sandbox_run_id,
        "config": config_slug,
        "run_dir": sandbox_dir,
    }


def _cleanup_cloned_run(run_dir: Path, keep_run: bool) -> None:
    if keep_run:
        typer.echo(f"[wctl2] Keeping cloned profile run at {run_dir}")
        return
    shutil.rmtree(run_dir, ignore_errors=True)


def _build_run_path(base_url: str, run_id: str, config_slug: str) -> str:
    base = base_url.rstrip("/")
    return f"{base}/runs/{run_id}/{config_slug}/"


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
            help="Suite preset: full (default), smoke, controllers, theme-metrics, mods-menu.",
        ),
        profile: Optional[str] = typer.Option(
            None,
            "--profile",
            help="Replay the specified profile via profile-playback before running tests.",
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
        report_path: Optional[str] = typer.Option(
            None,
            "--report-path",
            help="Destination directory for HTML reports (implies report generation without opening).",
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

        if suite_value not in SUITE_PATTERNS:
            typer.echo(f"[wctl2] Unknown suite preset '{suite}'.", err=True)
            raise typer.Exit(1)

        suite_pattern = SUITE_PATTERNS[suite_value]
        overrides_json = _build_overrides_json(overrides)

        resolved_url = _resolve_base_url(context, effective_env, base_url)
        _ping_test_support(resolved_url)

        profile_slug = profile.strip() if profile else None
        if profile_slug and overrides_json:
            typer.echo("[wctl2] Warning: --overrides ignored when using --profile.", err=True)

        project_value = _resolve_project(context, effective_env, project)
        report_output_path = report_path or DEFAULT_REPORT_PATH
        report_requested = report or report_path is not None

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
        if report_requested:
            cli_args.extend(["--reporter", "html", "--output", report_output_path])

        if playwright_args:
            cli_args.extend(shlex.split(playwright_args))

        static_src = context.project_dir / "wepppy" / "weppcloud" / "static-src"
        npm_cmd = ["npm", "run", "test:playwright", "--", *cli_args]

        typer.echo(f"[wctl2] Running Playwright tests against {resolved_url}")

        cloned_run: Optional[dict] = None
        if profile_slug:
            cloned_run = _clone_profile_run(context, profile_slug)
            run_path = _build_run_path(resolved_url, cloned_run["run_id"], cloned_run["config"])
            env_vars["SMOKE_RUN_PATH"] = run_path
            env_vars["SMOKE_RUN_CONFIG"] = cloned_run["config"]
            env_vars["SMOKE_CREATE_RUN"] = "false"
            typer.echo(f"[wctl2] Using profile '{profile_slug}' run {cloned_run['run_id']} ({run_path})")

        final_config = env_vars.get("SMOKE_RUN_CONFIG", config)
        typer.echo(
            f"[wctl2] Config: {final_config}, Project: {project_value}, Workers: {effective_workers}, Suite: {suite_value}"
        )

        try:
            result = subprocess.run(
                npm_cmd,
                cwd=str(static_src),
                env=env_vars,
            )
        finally:
            if cloned_run:
                _cleanup_cloned_run(Path(cloned_run["run_dir"]), keep_run)

        if report and result.returncode == 0:
            typer.echo(f"[wctl2] Opening report from {report_output_path}")
            subprocess.run(
                ["npx", "playwright", "show-report", report_output_path],
                cwd=str(static_src),
                env=env_vars,
            )

        raise typer.Exit(result.returncode)
