# Features Export Live-Run E2E Matrix (Phase 2: Omni Scenarios/Contrasts)

**Status**: Completed (Phase 2 closed 2026-03-29 after Omni scenario/contrast matrix execution)

## Overview
This package validates `features_export` end-to-end against real runs. Phase 1 completed on `clogging-starch/disturbed9002-wbt-mofe`. Phase 2 reopens the package to validate Omni scenarios/contrasts behavior on `walk-in-obsessive-compulsive/disturbed9002_wbt` (single OFE context). It remains a manual-plus-automated quality gate focused on output correctness, format integrity, CRS behavior, Unitizer-driven units, temporal selection behavior, and identity-key normalization.

The package now uses two anchors:
- Phase 1 anchor: roads-capable run (`clogging-starch/disturbed9002-wbt-mofe`).
- Phase 2 anchor: Omni-inclusive single-OFE run (`walk-in-obsessive-compulsive/disturbed9002_wbt`).

## Objectives
- Establish two execution gates:
  - `Gate-1` fast sentinel preflight (one representative case per format + core negatives).
  - `Gate-2` full matrix execution after `Gate-1` is clean.
- Verify every supported `features_export` format writes the correct payload type inside the zip artifact.
- Verify row/feature/column counts and identity columns (`topaz_id`, `wepp_id`) are correct and stable.
- Verify row-domain oracles by reconciling exported key domains with canonical source carrier domains (not only fixed expected counts).
- Verify CRS behavior (`wgs`, `utm`) across spatial formats and no-op CRS handling for tabular formats.
- Verify units behavior (`project`, `si`, `english`) with Unitizer preferences, and fix UI text from `Unitzer Selections` to `Unitizer Selections`.
- Verify units numerically with deterministic conversion checks/tolerances on selected fields.
- Verify temporal controls (`annual_average`, `yearly`, `event`, year selection options) across single- and multi-layer requests including atemporal+temporal mixes.
- Verify cache behavior by replaying identical payloads and asserting `cache_hit`, `source_job_id`, and stable artifact mapping.
- Expand negative-path coverage for invalid payload/selector combinations.
- Capture manual sanity evidence first, then codify deterministic pytest coverage.

## Scope

### Included
- Live-run matrix execution on `runid=clogging-starch`, `config=disturbed9002-wbt-mofe`.
- Format validation for `geojson`, `geoparquet`, `parquet`, `csv`, `kmz`, `geopackage`, `geodatabase`.
- Scope validation including roads (`output_scopes=["baseline", "roads"]`) for scope-aware layers.
- Gate-based execution model (`Gate-1` sentinel, `Gate-2` full matrix).
- Manifest-vs-artifact consistency checks.
- Identity normalization and missing-data irregularity checks, including strict tabular identity completeness.
- Cache-hit replay checks for deterministic artifact reuse contracts.
- Format-specific structural probes (`ogrinfo`/GDAL, parquet metadata, kmz/kml members).
- File-level CRS probes for each spatial format.
- Expanded negative-path payload validation set.
- UI regression checks for:
  - `Unitizer Selections` label copy,
  - no unexpected run-page reload on temporal changes,
  - export-button unlock behavior after completed export and settings changes.
- Manual artifact sanity review (QGIS / ogrinfo / parquet tools) with recorded evidence.
- Follow-up pytest/Jest additions for stable matrix subsets.
- Omni scenario and Omni contrast export validation on `walk-in-obsessive-compulsive/disturbed9002_wbt`.
- Omni selector-contract coverage where scenario vs contrast families are validated independently with single-OFE geometry.

### Explicitly Out of Scope
- New export families or catalog redesign.
- SWAT and AgFields broad parity validation (can be follow-up package).
- Performance optimization work beyond basic runtime capture.

## Stakeholders
- **Primary**: WEPPcloud operators using Features Export artifacts.
- **Reviewers**: NoDb/features_export maintainers.
- **Informed**: UI/controller maintainers and RQ-engine maintainers.

## Success Criteria
- [x] `Gate-1` sentinel suite passes before running `Gate-2`.
- [x] All matrix cases complete with pass/fail outcomes recorded in package artifacts.
- [x] Any discovered defects are fixed and linked from tracker notes.
- [x] Manual sanity checks for each format family are documented with evidence.
- [x] Automated tests are added for stable/critical matrix slices.
- [x] UI copy updated to `Unitizer Selections` and covered by test.
- [x] Cache-hit replay contract is verified and covered by tests.
- [x] Negative-path contract checks are verified and covered by tests.
- [x] Closeout includes reproducible commands and acceptance summary.
- [x] Omni scenario sentinel cases pass on `walk-in-obsessive-compulsive/disturbed9002_wbt`.
- [x] Omni contrast sentinel cases pass on `walk-in-obsessive-compulsive/disturbed9002_wbt`.
- [x] Omni scenario/contrast matrix evidence is appended and summarized in package artifacts.

## Dependencies

### Prerequisites
- Existing package: `docs/work-packages/20260328_features_export_profiles_provenance_zip/`
- Live run path: `/wc1/runs/cl/clogging-starch`
- Reopen live run path: `/wc1/runs/wa/walk-in-obsessive-compulsive`
- Features Export spec: `wepppy/nodb/mods/features_export/specification.md`

### Blocks
- Lock-in of long-term Features Export regression suite for release readiness.

## Related Packages
- **Depends on**: [20260328_features_export_profiles_provenance_zip](../20260328_features_export_profiles_provenance_zip/package.md)
- **Related**: [20260327_roads_peridot_trace_core](../20260327_roads_peridot_trace_core/package.md)
- **Follow-up**: dedicated SWAT/Omni/AgFields matrix package if needed.
- **Supersedes prior follow-up**: Omni coverage is now executed in this reopened package (Phase 2).

## Timeline Estimate
- **Expected duration**: 2-4 focused sessions (completed).
- **Complexity**: High.
- **Risk level**: Medium-High (data correctness and contract confidence gate).

## Full Test Matrix

### Anchor Inputs
- Run: `clogging-starch/disturbed9002-wbt-mofe`
- Canonical atemporal layers: `watershed.subcatchments`, `watershed.channels`, `landuse.dominant`, `soils.dominant`
- Canonical scope-aware layers: `wepp.summary.hillslopes`, `wepp.summary.channels`
- Canonical temporal layers:
  - `wepp.interchange.loss_all_years_hill` (`yearly`)
  - `wepp.temporal.events` (`event`)
  - `wepp.interchange.hill_pass` (`annual_average|yearly|event` mixed-mode anchor)

### Execution Gates
- `Gate-1` (sentinel): one representative successful case per format (7), plus contract-critical negative cases (mixed temporal long, missing event selector payload, invalid tabular object).
- `Gate-2` (full): execute matrix groups A-E, then expansion groups F-G only after A-E are clean.

### Matrix Groups

| Group | Cases | Runs | Request Dimensions | Required Assertions |
|---|---:|---:|---|---|
| A1 Spatial format contract | 5 formats x 2 CRS x 3 units | 30 | `format in {geojson, geoparquet, kmz, geopackage, geodatabase}`; atemporal single-layer | Correct member extension/signature, manifest counts match artifact, CRS matches request, identity columns present |
| A2 Tabular format contract | 2 formats x 2 CRS x 3 units | 12 | `format in {parquet, csv}`; atemporal single-layer | Geometry absent, CRS request accepted and treated as no-op, both `topaz_id` and `wepp_id` non-null per row |
| B1 Year selection variants | 5 year selectors | 5 | `format=parquet`, `temporal.mode=yearly`, layer=`wepp.interchange.loss_all_years_hill`, year selectors: `all`, `exclude_first`, `exclude_first_two`, `exclude_first_five`, `custom` | Year-column expansion or row-temporal layout matches selector; deterministic row domain; no duplicate key-year slices |
| B2 Yearly multi-layer | 1 | 1 | `format=parquet`, yearly, layers=`loss_all_years_hill + loss_all_years_channel` | Both carriers emitted, counts align to carrier keys, schema/column expectations valid |
| B3 Event selector variants | 2 | 2 | `format=parquet`, `temporal.mode=event`, layer=`wepp.temporal.events`, selector `date` and `return_period` | Correct temporal selector columns/tokens, deterministic event pivot behavior |
| B4 Mixed temporal wide | 1 | 1 | `format=parquet`, `tabular.temporal_layout=wide`, layers include one `event` and one `yearly` | Success with deterministic per-layer shaping |
| B5 Mixed temporal long negative | 1 | 1 | `format=parquet`, `tabular.temporal_layout=long`, mixed `event` + `yearly` | Request rejected with 400 and contract-consistent validation error |
| B6 Atemporal + temporal combinations | 2 | 2 | `format=parquet`, combo sets: (atemporal + yearly), (atemporal + event) | Combined export remains key-normalized, no Cartesian growth, expected warnings only |
| C1 Spatial yearly coverage | 5 formats | 5 | Spatial formats with yearly layer set | CRS + geometry + yearly shaping valid in each format |
| C2 Spatial event coverage | 5 formats | 5 | Spatial formats with event layer set | Event selector behavior preserved in each format |
| C3 Spatial mixed coverage | 5 formats | 5 | Spatial formats with atemporal + yearly layers | Mixed-layer export valid and normalized |
| D1 Scope baseline+roads | 7 formats | 7 | all formats; layers=`wepp.summary.hillslopes + wepp.summary.channels`; `output_scopes=[baseline,roads]` | Scope-specific outputs present and named correctly; counts align by carrier scope |
| D2 Tabular concatenate scope | 2 formats | 2 | `format in {parquet,csv}`, `tabular.concatenate_tables=true`, baseline+roads | `output_scope` provenance column present; expected concatenated file count (hillslopes/channels) |
| E1 Data irregularity audit | all successful runs | 77 | post-run artifact scan | No null-only identity columns, no rows with both ids missing, no unresolved many-to-many duplication symptoms |
| E2 Manifest integrity audit | all successful runs | 77 | post-run artifact scan | `manifest.json` row/feature/column metadata exactly matches payload files |
| F1 Cache-hit replay contract | 7 formats | 7 | repeat identical successful payload per format | 2nd run returns `cache_hit=true`, stable artifact mapping, valid `source_job_id`, valid download |
| F2 Negative-path payload contract | 8 | 8 | invalid layer id, invalid `tabular` shape, mixed long event+yearly, missing event selector payload, invalid CRS token, invalid temporal mode, invalid year-selection custom payload, invalid scope token | 400/404/409 response code and structured error contract match spec |
| G1 Units numeric oracle checks | 4 | 4 | selected conversions across `project`, `si`, `english` on stable fields | conversion magnitudes/tolerances match expected unit transforms |
| G2 UI regression checks | Jest/route tests | 0 export jobs | copy + behavior regression checks | label copy, no reload on temporal change, unlock behavior remain correct |

**Planned job count**:
- Core (`A-E`): 78 jobs (77 successful + 1 negative).
- Expansion (`F-G`): 19 jobs (11 successful + 8 negative) plus UI regression test runs.
- Total planned export job executions: **97**.

**Phase 2 Omni extension**:
- `H1`: Omni scenario sentinel across all formats (7).
- `H2`: Omni contrast sentinel across all formats (7).
- `H3`: Omni selector validation negatives (4).
- `H4`: Omni scope/temporal compatibility assertions (8).
- Total Phase 2 Omni executions: **26**.

### Cross-Run Assertions (every successful case)
- Artifact is a zip and includes required bundle members (`manifest.json`, `profile.yml`, `profiles/post-wepp.yml`, `profiles/prep-details.yml`, `README.md`).
- Payload member format matches request token.
- File count follows contract:
  - Single-layer formats: one payload file per resolved layer.
  - Multi-layer formats: one container payload member.
- Row and feature counts match manifest for each emitted layer.
- Output columns include canonical identity columns first: `topaz_id`, `wepp_id`.
- No row has both identity columns missing.
- Tabular exports (`parquet`, `csv`) have non-null `topaz_id` and `wepp_id` for every row (watershed fallback requirement).
- Per-temporal-mode row-domain checks:
  - atemporal: one row per effective key,
  - yearly: one row per `{key, year}` (or equivalent wide pivot domain),
  - event: one row per `{key, event_token}` (or equivalent wide pivot domain).
- Exported key-domain reconciliation against canonical source carrier domains (watershed/wepp source oracles).
- Null-profile scan flags any fully-null non-optional column as failure unless explicitly justified in matrix notes.

## References
- `wepppy/nodb/mods/features_export/specification.md` - authoritative contract.
- `wepppy/nodb/mods/features_export/layer_catalog.yaml` - layer ids, labels, temporal support.
- `wepppy/weppcloud/controllers_js/features_export.js` - run-page control behavior.
- `wepppy/weppcloud/templates/controls/features_export_pure.htm` - UI labels and controls.
- `/wc1/runs/cl/clogging-starch` - live run root.

## Deliverables
- Matrix execution log with case-by-case outcomes.
- Manual sanity evidence files under `artifacts/`.
- Code fixes for discovered defects.
- Automated regression tests for locked-in matrix slices.
- Updated docs/tracker/closure summary.

## Follow-up Work
- Extend same matrix harness to one SWAT-inclusive run.
- Add nightly matrix subset in CI for format/identity regression detection.

## Closure Notes
Phase 1 closed on 2026-03-29 after full live-run matrix execution against:
- `runid=clogging-starch`
- `config=disturbed9002-wbt-mofe`

Final outcomes:
- Matrix execution completed in strict order (`Gate-1` -> `Gate-2` -> `F-G`) with final pass counts:
  - `Gate-1`: 10/10
  - `Gate-2`: 80/80
  - `F-G`: 20/20
  - Total results rows: 110/110 passed
- All required behavior contracts validated:
  - 7-format payload/member signatures
  - spatial CRS file-level checks (`wgs`/`utm`) + tabular CRS no-op
  - units conversion checks (`project`/`si`/`english`) with numeric oracles
  - temporal selectors/year-selection variants and mixed long-layout rejection
  - identity completeness (`topaz_id`, `wepp_id`) and key-domain reconciliation
  - cache replay contract (`cache_hit`, `source_job_id`, stable artifact mapping)
  - UI regressions (Unitizer copy, temporal-change behavior, export-button unlock)

Evidence artifacts:
- `docs/work-packages/20260329_features_export_live_run_matrix/artifacts/matrix_results.jsonl`
- `docs/work-packages/20260329_features_export_live_run_matrix/artifacts/manual_sanity_notes.md`
- `docs/work-packages/20260329_features_export_live_run_matrix/artifacts/defect_log.md`

Validation commands executed:
- `wctl run-pytest tests/nodb/mods/test_features_export_service.py --maxfail=1`
- `wctl run-pytest tests/microservices/test_rq_engine_features_export_routes.py --maxfail=1`
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1`
- `wctl run-npm test -- features_export`

Phase 2 closure note (2026-03-29):
- Omni scenario/contrast matrix executed on:
  - `runid=walk-in-obsessive-compulsive`
  - `config=disturbed9002_wbt`
- Phase 2 pass counts:
  - `H1`: 7/7
  - `H2`: 7/7
  - `H3`: 4/4
  - `H4`: 8/8
  - Total: 26/26
- Shared matrix ledger now includes Phase 1 + Phase 2:
  - `docs/work-packages/20260329_features_export_live_run_matrix/artifacts/matrix_results.jsonl` (136 rows, 0 failures).
- Phase 2 artifacts:
  - `docs/work-packages/20260329_features_export_live_run_matrix/artifacts/manual_sanity_notes_phase2_omni.md`
  - `docs/work-packages/20260329_features_export_live_run_matrix/artifacts/defect_log_phase2_omni.md`
