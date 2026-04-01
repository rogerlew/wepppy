# Features Export Live-Run E2E Matrix (Phase 2 Reopen: Omni Scenarios/Contrasts)

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

This plan establishes release-confidence for Features Export by validating real outputs, not just unit behavior. After completion, maintainers will have evidence that every format produces valid artifacts, identity keys are normalized (`topaz_id`, `wepp_id`), CRS and units behavior is correct, temporal selectors behave as designed (including year selection), and regressions are locked in tests.

## Progress

- [x] (2026-03-29) Authored work-package scaffold and full matrix definition.
- [x] (2026-03-29) Expanded scope with gate model, cache-hit replay checks, data oracles, and additional negative-path validation.
- [x] (2026-03-29) Built single case-catalog source that emits `Gate-1`, `Gate-2`, and expansion (`F-G`) runs (`artifacts/run_live_matrix.py`).
- [x] (2026-03-29) Built matrix runner and executed against `clogging-starch/disturbed9002-wbt-mofe`.
- [x] (2026-03-29) Built artifact auditor validating format signatures, file-level CRS probes, manifest consistency, key-domain oracles, and identity/null invariants.
- [x] (2026-03-29) Executed `Gate-1` sentinel suite (7 success + 3 negatives) and captured manual evidence.
- [x] (2026-03-29) Executed `Gate-2` core matrix (`A-E`) and triaged defects.
- [x] (2026-03-29) Executed expansion groups (`F-G`) including cache replay, negative payload contract, and numeric unit oracles.
- [x] (2026-03-29) Implemented defects discovered during matrix execution (return-period selector materialization, unit conversion integration, mixed temporal wide planner behavior, atemporal temporal-mode inheritance, UI copy typo).
- [x] (2026-03-29) Added regression tests for critical slices.
- [x] (2026-03-29) Updated docs/trackers and artifacts for handoff.
- [x] (2026-03-29) Reopened this ExecPlan as Phase 2 to execute deferred Omni scenario/contrast live-run testing.
- [x] (2026-03-29) Implemented Phase-2 harness extensions (`--phase phase2_omni`) with dynamic selector discovery and Omni groups `H1-H4`.
- [x] (2026-03-29) Defined Omni scenario and Omni contrast case groups on `walk-in-obsessive-compulsive/disturbed9002_wbt` (single-OFE run).
- [x] (2026-03-29) Executed Omni `Gate-1` sentinel exports and captured artifacts.
- [x] (2026-03-29) Executed Omni expansion matrix groups and appended evidence/results.
- [x] (2026-04-01) Extended expansion matrix with disturbed lookup `bd` variant group `I1` (`base|extended` x `blank|numeric`) via runner preconditions.
- [x] (2026-04-01) Executed full rerun matrix with timestamped artifacts; all 140 rows passed (`I1`: 4/4).

## Surprises & Discoveries

- Observation: Cache index reset must preserve schema (`schema_version=1`); a malformed reset payload hard-failed all submissions with `Unsupported cache index schema_version None`.
  Evidence: Initial Gate-1 matrix run failures in `matrix_results.jsonl`; corrected cache payload structure.

- Observation: `temporal.event.selector=return_period` could not materialize with live data because `return_period_events.parquet` does not include a `return_period` column.
  Evidence: live run error `materialization_error` before fix; post-fix `b3_event_selector_return_period` passes.

- Observation: Unit conversion was previously only represented in cache fingerprints, not applied to exported numeric values.
  Evidence: pre-fix SI/English exports had identical values; post-fix `G1` numeric oracles pass with expected conversion magnitudes.

- Observation: Mixed event+yearly wide tabular requests were rejected due a planner-level `invalid_selector_combo` guard that also blocked valid wide-mode behavior.
  Evidence: `b4_mixed_temporal_wide` failed pre-fix and passes post-fix.

- Observation: Global temporal mode was being applied to atemporal layers, causing atemporal+temporal combo failures in `B6` and `C3`.
  Evidence: `materialization_error` on `watershed.subcatchments` pre-fix; combo cases pass post-fix.

- Observation: Phase 1 closure intentionally deferred Omni-inclusive validation to follow-up despite harness support.
  Evidence: package `Follow-up Work` and tracker closeout notes.

- Observation: The Phase-2 Omni run contains valid selectors for scenarios (`mulch_15_sbs_map`, `mulch_30_sbs_map`, `mulch_60_sbs_map`) and contrasts (`1-24`), but temporal selector columns (`date`, `return_period`, `year`) are absent from required Omni interchange sources.
  Evidence: `h4_neg_scenario_event_temporal_columns_missing` and `h4_neg_contrast_yearly_temporal_columns_missing` both passed expected `materialization_error` assertions.

- Observation: Omni scope-invariant exports continue to emit backend `scope_not_applicable` warnings when `output_scopes=["baseline","roads"]`; these are informational and do not affect artifact correctness.
  Evidence: `h4_scope_roads_scenario` and `h4_scope_roads_contrast` warning-code assertions.

- Observation: Disturbed lookup mutation for `I1` requires explicit state restoration to avoid leaking lookup variant/CSV edits into subsequent matrix runs.
  Evidence: `run_live_matrix.py` now snapshots and restores `disturbed.active_lookup_variant` and both lookup CSV files in `finally` around execution.

## Decision Log

- Decision: Start validation on one roads-capable live run before multi-run expansion.
  Rationale: Fastest path to real-data correctness confidence with meaningful scope/temporal coverage.
  Date/Author: 2026-03-29 / Codex.

- Decision: Treat tabular identity completeness as strict (`topaz_id` and `wepp_id` non-null per row).
  Rationale: Matches operator requirement and recent normalization bug history.
  Date/Author: 2026-03-29 / Codex.

- Decision: Use staged execution gates (`Gate-1` then `Gate-2`) instead of running full matrix first.
  Rationale: Reduces turnaround time for obvious contract regressions and prevents expensive full-matrix reruns before basic correctness.
  Date/Author: 2026-03-29 / Codex.

- Decision: Execute matrix against a fresh cache index with backup to ensure post-fix behavior is audited and stale artifacts do not mask fixes.
  Rationale: Existing cache entries predated defects fixed during execution (notably CRS and units behavior paths).
  Date/Author: 2026-03-29 / Codex.

- Decision: Treat `return_period_event_ranks` as lookup-only selector support and exclude it from carrier joins.
  Rationale: Including rank source rows in carrier joins created many-to-many cardinality conflicts and unstable event-token materialization.
  Date/Author: 2026-03-29 / Codex.

- Decision: Resolve return-period selector lookup using preferred measure ranking when available.
  Rationale: Restricts selector mapping to deterministic event candidates and avoids conflicting per-measure event assignments for one return-period token.
  Date/Author: 2026-03-29 / Codex.

- Decision: Allow mixed event+yearly requests in `tabular.temporal_layout=wide` and keep rejection scoped to long-layout mixed mode.
  Rationale: Matches feature contract (`B4` success / `B5` rejection) and UI behavior requirements.
  Date/Author: 2026-03-29 / Codex.

- Decision: Do not propagate global temporal mode onto atemporal layers.
  Rationale: Atemporal layers must remain exportable alongside temporal layers without synthetic temporal token requirements.
  Date/Author: 2026-03-29 / Codex.

- Decision: Reopen this existing package for Omni scenario/contrast testing instead of creating a new package.
  Rationale: Reuses established matrix harness, artifacts, and defect ledger while preserving one continuous validation history.
  Date/Author: 2026-03-29 / Codex.

- Decision: Discover Phase-2 Omni selector IDs directly from run-path datasets at execution time instead of hardcoding IDs in the case catalog.
  Rationale: Prevents stale selector fixtures and ensures sentinel coverage always targets selectors with required interchange dependencies.
  Date/Author: 2026-03-29 / Codex.

- Decision: Model missing Omni temporal selector columns on this run as expected negative-path contract checks (`materialization_error`) rather than patching runtime behavior in this package.
  Rationale: Current specification requires explicit materialization failure when required sources cannot satisfy requested temporal selectors.
  Date/Author: 2026-03-29 / Codex.

- Decision: Add disturbed `bd` coverage using runner-level preconditions (`lookup_variant`, `bd_mode`) instead of introducing new Features Export request fields.
  Rationale: Coverage requirement targets disturbed lookup state, and payload contract changes were out of scope.
  Date/Author: 2026-04-01 / Codex.

## Outcomes & Retrospective

Phase 1 matrix execution completed with strict gate order:
  - `Gate-1`: 10/10 passed.
  - `Gate-2`: 80/80 passed (includes synthesized `E1` and `E2` audits).
  - Expansion (`F-G`): 20/20 passed.
- Required behavior checks validated in final run:
  - all 7 formats emitted expected payload/member signatures,
  - spatial CRS behavior (`wgs`/`utm`) validated at file level and tabular CRS no-op validated,
  - units behavior (`project`/`si`/`english`) validated with numeric conversion assertions,
  - temporal behavior validated for annual-average/yearly/event selectors, year-selection variants, and mixed long-layout rejection,
  - identity/data integrity validated (`topaz_id`, `wepp_id`, tabular completeness, key-domain reconciliation),
  - cache replay contract validated (`cache_hit`, `source_job_id`, stable artifact mapping),
  - UI regression checks passed (`Unitizer Selections` copy, no temporal-change reload regression, export-button unlock behavior).
- Final artifact ledger: `docs/work-packages/20260329_features_export_live_run_matrix/artifacts/matrix_results.jsonl` (110 rows, 0 failures).
- Manual format sanity evidence: `docs/work-packages/20260329_features_export_live_run_matrix/artifacts/manual_sanity_notes.md`.
- Defect/fix/rerun log: `docs/work-packages/20260329_features_export_live_run_matrix/artifacts/defect_log.md`.
- Required validation suites passed:
  - `wctl run-pytest tests/nodb/mods/test_features_export_service.py --maxfail=1`
  - `wctl run-pytest tests/microservices/test_rq_engine_features_export_routes.py --maxfail=1`
  - `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1`
  - `wctl run-npm test -- features_export`

Phase 2 status:
- Omni Phase-2 execution completed on `walk-in-obsessive-compulsive/disturbed9002_wbt` with:
  - `H1` Omni scenario sentinel: 7/7 passed.
  - `H2` Omni contrast sentinel: 7/7 passed.
  - `H3` Omni selector negatives: 4/4 passed.
  - `H4` Omni scope/temporal compatibility: 8/8 passed.
  - Wall-clock execution window (matrix harness): 286.742 seconds (`2026-03-29T05:51:05Z` to `2026-03-29T05:55:52Z`).
- Phase-2 harness/artefact additions:
  - `docs/work-packages/20260329_features_export_live_run_matrix/artifacts/run_live_matrix.py` now supports `--phase phase2_omni` and dynamic Omni selector discovery from run-path datasets.
  - `docs/work-packages/20260329_features_export_live_run_matrix/artifacts/manual_sanity_notes_phase2_omni.md`
  - `docs/work-packages/20260329_features_export_live_run_matrix/artifacts/defect_log_phase2_omni.md`
- Shared matrix ledger appended with Omni rows:
  - `docs/work-packages/20260329_features_export_live_run_matrix/artifacts/matrix_results.jsonl` now contains 136 rows total (110 Phase-1 + 26 Phase-2), 0 new failures.
- Phase 3 rerun status:
  - Disturbed lookup `bd` variant coverage added as group `I1`:
    - `i1_bd_base_blank`
    - `i1_bd_base_numeric`
    - `i1_bd_extended_blank`
    - `i1_bd_extended_numeric`
  - Full rerun artifacts (`20260401_023942`) show 140/140 passed rows, including `I1` 4/4.
  - Rerun evidence:
    - `docs/work-packages/20260329_features_export_live_run_matrix/artifacts/matrix_results_rerun_20260401_023942.jsonl`
    - `docs/work-packages/20260329_features_export_live_run_matrix/artifacts/manual_sanity_notes_rerun_20260401_023942_phase1.md`
    - `docs/work-packages/20260329_features_export_live_run_matrix/artifacts/defect_log_rerun_20260401_023942_phase1.md`
    - `docs/work-packages/20260329_features_export_live_run_matrix/artifacts/manual_sanity_notes_rerun_20260401_023942_phase2_omni.md`
    - `docs/work-packages/20260329_features_export_live_run_matrix/artifacts/defect_log_rerun_20260401_023942_phase2_omni.md`

## Context and Orientation

Primary run under test:
- `runid=clogging-starch`
- `config=disturbed9002-wbt-mofe`
- run root: `/wc1/runs/cl/clogging-starch`

Phase 2 reopen run under test:
- `runid=walk-in-obsessive-compulsive`
- `config=disturbed9002_wbt`
- run root: `/wc1/runs/wa/walk-in-obsessive-compulsive`
- discovered scenario selectors with required interchange data: `mulch_15_sbs_map`, `mulch_30_sbs_map`, `mulch_60_sbs_map`
- discovered contrast selectors with required interchange data: `1..24`

Primary module and contracts:
- `wepppy/nodb/mods/features_export/specification.md`
- `wepppy/nodb/mods/features_export/layer_catalog.yaml`
- `wepppy/nodb/mods/features_export/service.py`
- `wepppy/microservices/rq_engine/export_routes.py`
- `wepppy/weppcloud/controllers_js/features_export.js`
- `wepppy/weppcloud/templates/controls/features_export_pure.htm`

Artifacts are zip bundles. Valid exports must include `manifest.json`, `profile.yml`, built-in profiles, and provenance `README.md`.

## Matrix Case Catalog

### Parameter Sets

- Spatial formats: `geojson`, `geoparquet`, `kmz`, `geopackage`, `geodatabase`
- Tabular formats: `parquet`, `csv`
- CRS options: `wgs`, `utm`
- Unit modes: `project`, `si`, `english`
- Scope modes: `baseline`, `baseline+roads`
- Temporal selectors:
  - yearly selectors: `all`, `exclude_first`, `exclude_first_two`, `exclude_first_five`, `custom`
  - event selectors: `date`, `return_period`

### Concrete Layer Anchors

- Atemporal: `watershed.subcatchments`
- Atemporal multi: `watershed.subcatchments`, `watershed.channels`, `landuse.dominant`, `soils.dominant`
- Scope-aware: `wepp.summary.hillslopes`, `wepp.summary.channels`
- Yearly: `wepp.interchange.loss_all_years_hill`
- Event: `wepp.temporal.events`
- Mixed temporal: `wepp.interchange.loss_all_years_hill` + `wepp.temporal.events`

### Matrix Expansion

- A1: 30 runs (spatial format contract)
- A2: 12 runs (tabular format contract)
- B1: 5 runs (year selection variants)
- B2: 1 run (yearly multi-layer)
- B3: 2 runs (event selector variants)
- B4: 1 run (mixed temporal wide success)
- B5: 1 run (mixed temporal long rejection)
- B6: 2 runs (atemporal+temporal blends)
- C1: 5 runs (spatial yearly)
- C2: 5 runs (spatial event)
- C3: 5 runs (spatial mixed)
- D1: 7 runs (scope baseline+roads across all formats)
- D2: 2 runs (tabular concatenate scope provenance)
- E1: integrity audit across successful runs
- E2: manifest integrity audit across successful runs
- F1: 7 runs (cache-hit replay contract)
- F2: 8 runs (additional negative payload contract)
- G1: 4 runs (units numeric oracle checks)
- G2: UI regression checks via Jest/route suites (no export job submissions)
- I1: 4 runs (disturbed lookup `bd` variant coverage: `base|extended` x `blank|numeric`)

Core total (`A-E`): 78 runs (77 positive + 1 negative).  
Expanded total (`A-G+I1`): 101 export-job runs + UI regression test suites.

Phase 2 Omni reopen additions:
- H1: Omni scenario exports on single-OFE run (`omni_scenarios` family).
- H2: Omni contrast exports on single-OFE run (`omni_contrasts` family).
- H3: Omni selector negative-path checks (mixed scenario+contrast selection rejection, missing selector rejection).
- H4: Omni scope/temporal compatibility assertions for selected WEPP-coupled layers.
Phase 2 Omni total: 26 runs (22 positive + 4 negative).

## Plan of Work

### Milestone 1 - Harness and Audit Substrate

Implement two helpers:
- Matrix runner: submits payloads, tracks `job_id`, waits for terminal state, downloads zip.
- Artifact auditor: validates members, signatures, schema/count invariants, identity/null checks, file-level CRS checks, and key-domain oracles.

Also implement UI text fix (`Unitizer Selections`) and add a focused Jest assertion.

### Milestone 2 - Gate-1 Sentinel

Execute one representative successful case per format (7 total), plus core negative contract cases. Capture:
- request payload,
- artifact id + manifest,
- summary of observed member files,
- spot verification (QGIS/ogrinfo/parquet reader),
- any anomalies.

### Milestone 3 - Gate-2 Core Matrix Execution and Defect Triage

Execute core matrix groups A-E. For each failure:
- classify as contract gap, implementation defect, or data-specific exception,
- patch defects,
- rerun failed case and nearest-neighbor cases,
- append evidence to `artifacts/` and tracker notes.

### Milestone 4 - Expansion Matrix and Cache/Negative Coverage

Execute expansion groups F-G:
- cache-hit replay checks,
- additional negative payload contract checks,
- units numeric oracle checks,
- UI regression suites.

### Milestone 5 - Regression Lock-In

Add/extend pytest and Jest coverage for:
- format/member/signature contract,
- CRS behavior,
- tabular identity completeness,
- key-domain oracle checks,
- temporal yearly/event selector rules,
- mixed temporal long rejection,
- cache-hit replay contract,
- additional invalid payload rejection cases,
- UI label copy (`Unitizer Selections`).

### Milestone 6 - Closeout

Update package docs and tracker, move ExecPlan to `prompts/completed/`, summarize outcomes and open follow-ups.

## Concrete Steps

Working directory for all commands: `/workdir/wepppy`.

1. Build/iterate harness utilities.
2. Execute manual pilot:
   - submit request,
   - inspect `jobinfo` and download artifact,
   - run artifact audit,
   - save evidence snippets under `docs/work-packages/20260329_features_export_live_run_matrix/artifacts/`.
3. Execute full matrix and collect structured results (`jsonl` or `csv`).
4. Patch defects and rerun impacted cases.
5. Add tests and run validation suites.
6. Run cache/negative expansion groups and lock in final evidence.

## Validation and Acceptance

Mandatory validations after code/test updates:

- `wctl run-pytest tests/nodb/mods/test_features_export_service.py --maxfail=1`
- `wctl run-pytest tests/microservices/test_rq_engine_features_export_routes.py --maxfail=1`
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1`
- `wctl run-npm test -- features_export`

Acceptance conditions:
- `Gate-1` sentinel suite passes.
- All core positive matrix cases pass.
- Negative-path cases fail with contract-consistent 400/404/409 responses.
- No unresolved identity-null irregularities remain.
- Cache-hit replay contract is verified (`cache_hit`, `source_job_id`, stable artifact mapping).
- Manual evidence exists for each format family.

## Idempotence and Recovery

- Matrix runner must write per-case artifacts with deterministic case IDs so reruns overwrite or version cleanly.
- Failed runs are safe to retry individually.
- For partial progress, resume from the first failed case; do not rerun already-passing cases unless affected by a patch.

## Artifacts and Notes

Target artifacts to capture:
- `matrix_results.jsonl` with one row per case.
- `manual_sanity_notes.md` with 7 format spot checks.
- `defect_log.md` with bug -> fix -> rerun evidence.
- timestamped rerun artifacts when full-matrix reruns are executed (for example `matrix_results_rerun_20260401_023942.jsonl` with paired phase1/phase2 notes and defect logs).

## Interfaces and Dependencies

- Features export submit endpoint: `/rq-engine/api/runs/{runid}/{config}/export/features`
- Polling endpoints: `/rq-engine/api/jobstatus/{job_id}`, `/rq-engine/api/jobinfo/{job_id}`
- Download endpoint shape in `jobinfo.result.download_url`

Date/author note:
- 2026-03-29 / Codex: initial ExecPlan authored with explicit 78-case matrix and milestone sequencing.
- 2026-03-29 / Codex: reopened ExecPlan for Omni scenario/contrast Phase 2 on `walk-in-obsessive-compulsive/disturbed9002_wbt`.
