# Landuse Batched Mapping Submit

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, a user can adjust one or many landuse mapping selects in the summary table and then click one explicit submit action to apply all staged mapping edits at once. This removes request-per-change behavior, unifies single and Multi-OFE UX, and reduces lock/queue contention by processing one mapping batch in one RQ job.

## Progress

- [x] (2026-04-24 00:27 UTC) Work-package scaffold, tracker, and initial ExecPlan created.
- [ ] Define and document canonical batch mapping API contract (payload, validation, response, and failure semantics).
- [ ] Implement staged mapping edit UX and explicit submit control in landuse report/controller.
- [ ] Implement batch mapping enqueue path in rq-engine route without mapping `depends_on`.
- [ ] Implement batch mapping worker behavior under one lock window and one completion trigger.
- [ ] Update controller JS, microservice route, and RQ mutation-guard tests.
- [ ] Run targeted validations and record outcomes in package docs.
- [ ] Move ExecPlan to `prompts/completed/` with closure outcome notes.

## Surprises & Discoveries

- None yet. Update this section as implementation work reveals non-obvious behavior.

## Decision Log

- Decision: Stage mapping edits in UI and submit them explicitly as one batch request.
  Rationale: Current per-change submit model creates queue fan-out and lock contention, especially in repeated Multi-OFE edit sessions.
  Date/Author: 2026-04-24 / Codex.

- Decision: Remove mapping `depends_on` chaining from enqueue path.
  Rationale: Chained failures can strand descendants in deferred state; one-submit/one-job semantics are simpler and more reliable for this UX.
  Date/Author: 2026-04-24 / Codex.

## Outcomes & Retrospective

Not complete yet. Populate at milestone and package closure with:
- implemented behavior vs plan,
- test/validation evidence,
- residual gaps/follow-up.

## Context and Orientation

Current behavior is split across these files:
- `wepppy/weppcloud/templates/reports/landuse.htm`: report table with mapping `<select data-landuse-role="mapping-select">`.
- `wepppy/weppcloud/controllers_js/landuse.js`: report delegate currently calls `landuse.modify_mapping(...)` immediately on mapping select `change`.
- `wepppy/microservices/rq_engine/landuse_routes.py`: route `/runs/{runid}/{config}/modify-landuse-mapping` enqueues one `modify_landuse_mapping_rq` job and currently wires `depends_on` to previous mapping job id from `RedisPrep`.
- `wepppy/rq/project_rq.py`: `modify_landuse_mapping_rq` applies one mapping mutation under landuse root maintenance lock.

Tests that cover this flow:
- `wepppy/weppcloud/controllers_js/__tests__/landuse.test.js`
- `tests/microservices/test_rq_engine_landuse_routes.py`
- `tests/rq/test_project_rq_mutation_guards.py`

## Plan of Work

Milestone 1 focuses on contract clarity before code edits. Define one canonical batch payload and deterministic semantics for duplicate/chained entries in the same request. Decide and document whether semantics are all-or-nothing and whether duplicates collapse to last-write-wins before execution.

Milestone 2 implements staged UI behavior. The mapping select change event should mark rows as pending rather than submit network requests. Add a secondary submit control in the report area, disable it when there are no staged edits, and provide clear pending/applied feedback while preserving current status-stream panel behavior.

Milestone 3 updates backend enqueue and worker execution. Route accepts batch payload, validates all entries, and enqueues one job without `depends_on`. Worker applies mappings in defined order inside one lock scope and emits one completion event for report refresh.

Milestone 4 validates behavior with targeted tests and closes documentation. Ensure single and Multi-OFE use the same interaction and that deferred-stranding failure mode is removed from this path.

## Concrete Steps

Working directory: `/home/workdir/wepppy`

1. Confirm and document current call path and route contracts.

    rg -n "mapping-select|modify_mapping|modify-landuse-mapping|depends_on" \
      wepppy/weppcloud/controllers_js/landuse.js \
      wepppy/weppcloud/templates/reports/landuse.htm \
      wepppy/microservices/rq_engine/landuse_routes.py \
      wepppy/rq/project_rq.py

2. Implement staged UI + explicit submit.
   - Edit `wepppy/weppcloud/templates/reports/landuse.htm`.
   - Edit `wepppy/weppcloud/controllers_js/landuse.js`.

3. Implement batch route + worker contract.
   - Edit `wepppy/microservices/rq_engine/landuse_routes.py`.
   - Edit `wepppy/rq/project_rq.py`.

4. Update tests.

    wctl run-pytest tests/microservices/test_rq_engine_landuse_routes.py --maxfail=1
    wctl run-pytest tests/rq/test_project_rq_mutation_guards.py --maxfail=1
    wctl run-npm test -- --runTestsByPath wepppy/weppcloud/controllers_js/__tests__/landuse.test.js

5. Run docs lint for package updates.

    wctl doc-lint --path docs/work-packages/20260423_landuse_batched_mapping_submit

## Validation and Acceptance

Acceptance requires:
- Changing mapping selects does not submit network requests immediately.
- Submit action posts one request containing one or more mapping changes.
- Route enqueues one mapping job without `depends_on` predecessor chaining.
- Worker applies the defined mapping batch semantics under one landuse lock scope.
- Existing status/completion behavior still refreshes report once for the submitted mapping batch.
- Targeted JS/microservice/RQ tests pass for new batch behavior and failure cases.

## Idempotence and Recovery

- Re-submitting unchanged staged payload should be safe and produce no unintended drift.
- If a batch fails validation, no partial mutation should be applied and staged UI state should remain visible for correction.
- If implementation introduces regression risk, keep edits isolated to mapping UX/API path and preserve straightforward rollback to immediate-submit behavior by reverting touched files.

## Artifacts and Notes

Execution artifacts to maintain in package folder:
- `tracker.md` progress/decision updates with UTC timestamps.
- Optional notes under `notes/` for payload examples and UX state diagrams.
- Optional evidence under `artifacts/` (manual smoke captures, failure payload samples).

## Interfaces and Dependencies

Primary interfaces:
- `Landuse` controller mapping delegate and submit actions (`wepppy/weppcloud/controllers_js/landuse.js`).
- Landuse report mapping controls (`wepppy/weppcloud/templates/reports/landuse.htm`).
- rq-engine mapping route handler (`wepppy/microservices/rq_engine/landuse_routes.py`).
- RQ mapping worker (`wepppy/rq/project_rq.py`).

Dependencies:
- `RedisPrep` mapping job id bookkeeping.
- runtime-path landuse lock contract (`nodir_maintenance_lock` path in RQ worker).
- existing completion event `LANDUSE_MODIFY_MAPPING_TASK_COMPLETED` unless intentionally versioned.

## Revision Notes

- 2026-04-24 / Codex: Initial ExecPlan created from user-approved direction to move from per-change submit to staged batch submit and remove mapping dependency chaining.
