# Outcome (2026-01-12)
- Review completed; findings resolved and tracker updated.

# Agent Prompt: Phase 4 Comprehensive Review

## Goal
Perform a comprehensive review of Phase 4 (deprecation cleanup) for the error schema standardization work package. Focus on regressions, missing updates, and documentation drift. Produce a review with findings prioritized by severity and file references.

## Scope
- Backend response helpers:
  - `wepppy/weppcloud/utils/helpers.py`
  - `wepppy/weppcloud/utils/helpers.pyi`
  - `wepppy/microservices/rq_engine/responses.py`
- RQ API routes that previously emitted legacy keys or 200-error responses.
- Frontend controllers and consoles:
  - `wepppy/weppcloud/controllers_js/*`
  - `wepppy/weppcloud/static-src/js/*`
  - `wepppy/weppcloud/static/js/*` (built outputs)
- Tests and fixtures (pytest, Jest, smoke).
- Documentation updates:
  - `docs/schemas/rq-response-contract.md`
  - `docs/work-packages/20260111_error_schema_standardization/tracker.md`
  - UI/dev docs that reference response shapes (see checklist).

## Review checklist
1. **Legacy keys fully removed**
   - Confirm `Success`, `success`, `Error`, `StackTrace`, and `jobId` are no longer emitted or required.
   - Use ripgrep to verify residual usage in runtime code. Treat archived/legacy docs as informational only.
2. **Canonical error shape**
   - Ensure error payloads match `{ error: { message, code?, details? }, errors?: [...] }`.
   - Check stacktrace rendering is sourced from `error.details` or `errors` arrays (no legacy stacktrace keys).
3. **Status-code-first behavior**
   - Validation/input errors should be 4xx; server exceptions remain 5xx.
   - Jobstatus/jobinfo still return HTTP 200 on `status: not_found` unless explicitly changed; verify tracker notes align.
4. **Client behavior and UI**
   - `WCHttp` and controllers should rely on HTTP status + canonical payloads.
   - Fork/archive consoles should parse error details and surface stacktraces without legacy aliases.
5. **Tests and coverage**
   - Validate that route tests, Jest, and smoke fixtures use canonical payloads.
   - Ensure coverage for endpoints called out in Phase 4 (archive/fork, landuse_and_soils, batch_runner, culvert).
6. **Documentation alignment**
   - Live docs should no longer show `Success`/`jobId` examples.
   - If historical docs retain legacy examples, note them as archival and acceptable.

## Suggested commands
```bash
rg -n "Success|success|Error|StackTrace|jobId" wepppy
rg -n "Success|success|Error|StackTrace|jobId" docs/ui-docs docs/dev-notes
rg -n "error\\s*:\\s*\\{\\s*message" wepppy/weppcloud/utils/helpers.py wepppy/microservices/rq_engine/responses.py
```

## Output expectations
- Provide a review report with findings ordered by severity (High/Medium/Low) and file references.
- List open questions or assumptions (e.g., jobstatus/jobinfo 404 vs 200).
- If no findings, state explicitly and call out any remaining testing/documentation gaps.

## Constraints
- Do not implement code changes; review only.
- Keep ASCII only.
- If you see `??` in the prompt, treat it as a directive to provide a critical response only (no code changes).
