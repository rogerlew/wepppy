# wctl2 Playwright Command Specification

## Overview

The `wctl2 run-playwright` command encapsulates the complexity of running Playwright smoke tests against various WEPPcloud environments (local dev, staging, production) while maintaining flexibility for CI/CD pipelines and developer workflows.

## Goals

1. **Simplify execution**: Reduce the verbose command invocation to a single concise command
2. **Environment flexibility**: Support local dev, remote staging, and production testing
3. **Sensible defaults**: Work out-of-the-box for common use cases while allowing overrides
4. **CI/CD ready**: Support both interactive development and automated pipeline usage
5. **Future-proof**: Accommodate profile-based testing and additional test suites

## Command Design

### Basic Usage

```bash
# Simplest invocation (uses defaults: dev domain, disturbed9002_wbt config)
wctl2 run-playwright

# Test against local docker-compose stack
wctl2 run-playwright --env local

# Test against staging with custom config
wctl2 run-playwright --env staging --config ltcalibration_wb

# Use an existing run (skip provisioning)
wctl2 run-playwright --run-path /weppcloud/runs/my-run-id/config-name/

# Full control with overrides
wctl2 run-playwright \
  --base-url https://custom.domain.com/weppcloud \
  --config disturbed9002_wbt \
  --create-run \
  --workers 2 \
  --project runs0 \
  --headed
```

### Named Environments

Pre-configured environment presets for common testing targets:

| Env Name | Base URL | Purpose |
|----------|----------|---------|
| `dev` (default) | `https://wc.bearhive.duckdns.org/weppcloud` | Dev server (pfSense/HAProxy, TLS) |
| `local` | `http://localhost:8080` | Local docker-compose dev stack via Caddy |
| `local-direct` | `http://localhost:8000/weppcloud` | Direct Flask app (no Caddy proxy) |
| `staging` | _(from env var `PLAYWRIGHT_STAGING_URL`)_ | Staging environment |
| `prod` | _(from env var `PLAYWRIGHT_PROD_URL`)_ | Production (requires explicit opt-in) |
| `custom` | _(requires `--base-url`)_ | User-specified URL |

Environment URLs can be overridden via:
1. `.env` file entries: `PLAYWRIGHT_DEV_URL`, `PLAYWRIGHT_STAGING_URL`, `PLAYWRIGHT_PROD_URL`
2. Host environment variables (merged by `CLIContext`)
3. Command-line `--base-url` flag (highest precedence)

### Command-Line Options

#### Environment & Target

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--env`, `-e` | Choice | `dev` | Named environment preset (dev, local, local-direct, staging, prod, custom) |
| `--base-url` | String | _(from env)_ | Override base URL (auto-selects `custom` env) |
| `--config`, `-c` | String | `disturbed9002_wbt` | WEPPcloud config slug for provisioning |
| `--run-path` | String | _(none)_ | Reuse existing run path (automatically disables provisioning) |
| `--create-run / --no-create-run` | Flag | `True` | Auto-provision runs via `/tests/api/create-run` (ignored if `--run-path` set) |
| `--keep-run` | Flag | `False` | Preserve provisioned run after tests complete |
| `--run-root` | Path | _(none)_ | Optional root directory for run provisioning |

#### Playwright Execution

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--project`, `-p` | String | `runs0` | Playwright project name from config |
| `--workers`, `-w` | Int | `1` | Number of parallel workers |
| `--headed` | Flag | `False` | Run in headed mode (visible browser) |
| `--grep`, `-g` | String | _(none)_ | Filter tests by pattern |
| `--debug` | Flag | `False` | Run Playwright in debug mode |
| `--ui` | Flag | `False` | Launch Playwright UI mode |
| `--report` | Flag | `False` | Open HTML report after test run |

#### Pass-through

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--playwright-args` | String | _(none)_ | Additional Playwright CLI arguments (quoted strings preserved via shlex) |

### Environment Variable Mapping

The command sets these environment variables before invoking `npm run test:playwright`:

| wctl2 Option | Env Var | Playwright Config Reads |
|--------------|---------|-------------------------|
| `--base-url` / `--env` | `SMOKE_BASE_URL` | `process.env.SMOKE_BASE_URL` |
| `--create-run` (if no `--run-path`) | `SMOKE_CREATE_RUN` | `process.env.SMOKE_CREATE_RUN` |
| `--run-path` | `SMOKE_RUN_PATH` | `process.env.SMOKE_RUN_PATH` |
| _(auto: `--run-path` present)_ | `SMOKE_CREATE_RUN` | Set to `"false"` when `--run-path` provided |
| `--config` | `SMOKE_RUN_CONFIG` | `process.env.SMOKE_RUN_CONFIG` |
| `--keep-run` | `SMOKE_KEEP_RUN` | `process.env.SMOKE_KEEP_RUN` |
| `--run-root` | `SMOKE_RUN_ROOT` | `process.env.SMOKE_RUN_ROOT` |
| `--headed` | `SMOKE_HEADLESS` | `process.env.SMOKE_HEADLESS !== 'false'` |
| _(computed)_ | `SMOKE_RUN_OVERRIDES` | `process.env.SMOKE_RUN_OVERRIDES` (JSON) |

## Implementation Plan

### Module Structure

```
tools/wctl2/commands/
  playwright.py              # New module
```

### Registration

Update `tools/wctl2/commands/__init__.py`:

```python
from . import doc, maintenance, npm, playback, playwright, python_tasks

def register(app: typer.Typer) -> None:
    # ... existing registrations ...
    playwright.register(app)
```

### Core Implementation

```python
from __future__ import annotations

import json
import shlex
import subprocess
from pathlib import Path
from typing import Literal, Optional

import typer

from ..context import CLIContext

EnvironmentPreset = Literal["local", "local-direct", "dev", "staging", "prod", "custom"]

# Environment URL mappings
_ENV_URLS = {
    "dev": "https://wc.bearhive.duckdns.org/weppcloud",
    "local": "http://localhost:8080",
    "local-direct": "http://localhost:8000/weppcloud",
}


def _context(ctx: typer.Context) -> CLIContext:
    context = ctx.obj
    if not isinstance(context, CLIContext):
        raise RuntimeError("CLIContext is not initialised.")
    return context


def _resolve_base_url(
    context: CLIContext,
    env: EnvironmentPreset,
    base_url: Optional[str],
) -> str:
    """Resolve base URL from preset, env vars, or explicit override."""
    if base_url:
        return base_url
    
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
    
    # Check for env-specific override in .env or host env
    env_var_name = f"PLAYWRIGHT_{env.upper().replace('-', '_')}_URL"
    override = context.env_value(env_var_name)
    if override:
        return override
    
    return _ENV_URLS.get(env, _ENV_URLS["dev"])


def register(app: typer.Typer) -> None:
    @app.command(
        "run-playwright",
        help="Run Playwright smoke tests against WEPPcloud environments.",
    )
    def run_playwright(
        ctx: typer.Context,
        # Environment & Target
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
            help="Auto-provision run via test API.",
        ),
        keep_run: bool = typer.Option(
            False,
            "--keep-run",
            help="Preserve provisioned run after tests.",
        ),
        run_root: Optional[str] = typer.Option(
            None,
            "--run-root",
            help="Optional root directory for provisioning.",
        ),
        # Playwright Execution
        project: str = typer.Option(
            "runs0",
            "--project",
            "-p",
            help="Playwright project name.",
        ),
        workers: int = typer.Option(
            1,
            "--workers",
            "-w",
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
            help="Run in debug mode.",
        ),
        ui: bool = typer.Option(
            False,
            "--ui",
            help="Launch Playwright UI mode.",
        ),
        report: bool = typer.Option(
            False,
            "--report",
            help="Open HTML report after run.",
        ),
        # Pass-through
        playwright_args: Optional[str] = typer.Option(
            None,
            "--playwright-args",
            help="Additional Playwright CLI arguments.",
        ),
    ) -> None:
        """
        Run Playwright smoke tests against WEPPcloud.
        
        Examples:
          wctl2 run-playwright
          wctl2 run-playwright --env dev --config ltcalibration_wb
          wctl2 run-playwright --base-url https://custom.com/weppcloud --headed
        
        Note: When --run-path is provided, provisioning is automatically disabled
        (SMOKE_CREATE_RUN=false) regardless of --create-run flag.
        """
        context = _context(ctx)
        
        # Resolve effective environment
        effective_env = "custom" if base_url else env
        resolved_url = _resolve_base_url(context, effective_env, base_url)
        
        # Build environment variables
        test_env = dict(context.environment)
        test_env["SMOKE_BASE_URL"] = resolved_url
        test_env["SMOKE_RUN_CONFIG"] = config
        test_env["SMOKE_HEADLESS"] = "false" if headed else "true"
        test_env["SMOKE_KEEP_RUN"] = "true" if keep_run else "false"
        
        # When run_path is provided, disable auto-provisioning
        if run_path:
            test_env["SMOKE_RUN_PATH"] = run_path
            test_env["SMOKE_CREATE_RUN"] = "false"
        else:
            test_env["SMOKE_CREATE_RUN"] = "true" if create_run else "false"
        
        if run_root:
            test_env["SMOKE_RUN_ROOT"] = run_root
        
        # Build Playwright command
        pw_args = ["--project", project, "--workers", str(workers)]
        
        if grep:
            pw_args.extend(["--grep", grep])
        if debug:
            pw_args.append("--debug")
        if ui:
            pw_args.append("--ui")
        if report:
            pw_args.extend(["--reporter", "html"])
        
        if playwright_args:
            # Use shlex.split() to properly handle quoted arguments
            pw_args.extend(shlex.split(playwright_args))
        
        # Execute via npm
        static_src = context.project_dir / "wepppy" / "weppcloud" / "static-src"
        npm_cmd = ["npm", "run", "test:playwright", "--", *pw_args]
        
        typer.echo(f"[wctl2] Running Playwright tests against {resolved_url}")
        typer.echo(f"[wctl2] Config: {config}, Project: {project}, Workers: {workers}")
        
        result = subprocess.run(
            npm_cmd,
            cwd=str(static_src),
            env=test_env,
        )
        
        if report and result.returncode == 0:
            # Open HTML report using npx playwright show-report
            report_cmd = ["npx", "playwright", "show-report"]
            subprocess.run(report_cmd, cwd=str(static_src), env=test_env)
        
        raise typer.Exit(result.returncode)
```

## Usage Examples

### Development Workflows

```bash
# Default: test against dev server (quick smoke check)
wctl2 run-playwright

# Test against local docker-compose stack
wctl2 run-playwright --env local

# Debug failing test locally with visible browser
wctl2 run-playwright --env local --headed --grep "landuse controller"

# Interactive Playwright UI
wctl2 run-playwright --ui

# Test with custom config
wctl2 run-playwright --config ltcalibration_wb

# Reuse existing run for faster iteration
wctl2 run-playwright --run-path /weppcloud/runs/my-test-run/disturbed9002_wbt/

# Keep run for manual inspection
wctl2 run-playwright --keep-run

# Generate and open HTML report after successful run
wctl2 run-playwright --report
```

### CI/CD Pipelines

```bash
# Full suite against staging
wctl2 run-playwright --env staging --workers 4

# Specific test subset for PR checks
wctl2 run-playwright --grep "controller regression" --workers 2

# Production smoke test (pre-configured URL)
wctl2 run-playwright --env prod --config dev_unit_1

# Custom deployment target
wctl2 run-playwright \
  --base-url https://pr-123.weppcloud-preview.dev/weppcloud \
  --config disturbed9002_wbt
```

### Performance Testing

```bash
# Test with different storage backends
wctl2 run-playwright --run-root /dev/shm/weppcloud_smoke

# Parallel execution for speed
wctl2 run-playwright --workers 8 --no-create-run
```

## Configuration Files

### .env Support

Environment-specific URLs can be pre-configured in `docker/.env` or host `.env`:

```bash
# docker/.env or host override
PLAYWRIGHT_DEV_URL=https://wc.bearhive.duckdns.org/weppcloud
PLAYWRIGHT_STAGING_URL=https://staging.weppcloud.example.com/weppcloud
PLAYWRIGHT_PROD_URL=https://weppcloud.example.com/weppcloud
```

### Playwright Config Integration

The command exports environment variables that `playwright.config.mjs` already reads:

```javascript
// playwright.config.mjs (existing)
export default defineConfig({
  use: {
    baseURL: process.env.SMOKE_BASE_URL || 'http://localhost:8080',
    headless: process.env.SMOKE_HEADLESS !== 'false',
    // ...
  }
});
```

No changes needed to existing Playwright configuration.

## Future Enhancements

### Profile-Based Testing

Support for profile YAML files (similar to `run-test-profile`):

```bash
# Run profile-defined test suite
wctl2 run-playwright --profile quick

# Override profile settings
wctl2 run-playwright --profile rattlesnake --env dev
```

Profile example (`tests/smoke/profiles/quick.yml`):
```yaml
name: quick
description: Small US watershed for fast health checks
env:
  SMOKE_RUN_CONFIG: dev_unit_1
  SMOKE_RUN_OVERRIDES:
    general:dem_db: ned1/2016
playwright:
  project: runs0
  workers: 1
  timeout: 120000
```

### Test Suite Selection

```bash
# Run specific test suite
wctl2 run-playwright --suite smoke
wctl2 run-playwright --suite regression
wctl2 run-playwright --suite e2e

# Multiple suites
wctl2 run-playwright --suite smoke,regression
```

### Browser Selection

```bash
# Test across browsers
wctl2 run-playwright --browser chromium,firefox,webkit

# Mobile emulation
wctl2 run-playwright --device "iPhone 13"
```

### Artifact Management

```bash
# Auto-upload artifacts on failure
wctl2 run-playwright --upload-artifacts s3://bucket/playwright-results/

# Generate JUnit XML for CI
wctl2 run-playwright --junit-output results.xml
```

## Integration with Existing wctl2

### Command Registration Order

Playwright command should be registered before the generic passthrough to ensure it takes precedence:

```python
# commands/__init__.py
def register(app: typer.Typer) -> None:
    doc.register(app)
    maintenance.register(app)
    npm.register(app)
    python_tasks.register(app)
    playwright.register(app)  # Before playback/passthrough
    playback.register(app)
```

### Context Reuse

Leverage existing `CLIContext` infrastructure:
- `context.project_dir` for resolving paths
- `context.environment` for merged env vars
- `context.env_value()` for .env lookups
- `context.logger` for consistent logging

### Help Documentation

```bash
wctl2 run-playwright --help

Usage: wctl2 run-playwright [OPTIONS]

  Run Playwright smoke tests against WEPPcloud environments.

Options:
  -e, --env [dev|local|local-direct|staging|prod|custom]
                                  Environment preset  [default: dev]
  --base-url TEXT                 Override base URL (implies custom env)
  -c, --config TEXT               WEPPcloud config slug  [default: disturbed9002_wbt]
  --run-path TEXT                 Reuse existing run path
  --create-run / --no-create-run  Auto-provision run  [default: create-run]
  --keep-run                      Preserve run after tests
  --run-root TEXT                 Optional run root directory
  -p, --project TEXT              Playwright project  [default: runs0]
  -w, --workers INTEGER           Parallel workers  [default: 1]
  --headed                        Run in headed mode
  -g, --grep TEXT                 Filter tests by pattern
  --debug                         Run in debug mode
  --ui                            Launch Playwright UI
  --report                        Open HTML report after run
  --playwright-args TEXT          Additional Playwright arguments
  -h, --help                      Show this message and exit.
```

## Testing Strategy

### Unit Tests

```python
# tools/wctl2/tests/test_playwright.py
def test_resolve_base_url_dev(mock_context):
    """Test default dev URL resolution."""
    url = _resolve_base_url(mock_context, "dev", None)
    assert url == "https://wc.bearhive.duckdns.org/weppcloud"

def test_resolve_base_url_override(mock_context):
    """Test explicit base URL override."""
    url = _resolve_base_url(mock_context, "local", "https://custom.com")
    assert url == "https://custom.com"

def test_environment_variable_mapping():
    """Test env vars are correctly set."""
    # Mock command invocation and verify SMOKE_* vars

def test_run_path_disables_provisioning(mock_context):
    """Test that --run-path automatically disables SMOKE_CREATE_RUN."""
    # Verify SMOKE_CREATE_RUN=false when run_path is set
    # Verify SMOKE_RUN_PATH is set correctly

def test_playwright_args_quoting():
    """Test that shlex.split handles quoted arguments."""
    import shlex
    args = '--grep "controller regression" --workers 2'
    parsed = shlex.split(args)
    assert parsed == ['--grep', 'controller regression', '--workers', '2']
```

### Integration Tests

```bash
# Dry-run mode to validate command construction
wctl2 run-playwright --dry-run --env dev --config test123

Expected output:
[wctl2] DRY RUN: Would execute:
cd /workdir/wepppy/wepppy/weppcloud/static-src
SMOKE_BASE_URL=https://wc.bearhive.duckdns.org/weppcloud
SMOKE_CREATE_RUN=true
SMOKE_RUN_CONFIG=test123
SMOKE_HEADLESS=true
npm run test:playwright -- --project runs0 --workers 1
```

### Acceptance Criteria

- [ ] Command runs successfully against local dev stack
- [ ] Command runs successfully against dev domain (wc.bearhive.duckdns.org)
- [ ] Environment presets resolve correct URLs
- [ ] `--base-url` override works correctly
- [ ] All environment variables are properly set
- [ ] Playwright arguments pass through correctly
- [ ] Exit codes propagate correctly
- [ ] `--help` documentation is clear and complete
- [ ] Works with both `wctl2` and future `wctl` symlink
- [ ] Error messages are helpful for common mistakes
- [ ] Integrates cleanly with existing `CLIContext`

## Migration Path

1. **Implement** `playwright.py` module following this spec
2. **Test** against local and dev environments
3. **Document** in `wctl/README.md` and `tests/README.smoke_tests.md`
4. **Update** CI/CD pipelines to use new command
5. **Deprecate** manual `npm run test:playwright` invocations in favor of `wctl2 run-playwright`
6. **Announce** to team with migration guide

## Benefits

### Before (Manual Invocation)
```bash
cd /workdir/wepppy/wepppy/weppcloud/static-src && \
  SMOKE_BASE_URL=https://wc.bearhive.duckdns.org/weppcloud \
  SMOKE_CREATE_RUN=true \
  SMOKE_RUN_CONFIG=disturbed9002_wbt \
  npm run test:playwright -- --project=runs0 --workers=1
```

Problems:
- ✗ Verbose and error-prone
- ✗ Must remember exact env var names
- ✗ Must navigate to correct directory
- ✗ Hard to script and maintain
- ✗ No validation or helpful errors

### After (wctl2)
```bash
wctl2 run-playwright
```

Benefits:
- ✓ Concise and memorable
- ✓ Self-documenting via `--help`
- ✓ Sensible defaults for common cases
- ✓ Flexible for advanced use cases
- ✓ Consistent with other wctl commands
- ✓ Environment presets prevent typos
- ✓ Integrates with existing .env infrastructure
- ✓ Ready for CI/CD automation

## Implementation Notes

### Argument Quoting

The `--playwright-args` option uses `shlex.split()` to properly handle shell quoting:

```python
# Handles quoted arguments correctly
wctl2 run-playwright --playwright-args '--grep "controller regression"'
wctl2 run-playwright --playwright-args "--grep 'landuse mode'"
```

Without `shlex.split()`, the simple `.split()` method would break on spaces inside quotes.

### Run Path Auto-Disables Provisioning

When `--run-path` is provided, the implementation automatically sets `SMOKE_CREATE_RUN=false` to prevent double-provisioning:

```python
if run_path:
    test_env["SMOKE_RUN_PATH"] = run_path
    test_env["SMOKE_CREATE_RUN"] = "false"  # Force disable provisioning
else:
    test_env["SMOKE_CREATE_RUN"] = "true" if create_run else "false"
```

This prevents the smoke harness from calling `/tests/api/create-run` when the user explicitly wants to reuse an existing run.

### HTML Report Opening

The `--report` flag uses `npx playwright show-report` instead of an npm script:

```python
if report and result.returncode == 0:
    report_cmd = ["npx", "playwright", "show-report"]
    subprocess.run(report_cmd, cwd=str(static_src), env=test_env)
```

Playwright's `show-report` command is a built-in CLI tool, not something defined in `package.json`.

## Appendix: Related Documentation

- `tools/wctl2/SPEC.md` - Overall wctl2 architecture
- `tests/README.smoke_tests.md` - Playwright test suite documentation
- `wepppy/weppcloud/static-src/playwright.config.mjs` - Playwright configuration
- `wctl/README.md` - wctl command reference
