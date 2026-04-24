# Landuse Batched Mapping Submit (Single + Multi-OFE UX Unification)

**Status**: Complete (2026-04-24)
**Timezone**: UTC

## Overview
Landuse mapping currently submits an RQ request on every select change in the summary table. This works for many single-OFE interactions, but in Multi-OFE workflows it creates avoidable queue churn, lock contention, and dependency-chain failure modes (including deferred jobs blocked behind failed predecessors). This package introduces staged client-side mapping edits with an explicit submit action that sends one batched request for one or more mapping changes.

## Objectives
- Replace per-select-change mapping submissions with staged edits and explicit user submit.
- Use the same mapping UX pattern for single-OFE and Multi-OFE runs.
- Execute one mapping batch as one RQ job and one lock window for the landuse root.
- Remove `depends_on` chaining from mapping enqueue flow.
- Define explicit batch semantics (ordering, duplicate-key handling, and failure behavior).
- Preserve status-stream feedback, completion triggers, and report-refresh behavior.

## Scope
This package covers end-to-end mapping UX, API, queue wiring, and RQ execution changes for batched landuse mapping updates.

### Included
- `wepppy/weppcloud/templates/reports/landuse.htm` updates for staged mapping UX and explicit submit control.
- `wepppy/weppcloud/controllers_js/landuse.js` refactor from immediate mapping POST on `change` to staged edits + submit.
- `wepppy/microservices/rq_engine/landuse_routes.py` API contract update to accept mapping batches.
- `wepppy/rq/project_rq.py` mapping worker updates to apply multiple mapping edits under one lock.
- Removal of `depends_on` use for mapping enqueue path.
- Regression coverage updates:
  - `tests/microservices/test_rq_engine_landuse_routes.py`
  - `wepppy/weppcloud/controllers_js/__tests__/landuse.test.js`
  - `tests/rq/test_project_rq_mutation_guards.py`
- Work-package and contract documentation updates reflecting new request/response semantics.

### Explicitly Out of Scope
- Coverage override batching (`modify_landuse_coverage`) unless explicitly approved in this package.
- Landuse mode/build workflow redesign.
- Changes to unrelated queue orchestration outside mapping path.
- WEPP model execution/runtime changes outside landuse mapping mutation flow.

## Stakeholders
- **Primary**: WEPPcloud landuse users (single and Multi-OFE), NoDb/RQ maintainers.
- **Reviewers**: WEPPcloud controller maintainers, rq-engine maintainers, QA maintainers.
- **Security Reviewer**: Not required for current scope.
- **Informed**: Operators monitoring RQ lock contention and job lifecycle issues.

## Success Criteria
- [x] Changing a mapping select in landuse report no longer enqueues a mapping RQ job immediately.
- [x] User can stage one or more mapping changes and submit them with one explicit action.
- [x] Single-OFE and Multi-OFE use the same mapping interaction pattern.
- [x] Mapping submit enqueues one job without `depends_on` chaining to previous mapping jobs.
- [x] Batch worker applies edits deterministically and emits one completion trigger for the submitted job.
- [x] Lock contention and queue fan-out are reduced in repeated mapping-edit sessions.
- [x] Targeted JS + microservice + RQ tests pass with new batch semantics.

## Dependencies

### Prerequisites
- Existing landuse report rendering and controller wiring in current `master`.

### Blocks
- Follow-on UX cleanup packages that depend on stable staged-edit behavior in landuse report.

## Related Packages
- **Related**: [20251023_controller_modernization](../20251023_controller_modernization/package.md)
- **Related**: [20260423_landuse_multi_ofe_build_optimization](../20260423_landuse_multi_ofe_build_optimization/package.md)
- **Follow-up**: Optional package for staged coverage overrides if needed.

## Timeline Estimate
- **Expected duration**: 2-4 focused sessions.
- **Complexity**: Medium.
- **Risk level**: Medium (user-visible UX change and queue contract change).

## Security Impact and Review Gate
- **Security impact triage**: `low`
- **Dedicated security review required**: `no`
- **Triage rationale**: changes are limited to authenticated run-scoped mapping UX/API behavior; no new auth/session/secrets/egress surfaces.
- **Security review artifact**: `N/A`

## References
- `wepppy/weppcloud/controllers_js/landuse.js`
- `wepppy/weppcloud/templates/reports/landuse.htm`
- `wepppy/microservices/rq_engine/landuse_routes.py`
- `wepppy/rq/project_rq.py`
- `tests/microservices/test_rq_engine_landuse_routes.py`
- `wepppy/weppcloud/controllers_js/__tests__/landuse.test.js`
- `tests/rq/test_project_rq_mutation_guards.py`

## Deliverables
- Batch mapping submit UX in landuse report with staged-change affordances.
- Updated rq-engine mapping API contract supporting list-based mapping updates.
- Mapping RQ execution path updated to process a batch in one job/lock scope.
- Removed mapping `depends_on` chaining logic.
- Updated targeted automated tests and package artifacts.

## Implemented Contract Decisions
- **Batch payload shape and limits**: canonical payload is `{"mappings":[{"dom":"...","newdom":"..."}, ...]}` with max 500 edits; response is `{"job_id":"...", "mapping_count": <int>}`.
- **Duplicate/chained edit semantics**: duplicate source `dom` entries collapse to last-write-wins; normalized edits execute in deterministic first-seen source-domain order.
- **All-or-nothing semantics**: route validates request before enqueue; worker validates all source doms before mutation; unknown source dom aborts without mutation; mapping state snapshots restore on downstream build exception.
- **Backward compatibility**: legacy top-level `{"dom":"...","newdom":"..."}` remains accepted and is normalized to a one-item `mappings` batch.

## Validation Summary
- `wctl run-pytest tests/microservices/test_rq_engine_landuse_routes.py --maxfail=1` (`19 passed`)
- `wctl run-pytest tests/rq/test_project_rq_mutation_guards.py --maxfail=1` (`23 passed`)
- `wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse.test.js` (`20 passed`)
- `wctl doc-lint --path docs/work-packages/20260423_landuse_batched_mapping_submit` (`4 files validated, 0 errors`)
- `wctl check-rq-graph` (`RQ dependency graph artifacts are up to date`)
- `wctl exec weppcloud python - <<'PY' ... Queue(...).job_ids ... PY` (`default_queue_jobs=0`; no live tree sample available for job-info inspection)
- Manual UX smoke (user-reported): `greenlight`, `job_id=3082d0f1-acd4-41e0-b897-abda94b31c1f`

## Post-Review Disposition
- Dispatched code + QA review pass and dispositioned all actionable findings in this package.
- Added guardrails for lock-gate stale completion short-circuiting, explicit `null` mapping-key validation, readonly submit disabling, inflight staging protection, and `project_rq.pyi` parity.

## Follow-up Work
- Evaluate whether staged-submit pattern should be applied to coverage overrides after mapping rollout stabilizes.
