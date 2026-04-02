# Run Sync Dashboard Source Token Integration

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Reference standard: `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, Run Sync Dashboard supports an optional source run token that is forwarded through rq-engine and used by `run_sync_rq` to authenticate remote fetches (`aria2c.spec` + file pulls). Private-run sync imports no longer require anonymous access on the source host.

## Progress

- [x] (2026-04-01 20:00Z) Created package, tracker, and active ExecPlan.
- [x] (2026-04-01 20:05Z) Verified current run-sync path is tokenless (`headers = {}` in worker).
- [x] (2026-04-01 20:25Z) Implemented dashboard form + JS payload field for optional source token.
- [x] (2026-04-01 20:30Z) Implemented rq-engine run-sync route payload propagation into worker enqueue.
- [x] (2026-04-01 20:35Z) Implemented worker bearer-header support for spec + aria2 requests.
- [x] (2026-04-01 20:50Z) Added regression tests and ran QA gates.
- [x] (2026-04-01 21:00Z) Updated docs + tracker and moved ExecPlan to `prompts/completed/`.

## Surprises & Discoveries

- Observation: Existing run-sync UI uses a dashboard-scoped rq-engine token (`rq:enqueue`) but has no per-source authorization field.
  Evidence: `wepppy/weppcloud/routes/run_sync_dashboard/run_sync_dashboard.py`, `wepppy/weppcloud/controllers_js/run_sync_dashboard.js`.
- Observation: `_serialize_job` fallback extraction used mismatched positional indexes for queued run-sync jobs.
  Evidence: `wepppy/microservices/rq_engine/run_sync_routes.py` (`config` and `source_host` were not aligned with enqueue arg layout).

## Decision Log

- Decision: Accept a user-supplied source token in dashboard payload and keep the field optional.
  Rationale: target host cannot guarantee source-host-signed token minting; this preserves existing tokenless behavior while enabling private source access.
  Date/Author: 2026-04-01 / Codex

## Outcomes & Retrospective

- Delivered:
  - Optional `source_run_token` dashboard field and payload wiring.
  - rq-engine run-sync payload propagation of optional source token into `run_sync_rq`.
  - `run_sync_rq` bearer header usage for `_download_spec(...)` and `_run_aria2c(...)`.
  - Job serialization fallback fix for `config`/`source_host` arg indexes.
  - Code/QA review artifacts:
    - `docs/work-packages/20260401_run_sync_source_token_integration/artifacts/code_review_findings.md`
    - `docs/work-packages/20260401_run_sync_source_token_integration/artifacts/qa_review_findings.md`
- Validation summary:
  - `wctl run-pytest tests/microservices/test_rq_engine_run_sync_routes.py tests/rq/test_run_sync_rq.py --maxfail=1` (`7 passed`)
  - `wctl run-npm lint` (pass)
  - `wctl check-rq-graph` (pass; artifacts refreshed)
  - `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` (`PASS`)
  - `wctl doc-lint --path docs/run_migration_strategy.md --path wepppy/rq/job-dependencies-catalog.md --path docs/standards/broad-exception-boundary-allowlist.md --path docs/work-packages/20260401_run_sync_source_token_integration --path PROJECT_TRACKER.md` (`7 files validated, 0 errors, 0 warnings`)

## Context and Orientation

Primary touchpoints:
- `wepppy/weppcloud/routes/run_sync_dashboard/templates/rq-run-sync-dashboard.htm`
- `wepppy/weppcloud/controllers_js/run_sync_dashboard.js`
- `wepppy/microservices/rq_engine/run_sync_routes.py`
- `wepppy/rq/run_sync_rq.py`
- `wepppy/rq/run_sync_rq.pyi`
- `tests/microservices/test_rq_engine_run_sync_routes.py`
- `tests/rq/test_run_sync_rq.py`

## Plan of Work

Add an optional `source_run_token` control on Run Sync Dashboard and include it in submit payload. rq-engine run-sync route will parse and forward this optional token to `run_sync_rq`. Worker will derive request headers from token (`Authorization: Bearer ...`) for `_download_spec(...)` and `_run_aria2c(...)`.

Preserve current behavior when token is empty/missing. Do not store token in status messages, migration table, or provenance. Add regression tests for propagation and header usage.

## Concrete Steps

From `/workdir/wepppy`:

1. Update dashboard template and controller payload serialization:
   - `wepppy/weppcloud/routes/run_sync_dashboard/templates/rq-run-sync-dashboard.htm`
   - `wepppy/weppcloud/controllers_js/run_sync_dashboard.js`
2. Update rq-engine run-sync route payload parsing and enqueue call:
   - `wepppy/microservices/rq_engine/run_sync_routes.py`
3. Update worker function signature and header logic:
   - `wepppy/rq/run_sync_rq.py`
   - `wepppy/rq/run_sync_rq.pyi`
4. Add regression tests:
   - `tests/microservices/test_rq_engine_run_sync_routes.py`
   - `tests/rq/test_run_sync_rq.py`
5. Update docs:
   - `docs/run_migration_strategy.md`
   - `wepppy/rq/job-dependencies-catalog.md`
6. Run validation:
   - `wctl run-pytest tests/microservices/test_rq_engine_run_sync_routes.py tests/rq/test_run_sync_rq.py --maxfail=1`
   - `wctl doc-lint --path docs/run_migration_strategy.md --path wepppy/rq/job-dependencies-catalog.md --path docs/work-packages/20260401_run_sync_source_token_integration`
   - `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`

## Validation and Acceptance

Acceptance checks:
- run-sync route accepts optional `source_run_token` and enqueues successfully.
- `run_sync_rq` sends bearer header for `aria2c.spec` and aria2 fetches when token provided.
- tokenless run-sync path is unchanged.
- Tests pass for both payload and worker behavior.
- Docs and package tracker reflect final behavior.

## Idempotence and Recovery

- Re-submitting the same run sync request remains idempotent from route perspective; queue behavior unchanged.
- If token is invalid, worker reports explicit exception and migration row status `EXCEPTION`, preserving current error contracts.
- No persisted schema changes are required.

## Artifacts and Notes

- Captured final review findings in:
  - `docs/work-packages/20260401_run_sync_source_token_integration/artifacts/code_review_findings.md`
  - `docs/work-packages/20260401_run_sync_source_token_integration/artifacts/qa_review_findings.md`

## Interfaces and Dependencies

Planned payload addition:

    {
      "runid": "<runid>",
      "source_host": "wepp.cloud",
      "source_run_token": "<optional jwt>",
      "run_migrations": true,
      "archive_before": false
    }

Planned worker behavior:
- when `source_run_token` is non-empty, set `Authorization: Bearer <token>` in headers.
- pass headers to both `_download_spec(...)` and `_run_aria2c(...)`.
