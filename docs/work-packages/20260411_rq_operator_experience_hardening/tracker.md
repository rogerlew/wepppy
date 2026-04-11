# Tracker - RQ Operator Experience Hardening

> Living document tracking progress, decisions, risks, and verification evidence for this package.

## Quick Status

**Timezone**: UTC
**Started**: 2026-04-11 06:03 UTC
**Current phase**: Follow-up remediation complete (validation + review gate closure)
**Last updated**: 2026-04-11 16:20 UTC
**Next milestone**: Final package handoff with second-acceptance prompt update
**Security impact**: `high`
**Dedicated security review**: `yes`
**Security artifact**: `docs/work-packages/20260411_rq_operator_experience_hardening/artifacts/2026-04-11_security_review.md`

## Task Board

### Ready / Backlog
- [x] Implement machine-safe operator token bootstrap path and document curl/python flow.
- [x] Add route/descriptor/openapi support for revision-domain metadata (`run_state_domain`, `run_state_vector`).
- [x] Enforce strict snapshot freshness semantics (`updated_at`, `data_state`, `data_updated_at`) on controller-state read surfaces.
- [x] Add/extend regression tests and guard checks for auth bootstrap ergonomics + revision/freshness invariants.
- [x] Update operator smoke automation/runbook to count-agnostic gates and API-only evidence collection.
- [x] Complete independent reviewer/qa/security passes and disposition findings.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Captured operator acceptance friction evidence from `clueless-aftertaste` replication report (2026-04-11 04:11-04:15 UTC).
- [x] Revised canonical schema docs to define target hardening requirements for operator bootstrap, revision coherence, and freshness semantics (2026-04-11 06:03 UTC).
- [x] Corrected smoke runbook pass/fail guidance to avoid hard-coded test-count drift (2026-04-11 06:03 UTC).
- [x] Scaffolded package docs and active ExecPlan (2026-04-11 06:03 UTC).
- [x] Implemented climate parse hardening to remove `KeyError` blocker and return contract-consistent validation payloads (2026-04-11 15:58 UTC).
- [x] Added batched endpoint discovery snapshot (`include_operation_docs=true`) to reduce operator discovery call volume (2026-04-11 15:58 UTC).
- [x] Updated schema/runbook docs for climate-mode alignment and batched discovery semantics (2026-04-11 15:58 UTC).

## Timeline

- **2026-04-11 06:03 UTC** - Package scaffolded (`package.md`, `tracker.md`, active ExecPlan).
- **2026-04-11 06:03 UTC** - Contract hardening requirements added to `rq-engine-agent-api-contract.md` and `rq-controller-state-contract.md`.
- **2026-04-11 06:03 UTC** - Smoke runbook reliability guidance updated to exit-code/count-agnostic expectations.
- **2026-04-11 06:55 UTC** - Machine-safe bootstrap endpoint implemented with rate limit/audit/scope-intersection behavior and CSRF exemption wiring.
- **2026-04-11 06:55 UTC** - Revision-domain + freshness semantics implemented across `pipeline`, `readiness`, `geospatial-metadata`, and `outputs` payload/descriptor surfaces.
- **2026-04-11 06:55 UTC** - Maintainer preflight + operator API-only smoke gates completed; evidence/security artifacts updated.
- **2026-04-11 07:18 UTC** - Post-review hardening shipped: required `jti` contract alignment, explicit revocation-outage `503` behavior (`Retry-After`), and deterministic non-future fallback timestamp handling.
- **2026-04-11 07:33 UTC** - Operator API-only smoke rerun with refreshed UTC/redacted evidence; parity checks confirmed with non-future freshness values.
- **2026-04-11 07:37 UTC** - Independent `reviewer`, `qa_reviewer`, and `security_reviewer` re-reviews closed with no unresolved medium/high findings.
- **2026-04-11 07:40 UTC** - Final reviewer follow-up closed after revision-coherence tweak (`data_updated_at` included in orchestration revision signature) and evidence `session_id` redaction; no unresolved medium/high findings remain.
- **2026-04-11 15:58 UTC** - Follow-up acceptance blocker remediation shipped: `build-climate` parse path now returns structured validation payloads, climate schema/defaults aligned for mode coverage (`0,2,3,5,6,11`), and `include_operation_docs=true` batched endpoint discovery added.
- **2026-04-11 15:58 UTC** - Follow-up validation gates passed: targeted parser/climate/schema suites, setup/openapi parity suites, endpoint/checklist guards, and docs lint.
- **2026-04-11 16:20 UTC** - Final remediation hardening shipped: mode-switch year-bound updates are atomic (no partial mutation on validation failure), OpenAPI boolean query param contract finalized for `include_operation_docs`, and independent `reviewer`/`qa_reviewer`/`security_reviewer` re-reviews confirmed no unresolved medium/high findings.

## Decisions Log

### 2026-04-11 06:03 UTC: Prioritize machine-safe bootstrap over wrapper tooling
**Context**: Acceptance smoke proved operators can run API-first workflows, but auth bootstrap currently relies on session/CSRF choreography and HTML extraction.

**Options considered**:
1. Ship a `wctl` wrapper for token minting.
2. Keep current browser-oriented flow and improve docs only.
3. Implement a machine-safe API bootstrap contract with route/test/descriptor support.

**Decision**: Option 3.

**Impact**: Delivers a durable operator surface independent of developer-local tooling.

---

### 2026-04-11 06:03 UTC: Use explicit revision domains instead of implicit global revision assumptions
**Context**: Source/target acceptance evidence showed inconsistent `run_state_revision` values between orchestration and metadata surfaces.

**Options considered**:
1. Keep one implicit `run_state_revision` and treat inconsistency as transient.
2. Expose explicit domain metadata (`run_state_domain`) and domain vector (`run_state_vector`) so clients can reason deterministically.

**Decision**: Option 2.

**Impact**: Removes ambiguity for autonomous planning loops and enables targeted stale-read detection.

---

### 2026-04-11 06:55 UTC: Ship phased run-state vector with explicit nulls for non-local domains
**Context**: Orchestration and metadata/outputs revisions are produced by separate route families. For this package, deterministic domain annotation and join-safe vectors were required without introducing cross-module dependency coupling.

**Options considered**:
1. Compute all three domain revisions on every endpoint response (cross-module coupling).
2. Emit domain-correct revision plus phased vector keys with explicit `null` for domains not computed by that surface.

**Decision**: Option 2.

**Impact**: Delivers deterministic cross-endpoint coherence semantics immediately, keeps route modules decoupled, and preserves the contract path to full non-null vectors in future follow-on work.

---

### 2026-04-11 07:18 UTC: Fail closed with explicit retry guidance for revocation outages
**Context**: Independent security review identified that revocation backend failures should avoid ambiguous 500s and provide clear retry semantics.

**Options considered**:
1. Keep generic `500` behavior on revocation check failure.
2. Return explicit `503` with retry guidance and bounded Redis timeouts.

**Decision**: Option 2.

**Impact**: Preserves fail-closed auth posture while making outage behavior machine-actionable for operators.

---

### 2026-04-11 15:58 UTC: Prefer contract-consistent validation errors over traceback details on climate parse failures
**Context**: Second acceptance halted at `build-climate` with parser `KeyError` details exposed to operators.

**Options considered**:
1. Keep traceback-based `400` responses and update runbook workaround only.
2. Normalize route boundary to canonical `validation_error` payloads with field-level missing-key details.

**Decision**: Option 2.

**Impact**: Removes brittle traceback coupling, enables machine remediation, and closes the blocker root cause.

---

### 2026-04-11 15:58 UTC: Add batched run-endpoint discovery payload to reduce orchestration chatter
**Context**: Second acceptance friction log reported high call volume due per-operation schema/default/error fetch loops.

**Options considered**:
1. Keep per-operation discovery only.
2. Add optional batched payload on existing run-endpoint catalog route.

**Decision**: Option 2 (`GET .../endpoints?include_operation_docs=true`).

**Impact**: One-call schema/default/error snapshot available for discovery-first agents without introducing a new route family.

---

### 2026-04-11 16:20 UTC: Enforce parse atomicity for future-mode validation failures
**Context**: QA re-review identified that future-mode parse failures could clear observed year bounds before returning `400`.

**Options considered**:
1. Keep current behavior and rely on retries to rehydrate state.
2. Validate required future fields before mutating any year-bound controller state.

**Decision**: Option 2.

**Impact**: Removes partial-state mutation on invalid payloads and closes the last high-severity follow-up finding.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| New token bootstrap path widens auth attack surface | High | Medium | Security-first design + dedicated security review + strict scope constraints | Mitigated |
| Revision-domain model introduces client confusion if partially rolled out | High | Medium | Add compatibility rules + descriptor docs + endpoint tests before rollout | Mitigated |
| Freshness semantics change causes downstream parsing regressions | Medium | Medium | Add additive fields first, preserve backward compatibility, gate with route tests | Mitigated |
| Smoke reliability fixes remain doc-only without executable validation | Medium | Medium | Add scripted API smoke gate and enforce in package acceptance | Mitigated |

## Verification Checklist

### Code/Contract
- [x] Route/descriptors/OpenAPI updated for machine-safe token bootstrap.
- [x] Route/descriptors/OpenAPI updated for revision-domain + freshness semantics.
- [x] Required microservice tests pass.
- [x] Inventory/checklist guards pass.

### Security
- [x] Security impact triage validated in implementation scope.
- [x] `artifacts/2026-04-11_security_review.md` completed.
- [x] No unresolved medium/high security findings remain.

### Docs
- [x] Schema docs and runbook updated to final shipped behavior.
- [x] `wctl doc-lint` passes on changed docs.

### Operator Acceptance
- [x] API-only smoke (no `wctl`) passes with UTC call evidence.
- [x] Source vs target parity checks pass under hardened contract semantics.

## Progress Notes

### 2026-04-11 06:03 UTC: Package kickoff and contract hardening scope
**Agent/Contributor**: Codex

**Work completed**:
- Added hardening requirements to:
  - `docs/schemas/rq-engine-agent-api-contract.md`
  - `docs/schemas/rq-controller-state-contract.md`
- Updated smoke runbook reliability expectation language:
  - `docs/work-packages/20260410_rq_controller_state_contract_cutover/artifacts/2026-04-11_rq_controller_state_e2e_smoke_runbook.md`
- Created new work-package scaffold and active ExecPlan:
  - `docs/work-packages/20260411_rq_operator_experience_hardening/package.md`
  - `docs/work-packages/20260411_rq_operator_experience_hardening/tracker.md`
  - `docs/work-packages/20260411_rq_operator_experience_hardening/prompts/active/rq_operator_experience_hardening_execplan.md`

**Blockers encountered**:
- None.

**Next steps**:
- Begin Milestone 1 implementation for machine-safe token bootstrap.
- Define concrete compatibility rollout for `run_state_domain`/`run_state_vector` and freshness fields.

**Test results**: Not run yet in this package (planning/docs session only).

### 2026-04-11 06:55 UTC: Implementation, validation, and evidence closure
**Agent/Contributor**: Codex

**Work completed**:
- Implemented machine-safe bootstrap route:
  - `POST /weppcloud/api/auth/rq-engine-operator-token`
  - strict scope intersection semantics, token-class gate (`user`/`service`), rate limiting, audit logging, `Cache-Control: no-store`, and CSRF exemption registration.
- Implemented revision/freshness contract semantics in run-scoped snapshot reads:
  - `pipeline` / `readiness` now emit `run_state_domain=orchestration`, phased `run_state_vector`, deterministic `updated_at`, and `data_state` / `data_updated_at`.
  - metadata surfaces emit `run_state_domain=metadata` + phased `run_state_vector`.
  - outputs surface now emits `run_state_domain=outputs`, outputs-domain revision, vector linkage to metadata revision, and explicit freshness state (`not_materialized` when no artifacts).
- Updated operation descriptors/schemas for snapshot read required fields.
- Updated tests across microservice + weppcloud route suites for new contract fields/semantics.
- Ran maintainer preflight gate (Phase A), operator API-only acceptance smoke, and generated required evidence artifact:
  - `docs/work-packages/20260411_rq_operator_experience_hardening/artifacts/2026-04-11_operator_smoke_evidence.md`
- Updated security artifact with threat model, controls, evidence, and findings disposition.

**Blockers encountered**:
- None.

**Test results**:
- `wctl run-pytest` consolidated Phase A command set: **251 passed**.
- Route inventory + checklist checks: **pass**.
- Guard tests: **2 passed**.
- Bootstrap/CSRF route tests: **34 passed**.

**Outcome status**:
- Package acceptance criteria satisfied.

### 2026-04-11 07:37 UTC: Post-review remediation and independent gate closure
**Agent/Contributor**: Codex

**Work completed**:
- Resolved independent review findings:
  - freshness fallback now revision-coherent and non-future-clamped;
  - revocation failure path now pre-throttled and returns explicit `503` + `Retry-After`;
  - machine-safe bootstrap `jti` requirement documented in canonical contract/runbook.
- Added/updated tests for:
  - revocation backend unavailability (`503` contract);
  - non-future freshness assertions on fallback paths.
- Reran operator API-only smoke and refreshed:
  - `artifacts/2026-04-11_operator_smoke_evidence.md`
- Completed independent re-reviews (`reviewer`, `qa_reviewer`, `security_reviewer`) with no unresolved medium/high findings.

**Blockers encountered**:
- None.

**Test results**:
- `wctl run-pytest tests/weppcloud/routes/test_rq_engine_token_api.py tests/weppcloud/routes/test_csrf_rollout.py --maxfail=1` -> **43 passed**
- `wctl run-pytest tests/microservices/test_rq_engine_orchestration_read_routes.py tests/microservices/test_rq_engine_errors_progress_outputs_routes.py tests/microservices/test_rq_engine_geospatial_upload_metadata_routes.py tests/microservices/test_rq_engine_schema_defaults_routes.py --maxfail=1` -> **102 passed**

**Outcome status**:
- Package acceptance criteria remain satisfied; independent gates closed.

### 2026-04-11 15:58 UTC: Second-acceptance blocker/friction remediation
**Agent/Contributor**: Codex

**Work completed**:
- Hardened climate parse boundary to return canonical `validation_error` payloads with machine-actionable missing field entries (no traceback detail leakage).
- Updated climate input parsing semantics to require future year bounds only for `ClimateMode.Future` and avoid unconditional `future_*` key access.
- Aligned climate schema/defaults for route discovery and defaults:
  - mode coverage includes `0,2,3,5,6,11`;
  - observed-year requirement narrowed to observed/gridmet modes;
  - future-year fields added with mode-conditional requirements;
  - run-resolved climate defaults now emit future year defaults when run mode is future.
- Added optional batched discovery response:
  - `GET /api/runs/{runid}/{config}/endpoints?include_operation_docs=true`
  - includes per-operation descriptor + schema + defaults + errors snapshot in one payload.
- Updated contract/runbook docs for new climate and discovery semantics.

**Blockers encountered**:
- None (local remediation and validation path completed).

**Test results**:
- `wctl run-pytest tests/nodb/test_climate_input_parser_service.py tests/microservices/test_rq_engine_climate_routes.py tests/microservices/test_rq_engine_schema_defaults_routes.py --maxfail=1` -> **65 passed**
- `wctl run-pytest tests/microservices/test_rq_engine_setup_discovery_routes.py tests/microservices/test_rq_engine_schema_defaults_routes.py tests/microservices/test_rq_engine_climate_routes.py tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1` -> **95 passed**
- `python tools/check_endpoint_inventory.py && python tools/check_route_contract_checklist.py` -> **pass**
- `wctl doc-lint --path ...` (5 updated docs) -> **0 errors, 0 warnings**

**Outcome status**:
- Acceptance blocker root cause remediated in code/contracts; follow-up independent reviewer gates executed before handoff.

### 2026-04-11 16:20 UTC: Follow-up reviewer gate closure
**Agent/Contributor**: Codex

**Work completed**:
- Fixed final QA-identified atomicity gap in future-mode parsing (validate before clearing observed years).
- Declared `include_operation_docs` as explicit boolean query parameter in FastAPI/OpenAPI and added contract assertion test.
- Added additional parser regressions for mode-switch determinism and no-mutation-on-validation-failure behavior.
- Executed independent re-reviews:
  - `reviewer`
  - `qa_reviewer`
  - `security_reviewer`

**Blockers encountered**:
- None.

**Test results**:
- `wctl run-pytest tests/microservices/test_rq_engine_setup_discovery_routes.py tests/microservices/test_rq_engine_schema_defaults_routes.py tests/microservices/test_rq_engine_climate_routes.py tests/nodb/test_climate_input_parser_service.py tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1` -> **109 passed**

**Outcome status**:
- Reviewer gates closed; no unresolved medium/high findings remain.

## Watch List

- Ensure operator bootstrap design remains compatible with existing browser/session flows.
- Keep scope disciplined: this package should not expand into unrelated auth platform redesign.

## Communication Log

### 2026-04-11 06:03 UTC: User directive
**Participants**: User, Codex
**Question/Topic**: Revise schema docs and create robust work-package for low-friction/high-quality agent operation, explicitly without `wctl` dependency for operators.
**Outcome**: Contract revisions drafted and package/ExecPlan scaffolded for implementation.
