# ExecPlan: Break Up `wepppy/rq/culvert_rq.py` Into Focused Modules

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept current as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this work, `wepppy/rq/culvert_rq.py` remains the stable public API for culvert RQ entrypoints, but the largest internal responsibility clusters are split into focused sibling modules. Queue wiring, payload/config helpers, and manifest/report helpers become independently testable units while preserving existing runtime behavior and error contracts.

The user-visible proof is that culvert queue orchestration still enqueues the same tasks with the same metadata semantics, helper behavior is covered by new deterministic unit tests, and RQ dependency graph artifacts remain in sync (or are regenerated if enqueue edge/source metadata changes).

## Progress

- [x] (2026-02-20 01:18Z) Completed discovery: reviewed root/test AGENTS guidance, loaded ExecPlan template, inspected `culvert_rq.py` seams, and identified existing culvert/RQ test coverage.
- [x] (2026-02-20 01:18Z) Authored active mini work package plan at `docs/mini-work-packages/20260220_culvert_rq_breakup_strategy.md`.
- [x] (2026-02-20 01:24Z) Extracted queue wiring from `run_culvert_batch_rq` into `wepppy/rq/culvert_rq_pipeline.py` while preserving job-meta keys, staged metadata, and dependency semantics.
- [x] (2026-02-20 01:24Z) Extracted shared payload/config/watershed validation utilities into `wepppy/rq/culvert_rq_helpers.py`.
- [x] (2026-02-20 01:24Z) Extracted manifest/report helper utilities into `wepppy/rq/culvert_rq_manifest.py`.
- [x] (2026-02-20 01:24Z) Added `.pyi` stubs for new culvert modules and aligned `wepppy/rq/culvert_rq.pyi` with the public surface (including `run_culvert_batch_finalize_rq`).
- [x] (2026-02-20 01:25Z) Added focused unit tests under `tests/rq/` for extracted pipeline/helpers/manifest modules and dependency-graph regression coverage.
- [x] (2026-02-20 01:26Z) Re-ran required gates: `tests/rq/test_dependency_graph_tools.py`, `tests/rq --maxfail=1`, `check-rq-graph`, `check-test-stubs`, and doc-lint on touched docs.
- [x] (2026-02-20 01:26Z) Detected graph drift after wiring changes, regenerated `wepppy/rq/job-dependency-graph.static.json` plus `wepppy/rq/job-dependencies-catalog.md`, re-linted catalog docs, and re-verified `wctl check-rq-graph`.
- [x] (2026-02-20 01:28Z) Finalized this plan with timestamped outcomes, moved it to `docs/mini-work-packages/completed/`, committed changes (`964de73fe`), and pushed to `origin/master`.

## Surprises & Discoveries

- (2026-02-20 01:18Z) Observation: Existing culvert tests heavily monkeypatch internal names on `wepppy.rq.culvert_rq`, so compatibility aliases in the public module are required even when implementation moves to sibling modules.
  Evidence: `tests/culverts/test_culvert_batch_rq.py` and `tests/culverts/test_culvert_orchestration.py` patch symbols such as `_generate_batch_topo`, `_generate_masked_stream_junctions`, and `_ensure_batch_landuse_soils` directly on `culvert_rq`.

- (2026-02-20 01:26Z) Observation: Moving enqueue calls behind `culvert_rq_pipeline._enqueue(...)` changed static graph source locations and required artifact refresh.
  Evidence: `wctl check-rq-graph` reported drift in both `wepppy/rq/job-dependency-graph.static.json` and `wepppy/rq/job-dependencies-catalog.md` until regeneration.

## Decision Log

- Decision: Keep `wepppy/rq/culvert_rq.py` as the stable import/entrypoint surface and delegate extracted internals through module aliases.
  Rationale: Route handlers and tests import `wepppy.rq.culvert_rq` directly; preserving that surface minimizes migration and compatibility risk.
  Date/Author: 2026-02-20 01:18Z / Codex

- Decision: Prioritize extraction of queue wiring plus helper/report clusters before attempting deeper run-execution decomposition.
  Rationale: This delivers immediate maintainability and testability gains with lower behavioral risk than splitting the large `_process_culvert_run` execution path in the same pass.
  Date/Author: 2026-02-20 01:18Z / Codex

- Decision: Keep topology/raster mutation helpers in `culvert_rq.py` for this pass and focus extraction on queue/helper/report seams.
  Rationale: Existing culvert integration tests monkeypatch raster helper symbols directly on `culvert_rq`; preserving that locality reduced regression risk while still achieving substantial modularization.
  Date/Author: 2026-02-20 01:24Z / Codex

## Outcomes & Retrospective

- (2026-02-20 01:26Z) Outcome: `culvert_rq.py` now delegates queue orchestration, payload/config helper logic, and manifest/report helpers to focused sibling modules while keeping public entrypoints stable.
- (2026-02-20 01:26Z) Outcome: New deterministic unit suites (`tests/rq/test_culvert_rq_pipeline.py`, `tests/rq/test_culvert_rq_helpers.py`, `tests/rq/test_culvert_rq_manifest.py`) provide direct coverage for extracted logic and high-risk branches.
- (2026-02-20 01:26Z) Outcome: Required quality gates are green, RQ graph artifacts were regenerated after drift, and additional culvert integration regressions passed.
- (2026-02-20 01:28Z) Outcome: Changes were committed and pushed (`964de73fe`) after moving this plan to the completed mini-work-package directory.
- (2026-02-20 01:26Z) Retrospective: The remaining large surface in `culvert_rq.py` is the topology + run execution path; it can be split in a follow-on once monkeypatch contracts are narrowed or migrated.

## Context and Orientation

`wepppy/rq/culvert_rq.py` currently combines several concerns in one file:

1. public queue entrypoints (`run_culvert_batch_rq`, `run_culvert_run_rq`, finalize wrapper),
2. queue dependency wiring and job-meta persistence for batch enqueue flow,
3. payload/config parsing and watershed validation helper logic,
4. manifest/report generation and run-summary artifact writing.

This plan separates concerns 2-4 into focused modules while keeping concern 1 in `culvert_rq.py`. The expected new files are:

- `wepppy/rq/culvert_rq_pipeline.py` for enqueue/dependency/meta orchestration.
- `wepppy/rq/culvert_rq_helpers.py` for payload/config/watershed-area helper logic.
- `wepppy/rq/culvert_rq_manifest.py` for manifest/report helper functions.

Queue wiring changes can affect static dependency extraction. The repository contract requires keeping `wepppy/rq/job-dependency-graph.static.json` and `wepppy/rq/job-dependencies-catalog.md` aligned with source code.

## Plan of Work

Implementation proceeds in six passes. First, add the new helper modules with behavior-preserving function moves and keep `culvert_rq.py` calling through aliases. Second, extract batch queue enqueue wiring to a pipeline helper and refactor `run_culvert_batch_rq` to delegate only the enqueue section. Third, add/update `.pyi` stubs for new modules plus any public-surface adjustments in `culvert_rq.pyi`. Fourth, add deterministic unit tests for extracted helpers and pipeline wiring. Fifth, run requested validation gates and refresh dependency graph artifacts if drift is detected. Sixth, update and close this ExecPlan, then move it to `completed/` with final notes.

## Concrete Steps

Run all commands from `/workdir/wepppy`.

1. Implement extraction and stubs:

       # edit/add:
       # - wepppy/rq/culvert_rq.py
       # - wepppy/rq/culvert_rq_pipeline.py
       # - wepppy/rq/culvert_rq_helpers.py
       # - wepppy/rq/culvert_rq_manifest.py
       # - corresponding .pyi files

2. Add focused tests:

       # add/update:
       # - tests/rq/test_culvert_rq_pipeline.py
       # - tests/rq/test_culvert_rq_helpers.py
       # - tests/rq/test_dependency_graph_tools.py (if wrapper shape regression coverage is needed)

3. Run required validation gates:

       wctl run-pytest tests/rq/test_dependency_graph_tools.py
       wctl run-pytest tests/rq --maxfail=1
       wctl check-rq-graph
       wctl check-test-stubs
       wctl doc-lint --path docs/mini-work-packages/20260220_culvert_rq_breakup_strategy.md
       wctl doc-lint --path wepppy/rq/job-dependencies-catalog.md

   Executed:
   - `wctl run-pytest tests/rq/test_dependency_graph_tools.py` -> `14 passed`
   - `wctl run-pytest tests/rq --maxfail=1` -> `89 passed`
   - `wctl check-test-stubs` -> `All stubs are complete`
   - `wctl doc-lint --path docs/mini-work-packages/20260220_culvert_rq_breakup_strategy.md` -> `0 errors`
   - `wctl doc-lint --path wepppy/rq/job-dependencies-catalog.md` -> `0 errors`

4. If graph drift appears, regenerate and re-check:

       python tools/check_rq_dependency_graph.py --write
       wctl check-rq-graph

   Executed:
   - first `wctl check-rq-graph` detected drift
   - `python tools/check_rq_dependency_graph.py --write` regenerated artifacts (`120 edges`)
   - follow-up `wctl check-rq-graph` confirmed artifacts are up to date

5. Additional regression confidence (not required but executed):

       wctl run-pytest tests/culverts/test_culvert_batch_rq.py tests/culverts/test_culvert_orchestration.py --maxfail=1

   Executed: `8 passed`

## Validation and Acceptance

Acceptance criteria are:

1. `wepppy/rq/culvert_rq.py` preserves public entrypoint behavior and signatures while delegating extracted internals.
2. New helper modules are covered by focused unit tests that exercise high-risk branches and contract behavior.
3. Queue-wiring semantics remain intact: staged job meta keys, dependency ordering, and queued task targets are unchanged in behavior.
4. If queue wiring source/shape changes static graph output, artifacts are regenerated and `wctl check-rq-graph` is green.
5. Requested gates complete without failures, and docs lint passes for the mini work package (and catalog if touched).

## Idempotence and Recovery

The refactor is additive and can be rerun safely by reapplying module extraction and rerunning tests. Graph artifact generation (`python tools/check_rq_dependency_graph.py --write`) is idempotent. If queue extraction introduces regressions, a safe recovery path is to revert only the pipeline delegation in `run_culvert_batch_rq` while keeping helper-module extractions and tests.

## Artifacts and Notes

Expected primary implementation artifacts:

- `wepppy/rq/culvert_rq.py`
- `wepppy/rq/culvert_rq_pipeline.py`
- `wepppy/rq/culvert_rq_helpers.py`
- `wepppy/rq/culvert_rq_manifest.py`
- `wepppy/rq/culvert_rq.pyi` and new sibling `.pyi` files

Expected validation/documentation artifacts (if wiring drift occurs):

- `wepppy/rq/job-dependency-graph.static.json`
- `wepppy/rq/job-dependencies-catalog.md`

Expected new/updated tests:

- `tests/rq/test_culvert_rq_pipeline.py`
- `tests/rq/test_culvert_rq_helpers.py`
- optionally `tests/rq/test_dependency_graph_tools.py` for wrapper-shape regressions

## Interfaces and Dependencies

Public interface remains in `wepppy/rq/culvert_rq.py`:

- `run_culvert_batch_rq(culvert_batch_uuid: str) -> Job`
- `run_culvert_run_rq(runid: str, culvert_batch_uuid: str, run_id: str) -> str`
- `run_culvert_batch_finalize_rq(culvert_batch_uuid: str) -> dict[str, Any]`
- `CulvertBatchError`, `TIMEOUT`

New internal modules will expose helper functions consumed by `culvert_rq.py`, and companion stubs will encode signatures for static checks. Queue orchestration should use explicit enqueue metadata keys that keep dependency graph extraction observable.

Revision Note (2026-02-20 01:28Z, Codex): Updated closeout status to completed with commit/push evidence after publishing commit `964de73fe`.
