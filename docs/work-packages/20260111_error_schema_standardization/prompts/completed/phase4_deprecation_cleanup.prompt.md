# Outcome (2026-01-12)
- Removed legacy response keys, aligned clients/tests/docs with canonical payloads, and switched jobstatus/jobinfo not_found to HTTP 404.

# Agent Prompt: Phase 4 Deprecation Cleanup

## Goal
Implement Phase 4 from `docs/work-packages/20260111_error_schema_standardization/tracker.md` by removing legacy error aliases and finalizing status-code-first behavior across rq-engine, rq/api, and clients.

## Scope
- Response helpers:
  - `wepppy/weppcloud/utils/helpers.py`
  - `wepppy/weppcloud/utils/helpers.pyi`
  - `wepppy/microservices/rq_engine/responses.py`
- RQ API routes and response helpers that still emit or consume legacy keys.
- Frontend controllers/tests that still reference `Success`, `success`, `Error`, `StackTrace`, or `jobId`.
- Tests + fixtures validating error payloads and job polling.

## Required changes
1. **Remove legacy keys**
   - Stop emitting `Success`, `success`, `Error`, `StackTrace`, and `jobId`.
   - Ensure canonical error payloads only: `{ error: { message, code?, details? }, errors?: [...] }`.
   - Update success payloads to avoid legacy aliases.

2. **Client cleanup**
   - Strip client-side fallback logic for legacy keys.
   - Ensure `WCHttp` and controllers depend on HTTP status + canonical payloads only.
   - Update UI error rendering to handle `error.details` and validation `errors` arrays.

3. **Job polling semantics**
   - If deprecation window is closed, switch jobstatus/jobinfo unknown jobs to HTTP 404.
   - If not ready, leave as HTTP 200 and document why in tracker.

4. **Tests and fixtures**
   - Update pytest/Jest/smoke tests to assert canonical payloads only.
   - Add coverage for routes that previously relied on legacy keys (archive/fork, landuse_and_soils, batch_runner, culvert).

5. **Docs and tracker**
   - Update `docs/schemas/rq-response-contract.md` if examples still include legacy keys.
   - Add a Phase 4 progress note in `docs/work-packages/20260111_error_schema_standardization/tracker.md`.

## Constraints
- Keep ASCII only.
- No new wrappers or abstraction layers.
- Avoid broad refactors outside error handling.

## Testing gates
- `wctl run-pytest tests/weppcloud/routes/test_rq_api_*`
- `wctl run-pytest tests --maxfail=1`
- `wctl run-npm lint`
- `wctl run-npm test`

## Notes
- Use `rg -n "Success|success|Error|StackTrace|jobId" wepppy` to locate remaining legacy references.
- Keep stacktrace logging for observability, but do not emit legacy keys in payloads.
