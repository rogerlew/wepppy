# wctl2 Playwright Command Specification

## Overview

The `wctl2 run-playwright` command encapsulates the complexity of running Playwright smoke tests against various WEPPcloud environments (explicit development/test runtimes) while maintaining flexibility for CI/CD pipelines and developer workflows.

## Goals

1. **Simplify execution**: Reduce the verbose command invocation to a single concise command
2. **Environment flexibility**: Support explicit development/test targets
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
| `prod` | _(from env var `PLAYWRIGHT_PROD_URL`)_ | Legacy URL alias; production profile has no support routes |
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
| `--create-run / --no-create-run` | Flag | `True` | Auto-provision runs via `/tests/api/create-run` (ignored when `--run-path` is set) |
| `--keep-run` | Flag | `False` | Preserve provisioned run after tests complete |
| `--run-root` | Path | _(none)_ | Optional root directory for run provisioning |
| `--suite`, `-s` | Choice | `full` | Named suite preset (`full`, `smoke`, `controllers` → mapped to Playwright `--grep`). Explicit `--grep` overrides. |

#### Playwright Execution

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--project`, `-p` | String | `runs0` | Playwright project name from config |
| `--workers`, `-w` | Int | `1` | Number of parallel workers (force to `1` when `--headed` is used) |
| `--headed` | Flag | `False` | Run in headed mode (visible browser); implies `--workers 1` |
| `--grep`, `-g` | String | _(none)_ | Filter tests by pattern |
| `--debug` | Flag | `False` | Run Playwright in debug mode |
| `--ui` | Flag | `False` | Launch Playwright UI mode |
| `--report` | Flag | `False` | Generate HTML report and open it via `npx playwright show-report` after a successful run |
| `--report-path` | Path | _(defaults to `playwright-report` when omitted)_ | Directory passed to Playwright’s `--output`; implies report generation without opening the viewer |

#### Pass-through

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--playwright-args` | String | _(none)_ | Additional Playwright CLI arguments (quoted strings preserved via `shlex.split`) |
| `--overrides` | Key=Value (repeatable) | _(none)_ | Converts to JSON and sets `SMOKE_RUN_OVERRIDES` (e.g., `--overrides general:dem_db=ned1/2016`) |

#### GL dashboard helpers

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--gl-dashboard-url` | String | Derived from `--run-path` when present | Full GL dashboard URL passed to the suite (highest priority) |
| `--gl-dashboard-path` | String | _(none)_ | Path appended to `SMOKE_BASE_URL` when URL is not set (for example `/runs/<id>/<config>/gl-dashboard`) |
| `--browsers-path` | Path | `./.playwright-browsers` | Sets `PLAYWRIGHT_BROWSERS_PATH` before invoking Playwright |

### Environment Variable Mapping

The command sets these environment variables before invoking `npm run test:playwright`:

| wctl2 Option | Env Var | Playwright Config Reads |
|--------------|---------|-------------------------|
| `--base-url` / `--env` | `SMOKE_BASE_URL` | `process.env.SMOKE_BASE_URL` |
| `--create-run` (if no `--run-path`) | `SMOKE_CREATE_RUN` | `process.env.SMOKE_CREATE_RUN` |
| `--run-path` | `SMOKE_RUN_PATH` | `process.env.SMOKE_RUN_PATH` (forces `SMOKE_CREATE_RUN=false`) |
| `--config` | `SMOKE_RUN_CONFIG` | `process.env.SMOKE_RUN_CONFIG` |
| `--keep-run` | `SMOKE_KEEP_RUN` | `process.env.SMOKE_KEEP_RUN` |
| `--run-root` | `SMOKE_RUN_ROOT` | `process.env.SMOKE_RUN_ROOT` |
| `--headed` | `SMOKE_HEADLESS` | `process.env.SMOKE_HEADLESS !== 'false'` |
| `--overrides` | `SMOKE_RUN_OVERRIDES` | `process.env.SMOKE_RUN_OVERRIDES` (JSON) |
| `--gl-dashboard-url` / derived `--run-path` | `GL_DASHBOARD_URL` | `process.env.GL_DASHBOARD_URL` (preferred by gl-dashboard tests) |
| `--gl-dashboard-path` | `GL_DASHBOARD_PATH` | `process.env.GL_DASHBOARD_PATH` (used with `SMOKE_BASE_URL` fallback) |
| `--browsers-path` | `PLAYWRIGHT_BROWSERS_PATH` | `process.env.PLAYWRIGHT_BROWSERS_PATH` |

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

### Support authentication implementation

The implementation is `commands/playwright.py` and `commands/auth.py`. See
[the canonical support contract](../../../docs/schemas/weppcloud-test-support-contract.md).
The wrapper validates transport before minting a one-hour container-local
WEPP_AUTH bearer, then authenticates its mandatory ping (even --no-create-run).
It passes `SMOKE_TEST_SUPPORT_TOKEN` only to the test child, never the report
viewer. Both HTTP clients reject redirects; remote targets require verified
HTTPS, loopback permits HTTP. Support requests use the untraced Node helper
and never global Playwright headers. Mint failures stop before ping/npm.
Production has no support routes and is unsupported by this wrapper.

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

# Store report artifacts in a custom path
wctl2 run-playwright --report --report-path /tmp/playwright-report

# Run only controller regression suite
wctl2 run-playwright --suite controllers

# Suite with explicit grep override (grep wins)
wctl2 run-playwright --suite smoke --grep "map tabs"

# Apply config overrides
wctl2 run-playwright --overrides general:dem_db=ned1/2016
```

### CI/CD Pipelines

```bash
# Full suite against staging
wctl2 run-playwright --env staging --workers 4

# Specific test subset for PR checks
wctl2 run-playwright --suite smoke --workers 2

# Legacy prod URL alias (target must actually use development/test profile)
wctl2 run-playwright --env prod --config dev_unit_1

# Custom deployment target
wctl2 run-playwright \
  --base-url https://pr-123.weppcloud-preview.dev/weppcloud \
  --config disturbed9002_wbt

# Mods menu with recorded profile
wctl2 run-playwright --suite mods-menu --profile legacy-palouse
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
PLAYWRIGHT_DEV_PROJECT=runs0
```

Setting `PLAYWRIGHT_<ENV>_PROJECT` is optional but allows each preset to default to a different Playwright project without passing `--project` explicitly.

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

## Profile Playback Provisioning

Passing `--profile <slug>` clones the recorded run snapshot from
`/workdir/wepppy-test-engine-data/profiles/<slug>/run` into the playback sandbox
before Playwright executes. The command:

1. Resolves the profile library via `PROFILE_PLAYBACK_ROOT` (default `/workdir/wepppy-test-engine-data/profiles`)
   and the sandbox location via `PROFILE_PLAYBACK_BASE` / `PROFILE_PLAYBACK_RUN_ROOT`
   (default `/workdir/wepppy-test-engine-data/playback/runs`).
2. Copies the `run/` directory into a fresh `profile;;tmp;;<uuid>` sandbox and reads `active_config.txt`
   to discover the config slug.
3. Exports `SMOKE_RUN_PATH` so Playwright hits `/runs/profile;;tmp;;<uuid>/<config>/` on the target
   WEPPcloud host (still controlled by `--env`/`--base-url`).
4. Removes the sandbox directory afterwards unless `--keep-run` is set.

Example:

```bash
wctl2 run-playwright --suite mods-menu --profile legacy-palouse
```

This clones the `legacy-palouse` capture locally, executes only the Mods menu suite,
and validates that run header checkboxes stay in sync with TOC/preflight state.

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
import urllib.error
from unittest.mock import MagicMock, patch

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

def test_ping_test_support_success():
    """Test successful ping check."""
    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response
        # Should not raise
        _ping_test_support("https://test.example.com/weppcloud")

def test_ping_test_support_failure():
    """Test failed ping check exits with error."""
    with patch('urllib.request.urlopen', side_effect=urllib.error.URLError("Connection refused")):
        with pytest.raises(typer.Exit) as exc_info:
            _ping_test_support("https://test.example.com/weppcloud")
        assert exc_info.value.exit_code == 1

def test_build_overrides_json():
    """Test overrides parsing."""
    overrides = ["general:dem_db=ned1/2016", "climate:source=daymet"]
    result = _build_overrides_json(overrides)
    parsed = json.loads(result)
    assert parsed == {
        "general:dem_db": "ned1/2016",
        "climate:source": "daymet"
    }
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

- **Suite presets**: `--suite controllers` maps to `--grep "controller regression"`. If the user also provides `--grep`, their explicit pattern takes precedence (suite pattern is ignored). New suites can be added by extending the `SUITE_PATTERNS` dict.
- **Run-path overrides provisioning**: `--run-path` always forces `SMOKE_CREATE_RUN=false`; `--create-run` is ignored in that scenario to prevent double-provisioning.
- **Ping validation**: `_ping_test_support()` hits `/tests/api/ping` before invoking Playwright so failures happen immediately with clear error messages differentiating network vs backend config issues.
- **Headed mode**: When `--headed` is set we clamp `--workers` to `1`, matching Playwright's single-context limitation for visible browser windows.
- **Overrides**: Multiple `--overrides key=value` flags build a JSON blob for `SMOKE_RUN_OVERRIDES`. Keys support `:` for nested config sections (e.g., `general:dem_db`).
- **Argument quoting**: `--playwright-args` is parsed with `shlex.split()` so quoted grep patterns survive intact (e.g., `--playwright-args '--grep "some pattern"'`).
- **Reports**: `--report` adds `--reporter html --output <path>` to the Playwright run and automatically calls `npx playwright show-report <path>` afterward (success only). Supplying `--report-path` without `--report` still attaches the HTML reporter but skips the viewer so CI can collect artifacts safely.
- **Type hints**: `TYPE_CHECKING` guard around `Literal` types prevents runtime issues with Typer's option parsing while preserving type safety for mypy/pylance.

## Appendix: Related Documentation

- `tools/wctl2/docs/SPEC.md` - Overall wctl2 architecture
- `tests/README.smoke_tests.md` - Playwright test suite documentation
- `wepppy/weppcloud/static-src/playwright.config.mjs` - Playwright configuration
- `wctl/README.md` - wctl command reference
