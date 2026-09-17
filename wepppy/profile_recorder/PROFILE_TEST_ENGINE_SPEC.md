# Profile Test Engine Specification
> Current behavior of the WEPPcloud profile recording, assembly, and playback toolchain.

## Overview
- Capture backend-visible WEPPcloud activity into per-run audit logs.
- Promote curated slices of those logs into portable “profiles” with seed assets.
- Rehydrate a sandbox and replay captured requests through the `profile_playback` service.
- Drive the pipeline from `wctl` commands so engineers and CI can exercise real workflows.

The stack favors append-only JSONL streams and direct filesystem snapshots over bespoke schemas. Profiles live alongside the application code while bulky run assets are mirrored into a sibling data repository.

## Data Roots
- `PROFILE_DATA_ROOT` (Flask config, default `/workdir/wepppy-test-engine-data`) anchors recorder output.
- Recorder audit logs land under `<run_dir>/_logs/profile.events.jsonl`. When the working directory is unknown, events fall back to `PROFILE_DATA_ROOT/audit/<sanitized-run>/profile.events.jsonl`.
- Draft profiles and promoted captures live under `PROFILE_DATA_ROOT/profiles/**`.
- Playback workspaces default to `/workdir/wepppy-test-engine-data/playback/runs/<sandbox_uuid>` and may be overridden via `PROFILE_PLAYBACK_BASE` / `PROFILE_PLAYBACK_RUN_ROOT`.

## Recorder Pipeline
1. `ProfileRecorder.append_event` accepts JSON events emitted by WEPPcloud middleware.
2. Events are normalized with UTC timestamps and optional non-PII user metadata.
3. The recorder resolves the run working directory (when possible) and appends the event to `_logs/profile.events.jsonl`.
4. When the assembler is enabled (`PROFILE_RECORDER_ASSEMBLER_ENABLED`, default `True`) the same event is forwarded for draft construction alongside file hints extracted from known payload keys.

Event payloads intentionally match what the playback runner expects: `stage` (`request` or `response`), `id`, `endpoint`, `method`, status data, and `requestMeta` for payload inspection.

## Recorder Privacy Standard
- Recorder artifacts (`_logs/profile.events.jsonl` and draft `capture/events.jsonl`) must not store email addresses.
- Recorder artifacts must not store JWTs, cookies, or `Authorization` header values.
- User attribution should use non-PII identifiers only (for example `user.id`).
- Treat this as a required contract for all recorder event schema changes.

## Streaming Assembler
- Drafts are created under `profiles/_drafts/<run>/<capture>` where `<capture>` defaults to `stream`.
- Every event is appended to `events.jsonl`; the assembler also stores the source run directory pointer (`run_dir.txt`) on first sight.
- File hints and upload events snapshot seed assets into `seed/`:
  - `seed/uploads/<type>/...` for landuse, SBS, CLI, cover transform, ash, and omni artifacts.
  - Task-driven rules (`TASK_RULES`) also capture derived outputs (DEM tiles, channel shapefiles) and record RON expectations in `validation.log`.
- `promote_draft(run_id, capture_id="stream", slug=Optional[str])` materializes a profile by copying the draft tree into `profiles/<slug>/capture` and cloning the run snapshot into `profiles/<slug>/run`.
- The assembler currently focuses on preservation. Higher-level YAML manifests or curated step lists do not exist yet; consumers read the JSONL stream directly.

### SBS event identity (intended; checkpoint pending)

New SBS response captures retain an immutable main-file seed and version1
receipt at`seed/uploads/sbs/events/<sha256(event-id)>/`, binding the event ID,
fixed local payload basename preserving the upload extension, length and SHA-256.
New eligible SBS response records include`_sbs_seed_version: 1` in their original
draft JSONL append, before fallible pointer/config/source/seed work. Playback
requires an event receipt for marked events even if its directory was never
created. Failed/partial capture evidence remains visible and promotion copies it.
The capture observes the existing controller-selected file at response time; it
is not a wire-level guarantee for arbitrary overlapping uploads.

Playback uses the paired event ID and verified retained bytes for its multipart
payload. An existing new event entry that is failed, incomplete, malformed or
mismatched fails explicitly; it cannot fall back to a different event/canonical
seed. Only an unmarked historical event without a new entry keeps legacy
canonical-first behavior with unverified historical identity. Existing profiles are not rewritten or stamped
on read. Receipt locations cannot select paths outside their event seed folder;
receipts retain no request secrets or PII. Other upload families are unchanged.

### SBS event performance acceptance (intended; checkpoint pending)

Use the reviewed actual 599,196-byte and 747,242-byte SBS fixtures and labeled
16,779,862-byte valid TIFF stress fixture. On local warm filesystem pages,
complete event capture must average at most 100 ms real /450 ms stress for an
established draft, and 125 ms real /550 ms stress for initial controller/draft/
config capture. Include actual owner lookup, event append, config/legacy seed
work, verified event copy and receipt publication. The first composed capture, including the complete configured primary seed,
must be measured on final implementation; separate baseline components are not
that acceptance evidence.

Complete event-bound form preparation through Requests multipart encoding must
average at most 20 ms real /150 ms stress, retaining the verified bytes, field,
MIME and accepted extension. It should read the retained payload once and avoid
an additional full-size retained copy beyond existing Requests buffering;
report final Python allocation peak separately from process RSS. Network,
server/native execution, promotion/archive and full HTTP playback are separate
acceptance requirements.

These are component mean budgets, not cold-storage or percentile guarantees and
not a new size limit. Larger supported files need additional size-aware
observation. Retain aggregate seed growth and follow existing seed/LFS guidance;
do not discard per-event identity to reduce copies. Evidence/rationale live in
`docs/work-packages/20260916_file_dependency_freshness/artifacts/sbs_receipts_profile_performance_qa.md`
and its linked script/JSON/log. Final implementation must be remeasured with all
required confinement and generation guards; the prototype is not a pass.

## Profile Layout
```
profiles/<slug>/
  capture/
    events.jsonl          # ordered response stream (requests are embedded via ids)
    seed/                 # uploads and task artifacts
      uploads/...
      <task-label>.missing/.dir.exists markers
    validation.log        # optional task-rule notes
    run_dir.txt           # optional pointer back to originating run
  run/                    # sandbox-friendly copy of the original working directory snapshot
```

Playback also looks for `capture/seed/uploads/<type>` when rebuilding multipart requests.

## Playback Service (`services/profile_playback/app.py`)
- FastAPI app exposing:
  - `GET /health` – liveness check.
  - `POST /run/{profile}` – stream playback logs as plain text.
  - `GET /run/result/{token}` – retrieve structured results persisted to `profiles/_runs/<token>.json`.
  - `POST /fork/{profile}` – run the WEPPcloud fork flow inside the sandbox run (waits for RQ job completion).
  - `POST /archive/{profile}` – trigger archive jobs against a sandbox run.
- Environment knobs:
  - `PROFILE_PLAYBACK_ROOT` – profile library root (defaults to `/workdir/wepppy-test-engine-data/profiles`).
  - `PROFILE_PLAYBACK_RUN_ROOT`, `PROFILE_PLAYBACK_FORK_ROOT`, `PROFILE_PLAYBACK_ARCHIVE_ROOT` – sandbox destinations for run, fork, and archive artifacts.
  - `PROFILE_PLAYBACK_BASE_URL` – default WEPPcloud origin (`https://wc.bearhive.duckdns.org/weppcloud`).
  - `PROFILE_PLAYBACK_COLOR` / `NO_COLOR` – toggle ANSI color output (`True` by default unless `NO_COLOR` is set).
  - `ADMIN_EMAIL` / `ADMIN_PASSWORD` – required for automated authentication when a raw cookie is not supplied.
- Streaming output arrives via an asyncio queue; each log line is formatted with ANSI colors:
  - Timestamps and `[profile_playback]` tag: bright magenta.
  - `HTTP 2xx`: bright green; non-2xx statuses: bright red.
  - `job <uuid>` tokens: purple3.
  - URLs: dodger_blue2.
  - Captured JSON payloads or response previews: bright green.
  - Users can opt out with `PROFILE_PLAYBACK_COLOR=0` or by exporting `NO_COLOR`.

## Playback Session Semantics (`wepppy/profile_recorder/playback.py`)
- Profiles are rooted at `<data_root>/profiles/<slug>`; playback requires `capture/events.jsonl` and optionally `run/`.
- Run discovery:
  - The runner reads `events.jsonl` (line-delimited JSON).
  - First request event containing `/runs/<runid>/` establishes the original run id.
  - Playback uses `profile;;tmp;;<sandbox_uuid>` run IDs (minted by the FastAPI service) to isolate mutations from the source snapshot while retaining the original identifier for reporting; standalone CLI usage without the service falls back to `profile;;tmp;;<original>`.
- Workspace preparation:
  - If `profiles/<slug>/run/` exists it is copied into the sandbox location before requests execute.
  - Seed assets from `capture/seed/**` hydrate expected uploads (landuse, SBS, CLI, cover transform, ash, omni) and config defaults.
  - `clear_locks` is called for both the sandbox and original run ids to avoid stale Redis locks.
- Request replay rules:
  - Only 2xx response events with matching request metadata are executed.
  - Supports GET and POST (JSON or known form-data). Unsupported payloads are logged and recorded as failures.
  - Paths are remapped from `/runs/<original>/...` to `/runs/{playback_run_id}/...`, ensuring NoDb resolves the sandbox workspace.
  - Elevation queries and recorded `rq-engine/api/jobstatus/` polls are skipped; playback polls real jobs instead.
  - After each POST, the runner inspects the JSON response for `job_id` and waits for completion via `/rq-engine/api/jobinfo/<id>` before proceeding.
  - Additional polling is performed for GETs ending with known work-complete suffixes (`_WAIT_SUFFIXES`).
  - Responses are summarized in `PlaybackSession.results`, exposed through the streamed log and persisted run report.
  - Verbose mode logs request line, parameters, payload hints, status codes, response previews, and job tracking messages.

## `wctl` Integration (`tools/wctl2/commands/playback.py`)
- `wctl run-test-profile <slug>`:
  - Resolves `PROFILE_PLAYBACK_URL` (default `http://127.0.0.1:8070`), base URL, and optional cookie.
  - Prints the request context to `stderr` and streams the FastAPI response to `stdout`.
  - Falls back to a non-streaming POST when chunked encoding fails (rare on misconfigured proxies).
- Additional helpers: `wctl run-fork-profile` and `wctl run-archive-profile` front the `/fork/` and `/archive/` endpoints and emit JSON responses.

## Authentication & Session Handling
- When a cookie is provided, it is forwarded verbatim to both playback and WEPPcloud.
- Otherwise the service logs in with `ADMIN_EMAIL` / `ADMIN_PASSWORD` against the HTTPS host to honor the `Secure` cookie flag, mirrors cookies across hosts if required, and reuses the authenticated `requests.Session`.
- Playback exposes login successes as INFO logs so streaming callers can confirm authentication state.

## Result Storage & Retrieval
- Every successful playback stores a `ProfileRunResult` JSON file under `profiles/_runs/<token>.json` containing profile slug, resolved run ids, run directory, report, and per-request outcome list.
- The streamed log includes the token and result path for quick lookup.

## Fork and Archive Helpers
- `POST /fork/{profile}`:
  - Copies the profile run snapshot into the sandbox.
  - Authenticates, submits `/rq-engine/api/runs/<runid>/<config>/fork`, waits for the job via `/rq-engine/api/jobinfo/<id>`, and copies resulting fork artifacts into `PROFILE_PLAYBACK_FORK_ROOT`.
- `POST /archive/{profile}`:
  - Repeats the sandbox copy/authentication flow, submits `/rq-engine/api/runs/<runid>/<config>/archive`, waits for completion, and mirrors generated archives into `PROFILE_PLAYBACK_ARCHIVE_ROOT/<runid>`.
- Both endpoints reuse the colorized log formatter so their status messages integrate cleanly with the streaming output.

## Limitations & Backlog
- Recorder does not yet expose explicit “start/stop capture” signals in the UI; it streams all backend events continuously.
- Profile assembly stops at event preservation plus seed snapshots; higher level manifests (`profile.yaml`, ordered step descriptions, diff baselines) are future work.
- Playback expects the data repository to provide required seed uploads; missing artifacts are reported but not regenerated.
- Parallel playback runs share global Redis locks; queuing long-running profiles may require coordination.
- Fork/Archive helpers assume RQ job APIs remain stable; additional error surface (e.g., transient failures) should be captured in future revisions.

## Operational Checklist
- Ensure `wepppy-test-engine-data` (or custom `PROFILE_DATA_ROOT`) is mounted read/write in the environment hosting WEPPcloud and the playback service.
- Export admin credentials in the playback service environment or provide cookies via `wctl`.
- Keep profile directories under version control (or a synced data repository) so CI/CD can run the same captures.
- Use `NO_COLOR=1` when streaming logs to sinks that cannot parse ANSI escape codes.
