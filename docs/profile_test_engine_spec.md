# Profile Test Engine Specification
> Draft high-level plan for recording and replaying WEPPcloud user workflows.

## Purpose
- Capture realistic, end-to-end WEPPcloud interactions as reusable “profiles”.
- Replay those profiles automatically to validate NoDb controllers, RQ jobs, and UI-driven flows.
- Provide an auditable record of how complex or edge-case runs are performed.
- Keep orchestration code close to the main application while hosting bulky profile assets in a sibling data repository.

## Audience
- Product owners deciding which flows to cover first.
- Engineers implementing the recorder, profile store, and runner.
- QA and support staff curating profiles from field reports.

## Goals
- Mirror real-world sequences (UI clicks, API calls, RQ tasks) without custom shims.
- Keep profile assets versioned inside the repository for repeatability and review.
- Make it simple to record a profile in the interface and replay it in automation.

## Out of Scope
- Low-level unit coverage for individual controllers (handled separately).
- Live analytics dashboards for profile executions; basic log output is sufficient for MVP.
- Parallel execution or sharding profiles across multiple hosts.

## Personas & Use Cases
- **Support Engineer:** Records a troublesome user workflow, submits it as a regression profile, and reruns it after fixes.
- **QA Analyst:** Builds a library of “happy path” and “edge” profiles that run nightly to guard releases.
- **Developer:** Replays a profile locally to verify bug fixes stay green.

## Core Concepts
- **Profile:** Named recipe combining input assets, ordered actions, and expected checkpoints.
- **Recorder Mode:** UI-assisted capture that watches user actions and serializes them into a profile draft.
- **Profile Runner:** Tool that hydrates inputs, replays actions, and checks results (CLI + pytest fixture).
- **Baseline Artifacts:** Minimal set of files/logs kept under version control for regression comparisons.

## MVP Feature Set
1. **Profile Schema**
   - Human-readable YAML stored under `profiles/<slug>/profile.yaml`.
   - Sections: metadata, prerequisites, ordered steps, expected outputs, notes.
2. **Seed Assets**
   - Each profile owns a `seed/` directory (e.g., uploaded shapefiles, small DEM snippets).
   - Optional `baseline/` folder capturing essential outputs (hashes, JSON summaries).
3. **Recorder Workflow**
   - Recorder runs globally to preserve an audit trail for every interaction; users can mark the start and end of a profile capture in the UI (or leave the pipeline dormant by not starting a capture).
   - Captures run id, configuration slug, session metadata (browser, window size), and every request that reaches the backend (HTTP endpoints, RQ task enqueues).
   - Fine-grained DOM/UI events are out of scope for the first version; focus stays on backend interactions that exercise NoDb and RQ.
   - Emits a JSONL audit stream under each run working directory for accountability regardless of capture state; when profile recording is enabled the same events are mirrored into the assembler pipeline.
   - Generates a draft YAML + seed snapshot for manual review when a capture is closed.
4. **Runner Workflow**
   - CLI command: `wctl run-test-profile <slug>` (host-side helper).
   - Helper calls the `profile_playback` FastAPI microservice which clones the promoted profile snapshot into `PROFILE_PLAYBACK_RUN_ROOT/<runid>` (default `/workdir/wepppy-test-engine-data/playback_runs/<runid>`) and replays the captured HTTP traffic with `PlaybackSession`.
   - During replay every request is rewritten to `/runs/profile;;tmp;;<runid>/...`, letting WEPPcloud resolve the temp run via `PROFILE_PLAYBACK_USE_CLONE=true` instead of touching the production directory.
   - Each run boots from a clean workspace: the assembler stores the active `.cfg` and `_defaults.toml` in the profile seed, and playback copies those into an empty run directory before reissuing the recorded requests.
   - Authentication remains anchored to the public HTTPS base URL so the secure `session` cookie survives; requests reuse that cookie while targeting the internal host.
   - POST requests that enqueue RQ tasks are tracked by job id; subsequent GETs defer until the queued jobs report `finished` via `/rq/api/jobstatus/<job_id>`, keeping playback aligned with the UI’s job lifecycle.
   - The service logs in automatically with `ADMIN_EMAIL` / `ADMIN_PASSWORD` from `docker/.env` when no cookie is supplied, so authenticated routes continue to pass.
   - Verbose mode streams step-by-step logging (clone source, run directory, job status updates) through the playback service so operators can follow along with `wctl logs profile_playback -f`.
   - Produces a structured JSON report (HTTP status per step, final run directory) that callers can persist or parse in follow-up tooling.
5. **Pytest Integration**
   - Fixture `profile_runner` exposes the same engine, enabling tests such as:
     ```python
     @pytest.mark.microservice
     def test_small_watershed(profile_runner):
         result = profile_runner.run("us-small")
         result.expect_completed("run_wepp")
     ```
6. **Baseline Comparison**
   - After replay, diff selected files against `baseline/` using configurable comparators (exact hash, raster statistics, tabular diff, etc.).
   - Warn when individual artifacts approach 50 MB and require review for anything larger; block files over 100 MB unless routed through Git LFS.
   - On mismatch, output human-friendly diagnostics and keep artifacts for inspection.

## Nice-to-Have Enhancements (Post-MVP)
- Profile tagging (e.g., climate-builder, wildfire-response) with targeted selectors.
- Web UI to browse profile catalog, inspect last run status, and download artifacts.
- Differential recording: auto-highlight deltas when re-recording an existing profile.
- Parallel runner orchestrator for nightly suites.
- CI integration that uploads run reports to central dashboard.
- Toggle to run without RQ (direct controller invocation) for faster “unitized” checks.
- Optional environment overlays (e.g., staging dataset vs. public dataset) per profile.

## Profile Lifecycle
1. **Record**
   - Mark capture boundaries in the UI; recorder writes a draft under `profiles/_drafts/`.
2. **Curate**
   - Review draft YAML for clarity.
   - Trim seed directory to required inputs only.
   - Define expected outputs (file list, log snippets, status flags).
   - Move curated profile into `profiles/<slug>/`.
3. **Commit**
   - Commit YAML + assets alongside short README snippet explaining the scenario.
   - Include baseline diff summary in PR for reviewer context.
4. **Replay**
   - Run locally via CLI or `pytest -k profile`.
   - CI picks up profiles based on markers or explicit job configuration.
5. **Maintain**
   - When legitimate changes alter outputs, rerun `wctl update-profile <slug>` to refresh baselines after review.
   - Deprecate stale profiles by moving them to `profiles/archived/` with rationale.

## Step Execution Model
- **Action Types:** HTTP POST (form submission), HTTP GET (status polling), RQ enqueue (if not automatically detected), waiting for status conditions, file upload.
- **Guards & Assertions:** Each step can declare wait conditions (e.g., “wait until run status is COMPLETE”), timeouts, and expected log phrases.
- **Error Handling:** Runner halts on first failure, captures diagnostic bundle (logs, responses, key files).

## Infrastructure Expectations
- Orchestration code lives in the main `wepppy` repository; large profile assets reside in `/workdir/wepppy-test-engine-data`.
- Profiles run inside the standard docker dev stack via `wctl`, with an optional flag pointing to the shared data repo.
- RQ worker remains enabled for MVP; CLI verifies worker health before starting.
- Temp run directories live under `/tmp/weppcloud_profiles/<slug>/<timestamp>/`.
- Artifacts from failed runs stored under `profiles/results/<slug>/<timestamp>/` (with heavy outputs written to the data repo when necessary).

## Reporting
- Runner outputs a concise summary:
  - Profile name, duration, result (pass/fail), failing step (if any).
  - Path to diagnostics bundle.
- Optional JSON report for CI consumption (`profiles/results/latest.json`).

## Profile YAML Snapshot
```yaml
metadata:
  slug: us-small-watershed
  rq_required: true
  data_repo: ../wepppy-test-engine-data
  seed_dir: profiles/us-small-watershed/seed
  baseline_dir: profiles/us-small-watershed/baseline

steps:
  - id: run-wepp
    action: enqueue_rq
    job: tasks.run_wepp
    payload:
      runid: "{{run_id}}"
    wait:
      type: status_poll
      endpoint: rq/status
      success_state: finished

comparisons:
  - target: wepp/output/run/summary.json
    method: json_exact
  - target: wepp/output/run/soil_loss.tif
    method: raster_stats
    params:
      tolerance:
        mean: 0.05
        max: 0.10
```

## Open Questions
- How to anonymize sensitive user data when recording profiles?

## Next Steps
1. Harden recorder coverage (multipart payload capture, RQ completion polling, richer validations) while keeping the existing WEPPcloud blueprint in place.
2. Extend the playback FastAPI service to support multipart replays and post-run assertions; wire results into pytest fixtures for automated validation.
3. Curate a baseline profile catalog (`sharing-mobilization`, `us-watershed-small`, etc.) and document promotion + playback workflows for collaborators.
4. Expand documentation (Recorder how-to, profile authoring guide, data repo usage) as capabilities mature.

## Recorder Blueprint
### Objectives
- Capture every backend-facing event (HTTP requests, uploads, RQ enqueues) with timestamps.
- Allow operators to mark the start/end of a profile capture while recording continues in the background for auditing.
- Produce a draft profile package (YAML + seed assets manifest) ready for curation.

### Components
- **Recorder Service (Frontend):**
  - Toggle control in the WEPPcloud interface (start/stop capture marker).
  - Interceptor wrapping the existing HTTP client helpers to log every request/response pair sent to the backend (including body metadata when safe).
  - Hook into RQ enqueue helpers to capture task name, payload, and resulting job id.
  - Metadata collector capturing session info (user id hash, theme, viewport) for the draft.
  - Buffer flushing mechanism to send events to backend in batches (debounced to avoid flooding).
- **Recorder API (Backend):**
  - Endpoints to accept event batches, persist raw logs, and snapshot relevant assets.
  - Hooks into existing RQ enqueue logic to tag jobs with recorder metadata.
  - Storage of capture state (active profile id, start/end markers, user notes).
- **Recorder Store (File-first):**
  - Appends every event to a JSONL log under the run working directory (for example `_logs/profile.events.jsonl`).
  - Maintains lightweight metadata files (e.g., `_logs/profile.captures.json`) indicating capture boundaries and notes.
  - Mirrors capture-specific slices into `/workdir/wepppy-test-engine-data/profiles/_drafts/<slug>/events.jsonl` when a profile is recorded (data repo is bind-mounted into the container).
  - Exposes a filesystem “tail” API so the assembler can react to each event immediately (used to snapshot assets before users overwrite them with later uploads).
- **Playback Service (FastAPI):**
  - Runs alongside WEPPcloud (`docker-compose.dev` service: `profile_playback`).
  - Resolves promoted profiles under `/workdir/wepppy-test-engine-data/profiles/<slug>`, clones their `run/` snapshot into `PROFILE_PLAYBACK_RUN_ROOT/<runid>`, and replays the event stream.
  - Authenticates with WEPPcloud using the admin credentials from `docker/.env` when a cookie is not provided, keeping the primary app’s authorization rules intact.
  - Exposes `/run/{profile}` for automation plus `/health` for monitoring; responses include the final run directory so downstream checks know which cloned workspace to inspect.

### Event Model
- Each recorded event includes:
  - `timestamp` (ISO-8601, UTC)
  - `category` (`http_request`, `rq_enqueue`, `file_upload`, `system_log`)
  - `payload` (sanitized details such as endpoint, params, task payload summaries)
  - `session` metadata (user hash, browser, viewport)
  - `run_context` (run id, config slug)
- Events flagged as sensitive (e.g., containing raw user identifiers) are hashed or redacted.

### Capture Workflow
1. User clicks “Mark Profile Start” in UI; backend stores capture boundary.
2. Recorder continues ingesting backend events (it was already running globally), tagging those between start/end markers inside the JSONL audit log.
3. User completes workflow and clicks “Mark Profile End”, optionally adding notes.
4. Background assembler (streaming):
   - Watches the JSONL audit file in near real-time, ingesting new events as they land.
   - For every event, snapshots referenced inputs/outputs immediately (preventing later uploads from overwriting seeds) and appends incremental state to the draft-in-progress.
   - Maintains an event ledger so the final profile can be reconstructed without reprocessing.
5. When the capture ends, the assembler finalizes the YAML (metadata, steps, comparisons placeholders) and writes the complete draft bundle for curation.

### UI Considerations
- Recorder status indicator (running, capturing, paused) visible in the header.
- Modal summarizing captured actions before commit (preview step list, ability to redact items).
- Access control: only authorized roles can export drafts; everyone sees audit log replay.

### Performance & Storage
- Event buffering designed to avoid blocking UI (use WebSocket or fetch with exponential backoff).
- JSONL audit files live alongside run logs; housekeeping tasks periodically trim or compress dormant runs.
- Draft retention policy (e.g., auto-expire uncurated drafts after 30 days, with notification).

### Next Steps for Recorder
1. Implement frontend HTTP/RQ interceptors and start/end marker controls.
2. Build backend collector endpoints with storage schema.
3. Implement streaming assembler job to transform raw events into draft profiles as they arrive.
4. Add basic draft review UI and CLI command to export a draft.

## Recorder Output & Storage Model
- **Audit stream:** `_logs/profile.events.jsonl` inside each run working directory contains every backend interaction with capture metadata. This file is always written, even when profile capture is inactive, providing traceability.
- **Capture manifest:** `_logs/profile.captures.json` records user-initiated capture windows (start/end timestamps, notes, optional slug hints). Empty when the recorder is effectively “off.”
- **Draft staging:** As events stream in, the assembler writes seed/baseline candidates into `/workdir/wepppy-test-engine-data/profiles/_drafts/<slug>/seed/<timestamp>-<hash>/...`, ensuring uploads are preserved even if the user replaces files later. When a capture closes, the assembler finalizes `events.jsonl`, `profile.yaml`, and supporting manifests under the same directory. The data repo is mounted read/write into the container.
- **Assembler entry point:** `profile_assembler_rq.py` (name TBD) reads the capture manifest, consumes the JSONL slice, generates `profile.yaml`, seeds, and baseline candidates, and drops a status record so curators know the draft is ready.
