# Postfire Debris Flow Specification

Status: updated 2026-09-10. Production M1 NoDb, upload, prerequisite/freshness,
RQ execution and minimal UI are implemented under the
[production contract](docs/production_m1.md). Development validation passed; deployment to other hosts is not implied. M3 production integration
and reports/dashboard remain deferred.

Track delivery stages, evidence, and unresolved decisions in the living
[implementation roadmap](implementation_roadmap.md). Update this specification
and affected detailed contracts alongside the roadmap in each implementation
change. The roadmap tracks progress; it does not ratify proposed behavior or
replace the required contract-first checkpoint.

## Accepted Direction and Rationale

| Decision | Rationale |
| --- | --- |
| Separate `PostfireDebrisFlow` NoDb module and Pure UI control | Keep model inputs, execution, and results together while preserving the older debris-flow controller and saved runs. |
| Assess the existing project watershed at its existing user-selected outlet | Reuse the completed delineation. Users should manually isolate burned basins they suspect may be at risk; nested/channel assessments are outside initial implementation. |
| Follow RUSLE documentation and source organization | Reuse established module, numerical-helper, integration, UI, and reference-bundle conventions. |
| Support WBT only | Reuse the owned terrain and watershed stack; no TOPAZ integration in the new module. |
| Require a completed WEPP Soils build for both models | Projects prepare soil data before postfire assessment; reuse the Soils inventory and provenance rather than building a parallel soil acquisition workflow. |
| Limit availability to the continental US (CONUS) locale | The model is empirical and the initial integration is limited to the conterminous United States; Western US intended-use guidance remains mandatory. |
| Support SI and English unitization in UI and reports | Follow project unit preferences while preserving the calibrated equation units and identical model results. |
| Implement M1 and M3, with M1 default and explicit M3 selection | M1 is the publication's recommended model; M3 offers a formulation without dNBR. Do not silently switch models for missing inputs. |
| Depend on RUSLE preparation/UI for M1 K | Reuse POLARIS Nomograph K generation, configuration, and provenance instead of a duplicate soil estimator. |
| Require SBS and derive moderate/high coverage directly | Use spatial severity classes rather than unrelated watershed summary proxies. |
| Follow SBS upload conventions for dNBR, with project-grid normalization | Accept differing source extents, projections, resolutions, and value scales; avoid requiring users to pre-align rasters. |
| Accept partial dNBR coverage when valid data overlap the watershed | Retain usable observations and expose missing coverage rather than requiring complete watershed coverage. |
| Derive code independently from published science | Preserve WEPPpy licensing without importing or translating GPL pfdf implementation or tests. |

The RUSLE dependency is established for M1's K artifact. M1 requires the named K artifact and its own current provenance, not completion
of the full RUSLE model. M3 prerequisite policy remains open.

## Scientific Model

Staley et al. (2017), equations 4-6 and Table 4, define:

```text
x = B + R * (Ct*T + Cf*F + Cs*S)
p = 1 / (1 + exp(-x))
R_p = (log(p / (1-p)) - B) / (Ct*T + Cf*F + Cs*S)
I_p = R_p / duration_hours
```

`R` is rainfall accumulation in mm for the coefficient duration; `I_p` is
mm/hour. `p` is a probability, not a percentage. The accepted
[numerical engine contract](docs/staley2017_engine.md) and
[ADR-0056](../../../../docs/adrs/ADR-0056-staley-numerical-engine.md) define scalar
validation, stable arithmetic, and inverse equality/unavailability policies.
RUSLE annual erosivity R is a different quantity and must not be used as Staley
rainfall.

### Model selection increment (2026-09-11)

The owner requested a shared M1/M3 header comparison, side-by-side model radios,
M1-only dNBR/K controls and an M3-only Soils prerequisite. Accepted presentation,
model-aware task transport/state compatibility and remaining integration decisions are
recorded in [model selection](docs/model_selection.md). Implementation and the
reviewed contract checkpoint remain pending; production still executes M1 only.

### Predictors

| Predictor | M1 | M3 |
| --- | --- | --- |
| T | Fraction of contributing area both moderately/highly burned and slope >=23 degrees | Maximum upstream raw elevation minus outlet elevation / square root of total upstream area |
| F | Mean contributing-area dNBR / 1000 | Fraction of contributing area moderately/highly burned |
| S | Mean contributing-area Kf; proposed integration uses RUSLE POLARIS Nomograph estimate | Mean contributing-area cumulative soil-layer thickness in inches / 100; SSURGO derivation under evaluation |

Fractions are 0-1, not percentages. M1 uses a spatial intersection of slope
and severity, not the product of their separate fractions. dNBR is the
continuous prefire-minus-postfire NBR difference, not classified SBS, RdNBR,
or an automatically updated recovery index. Preserve imagery dates,
assessment timing, and raster scaling; dividing already normalized dNBR by
1000 again would be incorrect.
The proposed standardized raster stores normalized NBR differences, so its
catchment mean directly supplies F; see the dNBR upload contract below.

### Published Coefficients

Verified against Table 4 in the local accepted manuscript; see the
[publication check](../../../../docs/work-packages/20260908_staley_watershed_engine/artifacts/coefficient_check.md)
and ADR-0056.

| Model | Duration (min) | B | Ct | Cf | Cs |
| --- | --- | --- | --- | --- | --- |
| M1 | 15 | -3.63 | 0.41 | 0.67 | 0.70 |
| M1 | 30 | -3.61 | 0.26 | 0.39 | 0.50 |
| M1 | 60 | -3.21 | 0.17 | 0.20 | 0.220 |
| M3 | 15 | -3.71 | 0.32 | 0.33 | 0.47 |
| M3 | 30 | -3.79 | 0.21 | 0.19 | 0.36 |
| M3 | 60 | -3.46 | 0.14 | 0.10 | 0.18 |

The study used 10 m DEMs and catchments of 0.2–8 km², with observations within
the first two years after fire in the western United States. These describe
the evidence domain. Availability is CONUS-only as specified below; an age
warning/rejection policy remains open.
Source authority (owner decision, 2026-09-09 UTC): use the operator-provided
accepted manuscript, printed page 12, as authoritative for this study range.
Its explicit 0.2–8 km² statement supersedes the earlier unsupported 0.02–8 km²
transcription; no final-journal reconciliation is required for this decision.
The numerical engine consumes explicit predictors and does not enforce
catchment size.

Area warning policy (owner decision, 2026-09-09 UTC): for either model, warn
when the full delineated watershed area is below 0.2 km² or above 8 km².
The endpoints are included in the study range and do not trigger this warning.
Compare unrounded canonical area in m² against 200,000 and 8,000,000; display
unit preferences and rounding must not change the warning decision.
Allow assessment and preserve calculated probabilities and inverse results;
area outside the range alone must not fail readiness, reject execution, or
make results unavailable. Present the warning with results and reports, for
example: "Watershed area is outside the study's 0.2–8 km² range. Results
extrapolate beyond the reported study areas."
This warns about the evidence domain without treating it as a validated
physical limit. [ADR-0057](../../../../docs/adrs/ADR-0057-staley-area-range-warning.md)
records the decision. Runtime warning integration belongs to the forthcoming
project assessment/results workflow; the scalar engine has no area input.

The authors recommend M1 and found 15-minute thresholds most accurate overall.
M3 is an alternative formulation, not a model assigned to a particular region.

## Availability and Soils Readiness

Both models require WBT, a CONUS locale, and a completed Soils controller build
with populated, readable project soil artifacts. A controller file existing
without built data does not establish readiness. Show the missing prerequisite
in the UI and reject bypassed submissions at the server boundary. The postfire
job consumes prepared soil data; it must not silently initiate a soil rebuild.

Interpret continental US here as the conterminous lower 48 states and DC,
excluding Alaska, Hawaii, territories, and non-US projects. Resolve eligibility
through the existing project-config/effective-locale authority, not labels or
interface filenames. Legacy configs commonly use `locales = ["us"]`; determine
their canonical CONUS mapping before implementation. Do not introduce locale
metadata into the config registry, which explicitly does not own that authority.
Exact cross-boundary footprint handling remains to be specified.

UI guidance and reports must explain: "Empirical postfire debris-flow model
intended for recently burned watersheds in the Western United States.
Availability elsewhere in CONUS does not establish local validation."
Include the source study's first-two-years, catchment-size, and terrain-data
context. Western US is intended-use guidance, not an additional hard regional
gate at this stage.

M1 also requires the RUSLE Nomograph K artifact and continuous dNBR. M3 requires
a valid thickness derivation; a successful WEPP soil build alone does not prove
that historical/custom/fallback runs contain suitable raw SSURGO horizons.

## M3 Soil Thickness: SSURGO Feasibility

Finding (2026-09-08): SSURGO can supply a comparable cumulative profile-thickness
estimate using raw component/horizon records already cached by current Soils
builds. It is a substitute source requiring comparison with the original
STATSGO predictor, not demonstrated calibration parity. See the detailed
[SSURGO feasibility assessment](docs/ssurgo_m3_feasibility.md).

The [M3 soil work package](../../../../docs/work-packages/20260908_staley_m3_soils/package.md)
scopes source inventory, reproducible offline derivation, and a fixed-10 m
comparison against original STATSGO THICK. The user requested this follow-up
after terrain completion; it resolves soil-source suitability independently
of terrain resolution. The subsequent owner decision selects **SSURGO as
primary and original STATSGO THICK as fallback**. Prefer the more detailed
SSURGO soil information where usable and retain STATSGO for broader coverage.
Differences from STATSGO do not establish that SSURGO is less accurate.

Source priority is accepted; runtime integration remains pending. Fallback must
be explicit in output provenance and coverage reporting. The fallback unit
(component, map unit, cell, or catchment), usability criteria, material policy,
and incomplete-component handling remain to be specified. A nonmissing STATSGO
pixel is not proof of complete underlying component observations; validate its
NoData/nonphysical values too. Do not apply the offline 100% support criterion
as an approved production gate. No live soil rebuild is authorized by this
source-priority decision.

The original STATSGO `THICK` is cumulative layer thickness in **inches**, not
centimeters, depth to bedrock, or WEPP's modeled profile depth. Thus:

```text
thickness_in = thickness_cm / 2.54
S = catchment_mean(thickness_in) / 100
  = catchment_mean(thickness_cm) / 254
```

Use raw horizon top/bottom depths in cm to derive component thickness after
validating interval topology and soil-versus-bedrock classification. Component
percentage weighting followed by contributing-area weighting is the proposed
map-unit/catchment method. The exact duplicate, overlap, gap, bedrock, incomplete
component, and coverage rules need ratification and a parameterization ADR.

Do not reuse generated `.sol` depth or `SurgoSpatializer`'s current `SolThk`:
the former can be clipped/adjusted, and the latter sums cumulative bottom
depths rather than layer thicknesses. Do not substitute a POLARIS depth interval
or numeric zero for missing thickness. Missing/invalid source data must remain
explicit; partial-coverage acceptance thresholds are not yet approved.

## Offline M3 Soil Evaluation Contract

The [version 1 offline soil contract](docs/m3_soil_thickness.md)
and [ADR-0053](../../../../docs/adrs/ADR-0053-staley-m3-offline-soil-thickness.md)
define the study helper before executable implementation. This contract applies
only to offline raw-record derivation and diagnostics. No live Soils build,
NoDb/UI/RQ integration or partial-coverage availability threshold is
established by the offline contract. The owner has separately approved the
SSURGO-primary/STATSGO-fallback direction above. Strict soil and all-recorded-layer
sensitivities remain scientifically distinct.

## RUSLE and POLARIS Dependency

Current RUSLE behavior is documented in [its specification](../rusle/specification.md).
Its UI can build `polaris_nomograph`, `polaris_epic`, or both and select a
default K for RUSLE soil loss. Our agreed starting input for M1 is Nomograph;
EPIC is not automatically enabled for Staley by its availability in RUSLE.

- Named input: `rusle/k_polaris_nomograph.tif`.
- Standard RUSLE builds do not create the lower-level helper's `rusle/k.tif` alias.
- K inputs use POLARIS mean layers over 0-15 cm, with 5:10 thickness weights.
- Nomograph infers structure/permeability and very fine sand; optional profile
  coarse fragments can modify permeability. This is an estimate, not a direct
  STATSGO Kf extraction or WEPP Ki/Kr substitution.
- Record source mode, depth treatment, fragment adjustment, units, gap filling,
  and artifact identity. The verified Nomograph scale maps to S with multiplier 1
  (ADR-0059); full finite [0,1] K support and provenance are required for point S.
  Partial K mean remains diagnostic, with no additional gap filling. Named K
  readiness is independent of unrelated RUSLE factors; completed WEPP Soils
  remains a production prerequisite. See [local contract](docs/m1_predictors.md).
- Changing K invalidates M1 results under the implemented
  [production freshness contract](docs/production_m1.md#owner-completion-and-recovery-conformance).

## Terrain, SBS, and Assessment Scope

Use real contributing catchments for aggregation. The existing WBT-side
`Watershed._compute_ruggedness_from_dem` uses DEM rectangle statistics/area;
it is not sufficient evidence of a Staley-compatible catchment calculation.

For M3, pfdf evaluates `relief / sqrt(area)` in consistent length units, which
is dimensionless. The local manuscript's section 5.2 prose omits the square root; pfdf
documentation also alternates between nearest and highest ridge and incorrectly
labels units in one method docstring. The user resolved the engineering definition below, and the owned WBT
implementation was verified against analytical fixtures and full catchment
counts/extrema. See [M3 terrain evaluation](docs/m3_terrain.md) for the
accepted contract, implementation limitations and resolution findings.

Accepted direction (2026-09-08): implement the terrain tooling in
weppcloud-wbt, then evaluate matched 10 m/30 m catchments to determine M3
resolution requirements. This keeps raster traversal in the owned Rust backend
and makes resolution acceptance evidence-based. Execution is scoped in the
[terrain work package](../../../../docs/work-packages/20260908_staley_m3_wbt_terrain/package.md);
the accepted formula and measured resolution recommendation are recorded below.

Discovery finding (2026-09-09): pinned pfdf 3.0.2/pysheds 0.4 returns 25 m
where a descending synthetic catchment has 30 m relief under all candidate
physical definitions. Raw-elevation alternatives also disagree with each other
under conditioned routing. The reference therefore cannot ratify the formula;
see [diagnostic evidence](../../../../docs/work-packages/20260908_staley_m3_wbt_terrain/artifacts/reference_parity.md)
and [ADR-0052](../../../../docs/adrs/ADR-0052-staley-m3-upstream-terrain.md).
The user subsequently adopted maximum upstream raw elevation minus outlet
elevation as the engineering contract. Include the outlet in the upstream
maximum and in area; use raw meter elevations with supplied conditioned D8
routing, A in m2, and T=H/sqrt(A). This choice includes internal raw maxima
and measures relief relative to the actual assessment outlet. Highest-source
and catchment-max-minus-min alternatives are rejected for these reasons.
Calibration-preprocessing equivalence remains unproven; 30 m acceptance still
requires the resolution study. ADR-0052 records decision provenance.

The completed terrain evaluation recommends requiring genuine 10 m for initial
M3 support. Across 24 outlet pairs, controlled 30 m effects reached 10.598
probability percentage points and 12.479% inverse-threshold change, exceeding
the predeclared 5-point/10% engineering screen. Larger sampled catchments
agreed closely, but the panel does not justify a universal 30 m size exemption.
See [resolution findings](../../../../docs/work-packages/20260908_staley_m3_wbt_terrain/artifacts/resolution_decision.md).
This recommendation is not implemented UI/server enforcement and does not
establish predictive validity or CONUS-wide calibration.
For illustration below the study's minimum area, a hypothetical 0.02 km²
catchment has approximately 200 and 22 cells respectively.
Upsampling a 30 m DEM does not establish 10 m terrain fidelity.

### Project Watershed Assessment Scope

Accepted owner decision (2026-09-09 UTC): assess the watershed already delineated
by the project, using its existing user-selected outlet as resolved by the
canonical WBT workflow. One project supplies one assessment domain per model.
Do not require a second delineation, additional outlet selection, automated
burned-basin extraction, or per-channel/nested catchment enumeration.
Use the full delineated upstream area, including channels and unburned portions;
do not clip the assessment to the fire perimeter, valid dNBR footprint, or
individual WEPP hillslopes. Confirm the canonical mask/grid and resolved outlet
cell in the implementation contract rather than silently snapping a new outlet.

User guidance in the control and reports: manually isolate a burned basin that
you suspect may be at risk for debris flows when creating the project. Place
the project outlet to delineate that basin. This basin-selection guidance does
not establish predictive validity or replace the study's area, age, and regional
context. The result is a basin assessment for the selected rainfall scenario,
not an aggregate probability of a debris flow occurring anywhere in a larger
landscape and not a runout prediction.

[ADR-0055](../../../../docs/adrs/ADR-0055-staley-project-watershed-scope.md)
records why the earlier per-channel proposal was rejected for initial delivery.
Nested assessments would require a separately approved scope change. Existing
offline helpers and evaluation fixtures may retain multiple masks/outlets for
testing; that capability is not a production workflow requirement.

The owner requested slope/SBS intersection tooling in weppcloud-wbt. The
[slope/SBS backend contract](docs/slope_sbs.md) and
[implementation package](../../../../docs/work-packages/20260908_staley_slope_sbs/package.md)
cover algorithm selection, raw-versus-conditioned terrain, class mapping,
coverage and owned Rust tooling. The owner adopted Horn 3×3 surface slope in
[ADR-0058](../../../../docs/adrs/ADR-0058-staley-horn-slope.md). Execution selects raw project elevation with strict nine-valid-cell neighborhoods;
original Staley slope preprocessing equivalence is not established.
[Historical source evidence](docs/historical_slope_evidence.md) now confirms
ArcGIS planar/Horn-style slope in the preserved 2022-named USGS M1 workflow,
followed by a 2023 migration to pysheds. The inspected modern helper uses
directional slope: treat that as a suspected predictor-preprocessing regression,
not a calibration reference. Exact 2017 tooling and predictive impact remain
unconfirmed.
Existing D8 flow-vector slope and WBT's projected Florinsky 5×5 Slope are
separate algorithms, not approved substitutes by their availability alone.
The owner accepted preserving incomplete-intersection uncertainty: report
coverage and full-watershed T bounds; publish point T only when no intersection
cells remain unknown. Do not replace it with an observed-support estimate.
The additive StaleySlopeSbs backend and both bindings are implemented and
validated locally; production M1 preparation/publication is implemented under
the [production contract](docs/production_m1.md).

The [local backend contract](docs/slope_sbs.md) fixes slope, explicit SBS class
mapping and whole-watershed support. Any future resampling/preparation workflow
requires its own integration contract. Missing SBS pixels
must not silently become unburned observations.

Canonical artifact mapping (verified 2026-09-09 UTC): `Watershed.bound` supplies
`dem/wbt/bound.tif`, produced by WBT from the existing D8 pointer and resolved
`dem/wbt/outlet.geojson`. Use its valid positive routed cells, including channel
cells, as the full assessment support. Validate that the resolved outlet is in
that support and matches its recorded row/column and projected cell center.
Do not use requested outlet coordinates to select a different cell.

Reuse the raw project DEM (`Watershed.dem_fn`) grid exactly: CRS, affine
transform, shape and extent. Resolve D8 pointer format through the existing WBT
property (`flovec.tif` or `flovec.vrt`). On a projected meter grid, cell area is
the absolute affine determinant in m²; full area is cell count times cell area.
Require explicit unit handling for other grids rather than assuming square
meters. M3 elevation remains raw DEM elevation, not conditioned WBT `relief`.

The derived `bound.geojson` and `bound.WGS.geojson` are display views;
user-drawn boundaries and outlet-selection masks are not the routed domain.
Outlet JSON `outlet_in_mask` and `watershed_cell_count` describe an optional
selection mask and must not replace direct checks of the completed routed mask.
Grid disagreement, an outlet outside support, or boundary-touch diagnostics
must be reported without implicit re-snapping or re-delineation. The existing
WBT boundary policy remains authoritative; this audit adds no rejection cutoff.

The [read-only fixture audit](../../../../docs/work-packages/20260908_staley_watershed_engine/artifacts/watershed_artifact_audit.md)
checks grid identity, 49,917 routed cells, outlet inclusion, polygon agreement
and source hashes. This mapping establishes reuse; slope/SBS/K aggregation and
scientific missing-data policies remain stage 3 work.

## Local M1 Predictor Composition

The local `integration.build_m1_predictors` adapter composes prepared sources
with the actual owned WBT executable. The [accepted contract](docs/m1_predictors.md)
and ADR-0059 define lossless copies, independent T/F/S support, K units/coverage,
provenance and retained incomplete failures. `evaluate_m1_scenarios` evaluates
explicit accumulations through the scalar engine; no climate defaults are added.

The [work package](../../../../docs/work-packages/20260909_staley_m1_predictors/package.md)
retains complete synthetic and authentic rebuilt Wallow T/F/S evidence, plus
missing-input cases. Stage 3 local composition acceptance is satisfied.
That local package excludes live publication; stages 4–5 now add Climate
composition and production NoDb/UI/RQ without rebuilding upstream sources.

## Unitization Contract

Use the existing `wepppy/nodb/unitizer.py` and WEPPcloud unitizer helpers for
project-selected SI/English presentation in controls, tables, reports, legends,
and tooltips. Any dimensional input exposed by the control must carry its unit
and normalize once at the API boundary. Initial M1 exposes no dimensional
model input; its upload cell size and area warning use Unitizer. Exact payloads
are defined in the [production contract](docs/production_m1.md).

| Quantity | SI presentation | English presentation | Calculation requirement |
| --- | --- | --- | --- |
| Rainfall accumulation/threshold | mm | in | Normalize to mm before evaluation |
| Rainfall intensity/threshold | mm/hour | in/hour | Normalize to mm/hour; convert to accumulation using duration |
| Soil thickness | metric depth through Unitizer | corresponding English depth | Explicit cm-to-inch conversion for M3 S; do not use a display-rounded value |
| Relief/elevation | m | ft | Use consistent length units with catchment area for ruggedness |
| Catchment area | ha or km2 via existing preference | acres via existing preference | Canonical area in m2 for ruggedness/aggregation |
| Probability and burned fraction | probability or labeled percent | same | Dimensionless; distinguish 0-1 from 0-100 |
| Duration, slope angle, dNBR, scaled predictors | min, degrees, or labeled dimensionless values | same | No arbitrary SI/English conversion |

Reuse Unitizer's existing `mm`, `in`, `mm/hour`, and `in/hour` categories.
Resolve the soil-depth display category without inventing an unimplemented
unit key. M1 K remains in its calibrated source convention; any separately
displayed K conversion needs an explicit unit contract, not a preference-driven
change to the regression input.

Changing display units must not rerun the model, change probabilities, or
rewrite canonical scientific values. Persist input/source units and scaling
provenance; machine-readable exports must identify their units independently
of browser preferences. Event/design/inverse export schemas are defined in
[the rainfall contract](docs/rainfall_results.md).

## dNBR Upload and Processing Contract

Accepted direction: reuse SBS upload conventions, accept different source grids
and extents, create a standardized project-aligned raster, require valid overlap
with the watershed, and support partial coverage. The detailed
[dNBR backend contract](docs/dnbr_upload.md) fixes the Python normalization and
summary interface; ADR-0054 records its numerical choices. Browser upload and
NoDb/RQ publication are implemented in [the production workflow](docs/production_m1.md).

The SBS precedent accepts `.tif`, `.tiff`, `.img`, and `.vrt` with a 100 MiB
file cap. Its categorical value checks (integer values and at most 256 classes)
do not apply to continuous dNBR. Backend v1 accepts real integer and floating-
point single-band inputs, self-contained GTiff/HFA and explicitly allowlisted
identity VRT wrappers. It does not execute arbitrary VRTs or read sidecars.
The backend defines raster validation and resource limits; production transport
adds streamed packaging, authorization and candidate publication checks.

Normalize to the authoritative WBT project grid: CRS, resolution, origin,
affine transform, dimensions, and extent must match, not just the EPSG code and
nominal cell size. Output is a single-band Float32 GeoTIFF containing
normalized prefire-minus-postfire NBR difference with NaN NoData. Backend v1
uses compiled GDAL nearest sampling to retain source observations and holes.
Use a separate coverage/support mask when needed to keep resampling from
turning absent source coverage into observations. Preserve the source artifact
and normalization provenance.

Treat value encoding separately from spatial scale. Explicit source scale and
offset (or a resolved encoding preset) determine normalized dNBR. The local
normalizer requires explicit encoding; production Auto resolves it from the
valid-value distribution under the evaluated detection contract below. Preserve valid negative and zero
values. NoData is not unburned and is not dNBR zero.

Production upload uses an Auto-default scale select with standard presets and a
Custom factor/offset option. The adapter must resolve Auto to explicit encoding
before normalization; unresolved scale cannot publish an accepted map. See the
[production UI contract](../../../../docs/ui-docs/contracts/postfire-debris-flow-control-contract.md#dnbr-field-and-copy)
for distribution-based detection, the uploaded-map summary table and correction
flow. Distribution-v1 numerical criteria and initial evidence are recorded in
[ADR-0063](../../../../docs/adrs/ADR-0063-dnbr-auto-scale.md). The local normalizer's
explicit encoding API remains unchanged.

Require positive valid-data overlap with the actual watershed mask; bounding-box
intersection alone is insufficient. Partial coverage is accepted and reported.
For catchments with some valid dNBR, F is the area-weighted target-cell mean
over observed support, with observed area/fraction reported against the full
catchment. This is a partial-coverage estimate of the publication's full-area
predictor. Do not shrink the SBS or soil aggregation domains to the dNBR footprint.
Catchments without valid dNBR have unavailable M1 results, not zero probability
and not an implicit M3 result. A catchment-level gap must not discard other
catchments that can be assessed.

Do not impose a new minimum coverage percentage as an unapproved heuristic.
Warn on partial coverage without treating every partial upload as an error.
Distinguish successful upload, successful normalization, and scientific result
availability. If source overlap disappears on the target grid, normalization
must return a clear unusable-at-project-resolution result rather than claim
readiness or extrapolate values.

## Rainfall Sources and Scenario Outputs

Local stage-4 implementation and evidence are in the
[rainfall/results package](../../../../docs/work-packages/20260909_staley_rainfall_results/package.md).
The [accepted adapter/result contract](docs/rainfall_results.md) composes M1
bundles with existing Climate artifacts. Callers explicitly select source,
durations, intervals and inverse targets. ADR-0062 records approved sample
handling. Production stage 5 consumes these artifacts and adds completion
notifications to Climate export; climate generation semantics are unchanged.

Accepted direction: focus on short return intervals and reuse Climate-owned
event intensities and NOAA PDS artifacts. Do not reconstruct CLIGEN storm
intensities inside this module.

The existing `ClimateArtifactExportService` writes
`climate/wepp_cli.parquet` with `peak_intensity_15`, `peak_intensity_30`, and
`peak_intensity_60` in mm/hour. Its post-build export also produces
`climate/wepp_cli_pds_mean_metric.csv`, using ranked wet-event intensities and
the existing Weibull PDS method. It supports 1, 2, 5, and 10 years (and longer
intervals), limited to intervals no greater than the number of represented
wet-event years. These are project CLI-derived estimates; preserve the actual
climate mode and provenance even when the selector is labeled CLIGEN.

The Climate-owned NOAA artifact is
`atlas14_intensity_pds_mean_metric.csv` under `Climate.cli_dir`. Current download
eligibility checks for `2015` or `legacy` in `cligen_db`; availability is not
guaranteed for every climate build. Both artifact exports can fail without
failing the climate build, so readiness must validate data rather than assume
files exist. The CLI frequency CSV can contain zero placeholders for missing
intensity columns; these must not become design-storm inputs. Validate against
the event parquet and report missing scenarios explicitly.

Implementation review also found that CLI frequency selection clamps a requested
rank to the last positive observation if a duration has too few samples. The
shared rank helper assigns indices across the supplied recurrence set, so exact
Climate parity requires its full request context before selecting a subset.
Approved R02 returns unavailable / `insufficient_positive_samples` when the
requested zero-based rank is at least the positive duration sample count. Retain
rank/count diagnostics and null rainfall/probability, while supported ranks and
other durations continue. The unchanged Climate CSV clamp remains parity
evidence only; see ADR-0062 for the decision and rationale.

Accepted local workflow; browser presentation defaults remain proposals:

- Require explicit CLI / NOAA frequency source selection, using the existing
  project artifacts and Climate-owned frequency method. Never silently switch
  sources. Keep event intensities in parquet as the source of full-precision
  CLI values; the current frequency CSV rounds to two decimal places.
- Evaluate 1-, 2-, 5-, and 10-year intervals for each of 15, 30, and 60 minutes:
  12 scenarios for the project watershed, selected model, and source. Lead the report with
  15-minute results; retain the other durations for comparison. The paper
  supplies duration-specific coefficients, not a prescribed return-period set.
- Convert intensity to accumulation as `R_mm = I_mm_per_hour * minutes / 60`.
  Each scenario reports conditional debris-flow occurrence probability, its
  rainfall intensity and accumulation, duration, return interval, source, and
  predictor coverage. Different durations are separate scenarios; do not
  average their probabilities or interpret them as independent joint events.
- Initial M1 supplies inverse rainfall thresholds at 50% for all three durations.
  A future dashboard may expose additional explicit targets under its contract. These thresholds depend on
  catchment predictors and coefficients, not on a rainfall-frequency source;
  assigning a return interval to a threshold is a separate operation.

Staley outputs occurrence likelihood and rainfall thresholds. It does not
estimate volume, runout, damage, or annual debris-flow probability. Keep PDS
average recurrence interval terminology; do not label a 1-year PDS scenario as
100% annual probability. Record climate record length and frequency method;
merely having ten years permits the existing estimator's 10-year output but
does not establish estimate precision. Missing intervals remain unavailable.
The scalar engine numerical policies are accepted in ADR-0056.
Sample adequacy is recorded with unavailable sparse ranks (ADR-0062).
Initial production M1 uses the fixed matrix and 50% inverse target (ADR-0063).

## Interactive Event Dashboard

Accepted direction: users can browse individual storm-event debris-flow
probabilities and select events for more detail. Interpret events as wet-event
records in the project CLI parquet. The proposed return-interval matrix is a
separate design-storm comparison, not the complete dashboard event catalog.
This preserves actual event combinations of duration-specific intensities
instead of replacing every event with a frequency estimate.

For each event, evaluate the available 15-, 30-, and 60-minute peak intensities
with their matching Staley coefficients for the project watershed and selected
model. Retain event identity, climate year/date, climate mode, and source
provenance. Synthetic climate dates must be identified as simulation dates.
NOAA PDS supplies design-storm estimates, not a dated event catalog; switching
frequency sources must not relabel project CLI events as NOAA observations.

Proposed interaction, pending detailed UI contract:

- A linked event plot and sortable table show probabilities for the project
  watershed, selected model, and duration. Start with 15 minutes and allow
  30/60-minute comparisons. Keep the existing project boundary/outlet visible
  where a map is presented; there is no catchment selector in initial scope.
- Selecting an event updates the watershed result and event detail. A map may
  show the basin result and input coverage; it must not imply independently
  evaluated channel, hillslope, or pixel probabilities.
- Event detail shows storm depth/duration when available, all three peak
  intensities and corresponding probabilities, source/date, model, watershed
  predictors, and data coverage/unavailable reasons. Apply project SI/English
  display preferences. A hyetograph requires a separate explicit reconstruction
  contract; peak-intensity columns alone do not supply one.
- Keep design-storm comparisons and inverse probability thresholds accessible
  alongside the event view. Event frequency estimates, if displayed, are
  duration-specific and must use the documented frequency method.

Evaluate these events against the selected current postfire predictor state.
A multidecade synthetic climate catalog is a set of rainfall scenarios under
that state, not a simulation of decades of postfire recovery or a cumulative
debris-flow forecast. Do not combine duration probabilities into a joint score.
Event identifiers, persistence/query strategy, filtering defaults, dashboard
host, and large-catalog performance requirements remain open.

## Production M1 Workflow Increment

Owner scope (2026-09-10 UTC): NoDb state, prerequisite/freshness checks, dNBR
upload and publication, RQ execution and a minimal control for uploading and
running M1. Reports and interactive dashboard are deferred. The owner plans a
10 m project for testing; this does not change M1 resolution eligibility.

[Production workflow contract](docs/production_m1.md) and
[UI contract](../../../../docs/ui-docs/contracts/postfire-debris-flow-control-contract.md)
specify intended state/publication behavior, a compact required-data list,
dNBR upload and one run action. Use familiar land-manager/hydrologist terminology;
keep implementation details in the job log and avoid additional parameter panels.
Owner revisions: required-data readiness updates through preflight in realtime;
label the raster “differenced Normalized Burn Ratio (dNBR)”; omit image-date
entry; offer Auto scale selection; persist the uploaded filename and show accepted
raster formats/datatypes; disable NOAA when unavailable. These remove unnecessary
map-preparation friction and avoid calling dNBR a soil burn severity map.
The accepted UI/default/state contract precedes runtime edits in ancestors
`5c0a172ee` and `595816476`. The
[production M1 package](../../../../docs/work-packages/20260910_staley_m1_production/package.md)
implements the accepted workflow. Initial completion means status and protected
model-file access, not report tables/charts or dashboard implementation.

## Planned File Organization

The scalar `staley2017.py` engine is implemented under its accepted contract.
The M1 facade, production adapter, routes, workers and control are implemented;
reports remain reserved for the deferred increment.

| Location | Responsibility |
| --- | --- |
| `postfire_debris_flow.py`, `__init__.py` in this directory | NoDb facade and exports |
| `staley2017.py` | Independent numerical M1/M3 evaluator |
| `integration.py` | Artifact validation, catchment aggregation, orchestration |
| `production.py`, `encoding.py` | Owner freshness, safe publication, Auto-scale resolution |
| `results.py`, `rainfall_io.py` | Result manifests, event/design/inverse artifacts and provenance |
| `wepppy/rq/postfire_debris_flow_rq.py` | Upload and model workers |
| `wepppy/weppcloud/controllers_js/postfire_debris_flow.js` | Pure UI controller |
| `wepppy/weppcloud/templates/controls/postfire_debris_flow_pure.htm` | Control and prerequisite presentation |
| `wepppy/weppcloud/templates/controls/postfire_debris_flow_reports.htm` | Deferred report increment; excluded from initial production upload/run package |
| `wepppy/microservices/rq_engine/postfire_debris_flow_routes.py` | RQ-engine submission boundary |
| `tests/nodb/mods/test_postfire_debris_flow_*.py` | Numerical and integration tests |
| `tests/microservices/test_rq_engine_postfire_debris_flow.py` | Route contracts |
| `wepppy/weppcloud/controllers_js/__tests__/postfire_debris_flow.test.js` | UI state and payload tests |

## Open Decisions Before Implementation

1. Ratify SSURGO thickness aggregation, bedrock/interval rules, missing-data
   coverage policy, and comparison against STATSGO THICK. Original units are
   resolved as inches. SSURGO primary and STATSGO fallback are approved;
   fallback granularity, triggers, and provenance require an implementation contract.
2. Production application of the accepted maximum-minus-outlet terrain
   contract and recommended 10 m requirement; original calibration
   preprocessing equivalence remains unproven.
3. M3 prerequisites, production soil/terrain freshness and publication through
   the shared workflow. M1 K-only readiness and freshness are implemented.
4. Interactive event dashboard, report placement, filters and presentation of
   unavailable scenarios. Existing event IDs, SI export schemas, the M1 source
   selector and fixed scenario matrix are implemented; no new scientific defaults
   are implied by future dashboard work.
5. Any future post-fire age policy, dimensional input fields and M3/report
   Unitizer mappings. M1 has no image-date input or age gate. Canonical continental-US
   eligibility, WBT enforcement, upload scaling/alignment, minimal control units
   and study-area warnings are implemented.

## Compatibility and Validation Plan

Offline soil artifacts follow the dedicated contract above. Production M1
is additive; future M3 integration must also
preserve existing `debris_flow.nodb` state and older outputs, and avoid renaming
user-visible fields without explicit approval. Before data mutations, specify
new NoDb/CSV/parquet schemas and downstream generated-artifact propagation.

Create an active implementation ExecPlan and complete the repository's
[contract-first checkpoint](../../../../docs/standards/contract-first-change-standard.md)
before editing runtime files. Include shared NoDb, RQ response, CSRF, controller,
and feature-registry contracts. Record accepted parameterization in an
[ADR](../../../../docs/standards/parameterization-adr-standard.md).

Validation should cover independently derived numerical examples, forward/inverse
consistency, spatial intersection and catchment aggregation, units, missing and
stale dependencies, valid/empty/legacy/hostile states, and real generated outputs.
Verify absent/empty/populated/custom/legacy Soils states, server enforcement of
CONUS/WBT eligibility, and SI/English input equivalence and report switching.
Thickness checks must include cumulative-depth overcounting, duplicate horizons,
bedrock intervals, and the 2.54 conversion; display rounding must not affect S.
dNBR checks must cover alternative encodings/grids, partial watershed coverage,
NoData-only overlap, valid zero/negative values, empty subcatchments, and safe
upload replacement. Detailed cases live in the dNBR upload design.
Compare independently authored fixtures against separately executed pfdf where
useful; do not copy its tests. Terrain work needs parity and performance evidence
against the owned stack. UI/RQ/NoDb boundaries require real workflow evidence
under production-equivalent identities and mounts before shipping.

## References

- Staley, D.M., Negri, J.A., Kean, J.W., Laber, J.L., Tillery, A.C., and
  Youberg, A.M. (2017). Prediction of spatially explicit rainfall
  intensity-duration thresholds for post-fire debris-flow generation in the
  western United States. Geomorphology 278, 149-162.
  [DOI](https://doi.org/10.1016/j.geomorph.2016.10.019).
- [Reference bundle and retrieval evidence](docs/README.md).
- [pfdf model guide](https://ghsc.code-pages.usgs.gov/lhp/pfdf/guide/models/s17.html):
  implementation comparison only, not a replacement for the published method.

## Local rainfall/results execution status

The [local rainfall contract](docs/rainfall_results.md) now defines additive
event/design/inverse tables and bounded local queries. Genuine Wallow snapshots
exercise both explicit frequency sources with fixed predictors. The separate
production M1 contract now supplies publication; a dashboard remains deferred. The owner explicitly approved
R02: unsupported positive ranks retain unavailable rows. Parameterization and
rationale are recorded in ADR-0062; the package tracker records final validation.

## Artifact observability

[Artifact observability](../../../../docs/standards/artifact-observability-standard.md)
is mandatory. Sources, intermediate maps, diagnostic files and failed/completed
attempts use visible attempts/<id>/ directories and durable status receipts.
Latest result files remain directly under postfire_debris_flow/. Preserve them
through canonical project archive/restore. Storage migration and failure retention
are governed by [production M1](docs/production_m1.md#observable-intermediate-artifacts-and-migration).
