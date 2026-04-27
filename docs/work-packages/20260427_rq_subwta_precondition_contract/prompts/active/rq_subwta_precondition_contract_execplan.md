# RQ WEPP Subwta Precondition Contract Enforcement

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this package, `run-wepp` and `run-wepp-watershed` will have a single unambiguous precondition contract: if `watershed.subwta` is missing, the request fails with canonical `409 invalid_watershed_abstraction_state` before enqueue. This removes ambiguity introduced by batch/base and checkbox-toggled execution modes.

## Progress

- [x] (2026-04-27 20:20 UTC) Package scaffolded and decision captured from user direction.
- [ ] Implement strict pre-enqueue abstraction-state gate ordering in `wepp_routes.py`.
- [ ] Align canonical response contract + schema-default metadata.
- [ ] Add/adjust targeted microservice regression tests.
- [ ] Run validation commands and update package lifecycle docs.

## Surprises & Discoveries

- Observation: Current route flow applies payload updates, then short-circuits batch/base before abstraction-state checks.
  Evidence: `wepppy/microservices/rq_engine/wepp_routes.py` `_handle_run_wepp_request`.

- Observation: `checkbox_wepp_watershed` can set `_run_wepp_watershed=False`, while RQ routes currently enforce abstraction-state checks only after batch/base short-circuit.
  Evidence: `wepppy/microservices/rq_engine/wepp_run_payload.py` routine override mapping and lock block.

## Decision Log

- Decision: `watershed.subwta` is always required for `run-wepp` and `run-wepp-watershed`.
  Rationale: user directive; removing `subwta.tif` invalidates hillslope/watershed run integrity.
  Date/Author: 2026-04-27 / Codex

## Outcomes & Retrospective

Pending implementation.

## Context and Orientation

Runtime behavior is governed by `wepppy/microservices/rq_engine/wepp_routes.py`, where `_handle_run_wepp_request` currently handles auth payload parsing, batch/base shortcut responses, optional abstraction-state validation, and enqueue wiring. Payload checkbox parsing is applied by `wepppy/microservices/rq_engine/wepp_run_payload.py`. Canonical contract text lives in `docs/schemas/rq-response-contract.md`, and endpoint defaults/error metadata are generated from `wepppy/microservices/rq_engine/schema_defaults_routes.py`.

## Plan of Work

Reorder and/or harden route precondition logic so strict abstraction-state validation happens before any batch/base return paths for the two run endpoints. Ensure payload routine flags do not bypass this validation. Then update contract docs and schema defaults to reflect strict behavior, followed by targeted regression tests for strict `subwta` enforcement in normal/batch/base/checkbox contexts.

## Concrete Steps

Run from `/workdir/wepppy`:

1. Edit route contract behavior and tests.
2. Update schema/docs text and metadata assertions.
3. Validate with:
   - `wctl run-pytest tests/microservices/test_rq_engine_wepp_routes.py tests/microservices/test_rq_engine_schema_defaults_routes.py --maxfail=1`
   - `wctl doc-lint --path docs/schemas/rq-response-contract.md --path docs/work-packages/20260427_rq_subwta_precondition_contract --path PROJECT_TRACKER.md`
   - `git diff --check`

## Validation and Acceptance

Acceptance requires all of the following:
- `run-wepp` and `run-wepp-watershed` both return canonical `409 invalid_watershed_abstraction_state` when `watershed.subwta` is missing, independent of batch/base/checkbox context.
- Contract docs and schema-default metadata match runtime behavior with no contradictions.
- Targeted microservice tests pass.

## Idempotence and Recovery

Changes are route/doc/test scoped and safe to iterate. If strict gating causes unexpected compatibility issues in test fixtures, update fixtures or explicit contract docs in the same change rather than introducing silent bypass behavior.

## Revision Notes

- 2026-04-27: Initial active ExecPlan created with strict contract decision from user direction.
