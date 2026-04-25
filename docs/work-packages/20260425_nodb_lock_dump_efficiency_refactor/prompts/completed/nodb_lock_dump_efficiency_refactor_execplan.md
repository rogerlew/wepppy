# NoDb Lock/Dump Efficiency Refactor for RQ Engine Mutation Paths

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

RQ-engine currently has several multi-field mutation paths that perform sequential `@nodb_setter` writes. Because each setter opens `with self.locked()` and persists on exit, one request may trigger many lock/dump cycles. After this change, the highest-impact and secondary rq-engine mutation paths will apply grouped updates inside a single lock context per controller mutation sequence, with behavior and response contracts unchanged.

A maintainer should be able to run the existing rq-engine tests and see no contract regressions, while code inspection confirms grouped writes in targeted paths.

## Progress

- [x] (2026-04-25 19:38 UTC) Package and ExecPlan scaffolding created with locked scope (rq-engine only; legacy Flask excluded).
- [x] (2026-04-25 20:28 UTC) Design and implement single-lock helper flow for `apply_wepp_run_payload` soils/watershed writes.
- [x] (2026-04-25 20:47 UTC) Design and implement single-lock helper flow for `_apply_watershed_updates` in `watershed_routes.py`.
- [x] (2026-04-25 21:08 UTC) Design and implement single-lock helper flow for `build_landuse` disturbed toggles and `set-landuse-mode` dual update.
- [x] (2026-04-25 21:28 UTC) Implement secondary helper flow for batch-runner `sbs_map` + `sbs_map_metadata` updates.
- [x] (2026-04-25 21:54 UTC) Implement secondary helper flow for WEPP job hint persistence (`job_id` + `job_key`) in rq-engine routes.
- [x] (2026-04-25 21:54 UTC) Add/update regression tests for helper behavior, payload parity, and lock/dump efficiency expectations.
- [x] (2026-04-25 21:55 UTC) Update package/tracker/docs with outcomes and closure evidence.

## Surprises & Discoveries

- Observation: `_parse_int`/`_parse_float` helper emptiness checks using membership against `(None, "", False)` can incorrectly reject valid numeric zero because `0 == False`.
  Evidence: Milestone 1 review found `0`/`0.0` regression; fixed and covered by targeted tests in `test_rq_engine_wepp_routes.py`.

- Observation: Grouped single-lock helpers reduce lock/dump churn inside a controller but do not provide cross-controller transaction atomicity.
  Evidence: Late-stage failure after one grouped helper persists can still leave partial state (accepted as residual architecture risk for this package scope).

## Decision Log

- Decision: Keep legacy Flask routes out of scope.
  Rationale: Operator direction to prioritize ROI and avoid low-value legacy churn.
  Date/Author: 2026-04-25 / Codex.

- Decision: Use facade/controller helper methods for grouped writes rather than expanding route-level direct underscore assignment patterns.
  Rationale: Preserve existing validation/invariant boundaries while eliminating lock/dump churn.
  Date/Author: 2026-04-25 / Codex.

- Decision: Keep cross-controller failure-atomicity redesign out of scope for this package and record as residual risk.
  Rationale: This package is constrained to lock/dump efficiency orchestration and behavior parity; broader transaction semantics need dedicated design work.
  Date/Author: 2026-04-25 / Codex.

## Outcomes & Retrospective

- Completed all scoped highest-impact and secondary backlog items in required order with per-milestone review triads and remediation closure for all Medium findings.
- Final scoped validation passed:
  - `wctl run-pytest ...` across 10 targeted suites (`198 passed`).
  - Milestone 5 closure reruns (`80 passed`) after QA-driven remediation.
- `wctl check-rq-graph` was executed and reported existing drift in graph/catalog artifacts; no queue-wiring edits were made in this package.
- Scope stayed strict (rq-engine + required NoDb helpers only; no legacy Flask route edits).
- Residual risks recorded:
  - cross-controller failure-atomicity remains architecture-level follow-up.
  - post-enqueue hint-persist helper currently catches `RuntimeError` only (low residual risk).

## Context and Orientation

`@nodb_setter` in `wepppy/nodb/base.py` wraps each setter in `with self.locked()`. The `locked()` context persists state (`dump_and_unlock`) on successful exit. This means multiple sequential setter calls in one route/payload path cause multiple lock acquisitions and persistence cycles.

Target highest-impact call sites:
- `wepppy/microservices/rq_engine/wepp_run_payload.py` (`apply_wepp_run_payload` soils/watershed multi-field writes).
- `wepppy/microservices/rq_engine/watershed_routes.py` (`_apply_watershed_updates`).
- `wepppy/microservices/rq_engine/landuse_routes.py` (`build_landuse` disturbed burn flags and `set-landuse-mode` dual field update).

Target secondary call sites:
- `wepppy/microservices/rq_engine/upload_batch_runner_routes.py` (`sbs_map` + `sbs_map_metadata`).
- `wepppy/microservices/rq_engine/wepp_routes.py` and `wepppy/microservices/rq_engine/bootstrap_routes.py` (`job_id` + `job_key`).

Out of scope:
- `wepppy/weppcloud/routes/nodb_api/**` legacy Flask routes.

## Plan of Work

Milestone 1 focuses on highest-impact paths by adding explicit grouped-apply helper methods on the relevant controllers (or tightly-scoped helper utilities) that perform all validated field updates inside one lock context. Route/payload code will call these helpers rather than issuing N sequential setters.

Milestone 2 applies the same pattern to secondary paths where two-field updates currently run as two independent setter lock cycles.

Milestone 3 adds/extends tests to prove unchanged external behavior and ensure grouped updates are used. Where direct lock-count assertions are brittle, tests will assert helper call boundaries and resulting state parity for equivalent payloads.

Milestone 4 completes documentation and package closure artifacts.

## Concrete Steps

From `/home/workdir/wepppy`:

1. Implement highest-impact helper methods and call-site refactors.
2. Implement secondary helper methods and call-site refactors.
3. Add/update targeted tests under `tests/microservices/` and `tests/nodb/` as needed.
4. Run targeted validations:
   - `wctl run-pytest tests/microservices --maxfail=1`
   - `wctl run-pytest tests/nodb --maxfail=1`
   - `wctl check-rq-graph` (only if queue wiring is touched)
5. Run docs lint for package files:
   - `wctl doc-lint --path docs/work-packages/20260425_nodb_lock_dump_efficiency_refactor/package.md --path docs/work-packages/20260425_nodb_lock_dump_efficiency_refactor/tracker.md --path docs/work-packages/20260425_nodb_lock_dump_efficiency_refactor/prompts/completed/nodb_lock_dump_efficiency_refactor_execplan.md --path PROJECT_TRACKER.md`

## Validation and Acceptance

Acceptance requires all of the following:

- Targeted rq-engine request paths produce the same responses and state outcomes for equivalent payloads as before the refactor.
- Code inspection confirms grouped updates happen through single-lock helper paths on the targeted candidates.
- No legacy Flask files were changed.
- Touched test suites pass.
- Package and tracker docs are updated with executed commands and outcomes.

## Idempotence and Recovery

Refactor steps are additive and can be applied incrementally by candidate path. If one candidate introduces regressions, revert that candidate's helper path without affecting completed candidates. Avoid broad shared helper abstractions until at least one highest-impact path is validated.

## Artifacts and Notes

Record key command outcomes and review findings in:
- `docs/work-packages/20260425_nodb_lock_dump_efficiency_refactor/tracker.md`
- optional artifacts under `docs/work-packages/20260425_nodb_lock_dump_efficiency_refactor/artifacts/`

## Interfaces and Dependencies

The end state should expose explicit grouped mutation interfaces (exact names can vary if equivalent and clear):

- Soils grouped apply method for fields currently set in `apply_wepp_run_payload`.
- Watershed grouped apply method for fields currently set in `_apply_watershed_updates`.
- Disturbed grouped apply method for burn toggles.
- Landuse grouped apply method for mode + single selection pair.
- BatchRunner grouped apply method for SBS map path + metadata.
- Wepp grouped apply method for job hint (`job_id`, `job_key`).

Each grouped interface must preserve existing validation semantics or raise the same contract-level errors.
