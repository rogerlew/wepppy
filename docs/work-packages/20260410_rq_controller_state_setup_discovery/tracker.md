# Tracker - RQ Controller State Setup Discovery

> Living document tracking progress, decisions, risks, and closeout evidence for this work package.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-04-10 06:58 UTC  
**Current phase**: Complete  
**Last updated**: 2026-04-10 07:29 UTC  
**Next milestone**: Handoff to roadmap package `20260410_rq_controller_state_orchestration_reads`.  
**Security impact**: `high`  
**Dedicated security review**: `yes`  
**Security artifact**: `docs/work-packages/20260410_rq_controller_state_setup_discovery/artifacts/2026-04-10_security_review.md`

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Completed required-reading pass (contracts, foundation package, freeze artifacts, roadmap, tracker context).
- [x] Bootstrapped package scaffold (`package.md`, `tracker.md`, `prompts/active/`, `prompts/completed/`, `artifacts/`).
- [x] Implemented setup-discovery routes in `wepppy/microservices/rq_engine/setup_discovery_routes.py`.
- [x] Registered setup-discovery router in `wepppy/microservices/rq_engine/__init__.py`.
- [x] Updated setup discovery and openapi contract tests:
  - `tests/microservices/test_rq_engine_setup_discovery_routes.py`
  - `tests/microservices/test_rq_engine_openapi_contract.py`
- [x] Updated route contract guards and frozen artifacts:
  - `tools/rq_engine_contract_rules.py`
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`
- [x] Completed reviewer + QA + security subagent passes; dispositioned all findings.
- [x] Completed required security artifact and docs/schema updates.
- [x] Archived ExecPlan to `prompts/completed/` with outcome note.
- [x] Updated `PROJECT_TRACKER.md` lifecycle entry to completed state.

## Timeline

- **2026-04-10 06:58 UTC** - Package scaffold created; execution started.
- **2026-04-10 07:11 UTC** - Setup discovery routes, router wiring, initial tests, and freeze/checklist updates completed.
- **2026-04-10 07:19 UTC** - Reviewer/QA/security findings triaged; remediation edits applied (create metadata parity, canonical 500 boundaries, expanded auth/failure tests).
- **2026-04-10 07:25 UTC** - Required code-gate commands re-run and passed after remediation.
- **2026-04-10 07:29 UTC** - Security artifact, docs updates, ExecPlan archive, and package closeout completed.

## Decisions Log

### 2026-04-10 06:58 UTC: Keep setup discovery bearer-gated with `rq:status` compatibility + `rq:read` parity
**Context**: Setup discovery is pre-run and read-only but still agent-facing.

**Options considered**:
1. Open-read setup endpoints without auth.
2. Bearer-only setup endpoints with rollout compatibility (`rq:status` or `rq:read`).
3. Session-cookie-only setup endpoints.

**Decision**: Option 2.

**Impact**: Preserves compatibility for existing bearer flows while keeping setup discovery explicitly authenticated and bounded to read-only surfaces.

### 2026-04-10 07:19 UTC: Align `rq_engine_create` setup metadata to current runtime instead of speculative target behavior
**Context**: Reviewers identified mismatch between setup descriptor claims and `POST /create/` runtime behavior.

**Options considered**:
1. Implement idempotency and JSON result fields immediately in `/create/`.
2. Make setup descriptor/schema truthfully reflect current redirect behavior and no idempotency support.

**Decision**: Option 2 (minimal, contract-driven scope for this package).

**Impact**: Removes metadata/runtime drift and defers idempotency feature work to the dedicated auth/concurrency roadmap package.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Descriptor metadata drifts from runtime behavior (`/create/`) | High | Medium | Corrected descriptor/schema contract and added parity assertions in setup-route tests | Mitigated |
| Setup routes return non-canonical framework 500 responses | High | Medium | Added explicit route-boundary exception handling and canonical 500 contract tests | Mitigated |
| Setup auth matrix regressions across routes | Medium | Medium | Added full auth matrix tests (`401`/`403`/`200`) across all six setup routes for `rq:status` and `rq:read` | Mitigated |
| Rollout compatibility (`rq:status`) retained longer than intended | Low | Medium | Documented bounded compatibility + follow-up sunset gate in `20260410_rq_controller_state_auth_concurrency` | Accepted-risk |

## Verification Checklist

### Code Gate
- [x] `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1`
- [x] `wctl run-pytest tests/microservices/test_rq_engine_setup_discovery_routes.py --maxfail=1`
- [x] `python tools/check_endpoint_inventory.py`
- [x] `python tools/check_route_contract_checklist.py`
- [x] `wctl run-pytest tests/tools/test_endpoint_inventory_guard.py tests/tools/test_route_contract_checklist_guard.py --maxfail=1`

### QA Gate
- [x] Independent reviewer subagent pass completed.
- [x] QA reviewer subagent pass completed.
- [x] Findings dispositioned in this tracker.
- [x] No unresolved medium/high QA findings.

### Security Gate
- [x] Security artifact created: `artifacts/2026-04-10_security_review.md`.
- [x] Auth/scope/session/CSRF implications explicitly reviewed.
- [x] No unresolved medium/high security findings.

### Docs Gate
- [x] `wctl doc-lint` run on all changed docs (schemas, package docs, tracker, completed ExecPlan/outcome, security artifact, freeze/checklist docs, and `PROJECT_TRACKER.md`).

## Reviewer Findings Disposition

### Independent Reviewer (`reviewer`) - 2026-04-10
1. **High**: Setup routes could leak non-canonical 500 responses.  
   **Disposition**: Resolved via explicit route-boundary `try/except` and canonical `error_response(..., status_code=500)` handling in setup routes.
2. **Medium**: Error catalog not-found codes drifted from runtime `error.code`.  
   **Disposition**: Resolved by standardizing setup error catalogs to `not_found`.
3. **Medium**: Missing failure-path contract tests.  
   **Disposition**: Resolved with new internal-failure tests (`raise_server_exceptions=False`) for configs/endpoints/schema/defaults/errors routes.
4. **Medium (re-review)**: `replay_behavior` enum in contract doc omitted `not_supported`.  
   **Disposition**: Resolved by updating `docs/schemas/rq-controller-state-contract.md` normative enum to include `not_supported`.
5. **Low**: Package/doc lifecycle consistency.  
   **Disposition**: Resolved at closeout (security artifact, tracker/package status, ExecPlan archive, and root tracker update).

### QA Reviewer (`qa_reviewer`) - 2026-04-10
1. **High**: `rq_engine_create` descriptor parity mismatch (idempotency and JSON required fields).  
   **Disposition**: Resolved by aligning setup descriptor/schema to actual redirect-only `/create/` behavior and removing idempotency support claims.
2. **Medium**: Incomplete auth matrix coverage across setup routes.  
   **Disposition**: Resolved by parameterized auth tests across all setup endpoints for missing auth, wrong scope, and both accepted scopes.
3. **Medium**: Missing canonical 500 boundary coverage.  
   **Disposition**: Resolved with explicit monkeypatched failure tests for setup helper resolution paths.
4. **Low (re-review)**: `/create/` description missing session-cookie fallback.  
   **Disposition**: Resolved by updating `project_routes.py` route description.
5. **Low (re-review)**: `_resolve_operation_docs` failure path not explicitly tested.  
   **Disposition**: Resolved by adding `_resolve_operation_docs` failure cases for schema/defaults/errors detail endpoints.

### Security Reviewer (`security_reviewer`) - 2026-04-10
1. **Medium**: Setup metadata overstated create idempotency/replay protection.  
   **Disposition**: Resolved by setting `idempotency_policy.supported=false` and removing dedupe key claims.
2. **Low**: Session token class with `rq:status` can read setup metadata during compatibility period.  
   **Disposition**: Accepted-risk with explicit bounded rollout and follow-up in `20260410_rq_controller_state_auth_concurrency`.

## Verification Evidence (Command Outcomes)

- `wctl run-pytest tests/microservices/test_rq_engine_setup_discovery_routes.py --maxfail=1` -> `28 passed`
- `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1` -> `9 passed`
- `python tools/check_endpoint_inventory.py` -> `Endpoint inventory check passed`
- `python tools/check_route_contract_checklist.py` -> `Route contract checklist check passed`
- `wctl run-pytest tests/tools/test_endpoint_inventory_guard.py tests/tools/test_route_contract_checklist_guard.py --maxfail=1` -> `2 passed`
- `wctl doc-lint --path docs/schemas/rq-controller-state-contract.md --path docs/schemas/rq-engine-agent-api-contract.md --path docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md --path docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md --path docs/work-packages/20260410_rq_controller_state_setup_discovery/package.md --path docs/work-packages/20260410_rq_controller_state_setup_discovery/tracker.md --path docs/work-packages/20260410_rq_controller_state_setup_discovery/prompts/completed/rq_controller_state_setup_discovery_execplan.md --path docs/work-packages/20260410_rq_controller_state_setup_discovery/prompts/completed/rq_controller_state_setup_discovery_execplan_outcome.md --path docs/work-packages/20260410_rq_controller_state_setup_discovery/artifacts/2026-04-10_security_review.md --path PROJECT_TRACKER.md` -> `pass`

## Final Handoff Summary

- Setup discovery is now implemented and frozen as agent-facing rq-engine surface with route, OpenAPI, and checklist/inventory parity gates passing.
- Metadata/runtime parity issues raised by reviewer/QA/security were resolved in-package.
- No unresolved medium/high QA or security findings remain at handoff.
