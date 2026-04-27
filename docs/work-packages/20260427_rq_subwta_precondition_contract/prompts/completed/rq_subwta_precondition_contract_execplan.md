# RQ WEPP Subwta Precondition Contract Enforcement

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Completion Outcome

Closed on 2026-04-27. The package enforced strict non-mutating `watershed.subwta` precondition checks for `run-wepp` and `run-wepp-watershed`, aligned canonical response docs and schema-default metadata, added targeted regression coverage, and dispositioned required reviewer/QA findings before archival.

## Purpose / Big Picture

After this package, `run-wepp` and `run-wepp-watershed` will have a single unambiguous precondition contract: if `watershed.subwta` is missing, the request fails with canonical `409 invalid_watershed_abstraction_state` before enqueue. This removes ambiguity introduced by batch/base and checkbox-toggled execution modes.

## Progress

- [x] (2026-04-27 20:20 UTC) Package scaffolded and decision captured from user direction.
- [x] (2026-04-27 20:33 UTC) Implemented strict abstraction-state gate ordering in `wepp_routes.py` for `run-wepp` and `run-wepp-watershed`.
- [x] (2026-04-27 20:33 UTC) Aligned canonical response contract text and schema-default error metadata.
- [x] (2026-04-27 20:33 UTC) Added targeted regression tests for normal, batch, `_base`, and `checkbox_wepp_watershed=false` contexts while preserving `prep-wepp-watershed`.
- [x] (2026-04-27 20:33 UTC) Ran targeted pytest gate: `118 passed`.
- [x] (2026-04-27 20:43 UTC) Disposed reviewer findings by moving the gate before payload mutation and documenting recovery-action limits for batch/_base contexts.
- [x] (2026-04-27 20:43 UTC) Reran targeted pytest after reviewer dispositions: `118 passed`.
- [x] (2026-04-27 20:43 UTC) Closed package tracker/package docs and prepared prompt archival.
- [x] (2026-04-27 20:44 UTC) Ran final doc-lint and diff-check gates.

## Surprises & Discoveries

- Observation: Current route flow applies payload updates, then short-circuits batch/base before abstraction-state checks.
  Evidence: `wepppy/microservices/rq_engine/wepp_routes.py` `_handle_run_wepp_request`.

- Observation: `checkbox_wepp_watershed` can set `_run_wepp_watershed=False`, while RQ routes currently enforce abstraction-state checks only after batch/base short-circuit.
  Evidence: `wepppy/microservices/rq_engine/wepp_run_payload.py` routine override mapping and lock block.

- Observation: A partial draft already added the canonical error helper and schema metadata but still placed the `subwta` check after the batch/base success shortcut.
  Evidence: local diff of `wepppy/microservices/rq_engine/wepp_routes.py` before this update showed `_watershed_abstraction_state_response(...)` below `if getattr(wepp, "run_group", "") == "batch" or _is_base_project_context(...)`.

## Decision Log

- Decision: `watershed.subwta` is always required for `run-wepp` and `run-wepp-watershed`.
  Rationale: user directive; removing `subwta.tif` invalidates hillslope/watershed run integrity.
  Date/Author: 2026-04-27 / Codex

- Decision: Execute the `subwta` gate immediately after resolving the run directory and before parsing/applying run payload.
  Rationale: reviewer feedback clarified that a strict precondition failure should not persist payload, soils, watershed, or routine-checkbox mutations before returning `409 invalid_watershed_abstraction_state`.
  Date/Author: 2026-04-27 / Codex

- Decision: Keep schema-default recovery metadata pointing to `build-subcatchments-and-abstract-watershed`, but document that this action only enqueues outside batch/_base contexts.
  Rationale: the watershed rebuild endpoint remains the normal-mode recovery operation, while its existing batch/_base no-queue behavior is out of scope for this package and must not be hidden from clients.
  Date/Author: 2026-04-27 / Codex

## Outcomes & Retrospective

Closed. Runtime and metadata changes are implemented, reviewer findings have code/docs dispositions, targeted pytest passed after those dispositions, final doc-lint/diff-check gates passed, and package lifecycle docs record closure. No follow-up package is recommended.

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

Final validation evidence:
- `wctl run-pytest tests/microservices/test_rq_engine_wepp_routes.py tests/microservices/test_rq_engine_schema_defaults_routes.py --maxfail=1` passed with `118 passed`.
- `wctl doc-lint --path docs/schemas/rq-response-contract.md --path docs/work-packages/20260427_rq_subwta_precondition_contract --path PROJECT_TRACKER.md` passed with `5 files validated, 0 errors, 0 warnings`.
- `git diff --check` passed.

## Validation and Acceptance

Acceptance requires all of the following:
- `run-wepp` and `run-wepp-watershed` both return canonical `409 invalid_watershed_abstraction_state` when `watershed.subwta` is missing, independent of batch/base/checkbox context.
- Contract docs and schema-default metadata match runtime behavior with no contradictions.
- Targeted microservice tests pass.

## Idempotence and Recovery

Changes are route/doc/test scoped and safe to iterate. If strict gating causes unexpected compatibility issues in test fixtures, update fixtures or explicit contract docs in the same change rather than introducing silent bypass behavior.

## Revision Notes

- 2026-04-27: Initial active ExecPlan created with strict contract decision from user direction.
- 2026-04-27: Updated with implementation progress, strict gate ordering decision, and targeted pytest evidence.
- 2026-04-27: Revised after reviewer feedback to make rejected precondition paths non-mutating and to document recovery-action limits.
- 2026-04-27: Closed package and archived this ExecPlan with completion outcome.
- 2026-04-27: Added final validation evidence after package closure gates passed.
