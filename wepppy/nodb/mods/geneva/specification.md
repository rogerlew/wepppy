# Geneva NoDb Mod Specification

Status: Draft (Greenfield, implementation not started)  
Last Updated: 2026-04-14  
Owner: WEPPpy NoDb hydrology stack  
Scope: Event runoff hydrograph modeling for BAER-style post-fire workflows using RMRS-GTR-334-aligned Curve Number (CN) + unit hydrograph methods.

Name note: `geneva` is the project codename selected in memory of Richard H. Hawkins (passed January 2026)

## 1. Purpose

Create a new NoDb mod that provides a canonical, auditable rainfall-runoff workflow for BAER users, with:

- HRUs derived from watershed raster products (`bound.tif`) using landuse + HSG + optional burn severity.
- Event-scale CN rainfall excess generation.
- Storm hyetograph and watershed outlet hydrograph outputs.
- Batch execution across multiple design storms.
- Storm depth/intensity support using CLIGEN and NOAA Atlas 14 PDS frequency products.
- US-only v1 landuse/soils assumptions aligned to NRCS/NLCD conventions.

This is a greenfield implementation in WEPPpy and must not reuse Culvert-at-risk runtime code.

## 2. Scope and Non-Goals

In scope (v1):

- US-only execution domain (NLCD + NRCS HSG assumptions; no non-US lookup packs in v1).
- Distributed CN rainfall excess (default `Ia/S = 0.20`, optional `Ia/S = 0.05`).
- NEH4 Type B (`NEH4B`, also known as SCS Type B) storm distribution support.
- Composite excess hyetograph generation from HRUs.
- Unit-hydrograph transformation to a composite outlet hydrograph.
- Batch storm runs with consistent metadata/provenance.
- Dual-source frequency panel generation:
  - always CLIGEN frequency panel,
  - NOAA14 PDS panel when available.
- WBT-backend-only enablement and explicit guardrails.

Out of scope (v1):

- Non-US landcover/soil taxonomies and non-US design-storm region defaults.
- Full channel hydraulics or kinematic-wave channel routing.
- Snowmelt-driven events.
- Rain-on-snow process representation.
- Mixed rainfall-excess process groups in the same run (for example CN on one fraction and phi-index on another in the same simulation).
- Reservoir routing (deferred to follow-on phase).

## 3. Canonical Reference Basis

Primary scientific/manual basis:

- USDA Forest Service RMRS-GTR-334 (Wildcat5 manual), especially:
  - Chapter 3 (storm distributions; includes NEH4B/Type B),
  - Chapter 4 (distributed CN rainfall excess),
  - Chapter 6 (unit hydrographs),
  - Chapter 7 (hydrograph outputs).
- USDA NRCS NEH 630 hydrology references for CN/HSG context.
- Watershed-default HSG fallback is allowed only as explicit fallback with warnings.

Conformance posture:

- RMRS-GTR-334 alignment is normative for method family and workflow sequence.
- Where RMRS gives multiple options, this spec defines a default and explicitly names optional alternatives.
- Any divergence must be logged in a `Conformance Deviations` section before implementation.

### 3.1 Conformance Deviations

Use this table for any deliberate departure from RMRS-GTR-334 workflow/math.

| Deviation ID | Spec Section | RMRS Reference | Deviation Description | Justification | Approval |
| --- | --- | --- | --- | --- | --- |
| DEV-001 | `7.1` | RMRS Ch. 4 workflow | Enforce minimum HRU area (`2 ha`) with deterministic collapse | Reduce raster speckle/noise while preserving watershed area closure | Approved (2026-04-14) |
| DEV-002 | `8.3` | RMRS Tables 4-10 to 4-14 | Keep non-forest/non-shrub burn CN values static by default in seed table | Conservative v1 default; user-editable run-scoped CN table retained | Approved (2026-04-14) |
| DEV-003 | `10.1` | RMRS storm options | Disable duration interpolation for frequency-panel materialization | Prevent synthetic storm generation without explicit evidence module | Approved (2026-04-14) |
| DEV-004 | `10` | RMRS climate sourcing | Use dual-source panel strategy (always CLIGEN; NOAA14 when available) | Avoid single-source oracle behavior and preserve analyst comparability | Approved (2026-04-14) |

Execution gate:

- Before WP-01 implementation starts, WP-00 must record conformance-deviation disposition evidence in `implementation-plan.md`.

### 3.2 Wildcat5 Source Artifacts and Legal Posture

Wildcat5 source artifacts are staged under:

- `wepppy/nodb/mods/geneva/resources/Wildcat5/`
- extracted VBA modules under:
  - `wepppy/nodb/mods/geneva/resources/Wildcat5/extracted_macros/wildcat5dec072015-64bits/`

For this project, Wildcat5 workbook/macro content is treated as public domain (USDA work product), with local notes tracked in:

- `wepppy/nodb/mods/geneva/resources/Wildcat5/AGENTS.md`

Implementation policy:

- Do not execute VBA at runtime.
- Re-implement selected algorithms in WEPPpy Python/Rust with unit tests and parity checks.
- Treat extracted VBA as a reference implementation, not as production code.

## 4. WBT-Only Guardrail (Hard Requirement)

Geneva is a `weppcloud-wbt` only feature.

Contract:

- Mod enablement must fail on non-WBT delineations with explicit user-facing error.
- Route/task handlers must check the same backend guard (no silent bypass).
- Error message must state that Geneva requires a WBT delineation backend.

Recommended check pattern:

- Reuse the same backend gating approach used by existing WBT-only mods (for example roads gating patterns in NoDb routes).

### 4.1 US-Only Guardrail (Hard Requirement)

Geneva v1 is United States only.

Contract:

- Landuse input must be a US NLCD-coded raster (integer NLCD classes).
- HSG assumptions and defaults are NRCS/NEH-based and valid only for US soils taxonomy.
- If run location or data source is outside US-supported conventions, fail with explicit error:
  - explain that Geneva v1 is US-only,
  - list required datasets (`NLCD`, US NRCS-compatible HSG source),
  - return `unsupported_domain` and do not offer runtime bypass in v1.

## 5. Input Contract

Required inputs:

- Watershed boundary raster: `bound.tif` aligned to run DEM grid.
- Landuse raster aligned to watershed grid (US NLCD classes for v1).
- Soil/HSG source from `wmesque2` layer `ssurgo/hydgrpdcd` (primary for v1), aligned to watershed grid or mappable to it.
- Frequency products:
  - `climate/wepp_cli_pds_mean_metric.csv` (required in v1),
  - `climate/atlas14_intensity_pds_mean_metric.csv` (optional when NOAA available).

Optional inputs:

- Burn severity raster from `sbs_map.py` normalized output (`0=unburned`, `1=low`, `2=moderate`, `3=high`, nodata `255`). If absent, `burn_severity_class=unburned` is applied to all in-bound cells.
- `default_hsg_code` override (integer `1|2|3|4` for `A|B|C|D`) used only for unresolved cells after `hydgrpdcd` lookup.
- `unresolved_hsg_policy` (`error|assume_d`, default `error`) for post-fallback unresolved cells.
- `strict_burn_nodata` (`true|false`, default `false`) to fail when in-bound burn nodata area is non-zero.
- User HRU merge threshold (optional override, but not allowed below `2 ha`).
- `allow_cross_hsg_merge` (`true|false`, default `false`) to permit HRU collapse across HSG groups with provenance.
- Hydrophobic assignment toggles (SBS-driven, v1 UI checkboxes):
  - `hydrophobic_forest_high` (`true|false`)
  - `hydrophobic_forest_moderate` (`true|false`)
  - `hydrophobic_shrub_high` (`true|false`)
  - `hydrophobic_shrub_moderate` (`true|false`)
- User overrides for CN lookup rows.

Required run metadata:

- CRS, cellsize, nodata policy for each source raster.
- Alignment diagnostics against `bound.tif` canonical grid (CRS, transform, width, height) for each categorical raster.
- Watershed area (`wsarea`) in SI and English units.
- Data provenance for all lookup tables used.
- HSG-source diagnostics for `ssurgo/hydgrpdcd` (coded cell count, unrated/unknown count, fallback-assigned count).
- Default-HSG diagnostics (`default_hsg_code`, derivation source, fallback-assigned count/area).
- Burn-nodata diagnostics (`burn_nodata_cell_count`, `burn_nodata_area_m2`, strict mode flag).
- Assumptions block (`arc_condition`, `storm_distribution_assumption`, `uniform_rainfall_assumed`, `burn_input_present`, `hydrophobic_rule_flags`).

### 5.1 Run-Scoped CN Table Initialization

On Geneva initialization (or first Geneva enablement), the backend must create:

- `<runid>/geneva/data/cn_table.csv`

from module seed data:

- `wepppy/nodb/mods/geneva/data/geneva_cn_table_us_v1_seed.csv`

Contract:

- `cn_table.csv` is run-scoped and mutable by the user.
- If `cn_table.csv` is missing, Geneva recreates it from the seed and emits a warning/audit event.
- If the seed schema version changes, Geneva performs explicit migration or fails with actionable schema diagnostics.
- CN-table edits follow disturbed-lookup semantics:
  - optimistic concurrency token (`if_match_sha256`) is required on save,
  - stale-token saves are rejected with actionable conflict response,
  - append-only JSONL audit events are recorded with `timestamp_utc`, `event`, `lookup_path`, `before`, `after`, and summary `details`.
- Geneva does not require `change_reason` for CN-table saves in v1.

Initial schema (v1):

- `nlcd_class`
- `nlcd_label`
- `hsg` (`A|B|C|D`)
- `burn_severity` (`unburned|low|moderate|high`)
- `hydrophobic` (`true|false`)
- `cn_arc_ii`
- `antecedent_condition_source` (`arc_ii_seed|user_override`)
- `source`
- `notes`

Seed intent:

- Static no-burn rows for all core NLCD classes.
- Burn-severity rows for forest/shrub classes (`NLCD 41, 42, 43, 52`) across HSG groups.
- Hydrophobic rows for moderate/high forest/shrub cases.

## 6. HSG Determination Contract

HSG assignment must be explicit, source-aware, and auditable.

Priority:

1. `wmesque2:ssurgo/hydgrpdcd` mapped through the pinned v1 codebook (`coded_lookup`).
2. Alternate NRCS-derived direct HSG attributes (when explicitly provided and mappable).
3. Watershed-default HSG fallback for any still-unresolved cells.

### 6.1 `hydgrpdcd` Codebook Domain (US v1)

Pinned codebook artifact:

- `wepppy/nodb/mods/geneva/data/geneva_hydgrpdcd_codebook_us_v1.csv`

Code domain for this build:

- `0 -> NODATA_OR_UNRESOLVED`
- `1 -> A`
- `2 -> B`
- `3 -> C`
- `4 -> D`

Contract:

- Geneva v1 expects `hydgrpdcd` raster codes in `{0,1,2,3,4}`.
- Codes `5`, `6`, and `7` are not part of this build and must be treated as invalid/unexpected values in v1 (counted, warned, then handled by fallback chain).
- Persist codebook provenance (`codebook_path`, `codebook_sha256`, `layer_path`, `layer_mtime`).

Dual-group note:

- Any dual-group policy (`A/D`, `B/D`, `C/D`) must be resolved upstream by the hydgrpdcd build pipeline; Geneva consumes only the normalized single-group code domain above.

Rules:

- Do not assume integer HSG code meaning without a dataset codebook/version reference.
- `coded_lookup` means HSG values derived from a versioned, dataset-specific codebook (for example, the mapped `ssurgo/hydgrpdcd` domain), with the codebook provenance persisted.
- Record `hsg_source` per HRU (`coded_lookup`, `nrcs_direct`, `default_hsg_fallback`).
- Emit warnings for any fallback HSG assignment and include fallback area fraction.
- Per-cell HSG override maps are out of scope in v1; any such payloads must be rejected with explicit diagnostics.
- Cell-level HSG mapping + fallback assignment execute in the `wepppyo3` `geneva_prepare_hrus(...)` kernel; Python NoDb collaborators handle orchestration/provenance only.
- Unknown/unrated `hydgrpdcd` handling must run through fallback chain first (`default_hsg_code`), and only then apply unresolved-cell policy:
  - `error` (default): fail with actionable diagnostics when cells remain unresolved after fallback chain.
  - `assume_d`: coerce remaining unresolved cells to `D` and emit warning counts + area affected.

### 6.2 Watershed Default HSG Fallback (Required in v1)

`default_hsg_code` is an integer in `{1,2,3,4}` mapped to `A|B|C|D`.

Derivation order:

1. Use user-supplied `default_hsg_code` when provided.
2. Else derive from watershed dominant soil using existing soils workflow outputs (dominant map-unit/component per run metadata).
3. If dominant-soil derivation is unavailable, use `4` (`D`) and emit warning.

Determinism rule:

- If dominant-soil candidates are tied on area, break ties by conservative HSG ordering `D > C > B > A`.

Usage:

- Apply `default_hsg_code` only to cells unresolved after `coded_lookup`.
- Persist fallback provenance:
  - `default_hsg_code`,
  - derivation source (`user_override|dominant_soil|assume_d`),
  - fallback cell count and area.

Water handling:

- Open-water classes must be represented as explicit HRUs (not dropped silently).
- Water detection precedence is:
  1. NLCD open-water class (`11`) classification,
  2. optional explicit water mask input when provided.
- HSG codebook values are not used to infer open water.
- Water HRUs default to `CN = 100` unless user explicitly overrides.

## 7. HRU Derivation Contract

HRUs are raster-derived unique combinations over in-bounds cells:

- key = `(landuse_class, hsg_group, burn_severity_class, hydrophobic_class)`
- burn severity is always present:
  - if burn raster absent: `burn_severity_class=unburned` for all in-bound cells.
  - if burn raster present: map from SBS codes and nodata policy below.
- hydrophobic is always present and rule-derived (no raster input in v1):
  - evaluate `hydrophobic_class` from NLCD class + burn severity + hydrophobic toggle settings.
  - forest classes are `NLCD 41, 42, 43`; shrub class is `NLCD 52`.
  - moderate/high burn classes map to hydrophobic only when corresponding toggle is enabled.
  - all other combinations map to `hydrophobic_class=false`.
- Burn severity class mapping (from normalized SBS raster) is fixed:
  - `0 -> unburned`
  - `1 -> low`
  - `2 -> moderate`
  - `3 -> high`
  - nodata `255` inside `bound==1` maps to `unburned` with `burn_source=nodata_fallback` unless `strict_burn_nodata=true`, which fails.
- Minimum HRU area is enforced at `2 ha` (`20,000 m2`) to suppress `hydgrpdcd`-driven speckle/noise in v1 outputs.

Processing:

1. Define `bound.tif` as the canonical analysis grid (CRS, transform, width, height).
2. Align all categorical rasters (`landuse`, `hydgrpdcd`, `burn_severity`) to the canonical grid using nearest-neighbor only.
3. Fail fast if any aligned raster still mismatches canonical grid metadata.
4. Apply in-bound mask (`bound == 1`) and ignore all out-of-bound cells.
5. Compute cell counts and area fractions for each unique key.
6. Attach CN from canonical lookup tables.
7. Apply required HRU collapsing for HRUs below minimum area threshold.
8. Enforce area closure `|sum(hru_area_m2)-inbound_area_m2| <= one_cell_area_m2`.

### 7.1 Minimum HRU Area Enforcement (Hard Requirement)

Default threshold:

- `min_hru_area_ha = 2.0` (`20,000 m2`)

Rules:

- HRUs with `area_m2 < 20,000` are donor HRUs and must be merged.
- Compatible recipient HRUs must match:
  - `landuse_class`
  - `burn_severity_class`
  - `hydrophobic_class`
  - `hsg_group` by default.
- Cross-HSG merges are optional via `allow_cross_hsg_merge=true`; when used, persist `merge_reason`, donor/recipient HSG, and `delta_cn_arc_ii`.
- Recipient selection order:
  1. smallest `abs(cn_arc_ii_recipient - cn_arc_ii_donor)`,
  2. largest recipient `area_m2`,
  3. lexical `hru_id` tie-break.
- Water HRUs are protected and are never merged into non-water HRUs.
- Area conservation is mandatory; total in-bound area must remain unchanged after collapse (within float tolerance).
- If no compatible recipient exists for a donor HRU, fail with explicit diagnostics by default.

Override policy:

- Users may set a larger threshold (for example `3 ha`, `5 ha`) but may not set below `2 ha`.

HRU table minimum fields:

- `hru_id`
- `area_m2`, `area_ac`, `area_fraction`
- `landuse_class`
- `hsg_group`
- `burn_severity_class`
- `hydrophobic_class` (`true|false`)
- `cn_arc_ii`
- `cn_lambda_020`
- `cn_lambda_005` (derived when needed)
- `antecedent_condition_source` (`arc_ii_seed|user_override`)
- `cn_source`
- `hsg_source`
- `collapsed_from_hru_ids` (nullable array)
- `warnings` (array or count summary)

### 7.2 Rationale (HRU Construction and Collapse Choices)

- RMRS/Wildcat workflows support HRU-based semi-distributed excess routing; preserving landuse/HSG/burn/hydrophobic dimensions keeps process assumptions explicit.
- Minimum-HRU threshold controls `hydgrpdcd` speckle while preserving area closure and reproducibility.
- Cross-HSG merge is opt-in because CN response is nonlinear with respect to infiltration potential and should not be blurred by default.

## 8. CN and Rainfall Excess Contract

### 8.0 CN Lookup Table Usage (Run-Scoped)

Geneva does not hardcode CNs in logic. CN lookup resolves through run-local:

- `<runid>/geneva/data/cn_table.csv`

Selection key:

- `(nlcd_class, hsg, burn_severity, hydrophobic)`

Resolution rules:

1. Exact row match required for forest/shrub burn rows in v1.
2. `burn_severity` is always required in key resolution; when burn input is absent or nodata-fallback is used, `burn_severity = unburned`.
3. `hydrophobic` is rule-derived from configured forest/shrub severity toggles (Section 5), not raster input.
4. Missing row policy defaults to explicit error with a diagnostic listing missing keys and affected area.

### 8.1 CN Equations

Default runoff equation (`Ia/S = 0.20`):

- `Q = (P - 0.2S)^2 / (P + 0.8S)` for `P >= 0.2S`, else `Q = 0`
- `S = 1000/CN - 10` (inch-form equivalent), with unit-consistent implementation in SI runtime.

Optional alternative (`Ia/S = 0.05`, RMRS Eq. 4-05 / 4-06):

- `S_0.20 = 1000/CN_0.20 - 10`
- `S_0.05 = 1.33 * (S_0.20 ^ 1.15)`
- `CN_0.05 = 100 / (1.879 * ((100/CN_0.20 - 1) ^ 1.15) + 1)`
- validity cap: if `CN_0.20 > 98.5`, set `CN_0.05 = CN_0.20` in v1.
- `Ia_0.05 = 0.05 * S_0.05`
- `Q = 0` for `P <= Ia_0.05`
- `Q = (P - Ia_0.05)^2 / (P + 0.95*S_0.05)` for `P > Ia_0.05`

Conformance note:

- Geneva follows RMRS `98.5` validity guidance for the conversion cap; legacy workbook shortcuts that cap at lower CN values are non-normative for v1.

### 8.2 Time-Discretized Excess

Per storm:

1. Build rainfall hyetograph on fixed timestep.
2. For each HRU, compute cumulative `Q(t)` from cumulative `P(t)`.
3. Convert to incremental excess depths `dQ(t)`.
4. Area-weight `dQ(t)` across HRUs to composite excess hyetograph.

### 8.3 Post-Fire CN Burn Augmentation Guidance (v1 Defaults)

Default seeding policy in `geneva_cn_table_us_v1_seed.csv`:

- Forest/shrub non-hydrophobic burn CNs are seeded from RMRS-GTR-334 Table 4-14 (AGWA-recommended set by cover + burn severity + HSG).
- Forest/shrub hydrophobic moderate/high rows are seeded from RMRS-GTR-334 Table 4-06 values (`moderate+repellency = 90`, `high+repellency = 95`) as conservative starting points.

Hydrophobic-toggle interpretation (v1):

- `hydrophobic_forest_high=true`: apply hydrophobic CN rows for `NLCD 41/42/43` with `burn_severity=high`.
- `hydrophobic_forest_moderate=true`: apply hydrophobic CN rows for `NLCD 41/42/43` with `burn_severity=moderate`.
- `hydrophobic_shrub_high=true`: apply hydrophobic CN rows for `NLCD 52` with `burn_severity=high`.
- `hydrophobic_shrub_moderate=true`: apply hydrophobic CN rows for `NLCD 52` with `burn_severity=moderate`.
- Any unchecked case resolves to non-hydrophobic CN rows.

Important conformance note:

- RMRS-GTR-334 states post-fire CN tables are compiled practice guides and should be treated as suggestions with local judgment; Geneva must preserve user editability and provenance for this reason.

Grass question (v1 position):

- Canonical guidance indicates grass/herbaceous CN can be fire-adjusted (RMRS Tables 4-10 to 4-13 include annual-grass burn classes; NRCS post-wildfire technical note includes herbaceous severity-specific CNs).
- Geneva v1 seed keeps non-forest/non-shrub classes static unless users edit `cn_table.csv`; grass burn augmentation is therefore user-driven in v1, not auto-enforced by code.

### 8.4 Antecedent Moisture / CN Condition Lock (Required)

- All seeded CN values are `ARC II` by default (`cn_arc_ii`).
- Geneva v1 does not auto-transform CN to `ARC I/III` from storm/soil-moisture state.
- Wet/dry antecedent scenarios require explicit CN-table overrides with provenance field `antecedent_condition_source`.
- `lambda_mode` (`0.20` vs `0.05`) is a model-form choice; cross-mode results are not directly comparable without documented CN-derivation rationale.

#### 8.5 Rationale (CN Method Choices)

- RMRS-GTR-334 and NEH references support CN as an event-scale rainfall-excess method when assumptions are explicit.
- Locking ARC II as default prevents hidden moisture-state inference from sparse inputs.
- Run-scoped CN mutability with provenance preserves BAER workflow flexibility while keeping results auditable.

## 9. Storm Contract (Frequency-Panel Driven, Including NEH4 Type B)

Geneva v1 does not accept user-entered storm hyetographs as primary inputs.  
Storm events are generated from available frequency products and then transformed to hyetographs/hydrographs.

Each generated event must include:

- `storm_id`
- `datasource_id` (`cligen_freq|noaa14_pds`)
- `ari_years`
- `duration_minutes`
- `depth_mm`
- `intensity_mm_per_hr` (derived from depth/duration when not explicitly provided)
- `distribution_type` (`neh4_type_b` in v1)

Required distribution support in v1:

- `neh4_type_b` (NEH4 Type B / SCS Type B) as first-class built-in option.

Canonical naming rule:

- Internal/API/artifact enums and field names use lowercase snake case.
- UI labels may present uppercase/readable aliases (for example `NOAA14_PDS`) but must map to canonical IDs.

Batch support:

- Runs operate over a generated event panel and optional panel filters (`datasource`, duration set, ARI set).
- Execution produces per-event artifacts and one batch summary.
- Failures are isolated per event when possible; batch result reports per-event status.

### 9.1 Frequency-Panel Storm Template (v1 Default)

Default event panel target:

- durations: `5m`, `10m`, `30m`, `1h`, `2h`, `3h`, `6h`, `12h`, `24h`
- return periods (`ari_years`): `1`, `2`, `5`, `10`, `25`, `50`, `100`
- distribution type: `neh4_type_b`

Datasource behavior:

- `cligen_freq`: always materialize available combinations from `climate/wepp_cli_pds_mean_metric.csv`.
- `noaa14_pds`: materialize available combinations from `climate/atlas14_intensity_pds_mean_metric.csv` when available.

Contract:

- Missing combinations are never silently filled with synthetic values.
- Unavailable combinations are recorded with reason (`duration_unavailable`, `ari_unavailable`, `source_missing`).
- Batch run status may be `completed_with_gaps` when at least one requested combination is unavailable.

### 9.2 `neh4_type_b` Construction Contract (v1)

Use cumulative dimensionless ordinates:

- `t* = [0, 0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6] / 6`
- `P* = [0, 0, 3.5, 8, 13.5, 23, 60, 70, 78, 83.5, 88.5, 92.5, 96, 100] / 100`

Scaling:

- `t_i = t*_i * duration_minutes`
- `Pcum_i = P*_i * depth_mm`

Interpolation/discretization:

- Evaluate cumulative rainfall at runtime timestep using linear interpolation between breakpoints.
- Convert cumulative rainfall to incremental depths per step:
  - `dP_k = Pcum(t_k) - Pcum(t_{k-1})`
  - `intensity_k = dP_k / dt_hours`
- Enforce monotonic cumulative rainfall and endpoint closure:
  - `Pcum(0) = 0`
  - `Pcum(duration_minutes) = depth_mm`
- Ordinates are pinned to RMRS-GTR-334 Type B and mirrored in `wepppy/nodb/mods/geneva/data/geneva_neh4_type_b_ordinates_v1.csv`; persist source SHA256 in run metadata.
- Duplicate `t*=0` points define an initial zero-intensity plateau and must not trigger duplicate-x interpolation errors.
- For `duration_minutes < 30`, emit `type_b_short_duration_extrapolation` warning.

#### 9.3 Rationale (Storm Construction Choices)

- NEH4 Type B is canonical in RMRS/Wildcat BAER workflows.
- Frequency-panel generation improves comparability across sources and durations versus ad hoc event picking.
- Pinned ordinates and explicit interpolation rules prevent implementation drift.

## 10. Storm Frequency Data Sources (Dual-Source Strategy)

Geneva v1 uses a dual-source strategy:

1. Always materialize CLIGEN frequency events from `climate/wepp_cli_pds_mean_metric.csv`.
2. Materialize NOAA14 PDS frequency events from `climate/atlas14_intensity_pds_mean_metric.csv` when available (or fetch/populate this artifact when supported).

Rules:

- Store provenance per event (`datasource_id`, `source_path`, `source_version`, `lat/lon`, timestamp).
- If CLIGEN frequency artifact is unavailable, fail with actionable message.
- If NOAA is unavailable, continue with CLIGEN events and report NOAA availability status.
- Persist both `depth_mm` (primary) and `intensity_mm_per_hr` (unit-normalized) per event.

### 10.0 Requested vs Available Matrix Handling

Geneva treats frequency storm generation as per-source matrix resolution:

1. Build requested matrix from selected durations x return periods.
2. Resolve CLIGEN available matrix.
3. Resolve NOAA available matrix (when NOAA data exist).
4. Materialize one event record per available matrix cell with explicit `datasource_id`.
5. Persist missing-cells list by datasource with reason codes.

This prevents hidden extrapolation and keeps source comparisons auditable.

### 10.1 NOAA Atlas 14 PDS Intensity/Duration Crosswalk (v1)

Purpose:

- Standardize NOAA frequency values to Geneva event records across multiple durations.

Core rule:

- Geneva treats storm depth as primary and derives intensity from depth and duration.

Formulas (unit-consistent):

- `depth = intensity * duration`
- `intensity = depth / duration`
- duration is converted to hours before calculation (`minutes/60`, `days*24`).

Frequency-series consistency:

- Query NOAA using PDS series and keep ARI basis consistent across durations.
- Do not mix AMS (`aep`) and PDS (`ari`) values within one event set unless explicit conversion metadata is provided.
- Never use `ARI = 1/AEP` shortcut conversion in code.

Duration handling:

- Use durations available in `climate/atlas14_intensity_pds_mean_metric.csv` as canonical for v1.
- v1 interpolation policy: disabled for panel materialization (`allow_duration_interpolation = false`).
- Requested durations missing from source remain unavailable matrix cells.

Hyetograph construction tie-in:

- Total depth from crosswalk is distributed by configured storm pattern (`neh4_type_b` in v1).

### 10.2 CLIGEN Frequency Contract (v1)

- Geneva reads explicitly available duration/frequency products from `climate/wepp_cli_pds_mean_metric.csv`.
- Geneva must not infer unavailable short durations (for example `5m` or `10m`) unless an explicitly versioned interpolation module is enabled.
- Output/report must label each event with canonical datasource IDs (`cligen_freq`, `noaa14_pds`).
- CLIGEN events persist support metadata (`cligen_years_count`, `recurrence_supported`).

### 10.3 Point-to-Basin Rainfall Assumption (Required)

- NOAA and CLIGEN frequency values are point estimates.
- Geneva v1 applies spatially uniform rainfall with `arf_method=constant_1.0` unless a future areal-reduction module is enabled.
- Emit `point_rainfall_assumption` warning for `wsarea_km2 > 25`.
- Emit severe `point_rainfall_assumption` warning for `wsarea_km2 > 100`.
- Persist `arf_method`, `arf_value`, and `uniform_rainfall_assumed=true` per event/run summary.

#### 10.4 Rationale (Dual-Source Frequency Strategy)

- Always generating CLIGEN avoids a single-source oracle workflow.
- Adding NOAA when available supports cross-source sensitivity checks and analyst judgment.
- Depth-first crosswalk and no synthetic fill keep event generation reproducible and academically defensible.

## 11. Hydrograph Contract

Geneva must produce both:

- Hyetograph outputs:
  - raw rainfall intensity/depth vs time,
  - composite rainfall excess vs time,
  - optional per-HRU excess traces.
- Hydrograph outputs:
  - outlet discharge vs time (composite),
  - summary metrics (`peak_discharge`, `time_to_peak`, `runoff_volume`, `runoff_depth`).

Unit hydrograph requirement:

- Default method: `scs_triangular`.
- Supported SCS methods in v1:
  - `scs_triangular`
  - `scs_curvilinear`
- Timing:
  - if user provides `tc_hours`, use it directly,
  - else compute from selected timing method (`kirpich`, `kent`, or `simas`) and persist method provenance.
- `scs_triangular` relations:
  - `tp = 0.6 * tc`
  - `tb = 2.667 * tp`
  - peak relation `qp = HF * A * Re / tp`
  - English form constant: `HF = 484` for `A(mi2)`, `Re(in)`, `tp(hr)`, `qp(cfs)`.
  - SI equivalent constants:
    - `HF = 0.208` for `A(km2)`, `Re(mm)`, `tp(hr)`, `qp(m3/s)`
    - `HF = 2.08` for `A(km2)`, `Re(cm)`, `tp(hr)`, `qp(m3/s)`
  - equivalent shape factor relation `HF = 1290.667 / (1 + b)` with default `b = 5/3` (English-unit form).
- `scs_curvilinear` definition:
  - use SCS dimensionless UH ordinates (`t/tp`, `q/qp`) from RMRS/Wildcat reference set,
  - evaluate by linear interpolation between tabulated ordinates.
- Discretization:
  - target `dt = tp / 5` (or nearest stable runtime timestep),
  - enforce UH mass closure `|integral(UH)-1| <= 0.005`.
- Keep UH settings explicit in artifacts and API payloads.
- Include timing parameter source (user provided or computed method) in run metadata.
- Persist UH unit and equation provenance (`uh_unit_system`, `hf_constant`, `qp_equation_id`).

#### 11.1 Rationale (UH Method Choices)

- SCS triangular and curvilinear UH methods are canonical in RMRS/Wildcat workflows and computationally practical for BAER screening.
- Explicit unit convention prevents silent magnitude errors when runtime units differ.
- Mass-closure and provenance constraints make hydrograph outputs auditable and reproducible.

### 11.2 Geneva Report Page Contract (Interactive)

Geneva report page must provide interactive exploration of batch storms.

Required selectors:

- `Climate Frequency Datasource`: `noaa14_pds | cligen_freq | all`
- `Return Period Interval (ARI years)`: multi-select from available values (`1`, `2`, `5`, `10`, `25`, `50`, `100` subset), default `all`
- `Measure of Interest`: `peak_discharge | runoff_depth | runoff_volume`

Chart contract (storm-event-analyzer style):

- x-axis: storm intensity (`mm/hr`), computed as `depth/duration` on normalized units
- y-axis: selected measure (`peak_discharge`, `runoff_depth`, or `runoff_volume`)
- series: separate lines by return period for selected ARIs
- markers: event points keyed by duration (`5m`, `10m`, `30m`, `1h`, `2h`, `3h`, `6h`, `12h`, `24h` as available)

Marker interaction:

- Selecting a marker opens/focuses an Event Table row for that storm.

Event Table required columns:

- storm event parameters (`storm_id`, `datasource_id`, `duration_minutes`, `depth_mm`, `intensity_mm_per_hr`, `distribution_type`, `ari_years`)
- `peak_discharge`
- `time_to_peak`
- `runoff_volume`
- `runoff_depth`

## 12. Watershed Size Warnings

Because RMRS/Wildcat methods target small watershed event analyses, Geneva must emit scale warnings.

Configurable thresholds (defaults):

- `warning_area_km2 = 25`
- `severe_warning_area_km2 = 100`
- `extreme_warning_area_km2 = 250`

Behavior:

- Exceed warning thresholds: run allowed, warnings persisted and shown in UI/report.
- Exceed extreme threshold: run allowed, warnings persisted and shown in UI/report.
- Warning payload includes area in `km2`, `mi2`, and `acres`.

## 13. NoDb Integration Blueprint

Planned module path:

- `wepppy/nodb/mods/geneva/`

Planned controller:

- `class Geneva(NoDbBase)`
- filename: `geneva.nodb`

Minimum persisted state:

- `enabled`
- `status` (`idle|prepared|running|completed|completed_with_gaps|failed`)
- `input_refs` (rasters, lookup tables, hashes)
- `storm_batch`
- `hru_summary`
- `run_summary`
- `warnings`
- `errors`
- timestamps/provenance

Suggested artifacts under run working dir:

- `geneva/hru_table.parquet`
- `geneva/storm_inputs.json`
- `geneva/storms/<storm_id>/hyetograph.parquet`
- `geneva/storms/<storm_id>/excess_hyetograph.parquet`
- `geneva/storms/<storm_id>/hydrograph.parquet`
- `geneva/storms/<storm_id>/summary.json`
- `geneva/batch_summary.json`
- `geneva/README.md`

### 13.1 Runtime Split (Required)

Geneva v1 is split into:

- Rust compute kernel in `wepppyo3` for numerically heavy loops (batch storm execution, CN excess time-stepping, UH transform, hydrograph assembly).
- Python orchestration in `wepppy` for NoDb state, routing, artifact wiring, validation, and report/query payload shaping.

Hard rule:

- Per-HRU/per-timestep/per-storm nested loops must not run in pure Python in production path.
- Raster alignment + HRU keying + HRU area aggregation + minimum-HRU collapse must run in Rust kernel code, not Python.

### 13.2 `wepppyo3` Architecture and File Structure (v1)

`wepppyo3` must avoid adding more monolith logic to `cli_revision/src/lib.rs`.
Use a pure-kernel crate plus a thin PyO3 adapter.

Workspace additions:

- `/workdir/wepppyo3/geneva_core/`
- `/workdir/wepppyo3/cli_revision/src/geneva/`

`geneva_core` (no PyO3; deterministic kernels + tests):

- `src/lib.rs` (public module wiring only)
- `src/types.rs` (`HruRow`, `StormEvent`, `RunConfig`, `StormResult`, `BatchResult`)
- `src/hru.rs` (grid alignment checks, cell-wise HRU keying, area aggregation, deterministic `min_hru_area` collapse)
- `src/cn.rs` (`S`, `Ia`, `Q(P)`, `lambda 0.20/0.05`, cumulative-to-incremental excess)
- `src/hyetograph.rs` (`neh4_type_b` scaling and timestep interpolation using pinned ordinates)
- `src/uh.rs` (`scs_triangular`, `scs_curvilinear`, mass-closure checks)
- `src/convolution.rs` (excess-to-hydrograph convolution kernels)
- `src/frequency_panel.rs` (matrix materialization from CLIGEN/NOAA frequency inputs)
- `src/error.rs` (typed kernel errors; no stringly-typed panic flow)

`cli_revision` PyO3 adapter:

- `src/geneva/mod.rs` (Python-callable entrypoints only)
- `src/geneva/convert.rs` (Py<->Rust data conversion helpers)
- `src/lib.rs` (register wrapper functions; no algorithm bodies)

Initial PyO3 entrypoints:

- `geneva_prepare_hrus(...)`
- `geneva_build_frequency_panel(...)`
- `geneva_run_batch(...)`
- `geneva_validate_uh(...)`

### 13.3 `wepppy` Architecture and File Structure (v1)

Keep NoDb facade small and collaborator-based per NoDb standard.

- `/workdir/wepppy/wepppy/nodb/mods/geneva/geneva.py` (NoDb facade only)
- `/workdir/wepppy/wepppy/nodb/mods/geneva/collaborators/`
- `/workdir/wepppy/wepppy/nodb/mods/geneva/schemas/`

Planned collaborators:

- `config_service.py` (load/save Geneva config + defaults)
- `hru_preparation_service.py` (prepare kernel inputs, invoke Rust HRU kernel, persist HRU artifacts/diagnostics)
- `hsg_assignment_service.py` (NoDb-side HSG provenance assembly; no cell-level mapping loops)
- `cn_table_service.py` (run-scoped `cn_table.csv` init/edit/reset/audit parity)
- `frequency_panel_service.py` (read climate artifacts, call Rust panel builder)
- `batch_run_service.py` (prepare Rust inputs, invoke Rust run, persist artifacts)
- `results_service.py` (aggregate status/results payloads)
- `report_payload_service.py` (chart/table payload for Geneva report page)
- `artifact_io.py` (stable read/write schemas for parquet/json artifacts)

Schema module files:

- `schemas/config_schema.py`
- `schemas/frequency_panel_schema.py`
- `schemas/run_batch_schema.py`
- `schemas/results_schema.py`

### 13.4 Route/Task Package Layout (v1)

Route handlers should be split by concern to avoid giant files:

- `/workdir/wepppy/wepppy/weppcloud/routes/nodb_api/geneva/__init__.py`
- `/workdir/wepppy/wepppy/weppcloud/routes/nodb_api/geneva/config_routes.py`
- `/workdir/wepppy/wepppy/weppcloud/routes/nodb_api/geneva/cn_table_routes.py`
- `/workdir/wepppy/wepppy/weppcloud/routes/nodb_api/geneva/task_routes.py`
- `/workdir/wepppy/wepppy/weppcloud/routes/nodb_api/geneva/query_routes.py`
- `/workdir/wepppy/wepppy/weppcloud/routes/nodb_api/geneva/report_routes.py`

### 13.5 Shared Data Boundary (`wepppy` <-> `wepppyo3`)

Rust input contract should be stable, versioned, and file-path based:

- Input parquet/json assembled under `<runid>/geneva/inputs/`
- Rust returns per-storm outputs under `<runid>/geneva/storms/<storm_id>/`
- Boundary schema version recorded as `kernel_schema_version`.
- HRU preparation uses the same boundary pattern:
  - raster refs + config input under `<runid>/geneva/inputs/hru_*`,
  - Rust output `geneva/hru_table.parquet` plus `geneva/hru_prepare_summary.json` (and optional `geneva/hru_id_map.tif` for diagnostics).

Contract requirements:

- Deterministic storm ordering (`datasource_id`, `duration_minutes`, `ari_years`, `storm_id`).
- Explicit unit fields in boundary payloads (`mm`, `hr`, `km2`, `m3/s`, `cfs`).
- No implicit defaulting inside Rust for missing required fields; fail with typed diagnostics.
- Reuse existing climate artifacts (`wepp_cli_pds_mean_metric.csv`, `atlas14_intensity_pds_mean_metric.csv`) as source-of-truth frequency inputs; no duplicate climate parsing stack in Python loops.
- Reuse existing `wepppyo3` geotiff/raster capability for HRU preprocessing; avoid duplicate raster scan loops in Python.

## 14. API/Task Sketch

Expected route family (patterned after existing NoDb mods):

- `POST /runs/<runid>/<config>/tasks/set_mod` with `{"mod":"geneva","enabled":true|false}`
- `GET|POST /runs/<runid>/<config>/api/geneva/config`
- `POST /runs/<runid>/<config>/tasks/geneva/prepare_hrus`
- `POST /runs/<runid>/<config>/tasks/geneva/run_batch`
- `POST /runs/<runid>/<config>/tasks/geneva/build_frequency_panel`
- `GET /runs/<runid>/<config>/modify_geneva_cn_table` (renders `controls/edit_csv.htm`)
- `POST /runs/<runid>/<config>/tasks/modify_geneva_cn_table`
- `GET /runs/<runid>/<config>/api/geneva/cn_table_meta`
- `GET /runs/<runid>/<config>/api/geneva/cn_table_snapshot`
- `POST /runs/<runid>/<config>/tasks/reset_geneva_cn_table`
- `GET /runs/<runid>/<config>/api/geneva/status`
- `GET /runs/<runid>/<config>/api/geneva/results`
- `GET /runs/<runid>/<config>/api/geneva/frequency_panel`
- `GET /runs/<runid>/<config>/query/geneva/summary`
- `GET /runs/<runid>/<config>/report/geneva/summary`

Execution mode:

- Queue-backed (`RQ`) for HRU prep and storm batch runs.
- Explicit per-storm status and warning propagation in job results.

### 14.1 Canonical Vocabulary (Normative)

Datasource IDs:

- `noaa14_pds`
- `cligen_freq`

Distribution IDs:

- `neh4_type_b`

Reserved (not accepted in v1 request payloads):

- `uniform`
- `custom_breakpoint`

Status IDs:

- `idle`
- `prepared`
- `running`
- `completed`
- `completed_with_gaps`
- `failed`

UH method IDs:

- `scs_triangular`
- `scs_curvilinear`

Field naming:

- JSON/API/artifact keys use lowercase snake case.
- Storm depth/duration/intensity fields are `depth_mm`, `duration_minutes`, `intensity_mm_per_hr`.

Type contracts (normative):

- `default_hsg_code` is integer-or-null only (`1|2|3|4|null`); reject string numerals.
- `reason_code` is nullable enum, never string `"null"`.
- `burn_severity_class` is non-null enum (`unburned|low|moderate|high`) in all persisted HRU rows.
- Hydrophobic toggles are booleans only (`true|false`).

### 14.2 API Payload Schemas (v1)

All async task endpoints must return canonical RQ submission payload:

```json
{
  "job_id": "rq-...",
  "status_url": "/rq-engine/api/jobstatus/rq-...",
  "message": "Job enqueued."
}
```

All error responses must use canonical envelope:

```json
{
  "error": {
    "message": "Human-readable summary",
    "code": "optional_code",
    "details": "details or stacktrace"
  },
  "error_id": "optional-correlation-id"
}
```

`GET /api/geneva/config` response:

```json
{
  "schema_version": 1,
  "enabled": true,
  "lambda_mode": "0.20|0.05",
  "uh_method": "scs_triangular|scs_curvilinear",
  "default_hsg_code": 2,
  "unresolved_hsg_policy": "error|assume_d",
  "strict_burn_nodata": false,
  "allow_cross_hsg_merge": false,
  "hydrophobic_forest_high": true,
  "hydrophobic_forest_moderate": false,
  "hydrophobic_shrub_high": true,
  "hydrophobic_shrub_moderate": false,
  "min_hru_area_ha": 2.0
}
```

`POST /api/geneva/config` request:

```json
{
  "enabled": true,
  "lambda_mode": "0.20|0.05",
  "uh_method": "scs_triangular|scs_curvilinear",
  "default_hsg_code": null,
  "unresolved_hsg_policy": "error|assume_d",
  "strict_burn_nodata": false,
  "allow_cross_hsg_merge": false,
  "hydrophobic_forest_high": true,
  "hydrophobic_forest_moderate": false,
  "hydrophobic_shrub_high": true,
  "hydrophobic_shrub_moderate": false,
  "min_hru_area_ha": 2.0
}
```

`POST /tasks/geneva/prepare_hrus` request:

```json
{
  "schema_version": 1,
  "force_rebuild": false
}
```

`GET /modify_geneva_cn_table` contract:

- Returns HTML for `controls/edit_csv.htm` backed by run-scoped `cn_table.csv`.

`POST /tasks/modify_geneva_cn_table` request:

```json
{
  "schema_version": 1,
  "if_match_sha256": "required-concurrency-token",
  "rows": []
}
```

Contract:

- `if_match_sha256` is required (disturbed parity).
- Save rejects stale or missing tokens with conflict/precondition responses.
- Server may also accept `X-If-Match-Sha256` header equivalent.

`GET /api/geneva/cn_table_meta` response:

```json
{
  "path": "geneva/data/cn_table.csv",
  "exists": true,
  "sha256": "hex",
  "rows": 0,
  "columns": 0,
  "schema_version": 1
}
```

`GET /api/geneva/cn_table_snapshot` response:

```json
{
  "meta": {
    "sha256": "hex",
    "rows": 0,
    "columns": 0
  },
  "rows": []
}
```

`POST /tasks/reset_geneva_cn_table` request:

```json
{
  "schema_version": 1,
  "confirm": true
}
```

`POST /tasks/geneva/build_frequency_panel` request:

```json
{
  "schema_version": 1,
  "durations_minutes": [5, 10, 30, 60, 120, 180, 360, 720, 1440],
  "ari_years": [1, 2, 5, 10, 25, 50, 100],
  "rebuild": false
}
```

`POST /tasks/geneva/run_batch` request:

```json
{
  "schema_version": 1,
  "batch_id": "optional-client-id",
  "event_filter": {
    "datasource_ids": ["cligen_freq", "noaa14_pds"],
    "durations_minutes": [5, 10, 30, 60, 120, 180, 360, 720, 1440],
    "ari_years": [1, 2, 5, 10, 25, 50, 100]
  },
  "hyetograph": {
    "distribution_type": "neh4_type_b",
    "time_step_minutes": 1.0
  },
  "runoff_model": {
    "lambda_mode": "0.20|0.05",
    "uh_method": "scs_triangular|scs_curvilinear",
    "timing_method": "kirpich|kent|simas"
  }
}
```

Rule:

- `event_filter` operates only on generated frequency-panel events; user-defined storm payloads are out of scope in v1.
- `hyetograph.distribution_type` must be `neh4_type_b` in v1.
- Reserved distribution IDs (`uniform`, `custom_breakpoint`) must return `400` with explicit unsupported-in-v1 diagnostics.
- Exactly one of `runoff_model.tc_hours` or `runoff_model.timing_method` must be provided and non-null.

`GET /api/geneva/status` response:

```json
{
  "status": "idle|prepared|running|completed|completed_with_gaps|failed",
  "status_message": "human-readable",
  "progress": {
    "completed": 0,
    "total": 0,
    "unit": "storms",
    "percent": 0.0,
    "updated_at": "2026-04-14T00:00:00Z"
  },
  "active_job_id": null,
  "last_job_id": null
}
```

`GET /api/geneva/results` response:

```json
{
  "status": "idle|prepared|running|completed|completed_with_gaps|failed",
  "last_prepare_summary": {
    "hru_count": 0,
    "hru_area_total_acres": 0.0,
    "hsg_provenance_counts": {}
  },
  "last_run_summary": {
    "batch_id": "string-or-null",
    "datasource_ids": ["cligen_freq", "noaa14_pds"],
    "storm_count_total": 0,
    "storm_count_completed": 0,
    "storm_count_failed": 0,
    "storm_count_unavailable": 0,
    "artifacts": {
      "batch_summary_relpath": "geneva/batch_summary.json",
      "frequency_panel_relpath": "geneva/frequency_panel.json"
    }
  },
  "warnings": [],
  "errors": []
}
```

`GET /api/geneva/frequency_panel` response:

```json
{
  "schema_version": 1,
  "datasource_ids": ["cligen_freq", "noaa14_pds"],
  "durations_minutes": [5, 10, 30, 60, 120, 180, 360, 720, 1440],
  "ari_years": [1, 2, 5, 10, 25, 50, 100],
  "cells": [
    {
      "storm_id": "noaa14_30m_25y",
      "datasource_id": "noaa14_pds",
      "duration_minutes": 30,
      "ari_years": 25,
      "depth_mm": 41.2,
      "intensity_mm_per_hr": 82.4,
      "availability": "available|unavailable",
      "reason_code": null
    }
  ],
  "warnings": []
}
```

Invariants:

- `availability=available -> reason_code=null`.
- `availability=unavailable -> reason_code in {duration_unavailable, ari_unavailable, source_missing}`.

`GET /query/geneva/summary` response:

```json
{
  "filters": {
    "datasource_id": "noaa14_pds|cligen_freq|all",
    "ari_years": [10, 25, 50],
    "measure": "peak_discharge|runoff_depth|runoff_volume"
  },
  "assumptions": {
    "arc_condition": "arc_ii",
    "storm_distribution_assumption": "neh4_type_b",
    "uniform_rainfall_assumed": true
  },
  "chart": {
    "x_axis": "intensity_mm_per_hr",
    "y_axis": "selected_measure",
    "series": []
  },
  "event_table": [],
  "warnings": []
}
```

`GET /report/geneva/summary` contract:

- Rendered HTML must embed one JSON payload with the same shape as `GET /query/geneva/summary`.

### 14.3 Artifact Schemas (v1)

- `geneva/frequency_panel.json`:
  - payload from `GET /api/geneva/frequency_panel`.
- `geneva/storm_inputs.json`:
  - normalized batch request, resolved datasource IDs, source artifact hashes.
- `geneva/storms/<storm_id>/summary.json`:
  - per-storm scalar metrics, warnings/errors, artifact paths, and assumptions metadata.
- `geneva/batch_summary.json`:
  - aggregate counts, extrema, failed storm IDs, warnings/errors, and per-source completion summary.
- `geneva/hru_table.parquet` fields include:
  - `hru_id`, `area_m2`, `area_ac`, `area_fraction`, `landuse_class`, `hsg_group`, `burn_severity_class`, `hydrophobic_class`, `cn_arc_ii`, `cn_lambda_020`, `cn_lambda_005`, `antecedent_condition_source`, `cn_source`, `hsg_source`, `collapsed_from_hru_ids`, `warnings`.
- `geneva/storms/<storm_id>/hyetograph.parquet` fields include:
  - `t_minutes`, `p_cum_mm`, `p_inc_mm`, `intensity_mm_per_hr`.
- `geneva/storms/<storm_id>/excess_hyetograph.parquet` fields include:
  - `t_minutes`, `qex_cum_mm`, `qex_inc_mm`.
- `geneva/storms/<storm_id>/hydrograph.parquet` fields include:
  - `t_minutes`, `q_cms`, `q_cfs`, `runoff_cum_mm`, `runoff_volume_m3`.

## 15. Conformance Acceptance Criteria (Must Pass Before “Implemented”)

1. RMRS Method Fidelity:
   - Distributed CN rainfall excess and unit-hydrograph transformation are both present.
2. NEH4B Availability:
   - NEH4 Type B is available as a first-class storm distribution option.
3. SCS UH Availability:
   - SCS unit hydrograph methods (`scs_triangular`, `scs_curvilinear`) are available in v1.
4. HRU Construction:
   - HRUs are derived from landuse + HSG + optional burn severity over `bound.tif`.
5. Hyetograph/Hydrograph Outputs:
   - Both are produced and persisted for each storm.
6. Batch Storm Support:
   - Multi-storm runs execute with per-storm summaries.
   - Frequency-panel matrix generation tracks available and unavailable storm cells explicitly.
7. Data Source Priority:
   - CLIGEN panel generation always runs; NOAA PDS panel generation runs when available; provenance is persisted for both.
8. WBT-Only Guard:
   - Non-WBT runs are rejected with clear messaging.
9. Scale Warnings:
   - Watershed-size warning behavior is enforced across warning/severe/extreme thresholds.
10. US-Only Enforcement:
   - Non-US or non-NLCD/HSG-compatible runs are rejected with explicit diagnostics.
11. Run-Scoped CN Editing:
   - `<runid>/geneva/data/cn_table.csv` is created at init, editable through `edit_csv.htm` flow, and consumed by CN resolution.
12. Default HSG Fallback:
   - Unresolved HSG handling follows `unresolved_hsg_policy`; fallback assignment uses `default_hsg_code` derived from dominant soil (or explicit override), with explicit warnings/provenance.
13. Interactive Report Usability:
   - Geneva summary report exposes datasource/ARI/measure filters with marker-to-event-table linkage.
14. Minimum HRU Area Enforcement:
   - HRUs below `2 ha` are collapsed per deterministic compatibility/selection rules, with area conservation and collapse provenance persisted.
   - For default `allow_cross_hsg_merge=false`, collapsed-vs-uncollapsed reference-case deltas must satisfy:
     - `runoff_depth` relative difference `<= 2%`,
     - `runoff_volume` relative difference `<= 2%`,
     - `peak_discharge` relative difference `<= 5%`.
   - If `allow_cross_hsg_merge=true`, collapsed-vs-uncollapsed reference-case runoff depth difference is `<= 2%`.
15. API/Schema Consistency:
   - Geneva task/query/report endpoints implement canonical payload schemas, canonical enum IDs, and canonical RQ/error contracts.
16. Assumption Disclosure:
   - Per-storm and batch outputs persist assumptions metadata needed for interpretation (ARC, distribution, rainfall uniformity, hydrophobic rule flags).
17. Unit-Safe UH Implementation:
   - UH implementation persists unit system and HF constant provenance, with SI/English parity tests passing.

## 16. Testing and Validation Plan (Initial)

Unit tests:

- HSG assignment and fallback policy behavior.
- Default-HSG fallback determinism and provenance fields.
- Minimum-HRU collapse logic with deterministic recipient selection and strict area conservation.
- HRU stacking/aggregation correctness.
- Burn nodata fallback handling and strict-mode failure behavior.
- CN runoff equation parity checks for both lambda options.
- NEH4B distribution generator regression tests.
- Frequency-panel event generation and filter-selection validation.
- SCS UH regression tests for both `scs_triangular` and `scs_curvilinear`.
- UH unit-system parity checks (`HF` constants and peak equation provenance).
- Area-weighted excess and hydrograph aggregation math.
- Guardrail negative tests in NoDb path for:
  - non-WBT runs (expected hard failure),
  - non-US/non-NLCD-HSG-compatible inputs (expected `unsupported_domain` failure).
- API schema validation for task/query/report payloads and canonical enum IDs.

Integration tests:

- End-to-end run on small WBT watershed with:
  - no burn severity input,
  - with burn severity input,
  - NOAA available,
  - NOAA unavailable (CLIGEN-only panel).
- Batch storms with mixed durations/return periods.
- Frequency-panel runs over `5m..24h` x `1..100` with partial availability handling.
- `ssurgo/hydgrpdcd` runs with unrated/unknown cells trigger `default_hsg_code` fallback as specified.
- `ssurgo/hydgrpdcd` speckle/noise cases produce no sub-`2 ha` HRUs after collapse.
- Default-collapse sensitivity test (`allow_cross_hsg_merge=false`) confirms:
  - runoff-depth delta `<= 2%`,
  - runoff-volume delta `<= 2%`,
  - peak-discharge delta `<= 5%` versus no-collapse reference cases.
- Cross-HSG merge sensitivity test (`allow_cross_hsg_merge=true`) confirms runoff-depth delta `<= 2%` on reference basins.
- Status lifecycle includes `completed_with_gaps` for partial-availability batches.
- Watershed-size warning (warning/severe/extreme thresholds) behavior.
- Dual-source panel behavior (CLIGEN always, NOAA when available) appears correctly in panel/results payloads.

Acceptance reference case:

- Reproduce RMRS-style example workflow pattern (storm + HRU CN mix + UH) with deterministic expected outputs.

### 16.1 Quantitative Acceptance Tolerances (Required)

CN and rainfall-excess kernels:

- Scalar CN transform checks (`S`, `CN_0.05`, `Q`) must satisfy absolute error `<= 1e-6`.
- HRU-weighted aggregation checks (`weighted_CN`, `Ia`) must satisfy absolute error `<= 1e-6`.

Storm construction:

- `neh4_type_b` cumulative depth ordinates must match reference within `0.1%` relative error.
- Final hyetograph depth closure must satisfy `|sum(dP)-depth_mm| <= max(0.01 mm, 0.1%)`.

UH and hydrograph:

- UH mass closure must satisfy `|integral(UH)-1| <= 0.005`.
- Hydrograph volume closure against excess volume must satisfy relative error `<= 1%`.

End-to-end storm parity (reference/golden cases):

- `peak_discharge` relative error `<= 5%`.
- `time_to_peak` error `<= 1` model timestep.
- `runoff_depth` and `runoff_volume` relative error `<= 2%`.

Interpretation note:

- Numerical tolerances validate implementation parity and numerical stability only.
- These tolerances are not predictive field-accuracy guarantees and must not be interpreted as site-specific certainty bounds.

Contract/determinism:

- Frequency-panel requested vs available matrix keys must match exactly expected key sets.
- Unavailable-cell `reason_code` values must match expected values exactly.
- Deterministic artifacts must be byte-stable except timestamps/job IDs.

## 17. Open Design Decisions (Tracked)

- Whether v1.1 should promote automatic grass burn augmentation from user-optional to default-on behavior.
- Dual-HSG drainage policy (`A/D`, `B/D`, `C/D`) when drainage state is unknown.
- Whether reservoir routing enters v2 or remains external.
- Whether v1.1 should add preset templates beyond the canonical full panel (`5m..24h` x `1..100`) for faster BAER workflows.

## 18. References

- USDA Forest Service. 2016. RMRS-GTR-334.  
- USDA NRCS. National Engineering Handbook, Part 630 (Hydrology).  
- USDA SCS. NEH Section 4 and TR-55 hydrology references.
- USDA NRCS. 2016. Hydrology Technical Note 210-4, *Hydrologic Analyses of Post-Wildfire Conditions*.

## 19. Wildcat5 Macro Reuse Assessment (Geneva Context)

### 19.1 Directly Usable as Algorithm Reference (Port and Test)

Primary module:

- `resources/Wildcat5/extracted_macros/wildcat5dec072015-64bits/wildcat.bas`

Routines that are directly relevant to Geneva v1:

- CN core transforms and variants:
  - `GetS`, `GetS2`, `GetCN_S`, `GetCN_PQ`, `GetCN5`, `GetCN5_QP`, `GetCN2After`
- HRU-weighted CN initialization and Ia derivation:
  - `Initial_Parameters_CN`, `Calculate_Ia_fraction`
- Storm distributions:
  - `SCS_TypeB`, `Farmer_Fletcher`, `Uniform_Storm`, `Custom_Storm`, `Generic_Storm`
- Rainfall excess generation:
  - `GetQ_fromP_Ia`, `WtCNQ`, `Calculate_Q_ContribArea`
- UH generation and hydrograph routing kernels:
  - `Set_UHData_original`, `get_UHbyType`, `get_CurvilinearUH`, `get_brokenUH`, `Generate_Synthetic_RunOff`

Supporting formulas from:

- `resources/Wildcat5/extracted_macros/wildcat5dec072015-64bits/funcs.bas`
  - `CalcTimeCon`, `Calc_SIMAS_Tl`, `GetValueTo_CN5`, `Weighted_CN`

Porting requirement:

- Preserve math intent while removing Excel sheet coupling and global mutable state.

### 19.2 Conditionally Usable (Reference Only for v2+)

Module:

- `resources/Wildcat5/extracted_macros/wildcat5dec072015-64bits/routing.bas`

Relevance:

- Reservoir routing logic (`RunRouting`, `Routing_And_MaximumQ`) is useful for a later Geneva reservoir-routing phase.
- Not required for Geneva v1 scope.

### 19.3 Not Usable as Runtime Code

Not usable directly for Geneva backend implementation:

- Workbook/sheet classes (`Sheet*.cls`, `ThisWorkbook.cls`)
- User forms (`fr*.frm`)
- Navigation/file dialog/UI glue (`Module1.bas`)
- Project text I/O convenience wrappers (`ModuleIO.bas`) as runtime contract

Reason:

- These are Excel/VBA UI orchestration layers with hardcoded cell references and side effects, not backend-safe model kernels.

### 19.4 Quality Caveats for Porting

Observed caveats in extracted VBA:

- Heavy reliance on global state and worksheet cells.
- No `Option Explicit` in core hydrology modules (`wildcat.bas`, `funcs.bas`, `routing.bas`).
- UI/report-label branches contain inconsistencies (treat report text as non-authoritative).

Therefore:

- Use equations/coefficients from routines, not worksheet label text.
- Require parity tests against controlled benchmark cases before declaring conformance.
