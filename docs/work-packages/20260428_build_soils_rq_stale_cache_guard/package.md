# `build_soils_rq` Stale NoDb Cache Guard

**Status**: Closed (2026-04-28)
**Timezone**: UTC

## Overview
This package addresses a production failure where `build_soils_rq` rejected a stale write after hydrating `Soils` from an older NoDb cache signature. The observed failure on `wepp1` (`runid=northwestern-yes`, `job_id=40ded984-4d89-44a2-a41e-f253d9dc1bd0`) was `NoDbStaleWriteError` for `soils.nodb` with an older expected `(mtime,size)` than the on-disk file. The intent is to add a scoped guard in `build_soils_rq` so stale `soils.nodb` cache payloads are cleared before hydration/build.

## Objectives
- Add a scoped stale-cache guard in `wepppy.rq.project_rq.build_soils_rq` before `Soils.getInstance(wd).build()`.
- Preserve existing route/job contracts while removing this known stale-cache failure mode for soils builds.
- Add targeted regression coverage proving the guard is executed on the `build_soils_rq` path.
- Document the contract and validation evidence in package artifacts.

## Scope
This package is scoped to the soils build RQ path and adjacent tests/docs required to safely land the guard.

### Included
- `wepppy/rq/project_rq.py`: `build_soils_rq` guard addition using scoped `clear_nodb_file_cache` for `soils.nodb`.
- `tests/rq/test_project_rq_mutation_guards.py`: regression coverage for guard invocation/ordering and existing boundary behavior.
- Minimal doc updates for package lifecycle (`package.md`, `tracker.md`, active ExecPlan, `PROJECT_TRACKER.md`).

### Explicitly Out of Scope
- Broader NoDb cache architecture changes in `wepppy/nodb/base.py`.
- Queue topology rewiring or dependency graph changes.
- Landuse/climate grouped-mutation refactors unrelated to `build_soils_rq`.
- Container/service restarts or operational runbook changes.

## Stakeholders
- **Primary**: RQ operators, NoDb maintainers, soils pipeline maintainers.
- **Reviewers**: RQ/NoDb maintainers (`reviewer`, `qa_reviewer` if required by execution flow).
- **Security Reviewer**: Not required by default; no new auth/public route surface expected.
- **Informed**: Incident responders tracking `NoDbStaleWriteError` recurrence.

## Success Criteria
- [x] `build_soils_rq` clears the scoped `soils.nodb` Redis cache before hydrating/building soils.
- [x] Existing archive-root precondition behavior (`NoDirError`) remains unchanged.
- [x] Targeted regression tests pass for the modified RQ path.
- [x] Package docs and `PROJECT_TRACKER.md` remain synchronized and lint-clean.

## Dependencies

### Prerequisites
- Current NoDb stale-write guard behavior in `wepppy/nodb/base.py`.
- Existing `clear_nodb_file_cache` helper and scoped `pup_relpath` support.
- Existing `build_soils_rq` contract/tests in `project_rq.py` and `tests/rq/test_project_rq_mutation_guards.py`.

### Blocks
- None currently identified.

## Related Packages
- **Related**: [20260424_rq_worker_nodb_cache_hardening](../20260424_rq_worker_nodb_cache_hardening/package.md)
- **Related**: [20260425_nodb_atomicity_observability_followups_a](../20260425_nodb_atomicity_observability_followups_a/package.md)
- **Related**: [20260427_rq_subwta_precondition_contract](../20260427_rq_subwta_precondition_contract/package.md)

## Timeline Estimate
- **Expected duration**: 1 focused session for implementation + validation, plus review cycle if required.
- **Complexity**: Low-Medium.
- **Risk level**: Medium (touches production RQ mutation path).

## Security Impact and Review Gate
- **Security impact triage**: `low`
- **Dedicated security review required**: `no`
- **Triage rationale**: internal reliability hardening in an existing authenticated/worker path with no new public endpoint or privilege model changes.
- **Security review artifact**: `N/A`

## Hardening and Callus Softening (Required for incident/remediation packages)
- **Failure signature(s)**:
  - `wepppy.nodb.base.NoDbStaleWriteError: stale NoDb write rejected for /wc1/runs/no/northwestern-yes/soils.nodb ...`
  - Failed job: `40ded984-4d89-44a2-a41e-f253d9dc1bd0`.
- **Related prior hardening efforts**:
  - `20260424_rq_worker_nodb_cache_hardening`
  - `20260425_nodb_atomicity_observability_followups_a`
- **Health signals**:
  - No recurrence of stale-cache `build_soils_rq` failures for equivalent run flows.
  - Guard test remains green and catches accidental removal.
- **Danger signals**:
  - New false-positive cache clears outside `soils.nodb` scope.
  - Contract drift in archive-root and job-status behavior.
- **Observation window**: package execution + first post-merge regression cycle.
- **Temporary calluses introduced**: none planned.
- **Callus softening hypothesis (if applicable)**: not applicable; this package introduces a narrow deterministic guard.

## References
- `wepppy/rq/project_rq.py` - `build_soils_rq` implementation path.
- `wepppy/nodb/base.py` - stale-write and NoDb cache semantics.
- `tests/rq/test_project_rq_mutation_guards.py` - existing route/mutation guard tests.
- `docs/work-packages/20260424_rq_worker_nodb_cache_hardening/package.md` - prior cache hardening context.
- `docs/work-packages/20260425_nodb_atomicity_observability_followups_a/package.md` - follow-up consistency hardening context.

## Deliverables
- Guard implementation in `build_soils_rq` with scoped cache clear for `soils.nodb`.
- Targeted regression tests for guard behavior and non-regression path checks.
- Updated package artifacts and tracker entries with validation evidence.

## Closure Notes

**Closed**: 2026-04-28 15:58 UTC

**Summary**: `build_soils_rq` now clears only the `soils.nodb` NoDb cache inside the existing soils directory-root lock callback and before `Soils.getInstance(wd).build()`. Status publication, completion trigger, and `TaskEnum.build_soils` timestamp behavior remain in the same order after the locked build. Archive-backed soils roots still raise `NoDirError` before cache clearing or soils hydration.

**Validation**:
- `wctl run-pytest tests/rq/test_project_rq_mutation_guards.py --maxfail=1` passed with `26 passed`.
- `wctl run-pytest tests/microservices/test_rq_engine_soils_routes.py --maxfail=1` passed with `3 passed`.
- `wctl doc-lint --path docs/work-packages/20260428_build_soils_rq_stale_cache_guard --path PROJECT_TRACKER.md` passed with `5 files validated, 0 errors, 0 warnings`.
- `git diff --check` passed.

**Archive Status**: Active ExecPlan archived under `prompts/completed/`.

## Follow-up Work
- Evaluate whether equivalent scoped guards are needed in additional RQ mutation jobs if future incidents show the same stale-cache signature pattern outside soils.

## Kickoff Prompt
- Execution prompt: `docs/work-packages/20260428_build_soils_rq_stale_cache_guard/prompts/active/execute_build_soils_rq_stale_cache_guard_prompt.md`
- Completed ExecPlan: `docs/work-packages/20260428_build_soils_rq_stale_cache_guard/prompts/completed/build_soils_rq_stale_cache_guard_execplan.md`
