# NoDb Atomicity, RQ Graph Baseline, and Observability Follow-Ups

**Status**: Open (2026-04-25 23:06 UTC)
**Timezone**: UTC

## Overview
This package follows `20260425_nodb_lock_dump_efficiency_refactor` and addresses the remaining hardening and maintainability gaps identified at closeout. The work combines transactional-consistency design/implementation for grouped NoDb mutations, queue-graph baseline hygiene, failure-path validation at the WEPP job-hint boundary, and guardrails against lock/dump-efficiency regressions.

## Objectives
- Implement a bounded cross-controller failure-atomicity strategy for scoped rq-engine mutation flows so late-stage failures do not leave avoidable partial persisted state.
- Resolve current `wctl check-rq-graph` drift to restore a clean baseline signal for future queue-wiring changes.
- Harden and validate post-enqueue WEPP job-hint persistence fault paths (including concurrency/error-class boundaries) while preserving response contracts.
- Add lock/dump-efficiency observability guards that detect reintroduction of sequential lock/dump churn in targeted rq-engine paths.
- Improve rq-engine test maintainability by reducing duplicated dummy collaborators and brittle assertions in touched suites.

## Scope
This package is scoped to rq-engine + required NoDb helpers + test/tooling/docs updates directly needed to deliver the five follow-ups above.

### Included
- Cross-controller atomicity design and implementation for scoped grouped-mutation flows in rq-engine/NoDb surfaces touched by the prior package.
- Queue-graph baseline cleanup (`wctl check-rq-graph` drift disposition with artifact regeneration or equivalent corrective action).
- WEPP job-hint failure-path hardening and concurrency/error-path tests for post-enqueue persistence behavior.
- Lock/dump-efficiency observability guard implementation (tests/tooling) for scoped rq-engine mutation paths.
- Test maintainability cleanup in affected `tests/microservices/test_rq_engine_*` suites and shared helper extraction where warranted.
- Package docs, tracker, and ExecPlan updates required for implementation and closure evidence.

### Explicitly Out of Scope
- Legacy Flask route work under `wepppy/weppcloud/routes/nodb_api/**`.
- Broad queue-topology redesign beyond drift baseline correction.
- Unrelated NoDb controller rewrites not required for scoped atomicity implementation.
- Frontend/controller-JS refactors unrelated to rq-engine mutation orchestration.

## Stakeholders
- **Primary**: NoDb maintainers, rq-engine maintainers, RQ operators.
- **Reviewers**: `reviewer` (correctness), `qa_reviewer` (coverage/maintainability), `security_reviewer` (error-boundary and auth-adjacent safety).
- **Security Reviewer**: recommended (boundary/error handling changes touch post-enqueue behavior semantics).
- **Informed**: maintainers of queue wiring and NoDb hardening standards.

## Success Criteria
- [ ] Scoped cross-controller atomicity strategy is implemented with explicit contract docs and regression coverage for failure paths.
- [ ] `wctl check-rq-graph` is clean (or drift source is corrected and documented with updated canonical artifacts).
- [ ] Post-enqueue WEPP job-hint persistence fault-path behavior is validated for non-`RuntimeError` classes and lock-contention scenarios per decided contract.
- [ ] Lock/dump-efficiency observability guard exists and passes for scoped routes/helpers.
- [ ] Test maintainability cleanup is completed for scoped suites (shared helpers/fixtures, reduced brittle assertions) without behavior regression.
- [ ] Targeted validation suite passes and package docs (`package.md`, `tracker.md`, ExecPlan, `PROJECT_TRACKER.md`) are current.

## Dependencies

### Prerequisites
- Completed package: `docs/work-packages/20260425_nodb_lock_dump_efficiency_refactor/package.md`.
- Canonical response contract: `docs/schemas/rq-response-contract.md`.
- Existing NoDb lock ownership baseline from `20260424_rq_worker_nodb_cache_hardening`.

### Blocks
- Future lock/dump hot-spot remediation packages that depend on observability guard patterns from this package.

## Related Packages
- **Depends on**: [20260425_nodb_lock_dump_efficiency_refactor](../20260425_nodb_lock_dump_efficiency_refactor/package.md)
- **Related**: [20260424_rq_worker_nodb_cache_hardening](../20260424_rq_worker_nodb_cache_hardening/package.md)
- **Follow-up**: potential broader transaction-contract package if scoped atomicity solution reveals wider architecture needs.

## Timeline Estimate
- **Expected duration**: 2-4 focused sessions.
- **Complexity**: Medium-High.
- **Risk level**: Medium.

## Security Impact and Review Gate
- **Security impact triage**: `low`
- **Dedicated security review required**: `no`
- **Triage rationale**: work is internal reliability/error-boundary hardening and queue metadata hygiene; it does not add new externally exposed endpoints or auth surfaces, but boundary behavior must still be reviewed.
- **Security review artifact**: `N/A`

## Hardening and Callus Softening (Required for incident/remediation packages)
- **Applicability**: Preventive hardening + post-closure callus softening from prior lock/dump package.
- **Failure signature(s)**:
  - Partial persisted state across controllers on late failure after earlier grouped helper persistence.
  - `wctl check-rq-graph` drift obscuring real queue-wiring regressions.
  - Post-enqueue hint persistence failures potentially bubbling on non-`RuntimeError` exception classes.
- **Related prior hardening efforts**:
  - `20260425_nodb_lock_dump_efficiency_refactor`
  - `20260424_rq_worker_nodb_cache_hardening`
- **Health signals**:
  - Scoped failure paths leave no unintended partial persisted state.
  - Queue-graph check baseline is clean and stable.
  - WEPP job enqueue responses remain contract-stable under persistence-fault paths.
  - Guard tests detect lock/dump-churn regressions early.
- **Danger signals**:
  - Hidden contract changes in rq-engine responses.
  - Overscoped transactional abstractions with unclear rollback semantics.
  - Guard tooling too brittle/noisy to maintain.
- **Observation window**: package execution window + first post-merge regression cycle.
- **Temporary calluses introduced**: none planned.
- **Callus softening hypothesis (if applicable)**: if current narrow fail-open exception handling is broadened, behavior can be made both explicit and resilient without introducing silent failure masking.

## References
- `wepppy/microservices/rq_engine/wepp_run_payload.py`
- `wepppy/microservices/rq_engine/wepp_routes.py`
- `wepppy/microservices/rq_engine/bootstrap_routes.py`
- `wepppy/nodb/core/wepp.py`
- `wepppy/nodb/core/soils.py`
- `wepppy/nodb/core/watershed.py`
- `wepppy/nodb/base.py`
- `wepppy/rq/job-dependency-graph.static.json`
- `wepppy/rq/job-dependencies-catalog.md`
- `tests/microservices/test_rq_engine_wepp_routes.py`
- `tests/microservices/test_rq_engine_bootstrap_routes.py`
- `tests/nodb/test_wepp_job_hint_grouped_updates.py`
- `docs/standards/hardening-lifecycle-standard.md`
- `docs/schemas/rq-response-contract.md`

## Deliverables
- Open (to be filled at closure).

## Follow-up Work
- Open (to be filled at closure).

## Closure Notes
- Open (to be filled at closure).

## Kickoff Prompt
- Active ExecPlan: `docs/work-packages/20260425_nodb_atomicity_observability_followups_a/prompts/active/nodb_atomicity_observability_followups_execplan.md`
