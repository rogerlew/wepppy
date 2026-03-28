# WP-Tabular: Features Export Concatenation + Temporal Wide/Long Controls

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Reference process template: `docs/prompt_templates/codex_exec_plans.md`. This document is maintained in accordance with that template.

## Purpose / Big Picture

Users exporting tabular features (`.csv`, `.parquet`) currently get one table per output layer and no explicit control for temporal shape. This change adds format-dependent controls that let users (1) concatenate tabular outputs by carrier (`hillslopes`, `channels`) and (2) choose temporal layout (`wide` default or `long`). The result is a downstream-friendly tabular export contract with clear validation when incompatible temporal selections are mixed.

After this change, a user can run tabular features export and explicitly choose:
- whether to concatenate hillslope/channel tables, with scope/scenario/contrast provenance columns attached
- whether temporal event/yearly metrics are emitted as wide columns or long rows

## Progress

- [x] (2026-03-28 14:35Z) Reviewed root and subsystem AGENTS guidance (`wepppy/nodb`, `wepppy/weppcloud/controllers_js`, `tests`, `rq_engine`) and current features_export implementation.
- [x] (2026-03-28 14:42Z) Authored this mini work-package with full phases and acceptance criteria.
- [x] (2026-03-28 15:12Z) Implemented backend request/planner contract for `tabular.concatenate_tables` + `tabular.temporal_layout` with mixed yearly/event long-mode validation.
- [x] (2026-03-28 15:28Z) Implemented service/export behavior for tabular concatenation and temporal long layout.
- [x] (2026-03-28 15:39Z) Implemented UI controls/hints and format-dependent visibility in template/controller JS.
- [x] (2026-03-28 16:01Z) Added/adjusted tests across planner/service/exporters/rq routes/template/controller JS.
- [x] (2026-03-28 16:22Z) Ran validation command set and captured evidence.
- [x] (2026-03-28 16:30Z) Performed explicit code review and QA review passes and recorded outcomes.
- [x] (2026-03-28 16:35Z) Updated `wepppy/nodb/mods/features_export/specification.md` to match shipped behavior.

## Surprises & Discoveries

- Observation: The backend already includes a temporal wide materializer (`temporal_wide_materializer.py`) invoked by carrier materialization.
  Evidence: `carrier_layer_materializer.py` calls `materialize_temporal_layer_wide(...)` for `event` and `yearly`.
- Observation: Existing CSV/Parquet writers always emit one file per resolved layer and do not currently concatenate by carrier.
  Evidence: `exporters/csv.py` and `exporters/parquet.py` iterate `layer_pairs` and write `<output_layer_id>.<ext>` per layer.
- Observation: Applying long temporal layout before writer stage is safest when done from already key-first, geometry-attached payload frames, but before final unitized-name suffixing.
  Evidence: `service.py` now calls `reshape_temporal_wide_to_long(...)` before `apply_unitized_column_suffixes(...)` in key-first carrier payload assembly.

## Decision Log

- Decision: Implement tabular options under a single request object `tabular` with keys `concatenate_tables` and `temporal_layout`.
  Rationale: Keeps payload explicit and extensible while containing tabular-only behavior away from spatial format contracts.
  Date/Author: 2026-03-28 / Codex
- Decision: Keep `wide` as the default temporal layout for tabular formats.
  Rationale: Matches existing effective behavior and user request `(x) wide`.
  Date/Author: 2026-03-28 / Codex
- Decision: Enforce a validation error when `tabular.temporal_layout=long` is used with mixed effective `event` and `yearly` layer modes.
  Rationale: Long mode requires one temporal axis column name (`date` vs `return_period` vs `year`) and mixed selectors become ambiguous.
  Date/Author: 2026-03-28 / Codex
- Decision: Treat `tabular` payload fields as invalid for non-tabular formats (`geopackage`, `geodatabase`, `geojson`, `geoparquet`, `kmz`).
  Rationale: Keeps request contract explicit and avoids silently ignored controls that can mask client-side wiring errors.
  Date/Author: 2026-03-28 / Codex
- Decision: Implement table concatenation in shared writer helpers (`exporters/tabular_common.py`) and keep CSV/Parquet writers thin.
  Rationale: Prevents format drift and keeps concatenation/provenance semantics identical across both tabular formats.
  Date/Author: 2026-03-28 / Codex

## Outcomes & Retrospective

Delivered end-to-end tabular controls and execution behavior for features_export:
- backend request/planner contract now includes normalized `tabular` options
- tabular concatenation now groups carrier outputs into `hillslopes` and `channels` files when requested, with provenance columns
- tabular long layout now restores temporal rows from wide columns and emits selector column (`date`, `return_period`, or `year`)
- UI now exposes format-dependent tabular controls and blocks invalid mixed long-mode temporal requests
- specification updated and full validation suite for targeted surfaces is green

No unresolved defects were found in the code-review or QA-review pass for this scope. Residual risk is medium-low around future catalog additions that might introduce non-carrier temporal layers; current long-layout reshape is integrated in the key-first carrier path.

## Context and Orientation

Primary backend modules:
- `wepppy/nodb/mods/features_export/contracts.py`: typed request and resolved-plan contracts.
- `wepppy/nodb/mods/features_export/planner.py`: normalization and validation.
- `wepppy/nodb/mods/features_export/service.py`: materialization orchestration and payload preparation.
- `wepppy/nodb/mods/features_export/exporters/csv.py` and `exporters/parquet.py`: tabular writer behavior.

Primary UI modules:
- `wepppy/weppcloud/templates/controls/features_export_pure.htm`: control markup.
- `wepppy/weppcloud/controllers_js/features_export.js`: format visibility, validation, payload build, and submit path.

Test surfaces:
- `tests/nodb/mods/test_features_export_planner.py`
- `tests/nodb/mods/test_features_export_service.py`
- `tests/nodb/mods/test_features_export_exporters.py`
- `tests/microservices/test_rq_engine_features_export_routes.py`
- `tests/weppcloud/routes/test_pure_controls_render.py`
- `wepppy/weppcloud/controllers_js/__tests__/features_export.test.js`

Documentation surface:
- `wepppy/nodb/mods/features_export/specification.md`

## Plan of Work

Phase 1 implements request-contract support for tabular options and planner validation. The planner will normalize tabular options, enforce enum/boolean correctness, and reject mixed yearly/event effective temporal modes when long layout is selected.

Phase 2 implements backend execution changes. Service/materialization will support long temporal output for tabular exports while preserving existing wide behavior as default. Tabular writers will support optional concatenation by carrier buckets (`hillslopes`, `channels`) and add provenance columns (`output_scope`, `omni_scenario`, `omni_contrast_id`) where applicable.

Phase 3 implements frontend controls and hints. The features-export settings panel will show tabular-only options when format is `csv` or `parquet`, and the controller will include options in payload + validation, including explicit user-facing error messaging for disallowed mixed long-mode temporal selections.

Phase 4 is verification and review. Update/extend tests, run command suite, execute explicit code-review and QA-review passes, then update the living spec and this work-package with evidence.

## Concrete Steps

1. Edit contracts/planner to add `tabular` request normalization and validation.
2. Edit service/materialization and tabular writers to implement long-layout/concatenation behavior.
3. Edit template/controller JS and frontend tests for new controls, hints, and payload/validation behavior.
4. Extend backend tests for normalization, long-mode validation, and concatenation outputs.
5. Run test/lint command set and document outputs.
6. Perform code-review pass and QA-review pass and document findings/results.
7. Update specification and finalize this plan’s living sections.

## Validation and Acceptance

Acceptance criteria:
- `csv`/`parquet` UI shows:
  - `Concatenate tables` checkbox
  - `wide/long` temporal layout radios
  only when tabular format is selected.
- Payload includes tabular options for tabular requests.
- Planner rejects invalid tabular options and rejects mixed yearly/event effective modes when long layout is selected.
- Tabular concatenate behavior emits carrier-concatenated hillslope/channel tables with `output_scope`, `omni_scenario`, `omni_contrast_id` columns.
- Wide remains default and long behavior is observable in exported tabular columns.
- Specification is updated to match implemented contract.

Validation commands to run:
- `wctl run-pytest tests/nodb/mods/test_features_export_planner.py tests/nodb/mods/test_features_export_service.py tests/nodb/mods/test_features_export_exporters.py tests/microservices/test_rq_engine_features_export_routes.py --maxfail=1`
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py -k features_export --maxfail=1`
- `wctl run-pytest tests/weppcloud/routes/test_run_0_openet_admin_gate.py -k features_export --maxfail=1`
- `wctl run-npm test -- features_export`
- `wctl doc-lint --path wepppy/nodb/mods/features_export/specification.md`
- `wctl doc-lint --path docs/mini-work-packages/20260328_features_export_tabular_concat_temporal_layout_execplan.md`

## Idempotence and Recovery

All edits are source-controlled and additive. Re-running tests is safe. If a specific test fails, iterate on the touched module and re-run only affected suites before repeating the full validation list.

## Artifacts and Notes

Validation evidence:
- `wctl run-pytest tests/nodb/mods/test_features_export_planner.py tests/nodb/mods/test_features_export_service.py tests/nodb/mods/test_features_export_exporters.py tests/microservices/test_rq_engine_features_export_routes.py --maxfail=1`
  - Result: `87 passed`
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py -k features_export --maxfail=1`
  - Result: `4 passed`
- `wctl run-pytest tests/weppcloud/routes/test_run_0_openet_admin_gate.py -k features_export --maxfail=1`
  - Result: `10 passed`
- `wctl run-npm test -- features_export`
  - Result: `17 passed`
- `wctl doc-lint --path wepppy/nodb/mods/features_export/specification.md`
  - Result: `0 errors, 0 warnings`
- `wctl doc-lint --path docs/mini-work-packages/20260328_features_export_tabular_concat_temporal_layout_execplan.md`
  - Result: `0 errors, 0 warnings`

Code-review phase summary:
- Reviewed diffs for contract normalization, service materialization touchpoints, and writer grouping semantics.
- Finding status: no critical or high-severity defects identified in changed code.
- Noted risk: long-layout reshape currently exercised in carrier path; future non-carrier temporal layers should add explicit coverage.

QA-review phase summary:
- Added targeted tests for planner tabular validation, temporal wide-to-long reshape, tabular concatenation/provenance output, rq-route payload acceptance, template DOM contract, and controller behavior.
- Executed all required validation commands successfully.

## Interfaces and Dependencies

New/updated interfaces to exist after completion:
- `NormalizedExportRequest.tabular` includes normalized tabular options.
- Planner accepts optional request payload object:
  - `tabular.concatenate_tables: bool`
  - `tabular.temporal_layout: "wide" | "long"`
- Controller payload builder includes `tabular` for `csv`/`parquet`.
- Tabular writers consume normalized tabular options via plan request and apply concatenation behavior.

---

Change log:
- 2026-03-28: Initial authored work-package for tabular concatenate + temporal layout controls, including implementation, test, code-review, QA-review, and spec update phases.
- 2026-03-28: Completed implementation, validations, and review phases; recorded evidence and retrospective.
