# Agent Prompt: Phase 1 Compatibility Layer (RQ Response Contract)

## Goal
Implement Phase 1 from `docs/work-packages/20260111_error_schema_standardization/tracker.md` by adding a compatibility layer that emits canonical keys (`job_id`, `job_ids`, `error`) while preserving legacy aliases (`jobId`, `Success`, `Error`, `StackTrace`). Align with `docs/schemas/rq-response-contract.md`.

## Scope
- Backend response helpers:
  - `wepppy/weppcloud/utils/helpers.py`
  - `wepppy/microservices/rq_engine/responses.py`
- RQ API routes that emit job submission payloads, especially run sync:
  - `wepppy/weppcloud/routes/run_sync_dashboard/run_sync_dashboard.py`
- Frontend normalization layer:
  - `wepppy/weppcloud/controllers_js/http.js`
  - `wepppy/weppcloud/controllers_js/control_base.js`

## Required changes
1. **Canonical job id keys**
   - Ensure job submission responses include `job_id` (single) and optionally `job_ids` (multi).
   - Preserve specialized fields (for example `sync_job_id`, `migration_job_id`). If you add `job_ids` for run sync, keep specialized fields and set `job_id` to the primary job id.
   - Keep legacy alias `jobId` where compatibility is needed.

2. **Canonical error keys**
   - Response helpers should emit canonical `error` payloads while preserving legacy `Error` and `StackTrace` fields (Phase 1 only).
   - Do not change status codes yet; focus on key normalization.

3. **Client normalization**
   - Normalize legacy keys in a single place (prefer `WCHttp` helpers):
     - `jobId` -> `job_id`
     - `Success`/`success` -> `success` (or map to a boolean field used consistently by controllers)
     - `Error` -> `error`
     - `StackTrace` -> `stacktrace`
   - Ensure `control_base` uses the normalized fields for jobstatus/jobinfo handling.

## Constraints
- Do not implement Phase 2 or 3 work (no archive_console pipeline move, no status-code changes).
- Keep legacy keys until Phase 4.
- Preserve existing behavior for jobstatus/jobinfo `status: not_found` (no 404 change).
- ASCII only.

## Deliverables
- Code updates per the scope above.
- Update `docs/work-packages/20260111_error_schema_standardization/tracker.md` with a Phase 1 progress note and any open questions.

## Testing gates
- `wctl run-pytest tests/weppcloud/routes/test_rq_api_*`
- `wctl run-npm lint`
- `wctl run-npm test -- <affected suites>` (note which suites you ran)

## Notes
- Use `rg -n "jobId|Success|Error|StackTrace"` to locate normalization sites.
- Keep changes tight and avoid refactoring unrelated logic.
