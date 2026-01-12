# Tracker – Error Schema Standardization (RQ API Migration)

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Started**: 2026-01-11  
**Current phase**: Phase 4 deprecation cleanup  
**Last updated**: 2026-01-11  
**Next milestone**: Phase 4 validation + test gates

## Task Board

### Ready / Backlog
- [ ] Validate rq-response contract with stakeholders

### In Progress
- [ ] Phase 4: deprecation cleanup (remove legacy keys, align clients/tests)

### Blocked
- [ ]

### Done
- [x] Work package created (2026-01-11)
- [x] Inventoried rq-engine response schemas and status codes
- [x] Inventoried weppcloud rq/api response schemas and status codes
- [x] Mapped frontend callsites that interpret `success`/`Success` or job status
- [x] Mapped backend callsites that interpret `success`/`Success` or job status
- [x] Drafted standard schema recommendations + migration notes
- [x] Authored `observed-error-schema-usages-report.md` artifact
- [x] Authored `docs/schemas/rq-response-contract.md`
- [x] Phase 1: response helper compatibility + client normalization
- [x] Phase 2: move `archive_console.js` into static-src build pipeline
- [x] Phase 3: status-code-first error responses + legacy key deprecation plan

## Timeline

- **2026-01-11** – Package created, initial scoping completed

## Decisions Log
### 2026-01-11
- Standardize job submission payloads on `job_id` and `job_ids`; keep `jobId` as a compatibility alias.
- Specialized job fields (for example `sync_job_id`, `migration_job_id`) may remain, but must include canonical job ids.
- Move `archive_console.js` into the standard static-src build pipeline.
- Keep `status: not_found` with HTTP 200 during the deprecation window; revisit 404 later.

## Implementation Plan
### Phase 0 - Contract (done)
- Publish `docs/schemas/rq-response-contract.md` and align stakeholders on canonical keys and error shapes.
- Gate: doc review sign-off.

### Phase 1 - Compatibility layer
- Response helpers emit canonical `job_id`/`job_ids` and `error` payloads while keeping legacy aliases.
- Client normalization in `WCHttp`/`control_base` maps `jobId`, `Success`, `Error`, `StackTrace` to canonical fields.
- Gate: `wctl run-pytest tests/weppcloud/routes/test_rq_api_*`, `wctl run-npm lint`, `wctl run-npm test -- <affected suites>`.

### Phase 2 - Archive console pipeline
- Move `archive_console.js` source into `wepppy/weppcloud/static-src/`, rebuild assets, and update references.
- Gate: `wctl build-static-assets`, `wctl run-npm test -- console_smoke` (if available), plus targeted smoke checks.

### Phase 3 - Status-code-first errors
- Shift validation errors to 4xx, server errors to 5xx; stop returning error payloads with HTTP 200.
- Update controllers/tests to rely on HTTP status + canonical error payloads.
- Gate: `wctl run-pytest tests --maxfail=1`, `wctl run-npm test`, `wctl run-npm lint`.

### Phase 4 - Deprecation cleanup
- Remove legacy keys (`Success`, `success`, `Error`, `StackTrace`, `jobId`) once clients are updated.
- Optional: switch jobstatus/jobinfo unknown jobs to HTTP 404 after deprecation window ends.
- Gate: targeted regression + smoke coverage for job polling and submission flows.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Incomplete inventory due to hidden callsites | Medium | Medium | Use rg across weppcloud + rq-engine + static-src, and note unknowns explicitly | Open |
| Breaking client assumptions during future migration | High | Medium | Document semantics per endpoint before proposing schema changes | Open |

## Verification Checklist

### Documentation
- [x] Report artifact completed
- [x] Package tracker updated with findings

## Progress Notes

### 2026-01-11: Package setup
**Agent/Contributor**: Codex

**Work completed**:
- Created package scaffolding and prompt

**Next steps**:
- Run the prompt to build the schema usage report

### 2026-01-11: Observed schema inventory completed
**Agent/Contributor**: Codex

**Work completed**:
- Inventoried rq-engine and weppcloud rq/api response schemas, status codes, and helper payloads
- Mapped frontend (controllers_js, static) and backend callsites for rq/api and rq-engine usage
- Drafted redundancy analysis and target schema recommendations

**Open questions**:
- rq-engine `error_response` ignores `status_code` arguments in `culvert_routes.py`; confirm intended HTTP codes for culvert retry errors
- No in-repo client uses `/rq/api/landuse_and_soils*` or culvert ingestion routes; confirm ownership and deprecation status
- `error_factory` still returns HTTP 200 for validation failures; decide if clients are ready to move to 4xx

### 2026-01-11: Contract + plan drafted
**Agent/Contributor**: Codex

**Work completed**:
- Authored `docs/schemas/rq-response-contract.md`
- Added multiphase implementation plan with testing gates

**Decisions captured**:
- Canonical job ids: `job_id` and `job_ids` with `jobId` as a compatibility alias
- `archive_console.js` should move into the standard static-src pipeline
- Keep `status: not_found` with HTTP 200 during deprecation window

### 2026-01-11: Phase 1 compatibility updates
**Agent/Contributor**: Codex

**Work completed**:
- Added canonical `error`/`stacktrace` fields to error helpers while preserving `Success`, `Error`, and `StackTrace`
- Updated run sync submission responses to include `job_id`, `job_ids` (when migrations are queued), and `jobId` alias
- Normalized legacy keys in `WCHttp` and updated `control_base` to consume normalized error/stacktrace fields

**Open questions**:
- Decision: preserve canonical error objects in client normalization and derive `error_message` for string consumers.

### 2026-01-11: Phase 1 compatibility peer pass
**Agent/Contributor**: Codex

**Work completed**:
- Added legacy keys and canonical `stacktrace` to rq-engine validation error responses
- Added `StackTrace`/`stacktrace` to `error_factory` responses
- Preferred canonical error/stacktrace fields in `control_base` resolution helpers

**Open questions**:
- Decision: preserve canonical error objects in client normalization and derive `error_message` for string consumers.

### 2026-01-11: Phase 1 error object preservation
**Agent/Contributor**: Codex

**Work completed**:
- Updated `WCHttp` normalization to keep canonical error objects and add `error_message` for string consumers
- Adjusted batch runner and project error messaging to prefer `error_message`

### 2026-01-11: Phase 2 archive console pipeline
**Agent/Contributor**: Codex

**Work completed**:
- Moved `archive_console.js` source into static-src and wired build output to `static/js/archive_console.js`
- Updated build tooling and Docker image copy step to include the archive console asset

### 2026-01-11: Phase 3 status-code-first errors
**Agent/Contributor**: Codex

**Work completed**:
- Shifted rq/api validation errors to HTTP 4xx while keeping 5xx for server faults
- Updated error helpers to emit canonical error objects with legacy keys preserved
- Adjusted WCHttp/batch runner/archive console error handling and refreshed route + frontend tests

**Next steps**:
- Run Phase 3 test gates (pytest + npm lint/test)

### 2026-01-11: Phase 3 observability refinements
**Agent/Contributor**: Codex

**Work completed**:
- Documented error helper usage in `docs/dev-notes/controller_foundations.md`
- Added stacktrace capture + logging for `error_factory` and rq-engine validation responses
- Extended WCHttp to recognize canonical `error.details`
- Added route tests for landuse/soils and archive/fork 4xx payloads
- Added WCHttp unit coverage for `error.details` fallback

### 2026-01-11: Phase 4 deprecation cleanup
**Agent/Contributor**: Codex

**Work completed**:
- Removed legacy key expectations in backend/frontend tests and smoke fixtures in favor of canonical error payloads.
- Updated control-base stacktrace handling to read `error.details` for display.
- Aligned batch runner, interchange, and upload helpers/tests with canonical response shapes.

**Open questions**:
- Keep jobstatus/jobinfo `status: not_found` on HTTP 200, or move to 404 now that Phase 4 is underway?
