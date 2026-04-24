# Landuse Batched Mapping Submit (Single + Multi-OFE UX Unification)

**Status**: Open (2026-04-23)
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
- [ ] Changing a mapping select in landuse report no longer enqueues a mapping RQ job immediately.
- [ ] User can stage one or more mapping changes and submit them with one explicit action.
- [ ] Single-OFE and Multi-OFE use the same mapping interaction pattern.
- [ ] Mapping submit enqueues one job without `depends_on` chaining to previous mapping jobs.
- [ ] Batch worker applies edits deterministically and emits one completion trigger for the submitted job.
- [ ] Lock contention and queue fan-out are reduced in repeated mapping-edit sessions.
- [ ] Targeted JS + microservice + RQ tests pass with new batch semantics.

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

## Follow-up Work
- Evaluate whether staged-submit pattern should be applied to coverage overrides after mapping rollout stabilizes.
