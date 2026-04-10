# Tracker - RQ Controller State Schema and Defaults

> Living document tracking progress, decisions, risks, and closeout evidence for this work package.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-04-10 18:21 UTC  
**Current phase**: Complete  
**Last updated**: 2026-04-10 19:52 UTC  
**Next milestone**: Handoff to roadmap packages `20260410_rq_controller_state_geospatial_uploads` and `20260410_rq_controller_state_errors_progress_outputs`.  
**Security impact**: `high`  
**Dedicated security review**: `yes`  
**Security artifact**: `docs/work-packages/20260410_rq_controller_state_schema_defaults/artifacts/2026-04-10_security_review.md`

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Completed required-reading pass (contracts, predecessor package outputs, freeze artifacts, roadmap dependencies).
- [x] Implemented controller metadata reads:
  - `GET /api/runs/{runid}/{config}/controllers`
  - `GET /api/runs/{runid}/{config}/controllers/{controller}/schema`
  - `GET /api/runs/{runid}/{config}/controllers/{controller}/hints`
  - `GET /api/runs/{runid}/{config}/controllers/{controller}/templates`
- [x] Implemented endpoint metadata reads:
  - `GET /api/runs/{runid}/{config}/endpoints`
  - `GET /api/runs/{runid}/{config}/endpoints/{operation_id}/schema`
  - `GET /api/runs/{runid}/{config}/endpoints/{operation_id}/defaults`
- [x] Registered schema/default router in `wepppy/microservices/rq_engine/__init__.py`.
- [x] Added and updated route/openapi/contract tests and guards:
  - `tests/microservices/test_rq_engine_schema_defaults_routes.py`
  - `tests/microservices/test_rq_engine_openapi_contract.py`
  - `tools/rq_engine_contract_rules.py`
- [x] Updated frozen artifacts:
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`
- [x] Completed independent `reviewer`, `qa_reviewer`, and `security_reviewer` passes; dispositioned findings.
- [x] Re-ran full required code-gate command set after final remediation.
- [x] Completed security artifact and package lifecycle docs.
- [x] Archived ExecPlan to `prompts/completed/` with outcome note.
- [x] Updated `PROJECT_TRACKER.md` lifecycle entry to completed state.

## Timeline

- **2026-04-10 18:21 UTC** - Package scaffold and kickoff ExecPlan authored.
- **2026-04-10 19:05 UTC** - Schema/default routes, wiring, tests, and freeze/checklist updates completed.
- **2026-04-10 19:22 UTC** - Independent review findings triaged; parity and metadata-remediation iteration completed.
- **2026-04-10 19:52 UTC** - Final security/QA re-reviews and docs gate completed after parity and hardening updates; package closeout finalized.

## Decisions Log

### 2026-04-10 18:21 UTC: Keep package scope aligned to roadmap row 4 schema/default surfaces
**Context**: Orchestration-read package is complete and later roadmap rows already own geospatial/uploads, outputs/progress/errors, and auth-concurrency rollout.

**Options considered**:
1. Fold geospatial and output concerns into this package.
2. Keep strict row-4 scope and hand off follow-on surfaces to planned packages.

**Decision**: Option 2.

**Impact**: Preserved dependency boundaries and kept this package focused on machine-readable schema/default metadata.

### 2026-04-10 19:22 UTC: Keep metadata parity with live route handlers as the source of truth
**Context**: Independent reviewer and QA passes found several schema/default descriptors that drifted from actual request contracts.

**Options considered**:
1. Keep richer descriptive payloads even when handlers do not consume those fields.
2. Constrain descriptors/defaults strictly to fields currently accepted/emitted by handlers.

**Decision**: Option 2.

**Impact**: Reduced contract drift risk and prevented agent planners from selecting unsupported fields.

### 2026-04-10 19:24 UTC: Gate `/upload-sbs` metadata by disturbed fire-mod support
**Context**: Review surfaced that endpoint availability was keyed only to `sbs_upload_supported` in state, missing non-baseline disturbed-mode semantics.

**Options considered**:
1. Expose `/upload-sbs` metadata for all disturbed runs.
2. Expose only when supported fire mods are active (`disturbed`, `baer`, `ash`, `debris_flow`) and include explicit predicate semantics.

**Decision**: Option 2.

**Impact**: Matched runtime behavior and reduced false-positive availability for unsupported contexts.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Schema/default payloads drift from contract semantics | High | Medium | Bound payload builders and tests to `rq-controller-state-contract.md`; reviewer remediation closed known drifts | Mitigated |
| Run-resolved defaults become nondeterministic for equivalent state | High | Medium | Added deterministic assembly rules and regression tests across baseline/disturbed fixtures | Mitigated |
| Sensitive internals leak through metadata payloads | High | Medium | Security review + explicit redaction/omission assertions in route tests | Mitigated |
| Frozen inventory/checklist artifacts lag endpoint implementation | Medium | Medium | Updated artifacts in-package and enforced with guard scripts/tests | Mitigated |
| `deployment_revision` metadata can expose internal revision identifiers if configured with sensitive values | Low | Medium | Accepted-risk with policy requirement that `RQ_ENGINE_DEPLOYMENT_REVISION` remains a non-sensitive public build label | Accepted-risk |
| Unexpected exceptions in auth boundary blocks map to `401`, which can collapse root-cause taxonomy | Low | Medium | Accepted-risk for current auth compatibility; tightening deferred to `20260410_rq_controller_state_auth_concurrency` | Accepted-risk |

## Verification Checklist

### Code Gate
- [x] `wctl run-pytest tests/microservices/test_rq_engine_schema_defaults_routes.py --maxfail=1`
- [x] `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1`
- [x] `python tools/check_endpoint_inventory.py`
- [x] `python tools/check_route_contract_checklist.py`
- [x] `wctl run-pytest tests/tools/test_endpoint_inventory_guard.py tests/tools/test_route_contract_checklist_guard.py --maxfail=1`

### QA Gate
- [x] Independent `reviewer` subagent pass completed.
- [x] Independent `qa_reviewer` subagent pass completed.
- [x] Findings dispositioned in this tracker.
- [x] No unresolved medium/high QA findings.

### Security Gate
- [x] Security artifact completed: `artifacts/2026-04-10_security_review.md`.
- [x] Independent `security_reviewer` subagent pass completed.
- [x] Auth/scope/session/CSRF and metadata disclosure implications explicitly reviewed.
- [x] No unresolved medium/high security findings.

### Docs Gate
- [x] `wctl doc-lint` run on changed docs (`package.md`, `tracker.md`, completed ExecPlan/outcome, security artifact, frozen artifacts, schema docs as changed, and `PROJECT_TRACKER.md`).

## Reviewer Findings Disposition

### Independent Reviewer (`reviewer`) - 2026-04-10
1. **High**: Endpoint metadata for several operations drifted from actual handler contracts (`run_wepp`, `build_landuse`, `build_soils`, watershed prep/run, issue-session-token response shape).  
   **Disposition**: Resolved by tightening operation schema/default descriptors to actual accepted/returned fields and adding/adjusting regression assertions in `tests/microservices/test_rq_engine_schema_defaults_routes.py`.
2. **Medium**: Climate defaults emitted string enum value despite integer schema semantics.  
   **Disposition**: Resolved by introducing integer enum/default normalization for climate mode (`climate_mode_code`) in schema/default payloads with targeted regression coverage.
3. **Medium**: `/upload-sbs` availability logic not aligned with disturbed fire-mod support semantics.  
   **Disposition**: Resolved via explicit supported-mod predicate and state gating (`sbs_upload_supported`) with positive/negative regression tests.

### QA Reviewer (`qa_reviewer`) - 2026-04-10
1. **High**: Test fixtures and metadata docs diverged from actual runtime request contracts, risking false confidence.  
   **Disposition**: Resolved by aligning fixtures and route metadata with live handler payloads and extending assertions for contract parity.
2. **Medium**: Coverage gap around disturbed-mod-sensitive endpoint availability.  
   **Disposition**: Resolved by adding BAER/non-fire-mod tests for `/upload-sbs` availability behavior.
3. **Medium**: Inconsistent field typing risk in defaults path (`climate_mode`).  
   **Disposition**: Resolved with integer default derivation and dedicated regression test.

### Security Reviewer (`security_reviewer`) - 2026-04-10
1. **Low**: Reflected controller/operation identifiers in `404` messages could become a downstream injection sink if callers render error text unsafely.  
   **Disposition**: Resolved by switching to generic messages (`Controller not found`, `Operation not found`) without echoing untrusted path inputs.
2. **Low**: `deployment_revision` metadata may expose internal revision details if configured with sensitive values.  
   **Disposition**: Accepted-risk with operational requirement that `RQ_ENGINE_DEPLOYMENT_REVISION` remains a non-sensitive public build label.
3. **Low**: Unexpected auth-boundary exceptions map to `401`, collapsing some internal faults into auth failures.  
   **Disposition**: Accepted-risk for current auth compatibility; follow-on tightening deferred to `20260410_rq_controller_state_auth_concurrency`.

## Verification Evidence (Command Outcomes)

- `wctl run-pytest tests/microservices/test_rq_engine_schema_defaults_routes.py --maxfail=1` -> `43 passed`
- `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1` -> `9 passed`
- `python tools/check_endpoint_inventory.py` -> `Endpoint inventory check passed`
- `python tools/check_route_contract_checklist.py` -> `Route contract checklist check passed`
- `wctl run-pytest tests/tools/test_endpoint_inventory_guard.py tests/tools/test_route_contract_checklist_guard.py --maxfail=1` -> `2 passed`
- `wctl doc-lint --path docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md --path docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md --path docs/work-packages/20260410_rq_controller_state_schema_defaults/package.md --path docs/work-packages/20260410_rq_controller_state_schema_defaults/tracker.md --path docs/work-packages/20260410_rq_controller_state_schema_defaults/artifacts/2026-04-10_security_review.md --path docs/work-packages/20260410_rq_controller_state_schema_defaults/prompts/completed/rq_controller_state_schema_defaults_execplan.md --path docs/work-packages/20260410_rq_controller_state_schema_defaults/prompts/completed/rq_controller_state_schema_defaults_execplan_outcome.md --path docs/schemas/rq-controller-state-contract.md --path PROJECT_TRACKER.md` -> `9 files validated, 0 errors, 0 warnings`

## Final Handoff Summary

- Implemented and validated all seven run-scoped schema/default read endpoints for controller and operation metadata.
- Completed independent reviewer, QA, and security review loops with all medium/high findings resolved; remaining low accepted risks are documented for deployment-revision disclosure policy and auth-taxonomy tightening follow-on.
- Frozen endpoint inventory and route contract checklist artifacts now include all row-4 schema/default routes.
