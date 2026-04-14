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
- Storm depth/intensity support using NOAA Atlas 14 PDS when available, with CLIGEN-derived frequency fallback.
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
- SCS TR-55 texture-based HSG shortcuts are allowed only as explicit fallback with warnings.

Conformance posture:

- RMRS-GTR-334 alignment is normative for method family and workflow sequence.
- Where RMRS gives multiple options, this spec defines a default and explicitly names optional alternatives.
- Any divergence must be logged in a `Conformance Deviations` section before implementation.

### 3.1 Wildcat5 Source Artifacts and Legal Posture

Wildcat5 source artifacts are staged under:

- `wepppy/nodb/mods/geneva/resources/Wildcat5/`
- extracted VBA modules under:
  - `wepppy/nodb/mods/geneva/resources/Wildcat5/extracted_macros/wildcat5dec072015-64bits/`

For this project, Wildcat5 workbook/macro content is treated as public domain per project context and local notes in:

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
  - suggest user override workflow only after explicit acknowledgement.

## 5. Input Contract

Required inputs:

- Watershed boundary raster: `bound.tif` aligned to run DEM grid.
- Landuse raster aligned to watershed grid (US NLCD classes for v1).
- Soil/HSG source aligned to watershed grid or mappable to it.
- One or more storm definitions.

Optional inputs:

- Burn severity raster (SBS-like classes). If absent, HRUs are based on landuse + HSG only.
- User HRU merge threshold (minimum HRU area fraction).
- User overrides for CN lookup rows.

Required run metadata:

- CRS, cellsize, nodata policy for each source raster.
- Watershed area (`wsarea`) in SI and English units.
- Data provenance for all lookup tables used.

### 5.1 Run-Scoped CN Table Initialization

On Geneva initialization (or first Geneva enablement), the backend must create:

- `<runid>/geneva/data/cn_table.csv`

from module seed data:

- `wepppy/nodb/mods/geneva/data/geneva_cn_table_us_v1_seed.csv`

Contract:

- `cn_table.csv` is run-scoped and mutable by the user.
- If `cn_table.csv` is missing, Geneva recreates it from the seed and emits a warning/audit event.
- If the seed schema version changes, Geneva performs explicit migration or fails with actionable schema diagnostics.

Initial schema (v1):

- `nlcd_class`
- `nlcd_label`
- `hsg` (`A|B|C|D`)
- `burn_severity` (`unburned|low|moderate|high`)
- `hydrophobic` (`true|false`)
- `cn_arc_ii`
- `source`
- `notes`

Seed intent:

- Static no-burn rows for all core NLCD classes.
- Burn-severity rows for forest/shrub classes (`NLCD 41, 42, 43, 52`) across HSG groups.
- Hydrophobic rows for moderate/high forest/shrub cases.

## 6. HSG Determination Contract

HSG assignment must be explicit, source-aware, and auditable.

Priority:

1. NRCS-derived HSG attributes (when available and mappable).
2. Dataset-specific hydrologic group codebooks (when integer-coded rasters are used and codebook is present).
3. Texture-based fallback (TR-55 style) only when no direct HSG is available.

Rules:

- Do not assume integer HSG code meaning without a dataset codebook/version reference.
- Record `hsg_source` per HRU (`nrcs_direct`, `coded_lookup`, `texture_fallback`, `user_override`).
- Emit warnings for any fallback HSG assignment.
- Unknown/unrated HSG handling policy must be configurable:
  - `error` (default): fail with actionable diagnostics.
  - `assume_d`: coerce unknown cells to `D` and emit warning counts + area affected.

Water handling:

- Open-water classes must be represented as explicit HRUs (not dropped silently).
- Water HRUs default to `CN = 100` unless user explicitly overrides.

## 7. HRU Derivation Contract

HRUs are raster-derived unique combinations over in-bounds cells:

- key = `(landuse_class, hsg_group, burn_severity_class?)`
- burn severity dimension is included only when the burn raster is provided/enabled.

Processing:

1. Mask all sources by `bound.tif`.
2. Align to a common analysis grid.
3. Compute cell counts and area fractions for each unique key.
4. Attach CN from canonical lookup tables.
5. Apply optional HRU collapsing (merge below minimum area threshold into nearest compatible class).

HRU table minimum fields:

- `hru_id`
- `area_m2`, `area_ac`, `area_fraction`
- `landuse_class`
- `hsg_group`
- `burn_severity_class` (nullable)
- `cn_arc_ii`
- `cn_lambda_020`
- `cn_lambda_005` (derived when needed)
- `cn_source`
- `hsg_source`
- `warnings` (array or count summary)

## 8. CN and Rainfall Excess Contract

### 8.0 CN Lookup Table Usage (Run-Scoped)

Geneva does not hardcode CNs in logic. CN lookup resolves through run-local:

- `<runid>/geneva/data/cn_table.csv`

Selection key:

- `(nlcd_class, hsg, burn_severity, hydrophobic)`

Resolution rules:

1. Exact row match required for forest/shrub burn rows in v1.
2. If burn severity is absent, use `burn_severity = unburned`.
3. If hydrophobic flag is false/unknown, use `hydrophobic = false`.
4. Missing row policy defaults to explicit error with a diagnostic listing missing keys and affected area.

### 8.1 CN Equations

Default runoff equation (`Ia/S = 0.20`):

- `Q = (P - 0.2S)^2 / (P + 0.8S)` for `P >= 0.2S`, else `Q = 0`
- `S = 1000/CN - 10` (inch-form equivalent), with unit-consistent implementation in SI runtime.

Optional alternative:

- `Ia/S = 0.05` using converted CN (`CN_0.05`) derived from `CN_0.20` per RMRS guidance.

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

Important conformance note:

- RMRS-GTR-334 states post-fire CN tables are compiled practice guides and should be treated as suggestions with local judgment; Geneva must preserve user editability and provenance for this reason.

Grass question (v1 position):

- Canonical guidance indicates grass/herbaceous CN can be fire-adjusted (RMRS Tables 4-10 to 4-13 include annual-grass burn classes; NRCS post-wildfire technical note includes herbaceous severity-specific CNs).
- Geneva v1 seed keeps non-forest/non-shrub classes static unless users edit `cn_table.csv`; grass burn augmentation is therefore user-driven in v1, not auto-enforced by code.

## 9. Storm Contract (Including NEH4 Type B)

Each storm record must include:

- `storm_id`
- `depth` (mm)
- `duration` (hours)
- `distribution_type` (`neh4b`, `uniform`, `custom_breakpoint`, later extensions)
- `distribution_payload` (if custom)
- recurrence metadata when sourced from frequency tables (`ari_years`, datasource)

Required distribution support in v1:

- `neh4b` (NEH4 Type B / SCS Type B) as first-class built-in option.

Batch support:

- Requests may include `storms: []`.
- Execution produces per-storm artifacts and one batch summary.
- Failures are isolated per storm when possible; batch result must report per-storm status.

## 10. Storm Depth/Frequency Source Priority

When user selects frequency-derived storms:

1. NOAA Atlas 14 PDS (preferred when available for watershed centroid).
2. CLIGEN-derived precip frequency estimates from `wepp_cli.parquet` artifacts.

Rules:

- Store source provenance per storm (`source`, `version`, `lat/lon`, timestamp).
- If NOAA is unavailable, fallback to CLIGEN and emit clear warning.
- If neither source is available, fail with actionable message.

## 11. Hydrograph Contract

Geneva must produce both:

- Hyetograph outputs:
  - raw rainfall intensity/depth vs time,
  - composite rainfall excess vs time,
  - optional per-HRU excess traces.
- Hydrograph outputs:
  - outlet discharge vs time (composite),
  - summary metrics (`peak_flow`, `time_to_peak`, `runoff_volume`, `runoff_depth`).

Unit hydrograph requirement:

- Use a supported UH method (default simple triangular UH).
- Keep UH settings explicit in artifacts and API payloads.
- Include timing parameter source (user provided or computed method) in run metadata.

## 12. Watershed Size Warnings and Guardrails

Because RMRS/Wildcat methods target small watershed event analyses, Geneva must emit scale warnings.

Configurable thresholds (defaults):

- `warning_area_km2 = 25`
- `severe_warning_area_km2 = 100`
- `hard_limit_area_km2 = 250` (unless explicit override flag is set by privileged caller)

Behavior:

- Exceed warning thresholds: run allowed, warnings persisted and shown in UI/report.
- Exceed hard limit: fail with explicit message unless override is enabled.
- Warning payload includes area in `km2`, `mi2`, and `acres`.

## 13. NoDb Integration Blueprint

Planned module path:

- `wepppy/nodb/mods/geneva/`

Planned controller:

- `class Geneva(NoDbBase)`
- filename: `geneva.nodb`

Minimum persisted state:

- `enabled`
- `status` (`idle|prepared|running|completed|failed`)
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

## 14. API/Task Sketch

Expected route family (patterned after existing NoDb mods):

- `POST /runs/<runid>/<config>/tasks/set_mod` with `{"mod":"geneva","enabled":true|false}`
- `GET|POST /runs/<runid>/<config>/api/geneva/config`
- `POST /runs/<runid>/<config>/tasks/geneva/prepare_hrus`
- `POST /runs/<runid>/<config>/tasks/geneva/run_batch`
- `GET /runs/<runid>/<config>/modify_geneva_cn_table` (renders `controls/edit_csv.htm`)
- `POST /runs/<runid>/<config>/tasks/modify_geneva_cn_table`
- `GET /runs/<runid>/<config>/api/geneva/cn_table_meta`
- `GET /runs/<runid>/<config>/api/geneva/cn_table_snapshot`
- `POST /runs/<runid>/<config>/tasks/reset_geneva_cn_table`
- `GET /runs/<runid>/<config>/api/geneva/status`
- `GET /runs/<runid>/<config>/api/geneva/results`
- `GET /runs/<runid>/<config>/query/geneva/summary`
- `GET /runs/<runid>/<config>/report/geneva/summary`

Execution mode:

- Queue-backed (`RQ`) for HRU prep and storm batch runs.
- Explicit per-storm status and warning propagation in job results.

## 15. Conformance Acceptance Criteria (Must Pass Before “Implemented”)

1. RMRS Method Fidelity:
   - Distributed CN rainfall excess and unit-hydrograph transformation are both present.
2. NEH4B Availability:
   - NEH4 Type B is available as a first-class storm distribution option.
3. HRU Construction:
   - HRUs are derived from landuse + HSG + optional burn severity over `bound.tif`.
4. Hyetograph/Hydrograph Outputs:
   - Both are produced and persisted for each storm.
5. Batch Storm Support:
   - Multi-storm runs execute with per-storm summaries.
6. Data Source Priority:
   - NOAA PDS preference with CLIGEN fallback works and is logged.
7. WBT-Only Guard:
   - Non-WBT runs are rejected with clear messaging.
8. Scale Warnings:
   - Watershed-size warnings/hard-limit behavior is enforced.
9. US-Only Enforcement:
   - Non-US or non-NLCD/HSG-compatible runs are rejected with explicit diagnostics.
10. Run-Scoped CN Editing:
   - `<runid>/geneva/data/cn_table.csv` is created at init, editable through `edit_csv.htm` flow, and consumed by CN resolution.

## 16. Testing and Validation Plan (Initial)

Unit tests:

- HSG assignment and fallback policy behavior.
- HRU stacking/aggregation correctness.
- CN runoff equation parity checks for both lambda options.
- NEH4B distribution generator regression tests.
- Area-weighted excess and hydrograph aggregation math.

Integration tests:

- End-to-end run on small WBT watershed with:
  - no burn severity input,
  - with burn severity input,
  - NOAA available,
  - NOAA unavailable (CLIGEN fallback).
- Batch storms with mixed durations/return periods.
- Watershed-size warning and hard-limit enforcement.

Acceptance reference case:

- Reproduce RMRS-style example workflow pattern (storm + HRU CN mix + UH) with deterministic expected outputs.

## 17. Open Design Decisions (Tracked)

- Whether v1.1 should promote automatic grass burn augmentation from user-optional to default-on behavior.
- Dual-HSG drainage policy (`A/D`, `B/D`, `C/D`) when drainage state is unknown.
- Whether reservoir routing enters v2 or remains external.
- UI defaults for storm batch templates (for example 2-, 5-, 10-, 25-, 50-, 100-year sets by duration).

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
