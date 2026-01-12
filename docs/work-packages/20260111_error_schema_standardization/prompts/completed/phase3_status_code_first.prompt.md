# Outcome (2026-01-12)
- Shifted validation errors to 4xx, kept 5xx for server faults, and updated clients/tests for canonical errors.

# Agent Prompt: Phase 3 Status-Code-First Errors

## Goal
Implement Phase 3 from `docs/work-packages/20260111_error_schema_standardization/tracker.md` by shifting rq-engine and weppcloud rq/api error handling to status-code-first semantics while preserving legacy keys for compatibility.

## Scope
- Backend response helpers:
  - `wepppy/weppcloud/utils/helpers.py`
  - `wepppy/microservices/rq_engine/responses.py`
- RQ API routes that currently return HTTP 200 with `Success: False` or `success: False` for validation/input errors.
- Frontend controllers/tests that assume HTTP 200 on error.

## Required changes
1. **Status codes**
   - Convert validation/input errors to HTTP 4xx (prefer 400/403/404 as appropriate).
   - Reserve 5xx for server errors and exception paths.
   - Keep jobstatus/jobinfo `status: not_found` on HTTP 200 (do not introduce 404 yet).

2. **Canonical error shape**
   - Emit canonical error payloads per `docs/schemas/rq-response-contract.md`:
     - `{ error: { message, code?, details? }, errors?: [...] }`
   - Preserve legacy aliases (`Success`, `Error`, `StackTrace`) during Phase 3.

3. **Client updates**
   - Adjust `WCHttp`/controller error handling to rely on HTTP status + canonical error payloads.
   - Update any controller logic that checks `Success` or `success` to accept the new error paths.

4. **Tests and fixtures**
   - Update pytest route tests to assert new status codes and error shapes.
   - Update frontend test stubs (Jest + smoke) to reflect canonical error payloads and status handling.

5. **Tracker update**
   - Add a Phase 3 progress note in `docs/work-packages/20260111_error_schema_standardization/tracker.md`.

## Constraints
- Do not remove legacy keys or aliases yet (Phase 4 handles removal).
- Keep ASCII only.
- Avoid broad refactors outside error handling.

## Testing gates
- `wctl run-pytest tests/weppcloud/routes/test_rq_api_*`
- `wctl run-pytest tests --maxfail=1`
- `wctl run-npm lint`
- `wctl run-npm test`

## Notes
- Use `rg -n "Success" wepppy/weppcloud/routes` to locate routes returning HTTP 200 errors.
- Pay attention to `batch_runner` and `archive_console` flows; ensure UI errors render correctly.
