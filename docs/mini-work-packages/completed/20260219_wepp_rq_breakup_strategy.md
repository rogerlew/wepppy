# ExecPlan: Break Up `wepppy/rq/wepp_rq.py` Into Focused Modules

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept current as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this work, `wepppy/rq/wepp_rq.py` is no longer a single monolithic orchestration + utility file. The DSS helpers and queue orchestration graph wiring are moved into focused sibling modules, while `wepp_rq.py` keeps stable public entrypoints.

The user-visible proof is straightforward: existing WEPP RQ tests still pass, queue dependency artifacts stay in sync with `wctl check-rq-graph`, and the codebase has smaller files with clearer ownership boundaries.

## Progress

- [x] (2026-02-19 23:58Z) Established ad hoc mini-work-package ExecPlan and aligned scope with the requested breakup strategy.
- [x] (2026-02-19 23:58Z) Extracted DSS helper logic from `wepppy/rq/wepp_rq.py` into `wepppy/rq/wepp_rq_dss.py` and added `wepppy/rq/wepp_rq_dss.pyi`.
- [x] (2026-02-19 23:58Z) Extracted queue wiring/orchestration into `wepppy/rq/wepp_rq_pipeline.py` and added `wepppy/rq/wepp_rq_pipeline.pyi`.
- [x] (2026-02-19 23:58Z) Refactored `run_wepp_rq`, `run_wepp_noprep_rq`, `run_wepp_watershed_rq`, and `run_wepp_watershed_noprep_rq` in `wepppy/rq/wepp_rq.py` to delegate to the pipeline module while preserving runtime contracts.
- [x] (2026-02-19 23:58Z) Added unit coverage for DSS helper logic in `tests/rq/test_wepp_rq_dss_helpers.py` and pipeline branch behavior in `tests/rq/test_wepp_rq_pipeline.py`.
- [x] (2026-02-19 23:58Z) Updated dependency-graph tooling to recognize `_enqueue(...)` wrapper usage in the pipeline module and added regression coverage in `tests/rq/test_dependency_graph_tools.py`.
- [x] (2026-02-19 23:58Z) Regenerated RQ graph artifacts (`wepppy/rq/job-dependency-graph.static.json`, `wepppy/rq/job-dependencies-catalog.md`) and verified drift checks pass.
- [x] (2026-02-20 00:32Z) Closed review findings for nested wrapper call extraction by confirming `_Collector.visit_Call` coverage with callsite-position dedupe and regression tests for `append(_enqueue(...))` plus `return _enqueue(...)`.
- [x] (2026-02-20 00:32Z) Revalidated generated graph completeness for WEPP pipelines (`jobs:6` `_log_complete_rq` edges present in all pipeline orchestrators) and reran `wctl check-rq-graph`.
- [x] (2026-02-20 00:50Z) Closed follow-up review finding for qualified wrapper syntax by extending wrapper detection to include attribute-style calls (for example `_pipeline.enqueue_log_complete(...)`) in `tools/extract_rq_dependency_graph.py`.
- [x] (2026-02-20 00:50Z) Added regression coverage for qualified wrapper calls in `tests/rq/test_dependency_graph_tools.py` and revalidated artifacts/tests (`wctl check-rq-graph`, `wctl run-pytest tests/rq --maxfail=1`).

## Surprises & Discoveries

- (2026-02-19 23:58Z) Observation: Moving queue calls behind helper wrappers initially caused static dependency graph under-reporting for WEPP pipelines.
  Evidence: `wctl check-rq-graph` reported drift and the generated static graph dropped WEPP pipeline edges until extractor support for `_enqueue(...)` wrappers was added.

- (2026-02-19 23:58Z) Observation: The extractor needed to resolve dependency refs from call expressions (not only named job vars) once `_enqueue(...)` was introduced in list-building patterns.
  Evidence: Generated dependencies initially appeared as raw expression strings (for example, full `_enqueue(...)` expressions) until `_collect_dep_refs` was updated to normalize enqueue-call targets.

- (2026-02-20 00:32Z) Observation: wrapper coverage cannot rely on assignment/standalone expression handlers alone because orchestration patterns frequently embed wrapper calls in other call arguments and `return` expressions.
  Evidence: WEPP pipeline `_enqueue(...)` calls at `wepppy/rq/wepp_rq_pipeline.py:80`, `wepppy/rq/wepp_rq_pipeline.py:374`, and `wepppy/rq/wepp_rq_pipeline.py:45` only appear when traversal captures nested `ast.Call` nodes.

- (2026-02-20 00:50Z) Observation: wrapper-name matching by `ast.Name` alone misses refactored callsites that invoke wrappers through module aliases.
  Evidence: `_pipeline.enqueue_log_complete(...)` callsites in `wepppy/rq/wepp_rq.py` were excluded until wrapper detection also matched `ast.Attribute` function names.

## Decision Log

- Decision: Keep `wepppy/rq/wepp_rq.py` as the stable public API surface and delegate internals to extracted modules.
  Rationale: Route handlers and existing tests import `wepppy.rq.wepp_rq` directly; preserving that surface minimizes migration risk.
  Date/Author: 2026-02-19 23:58Z / Codex

- Decision: Split by concern first (DSS helpers and pipeline wiring) instead of attempting a full stage-wrapper module in the same pass.
  Rationale: This captures most of the complexity reduction while keeping behavior-preserving refactor risk manageable in one session.
  Date/Author: 2026-02-19 23:58Z / Codex

- Decision: Extend dependency-graph extraction for `_enqueue(...)` wrappers instead of rolling back helper-based queue wiring.
  Rationale: The wrapper style significantly reduces orchestration duplication; extractor support preserves observability contracts without undoing the refactor.
  Date/Author: 2026-02-19 23:58Z / Codex

## Outcomes & Retrospective

- (2026-02-19 23:58Z) Outcome: The requested breakup strategy is implemented for the heaviest `wepp_rq.py` concerns: DSS helpers and queue wiring moved to dedicated modules with companion stubs.
- (2026-02-19 23:58Z) Outcome: Existing targeted WEPP RQ tests and new regression tests pass, and `wctl check-rq-graph` is green after artifact refresh.
- (2026-02-19 23:58Z) Retrospective: The largest remaining monolithic area is stage implementation wrappers (`_prep_*`, `_post_*`) still in `wepp_rq.py`; this can be a follow-on extraction now that orchestration and DSS concerns are separated and tested.
- (2026-02-20 00:32Z) Outcome: Post-review validation confirms static graph extraction now includes nested/return wrapper callsites and retains expected WEPP final-stage (`jobs:6`) edges in generated artifacts.
- (2026-02-20 00:50Z) Outcome: Static graph extraction now includes qualified wrapper callsites; regenerated artifacts returned to 120 extracted edges with all expected WEPP pipeline and wrapper completion edges.

## Context and Orientation

`wepppy/rq/wepp_rq.py` historically mixed multiple responsibilities:

1. public RQ entrypoints (`run_wepp_rq` variants),
2. queue graph wiring and dependency sequencing,
3. DSS export utility logic,
4. many stage-level execution wrappers.

This change focuses on splitting responsibilities 2 and 3 into standalone modules while preserving responsibility 1 as a stable import surface. The new modules are:

- `wepppy/rq/wepp_rq_dss.py`: DSS export helper internals.
- `wepppy/rq/wepp_rq_pipeline.py`: queue enqueue/dependency/meta orchestration.

The dependency graph toolchain (`tools/extract_rq_dependency_graph.py` and rendered artifacts) is part of the repository contract for RQ wiring changes and must remain accurate.

## Plan of Work

The work is executed in five passes. First, extract DSS helpers and wire `wepp_rq.py` through module aliases to preserve test monkeypatch behavior. Second, extract queue orchestration into a pipeline module and convert the four large public orchestrators into thin wrappers. Third, add targeted unit tests for the new DSS and pipeline modules. Fourth, update dependency graph extraction to keep wrapper-based enqueue calls visible to tooling. Fifth, regenerate and validate graph artifacts plus the affected test suites.

## Concrete Steps

Run all commands from `/workdir/wepppy`.

1. Run focused WEPP RQ test suites and new regression tests:

       wctl run-pytest tests/rq/test_wepp_rq_pipeline.py tests/rq/test_bootstrap_autocommit_rq.py tests/rq/test_wepp_rq_nodir.py tests/rq/test_wepp_rq_dss_helpers.py tests/rq/test_dependency_graph_tools.py

   Executed: passed (`36 passed`).

2. Refresh dependency graph artifacts and validate drift:

       python tools/check_rq_dependency_graph.py --write
       wctl check-rq-graph

   Executed: static graph and catalog were regenerated and `wctl check-rq-graph` returned `RQ dependency graph artifacts are up to date`.

## Validation and Acceptance

Acceptance criteria are:

1. WEPP RQ orchestrator entrypoints still enqueue expected completion jobs and metadata wiring (validated by `tests/rq/test_bootstrap_autocommit_rq.py` plus pipeline tests).
2. Newly extracted helper modules have direct unit coverage (validated by `tests/rq/test_wepp_rq_dss_helpers.py` and `tests/rq/test_wepp_rq_pipeline.py`).
3. RQ graph contracts remain consistent after queue wiring changes (validated by `wctl check-rq-graph` and `tests/rq/test_dependency_graph_tools.py`).

## Idempotence and Recovery

The graph tooling commands are idempotent. If drift is reported after additional edits, rerun:

    python tools/check_rq_dependency_graph.py --write
    wctl check-rq-graph

If pipeline extraction introduces regressions, the safest rollback path is to revert only `wepppy/rq/wepp_rq_pipeline.py` integration in `wepppy/rq/wepp_rq.py` while leaving DSS extraction intact.

## Artifacts and Notes

Primary changed implementation files:

- `wepppy/rq/wepp_rq.py`
- `wepppy/rq/wepp_rq_dss.py`
- `wepppy/rq/wepp_rq_pipeline.py`
- `tools/extract_rq_dependency_graph.py`

Primary changed validation artifacts:

- `wepppy/rq/job-dependency-graph.static.json`
- `wepppy/rq/job-dependencies-catalog.md`

Primary new tests:

- `tests/rq/test_wepp_rq_dss_helpers.py`
- `tests/rq/test_wepp_rq_pipeline.py`
- additional extractor wrapper case in `tests/rq/test_dependency_graph_tools.py`

## Interfaces and Dependencies

`wepppy/rq/wepp_rq.py` remains the public entrypoint module. The extracted modules are internal siblings and keep stable function signatures used by wrappers:

- `wepppy/rq/wepp_rq_dss.py` exports `_cleanup_dss_export_dir`, `_copy_dss_readme`, `_resolve_downstream_channel_ids`, `_extract_channel_topaz_id`, `_write_dss_channel_geojson`.
- `wepppy/rq/wepp_rq_pipeline.py` exports enqueue orchestration helpers used by the four public run entrypoints.

`tools/extract_rq_dependency_graph.py` now supports `_enqueue(...)` wrappers and still supports direct `q.enqueue_call(...)` patterns.

Revision Note (2026-02-20 00:50Z, Codex): Authored this mini-work-package as an ad hoc ExecPlan, completed the WEPP RQ breakup strategy, and recorded two post-review dependency-graph hardening cycles (nested wrapper calls and qualified wrapper calls).
