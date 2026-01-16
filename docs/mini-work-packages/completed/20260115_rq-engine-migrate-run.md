# Mini Work Package: rq-engine migrate/run + migrate page polling
Status: Complete
Last Updated: 2026-01-15
Primary Areas: `wepppy/microservices/rq_engine/*`, `wepppy/weppcloud/routes/run_0/run_0_bp.py`, `wepppy/weppcloud/routes/run_0/templates/run_0/rq-migration-status.htm`, `docs/schemas/rq-response-contract.md`

## Objective
Move migration enqueue to rq-engine with JWT auth and update the migrate page to poll canonical jobinfo/jobstatus endpoints so `/migrate/status/` can be removed and remote JWT-based batch migrations are possible.

## Scope
- Add rq-engine migration enqueue route (kebab-case) under `/rq-engine/api/runs/<runid>/<config>/migrate-run` that calls `migrations_rq`, respects locks/readonly, stores the migration job id, and returns canonical RQ response (`job_id`, `status_url`, `message`).
- Enforce JWT (`rq:enqueue`) + run authorization (`authorize_run_access` or `runs` claim for service tokens).
- Update migrate page JS to:
  - use `WCHttp.postJsonWithSessionToken` for enqueue,
  - rely on `job_id`/`status_url` instead of legacy `Content`,
  - poll `/rq-engine/api/jobstatus/<job_id>` and render state from canonical fields (fetch jobinfo only after completion for results).
- Remove Flask routes `/runs/<runid>/<config>/migrate/run` and `/runs/<runid>/<config>/migrate/status/<job_id>`.
- Keep `migration_page` route for UI; update any token bootstrap if needed.

## Non-goals
- Changing migration logic or file formats.
- Reworking run ownership rules beyond existing auth helpers.
- Redesigning the migrate page layout.

## Plan
### Phase 1 - API design + auth policy
- Confirm JWT policy:
  - `rq:enqueue` required.
- Admin role overrides run claims (including service tokens).
  - `token_class=user` -> `authorize_run_access`.
  - `token_class=session` -> `require_session_marker`.
  - `token_class=service` -> `runs` claim must include target run unless admin.
- Confirm response matches `docs/schemas/rq-response-contract.md`.

### Phase 2 - rq-engine route implementation
- Add new router module (e.g. `migration_routes.py`) and include in `wepppy/microservices/rq_engine/__init__.py`.
- Port queuing logic from `run_0_bp.run_migrations`:
  - run existence check, lock gate, readonly toggle/restore, enqueue `migrations_rq`.
  - `RedisPrep.set_rq_job_id("migrations", job.id)` + `StatusMessenger.publish`.
- Use `error_response`/`error_response_with_traceback`; return 202 with `job_id` + `status_url`.

### Phase 3 - Migrate page updates
- Update `run_0/rq-migration-status.htm` JS to call the rq-engine enqueue endpoint and poll `jobinfo`/`jobstatus` under `/rq-engine/api/*`.
- Switch to canonical response parsing (`job_id`, `message`, `result`, `error`).
- Prefer `status_url` when present; fallback to `/rq-engine/api/jobinfo/<job_id>`.
- Handle `status=not_found` and `exc_info` in polling UI.

### Phase 4 - Remove legacy Flask endpoints
- Drop `/migrate/run` and `/migrate/status/<job_id>` routes from `run_0_bp`.
- Remove any references to `/migrate/status/` in templates.

### Phase 5 - Tests + validation
- Add rq-engine tests for migration enqueue auth and response shape.
- Add template render or JS unit test for migrate page if coverage exists.
- Manual smoke: migrate a run, verify polling via jobinfo/jobstatus, confirm readonly restoration.

## Implementation Notes
- migrate-run emits canonical errors (including `error.details` for 5xx) via `error_response_with_traceback`.
- Migration UI renders stacktraces safely via text nodes and keeps polling on `job_id`.

## Verification checklist
- [x] Enqueue returns HTTP 202 with `job_id` + `status_url` and no legacy `Content`.
- [x] Migrate page polls `/rq-engine/api/jobstatus/<job_id>` and fetches jobinfo on completion.
- [x] `/runs/<runid>/<config>/migrate/status/*` no longer registered.
- [x] Remote JWT token (service/user/session) can enqueue migration when authorized; unauthorized tokens fail with canonical error payload.
- [x] Error payloads include `error.details` for exception-driven failures.

## Validation
- Tests: `wctl run-pytest tests/microservices/test_rq_engine_migration_routes.py`
- Tests: `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py`
- Manual: run `lt_202012_0_Near_Burton_Creek_Thinn96/cfg` migration via rq-engine.

## Risks / Notes
- Migration page depends on `WCHttp` availability; ensure the template still loads it.
- Session-token issuance must be reachable for migrate page requests; ensure cookies permit `/rq-engine`.
- Auth policy should preserve owner/admin behavior from Flask (avoid loosening access).

## Decisions
- Route path: `/migrate-run`.
- Admin role bypasses run-claim enforcement.
- Poll jobstatus; fetch jobinfo only when a terminal state is reached.
