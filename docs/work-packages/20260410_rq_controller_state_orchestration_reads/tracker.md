# Tracker - RQ Controller State Orchestration Reads

> Living document tracking progress, decisions, risks, and closeout evidence for this work package.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-04-10 17:11 UTC  
**Current phase**: Complete  
**Last updated**: 2026-04-10 18:08 UTC  
**Next milestone**: Handoff to roadmap package `20260410_rq_controller_state_schema_defaults`.  
**Security impact**: `high`  
**Dedicated security review**: `yes`  
**Security artifact**: `docs/work-packages/20260410_rq_controller_state_orchestration_reads/artifacts/2026-04-10_security_review.md`

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Completed required-reading pass (contracts, predecessor package outputs, freeze artifacts, roadmap dependencies).
- [x] Implemented orchestration reads:
  - `GET /api/runs/{runid}/{config}/pipeline`
  - `GET /api/runs/{runid}/{config}/readiness`
- [x] Registered orchestration router in `wepppy/microservices/rq_engine/__init__.py`.
- [x] Updated route/openapi/contract tests and guards:
  - `tests/microservices/test_rq_engine_orchestration_read_routes.py`
  - `tests/microservices/test_rq_engine_openapi_contract.py`
  - `tools/rq_engine_contract_rules.py`
- [x] Updated frozen artifacts:
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md`
  - `docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md`
- [x] Completed independent `reviewer`, `qa_reviewer`, and `security_reviewer` passes; dispositioned all findings.
- [x] Re-ran full required code-gate command set after final remediation.
- [x] Completed security artifact and package lifecycle docs.
- [x] Archived ExecPlan to `prompts/completed/` with outcome note.
- [x] Updated `PROJECT_TRACKER.md` lifecycle entry to completed state.

## Timeline

- **2026-04-10 17:11 UTC** - Package scaffold and kickoff ExecPlan authored.
- **2026-04-10 17:36 UTC** - Initial orchestration routes, tests, and freeze/checklist updates completed.
- **2026-04-10 17:53 UTC** - Independent review findings triaged; remediation iteration started.
- **2026-04-10 18:07 UTC** - Reviewer/QA/security re-reviews confirmed no unresolved high/medium findings.
- **2026-04-10 18:08 UTC** - Final code-gate rerun and lifecycle closeout completed.

## Decisions Log

### 2026-04-10 17:11 UTC: Keep package scope limited to roadmap row 3 orchestration reads
**Context**: Follow-on packages already own schema/defaults, geospatial/uploads, errors/outputs, and auth-concurrency rollout.

**Options considered**:
1. Fold schema/default and output/progress work into orchestration package.
2. Keep strict row-3 scope and hand off subsequent surfaces to planned packages.

**Decision**: Option 2.

**Impact**: Maintains incremental delivery and reduces cross-package drift/risk.

### 2026-04-10 17:53 UTC: Narrow not-found mapping to explicit config mismatch exception
**Context**: QA/security review identified broad `ValueError` -> `404` mapping as masking internal data faults.

**Options considered**:
1. Continue broad `ValueError` mapping for convenience.
2. Introduce dedicated exception for config mismatch and preserve canonical `500` for all other value failures.

**Decision**: Option 2.

**Impact**: Aligns error taxonomy with canonical contracts and improves incident diagnosability.

### 2026-04-10 17:59 UTC: Fold child-job trees into effective status and completion timestamps
**Context**: Reviewer identified parent orchestration jobs could look terminal before child work settled.

**Options considered**:
1. Use root-job status only.
2. Derive effective status and latest ended-at from recursive child job tree.

**Decision**: Option 2.

**Impact**: Prevents premature completion classification for fan-out operations while preserving deterministic readiness semantics.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Pipeline/readiness payloads drift from contract semantics | High | Medium | Added contract-focused payload assertions + review remediation tests | Mitigated |
| `next_actionable_steps` nondeterminism across equivalent runs | High | Medium | Added disturbed + baseline determinism regressions and stable ordering keys | Mitigated |
| Fan-out parent jobs misclassified as completed | High | Medium | Folded child status tree + latest child ended-at into effective job state | Mitigated |
| Auth/scope/session behavior drift from planned cutover | Medium | Medium | Security review + explicit accepted-risk note for temporary `rq:status` compatibility | Accepted-risk |
| Frozen inventory/checklist artifacts lag endpoint implementation | Medium | Medium | Updated artifacts in-package and enforced with guard scripts/tests | Mitigated |

## Verification Checklist

### Code Gate
- [x] `wctl run-pytest tests/microservices/test_rq_engine_orchestration_read_routes.py --maxfail=1`
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
- [x] Auth/scope/session/CSRF and run-state disclosure implications explicitly reviewed.
- [x] No unresolved medium/high security findings.

### Docs Gate
- [x] `wctl doc-lint` run on changed docs (`package.md`, `tracker.md`, completed ExecPlan/outcome, security artifact, frozen artifacts, and `PROJECT_TRACKER.md`).

## Reviewer Findings Disposition

### Independent Reviewer (`reviewer`) - 2026-04-10
1. **High**: `prepare-roads` completion semantics blocked `run-roads`.  
   **Disposition**: Resolved by allowing terminal finished-job fallback plus child-tree status folding; added regression coverage (`prepare-roads` finished -> `run-roads` ready).
2. **Medium**: `run-swat` could not reach completed state under prior completion criteria.  
   **Disposition**: Resolved via finished-job fallback plus child-tree-aware status folding to avoid parent-job premature completion.
3. **Medium**: Broad `ValueError` mapping to `404` hid internal state failures.  
   **Disposition**: Resolved with dedicated `RunConfigMismatchError` and narrow route-level `404` mapping.
4. **Medium (re-review)**: Mixed child status trees (`failed` + non-terminal) could be reported as running.  
   **Disposition**: Resolved by prioritizing failed/canceled child statuses over non-terminal states and adding regression test.

### QA Reviewer (`qa_reviewer`) - 2026-04-10
1. **High**: Naive datetime parsing was timezone-dependent.  
   **Disposition**: Resolved by normalizing naive parsed datetimes to UTC before timestamp conversion; added regression coverage.
2. **Medium**: Broad `ValueError` handling produced false `404` responses.  
   **Disposition**: Resolved with dedicated mismatch exception and explicit non-mismatch `500` regression test.
3. **Medium**: `updated_at` could drift per request while etag remained stable when timeline data was empty.  
   **Disposition**: Resolved by deterministic `UNKNOWN_UPDATED_AT` fallback and stability regression test.
4. **Coverage note**: Determinism coverage too narrow.  
   **Disposition**: Resolved with baseline determinism tests in addition to disturbed scenario tests.

### Security Reviewer (`security_reviewer`) - 2026-04-10
1. **Low**: Broad `ValueError` handling at route boundary masked internal faults as `404`.  
   **Disposition**: Resolved via `RunConfigMismatchError` + narrow 404 catches.
2. **Low**: `rq:status` still permitted orchestration reads.  
   **Disposition**: Accepted-risk for roadmap compatibility; follow-on package `20260410_rq_controller_state_auth_concurrency` owns tightening to `rq:read`-only semantics.

## Verification Evidence (Command Outcomes)

- `wctl run-pytest tests/microservices/test_rq_engine_orchestration_read_routes.py --maxfail=1` -> `25 passed`
- `wctl run-pytest tests/microservices/test_rq_engine_openapi_contract.py --maxfail=1` -> `9 passed`
- `python tools/check_endpoint_inventory.py` -> `Endpoint inventory check passed`
- `python tools/check_route_contract_checklist.py` -> `Route contract checklist check passed`
- `wctl run-pytest tests/tools/test_endpoint_inventory_guard.py tests/tools/test_route_contract_checklist_guard.py --maxfail=1` -> `2 passed`
- `wctl doc-lint --path docs/work-packages/20260208_rq_engine_agent_usability/artifacts/endpoint_inventory_freeze_20260208.md --path docs/work-packages/20260208_rq_engine_agent_usability/artifacts/route_contract_checklist_20260208.md --path docs/work-packages/20260410_rq_controller_state_orchestration_reads/package.md --path docs/work-packages/20260410_rq_controller_state_orchestration_reads/tracker.md --path docs/work-packages/20260410_rq_controller_state_orchestration_reads/prompts/completed/rq_controller_state_orchestration_reads_execplan.md --path docs/work-packages/20260410_rq_controller_state_orchestration_reads/prompts/completed/rq_controller_state_orchestration_reads_execplan_outcome.md --path docs/work-packages/20260410_rq_controller_state_orchestration_reads/artifacts/2026-04-10_security_review.md --path PROJECT_TRACKER.md` -> `8 files validated, 0 errors, 0 warnings`

## Final Handoff Summary

- Implemented and validated run-scoped orchestration reads (`/pipeline`, `/readiness`) with deterministic payload semantics and machine-safe blocker joins.
- Completed independent reviewer, QA, and security review loops with all findings resolved or explicitly accepted as low-risk follow-on.
- No unresolved medium/high QA or security findings remain.
