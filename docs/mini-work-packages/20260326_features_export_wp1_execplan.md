# Features Export WP-1 Contracts, Catalog Loader, and Planner Skeleton

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md` and must be maintained in accordance with that template.

## Purpose / Big Picture

WP-1 establishes the deterministic planning boundary for Features Export before any exporter or queue wiring exists. After this change, backend code can take a request payload plus the authoritative layer catalog and produce a fully normalized, validated, deterministic `ResolvedExportPlan` or a canonical 400-style validation contract. This unlocks WP-2+ without introducing filesystem/geospatial side effects into planning.

## Progress

- [x] (2026-03-26 15:52Z) Read required inputs: root `AGENTS.md`, `wepppy/nodb/AGENTS.md`, features export specification sections 3/4/5.1/7/8/9/14.1/14.3, and `layer_catalog.yaml`.
- [x] (2026-03-26 15:58Z) Implemented WP-1 module files: `contracts.py`, `catalog_loader.py`, `planner.py`, and package `__init__.py` exports.
- [x] (2026-03-26 16:02Z) Added focused WP-1 tests for catalog loader and planner selector/normalization behaviors.
- [x] (2026-03-26 16:13Z) Ran requested validation commands: both focused pytest modules, full `tests/nodb/mods`, `wctl run-stubtest wepppy.nodb.mods.features_export`, and `wctl check-test-stubs`.
- [x] (2026-03-26 16:07Z) Completed correctness self-review pass and patched one issue (nullable temporal access warning found via stubtest/mypy).
- [x] (2026-03-26 16:15Z) Completed QA edge-case pass and added coverage for temporal compatibility drop behavior and all-layers-excluded error behavior.
- [x] (2026-03-26 16:16Z) Updated `wepppy/nodb/mods/features_export/specification.md` with WP-1 completion status and concrete contract clarifications.
- [x] (2026-03-26 16:16Z) Finalized outcomes/retrospective and handoff-ready notes.

## Surprises & Discoveries

- Observation: `layer_catalog.yaml` currently contains 18 layers across scope-aware and scope-invariant families, including per-layer temporal mode rules and strict locator-kind contracts.
  Evidence: parsed catalog summary from `wepppy/nodb/mods/features_export/layer_catalog.yaml` during planning.
- Observation: `stubtest` for a new module without dedicated stubs can fail on runtime typing helper symbols (`Any`, `Mapping`, `Sequence`) even when functional tests pass.
  Evidence: initial `wctl run-stubtest wepppy.nodb.mods.features_export` failures; resolved after removing runtime typing helper exports from module surfaces.
- Observation: temporal compatibility behavior needed explicit edge-case tests to guard partial-export warnings and all-layer exclusion failures.
  Evidence: added planner tests that now assert `layer_unavailable` warning behavior and `no_exportable_layers` validation behavior.

## Decision Log

- Decision: Keep planner APIs pure and side-effect free by requiring a preloaded catalog object input; no catalog file I/O inside planner paths.
  Rationale: Matches section 14.3 keep-it-organized rules and enables deterministic unit testing.
  Date/Author: 2026-03-26 / Codex

- Decision: Enforce canonical validation failures through a module-local typed validation exception that can emit rq-engine-compatible 400 error payload shape (`code=validation_error`, `errors[]`).
  Rationale: WP-1 must deliver strong validation contracts before route/task adapters exist.
  Date/Author: 2026-03-26 / Codex
- Decision: Keep catalog/planner type hints runtime-neutral (`object` + `collections.abc`) instead of exposing typing helper symbols.
  Rationale: Prevents `stubtest` runtime-surface mismatches while preserving static typing clarity.
  Date/Author: 2026-03-26 / Codex
- Decision: Add QA regression coverage for temporal compatibility outcomes beyond baseline validation cases.
  Rationale: Temporal mode handling is a high-risk selector path and needed explicit tests for partial success vs hard failure.
  Date/Author: 2026-03-26 / Codex

## Outcomes & Retrospective

WP-1 is complete and confined to requested scope. The module now provides typed contracts, strict request normalization/validation, catalog loading/schema validation, and deterministic resolved planning with warning/error contracts. No WP-2+ features (dependency tracking/cache index/exporters/routes/UI) were implemented.

Both required review loops were completed. The correctness pass surfaced one typing-surface issue (nullable temporal attribute access) and the QA pass surfaced a coverage gap in temporal compatibility outcomes; both were fixed with code/tests and revalidated.

Validation commands requested for this milestone all pass from the final state, including the broad `tests/nodb/mods` sweep and stub checks.

## Context and Orientation

Target code lives under `wepppy/nodb/mods/features_export/` and currently includes only specification/catalog UI planning docs. WP-1 adds backend contracts and deterministic planning artifacts only. No exporter implementations, dependency fingerprinting, RQ routes/tasks, cache index logic, or UI wiring are in scope.

Primary files to add in this milestone:
- `wepppy/nodb/mods/features_export/contracts.py`
- `wepppy/nodb/mods/features_export/catalog_loader.py`
- `wepppy/nodb/mods/features_export/planner.py`
- `wepppy/nodb/mods/features_export/__init__.py`

Primary tests to add:
- `tests/nodb/mods/test_features_export_catalog_loader.py`
- `tests/nodb/mods/test_features_export_planner.py`

## Plan of Work

Implement typed contracts first so validation issues, warning codes, request structures, and resolved-plan structures are centralized and reusable. Next, implement catalog loading with schema checks required by the planner: metadata/header presence, unique layer IDs, strict locator vocabulary (`kind` + `value` only), and temporal mode/event-selector constraints.

After that, implement planner normalization and validation rules against the loaded catalog: canonical format/units/crs/output_scopes, alias `f_esri -> geodatabase`, layer existence checks, scenario/contrast mutual exclusion and family compatibility rules, temporal mode/event selector validation (including explicit daily rejection), and deterministic resolved-layer ordering/serialization.

Finally, add focused tests for required WP-1 cases, run requested validation commands, then perform two review loops (correctness, QA edge cases) with patches and reruns as needed.

## Concrete Steps

From `/workdir/wepppy`:

1. Create WP-1 code files in `wepppy/nodb/mods/features_export/`.
2. Add WP-1 tests in `tests/nodb/mods/`.
3. Run:
   - `wctl run-pytest tests/nodb/mods/test_features_export_catalog_loader.py --maxfail=1`
   - `wctl run-pytest tests/nodb/mods/test_features_export_planner.py --maxfail=1`
   - `wctl run-pytest tests/nodb/mods --maxfail=1`
4. If public typing surface changed, run:
   - `wctl run-stubtest wepppy.nodb.mods.features_export`
   - `wctl check-test-stubs`
5. Update this ExecPlan plus `wepppy/nodb/mods/features_export/specification.md` with concrete WP-1 completion notes.

## Validation and Acceptance

Acceptance for this milestone requires:
- Deterministic `ResolvedExportPlan` generation from normalized requests and catalog.
- Strong validation with canonical 400-style error contract payload conversion.
- Required selector and enum validations from spec section 5.1/8/9.
- Strict catalog loader validation for planner-required schema/locator/temporal contracts.
- Requested pytest commands passing.
- Review loops completed with high/medium findings fixed.

## Idempotence and Recovery

Changes are additive and local to features export module/tests/docs. Test commands are safe to rerun. If a failure appears during review, patch only the affected module(s), rerun targeted tests first, then rerun the broader `tests/nodb/mods` command.

## Artifacts and Notes

Validation evidence from `/workdir/wepppy` final state:
- `wctl run-pytest tests/nodb/mods/test_features_export_catalog_loader.py --maxfail=1` -> pass (2 passed).
- `wctl run-pytest tests/nodb/mods/test_features_export_planner.py --maxfail=1` -> pass (13 passed).
- `wctl run-pytest tests/nodb/mods --maxfail=1` -> pass (410 passed).
- `wctl run-stubtest wepppy.nodb.mods.features_export` -> pass (no issues found in 4 modules).
- `wctl check-test-stubs` -> pass.

Review findings resolved:
- Correctness pass: fixed nullable temporal mode access path in warning message construction.
- QA pass: added two tests for temporal compatibility behavior (`layer_unavailable` partial drop and `no_exportable_layers` terminal validation).

## Interfaces and Dependencies

Planned public interfaces for WP-1:
- Contracts and error/warning/request/result dataclasses in `contracts.py`.
- Catalog loading + validation API in `catalog_loader.py`.
- Pure normalization/planning APIs in `planner.py`.

No new third-party dependencies are introduced; use existing runtime dependencies already present in the repository (including YAML parsing support used elsewhere).

## Revision Notes

- 2026-03-26 (Codex): Created initial WP-1 ExecPlan at the user-specified path after reading required AGENTS/spec/catalog context.
- 2026-03-26 (Codex): Marked implementation/testing/review completion, captured stubtest-driven typing-surface fix, documented QA edge-case additions, and recorded final validation outcomes.
