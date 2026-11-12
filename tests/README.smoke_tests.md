# Smoke Testing (Playwright)

This document explains how to run the UI smoke suite, provision disposable runs, and understand the available toggles. The smoke harness provides a quick health check (~2 minutes) and can be expanded to cover additional workflows.

## 1. Prerequisites
- Backend running (dev stack or staging).
- `WEPPCLOUD_DEPLOYMENT_PROFILE=development` and `TEST_SUPPORT_ENABLED=true` in the backend environment so `/tests/api/*` endpoints are available. `wctl run-playwright` supplies bearer authentication transiently; never store the bearer in `docker/.env`.
- Inside `wepppy/weppcloud/static-src` run:
  ```bash
  npm install
  npx playwright install
  ```
  (or via `wctl run-npm install` + `wctl run-npm exec -- playwright install`).

## 2. Profiles and `wctl run-smoke`

We maintain YAML profile files under `tests/smoke/profiles/` that describe common scenarios (quick US watershed, Rattlesnake SBS, Blackwood, Earth datasets, etc.). Each profile can specify:

```yaml
name: quick
description: Small US watershed for fast health checks.
env:
  SMOKE_CREATE_RUN: "true"
  SMOKE_RUN_CONFIG: dev_unit_1
  SMOKE_RUN_OVERRIDES:
    general:dem_db: ned1/2016
  SMOKE_RUN_ROOT: /tmp/weppcloud_smoke
  SMOKE_KEEP_RUN: "false"
steps:
  - description: load runs0 page and ensure controllers render
  - description: run map tab/StatusStream sanity checks
  - description: toggle landuse mode and verify UI updates
timeout: 120000   # optional per-profile timeout (ms)
```

The planned `wctl run-smoke --profile quick` command will:
- Load the chosen profile (merging any flag overrides).
- Export the env vars, including optional `SMOKE_RUN_ROOT` for run provisioning.
- Invoke `npm run smoke` with the Playwright config (possibly filtered to the steps declared in the profile).
- Collect results (list reporter + HTML/trace outputs).

Profiles under consideration:
- `quick` – small US watershed sanity (2 minutes).
- `rattlesnake` – SBS medium watershed (tests disturbed/treatments plus SBS flows).
- `blackwood` – larger US watershed without SBS.
- `earth` – international/earth datasets (non-US coverage).

Each profile is a YAML file under `tests/smoke/profiles/`. See `quick.yml` for the structure (env overrides, steps, timeout, descriptions).

Each profile will eventually describe a set of actions (map, landuse, climate, WEPP run) and the harness will translate those into targeted Playwright specs.

Until `wctl run-smoke` lands, you can export the env vars manually (below) to mimic the quick profile.

## 3. Running the Smoke Suite

### `wctl2 run-playwright` (recommended)
`wctl2 run-playwright` wraps all environment setup, ping validation, and Playwright CLI args:
```bash
# Default: dev environment, provisions disturbed9002_wbt, runs full suite
wctl2 run-playwright

# Local stack with existing run (skip provisioning)
wctl2 run-playwright --env local --no-create-run --run-path http://localhost:8080/weppcloud/runs/<id>/<config>/

# Controller-only checks with overrides and HTML report
wctl2 run-playwright \
  --env dev \
  --suite controllers \
  --workers 2 \
  --overrides general:dem_db=ned1/2016 \
  --report

# GL dashboard regressions (uses run path to auto-derive GL_DASHBOARD_URL)
wctl2 run-playwright \
  --suite gl-dashboard-state-transitions \
  --run-path https://wc.bearhive.duckdns.org/weppcloud/runs/minus-farce/disturbed9002_wbt/ \
  --workers 1
```
`--run-path` now auto-appends `/gl-dashboard` for that suite; you can also pass `--gl-dashboard-url` or `--gl-dashboard-path` directly. The wrapper defaults `PLAYWRIGHT_BROWSERS_PATH` to `./.playwright-browsers` (override via `--browsers-path` when sharing a cache).
Flags map directly to the smoke harness env vars (`SMOKE_BASE_URL`, `SMOKE_RUN_CONFIG`, etc.) and support advanced toggles like `--headed`, `--run-root`, and `--playwright-args`. See `tools/wctl2/docs/playwright.SPEC.md` for the full option table.

### Direct npm execution

Prefer `wctl run-playwright`. A trusted harness invoking npm directly must
inject `SMOKE_TEST_SUPPORT_TOKEN` transiently and set `SMOKE_BASE_URL` to the
correct application prefix. The backend requires explicit development/test
profile and enabled support. Do not store tokens in shell history or env files.

### Environment Variables
| Variable | Default | Description |
| --- | --- | --- |
| `TEST_SUPPORT_ENABLED` | `false` | Requires explicit development/test profile and support bearer. |
| `SMOKE_CREATE_RUN` | `true` | When `true`, auto-provisions a run via `/tests/api/create-run`. Set to `false` to reuse an existing run. |
| `SMOKE_RUN_CONFIG` | `dev_unit_1` | Config slug for provisioning. |
| `SMOKE_RUN_OVERRIDES` | _(unset)_ | JSON string of config overrides (e.g., `{ "general:dem_db": "ned1/2016" }`). |
| `SMOKE_RUN_PATH` | _(unset)_ | Full runs0 URL to test (skips provisioning). |
| `SMOKE_RUN_ROOT` | _(unset)_ | Optional root directory for provisioning (e.g., `/tmp/weppcloud_smoke`, `/dev/shm/weppcloud_smoke`). |
| `SMOKE_BASE_URL` | `http://localhost:8080` | Backend origin. Use `http://localhost:8000` for direct Flask (no Caddy), or `http://localhost:8000/weppcloud` when the base includes the app prefix. |
| `SMOKE_SITE_PREFIX` | `/weppcloud` | Site path prefix appended by smoke specs for app routes (`/login`, `/runs/...`, `/ui/components/...`) when `SMOKE_BASE_URL` does not include the prefix. |
| `SMOKE_HEADLESS` | `true` | Set to `false` to watch executions. |
| `SMOKE_KEEP_RUN` | `false` | Keeps the provisioned run after completion. |
| `ALLY_AGENT_EMAIL` / `ALLY_AGENT_PASSWORD` | _(unset)_ | Preferred credentials for authenticated UI smoke runs (CAP bypass by login). |
| `SMOKE_AGENT_EMAIL` / `SMOKE_AGENT_PASSWORD` | _(unset)_ | Generic aliases accepted by the axe suite. |
| `SMOKE_AGENT_CREDENTIALS_FILE` | `docker/secrets/ally-agent-smoke.env` | Env-style file for agent credentials; supports `ALLY_AGENT_*` and `SMOKE_AGENT_*` keys. |
| `SMOKE_AGENT_REQUIRED` | `false` | When true, axe run scans skip/fail fast if agent credentials are missing. |

### Current Coverage (Playwright)
- `page-load.spec.js`: Quick health check that provisions/reuses a run, loads the runs0 dashboard, verifies core controllers render, and fails fast on unexpected console errors.
- `run-page-smoke.spec.js`: Extended coverage that drives map tabs, toggles landuse modes, exercises StatusStream wiring, and injects stacktraces for multiple controllers.
- `controller-regression.spec.js`: Drives the Landuse workflow end-to-end—simulates a successful job submission (job hint/link updates) and injects failure payloads to ensure stacktraces render correctly.
- `mods-menu.spec.js`: Opens the header Mods dropdown, verifies each checkbox mirrors `Ron.mods`, ensures the TOC/preflight nav and controller placeholders stay synchronized, and toggles every mod off/on twice to confirm the project returns to its initial state.
- `gl-dashboard-state-transitions.spec.js`: Basemap changes, RAP/WEPP/Climate graph toggles, cumulative contribution workflow, year-slider visibility rules, and RAP year updates.
- `gl-dashboard-graph-modes.spec.js`: Graph mode/slider placement (WEPP split vs. Climate full), cumulative contribution stability, year-slider playback, graph-focus map hiding, and legend rendering (comparison diverging legend assertion skips when no scenario supports it).
- `theme-metrics.spec.js`: Theme contrast/metrics sampling for WC theme system.
  - AA enforcement defaults to: `default`, `light-high-contrast`, `ayu-mirage`, `ayu-mirage-bordered`, `cursor-dark-midnight`.
  - Non-enforced themes are still measured and reported, but do not fail the suite.
  - Override enforcement list when needed with `THEME_METRICS_ENFORCED_THEMES=theme1,theme2,...`.
- `a11y/axe-runs0.spec.js`: Axe-core structural accessibility scan for WEPPcloud root, interfaces landing, Theme Lab, and runs0 dashboard, with JSON/Markdown artifacts under `test-results/a11y/`.
  - For CAP-gated runs0 scans, prefer the `ally-agent` account via `docker/secrets/ally-agent-smoke.env`:
    ```bash
    # gitignored path (see root .gitignore docker/secrets/*)
    cat > docker/secrets/ally-agent-smoke.env <<'EOF'
    ALLY_AGENT_EMAIL=ally-agent@example.com
    ALLY_AGENT_PASSWORD=replace-with-local-secret
    EOF
    chmod 600 docker/secrets/ally-agent-smoke.env
    ```

All tests use request interception to mock 500 errors instead of backend failure injection. Console error checks filter expected bootstrap failures for optional controllers (debris_flow, treatments) that may not exist in all configs.

### Mods menu smoke
`mods-menu.spec.js` catches regressions like “DSS Export checkbox checked but nav item missing.” Important notes:

- **Run selection:** The spec defaults to `SMOKE_RUN_CONFIG=disturbed9002_wbt` and fails fast when `Ron.mods` lacks `disturbed`. When possible, clone an existing disturbed profile by using the built-in `--profile` flag (`wctl run-playwright --suite mods-menu --profile legacy-palouse`) which copies `/workdir/wepppy-test-engine-data/profiles/<slug>/run` into the playback sandbox and points Playwright at `/runs/profile;;tmp;;<uuid>/<config>/`.
- **No `playwright_load_all`:** The suite strips the helper query parameter from `SMOKE_RUN_PATH` so nav visibility reflects real mod state. Do not re-add `playwright_load_all=true` when sharing URLs for this spec.
- **What it validates:** Each checkbox state is compared against `window.runContext.mods`, the preflight/TOC entry (`data-mod-nav="<mod>"`), and the controller wrapper (`data-mod-section="<mod>"`). It then toggles every mod, verifies UI + state updates, and toggles again to ensure the project ends where it started.
- **Automated provisioning:** Cloning honours the same environment variables as the playback helpers (`PROFILE_PLAYBACK_ROOT`, `PROFILE_PLAYBACK_BASE`, `PROFILE_PLAYBACK_RUN_ROOT`). CI can point these at `/workdir/wepppy-test-engine-data` so cloned runs share the same lifecycle as recorder/fork jobs.

### Playwright Controller Regression Suite
`controller-regression.spec.js` is now its own suite (`--suite controllers`) that exercises every controller listed in `static-src/tests/smoke/controller-cases.js`. Important details:

- **Prerequisites:** Same profile and automatic bearer prerequisites as other smoke specs. The `/tests/api/create-run` endpoint automatically adds `playwright_load_all=true` to the runs0 URL so optional controllers (observed, debris_flow, etc.) render even when the config would normally hide them.
- **RQ vs synchronous controllers:** Cases with `workflow: "rq_job"` run through `runRqJobWorkflow`, which stubs a successful `job_id` response followed by a failure response. Synchronous controllers (lacking the flag) simply intercept the HTTP request and inject a 500 payload.
- **Controller metadata:** `controller-cases.js` defines per-controller selectors and optional hooks (`prepareAction` for form setup, `failureStatus` for non-500 responses, `expectJobHint` to skip hint assertions, `requireHintVisible` to ensure a job hint is actually shown). Keep helpers in that file lightweight; if more bespoke helpers accumulate, fold them into a small config module.
- **Adding cases:** Provide `formSelector`, `actionSelector`, `stacktraceLocator`, and `hintLocator`. Set `workflow: "rq_job"` if the real controller enqueues an RQ task so the suite can validate both job-hint updates and failure stacktraces. Consider `requireHintVisible` whenever the UI should keep the job hint visible (for example, after switching modes).
- **Execution:** `wctl2 run-playwright --suite controllers --workers 1` (or the equivalent `npm run test:playwright -- --grep "controller regression"`). The suite currently runs in ~25 seconds against dev, skipping controllers that are disabled for the target config.

### CI Considerations
- The smoke suite is designed to give a quick health signal. As coverage grows (job submission, StatusStream assertions, additional flows) consider:
  - Splitting specs into targeted groups (`smoke`, `regression`).
  - Running headless Chromium by default; add Firefox/WebKit selectively.
  - Integrating with `wctl` or pipeline scripts so provisioning/cleanup happens automatically.

### Cleanup / Provisioning
- Both specs provision via `/tests/api/create-run` when `SMOKE_CREATE_RUN=true`; runs are deleted automatically unless `SMOKE_KEEP_RUN=true`.
- Manual cleanup requires the same scoped bearer at `DELETE /tests/api/run/<runid>`; verify path absence, especially on NFS.

---

This suite is intended to become a collection of targeted tests. Each spec should complete in under two minutes for fast feedback. Update this document as new flows are added.

## Status2 WebSocket Smoke

A trusted operator Go fixture lives at `tests/tools/status2_smoke/`. Run it through
`scripts/run-status2-smoke.sh` with a configured `docker/.env` and the same
secret files used by status2. No default signing secrets are generated.

```bash
STATUS2_SMOKE_CLIENTS=4 STATUS2_SMOKE_TIMEOUT=60s scripts/run-status2-smoke.sh
```

The wrapper mounts the signing ring and Redis password only into the one-off
builder and passes the exact configured Origin. The fixture appends a random
suffix to the requested run prefix, creates one bounded DB 11 session marker,
and signs the exact status profile with `config=smoke`. It sends only the fixed
plus bearer protocol pair, verifies the fixed selected protocol, and removes its
exact marker on normal completion or client failure (TTL bounds interruption).
It does not create or inspect a real run. This is **service fanout evidence**;
only the separate browser acceptance test proves cookie/run authorization.

Existing options remain: `STATUS2_SMOKE_SAMPLES`, `STATUS2_SMOKE_PAYLOAD_BYTES`,
`STATUS2_SMOKE_CLIENTS`, `STATUS2_SMOKE_RECEIVE_TIMEOUT`, `STATUS2_SMOKE_TIMEOUT`,
`STATUS2_SMOKE_WS_URL`, `STATUS2_SMOKE_REDIS_URL`, `STATUS2_SMOKE_RUN_ID` (prefix),
and `STATUS2_SMOKE_CHANNEL`. Overall timeout is at most 290 seconds. The nightly
workflow invokes this wrapper; its runner must provision the configured secret
files. Latency summaries contain no credentials; never enable shell tracing or
upload secret files.

## Test-support authentication

Production defaults to `WEPPCLOUD_DEPLOYMENT_PROFILE=production` and never
registers `/tests/api/*`. Explicit `development` or `test` plus
`TEST_SUPPORT_ENABLED=true` enables the privileged support API. Production
with support enabled refuses startup; unknown profiles also fail. Dev Compose
selects development explicitly; production Compose pins production/disabled.

Use `wctl run-playwright` for automatic one-hour WEPP_AUTH bearer minting and
injection, including runs using `--no-create-run`. No login, cookie, manual
token copying or smoke markers are needed for support provisioning/cleanup.
Remote targets require verified HTTPS; localhost/loopback may use HTTP.
The wrapper must target the environment whose container issued its token.
Direct npm smoke needs transient `SMOKE_TEST_SUPPORT_TOKEN` injection by a
trusted harness. Never save it to env files, reports, argv or URLs.

Support calls use the shared untraced HTTP helper; ordinary application calls
receive no support header. A valid support token can delete any resolvable run
in that non-production environment. See the [canonical contract](../docs/schemas/weppcloud-test-support-contract.md)
for statuses, lifetime, CSRF exemption and validation requirements.

### NFS cleanup acceptance

Support deletion returns 200 only after directory-absence readback. A filesystem
error or remaining path returns 500 (`Run cleanup failed`); retain the disposable
run ID for scoped recovery. Never treat a passing browser assertion or cleanup
warning as evidence of removal. Run log handlers release idle file descriptors,
but deletion concurrent with active writers can still fail.
