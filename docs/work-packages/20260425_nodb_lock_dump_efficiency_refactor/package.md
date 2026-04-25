# NoDb Lock/Dump Efficiency Refactor (RQ Engine)

**Status**: Closed (2026-04-25 21:55 UTC)
**Timezone**: UTC

## Overview
`Wepp.parse_inputs()` and the climate parser already use a single lock context per parse call, but several rq-engine mutation paths still perform sequential `@nodb_setter` writes. Because `@nodb_setter` wraps each write in `with self.locked()`, those paths create avoidable lock/dump churn, increase contention windows, and add unnecessary Redis/file persistence overhead.

This package refactors the highest-impact and secondary rq-engine candidates into single-lock mutation flows while preserving existing request contracts and behavior. Legacy Flask routes are explicitly excluded.

## Objectives
- Reduce lock/dump churn in the highest-impact rq-engine mutation paths identified during lock-efficiency discovery.
- Refactor secondary rq-engine candidates where multi-field updates are currently persisted as multiple independent lock/dump cycles.
- Preserve payload contracts, response contracts, and controller invariants while changing mutation orchestration.
- Add regression coverage that demonstrates behavioral parity and validates single-lock mutation semantics for touched paths.
- Document the lock/dump efficiency rule and applied patterns for future NoDb work.

## Scope
This package targets rq-engine and NoDb facade mutation orchestration only.

### Included
- Highest-impact refactors:
  - `wepppy/microservices/rq_engine/wepp_run_payload.py`
  - `wepppy/microservices/rq_engine/watershed_routes.py`
  - `wepppy/microservices/rq_engine/landuse_routes.py` (`build-landuse` disturbed toggles + `set-landuse-mode` dual-field set)
- Secondary refactors:
  - `wepppy/microservices/rq_engine/upload_batch_runner_routes.py`
  - `wepppy/microservices/rq_engine/wepp_routes.py`
  - `wepppy/microservices/rq_engine/bootstrap_routes.py`
- Supporting controller/facade helper updates under `wepppy/nodb/**` as needed to enable single-lock mutation entrypoints.
- Tests and docs updates required to prove parity and enforce the new mutation pattern.

### Explicitly Out of Scope
- Legacy Flask route refactors under `wepppy/weppcloud/routes/nodb_api/**`.
- Business-rule changes to payload validation or run workflow semantics.
- Queue topology changes, new job dependency edges, or RQ graph rewiring.
- Redis connection strategy changes (handled in prior/parallel packages).

## Stakeholders
- **Primary**: NoDb maintainers, rq-engine maintainers, RQ operators.
- **Reviewers**: code reviewer + QA reviewer for behavior/regression parity.
- **Security Reviewer**: optional (security triage is low).
- **Informed**: maintainers of packages touching adjacent lock/cache hardening work.

## Success Criteria
- [x] Highest-impact paths are converted to single-lock mutation orchestration with no behavior regressions.
- [x] Secondary candidates are converted to single-lock mutation orchestration with no behavior regressions.
- [x] No legacy Flask files are changed.
- [x] Targeted regression tests are added/updated and passing.
- [x] `wctl check-rq-graph` result is documented with no queue-wiring edits in this package.
- [x] Documentation updated to capture the lock/dump efficiency rule and the preferred facade mutation pattern.

## Dependencies

### Prerequisites
- Existing NoDb lock ownership and stale-write hardening baseline from:
  - `docs/work-packages/20260424_rq_worker_nodb_cache_hardening/package.md`
- Current rq-engine route behavior and payload contracts in:
  - `docs/schemas/rq-response-contract.md`

### Blocks
- None.

## Related Packages
- **Related**: [20260424_rq_worker_nodb_cache_hardening](../20260424_rq_worker_nodb_cache_hardening/package.md)
- **Related**: [20260410_rq_controller_state_auth_concurrency](../20260410_rq_controller_state_auth_concurrency/package.md)
- **Follow-up**: potential cleanup package for lower-priority lock/dump churn outside rq-engine if additional hotspots are confirmed.

## Timeline Estimate
- **Expected duration**: 2-4 focused sessions.
- **Complexity**: Medium.
- **Risk level**: Medium.

## Security Impact and Review Gate
- **Security impact triage**: `low`
- **Dedicated security review required**: `no`
- **Triage rationale**: changes are internal mutation-orchestration refactors that should not alter auth boundaries, route exposure, or privilege semantics.
- **Security review artifact**: `N/A`

## Hardening and Callus Softening (Required for incident/remediation packages)
- **Applicability**: Not an incident-response package; this is preventive lock/dump efficiency and reliability hardening.
- **Failure signature(s)**: N/A (no single triggering incident).
- **Related prior hardening efforts**: `20260424_rq_worker_nodb_cache_hardening`.
- **Health signals**: lower mutation-path lock churn, reduced persistence overhead, unchanged route behavior.
- **Danger signals**: hidden contract changes, direct underscore writes outside lock discipline, coverage gaps.
- **Observation window**: during package execution and post-merge CI/regression runs.
- **Temporary calluses introduced**: none planned.
- **Callus softening hypothesis**: N/A.

## References
- `wepppy/nodb/base.py`
- `wepppy/nodb/core/wepp.py`
- `wepppy/nodb/core/climate_input_parser.py`
- `wepppy/microservices/rq_engine/wepp_run_payload.py`
- `wepppy/microservices/rq_engine/watershed_routes.py`
- `wepppy/microservices/rq_engine/landuse_routes.py`
- `wepppy/microservices/rq_engine/upload_batch_runner_routes.py`
- `wepppy/microservices/rq_engine/wepp_routes.py`
- `wepppy/microservices/rq_engine/bootstrap_routes.py`
- `docs/standards/nodb-facade-collaborator-pattern.md`
- `docs/work-packages/README.md`
- `docs/prompt_templates/codex_exec_plans.md`

## Deliverables
- Grouped single-lock mutation helper flows delivered for all scoped highest-impact and secondary candidates:
  - `wepp_run_payload.py` + `Soils`/`Watershed` grouped apply helpers.
  - `watershed_routes.py` + grouped build-subcatchment update helper.
  - `landuse_routes.py` + grouped `Landuse` and `Disturbed` update helpers.
  - `upload_batch_runner_routes.py` + grouped `BatchRunner` SBS helper.
  - `wepp_routes.py` + `bootstrap_routes.py` + grouped `Wepp.persist_job_hint(...)`.
- New/updated parity regressions in scoped microservice and NoDb suites, including direct grouped-helper branch coverage tests under `tests/nodb/`.
- Package closure evidence in:
  - `tracker.md` (timeline, review dispositions, validation logs).
  - Completed ExecPlan under `prompts/completed/`.

## Follow-up Work
- Optional hardening follow-up: evaluate whether post-enqueue WEPP job-hint persistence should catch additional NoDb lock exceptions beyond `RuntimeError` while preserving response-contract stability.
- Optional architectural follow-up: design broader cross-controller transaction semantics for failure-atomicity across multi-controller mutation sequences.

## Closure Notes
- All scoped backlog items were completed in required execution order with per-milestone review triads and Medium/High finding closure before milestone progression.
- Final targeted package validation passed:
  - `wctl run-pytest ...` across 10 scoped suites (`198 passed`).
- `wctl check-rq-graph` was executed; it reported drift in existing graph/catalog artifacts, but no queue-wiring files were edited in this package.
- Scope discipline held: no changes under legacy Flask `wepppy/weppcloud/routes/nodb_api/**`.
- Lock/dump efficiency rule captured and applied consistently: route-level multi-field updates now flow through explicit grouped helper entrypoints that execute one lock/dump cycle per controller mutation sequence.

## Kickoff Prompt
- Completed ExecPlan: `docs/work-packages/20260425_nodb_lock_dump_efficiency_refactor/prompts/completed/nodb_lock_dump_efficiency_refactor_execplan.md`
