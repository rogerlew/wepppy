# RQ WEPP Subwta Precondition Contract Enforcement

**Status**: Closed (2026-04-27)
**Timezone**: UTC

## Overview

This package closes deferred RQ contract findings around watershed abstraction preconditions on WEPP run endpoints. The contract is now explicit: `watershed.subwta` is always required for `run-wepp` and `run-wepp-watershed`, because missing `subwta.tif` invalidates hillslope/watershed run integrity.

## Objectives

- Enforce `watershed.subwta` precondition consistently on `run-wepp` and `run-wepp-watershed` across normal, batch, and base contexts.
- Prevent `checkbox_wepp_watershed` payload toggles from bypassing abstraction validity checks.
- Align canonical docs, schema defaults endpoint metadata, and regression tests with the enforced contract.

## Scope

### Included

- `wepppy/microservices/rq_engine/wepp_routes.py` pre-enqueue abstraction gating behavior.
- `docs/schemas/rq-response-contract.md` contract language for strict `subwta` requirement.
- `wepppy/microservices/rq_engine/schema_defaults_routes.py` and paired tests for consistent error/recovery metadata.
- Targeted tests in `tests/microservices/test_rq_engine_wepp_routes.py` and `tests/microservices/test_rq_engine_schema_defaults_routes.py`.

### Explicitly Out of Scope

- `wepp_runner` instrumentation and binary lifecycle work.
- WEPP model binaries, vendoring, compiler flags, or release workflows.
- Unrelated RQ engine endpoint refactors outside strict abstraction-state contract behavior.

## Stakeholders

- **Primary**: RQ engine maintainers and WEPPcloud operators.
- **Reviewers**: NoDb/RQ maintainers.
- **Security Reviewer**: Not required by default; no new auth/public attack surface.
- **Informed**: Incident responders and package maintainers for run reliability.

## Success Criteria

- [x] `run-wepp` and `run-wepp-watershed` return canonical `409 invalid_watershed_abstraction_state` whenever `watershed.subwta` is missing.
- [x] Batch/base mode and `checkbox_wepp_watershed` do not bypass the abstraction-state check.
- [x] Canonical response contract and schema-defaults error metadata match runtime behavior exactly.
- [x] Targeted microservice regression tests pass for strict precondition cases.

## Dependencies

### Prerequisites

- Current RQ route handlers and payload-application path in `wepp_routes.py` and `wepp_run_payload.py`.
- Existing strict-error canonical contract in `docs/schemas/rq-response-contract.md`.

### Blocks

- Clean closure of deferred RQ findings from `20260427_wepp_runner_traceability_hardening` review disposition.

## Related Packages

- **Related**: [20260427_wepp_runner_traceability_hardening](../20260427_wepp_runner_traceability_hardening/package.md)
- **Related**: [20260425_nodb_atomicity_observability_followups_a](../20260425_nodb_atomicity_observability_followups_a/package.md)

## Timeline Estimate

- **Expected duration**: 1-2 focused sessions
- **Complexity**: Medium
- **Risk level**: Medium (changes enqueue contract behavior)

## Security Impact and Review Gate

- **Security impact triage**: `low`
- **Dedicated security review required**: `no`
- **Triage rationale**: Contract hardening in existing authenticated RQ endpoints; no new route surfaces or privilege model changes.
- **Security review artifact**: `N/A`

## References

- `wepppy/microservices/rq_engine/wepp_routes.py` - run endpoint pre-enqueue behavior.
- `wepppy/microservices/rq_engine/wepp_run_payload.py` - checkbox routine override ingestion.
- `docs/schemas/rq-response-contract.md` - canonical response/error contract.
- `wepppy/microservices/rq_engine/schema_defaults_routes.py` - endpoint error metadata catalog.
- `tests/microservices/test_rq_engine_wepp_routes.py` - route behavior tests.
- `tests/microservices/test_rq_engine_schema_defaults_routes.py` - schema defaults metadata tests.

## Deliverables

- Updated route logic enforcing strict `subwta` precondition contract.
- Updated contract docs and schema-defaults metadata.
- Regression tests covering strict precondition behavior in all relevant contexts.

## Closure Notes

**Closed**: 2026-04-27 20:43 UTC

**Summary**: Completed strict `watershed.subwta` precondition enforcement for `run-wepp` and `run-wepp-watershed`. Missing `subwta.tif` now returns HTTP `409` with `error.code="invalid_watershed_abstraction_state"` and `error.message="Watershed Abstraction is not in Valid state"` before payload mutation, batch/base acknowledgement, or enqueue. `prep-wepp-watershed` remains able to enqueue with missing `subwta` so existing prep behavior is preserved.

**Validation**:
- `wctl run-pytest tests/microservices/test_rq_engine_wepp_routes.py tests/microservices/test_rq_engine_schema_defaults_routes.py --maxfail=1` passed with `118 passed`.
- `wctl doc-lint --path docs/schemas/rq-response-contract.md --path docs/work-packages/20260427_rq_subwta_precondition_contract --path PROJECT_TRACKER.md` passed with `5 files validated, 0 errors, 0 warnings`.
- `git diff --check` passed.

**Review disposition**: Required `reviewer` and `qa_reviewer` passes were completed. Medium findings were remediated in code/docs; the low stale-tracker finding was resolved in package lifecycle docs.

**Archive Status**: Active ExecPlan archived under `prompts/completed/`.
