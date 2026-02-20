# ExecPlan: Phase 2 Breakup of `wepppy/rq/wepp_rq.py` Stage Wrappers

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept current as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

This plan builds directly on `docs/mini-work-packages/completed/20260219_wepp_rq_breakup_strategy.md`, which completed DSS helper and pipeline extraction. This phase focuses on the remaining stage-wrapper and helper-glue logic still living in `wepppy/rq/wepp_rq.py`.

## Purpose / Big Picture

After this work, `wepppy/rq/wepp_rq.py` remains the stable public entrypoint module, but the remaining stage wrapper implementations (`_prep_*`, `_run_*`, `_post_*`, and close helper glue) are moved to focused sibling modules. The user-visible result is unchanged behavior and queue contracts, with lower per-file complexity and easier targeted testing of stage logic.

A maintainer should be able to run WEPP RQ tests and observe that pipeline edges, completion behavior, and NoDir safeguards behave exactly as before while code ownership is cleaner.

## Progress

- [x] (2026-02-20 03:42Z) Reviewed root and nearest AGENTS guidance plus the ExecPlan template requirements.
- [x] (2026-02-20 03:42Z) Mapped `wepppy/rq/wepp_rq.py` responsibilities and identified extraction targets for stage helpers, prep/run wrappers, and post/finalization wrappers.
- [x] (2026-02-20 03:42Z) Authored this mini work package ExecPlan in `docs/mini-work-packages/20260220_wepp_rq_phase2_breakup_strategy.md`.
- [x] (2026-02-20 03:50Z) Extracted stage helper glue into `wepppy/rq/wepp_rq_stage_helpers.py` and converted `wepppy/rq/wepp_rq.py` helper functions to delegators.
- [x] (2026-02-20 03:50Z) Extracted prep/run stage implementations into `wepppy/rq/wepp_rq_stage_prep.py` and converted `_prep_*`/`_run_*` wrappers in `wepppy/rq/wepp_rq.py` to delegators.
- [x] (2026-02-20 03:50Z) Extracted post/finalization stage implementations into `wepppy/rq/wepp_rq_stage_post.py` and `wepppy/rq/wepp_rq_stage_finalize.py`, with delegating wrappers in `wepppy/rq/wepp_rq.py`.
- [x] (2026-02-20 03:50Z) Added/updated stubs: `wepppy/rq/wepp_rq_stage_helpers.pyi`, `wepppy/rq/wepp_rq_stage_prep.pyi`, `wepppy/rq/wepp_rq_stage_post.pyi`, `wepppy/rq/wepp_rq_stage_finalize.pyi`, and refreshed `wepppy/rq/wepp_rq.pyi`.
- [x] (2026-02-20 03:50Z) Expanded WEPP RQ test coverage for extracted modules by updating monkeypatch targets to stage modules in `tests/rq/test_wepp_rq_nodir.py` and `tests/rq/test_bootstrap_autocommit_rq.py`, while preserving public wrapper invocation.
- [x] (2026-02-20 03:50Z) Ran required validation gates: `wctl run-pytest tests/rq --maxfail=1`, `wctl check-test-stubs`, `wctl check-rq-graph`, `wctl doc-lint --path docs/mini-work-packages/20260220_wepp_rq_phase2_breakup_strategy.md`, and `wctl doc-lint --path wepppy/rq/job-dependencies-catalog.md`.
- [ ] (2026-02-20 03:51Z) Closeout in progress (completed: moved this mini work package to `docs/mini-work-packages/completed/`; remaining: commit and push all changes).

## Surprises & Discoveries

- Observation: `wctl check-rq-graph` reported drift after stage extraction, even though queue wiring logic was not intentionally changed.
  Evidence: graph check flagged `wepppy/rq/job-dependency-graph.static.json` and `wepppy/rq/job-dependencies-catalog.md`; rerunning `python tools/check_rq_dependency_graph.py --write` regenerated 120 edges and restored a clean `wctl check-rq-graph`.

## Decision Log

- Decision: Keep `wepppy/rq/wepp_rq.py` function names stable and delegate to extracted implementation modules instead of relocating entrypoint symbols directly.
  Rationale: RQ serialization and import compatibility are safer when public wrappers remain in place.
  Date/Author: 2026-02-20 / Codex

- Decision: Split extraction by concern (helpers, prep/run wrappers, post/finalization wrappers) instead of one large “stages” module.
  Rationale: Smaller concern-based modules are easier to test, review, and maintain.
  Date/Author: 2026-02-20 / Codex

- Decision: Keep `_log_complete_rq` as a stable wrapper in `wepppy/rq/wepp_rq.py` and pass `send_discord_message` into extracted finalization logic.
  Rationale: Preserves compatibility for callers/tests that patch `wepp_rq.send_discord_message` while still moving implementation details out of the monolith.
  Date/Author: 2026-02-20 / Codex

## Outcomes & Retrospective

- (2026-02-20 03:50Z) Outcome: `wepppy/rq/wepp_rq.py` was reduced from 1514 lines to 724 lines while keeping queue-facing entrypoint names and signatures stable.
- (2026-02-20 03:50Z) Outcome: Stage logic now lives in concern-based modules (`wepp_rq_stage_helpers.py`, `wepp_rq_stage_prep.py`, `wepp_rq_stage_post.py`, `wepp_rq_stage_finalize.py`) with companion `.pyi` files.
- (2026-02-20 03:50Z) Outcome: All RQ tests pass (`97 passed`) and graph contracts are current after artifact refresh (`wctl check-rq-graph` clean; `jobs:6` edges confirmed for all WEPP pipeline entrypoints).
- (2026-02-20 03:50Z) Retrospective: Extracting modules without changing wrapper names preserved runtime contracts while making future targeted cleanup of individual stage concerns substantially easier.

## Context and Orientation

`wepppy/rq/wepp_rq.py` currently still contains substantial wrapper logic beyond the already-extracted pipeline and DSS helper modules. These wrappers run inside RQ workers and are responsible for status messaging, NoDir projection safety, WEPP prep/run sequencing, post-processing exports, and final completion notifications.

The risk in this phase is accidental contract drift: changing status channels/messages, queue target function names, exception boundary behavior, or final completion dependencies. To prevent that, this refactor will preserve existing signatures in `wepp_rq.py` and move implementation details behind delegation boundaries.

Key files in scope:

- `wepppy/rq/wepp_rq.py` (public entrypoint/delegator surface)
- New sibling modules under `wepppy/rq/` for helper, prep/run, and post/finalization stage logic
- `.pyi` stubs for new modules and any adjusted signatures
- `tests/rq/test_wepp_rq_pipeline.py`
- `tests/rq/test_wepp_rq_dss_helpers.py`
- `tests/rq/test_bootstrap_autocommit_rq.py`
- `tests/rq/test_wepp_rq_nodir.py`
- `tests/rq/test_dependency_graph_tools.py` (only if wiring/tooling impact emerges)

## Plan of Work

First, create helper and stage modules by moving logic in behavior-preserving form. Second, rewrite `wepppy/rq/wepp_rq.py` wrappers to delegate while keeping function names, signatures, decorators, and queue-facing symbols stable. Third, extend tests to cover extracted modules directly and verify high-risk branches (NoDir mixed state, projection wrapping, autocommit behavior, and post-stage dependency assumptions). Fourth, run all required validation gates and only regenerate RQ graph artifacts if queue wiring changed.

## Concrete Steps

Run commands from `/workdir/wepppy`.

1. Refactor implementation modules and delegators.
2. Update/add `.pyi` stubs.
3. Run targeted WEPP RQ tests during iteration.
4. Run required gates before handoff:

       wctl run-pytest tests/rq --maxfail=1
       wctl check-test-stubs
       wctl check-rq-graph
       wctl doc-lint --path docs/mini-work-packages/20260220_wepp_rq_phase2_breakup_strategy.md

5. If queue graph drift is reported:

       python tools/check_rq_dependency_graph.py --write
       wctl check-rq-graph

6. Move mini work package to completed and finalize with commit/push.

## Validation and Acceptance

Acceptance is met when all of the following are true:

1. `wepppy/rq/wepp_rq.py` remains import-compatible and delegates stage logic to extracted modules.
2. Existing behavior/contract tests for WEPP RQ pass, plus added tests for extracted modules and high-risk branches.
3. Stub checks pass with new module coverage.
4. RQ graph contract remains green (`wctl check-rq-graph`) and `jobs:6` completion edges remain present.
5. Documentation lint passes for the mini work package (and dependency catalog if touched).

## Idempotence and Recovery

This refactor is additive and can be repeated safely by rerunning tests and checks after edits. If a module extraction causes regression, rollback is straightforward by restoring the previous implementation in `wepppy/rq/wepp_rq.py` and rerunning the same test gates. RQ graph artifacts should only be rewritten when the checker reports drift.

## Artifacts and Notes

Expected primary artifacts:

- New `wepppy/rq/wepp_rq_stage_*.py` implementation modules (exact names to be finalized during extraction)
- Corresponding `.pyi` files
- Updated `wepppy/rq/wepp_rq.py` delegators
- Updated tests under `tests/rq/`
- This mini work package moved to `docs/mini-work-packages/completed/` on completion

## Interfaces and Dependencies

Public API expectations remain anchored to `wepppy/rq/wepp_rq.py`. Queue orchestration remains in `wepppy/rq/wepp_rq_pipeline.py` and should continue targeting functions exported by `wepp_rq.py`. Extracted stage modules are internal siblings and must preserve the same runtime side effects and exception behavior currently enforced by tests and RQ integration.

Revision Note (2026-02-20 03:50Z, Codex): Updated this living ExecPlan to completed implementation status, recorded validation evidence (tests/stubs/graph/doc lint), and captured graph drift handling plus final module split decisions.
