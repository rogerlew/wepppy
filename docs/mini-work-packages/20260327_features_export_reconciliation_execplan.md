# Features Export WP-7 Reconciliation (DuckDB + UX Contract Reset)

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md` and must be maintained in accordance with that template.

## Purpose / Big Picture

This work package reconciles the current `features_export` behavior with operator expectations before further feature growth. After this plan, users should see one clear WEPP dataset catalog (familiar output names), select temporal mode per applicable dataset, apply one global year selection, and get consolidated exports with predictable layer names and counts (base plus selected Omni contexts). Performance-sensitive merge/materialization paths should run through DuckDB SQL execution rather than pandas merge pipelines.

The expected user-visible outcome is that a typical base WEPP export produces up to two layers per requested scope (`subcatchments` and `channels` carriers), while selected Omni scenarios/contrasts add their own scope-aware carrier layers with descriptive names. The control should remove unnecessary search/filter clutter, present clear hierarchy, dynamically hide unavailable groups while disabling unavailable scope options, and allow per-dataset column selection from an expandable unit-aware column list. This plan also adds geometryless export formats (`parquet`, `csv`) as first-class tabular outputs and prepares follow-on profile work to replace `prep_details`.

## Progress

- [x] (2026-03-27 19:14Z) Read required context: root `AGENTS.md`, `wepppy/nodb/AGENTS.md`, `wepppy/nodb/mods/features_export/specification.md`, `wepppy/nodb/mods/features_export/ui_control_layout.md`, and recent WP-1..WP-5 ExecPlans.
- [x] (2026-03-27 19:14Z) Updated `wepppy/nodb/mods/features_export/specification.md` with reconciliation contracts for DuckDB-first merging, WEPP taxonomy, temporal controls, Omni selection semantics, consolidated naming, and discovery-driven UI behavior.
- [x] (2026-03-27 19:14Z) Added WP-7 registration in specification Section 14.1 with dependency-order updates.
- [x] (2026-03-27 19:14Z) Created this WP-7 ExecPlan.
- [x] (2026-03-27 19:25Z) Updated specification/UI contracts to include geometryless `parquet` and `csv` formats and noted post-WP follow-on profile direction for replacing `prep_details`.
- [x] (2026-03-27 20:08Z) Implemented catalog/data-contract reconciliation in code paths (`contracts.py`, `planner.py`, `run_0_bp.py`) including WEPP family/UI consolidation and canonical Omni array selectors (`scenarios`, `contrast_ids`) with singular alias compatibility.
- [x] (2026-03-27 20:09Z) Implemented geometryless format support (`parquet`, `csv`) as first-class exporters with deterministic per-layer naming and manifest surfacing.
- [x] (2026-03-27 20:09Z) Implemented DuckDB-first merge/materialization hot paths in `service.py`, including DuckDB join helper usage for source joins and consolidated carrier materialization for WEPP/Omni contexts.
- [x] (2026-03-27 20:10Z) Implemented UI layout/discovery revisions in template/controller (search/filter strip removed, hierarchy-first catalog, Omni multiselect controls, global temporal selectors with per-dataset mode controls).
- [x] (2026-03-27 20:10Z) Implemented per-dataset expandable column selectors with unit/required-lock rendering and request serialization via `column_selection`.
- [x] (2026-03-27 20:11Z) Implemented discovery-aware behavior and websocket refresh path: unavailable families/layers hidden, roads scope disabled when unavailable, and status-stream discovery payload refresh support.
- [x] (2026-03-27 20:15Z) Added/extended coverage for WP-7 behaviors:
- consolidated carrier naming/materialization regression in `tests/nodb/mods/test_features_export_service.py`
- geometryless parquet/csv schema behavior in `tests/nodb/mods/test_features_export_exporters.py`
- controller payload/discovery/omni-multiselect behavior in `wepppy/weppcloud/controllers_js/__tests__/features_export.test.js`
- [x] (2026-03-27 20:18Z) Ran requested validation gates with passing results:
- `wctl run-pytest tests/nodb/mods/test_features_export_planner.py tests/nodb/mods/test_features_export_service.py tests/nodb/mods/test_features_export_exporters.py tests/microservices/test_rq_engine_features_export_routes.py --maxfail=1` -> `47 passed`
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py -k features_export --maxfail=1` -> `4 passed`
- `wctl run-pytest tests/weppcloud/routes/test_run_0_openet_admin_gate.py -k features_export --maxfail=1` -> `7 passed`
- `wctl run-npm test -- features_export` -> `11 passed`
- `wctl run-playwright --env dev --no-create-run --run-path "https://wc.bearhive.duckdns.org/weppcloud/runs/minus-farce/disturbed9002_wbt/?playwright_load_all=true" --workers 1 --grep "features_export"` -> `1 passed`
- [x] (2026-03-27 20:58Z) Addressed operator-reported regressions in WP-7 UI/output behavior:
- moved global Year selection block directly after CRS in `features_export_pure.htm`
- corrected collapsible markup so dataset toggle checkbox is no longer nested inside `<summary>`
- constrained per-dataset temporal-mode control width (`max-width: 22rem`)
- normalized checkbox styling to `wc-choice wc-choice--checkbox` for per-column selectors
- hardened column-unit discovery/inference for fallback contracts (`baseflow_mm` now resolves to `mm`)
- added frontend defensive column dedupe to prevent duplicate checkbox rows if payloads drift
- bumped export cache marker to invalidate stale pre-WP-7 artifacts (`features-export-wp7`)
- [x] (2026-03-27 21:04Z) Added regression coverage for operator pain points:
- `tests/nodb/mods/test_features_export_service.py` adds explicit 6 WEPP inputs -> 2 carrier outputs assertion (`sbs_map-subcatchments`, `chan_map-channels`)
- `wepppy/weppcloud/controllers_js/__tests__/features_export.test.js` asserts no layer checkbox inside `<summary>` and no duplicated per-layer rendered columns
- `tests/weppcloud/routes/test_pure_controls_render.py` asserts Year selection appears after CRS and before the temporal group section
- [x] (2026-03-27 21:04Z) Re-ran required validation gates after regression fixes:
- `wctl run-pytest tests/nodb/mods/test_features_export_planner.py tests/nodb/mods/test_features_export_service.py tests/nodb/mods/test_features_export_exporters.py tests/microservices/test_rq_engine_features_export_routes.py --maxfail=1` -> `48 passed`
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py -k features_export --maxfail=1` -> `4 passed`
- `wctl run-pytest tests/weppcloud/routes/test_run_0_openet_admin_gate.py -k features_export --maxfail=1` -> `8 passed`
- `wctl run-npm test -- features_export` -> `12 passed`
- `wctl run-playwright --env dev --no-create-run --run-path "https://wc.bearhive.duckdns.org/weppcloud/runs/minus-farce/disturbed9002_wbt/?playwright_load_all=true" --workers 1 --grep "features_export"` -> `1 passed`
- [x] (2026-03-27 21:12Z) Extended consolidation to carrier-level merging for base geometric families (not WEPP-only) and normalized base `shared` scope into baseline consolidation groups so baseline exports can collapse to two carrier outputs (`chan_map-channels`, `sbs_map-subcatchments`).
- [x] (2026-03-27 21:12Z) Bumped cache marker to `features-export-wp8` after consolidation-key behavior change to prevent stale six-layer cache reuse.
- [x] (2026-03-27 21:15Z) Verified on operator run workspace (`/wc1/runs/cl/clogging-starch`) by replaying the recorded request payload:
- old job manifest (`jobs/0bee93f8-6556-4894-9a0c-239d34e3a034/manifest.json`) had `6` layers
- fresh run (`jobs/manual-wp8-layer-check/manifest.json`) now has `2` layers: `clogging-starch-chan_map-channels`, `clogging-starch-sbs_map-subcatchments`
- [x] (2026-03-27 23:01Z) Investigated follow-on operator report (“2 layers but only ID columns”) and confirmed legacy WEPP interchange parquet schema mismatch:
- source columns were legacy labels (`Runoff Volume`, `Soil Loss`, `Sediment Yield`, `Discharge Volume`) that did not match canonical selection IDs (`runoff_mm`, `soil_loss_kg_ha`, `sediment_yield_kg_ha`, `discharge_mm`, etc.)
- [x] (2026-03-27 23:01Z) Implemented source-column canonicalization for `wepp_loss_hill` and `wepp_loss_channel` plus identity-column de-duplication in consolidated outputs, then bumped cache marker to `features-export-wp9`.
- [x] (2026-03-27 23:01Z) Revalidated on `/wc1/runs/cl/clogging-starch` with direct service execution:
- artifact `export/features/artifacts/459dab5f11b34c3794df24c11deb8058/features_export.gpkg`
- manifest `export/features/jobs/manual-wp9-column-check/manifest.json`
- `2` layers with expected measures:
- `clogging-starch-sbs_map-subcatchments`: `TopazID`, `wepp_id`, `runoff_mm`, `subrunoff_mm`, `baseflow_mm`, `soil_loss_kg_ha`, `sediment_yield_kg_ha`
- `clogging-starch-chan_map-channels`: `TopazID`, `discharge_mm`, `sediment_delivery_kg_ha`, `erosion_kg_ha`
- [x] (2026-03-27 23:26Z) Replaced hardcoded WEPP source-column aliasing with discovery-first schema flow:
- `run_0_bp.py` now discovers per-layer parquet source schemas/units from run data and pushes discovered column contracts to UI payloads.
- planner now accepts dynamic `column_selection` ids for layers without explicit static `columns` contracts.
- service now propagates discovered parquet field units into manifest/output metadata without static alias maps.
- [x] (2026-03-27 23:26Z) Bumped cache marker to `features-export-wp10` to invalidate stale pre-discovery column-selection artifacts.
- [x] (2026-03-27 23:26Z) Revalidated requested gates after discovery-first changes:
- `wctl run-pytest tests/nodb/mods/test_features_export_planner.py tests/nodb/mods/test_features_export_service.py tests/nodb/mods/test_features_export_exporters.py tests/microservices/test_rq_engine_features_export_routes.py --maxfail=1` -> `51 passed`
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py -k features_export --maxfail=1` -> `4 passed`
- `wctl run-pytest tests/weppcloud/routes/test_run_0_openet_admin_gate.py -k features_export --maxfail=1` -> `9 passed`
- `wctl run-npm test -- features_export` -> `12 passed`
- `wctl run-playwright --env dev --no-create-run --run-path "https://wc.bearhive.duckdns.org/weppcloud/runs/minus-farce/disturbed9002_wbt/?playwright_load_all=true" --workers 1 --grep "features_export"` -> `1 passed`
- [x] (2026-03-27 23:26Z) Updated specs to codify discovery-driven column contract fallback and planner validation semantics for layers without explicit static `columns` metadata.
- [x] (2026-03-27 23:26Z) Run-path evidence on `/wc1/runs/cl/clogging-starch` with direct service execution and no hardcoded aliasing:
- manifest `export/features/jobs/manual-wp10-discovery/manifest.json`
- artifact `export/features/artifacts/72510aa151194d9caabcd8175cb61f18/features_export.gpkg` (`manual-wp10-discovery-v2`)
- consolidated layers: `clogging-starch-chan_map-channels` (30 columns) and `clogging-starch-sbs_map-subcatchments` (27 columns), confirming 2-layer consolidation with expanded discovered schema columns.
- [x] (2026-03-28 00:18Z) Added schema-description discovery and UI hierarchy hardening for operator usability:
- `run_0_bp.py` now enriches discovered columns with parquet metadata (`description`, `units`, `label`) and falls back to interchange `README.md` table docs by discovered source filename.
- column-contract normalization now dedupes alias-equivalent column IDs (`topaz_id` vs `TopazID`) by canonical key and keeps only one required identity lock per alias-family.
- `features_export.js` now renders explicit family -> dataset -> columns hierarchy with indented nested containers, schema-description rows, and bounded temporal-select width class (`features-export-tree__temporal-field`).
- `features_export_pure.htm` now defines scoped hierarchy styles (`features-export-tree__*`) for readability and consistent PureCSS checkbox presentation.
- [x] (2026-03-28 00:18Z) Re-ran required WP-7 validation commands after hierarchy/description changes:
- `wctl run-pytest tests/nodb/mods/test_features_export_planner.py tests/nodb/mods/test_features_export_service.py tests/nodb/mods/test_features_export_exporters.py tests/microservices/test_rq_engine_features_export_routes.py --maxfail=1` -> `51 passed`
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py -k features_export --maxfail=1` -> `4 passed`
- `wctl run-pytest tests/weppcloud/routes/test_run_0_openet_admin_gate.py -k features_export --maxfail=1` -> `10 passed`
- `wctl run-npm test -- features_export` -> `12 passed`
- `wctl run-playwright --env dev --no-create-run --run-path "https://wc.bearhive.duckdns.org/weppcloud/runs/minus-farce/disturbed9002_wbt/?playwright_load_all=true" --workers 1 --grep "features_export"` -> `1 passed`

## Surprises & Discoveries

- Observation: The current contract exposes internal vocabulary (`WEPP Summary`, `WEPP Temporal`, `WEPP Interchange`, and `wepp.temporal.events`) that does not match domain naming used elsewhere in WEPP workflows.
  Evidence: Current `features_export` spec/UI layout sections and operator feedback from this request.
- Observation: Existing selector schema (`scenario`, `contrast_id`) is singular, which blocks required multi-selection behavior and bulk selection controls.
  Evidence: Request schema in `wepppy/nodb/mods/features_export/specification.md` before WP-7 update.
- Observation: Layer cardinality currently trends toward one-layer-per-output behavior, which creates noisy output packs and obscures the intended geometry-carrier model.
  Evidence: User-reported output behavior and existing scope naming contract (`{scope}__{layer_id}`) in pre-WP-7 spec text.
- Observation: Existing service tests were coupled to removed internal helper `_build_layer_payloads`; WP-7 materialization refactor renamed this boundary to `_materialize_export_payloads`.
  Evidence: Initial `test_features_export_service.py` failures during validation run.
- Observation: Catalog entries do not yet provide explicit `columns` contracts for every dataset; WP-7 UI requires a deterministic fallback.
  Evidence: `run_0_bp.py` needed `_features_export_column_contract` fallback derivation from join/measures/identity metadata.
- Observation: `controlBase.attach_status_stream` already exposes `onStatus` callback with raw payload, which made discovery-refresh-on-websocket feasible without framework changes.
  Evidence: `control_base.js` callback surface (`onStatus`) and successful controller regression test for discovery refresh.
- Observation: stale cache artifacts can surface pre-consolidation layer cardinality even after service logic changes.
  Evidence: operator report of 6 output layers despite consolidation contract and subsequent cache marker bump (`features-export-wp7`) to force artifact regeneration.
- Observation: even with WEPP consolidation active, base scope-invariant families (`watershed`, `landuse`, `soils`) remained unconsolidated because `_should_consolidate_layer` was family-gated and grouping keys split `shared` vs `baseline`.
  Evidence: run manifest at `/wc1/runs/cl/clogging-starch/export/features/jobs/0bee93f8-6556-4894-9a0c-239d34e3a034/manifest.json` showed 2 WEPP carrier outputs plus 4 shared family outputs (6 total).
- Observation: the run’s WEPP interchange parquet schema uses legacy human-readable column labels rather than canonical snake-case IDs, so canonical `column_selection` include lists excluded those measures.
  Evidence: `loss_pw0.hill.parquet` columns (`Runoff Volume`, `Baseflow Volume`, `Soil Loss`, `Sediment Yield`) and `loss_pw0.chn.parquet` columns (`Discharge Volume`, `Soil Loss`, `Sediment Yield`) inspected directly from `/wc1/runs/cl/clogging-starch/wepp/output/interchange/`.
- Observation: nesting interactive labels/inputs inside `<summary>` caused collapsible interaction breakage and flaky checkbox state transitions under Playwright.
  Evidence: operator-provided DOM snippet and one regression during controller rerender behavior (`locator.check` did not observe state change until markup/rerender strategy was corrected).
- Observation: static catalog-derived measure ids (`runoff_mm`, `baseflow_mm`, etc.) can drift from runtime interchange schemas (`Runoff Volume`, `Baseflow Volume`, etc.), causing UI include lists to under-select merged outputs.
  Evidence: operator report of six-column outputs and direct schema inspection from `/wc1/runs/cl/clogging-starch/wepp/output/interchange/*.parquet`.
- Observation: parquet field metadata is heterogeneous; many files only provide `units` while descriptions are present in interchange `README.md` tables for a subset of datasets.
  Evidence: direct metadata inspection via `wctl exec weppcloud python` and README table review under `/wc1/runs/cl/clogging-starch/wepp/output/interchange/README.md`.
- Observation: required identity aliases (`topaz_id`, `TopazID`) can silently force duplicate lock-columns in selectors unless canonicalized before UI contract emission.
  Evidence: operator screenshot + prior contract behavior that treated each alias token as independently required.

## Decision Log

- Decision: Formalize DuckDB-first as the required production data-shaping path for `features_export`.
  Rationale: Merge performance and deterministic schema handling are central pain points; SQL joins/projections are the intended owned-stack baseline.
  Date/Author: 2026-03-27 / Codex
- Decision: Keep backward compatibility for request payloads by accepting singular `scenario`/`contrast_id` aliases while standardizing contract fields to `scenarios`/`contrast_ids`.
  Rationale: Enables immediate multi-select semantics without breaking callers still on singular payload shape.
  Date/Author: 2026-03-27 / Codex
- Decision: Consolidate WEPP/Omni output materialization to geometry carriers (`sbs_map-subcatchments`, `chan_map-channels`) per context and scope.
  Rationale: Aligns output-layer count with operator expectations and simplifies interpretation of exported artifacts.
  Date/Author: 2026-03-27 / Codex
- Decision: Make temporal mode dataset-scoped but keep year selection global.
  Rationale: Supports mixed temporal needs without fragmenting year-filter behavior across controls.
  Date/Author: 2026-03-27 / Codex
- Decision: Add per-dataset column selection through expandable row details with unit visibility.
  Rationale: Users need precise field control without losing scan-first dataset discovery; units must be visible at selection time.
  Date/Author: 2026-03-27 / Codex
- Decision: Add canonical geometryless format tokens `parquet` and `csv`.
  Rationale: Users need tabular exports independent of geometry containers, and these formats are the basis for a planned `prep_details` replacement profile.
  Date/Author: 2026-03-27 / Codex
- Decision: Keep consolidation naming/materialization in service execution rather than planner normalization.
  Rationale: Planner remains request-resolution focused, while service has runid/context needed for deterministic carrier naming (`{runid}-...`) and source-frame materialization.
  Date/Author: 2026-03-27 / Codex
- Decision: Build geometryless parquet/csv rows from feature-collection `properties` and drop geometry consistently.
  Rationale: Preserves required identity/join columns while guaranteeing geometryless outputs and stable tabular schema behavior.
  Date/Author: 2026-03-27 / Codex
- Decision: Accept discovery refresh payloads from status stream as either direct availability payloads or nested `discovery` objects.
  Rationale: Supports existing and future server-side message envelopes while keeping controller update logic strict to `refresh_channel=features_export`.
  Date/Author: 2026-03-27 / Codex
- Decision: Invalidate legacy features-export cache artifacts via `DEFAULT_EXPORT_VERSION_MARKER="features-export-wp7"`.
  Rationale: Guarantees operator-visible layer cardinality and naming reflect WP-7 consolidation contracts instead of pre-WP-7 cached bundles.
  Date/Author: 2026-03-27 / Codex
- Decision: Add duplicate-column guards in both catalog payload normalization and client rendering paths.
  Rationale: Keeps WEPP measure rows deterministic even when upstream catalog sources omit explicit `columns` blocks and fallback derivation is used.
  Date/Author: 2026-03-27 / Codex
- Decision: Consolidate any layer that has a carrier geometry assignment and normalize base `shared` scope into baseline consolidation groups.
  Rationale: Meets operator expectation of two base carrier outputs (subcatchments/channels) for baseline exports while preserving roads-specific carrier separation.
  Date/Author: 2026-03-27 / Codex
- Decision: Canonicalize known legacy WEPP interchange column labels to contract IDs during source ingestion and dedupe suffixed identity columns (`TopazID__*`, `wepp_id__*`) in consolidated projections.
  Rationale: Preserves backwards compatibility with existing run artifacts while restoring expected measure columns in merged carrier outputs.
  Date/Author: 2026-03-27 / Codex
- Decision: Replace hardcoded source-column alias mapping with runtime parquet schema discovery and UI contract propagation; treat static catalog column contracts as optional and allow dynamic column ids when explicit contracts are absent.
  Rationale: Removes fragile downstream coupling and keeps column-selection/merge behavior resilient to interchange schema evolution without per-column code patches.
  Date/Author: 2026-03-27 / Codex
- Decision: Resolve column display metadata in priority order `parquet field metadata -> interchange README table -> inferred fallback`, keyed by discovered source filename and canonicalized column token.
  Rationale: Keeps metadata robust to schema drift while still surfacing professional descriptions/units when only one source carries richer docs.
  Date/Author: 2026-03-28 / Codex
- Decision: Canonicalize required identity column aliases before emitting UI/service required-column locks.
  Rationale: Preserves join integrity while preventing duplicated alias-equivalent required columns in selectors and default exports.
  Date/Author: 2026-03-28 / Codex
- Decision: Render catalog with explicit nested hierarchy classes (`features-export-tree__family`, `__dataset`, `__columns`) and keep checkboxes outside `<summary>`.
  Rationale: Improves scanability and interaction clarity while staying compliant with PureCSS control semantics.
  Date/Author: 2026-03-28 / Codex

## Outcomes & Retrospective

WP-7 implementation is complete for the scoped contracts in this package.

Delivered outcomes:
- DuckDB-first joins/materialization are now the active hot path in export service assembly, including consolidated WEPP/Omni carrier outputs with deterministic naming.
- UI contracts were reconciled to WEPP-facing taxonomy, per-dataset temporal/column controls, Omni multiselect bulk actions, and discovery-aware visibility/roads-scope behavior.
- Geometryless `parquet` and `csv` formats are wired through writer registry and tested for geometry dropping with identity fields retained.
- Manifest payload now carries request column selection plus output-layer column/unit/context metadata needed for downstream consumers.
- Validation evidence across pytest/Jest/Playwright confirms the targeted WP-7 behavior set.
- Post-reconciliation hardening addressed operator-reported UI regressions (Year selection placement, temporal control width, collapsible structure, checkbox styling) and output concerns (WEPP 6->2 carrier consolidation, unitized fallback discovery, duplicate column rows).
- Post-reconciliation run-path verification confirms `/wc1/runs/cl/clogging-starch` payload now materializes to two carrier layers when regenerated under WP-8 cache marker.
- Post-reconciliation run-path verification under WP-9 cache marker confirms both carrier-count and measure-column expectations on the operator run workspace.
- Post-reconciliation hardening replaced brittle alias-based column normalization with runtime schema discovery, so UI column selectors and export selection derive from actual run datasets rather than static assumptions.
- Post-reconciliation run-path verification under WP-10 cache marker confirms two-layer consolidation with expanded discovered columns (`30` channel columns, `27` subcatchment columns) for `/wc1/runs/cl/clogging-starch`.
- Post-reconciliation hardening now surfaces schema-sourced column descriptions/units in the UI hierarchy and removes alias-duplicate required locks, addressing the latest operator usability/regression feedback without adding hardcoded dataset maps.
- Regression coverage now includes README-doc parsing and hierarchy/description rendering assertions, and all required WP-7 validation commands continue to pass after these changes.

Residual follow-on:
- Full profile replacement work for `prep_details` remains post-WP-7 as intended by scope.

## Context and Orientation

`features_export` spans NoDb export logic, rq-engine adapters, and Runs-page controller/template surfaces. The key files for WP-7 are:

- `wepppy/nodb/mods/features_export/specification.md` (normative contract)
- `wepppy/nodb/mods/features_export/layer_catalog.yaml` (dataset taxonomy and capabilities)
- `wepppy/nodb/mods/features_export/contracts.py` (request/result schema contracts)
- `wepppy/nodb/mods/features_export/planner.py` (selector resolution and plan shape)
- `wepppy/nodb/mods/features_export/service.py` (payload assembly orchestration)
- `wepppy/nodb/mods/features_export/exporters/*` (writer boundaries)
- `wepppy/weppcloud/templates/controls/features_export_pure.htm` (control structure)
- `wepppy/weppcloud/controllers_js/features_export.js` (control behavior)
- `wepppy/weppcloud/routes/run_0/run_0_bp.py` + bootstrap templates (dynamic discovery payloads)
- `tests/nodb/mods/test_features_export_*`, `tests/microservices/test_rq_engine_features_export_routes.py`, and UI/route tests under `wepppy/weppcloud/controllers_js/__tests__` and `tests/weppcloud/routes/`.

In this repository, “consolidated carrier layer” means one geometry layer that joins multiple selected WEPP/Omni output measures into a single subcatchment or channels output table for a given context and scope.

## Plan of Work

Milestone 1 updates contracts and catalog semantics. This includes catalog family/label normalization to one user-facing WEPP family, request schema normalization to `scenarios`/`contrast_ids`, and temporal mode resolution updates (`layer_modes` + global year selection semantics). Acceptance for this milestone is contract and planner tests proving backward-compatible alias handling and deterministic selector normalization.

Milestone 2 replaces the WEPP/Omni merge hot path with DuckDB-oriented consolidation. Planner/service outputs must describe carrier targets so service assembly can produce at most two carrier layers per context/scope. Layer naming must follow the descriptive pattern from the specification. Acceptance is functional tests showing expected layer counts/names for base, roads, scenario, and contrast requests.

Milestone 3 applies UI contract reconciliation. Runs-page control layout is updated to hierarchy-first dataset discovery without search/filter strip, with per-dataset temporal mode controls, global year selection after CRS, Omni families pinned to bottom, and explicit bulk select controls for Omni selectors. Acceptance is route/template/Jest/smoke coverage that enforces control order and behavior.

Milestone 3 also implements per-dataset expandable column sections so users can inspect columns, view units, and include/exclude fields before export. Acceptance includes controller/request tests proving `column_selection` payload generation and required-column lock behavior.

Milestone 4 implements dynamic discovery refresh. Controller bootstrap/status stream handling should update availability and scope readiness from websocket-backed payload updates, hide unavailable groups, and disable unavailable roads scope without manual dataset detection. Acceptance is event-driven controller tests plus route/bootstrap payload tests for availability deltas.

Milestone 5 closes validation and rollout evidence. Add targeted regressions for yearly-mode “all years” behavior, unitized column naming, consolidated output naming, and geometryless output behavior (`parquet`, `csv`). Run focused pytest/Jest/smoke gates, then broader sanity gates, recording evidence in this plan.

Milestone 6 captures post-WP follow-on preparation for defaults profiles. This milestone does not replace `prep_details` directly, but documents the profile contract needed for a subsequent package that uses geometryless exports plus curated columns.

## Concrete Steps

From `/workdir/wepppy`:

1. Update contracts/planner/catalog:
   - Edit `wepppy/nodb/mods/features_export/layer_catalog.yaml`, `contracts.py`, `planner.py`, and associated tests.
   - Add catalog column metadata and selection validation paths (`column_selection`).
   - Add format-contract updates for geometryless `parquet` and `csv`.
2. Implement DuckDB consolidation path:
   - Edit `wepppy/nodb/mods/features_export/service.py` and any collaborator modules used for source extraction/joining.
   - Ensure exporter inputs carry consolidated carrier payloads and descriptive output layer names.
3. Update Runs-page control and bootstrap payloads:
   - Edit `wepppy/weppcloud/templates/controls/features_export_pure.htm`.
   - Edit `wepppy/weppcloud/controllers_js/features_export.js`.
   - Edit run bootstrap payload assembly in `wepppy/weppcloud/routes/run_0/run_0_bp.py` and related template JS.
   - Add expandable per-dataset columns UI and column toggle hooks with unit display.
4. Add/adjust tests:
   - `tests/nodb/mods/test_features_export_planner.py`
   - `tests/nodb/mods/test_features_export_service.py`
   - `tests/nodb/mods/test_features_export_exporters.py`
   - `tests/microservices/test_rq_engine_features_export_routes.py`
   - `wepppy/weppcloud/controllers_js/__tests__/features_export.test.js`
   - `tests/weppcloud/routes/test_pure_controls_render.py`
   - `tests/weppcloud/routes/test_run_0_openet_admin_gate.py`
5. Run validation commands:
   - `wctl run-pytest tests/nodb/mods/test_features_export_planner.py --maxfail=1`
   - `wctl run-pytest tests/nodb/mods/test_features_export_service.py --maxfail=1`
   - `wctl run-pytest tests/nodb/mods/test_features_export_exporters.py --maxfail=1`
   - `wctl run-pytest tests/microservices/test_rq_engine_features_export_routes.py --maxfail=1`
   - `wctl run-npm test -- features_export`
   - `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1`
   - `wctl run-pytest tests/weppcloud/routes/test_run_0_openet_admin_gate.py --maxfail=1`
   - `wctl doc-lint --path wepppy/nodb/mods/features_export/specification.md`
   - `wctl doc-lint --path docs/mini-work-packages/20260327_features_export_reconciliation_execplan.md`
6. Run broader sanity (if feasible): `wctl run-pytest tests --maxfail=1`.

## Validation and Acceptance

WP-7 is accepted when:

- Base WEPP exports produce at most two carrier layers per requested scope, with descriptive names matching the updated contract.
- Selected Omni scenarios or contrasts produce their own carrier layers per scope while inheriting base WEPP output selections.
- `yearly` mode includes all available years by default and global year selection applies consistently across selected temporal-capable datasets.
- Unit-applicable columns include unitized column names and manifest unit mappings are present.
- Dataset rows provide collapsible column sections showing column names and units, and users can include/exclude columns per dataset.
- `parquet` and `csv` exports are available as geometryless formats and produce tabular outputs without geometry encodings.
- UI no longer renders a layer search/filter strip, presents hierarchical family/dataset structure, places Omni groups at the bottom, and shows global year selection after CRS.
- Unavailable families are hidden and unavailable roads scope is disabled automatically through discovery updates.
- Targeted test suites and requested validation commands pass.

## Idempotence and Recovery

All WP-7 steps are additive and should be safe to rerun. If a migration step partially updates schema contracts, keep backward alias parsing (`scenario`, `contrast_id`) enabled until all touched tests pass. If a DuckDB consolidation change fails mid-flight, preserve the previous planner/service path behind explicit feature-branch commits and re-run focused tests before attempting broad suite validation.

## Artifacts and Notes

Initial planning artifacts:

- Updated contract document:
  - `wepppy/nodb/mods/features_export/specification.md`
- New implementation plan:
  - `docs/mini-work-packages/20260327_features_export_reconciliation_execplan.md`

Implementation-phase artifacts to capture in this section:

- Before/after layer manifest excerpts showing reduced layer cardinality.
- Timing snapshots for representative merge/materialization workloads (pre vs post DuckDB path).
- UI screenshots or DOM/test evidence for hierarchy/discovery changes and control ordering.

## Interfaces and Dependencies

No new third-party dependency is planned. DuckDB usage should rely on existing repository dependency surfaces. Keep interfaces explicit:

- Planner output must encode context (`base|scenario|contrast`), scope, and carrier target.
- Planner/service contracts must carry per-layer selected column sets for export shaping and manifest reporting.
- Exporter contracts must include geometryless writer paths for `parquet` and `csv`.
- Service assembly must accept normalized selector arrays and produce deterministic layer names.
- UI bootstrap payload must expose discovery metadata needed to hide unavailable families and disable unavailable scopes.
- Controller submit payload must preserve canonical JSON-only contract while supporting updated temporal and Omni selector structures.

## Revision Notes

- 2026-03-27 (Codex): Created WP-7 ExecPlan in response to operator reconciliation request; aligned with updated specification contracts and scoped implementation milestones.
