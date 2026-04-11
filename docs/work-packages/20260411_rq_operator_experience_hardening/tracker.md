# Tracker - RQ Operator Experience Hardening

> Living document tracking progress, decisions, risks, and verification evidence for this package.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-04-11 06:03 UTC  
**Current phase**: Discovery/Planning  
**Last updated**: 2026-04-11 06:03 UTC  
**Next milestone**: Approve and begin Milestone 1 (machine-safe token bootstrap implementation)  
**Security impact**: `high`  
**Dedicated security review**: `yes`  
**Security artifact**: `docs/work-packages/20260411_rq_operator_experience_hardening/artifacts/2026-04-11_security_review.md`

## Task Board

### Ready / Backlog
- [ ] Implement machine-safe operator token bootstrap path and document curl/python flow.
- [ ] Add route/descriptor/openapi support for revision-domain metadata (`run_state_domain`, `run_state_vector`).
- [ ] Enforce strict snapshot freshness semantics (`updated_at`, `data_state`, `data_updated_at`) on controller-state read surfaces.
- [ ] Add/extend regression tests and guard checks for auth bootstrap ergonomics + revision/freshness invariants.
- [ ] Update operator smoke automation/runbook to count-agnostic gates and API-only evidence collection.
- [ ] Complete independent reviewer/qa/security passes and disposition findings.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Captured operator acceptance friction evidence from `clueless-aftertaste` replication report (2026-04-11 04:11-04:15 UTC).
- [x] Revised canonical schema docs to define target hardening requirements for operator bootstrap, revision coherence, and freshness semantics (2026-04-11 06:03 UTC).
- [x] Corrected smoke runbook pass/fail guidance to avoid hard-coded test-count drift (2026-04-11 06:03 UTC).
- [x] Scaffolded package docs and active ExecPlan (2026-04-11 06:03 UTC).

## Timeline

- **2026-04-11 06:03 UTC** - Package scaffolded (`package.md`, `tracker.md`, active ExecPlan).
- **2026-04-11 06:03 UTC** - Contract hardening requirements added to `rq-engine-agent-api-contract.md` and `rq-controller-state-contract.md`.
- **2026-04-11 06:03 UTC** - Smoke runbook reliability guidance updated to exit-code/count-agnostic expectations.

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

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| New token bootstrap path widens auth attack surface | High | Medium | Security-first design + dedicated security review + strict scope constraints | Open |
| Revision-domain model introduces client confusion if partially rolled out | High | Medium | Add compatibility rules + descriptor docs + endpoint tests before rollout | Open |
| Freshness semantics change causes downstream parsing regressions | Medium | Medium | Add additive fields first, preserve backward compatibility, gate with route tests | Open |
| Smoke reliability fixes remain doc-only without executable validation | Medium | Medium | Add scripted API smoke gate and enforce in package acceptance | Open |

## Verification Checklist

### Code/Contract
- [ ] Route/descriptors/OpenAPI updated for machine-safe token bootstrap.
- [ ] Route/descriptors/OpenAPI updated for revision-domain + freshness semantics.
- [ ] Required microservice tests pass.
- [ ] Inventory/checklist guards pass.

### Security
- [ ] Security impact triage validated in implementation scope.
- [ ] `artifacts/2026-04-11_security_review.md` completed.
- [ ] No unresolved medium/high security findings remain.

### Docs
- [ ] Schema docs and runbook updated to final shipped behavior.
- [ ] `wctl doc-lint` passes on changed docs.

### Operator Acceptance
- [ ] API-only smoke (no `wctl`) passes with UTC call evidence.
- [ ] Source vs target parity checks pass under hardened contract semantics.

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

## Watch List

- Ensure operator bootstrap design remains compatible with existing browser/session flows.
- Keep scope disciplined: this package should not expand into unrelated auth platform redesign.

## Communication Log

### 2026-04-11 06:03 UTC: User directive
**Participants**: User, Codex  
**Question/Topic**: Revise schema docs and create robust work-package for low-friction/high-quality agent operation, explicitly without `wctl` dependency for operators.  
**Outcome**: Contract revisions drafted and package/ExecPlan scaffolded for implementation.
