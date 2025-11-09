# WEPPcloud Profile Recorder

> End-to-end testing framework that captures, assembles, and replays real WEPPcloud user sessions to enable regression testing, workflow validation, and reproducible scenario creation for erosion modeling runs.

> **See also:** [AGENTS.md](AGENTS.md) for developer onboarding and implementation patterns, [PROFILE_TEST_ENGINE_SPEC.md](PROFILE_TEST_ENGINE_SPEC.md) for detailed technical specifications. This document is intended for humans.

## Overview

The Profile Recorder system transforms WEPPcloud user interactions into portable, replayable test scenarios. When a user builds a watershed, uploads data, runs WEPP simulations, or generates reports, the recorder captures every backend request, snapshots required input files, and packages everything into self-contained profiles. These profiles can then be replayed against any WEPPcloud instance to verify that workflows still function correctly after code changes, infrastructure updates, or WEPP model upgrades.

This capability addresses critical challenges in testing complex geospatial modeling applications where:
- **Manual testing is prohibitively expensive** – A single WEPP run may require 15+ interaction steps (DEM fetch, outlet placement, delineation, landuse/soils configuration, climate selection, model execution, report generation)
- **Test data preparation is fragile** – Coordinating config files, GeoJSON uploads, raster inputs, and database state manually leads to brittle test suites
- **Regression detection requires real workflows** – Unit tests catch code-level issues but miss integration failures across services (Redis, PostgreSQL, RQ workers, Go microservices, Rust binaries)
- **Domain experts need reproducible scenarios** – Hydrologists and land managers want to validate model behavior against known-good baselines without understanding Docker internals

The recorder operates transparently during normal WEPPcloud use. Frontend JavaScript intercepts all HTTP traffic, backend Flask middleware captures request/response payloads, and the assembler snapshots derived files as workflows progress. After a run completes, an operator promotes the draft into a named profile that CI pipelines, manual testers, or automated regression suites can replay indefinitely.

### Key Capabilities

- **Zero-instrumentation capture** – Works with existing WEPPcloud UI; no code changes required to record new scenarios
- **Automatic seed assembly** – Intelligently captures landuse rasters, soil burn severity maps, climate files, and configuration state
- **Authenticated playback** – Handles WEPPcloud login flows and session management for unattended execution
- **RQ job orchestration** – Tracks asynchronous background tasks, polls for completion, and reports hierarchical job trees on failures
- **Multi-endpoint validation** – Replays fork operations, archive jobs, and complete model runs across multiple configurations
- **Streaming diagnostics** – Real-time log output with ANSI color highlighting (HTTP statuses, job IDs, URLs, JSON payloads) for rapid troubleshooting

## Architecture

The system consists of five coordinated components spanning frontend JavaScript, Python Flask middleware, background assembly logic, a FastAPI playback service, and CLI tooling:

### 1. Frontend Interceptor (`recorder_interceptor.js`)

A lightweight JavaScript module wrapping the `WCHttp.request` interface used by all WEPPcloud controllers. It operates as a transparent proxy:

- **Event emission** – Captures method, endpoint, request body metadata, execution timing, HTTP status codes, and error details for every backend call
- **Batching and delivery** – Queues events and flushes them in batches (default: 10 events or 200ms intervals) via `navigator.sendBeacon` or `fetch` to the `/runs/<runid>/<config>/recorder/events` endpoint
- **Session tracking** – Enriches events with client-side context (run ID, config slug, session ID, root URL) extracted from global JavaScript state
- **Selective recording** – Honors `__WEPP_RECORDER_CONFIG` toggles so playback requests never recursively record themselves

The interceptor requires no controller modifications; it wraps `http.request` once during page initialization and automatically instruments all subsequent traffic including file uploads, JSON payloads, and GET requests.

### 2. Flask Recorder Extension (`profile_recorder.py` + `recorder_bp.py`)

Backend Flask middleware that persists events and forwards them to the assembler:

- **Audit logging** – Appends timestamped JSON events to `<run_dir>/_logs/profile.events.jsonl` ensuring all backend activity is permanently captured
- **User enrichment** – Attaches authenticated user metadata (ID, email) to events when available
- **Assembler forwarding** – Passes successful response events plus file path hints (extracted from known payload keys like `output_files`, `upload_files`) to the streaming assembler
- **Per-run toggle** – Respects `Ron.profile_recorder_assembler_enabled` flag so specific runs can disable draft generation while preserving audit trails
- **Promotion endpoint** – Exposes `/runs/<runid>/<config>/recorder/promote` (PowerUser-only) for finalizing profile captures

Configuration lives in `RecorderConfig` (default data root: `/workdir/wepppy-test-engine-data`) and Flask app initialization installs the recorder as `app.extensions['profile_recorder']`.

### 3. Streaming Assembler (`assembler.py`)

The assembler consumes events on-the-fly and builds draft profiles under `profiles/_drafts/<run>/<capture>/`:

- **Event streaming** – Appends all received events to `events.jsonl` for verbatim replay
- **Seed capture** – Snapshots input files (landuse rasters, SBS uploads, CLI files, ash loads, omni scenarios) into `seed/uploads/` subdirectories
- **Task-driven rules** – Uses endpoint-specific patterns (`TASK_RULES`) to capture derived outputs (DEM tiles, channel shapefiles) and validate expected NoDb state
- **Config preservation** – Copies project `.cfg` files and default configs into `seed/config/` so playback can reconstruct Ron instances
- **Upload detection** – Hooks into known multipart form-data endpoints and mirrors original files with canonical names (`input_upload_landuse.tif`, `input_upload_sbs.tif`)
- **Promotion workflow** – `promote_draft(run_id, capture_id, slug)` materializes final profiles by copying `_drafts/<run>/<capture>` to `profiles/<slug>/capture` and cloning the run directory to `profiles/<slug>/run`

The assembler intentionally preserves everything; curation and manifest generation are future enhancements. Current profiles contain raw JSONL streams plus seed directories ready for immediate playback.

### 4. Playback Service (`services/profile_playback/app.py`)

A FastAPI microservice that rehydrates sandboxed runs and replays captured traffic:

**Endpoints:**
- `POST /run/{profile}` – Streams playback logs as plain text while executing recorded requests
- `GET /run/result/{token}` – Returns structured JSON results after playback completes
- `POST /fork/{profile}` – Triggers WEPPcloud fork workflow against sandbox run, waits for RQ job completion
- `POST /archive/{profile}` – Submits archive jobs and polls until archives materialize

**Playback semantics:**
- Hydrates `profiles/<slug>/run/` snapshot into clean sandbox workspace (`/workdir/wepppy-test-engine-data/playback/runs/<sandbox_uuid>`)
- Rewrites URLs from `/runs/<original>/` to `/runs/{playback_run_id}/`; the FastAPI service issues playback run IDs in the form `profile;;tmp;;<sandbox_uuid>` so sandbox runs stay isolated while the original ID remains available for reporting
- Skips recorded elevation queries and jobstatus polls (replays generate fresh job IDs)
- Automatically rebuilds multipart form-data payloads using seed assets (landuse, SBS, CLI, ash, omni uploads)
- Polls new job IDs until completion via `/rq/api/jobinfo/<id>`, parses hierarchical job trees on failures
- Applies 1-second delays between requests to prevent race conditions in async workflows

**Authentication:**
- Accepts optional `Cookie` header for manual sessions
- Otherwise performs automated login using `ADMIN_EMAIL`/`ADMIN_PASSWORD` against HTTPS WEPPcloud host (required because auth cookies are Secure-flagged)
- Mirrors session cookies across hosts when playback base URL differs from login URL

**Diagnostics:**
- Colored ANSI output (bright green for HTTP 2xx, red for errors, purple for job IDs, blue for URLs, green for JSON)
- Real-time streaming via asyncio queues and SSE-like line delivery
- Verbose mode emits request details, payload hints, response previews, job tracking, and completion summaries

### 5. CLI Integration (`wctl2` commands)

Typer-based commands exposing playback workflows to engineers and CI:

```bash
# Stream playback logs (dry-run previews requests without execution)
wctl run-test-profile backed-globule --dry-run

# Execute full profile replay with authentication
wctl run-test-profile rattlesnake-topaz-vanilla-wepp-watar

# Fork sandbox run with optional undisturbify processing
wctl run-fork-profile backed-globule --undisturbify --timeout 120

# Archive sandbox run with comment metadata
wctl run-archive-profile backed-globule --archive-comment "v2.3.1 baseline" --timeout 120
```

Commands resolve `PROFILE_PLAYBACK_URL` (default `http://127.0.0.1:8070`), `PROFILE_PLAYBACK_BASE_URL` (target WEPPcloud instance), and optional cookies from files (`--cookie-file`) or environment variables. Streaming output delivers logs to `stdout` while metadata appears on `stderr` for clean pipeline integration.

## Data Flow

```
User Interaction (Browser)
  ↓ WCHttp.request calls
recorder_interceptor.js
  ↓ Batched JSON events
POST /runs/<runid>/<config>/recorder/events
  ↓ Flask Blueprint
ProfileRecorder.append_event()
  ├─→ Audit log: <run_dir>/_logs/profile.events.jsonl
  └─→ ProfileAssembler.handle_event()
        ├─→ Draft capture: profiles/_drafts/<run>/<capture>/events.jsonl
        ├─→ Seed snapshots: seed/uploads/, seed/config/
        └─→ Validation notes: validation.log

POST /runs/<runid>/<config>/recorder/promote (Admin)
  ↓
ProfileAssembler.promote_draft()
  ├─→ Final capture: profiles/<slug>/capture/
  └─→ Run snapshot: profiles/<slug>/run/

wctl run-test-profile <slug>
  ↓ HTTP POST
POST /run/{profile} (FastAPI service)
  ↓ Thread pool
PlaybackSession.run()
  ├─→ Hydrate sandbox: playback/runs/<sandbox_uuid>/
  ├─→ Replay requests against WEPPcloud
  ├─→ Poll RQ jobs until completion
  └─→ Stream logs + store result JSON

wctl run-fork-profile <slug>
  ↓
fork_profile() → POST /rq/api/fork → Poll job → Copy fork artifacts

wctl run-archive-profile <slug>
  ↓
archive_profile() → POST /rq/api/archive → Poll job → Mirror archives
```

## Profile Layout

Promoted profiles reside under `PROFILE_DATA_ROOT/profiles/<slug>/`:

```
profiles/backed-globule/
  capture/
    events.jsonl              # Complete request/response stream
    seed/
      config/
        dev_unit_1.cfg        # Project configuration
        active_config.txt     # Which config was active
        defaults.cfg          # System defaults
      uploads/
        landuse/
          input_upload_landuse.tif
        sbs/
          input_upload_sbs.tif
        climate/
          input_upload_cli.cli
        ash/
          input_upload_ash_load.tif
        omni/
          _limbo/
            scenario_0_sbs.tif
      rq-api-fetch_dem_and_build_channels-dem-dem.tif
      rq-api-build_subcatchments_and_abstract_watershed-dem-channels.shp
    validation.log           # Task rule verification notes
    run_dir.txt              # Original run directory pointer
  run/                       # Snapshot of working directory
    .nodb/
    climate/
    dem/
    landuse/
    soils/
    wepp/
    watershed/
    _logs/
```

Playback expects `capture/events.jsonl` and optionally `run/` for complete workspace reconstruction. Missing seed uploads trigger warnings but don't prevent replay (some endpoints may fail gracefully).

## Configuration

### Flask Application Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `PROFILE_DATA_ROOT` | `/workdir/wepppy-test-engine-data` | Root directory for profiles, drafts, and audit logs |
| `PROFILE_RECORDER_ASSEMBLER_ENABLED` | `True` | Global toggle for assembler; per-run overrides via `Ron.profile_recorder_assembler_enabled` |

### Playback Service Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `PROFILE_PLAYBACK_ROOT` | `/workdir/wepppy-test-engine-data/profiles` | Profile library location |
| `PROFILE_PLAYBACK_BASE` | `/workdir/wepppy-test-engine-data/playback` | Sandbox parent directory |
| `PROFILE_PLAYBACK_RUN_ROOT` | `$BASE/runs` | Clean workspace destination for replays (UUID-named sandboxes) |
| `PROFILE_PLAYBACK_FORK_ROOT` | `$BASE/fork` | Fork artifact storage (UUID suffix from generated run id) |
| `PROFILE_PLAYBACK_ARCHIVE_ROOT` | `$BASE/archive` | Archive output storage (per-archive UUID) |
| `PROFILE_PLAYBACK_BASE_URL` | `https://wc.bearhive.duckdns.org/weppcloud` | Target WEPPcloud instance |
| `ADMIN_EMAIL` | *(required)* | Admin credentials for automated login |
| `ADMIN_PASSWORD` | *(required)* | Admin credentials for automated login |
| `PROFILE_PLAYBACK_COLOR` | `auto` | ANSI color toggle (`0`/`false` to disable) |
| `NO_COLOR` | *(unset)* | Presence disables all color output |

### wctl Command Options

All commands support:
- `--service-url` – Override playback service location (default: `$PROFILE_PLAYBACK_URL` or `http://127.0.0.1:8070`)
- `--base-url` – Override WEPPcloud target (default: `$PROFILE_PLAYBACK_BASE_URL`)
- `--cookie` – Raw Cookie header for authenticated requests
- `--cookie-file` – Read Cookie from file path

Additional per-command flags:
- `run-test-profile`: `--dry-run` (preview without execution)
- `run-fork-profile`: `--undisturbify`, `--target-runid`, `--timeout`
- `run-archive-profile`: `--archive-comment`, `--timeout`

## Usage Examples

### Capturing a New Profile

1. **Start a normal WEPPcloud session** – Navigate to run interface, complete workflow steps (DEM fetch, outlet selection, delineation, landuse/soils/climate configuration, WEPP execution)

2. **Verify capture is active** – Check `<run_dir>/_logs/profile.events.jsonl` for appended events and confirm draft exists under `profiles/_drafts/<runid>/stream/`

3. **Promote the draft** – Open PowerUser Panel (Admin role shows button, PowerUser+ can access endpoint):
   - Navigate to run interface
   - Open PowerUser Panel via hamburger menu or keyboard shortcut
   - Click "Promote Profile Draft" button (visible to Admin users)
   - Enter desired profile slug when prompted (defaults to run ID)
   - Confirm promotion in success dialog showing saved location

   The UI triggers `POST /runs/<runid>/<config>/recorder/promote` with the slug. Advanced users with PowerUser role can also call the endpoint directly with JSON payload `{"slug": "profile-name"}`.

4. **Commit profile to version control** – Add `profiles/<slug>/` directory to wepppy repository or data repository

### Replaying a Profile Locally

```bash
# Preview requests without execution
wctl run-test-profile backed-globule --dry-run

# Execute full replay with automated login
wctl run-test-profile backed-globule

# Override target WEPPcloud instance
wctl run-test-profile backed-globule \
  --base-url https://staging.weppcloud.org/weppcloud
```

Output streams to console with colored diagnostics. Playback service must be running (`uvicorn services.profile_playback.app:app --port 8070`).

### Testing Fork and Archive Operations

```bash
# Fork sandbox run without disturbance modifications
wctl run-fork-profile backed-globule

# Fork with undisturbify processing enabled
wctl run-fork-profile backed-globule --undisturbify --timeout 180

# Archive run with comment metadata
wctl run-archive-profile backed-globule \
  --archive-comment "v2.4.0 regression baseline" \
  --timeout 300
```

Both commands return JSON with job IDs, status, and artifact locations. Fork creates new run under `playback/fork/<fork_uuid>/`, archive materializes zip files under `playback/archive/<archive_uuid>/`.

### CI Pipeline Integration

```yaml
# .github/workflows/profile-regression.yml
- name: Start playback service
  run: docker compose -f docker/docker-compose.dev.yml up -d profile-playback

- name: Run profile suite
  run: |
    wctl run-test-profile backed-globule
    wctl run-test-profile rattlesnake-topaz-vanilla-wepp-watar
    wctl run-test-profile disturbed-high-severity-burn

- name: Check for failures
  run: |
    if grep -q "HTTP [45]" playback.log; then
      echo "Profile playback failures detected"
      exit 1
    fi
```

For headless environments, export `NO_COLOR=1` to disable ANSI codes.

## Adding Support for New Upload Types

When introducing a new form-data endpoint (for example, a custom shapefile upload):

1. **Update assembler capture** – Add case to `_capture_file_upload()` in `assembler.py`:
   ```python
   elif endpoint.endswith("tasks/upload_shapefile"):
       self._snapshot_shapefile_upload(seed_root, Path(run_dir))
   ```

2. **Implement snapshot helper** – Create `_snapshot_shapefile_upload()` that copies source files from run directory into `seed/uploads/shapefile/` with canonical names

3. **Extend playback reconstruction** – Add case to `_build_form_request()` in `playback.py`:
   ```python
   elif normalized.endswith("tasks/upload_shapefile"):
       self._populate_shapefile_form(files)
   ```

4. **Implement form builder** – Create `_populate_shapefile_form()` that locates seed file and adds to `files` dict with correct MIME type

5. **Test end-to-end** – Capture a profile exercising the upload, promote it, replay with `wctl run-test-profile`, verify upload succeeds

See `AGENTS.md` multipart upload inventory table for existing examples (landuse, SBS, CLI, ash, omni).

## Developer Notes

### Event Schema

Frontend events include:
- `stage`: `"request"`, `"response"`, or `"error"`
- `id`: Unique request identifier (timestamp + counter)
- `method`: HTTP verb (`"GET"`, `"POST"`)
- `endpoint`: Request URL (may include query parameters)
- `category`: `"http_request"` or `"file_upload"`
- `requestMeta`: Body summary (`bodyType`, `jsonPayload`, `formKeys`)
- `status`: HTTP status code (response stage only)
- `ok`: Boolean success flag (response stage only)
- `durationMs`: Request execution time

Backend enrichment adds:
- `received_at`: UTC timestamp (ISO 8601)
- `user`: `{id, email}` when authenticated
- `runId`, `config`, `sessionId`, `rootUrl`: Context from JavaScript globals

### Testing Strategy

- **Unit tests** – `tests/profile_recorder/` covers assembler rules, playback payload reconstruction, and utility functions
- **Integration tests** – `tests/weppcloud/routes/test_recorder_bp.py` validates Flask endpoint behavior
- **Smoke tests** – `wctl2/tests/test_playback.py` exercises CLI command parsing and service communication
- **End-to-end validation** – Manual profile capture → promotion → replay cycle before committing new upload support

### Known Limitations

- **No explicit capture start/stop UI** – Recorder runs continuously; draft isolation relies on `capture_id` parameter (currently hardcoded to `"stream"`)
- **Large file handling** – Seeds >50MB should be reviewed for LFS migration; playback does not optimize for network-heavy artifacts
- **Parallel playback constraints** – Redis locks are global; concurrent profile replays may experience contention
- **Form-data coverage** – Only documented upload types are automatically captured; new endpoints require manual plumbing
- **Manifest generation** – Profiles currently contain raw event streams; curated step lists and YAML descriptors are backlog items

### Code Organization

```
wepppy/profile_recorder/
  __init__.py              # Public exports (get_profile_recorder)
  profile_recorder.py      # Flask extension, audit logging
  assembler.py             # Streaming event processor, seed capture
  playback.py              # Session replay engine, form reconstruction
  config.py                # RecorderConfig dataclass
  utils.py                 # Path sanitization helpers
  AGENTS.md                # Developer onboarding playbook
  README.md                # This document

wepppy/weppcloud/controllers_js/
  recorder_interceptor.js  # Frontend HTTP interceptor

wepppy/weppcloud/routes/
  recorder_bp.py           # Flask blueprint (/recorder/*)

services/profile_playback/
  app.py                   # FastAPI playback service
  __init__.py

tools/wctl2/commands/
  playback.py              # Typer CLI commands
```

### Runtime Module Reference

| Module | Key Classes / Functions | Responsibilities | Notes |
|--------|-------------------------|------------------|-------|
| `profile_recorder/profile_recorder.py` | `ProfileRecorder`, `get_profile_recorder()` | Flask extension that persists recorder events, enriches payloads with user metadata, and forwards successful responses (plus inferred file hints) to the assembler. | Docstrings outline audit log layout and extension wiring; stubs live in `profile_recorder.pyi`. Covered by `tests/profile_recorder/test_profile_recorder.py`. |
| `profile_recorder/assembler.py` | `ProfileAssembler`, `TASK_RULES` | Streams events into `_drafts`, snapshots uploads/derived assets, enforces task-specific expectations, and promotes drafts into reusable profiles. | Event lifecycle, seed handling, and validation logging are described inline; stubs in `assembler.pyi`. Exercised by `tests/profile_recorder/test_assembler.py`. |
| `profile_recorder/playback.py` | `PlaybackSession`, `SandboxViolationError`, `main()` | Replays promoted captures, hydrates sandboxed run directories, rebuilds form-data payloads, polls RQ jobs, and emits human-readable reports. | CLI docstrings describe every helper (form builders, polling, logging). Stubs in `playback.pyi`; tested via `tests/profile_recorder/test_playback_session.py`. |
| `profile_recorder/config.py` | `RecorderConfig`, `resolve_recorder_config()` | Centralizes recorder settings (data roots, assembler toggle) and documents required Flask app config keys. | Protocol `_ConfiguredApp` keeps typing explicit; changes require stub update in `config.pyi`. |
| `profile_recorder/utils.py` | `sanitise_component()` | Normalizes user-provided identifiers for file-system safe paths. | Shared by assembler & playback. Simple docstring backed by `utils.pyi`. |

All runtime modules ship with colocated `.pyi` stubs. When adding new public methods, update the docstrings and stubs together, then run `wctl run-stubtest wepppy.profile_recorder.<module>` plus `wctl run-pytest tests/profile_recorder` (see [docs/prompt_templates/module_documentation_workflow.prompt.md](../../docs/prompt_templates/module_documentation_workflow.prompt.md) for details).

## Operational Notes

### Service Deployment

The playback service runs as a standalone FastAPI app, typically via Docker Compose:

```yaml
# docker-compose.dev.yml snippet
profile-playback:
  build:
    context: .
    dockerfile: Dockerfile
  command: >
    uvicorn services.profile_playback.app:app
    --host 0.0.0.0 --port 8070 --reload
  ports:
    - "8070:8070"
  volumes:
    - /workdir/wepppy-test-engine-data:/workdir/wepppy-test-engine-data
  environment:
    ADMIN_EMAIL: admin@example.org
    ADMIN_PASSWORD: "${ADMIN_PASSWORD}"
    PROFILE_PLAYBACK_BASE_URL: https://wc.bearhive.duckdns.org/weppcloud
```

Ensure `wepppy-test-engine-data` volume is writable and `ADMIN_*` credentials match a PowerUser account in the target WEPPcloud instance.

### Data Repository Management

Profiles grow quickly (typical capture: 1-5 MB for `events.jsonl`, 50-200 MB for `run/` snapshot). Consider:
- Separate git repository for profile data (submodule or sibling directory)
- LFS for large seed files (DEM tiles, high-resolution rasters)
- Automated pruning of `_drafts/` older than 30 days
- Selective promotion (only promote runs that represent critical workflows)

### Troubleshooting

**Symptom**: Playback fails with `401 Unauthorized`  
**Solution**: Verify `ADMIN_EMAIL`/`ADMIN_PASSWORD` in playback service environment. Ensure credentials exist in target WEPPcloud instance and user has PowerUser role. Check that `PROFILE_PLAYBACK_BASE_URL` uses HTTPS (Secure cookies required).

**Symptom**: Missing upload file during replay  
**Solution**: Inspect `profiles/<slug>/capture/seed/uploads/` for expected files. If missing, assembler capture was not implemented for that endpoint. Add snapshot logic to `_capture_file_upload()` and re-promote profile.

**Symptom**: Job status stuck at `404` during playback  
**Solution**: Expected behavior once worker completes job. Playback treats 404 as completion signal and proceeds to next request. Verify follow-up GET returns expected data.

**Symptom**: Race condition errors (missing files, incomplete state)  
**Solution**: Increase delay between requests in `playback.py` (`time.sleep(1.0)` after each POST). Check that RQ workers finished before subsequent requests execute (verbose logging shows job completion).

**Symptom**: ANSI color codes in CI logs  
**Solution**: Export `NO_COLOR=1` or `PROFILE_PLAYBACK_COLOR=0` before running playback commands. Most modern terminals support ANSI but some log aggregators require plain text.

## Further Reading

- **[AGENTS.md](AGENTS.md)** – Developer onboarding, upload implementation checklist, multipart inventory
- **[PROFILE_TEST_ENGINE_SPEC.md](PROFILE_TEST_ENGINE_SPEC.md)** – Detailed technical specification covering event schemas, playback semantics, authentication flows
- **[tools/wctl2/README.md](../../tools/wctl2/README.md)** – wctl CLI documentation, command reference
- **[wepppy/weppcloud/controllers_js/README.md](../../wepppy/weppcloud/controllers_js/README.md)** – Frontend controller architecture, HTTP abstraction patterns
- **[services/status2/README.md](../../services/status2/README.md)** – WebSocket streaming architecture (similar pattern used for playback logs)

## Credits

**Developed**: University of Idaho, 2024-2025  
**Primary contributors**: Roger Lew, GitHub Copilot  
**License**: BSD-3 Clause (see `license.txt`)
