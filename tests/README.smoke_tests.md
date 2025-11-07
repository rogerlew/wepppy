# Smoke Testing (Playwright)

This document explains how to run the UI smoke suite, provision disposable runs, and understand the available toggles. The smoke harness provides a quick health check (~2 minutes) and can be expanded to cover additional workflows.

## 1. Prerequisites
- Backend running (dev stack or staging).
- `TEST_SUPPORT_ENABLED=true` set for the backend service (either in `docker/.env` or exported manually) so `/tests/api/*` endpoints are available.
- Inside `wepppy/weppcloud/static-src` run:
  ```bash
  npm install
  npx playwright install
  ```
  (or via `wctl run-npm install` + `wctl run-npm exec -- npx playwright install`).

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

## 3. Running the Smoke Suite (manual env)
- From repository root:
  ```bash
  export TEST_SUPPORT_ENABLED=true
  export SMOKE_CREATE_RUN=true
  export SMOKE_RUN_CONFIG=dev_unit_1
  # optional overrides:
  export SMOKE_RUN_OVERRIDES='{"general:dem_db":"ned1/2016"}'
  wctl run-npm smoke
  ```
- Alternatively, run locally inside `static-src`: `npm run smoke`.
- **For testing against dev/staging environments**, ensure `TEST_SUPPORT_ENABLED=true` is set in the backend environment and restart the service. Then:
  ```bash
  cd wepppy/weppcloud/static-src
  SMOKE_BASE_URL=https://wc.bearhive.duckdns.org \
  SMOKE_CREATE_RUN=true \
  SMOKE_RUN_CONFIG=dev_unit_1 \
  npm run test:playwright -- --project=runs0
  ```

### Environment Variables
| Variable | Default | Description |
| --- | --- | --- |
| `TEST_SUPPORT_ENABLED` | `false` | Must be `true` for `/tests/api/*` endpoints. |
| `SMOKE_CREATE_RUN` | `true` | When `true`, auto-provisions a run via `/tests/api/create-run`. Set to `false` to reuse an existing run. |
| `SMOKE_RUN_CONFIG` | `dev_unit_1` | Config slug for provisioning. |
| `SMOKE_RUN_OVERRIDES` | _(unset)_ | JSON string of config overrides (e.g., `{ "general:dem_db": "ned1/2016" }`). |
| `SMOKE_RUN_PATH` | _(unset)_ | Full runs0 URL to test (skips provisioning). |
| `SMOKE_RUN_ROOT` | _(unset)_ | Optional root directory for provisioning (e.g., `/tmp/weppcloud_smoke`, `/dev/shm/weppcloud_smoke`). |
| `SMOKE_BASE_URL` | `http://localhost:8080` | Backend origin. Use `http://localhost:8000` for direct Flask (no Caddy), or `http://localhost:8000/weppcloud` when the base includes the app prefix. |
| `SMOKE_HEADLESS` | `true` | Set to `false` to watch executions. |
| `SMOKE_KEEP_RUN` | `false` | Keeps the provisioned run after completion. |

### Current Coverage (Playwright)
- `page-load.spec.js`: provisions (or reuses) a run and verifies the runs0 page loads without console errors.
- `controller-regression.spec.js`: currently drives the Landuse workflow end-to-end—simulates a successful job submission (job hint/link updates) and then injects an `exception_factory` payload to verify stacktrace rendering. Additional controllers will be layered in once their flows are stabilized.

### CI Considerations
- The smoke suite is designed to give a quick health signal. As coverage grows (job submission, StatusStream assertions, additional flows) consider:
  - Splitting specs into targeted groups (`smoke`, `regression`).
  - Running headless Chromium by default; add Firefox/WebKit selectively.
  - Integrating with `wctl` or pipeline scripts so provisioning/cleanup happens automatically.

### Cleanup / Provisioning
- Both specs provision via `/tests/api/create-run` when `SMOKE_CREATE_RUN=true`; runs are deleted automatically unless `SMOKE_KEEP_RUN=true`.
- Manual cleanup remains available via `DELETE /tests/api/run/<runid>`.

---

This suite is intended to become a collection of targeted tests. Each spec should complete in under two minutes for fast feedback. Update this document as new flows are added.

## Status2 WebSocket Smoke

A lightweight Go harness lives at `tests/tools/status2_smoke/`. It exercises the
status2 WebSocket fan-out from inside the dev stack:

```bash
wctl run status-build sh -lc 'cd /workspace/tests/tools/status2_smoke && PATH=/usr/local/go/bin:$PATH go run . \
  --ws ws://status:9002 \
  --redis redis://redis:6379/2 \
  --run smoke-test \
  --channel climate \
  --samples 5 \
  --payload-bytes 256 \
  --clients 1 \
  --receive-timeout 10s \
  --timeout 10s'
```

Flags:

- `--samples` – number of publish/receive cycles to measure (default `1`)
- `--payload-bytes` – bytes of additional payload appended to each message (default `0`)
- `--clients` – number of concurrent WebSocket clients to run (default `1`)
- `--receive-timeout` – per-message receive timeout (default `8s`)
- `--timeout` – overall deadline for the run (default `10s`)

The tool publishes payload(s) to Redis and waits for matching `status` frames
over the WebSocket connection. When `--clients > 1`, each client runs in
parallel with its own WebSocket connection; all latencies are aggregated into a
single summary (min/median/mean/p95/max in milliseconds). Use `--ws`/`--redis`
to point at alternate hosts (the defaults target `127.0.0.1` from inside the
container).

### CI/Nightly Helper

To avoid orphan containers and prep dependencies automatically, use the helper
script:

```bash
scripts/run-status2-smoke.sh
```

Override defaults via environment variables (for example
`STATUS2_SMOKE_CLIENTS=4 STATUS2_SMOKE_TIMEOUT=60s scripts/run-status2-smoke.sh`).
