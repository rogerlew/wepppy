# RQ Scoped Stale NoDb Cache Guard Priority 2

**Status**: Complete (2026-04-28)  
**Timezone**: UTC  
**Priority class**: Priority 2 follow-up from the scoped stale-cache guard rollout

## Overview

This package scopes the Priority 2 module-family follow-ups deferred from
`docs/work-packages/20260428_rq_scoped_stale_cache_guard_followups/`.
The work continues adoption of the canonical scoped NoDb mutation cache-guard
contract for RQ jobs that hydrate a run-scoped NoDb controller and then mutate
or persist that controller.

This is standards conformance work, not incident hardening. The package should
only add guards to confirmed hydrate-then-mutate paths with exact
`pup_relpath` scopes and targeted regression coverage.

## Canonical Contract Reference

This package executes against:

- `docs/standards/rq-scoped-nodb-mutation-cache-guard-standard.md`

The governing contract requires scoped cache clearing after preconditions and
immediately before mutable controller hydration. It also excludes read-only
hydration, non-runid workspaces, broad lifecycle resets, and speculative guard
coverage.

## Objectives

- Audit each Priority 2 module family against the scoped mutation cache-guard
  standard.
- Implement scoped guards for confirmed, testable mutation paths.
- Record explicit split/defer/not-applicable disposition where a path needs a
  narrower package or does not meet the standard.
- Preserve existing lock, archive-root, status, timestamp, enqueue, clone,
  deletion, autocommit, and runtime-lock contracts.
- Add targeted regression coverage for every touched implementation module.

## Candidate Modules

The candidates below come from the closure disposition in
`20260428_rq_scoped_stale_cache_guard_followups`.

| File | Candidate functions | Initial guard scope | Primary validation focus |
|------|---------------------|---------------------|--------------------------|
| `wepppy/rq/wepp_rq.py` | `bootstrap_enable_rq`, `run_wepp_rq`, `run_wepp_watershed_rq`, `prep_wepp_watershed_rq` | `wepp.nodb` | Bootstrap state, mixed-NoDir recovery, queue pipeline metadata, lock/status behavior. |
| `wepppy/rq/swat_rq.py` | `_build_swat_inputs_rq`, `_run_swat_rq`, `run_swat_interchange_rq` | `swat.nodb` | Build/run/interchange mutations, bootstrap autocommit side effects, status/timestamp behavior. |
| `wepppy/rq/omni_rq.py` | `run_omni_scenario_rq`, `run_omni_contrast_rq`, `run_omni_scenarios_rq`, `run_omni_contrasts_rq`, `delete_omni_contrasts_rq` | `omni.nodb` plus per-PUP scopes only where proven | Existing clone cache helpers, concurrency branches, scenario/contrast deletion behavior. |
| `wepppy/rq/path_ce_rq.py` | `run_path_cost_effective_rq` | `path_ce.nodb`, `omni.nodb` | Combined PATH and Omni mutation ordering, progress/status behavior, solver failure paths. |
| `wepppy/rq/roads_rq.py` | `run_roads_prepare_rq`, `run_roads_rq` | `roads.nodb` | Enabled-state sync, single-flight runtime lock behavior, prepare/run completion timestamps. |
| `wepppy/rq/geneva_rq.py` | `run_geneva_prepare_hrus_rq`, `run_geneva_build_frequency_panel_rq`, `run_geneva_run_batch_rq` | `geneva.nodb` | Config-specific controller creation, best-effort state-lock retries, completion state. |
| `wepppy/rq/project_rq_fork.py` | `prepare_fork_run(..., undisturbify=True)` | new-run `ron.nodb`, `disturbed.nodb`, `landuse.nodb`, `soils.nodb` | New-runid cache keying, copied `.nodb` rewrite order, undisturbify mutations. |

## Scope

### Included

- Method-level audit of the listed Priority 2 module families.
- Guard implementation where the mutation boundary, runid cache key, and
  regression test can be kept narrow.
- Per-module tests under `tests/rq/` for exact scope and guard-before-hydration
  ordering.
- Written disposition for each candidate path: `implemented`, `split/defer`, or
  `not_applicable`.
- Package lifecycle updates in `package.md`, `tracker.md`, the active ExecPlan,
  and `PROJECT_TRACKER.md`.

### Explicitly Out of Scope

- Reworking NoDb cache internals or Redis dependency handling.
- Replacing scoped guards with broad run-wide cache clears.
- Guarding read-only `getInstance(...)` calls.
- Queue topology or dependency-edge changes unless implementation proves they
  are unavoidable. If queue wiring changes, update
  `wepppy/rq/job-dependencies-catalog.md` and run `wctl check-rq-graph`.
- Changes to endpoint auth, public API payloads, or user-visible run data
  schemas.

## Success Criteria

- [x] Every listed Priority 2 candidate has an evidence-backed disposition.
- [x] Implemented guards use exact `pup_relpath` values and execute after
      preconditions but before mutable hydration.
- [x] Existing status, timestamp, enqueue, lock, clone, deletion, and
      autocommit behavior remains unchanged.
- [x] Focused pytest commands pass for every touched non-`project_rq.py` module.
- [x] Work-package docs and `PROJECT_TRACKER.md` pass docs lint.

## Validation Plan

Run targeted tests for each touched module. Expected starting points:

- `wctl run-pytest tests/rq/test_bootstrap_enable_rq.py tests/rq/test_bootstrap_autocommit_rq.py --maxfail=1`
- `wctl run-pytest tests/rq/test_omni_rq.py --maxfail=1`
- `wctl run-pytest tests/rq/test_path_ce_rq.py --maxfail=1`
- `wctl run-pytest tests/rq/test_roads_rq.py --maxfail=1`
- `wctl run-pytest tests/rq/test_geneva_rq.py --maxfail=1`
- `wctl run-pytest tests/rq/test_project_rq_fork.py --maxfail=1`
- `wctl doc-lint --path docs/work-packages/20260428_rq_scoped_stale_cache_guard_priority2 --path PROJECT_TRACKER.md`
- `git diff --check`

If only a subset of modules is implemented in one execution pass, run the
commands for that subset plus docs lint and `git diff --check`.

## Security Impact and Review Gate

- **Security impact triage**: `low`
- **Dedicated security review required**: `no`
- **Triage rationale**: internal worker cache-coherence conformance in existing
  queued paths with no expected endpoint, auth, privilege, or data-schema
  surface change.
- **Security review artifact**: `N/A`

Revisit this triage if implementation changes endpoint behavior, queue
authorization boundaries, or run-scoped access expectations.

## Deliverables

- Scoped guard implementation or explicit disposition for each Priority 2
  candidate.
- Focused regression tests for every touched module.
- Updated package lifecycle docs with UTC-stamped progress and validation
  evidence.
- Completed ExecPlan moved from `prompts/active/` to `prompts/completed/` at
  closure.

## Dependencies

- Completed follow-up package:
  `docs/work-packages/20260428_rq_scoped_stale_cache_guard_followups/`
- Canonical standard:
  `docs/standards/rq-scoped-nodb-mutation-cache-guard-standard.md`
- Existing RQ fixtures in `tests/rq/` for WEPP, SWAT, Omni, PATH CE, Roads,
  Geneva, and project fork workflows.

## Related Packages

- **Depends on:** [RQ Scoped Stale NoDb Cache Guard Follow-Ups](../20260428_rq_scoped_stale_cache_guard_followups/package.md)
- **Related:** [Build Soils RQ Stale Cache Guard](../20260428_build_soils_rq_stale_cache_guard/package.md)
- **Related:** [RQ Worker NoDb Cache Hardening](../20260424_rq_worker_nodb_cache_hardening/package.md)

## Closure Summary

Closed on 2026-04-28 with all listed Priority 2 candidate call sites implemented.
Each confirmed mutate path now clears a scoped NoDb cache entry immediately before
mutable controller hydration using exact per-file `pup_relpath` values.

The fork-undisturbify path was implemented with explicit `new_runid` cache-keyed
clears (`ron.nodb`, `disturbed.nodb`, `landuse.nodb`, `soils.nodb`) via an
injected cache-clear collaborator in `prepare_fork_run(...)`, preserving existing
fork behavior and making scope/order testable.

No queue wiring or dependency-edge behavior changed, so
`wepppy/rq/job-dependencies-catalog.md` and `wctl check-rq-graph` were not
required.

### Implementation and Disposition Matrix

| Candidate path | Disposition | Guard scope |
|----------------|-------------|-------------|
| `wepppy/rq/wepp_rq.py::bootstrap_enable_rq` | Implemented | `wepp.nodb` |
| `wepppy/rq/wepp_rq.py::run_wepp_rq` | Implemented | `wepp.nodb` |
| `wepppy/rq/wepp_rq.py::run_wepp_watershed_rq` | Implemented | `wepp.nodb` |
| `wepppy/rq/wepp_rq.py::prep_wepp_watershed_rq` | Implemented | `wepp.nodb` |
| `wepppy/rq/swat_rq.py::_build_swat_inputs_rq` | Implemented | `swat.nodb` |
| `wepppy/rq/swat_rq.py::_run_swat_rq` | Implemented | `swat.nodb` |
| `wepppy/rq/swat_rq.py::run_swat_interchange_rq` | Implemented | `swat.nodb` |
| `wepppy/rq/omni_rq.py::run_omni_scenario_rq` | Implemented | `omni.nodb` |
| `wepppy/rq/omni_rq.py::run_omni_contrast_rq` | Implemented | `omni.nodb` |
| `wepppy/rq/omni_rq.py::run_omni_scenarios_rq` | Implemented | `omni.nodb` |
| `wepppy/rq/omni_rq.py::run_omni_contrasts_rq` | Implemented | `omni.nodb` |
| `wepppy/rq/omni_rq.py::delete_omni_contrasts_rq` | Implemented | `omni.nodb` |
| `wepppy/rq/path_ce_rq.py::run_path_cost_effective_rq` | Implemented | `path_ce.nodb`, `omni.nodb` |
| `wepppy/rq/roads_rq.py::run_roads_prepare_rq` | Implemented | `roads.nodb` |
| `wepppy/rq/roads_rq.py::run_roads_rq` | Implemented | `roads.nodb` |
| `wepppy/rq/geneva_rq.py::run_geneva_prepare_hrus_rq` | Implemented | `geneva.nodb` |
| `wepppy/rq/geneva_rq.py::run_geneva_build_frequency_panel_rq` | Implemented | `geneva.nodb` |
| `wepppy/rq/geneva_rq.py::run_geneva_run_batch_rq` | Implemented | `geneva.nodb` |
| `wepppy/rq/project_rq_fork.py::prepare_fork_run(..., undisturbify=True)` | Implemented | `new_runid` scopes: `ron.nodb`, `disturbed.nodb`, `landuse.nodb`, `soils.nodb` |

### Validation Evidence

- `wctl run-pytest tests/rq/test_bootstrap_enable_rq.py tests/rq/test_bootstrap_autocommit_rq.py --maxfail=1` -> `21 passed, 6 warnings`.
- `wctl run-pytest tests/rq/test_omni_rq.py --maxfail=1` -> `15 passed, 4 warnings`.
- `wctl run-pytest tests/rq/test_path_ce_rq.py --maxfail=1` -> `3 passed, 4 warnings`.
- `wctl run-pytest tests/rq/test_roads_rq.py --maxfail=1` -> `4 passed, 4 warnings`.
- `wctl run-pytest tests/rq/test_geneva_rq.py --maxfail=1` -> `5 passed, 2 warnings`.
- `wctl run-pytest tests/rq/test_project_rq_fork.py --maxfail=1` -> `13 passed, 2 warnings`.
- `wctl doc-lint --path docs/work-packages/20260428_rq_scoped_stale_cache_guard_priority2 --path PROJECT_TRACKER.md` -> passed.
- `git diff --check` -> passed.

## Kickoff Prompt

- Execution prompt: `docs/work-packages/20260428_rq_scoped_stale_cache_guard_priority2/prompts/active/execute_rq_scoped_stale_cache_guard_priority2_prompt.md`
- Completed ExecPlan: `docs/work-packages/20260428_rq_scoped_stale_cache_guard_priority2/prompts/completed/rq_scoped_stale_cache_guard_priority2_execplan.md`
