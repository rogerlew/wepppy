# Tracker - RQ WEPP Subwta Precondition Contract Enforcement

> Living document tracking progress, decisions, risks, and validation for strict watershed abstraction-state enforcement on WEPP run endpoints.

## Quick Status

**Timezone**: UTC
**Started**: 2026-04-27 20:20 UTC
**Current phase**: Closed
**Last updated**: 2026-04-27 20:44 UTC
**Next milestone**: None; package closed
**Security impact**: `low`
**Dedicated security review**: `no`
**Security artifact**: `N/A`

## Task Board

### Ready / Backlog
- None.

### In Progress
- None.

### Blocked
- None.

### Done
- [x] Package scaffold created (`package.md`, `tracker.md`, active ExecPlan path) (2026-04-27 20:20 UTC).
- [x] User decision recorded: `watershed.subwta` is always required because removed `subwta.tif` invalidates hillslope/watershed integrity (2026-04-27 20:20 UTC).
- [x] Strict abstraction-state gate now runs before batch/base acknowledgement for `run-wepp` and `run-wepp-watershed` (2026-04-27 20:33 UTC).
- [x] `checkbox_wepp_watershed=false` cannot bypass missing-`subwta` rejection (2026-04-27 20:33 UTC).
- [x] Canonical contract docs and schema-default error metadata updated for strict enforcement (2026-04-27 20:33 UTC).
- [x] Targeted route/schema regression tests added and passing (2026-04-27 20:33 UTC).
- [x] Reviewer and QA reviewer findings dispositioned in code/docs (2026-04-27 20:43 UTC).
- [x] Final targeted validation rerun passed after reviewer dispositions (2026-04-27 20:43 UTC).
- [x] Package closure notes written and active ExecPlan archived (2026-04-27 20:43 UTC).
- [x] Final doc-lint and diff-check gates passed (2026-04-27 20:44 UTC).

## Timeline

- **2026-04-27 20:20 UTC** - Package created from deferred review findings.
- **2026-04-27 20:20 UTC** - Strict contract decision captured from user directive.
- **2026-04-27 20:33 UTC** - Implemented strict gate ordering and metadata/docs/tests; targeted pytest passed (`118 passed`).
- **2026-04-27 20:43 UTC** - Disposed reviewer findings: rejected precondition paths are non-mutating, and recovery metadata documents batch/_base limits.
- **2026-04-27 20:43 UTC** - Reran targeted pytest (`118 passed`) and closed package lifecycle docs.
- **2026-04-27 20:44 UTC** - Final doc-lint and `git diff --check` passed.

## Decisions Log

### 2026-04-27 20:20 UTC: `watershed.subwta` is always required on WEPP run endpoints
**Context**: Deferred review findings identified ambiguity around batch/base exceptions and `checkbox_wepp_watershed=false` behavior.

**Options considered**:
1. Require `subwta` only when watershed routine is enabled.
2. Require `subwta` for all `run-wepp` and `run-wepp-watershed` requests.

**Decision**: Option 2.

**Impact**: Endpoint contract is strict; no batch/base or checkbox path can bypass `subwta` precondition.

### 2026-04-27 20:43 UTC: Gate before payload application
**Context**: The route already parses and applies WEPP payload settings before returning batch/base acknowledgement.

**Decision**: Run the strict `subwta` gate immediately after resolving the run directory and before parsing/applying payload settings.

**Impact**: Missing `subwta.tif` produces the canonical `409 invalid_watershed_abstraction_state` response in normal, batch, `_base`, and checkbox-toggled contexts without persisting rejected request payload mutations.

### 2026-04-27 20:43 UTC: Recovery metadata documents batch/_base limits
**Context**: `build-subcatchments-and-abstract-watershed` is the normal-mode recovery route, but it preserves existing batch/_base no-queue behavior.

**Decision**: Keep the normal-mode recovery action in schema defaults and canonical docs, and add explicit recovery notes that batch/_base callers must materialize `watershed.subwta` through their normal setup flow before retrying `run-wepp` endpoints.

**Impact**: Metadata no longer implies an unconditional queued recovery path for batch/_base contexts.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Strict precondition causes behavior change for existing batch/base workflows | Medium | Medium | Added focused regression tests and explicit contract docs to prevent silent drift | Mitigated |
| Contract/docs mismatch reappears between runtime and schema defaults | Medium | Medium | Updated `rq-response-contract.md`, schema-default metadata, and schema-default tests in same change | Mitigated |
| Rejected precondition path mutates run payload before returning 409 | Medium | Low | Moved strict gate before payload parse/apply and added no-mutation assertions | Mitigated |
| Recovery metadata can imply queued rebuild in batch/_base contexts | Medium | Low | Added schema/docs recovery notes about batch/_base no-queue limits | Mitigated |

## Verification Checklist

### Code Quality
- [x] `wctl run-pytest tests/microservices/test_rq_engine_wepp_routes.py tests/microservices/test_rq_engine_schema_defaults_routes.py --maxfail=1` (`118 passed`, 2026-04-27 20:33 UTC)
- [x] `wctl run-pytest tests/microservices/test_rq_engine_wepp_routes.py tests/microservices/test_rq_engine_schema_defaults_routes.py --maxfail=1` (`118 passed`, 2026-04-27 20:43 UTC after reviewer dispositions)
- [x] `git diff --check` (passed, 2026-04-27 20:33 UTC)
- [x] `git diff --check` (passed, 2026-04-27 20:44 UTC after package closure docs)

### Documentation
- [x] `wctl doc-lint --path docs/schemas/rq-response-contract.md --path docs/work-packages/20260427_rq_subwta_precondition_contract --path PROJECT_TRACKER.md` (`5 files validated, 0 errors, 0 warnings`, 2026-04-27 20:44 UTC)

### Testing
- [x] Route tests cover strict enforcement in normal, batch/base, and checkbox-toggled payload cases.
- [x] Schema-default tests assert strict error metadata/recovery for both run endpoints.

## Progress Notes

### 2026-04-27 20:20 UTC: Package setup
**Agent/Contributor**: Codex

**Work completed**:
- Created package and tracker scaffolding.
- Recorded strict contract decision from user directive.

**Next steps**:
1. Implement strict gate ordering in `wepp_routes.py`.
2. Update contract docs and schema-default metadata.
3. Add/adjust targeted route/schema tests and run required gates.

### 2026-04-27 20:33 UTC: Implementation and targeted pytest
**Agent/Contributor**: Codex

**Work completed**:
- Moved `run-wepp` / `run-wepp-watershed` `subwta` validation before batch/base acknowledgement and before enqueue.
- Added tests for missing `subwta` in normal, batch, `_base`, and `checkbox_wepp_watershed=false` contexts.
- Preserved `prep-wepp-watershed` missing-`subwta` rebuild behavior.
- Updated canonical response contract text and schema-default error metadata.

**Validation**:
- `wctl run-pytest tests/microservices/test_rq_engine_wepp_routes.py tests/microservices/test_rq_engine_schema_defaults_routes.py --maxfail=1` passed with `118 passed`.
- `git diff --check` passed.

**Next steps**:
1. Complete requested reviewer and QA reviewer disposition.
2. Run scoped doc-lint.
3. Close package docs and archive active ExecPlan.

### 2026-04-27 20:43 UTC: Review disposition
**Agent/Contributor**: Codex

**Findings dispositioned**:
- Reviewer Medium: invalid-state path mutated payload before returning 409. Disposition: fixed by moving `subwta` gate before payload parse/apply; tests now assert no WEPP/soils/watershed payload mutation and no checkbox persistence on rejected requests.
- Reviewer Medium: recovery metadata could loop in batch/_base contexts. Disposition: documented recovery-action limits in schema metadata and canonical contract text; batch/_base recovery remains outside this package's route behavior changes.
- Reviewer/QA Low: tracker stale. Disposition: tracker updated with current phase, task state, validation, decisions, and risks.

**Next steps**:
1. Rerun targeted pytest and `git diff --check`.
2. Run scoped doc-lint.
3. Close package docs and archive active ExecPlan.

### 2026-04-27 20:43 UTC: Closure
**Agent/Contributor**: Codex

**Work completed**:
- Reran targeted pytest after review dispositions.
- Updated `package.md` closure notes.
- Prepared active ExecPlan for archive under `prompts/completed/`.

**Validation**:
- `wctl run-pytest tests/microservices/test_rq_engine_wepp_routes.py tests/microservices/test_rq_engine_schema_defaults_routes.py --maxfail=1` passed with `118 passed`.
- `wctl doc-lint --path docs/schemas/rq-response-contract.md --path docs/work-packages/20260427_rq_subwta_precondition_contract --path PROJECT_TRACKER.md` passed with `5 files validated, 0 errors, 0 warnings`.
- `git diff --check` passed.

**Next steps**:
- None for this package.
