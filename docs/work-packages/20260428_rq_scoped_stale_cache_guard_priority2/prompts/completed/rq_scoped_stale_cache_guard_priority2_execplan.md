# RQ Scoped Stale NoDb Cache Guard Priority 2

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` are kept current as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Priority 2 RQ module-family paths that meet the canonical hydrate-then-mutate
conditions must clear the relevant NoDb cache entry before mutable controller
hydration. Paths not meeting the conditions require explicit disposition.

Execution conforms to:
`docs/standards/rq-scoped-nodb-mutation-cache-guard-standard.md`.

## Progress

- [x] (2026-04-28 17:07 UTC) Prepared package scaffold, active ExecPlan, execution prompt, and tracker entry.
- [x] (2026-04-28 17:07 UTC) Added package to `PROJECT_TRACKER.md` Backlog.
- [x] (2026-04-28 17:12 UTC) Audited candidate modules against the standard.
- [x] (2026-04-28 17:18 UTC) Implemented scoped guards for all listed candidates.
- [x] (2026-04-28 17:19 UTC) Added focused regression tests for every touched module.
- [x] (2026-04-28 17:28 UTC) Ran targeted pytest, docs lint, and `git diff --check`.
- [x] (2026-04-28 17:28 UTC) Updated package lifecycle docs for closure.

## Surprises & Discoveries

- Observation: All seven deferred module families had clear mutable hydration
  boundaries suitable for scoped guard insertion.
  Evidence: audited call sites in `wepp_rq.py`, `swat_rq.py`, `omni_rq.py`,
  `path_ce_rq.py`, `roads_rq.py`, `geneva_rq.py`, and `project_rq_fork.py`.

- Observation: Fork-undisturbify required `new_runid` cache keys, not source
  run keys.
  Evidence: `prepare_fork_run(...)` mutates copied NoDb state in `new_wd`
  during undisturbify.

- Observation: Existing test suites already covered the relevant lock/status/
  enqueue behavior, allowing focused scope/order assertions without broad fixture
  churn.
  Evidence: targeted suites under `tests/rq/` accepted incremental assertions.

## Decision Log

- Decision: Treat this package as standards conformance, not hardening.
  Rationale: the contract is explicitly governed by the scoped NoDb mutation
  cache-guard standard.
  Date/Author: 2026-04-28 / Codex

- Decision: Implement all listed candidates in one pass.
  Rationale: audit confirmed each candidate had clear mutate boundaries and
  testable guard placement.
  Date/Author: 2026-04-28 / Codex

- Decision: Inject a cache-clear collaborator into fork preparation and clear
  using `new_runid`.
  Rationale: copied NoDb files in `new_wd` must be keyed to destination run
  cache entries.
  Date/Author: 2026-04-28 / Codex

## Outcomes & Retrospective

Complete. All Priority 2 candidates were implemented with scoped guards before
mutable hydration, including fork-undisturbify destination-run scopes. Targeted
regression coverage now asserts exact `pup_relpath` scope values and guard
ordering while preserving lock/status/timestamp/enqueue behavior across touched
modules.

Validation summary:
- `tests/rq/test_bootstrap_enable_rq.py` + `tests/rq/test_bootstrap_autocommit_rq.py`: `21 passed`
- `tests/rq/test_omni_rq.py`: `15 passed`
- `tests/rq/test_path_ce_rq.py`: `3 passed`
- `tests/rq/test_roads_rq.py`: `4 passed`
- `tests/rq/test_geneva_rq.py`: `5 passed`
- `tests/rq/test_project_rq_fork.py`: `13 passed`
- package doc lint passed
- `git diff --check` passed

No queue wiring changed; `wctl check-rq-graph` was not required.

## Context and Orientation

This package continues the prior follow-up package that closed Priority 0 and
simple Priority 1 `project_rq.py` paths. The remaining deferred module families
were:

- WEPP orchestration (`wepp_rq.py`)
- SWAT execution (`swat_rq.py`)
- Omni scenario/contrast orchestration (`omni_rq.py`)
- PATH CE orchestration (`path_ce_rq.py`)
- Roads orchestration (`roads_rq.py`)
- Geneva orchestration (`geneva_rq.py`)
- Fork-undisturbify path (`project_rq_fork.py`)

The implemented pattern is:
1. run preconditions/guards already present in the flow,
2. clear scoped NoDb cache using exact `pup_relpath`,
3. hydrate mutable controller and continue existing behavior.

## Plan of Work

1. Audit candidate functions and confirm mutable hydration boundaries.
2. Insert scoped guards with exact `pup_relpath` values.
3. Add focused tests for scope/order and unchanged behavior.
4. Validate with targeted pytest, docs lint, and `git diff --check`.
5. Close package docs and archive the ExecPlan.

## Concrete Steps

Implemented:

1. `wepppy/rq/wepp_rq.py`: guards for
   `bootstrap_enable_rq`, `run_wepp_rq`, `run_wepp_watershed_rq`,
   `prep_wepp_watershed_rq` (`wepp.nodb`).
2. `wepppy/rq/swat_rq.py`: guards for
   `_build_swat_inputs_rq`, `_run_swat_rq`, `run_swat_interchange_rq`
   (`swat.nodb`).
3. `wepppy/rq/omni_rq.py`: guards for
   `run_omni_scenario_rq`, `run_omni_contrast_rq`, `run_omni_scenarios_rq`,
   `run_omni_contrasts_rq`, `delete_omni_contrasts_rq` (`omni.nodb`).
4. `wepppy/rq/path_ce_rq.py`: guards for
   `run_path_cost_effective_rq` (`path_ce.nodb`, `omni.nodb`).
5. `wepppy/rq/roads_rq.py`: guards for
   `run_roads_prepare_rq`, `run_roads_rq` (`roads.nodb`).
6. `wepppy/rq/geneva_rq.py`: guards for
   `run_geneva_prepare_hrus_rq`, `run_geneva_build_frequency_panel_rq`,
   `run_geneva_run_batch_rq` (`geneva.nodb`).
7. `wepppy/rq/project_rq_fork.py`: destination-run guards in
   `prepare_fork_run(..., undisturbify=True)` for
   `ron.nodb`, `disturbed.nodb`, `landuse.nodb`, `soils.nodb`.

## Validation and Acceptance

Acceptance criteria are met:

- every listed Priority 2 candidate has implementation,
- implemented guards are scoped and ordered correctly,
- lock/archive/status/timestamp/enqueue/clone/delete/autocommit/runtime-lock
  behavior remains intact in targeted coverage,
- focused pytest and docs lint passed,
- `git diff --check` passed.

## Idempotence and Recovery

Work is additive. No broad run-wide cache clears were introduced, and no silent
fallback wrappers for cache dependencies were added.

## Artifacts and Notes

- Package docs: `package.md`, `tracker.md`
- ExecPlan: archived under `prompts/completed/`
- Execution prompt retained under `prompts/active/`

## Revision Notes

- 2026-04-28: Initial Priority 2 package ExecPlan prepared from deferred
  module-family list.
- 2026-04-28: Closed with full implementation and validation evidence.
