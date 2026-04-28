# Geneva NoDb Mod Specification

Status: Implemented Baseline (WP-00..WP-10 complete; WP-11 follow-on backlog)  
Last Updated: 2026-04-23  
Owner: WEPPpy NoDb hydrology stack  
Scope: Event runoff hydrograph modeling for BAER-style post-fire workflows using RMRS-GTR-334-aligned Curve Number (CN) plus unit hydrograph methods.

Name note: `geneva` is the project codename selected in memory of Richard H. Hawkins (passed January 2026).

## 1. Purpose

Geneva provides a run-scoped NoDb workflow for event rainfall-runoff analysis with:

- raster-derived HRUs,
- CN rainfall excess,
- hydrograph generation,
- batch execution over a frequency panel,
- query/report payloads for interactive storm exploration,
- auditable run artifacts under `<run>/geneva/`.

This document now records the **current shipped behavior**. Historical design intent is retained in deferred sections for future implementation work.

## 2. Implementation Snapshot (2026-04-23)

| Area | Current State | Notes |
| --- | --- | --- |
| NoDb facade + collaborators | Implemented | `wepppy/nodb/mods/geneva/` |
| Rust kernel entrypoints | Implemented | `geneva_prepare_hrus`, `geneva_build_frequency_panel`, `geneva_run_batch` |
| `geneva_validate_uh` | Stub | Exposed but scaffold-only response |
| WBT-only guardrail | Implemented | Hard fail with `unsupported_backend` |
| US-only guardrail | Implemented | Broad US envelope + NLCD/SSURGO compatibility checks |
| Run-scoped CN-table lifecycle | Implemented | Init/reset/modify/audit with optimistic concurrency |
| CN-table consumption in HRU CN assignment | Implemented | `prepare_hrus` resolves persisted HRU CN fields from run-scoped `geneva/data/cn_table.csv` before writing `hru_table.parquet`; missing exact rows fall back explicitly |
| Frequency panel matrix + unavailable reasons | Implemented | CLIGEN always attempted; NOAA optional |
| Runtime batch hyetograph distribution | **Uniform (interim)** | `run_batch` currently builds linear cumulative rainfall from depth/duration |
| NEH4 Type B hyetograph kernel module | Implemented in Rust | Not yet wired into Python `run_batch` orchestration path |
| Flask routes + RQ tasks | Implemented | Single `geneva_bp.py` module |
| rq-engine Geneva API/state | Implemented | Includes chained `run-workflow` endpoint and revisioned state payload |
| Interactive summary query/report payload | Implemented | Marker/table selection contract live |

## 3. Scope and Non-Goals

In scope (v1 baseline):

- US-only workflow assumptions (NLCD + NRCS-compatible HSG source expectations).
- HRU preparation from `bound.tif`, landuse, `hydgrpdcd`, optional burn severity.
- Frequency-panel generation from CLIGEN and optional NOAA Atlas 14 artifacts.
- Batch storm execution with per-storm artifacts and batch summary.
- Interactive summary query/report payloads.
- CN-table editing workflow with audit trail and optimistic concurrency.

Out of scope (still deferred):

- Non-US taxonomy packs.
- Snowmelt and rain-on-snow process representation.
- Channel hydraulics/kinematic-wave routing and reservoir routing.
- Mixed rainfall-excess process families in one run.

## 4. Scientific Basis and Conformance

Primary references remain:

- RMRS-GTR-334 (Wildcat5 manual),
- NRCS NEH 630 hydrology references,
- SCS/TR-55 method family references.

Conformance posture:

- RMRS method family and workflow sequencing remain normative.
- Where implementation differs, deviations are documented explicitly below.

### 4.1 Conformance Deviations (Retained + Current)

| Deviation ID | Section | Description | Status |
| --- | --- | --- | --- |
| DEV-001 | HRU collapse | Minimum HRU area floor `2 ha` and deterministic collapse | Implemented |
| DEV-002 | CN seeding | Non-forest/non-shrub burn CN rows remain static in seed defaults | Implemented (table workflow) |
| DEV-003 | Frequency panel | Duration interpolation disabled for panel materialization | Implemented |
| DEV-004 | Climate sourcing | Dual-source panel strategy (CLIGEN always attempted; NOAA optional) | Implemented |
| DEV-005 | CN resolution | Runtime HRU CN now resolves from run-scoped `cn_table.csv` at `prepare_hrus` persistence time; missing exact lookup rows fall back explicitly to the kernel proxy estimator | Implemented behavior |
| DEV-006 | Storm construction | Python `run_batch` currently builds uniform hyetograph from depth/duration | Active gap |
| DEV-007 | Default HSG derivation | Dominant-soil derivation path is not implemented; only explicit `default_hsg_code` is used | Active gap |
| DEV-008 | Enable/disable semantics | `enabled` remains effectively true when mod is present (membership-driven) | Implemented behavior |
| DEV-009 | Collapse failure policy | No compatible recipient does not fail run; donor HRU is retained with warning | Implemented behavior |

### 4.2 Wildcat5 Source Artifacts and Legal Posture

Wildcat5 workbook/macro references remain staged under:

- `wepppy/nodb/mods/geneva/resources/Wildcat5/`
- extracted VBA modules under `.../extracted_macros/wildcat5dec072015-64bits/`

Policy remains:

- do not execute VBA at runtime,
- port equations/algorithms into owned Python/Rust code,
- keep parity/unit tests around ported logic.

## 5. Runtime Architecture (Current)

### 5.1 Python (`wepppy`) orchestration

Geneva NoDb facade:

- `wepppy/nodb/mods/geneva/geneva.py`

Collaborators:

- `config_service.py`
- `hsg_assignment_service.py`
- `hru_preparation_service.py`
- `frequency_panel_service.py`
- `batch_run_service.py`
- `results_service.py`
- `report_payload_service.py`
- `cn_table_service.py`
- `artifact_io.py`
- `kernel_gateway.py`

### 5.2 Rust (`wepppyo3`) kernel boundary

PyO3 adapter entrypoints:

- `geneva_prepare_hrus`
- `geneva_build_frequency_panel`
- `geneva_run_batch`
- `geneva_validate_uh` (stub)

Core crate modules:

- `hru.rs`
- `frequency_panel.rs`
- `cn.rs`
- `uh.rs`
- `convolution.rs`
- `hyetograph.rs` (implemented but not currently wired from Python `run_batch`)

## 6. Guardrails (Hard Requirements)

### 6.1 WBT-only

Geneva rejects non-WBT delineations with:

- code: `unsupported_backend`
- message: `Geneva requires the WBT delineation backend.`

### 6.2 US-only / dataset compatibility

Geneva rejects unsupported domain conditions with:

- code: `unsupported_domain`
- message: `Geneva v1 is US-only and requires NLCD + US NRCS-compatible HSG inputs.`

Current checks:

- US envelope: `-179.5 <= lng <= -64.0` and `17.0 <= lat <= 72.5`.
- NLCD compatibility by `landuse.nlcd_db`/`landuse.lc_fn` containing `nlcd`.
- HSG compatibility by `soils.ssurgo_db`/`soils.ssurgo_fn` containing `ssurgo` or `hydgrpdcd`.

### 6.3 Enablement semantics

Current behavior is membership-driven:

- Geneva is auto-enabled on initialization.
- `set_enabled(false)` does not disable runtime execution; effective `enabled` remains `true`.
- Config payload still contains `enabled`, but it tracks effective state, not a hard off switch.

## 7. Configuration Contract (Current)

Schema version: `1`

Current config fields:

- `enabled` (effective true while mod is present)
- `lambda_mode`: `0.20 | 0.05` (default `0.20`)
- `uh_method`: `scs_triangular | scs_curvilinear` (default `scs_triangular`)
- `default_hsg_code`: `1 | 2 | 3 | 4 | null` (integer or null only)
- `unresolved_hsg_policy`: `error | assume_d` (default `assume_d`)
- `strict_burn_nodata`: boolean (default `false`)
- `allow_cross_hsg_merge`: boolean (default `false`)
- `hydrophobic_forest_high`: boolean (default `true`)
- `hydrophobic_forest_moderate`: boolean (default `false`)
- `hydrophobic_shrub_high`: boolean (default `true`)
- `hydrophobic_shrub_moderate`: boolean (default `false`)
- `min_hru_area_ha`: numeric `>= 2.0` (default `2.0`)

Validation highlights:

- boolean fields reject string booleans,
- `default_hsg_code` rejects string numerals,
- `min_hru_area_ha < 2.0` is rejected,
- config updates clear runtime results/status caches when values change after prepared/running/completed states.

## 8. Input Contract and CN-Table Workflow

### 8.1 HRU prepare input references

Required raster references:

- `bound_tif`
- `landuse_tif`
- `hydgrpdcd_tif`

Optional:

- `burn_severity_tif`

Current source resolution behavior:

- required refs default from watershed/landuse/soils NoDb objects,
- optional burn ref can be auto-discovered from `Disturbed` (`sbs_4class_path`, then `disturbed_cropped`),
- auto-discovered Disturbed burn refs are materialized as
  `geneva/inputs/burn_severity_4class.tif` on the canonical `bound.tif`
  grid with nearest-neighbor reprojection before the kernel request,
- explicit `burn_severity_tif` overrides are passed through unchanged so
  callers can supply a deliberate raster contract,
- required paths must exist or request fails,
- missing optional burn path is dropped silently (optional-only behavior).

### 8.2 Run-scoped CN table (`geneva/data/cn_table.csv`)

Current implemented workflow:

- initialized from module seed: `wepppy/nodb/mods/geneva/data/geneva_cn_table_us_v1_seed.csv`
- recreated when missing,
- reset endpoint restores seed deterministically,
- optimistic concurrency required on modify (`if_match_sha256`),
- append-only audit log at `geneva/data/cn_table_audit.jsonl`.

Current canonical persisted columns:

- `nlcd_class`
- `nlcd_label`
- `hsg`
- `burn_severity`
- `hydrophobic`
- `cn_arc_ii`
- `antecedent_condition_source`
- `source`
- `notes`

Migration behavior:

- legacy files missing `antecedent_condition_source` are migrated to schema v1 with default `arc_ii_seed`.

Modify behavior constraints:

- non-empty row list required,
- duplicate composite keys rejected,
- payload must include all existing keys (row deletions rejected),
- accepts body token and/or `X-If-Match-Sha256` header token.

### 8.3 Runtime CN-table consumption

`cn_table.csv` is the active runtime source for persisted HRU CN values.

- `GenevaHruPreparationService` resolves HRU `cn_arc_ii` by exact lookup on:
  - `nlcd_class`
  - `hsg`
  - `burn_severity`
  - `hydrophobic`
- The resolved CN is written into `geneva/hru_table.parquet`, and downstream `run_batch` uses that persisted parquet.
- Editing `geneva/data/cn_table.csv` does not retroactively mutate an existing `hru_table.parquet`; rerun `prepare_hrus` to regenerate the artifact.
- `prepare_hrus` now invalidates its cached summary when the CN-table hash changes, so rerunning the task after a CN-table edit refreshes `hru_table.parquet` even when `force_rebuild=false`.
- When an exact CN-table row is missing, Geneva keeps the kernel-estimated CN for that HRU and marks the persisted row with:
  - `cn_source = "geneva_proxy_cn_v1_fallback_missing_row"`
  - warning `cn_table_missing_exact_row`

## 9. HRU Preparation Contract (Current)

Entry: `geneva_prepare_hrus` kernel call via `GenevaHruPreparationService`.

### 9.1 Kernel request fields

Python sends:

- `kernel_schema_version = 1`
- raster refs (`bound_tif`, `landuse_tif`, `hydgrpdcd_tif`, optional `burn_severity_tif`)
- `default_hsg_code` (user override only)
- `default_hsg_derivation` (currently `user_override` or null)
- `unresolved_hsg_policy`
- `strict_burn_nodata`
- `allow_cross_hsg_merge`
- `min_hru_area_ha`
- hydrophobic toggles

### 9.2 HRU key and burn/hydrophobic rules

Kernel HRU key dimensions:

- `landuse_class`
- `hsg_group`
- `burn_severity_class`
- `hydrophobic_class`
- `is_water`

Burn mapping:

- `0 -> unburned`
- `1 -> low`
- `2 -> moderate`
- `3 -> high`
- nodata in-bound:
  - error when `strict_burn_nodata=true`,
  - mapped to `unburned` with warning otherwise.

Hydrophobic toggles:

- forest classes `41,42,43` use forest toggles for moderate/high burn,
- shrub class `52` uses shrub toggles for moderate/high burn,
- all other combinations resolve to `false`.

### 9.3 HSG handling

Hydgrpdcd mapping domain:

- `1->A`, `2->B`, `3->C`, `4->D`
- `0` or nodata => unresolved
- `5/6/7` and other unexpected codes => warning + unresolved path

Fallback chain:

1. coded lookup
2. `default_hsg_code` (if provided)
3. unresolved policy:
  - `error` => fail
  - `assume_d` => coerce to D with warning

### 9.4 Minimum HRU area collapse

Current enforced floor:

- `min_hru_area_ha >= 2.0`

Collapse compatibility:

- must match `is_water`, `landuse`, `burn`, `hydrophobic`
- must match `hsg` unless `allow_cross_hsg_merge=true`

Recipient selection order:

1. smallest `abs(delta_cn_arc_ii)`
2. largest recipient area
3. lexical `hru_id`

Current no-recipient behavior:

- donor HRU is retained (warning `collapse_no_compatible_recipient`),
- run does not fail solely because no compatible recipient exists.

### 9.5 Runtime CN resolution path

Current runtime path:

- kernel still computes a provisional CN via `estimate_cn_arc_ii(...)`,
- Python `prepare_hrus` replaces persisted HRU CN fields from the run-scoped CN table when an exact lookup row exists,
- persisted table-backed rows use `cn_source = "geneva_cn_table_csv_v1"`,
- persisted fallback rows use `cn_source = "geneva_proxy_cn_v1_fallback_missing_row"`.

Current provisional kernel estimator:

- base CN by NLCD class (`11=100`, `41-43=55`, `52=65`, `71=68`, `81=74`, `82=78`, else `75`)
- HSG adjustment (`A=0`, `B=+7`, `C=+14`, `D=+21`)
- burn adjustment (`unburned=0`, `low=+2`, `moderate=+5`, `high=+8`)
- hydrophobic adjustment (`+6` when `hydrophobic_class=true`)
- final clamp: `[30, 100]`
- `cn_lambda_005` derived with RMRS-style transform and cap behavior for `cn_arc_ii > 98.5`.

### 9.6 HRU outputs and persisted artifacts

Persisted artifact:

- `geneva/hru_table.parquet`

Persisted columns:

- `hru_id`
- `area_m2`
- `area_ac`
- `area_fraction`
- `landuse_class`
- `hsg_group`
- `burn_severity_class`
- `hydrophobic_class`
- `is_water`
- `cn_arc_ii`
- `cn_lambda_020`
- `cn_lambda_005`
- `antecedent_condition_source`
- `cn_source`
- `hsg_source`
- `collapsed_from_hru_ids`
- `warnings`

Persisted summary:

- `geneva/hru_prepare_summary.json`
- current summary includes `hru_count`, `hru_area_total_m2`, `hru_area_total_acres`, `hsg_provenance_counts`, warnings, refs, artifact relpaths, and CN-table lookup metadata (`lookup_sha256`, runtime source, fallback count).

## 10. Frequency Panel Contract (Current)

Entry: `geneva_build_frequency_panel`.

Defaults:

- durations: `[5,10,15,30,60,120,180,360,720,1440]`
- ARI years: `[1,2,5,10,25,50,100]`
- `distribution_type = neh4_type_b`
- `allow_duration_interpolation = false`

Sources:

- CLIGEN default: `climate/wepp_cli_pds_mean_metric.csv`
- NOAA default: `climate/atlas14_intensity_pds_mean_metric.csv`

CLIGEN materialization:

- `Storm depth (mm)` + `Storm duration (hours)` rows produce the duration/ARI cells they describe.
- Available CLIGEN intensity rows such as `10-min intensity (mm/hour)`, `15-min intensity (mm/hour)`, `30-min intensity (mm/hour)`, and `60-min intensity (mm/hour)` also produce duration/ARI cells.
- Intensity-derived cell depth is `intensity_mm_per_hr * duration_minutes / 60`.
- Existing depth/duration cells take precedence if an intensity row would duplicate the same `(duration_minutes, ari_years)` key.

CLIGEN normalization shim (current implementation detail):

- if CLIGEN file uses `Precipitation depth (mm):` row label, service writes normalized copy with `Storm depth (mm):` to:
  - `geneva/normalized_sources/wepp_cli_pds_mean_metric_kernel.csv`
- normalization preserves CLIGEN intensity rows so they remain available to the kernel.

Output invariants:

- persisted to `geneva/frequency_panel.json`
- cell `availability` is `available|unavailable`
- `reason_code` must be null when available
- unavailable reason codes are:
  - `duration_unavailable`
  - `ari_unavailable`
  - `source_missing`
- cells sorted deterministically by `(datasource_id, duration_minutes, ari_years, storm_id)`.

## 11. Batch Run and Hydrograph Contract (Current)

Entry: `geneva_run_batch` (Python orchestrates per-storm kernel calls).

### 11.1 Request validation

`schema_version=1` and:

- `event_filter.datasource_ids` optional list of `cligen_freq|noaa14_pds`
- `event_filter.durations_minutes` optional positive int list
- `event_filter.ari_years` optional positive int list
- `hyetograph.distribution_type` must be `neh4_type_b`
- `hyetograph.time_step_minutes > 0`
- exactly one of:
  - `runoff_model.tc_hours`, or
  - `runoff_model.timing_method` (`kirpich|kent|simas`)

Prerequisites:

- `geneva/frequency_panel.json` must exist
- `geneva/hru_table.parquet` must exist and be non-empty

### 11.2 Current storm construction in Python

Current runtime behavior uses **uniform cumulative rainfall** per storm cell:

- uses selected cell `duration_minutes` and `depth_mm`
- builds linear cumulative series from `0` to `depth_mm`
- uses configured `time_step_minutes`

Timing fallback when `timing_method` is used:

- `kirpich`: `tc = clamp(0.6 * sqrt(area_km2), 0.25, 6.0)`
- `kent`: `tc = clamp(0.8 * sqrt(area_km2), 0.25, 6.0)`
- `simas`: `tc = clamp(1.0 * sqrt(area_km2), 0.25, 6.0)`

### 11.3 Kernel run-batch behavior

Kernel receives per-storm payload with:

- `lambda_mode`, `uh_method`, `tc_hours`
- `time_minutes`, `cumulative_rainfall_mm`
- HRU rows (`hru_id`, `area_m2`, `cn_lambda_020`)

Kernel computes:

- CN excess (`0.20` and `0.05` forms with 98.5 cap behavior)
- composite excess
- unit hydrograph (`scs_triangular|scs_curvilinear`)
- hydrograph, summary metrics, diagnostics

### 11.4 Persisted storm and batch artifacts

Per completed storm:

- `geneva/storms/<storm_id>/hyetograph.parquet`
- `geneva/storms/<storm_id>/excess_hyetograph.parquet`
- `geneva/storms/<storm_id>/hydrograph.parquet`
- `geneva/storms/<storm_id>/summary.json`

Batch-level:

- `geneva/storm_inputs.json`
- `geneva/batch_summary.json`

Run status aggregation:

- `failed` if any available storm fails
- else `completed_with_gaps` if unavailable panel cells are present
- else `completed`

### 11.5 Watershed scale warnings

Thresholds:

- warning: `>25 km2`
- severe: `>100 km2`
- extreme: `>250 km2`

Warning payload includes:

- code `point_rainfall_assumption`
- area values (`km2`, `mi2`, `acres`)
- threshold details
- `arf_method=constant_1.0`, `arf_value=1.0`, `uniform_rainfall_assumed=true`

### 11.6 Planned storm-shape implementation contract

Status: specified for `docs/work-packages/20260428_geneva_storm_shape_control/`; not yet implemented in runtime.

The planned Geneva `Storm Shape` control has six closed enum values:

| ID | Label | Implementation source |
| --- | --- | --- |
| `uniform` | Uniform | Linear cumulative event rainfall. |
| `neh4_type_b` | NEH-4 B | Existing Geneva Rust normalized Type B ordinates. |
| `type_i` | Type I | NRCS legacy 24-hour cumulative mass curve generated from WinTR-20 output. |
| `type_ia` | Type IA | NRCS legacy 24-hour cumulative mass curve generated from WinTR-20 output. |
| `type_ii` | Type II | NRCS legacy 24-hour cumulative mass curve generated from WinTR-20 output. |
| `type_iii` | Type III | NRCS legacy 24-hour cumulative mass curve generated from WinTR-20 output. |

Type I/IA/II/III source and provenance requirements:

- Authoritative technical basis: NRCS Title 210, National Engineering Handbook, Part 630, Chapter 4, "Storm Rainfall Depth and Distribution" (Aug 2019).
- Implementation source of truth: checked-in WinTR-20-derived artifacts under `/workdir/wepppyo3/geneva_core/resources/`:
  - raw WinTR-20 distribution output: `nrcs_legacy_24h_distributions.wintr20_raw.txt`
  - normalized 24-hour cumulative ordinate table: `nrcs_legacy_24h_distributions.csv`
  - provenance metadata: `nrcs_legacy_24h_distributions.metadata.json`
- Required metadata fields: WinTR-20 version, generation date, `raw_output_filename`, `raw_output_sha256`, `export_mode`, `time_increment_hours`, `decimal_precision`, `rounding_policy`, `post_processing_steps`, `normalized_csv_sha256`, row count, and monotonic endpoint checks.
- Source table time increment must be recorded. A 0.1-hour source increment is acceptable only if validation against NEH Chapter 4 Figure 4-31 passes; otherwise regenerate/export a finer source table before implementation.
- Type II embedded-duration ratios must match NEH Chapter 4 Figure 4-31 within absolute fraction tolerance `<= 0.003`. Tolerance relaxation requires a review artifact explaining why the source export, interpolation, and validation target are still authoritative.
- Secondary web tables are not authoritative implementation sources. They may be used only for sanity checks.

Type I/IA/II/III event-duration algorithm:

1. Treat the 24-hour table as a piecewise-linear cumulative mass curve `F(t)` over `0 <= t <= 24` hours.
2. Validate `0 < duration_minutes <= 1440`, `depth_mm > 0`, and `time_step_minutes > 0`.
3. Convert event duration to hours, `d = duration_minutes / 60`.
4. For `d == 24`, use the full source curve.
5. For `d < 24`, find the window start `a` in `[0, 24 - d]` that maximizes `F(a + d) - F(a)`.
6. Candidate starts must include source table times and source table times minus `d`, clipped to `[0, 24 - d]`.
7. If candidates tie within tolerance, choose the candidate closest to `12 - d / 2`; if still tied, choose the earliest.
8. Let `r = F(a + d) - F(a)`. Fail if `r <= 0`.
9. Build the output time vector with `0` and exact `duration_minutes` endpoints. Intermediate points are regular `time_step_minutes` multiples strictly inside the duration; if `time_step_minutes >= duration_minutes`, output only the two endpoints. If duration is not evenly divisible by the step, the final interval is shorter.
10. For output time `t` in the event, compute `event_fraction(t) = (F(a + t_hours) - F(a)) / r`.
11. Force the first and final output points to `0.0` and `1.0`, enforce monotonicity within tolerance, and set `cumulative_rainfall_mm = event_fraction(t) * depth_mm`.

This is intentionally an embedded-window extraction, not full-curve compression. Geneva frequency-panel cells provide depth for the selected duration; for example, a 60-minute event uses the selected 60-minute depth. The Type II 60-minute hyetograph therefore comes from the maximum embedded 60-minute window of the 24-hour Type II curve, normalized to the selected 60-minute depth.

Type I/IA/II/III output metadata must include:

- `source_distribution_type`
- `source_curve_duration_hours=24`
- `extraction_start_hours`
- `extraction_end_hours`
- `extraction_ratio_to_24h`
- `event_depth_is_duration_depth=true`
- `source_table_sha256`

NRCS cautions that legacy Type I/IA/II/III regional distributions can be inconsistent with NOAA Atlas 14 site-specific ratios. Geneva must therefore expose these shapes as explicit user-selected assumptions, not as an automatic regional recommendation.

## 12. State, Results, Query, and Report Contracts (Current)

### 12.1 Geneva lifecycle states

- `idle`
- `prepared`
- `running`
- `completed`
- `completed_with_gaps`
- `failed`

### 12.2 Status and results payloads

`status_payload` includes:

- `status`, `status_message`
- `progress` (`completed`, `total`, `unit`, `percent`, `updated_at`)
- `active_job_id`, `last_job_id`

`results_payload` includes:

- `status`
- `last_prepare_summary`
- `last_run_summary`
- `warnings`, `errors`

`state_payload` additionally includes:

- `state_version=1`
- `enabled`
- `config_snapshot`
- artifact readiness flags (`hru_table_ready`, `frequency_panel_ready`, `batch_summary_ready`)
- `updated_at`

### 12.3 Query/report summary payload

`query_summary_payload` provides:

- `filters` (`datasource_id`, `ari_years`, `measure`)
- `filter_options`:
  - `datasource_ids = [all, cligen_freq, noaa14_pds]`
  - `datasource_availability`
  - `ari_years`
  - `measures = [peak_discharge, runoff_depth, runoff_volume]`
  - `duration_minutes`
- `chart` grouped by ARI, marker-labeled by duration
- `event_table` with status and metrics
- `selected_storm_id` sync key
- sanitized `warnings` and `errors`

Current row status resolution precedence:

1. panel availability (`unavailable` if not available),
2. run summary failed/completed sets,
3. fallback to storm summary status.

Chart includes completed storms only.

## 13. API Surface (Current)

### 13.1 Flask WEPPcloud routes (`geneva_bp.py`)

Config and task routes:

- `GET /runs/<runid>/<config>/api/geneva/config`
- `POST /runs/<runid>/<config>/api/geneva/config`
- `POST /runs/<runid>/<config>/tasks/geneva/prepare_hrus`
- `POST /runs/<runid>/<config>/tasks/geneva/build_frequency_panel`
- `POST /runs/<runid>/<config>/tasks/geneva/run_batch`

Status/results/query/report:

- `GET /runs/<runid>/<config>/api/geneva/status`
- `GET /runs/<runid>/<config>/api/geneva/results`
- `GET /runs/<runid>/<config>/api/geneva/frequency_panel`
- `GET /runs/<runid>/<config>/query/geneva/summary`
- `GET /runs/<runid>/<config>/report/geneva/summary`

CN-table routes:

- `GET /runs/<runid>/<config>/modify_geneva_cn_table`
- `GET /runs/<runid>/<config>/api/geneva/cn_table_meta`
- `GET /runs/<runid>/<config>/api/geneva/cn_table_snapshot`
- `POST /runs/<runid>/<config>/tasks/modify_geneva_cn_table`
- `POST /runs/<runid>/<config>/tasks/reset_geneva_cn_table`

Response-shape note:

- most Geneva Flask endpoints return raw JSON payloads (`jsonify(payload)`),
- CN-table meta/snapshot/reset use `success_factory`, so payload is wrapped under `{"Content": ...}`.

### 13.2 rq-engine Geneva routes (`microservices/rq_engine/geneva_routes.py`)

Enqueue routes:

- `POST /api/runs/{runid}/{config}/geneva/prepare-hrus`
- `POST /api/runs/{runid}/{config}/geneva/build-frequency-panel`
- `POST /api/runs/{runid}/{config}/geneva/run-batch`
- `POST /api/runs/{runid}/{config}/geneva/run-workflow`

State route:

- `GET /api/runs/{runid}/{config}/geneva/state`

Workflow chaining:

- `run-workflow` enqueues prepare -> panel -> run-batch dependencies,
- workflow normalization forces:
  - `prepare.force_rebuild = true`
  - `panel.rebuild = true`

State response extras:

- `contract_version`
- `deployment_revision`
- `run_state_domain`
- `run_state_revision`
- `run_state_vector`
- `etag`
- plus Geneva `state_payload` fields

### 13.3 Canonical error and enqueue envelopes

Current canonical error shape:

```json
{
  "error": {
    "message": "Human-readable summary",
    "code": "error_code",
    "details": "or object"
  }
}
```

Canonical enqueue success shape (single-job endpoints):

```json
{
  "job_id": "rq-...",
  "status_url": "/rq-engine/api/jobstatus/rq-...",
  "message": "Job enqueued."
}
```

Workflow enqueue success shape:

```json
{
  "job_id": "prepare-job-id",
  "job_ids": {
    "prepare_hrus": "prepare-job-id",
    "build_frequency_panel": "panel-job-id",
    "run_batch": "run-job-id"
  },
  "status_url": "/rq-engine/api/jobstatus/prepare-job-id",
  "message": "Workflow enqueued."
}
```

## 14. UI Contract (Current)

Run-page Geneva control (`controls/geneva_pure.htm` + `controllers_js/geneva.js`):

- state authority is rq-engine Geneva state endpoint,
- one primary run action queues chained workflow (`run-workflow`),
- config is auto-saved before queue submission when dirty,
- control includes panel and run filters, CN-table launch, query/report launch links.

Summary report (`reports/geneva/summary.htm` + `geneva_summary_report.js`):

- embeds summary payload in one JSON script node:
  - `id="geneva-summary-payload"`
  - `type="application/json"`
- filter controls: datasource, ARI, measure,
- marker/table selection synchronization via `selected_storm_id`,
- datasource availability messaging (NOAA unavailable note).

## 15. Artifact Catalog (Current)

Under `<run>/geneva/`:

- `data/cn_table.csv`
- `data/cn_table_audit.jsonl`
- `hru_table.parquet`
- `hru_prepare_summary.json`
- `frequency_panel.json`
- `storm_inputs.json`
- `batch_summary.json`
- `storms/<storm_id>/hyetograph.parquet`
- `storms/<storm_id>/excess_hyetograph.parquet`
- `storms/<storm_id>/hydrograph.parquet`
- `storms/<storm_id>/summary.json`
- optional normalization artifact:
  - `normalized_sources/wepp_cli_pds_mean_metric_kernel.csv`

## 16. Current Test/Validation Baseline

Geneva coverage currently includes:

- schema contract tests (`config`, `frequency panel`, `run batch` validation),
- guardrail tests (WBT/domain rejection),
- facade/collaborator tests,
- CN-table lifecycle/concurrency/audit tests,
- query/report payload contract tests,
- Flask route contract tests,
- rq task wrappers and lock-retry behavior tests,
- rq-engine route and state response tests,
- integrated scenario matrix (`completed`, `completed_with_gaps`, warning propagation, collapse sensitivity checks).

Primary suites:

- `tests/nodb/mods/geneva/`
- `tests/weppcloud/routes/test_geneva_bp.py`
- `tests/weppcloud/routes/test_geneva_wp08_routes.py`
- `tests/rq/test_geneva_rq.py`
- `tests/microservices/test_rq_engine_geneva_routes.py`

## 17. Deferred Work (Future Reference)

The following are intentionally tracked for follow-on implementation:

- wire run-scoped `cn_table.csv` into runtime HRU CN lookup/resolution,
- wire NEH4 Type B hyetograph generation into batch execution path (replace uniform interim builder),
- implement dominant-soil derivation for `default_hsg_code` when user override is absent,
- implement non-stub `geneva_validate_uh` API,
- evaluate refine/cleanup of route module structure (currently single `geneva_bp.py`),
- address rq-engine generic payload normalization behavior that can collapse single-item arrays to scalars.

## 18. Open Design Decisions (Tracked)

- Should post-fire grass/herbaceous CN augmentation become default-on in v1.1?
- Should dual-HSG drainage policy (`A/D`, `B/D`, `C/D`) be handled in Geneva or remain upstream-only?
- When should reservoir routing enter scope (v2 vs external workflow)?
- Should we add curated panel presets beyond the full matrix (`5m..24h` x `1..100`)?

## 19. Wildcat5 Macro Reuse Assessment (Retained)

Direct algorithm reference candidates (port-and-test only):

- CN transforms, weighted CN helpers, rainfall excess routines,
- storm distribution routines,
- UH/hydrograph routines.

Reference-only (deferred phase):

- routing/reservoir VBA routines.

Not runtime-usable:

- workbook sheets/forms/UI glue modules and Excel-coupled orchestration code.

## 20. References

- USDA Forest Service. 2016. RMRS-GTR-334.
- USDA NRCS. National Engineering Handbook, Part 630 (Hydrology).
- USDA SCS. NEH Section 4 and TR-55 hydrology references.
- USDA NRCS. 2016. Hydrology Technical Note 210-4, *Hydrologic Analyses of Post-Wildfire Conditions*.
