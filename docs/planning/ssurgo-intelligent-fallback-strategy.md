# SSURGO Intelligent Fallback Strategy

**Status:** Proposed research and implementation strategy; no selection behavior changes are authorized by this document.

## Purpose

When the gridded SSURGO builder cannot create a valid WEPP soil for a raster
MUKEY, it currently assigns that hillslope the most common valid MUKEY in the
run. This keeps a run executable, but can replace a locally distinctive or
partly described soil with an unrelated watershed-wide soil.

This strategy first measures the residual-invalid population and its causes.
It then evaluates deterministic candidate-selection policies that use (in
order of scientific relevance) information retained for the invalid MUKEY,
nearby valid MUKEY pixels in the gridded SSURGO map, and comparable terrain.
Hillslopes consume the resulting soil-map evidence but do not define the
neighborhood. The desired result is a model-ready soil assignment that is more
locally defensible while retaining a safe, observable continuity path when
evidence is weak.

The proposed work is confined initially to the gridded
`Soils._build_gridded()` path in `wepppy/nodb/core/soils.py`. It does not
change SSURGO retrieval, the current valid-profile conversion rules, WEPP
erosion equations, or the meaning of existing final mappings.

## Current State and Constraints

`_build_gridded()` builds every MUKEY present in the SSURGO/gNATSGO raster,
derives one raw dominant MUKEY per hillslope, and selects the first valid MUKEY
in the descending watershed-wide frequency order. Every hillslope whose raw
dominant MUKEY has no generated soil receives that same `dom_mukey`.

The existing provenance contract must remain intact:

- `domsoil_d` and `ssurgo_domsoil_d` are the final, model-ready assignments.
- `raw_ssurgo_domsoil_d` retains the raster-selected dominant MUKEY.
- `ssurgo_substitution_d` records the raw MUKEY, replacement MUKEY, and
  current `invalid_dominant_mukey` reason.
- A run with no valid SSURGO soil continues to use the separate STATSGO
  fallback path; an intelligent soil-map selector must not conceal this
  condition.

An invalid soil is not simply a raw record with a blank field. `Horizon` can
apply existing defaults and estimate some properties. For this study, a MUKEY
is **residual-invalid** only when it still has no valid `WeppSoil` after the
existing conversion/default/estimation process, or when its worker fails before
producing a soil object. This avoids treating a successful, documented repair
as a fallback failure.

The validity boundary currently requires a non-organic horizon with usable
depth, sand, clay, organic matter, CEC, very-fine sand, conductivity, and bulk
density, plus a major component and at least one emitted WEPP layer. The study
must report both the raw missingness and the post-conversion reason that the
MUKEY remains unusable.

## Questions to Answer Before Selecting a New Policy

1. What fraction of requested MUKEYs, raw dominant hillslopes, affected area,
   and completed builds are residual-invalid? Report each denominator; a rare
   MUKEY can still cover a material hillslope area.
2. Which failure classes dominate nationally, by region, source raster/version,
   landform, and build configuration? Are causes missing fields, invalid
   physical values, no eligible component, no eligible horizon, restrictive
   profile handling, or worker/data-access failures?
3. For a residual-invalid MUKEY, which retained attributes are trustworthy
   enough to compare to valid candidate soils? How often are those attributes
   actually present?
4. Do valid MUKEYs that share a soil-raster boundary with an invalid MUKEY, or
   occur nearest to its mapped footprint, have materially more similar profiles
   than watershed-wide candidates? Does that hold after accounting for
   elevation and other verified terrain covariates?
5. Under a masked-valid-soil experiment, which policy most often recovers a
   soil comparable to the withheld soil without reducing build continuity or
   producing unstable ties?

No score weights, distance thresholds, data imputation rules, or confidence
cutoffs are decided here. Those alter model input parameterization and require
an ADR under `docs/standards/parameterization-adr-standard.md` before an
implementation changes production assignments.

## Phase 1: Empirical Study

### Population and Sampling

Analyze a versioned cohort of completed gridded SSURGO builds drawn from at
least three independent sources:

- retained local or production run directories for which the source raster,
  watershed data, project SSURGO SQLite cache, and soil build logs are
  available;
- deterministic repository fixtures, including the Fairpoint reclaimed-soil
  case that previously exposed a zero-layer conversion failure; and
- a prospective, opt-in diagnostic sample collected after structured records
  are available.

Stratify the historical cohort by SSURGO/gNATSGO source version, geographic
region, watershed-size bin, and terrain class. Publish both the number of runs
and the number of MUKEY/hillslope/area observations in every aggregate. Do not
claim a national rate from an opportunistic collection of incident runs.

Historical run data may contain run identifiers and locations. Keep raw
analysis extracts out of git and publish only anonymized or approved aggregate
tables. Store reproducible queries, schema versions, and non-sensitive
aggregates under a work package or investigation artifact directory rather than
embedding counts in this plan.

### Structured Diagnostic Record

Add a research-only, additive record at the point where
`SurgoSoilCollection.makeWeppSoils()` has complete success/failure information
and where `_build_gridded()` has raw dominant assignments. Do not derive the
study primarily by parsing `.log` prose. One record is required per attempted
MUKEY and a linked record per affected hillslope.

The MUKEY-level record should include:

| Group | Required fields |
| --- | --- |
| Identity | schema version, run cohort ID, raster/source version, MUKEY, build configuration, cache/schema version |
| Outcome | `valid`, `residual_invalid`, or `worker_failed`; build stage; exception type/message fingerprint when applicable; log path only when permitted |
| Failure evidence | component count; eligible-component count; horizon count; post-default valid-horizon count; emitted WEPP-layer count; restrictive-layer state; explicit reason codes |
| Raw-data completeness | for every converter-required horizon field, count missing, nonnumeric, nonfinite, nonphysical, and defaulted values; preserve the field names but not a vague single “missing data” flag |
| Retained comparison features | major-component percentage, component/map-unit text or normalized class where allowed, depth profile, sand/clay/OM/CEC/very-fine-sand/rock/ksat/bulk-density summaries, and a per-feature availability flag |
| Repair provenance | existing defaults and estimates applied, including Rosetta field-capacity/wilting-point sanitation; distinguish these from a failed build |

The hillslope-level record should link the raw MUKEY, its soil-map region ID,
the final MUKEY, affected area, raw-MUKEY raster coverage within the hillslope,
raster/source version, and final substitution provenance. It must also reserve
nullable fields for the map-derived candidate set, chosen policy/version, score
components, confidence tier, and fallback reason. Existing `soils.parquet`
columns and NoDb fields remain backward compatible; new fields are additive and
nullable.

Use reason codes that can be aggregated without parsing text. Start with
`worker_failed`, `no_components`, `no_eligible_component`, `no_horizons`,
`no_valid_horizons`, `zero_wepp_layers`, and `invalid_required_attributes`.
For the last code, retain the field-level subcodes (for example
`missing_sandtotal_r`, `nonfinite_ksat_r`, `nonphysical_fc_wp`) rather than
inventing one ambiguous primary cause. A reason can have more than one code.

### Study Scaffold

`tools/ssurgo_empirical_study.py` now provides the offline, non-production
analysis boundary for this phase. It intentionally does not retrieve SSURGO
tabular data, invoke the soil converter, or mutate any run. Its three commands
are:

```bash
# Full streaming inventory; run as a batch because the supplied raster is large.
python tools/ssurgo_empirical_study.py inventory \
  --raster /wc1/geodata/ssurgo/gNATSGSO/2025/gNATSGO_mukey_202502.tif \
  --output artifacts/gnatsgo_2025_mukey_inventory.json

# A smoke test only: output is deliberately marked incomplete.
python tools/ssurgo_empirical_study.py inventory \
  --raster /wc1/geodata/ssurgo/gNATSGSO/2025/gNATSGO_mukey_202502.tif \
  --max-windows 100 --output /tmp/gnatsgo_2025_smoke_inventory.json

# Aggregate version-1 build records and join them to a complete inventory.
python tools/ssurgo_empirical_study.py template \
  --output artifacts/mukey_build_diagnostic_template.json
python tools/ssurgo_empirical_study.py diagnostics \
  --input artifacts/mukey_build_diagnostics.jsonl \
  --output artifacts/mukey_build_diagnostic_summary.json
python tools/ssurgo_empirical_study.py coverage \
  --inventory artifacts/gnatsgo_2025_mukey_inventory.json \
  --diagnostics artifacts/mukey_build_diagnostics.jsonl \
  --output artifacts/gnatsgo_2025_coverage_summary.json
```

The `inventory` command reads the GeoTIFF in native blocks and emits pixel
counts per MUKEY, CRS, raster dimensions, block shape, and pixel area. A
limited inventory is never accepted by `coverage`, preventing accidental
publication of a first-block sample as a national frequency. The `diagnostics`
and `coverage` commands validate the required JSONL fields and preserve
unobserved raster coverage separately from invalid coverage. `template` emits
the version-1 required record shape, including all converter failure-evidence
fields; it is the handoff contract for the future build-boundary collector.

The next implementation step is a deliberately separate collector at the
SSURGO build boundary. It must emit the version-1 `mukey_build` records above,
including the full field-level diagnostics, before the empirical rate can be
reported. Keeping that collector separate ensures the initial national raster
inventory is reproducible and makes no production fallback or data-contract
change.

### Analysis Outputs

The empirical report must produce:

- a funnel from raster MUKEYs to attempted builds, valid WEPP soils,
  residual-invalid MUKEYs, affected dominant hillslopes, and affected area;
- failure-code frequency and co-occurrence tables, separately before and after
  existing defaults/estimators;
- distributions of available comparison features for residual-invalid MUKEYs;
- maps or anonymized spatial summaries of invalidity and of current global
  substitutions;
- comparison of raw-MUKEY coverage, connected soil-map-region area, distance
  to valid MUKEY pixels, shared-boundary length, elevation/terrain differences,
  and the present watershed-wide assignment; and
- a data-quality report that lists missing diagnostic fields, sampling bias,
  and every excluded run with its reason.

Report uncertainty using bootstrap intervals clustered by watershed, not only
by individual hillslope. Preserve the raw numerator and denominator beside
percentages.

## Phase 2: Candidate Evidence and Policies

### Candidate Set

Phase 2 candidate discovery uses a bounded cluster query, not a national
MUKEY-adjacency graph. The caller groups spatially adjacent invalid MUKEYs and
supplies the cluster's soil-map bounds in the raster CRS. The native kernel
expands one crop per cluster until it finds valid already-built MUKEYs, then
returns the same deterministic candidate set to every source MUKEY in that
cluster. MUKEY values alone are insufficient because one MUKEY can occur in
disconnected national locations.

The research interface is batch-oriented:

    local_mukey_candidates(raster_path, clusters, valid_mukeys,
                           initial_radius_m, max_radius_m,
                           min_candidates, workers)

Each cluster has an immutable identifier, an ordered/deduplicated list of
source MUKEYs, and `(min_x, min_y, max_x, max_y)` bounds in the source raster
CRS. Each result records the cluster identifier, source MUKEYs, successful
radius or exhaustion, sorted candidate MUKEYs, and crop-read provenance.
Concurrent work must use worker-local GDAL dataset handles; it must not share
one GDAL handle across threads. Benchmark clustered synthetic requests and
representative gNATSGO windows before choosing a worker default or adding a
precomputed tile-set index.

Build the candidate set only from valid WEPP soils already generated in the
same run and source context. Do not synthesize a new hybrid profile by copying
individual parameters from an invalid soil during the first implementation.
That would introduce a separate imputation and physical-validity problem.

The primary spatial unit is a connected region of one invalid MUKEY in the
SSURGO raster, not a hillslope. This matters because one MUKEY can occur in
separate places with different nearby soils, while a hillslope can cut across
several soil-map regions. A hill whose dominant raw MUKEY is invalid consumes
the recommendation for the invalid region that supplies its dominant pixels;
when more than one region contributes, aggregate only by documented raster
coverage, never by watershed topology.

Construct a MUKEY-region adjacency graph directly from the soil raster (or
equivalent soil-map polygons). Shared raster edge or polygon boundary length is
the primary relation; a corner-only contact is recorded separately and is not
treated as equivalent. Candidates are evaluated in expanding, explicit rings:

1. valid MUKEYs sharing a boundary with the invalid MUKEY region;
2. valid MUKEYs within a bounded raster/geographic distance of that region; and
3. valid MUKEYs elsewhere in the source raster clipped to the run extent only
   when the local rings are empty or fail a future ADR-approved confidence
   gate.

Candidate discovery must be deterministic: normalize MUKEY types to strings,
deduplicate candidates, retain region geometry/edge metrics, and use a
documented stable final tie-breaker. It must not make a network call or depend
on unordered process completion.

### Evidence Features

Score candidates only with features present for the particular invalid MUKEY;
missing values must remove or reweight that comparison dimension, never become
a zero that implies similarity. Feature families to evaluate are:

- **Residual soil evidence:** compatible component/map-unit class where
  available; usable horizon count; profile depth; and robust surface and
  depth-weighted texture, organic matter, CEC, rock-fragment, bulk-density,
  and conductivity summaries. Each feature carries source/default/estimated
  provenance.
- **Spatial evidence:** shared-boundary length or raster-edge count first,
  then region-to-region raster/geographic distance. A large shared boundary
  must not be silently equivalent to a one-cell contact.
- **Terrain evidence:** summarize an elevation raster over the invalid region,
  its candidate contact zone, and candidate regions: median/quantiles and
  overlap or distance of their distributions. Add slope, aspect, and relief
  only when they are available on the same grid and their resampling rules are
  recorded. Elevation is a promising primary terrain feature because it is
  independent of watershed delineation; do not fabricate it from a slope field.
- **Local support:** candidate boundary/contact support around the invalid
  soil-map region and consistency of its immediate map neighborhood. This is
  evidence, not a license for a watershed-wide majority override.

The study must test each family separately before fitting or choosing a hybrid
policy. Standardize continuous variables within an explicitly declared cohort,
and retain unscaled inputs and transformations in the diagnostic artifact.

### Policies to Compare

Compare the present global-dominant behavior with these deterministic baselines:

| Policy | Selection rule | Purpose |
| --- | --- | --- |
| Current baseline | Most common valid MUKEY in the watershed | Continuity and regression baseline |
| Map-adjacent majority | Valid MUKEY with greatest shared-boundary/contact support | Tests whether soil-map locality alone improves selection |
| Profile-nearest | Candidate nearest on available retained soil features, independent of location | Tests residual SSURGO information |
| Terrain-nearest | Candidate nearest on verified elevation/terrain summaries within a map neighborhood | Tests terrain as a proxy only |
| Hierarchical hybrid | ADR-approved combination of profile, map adjacency, and terrain evidence | Candidate production policy only after validation |

The hybrid must be hierarchical and explainable, not an opaque model: eligibility
filters first, then score components, then a confidence gate, then a stable
tie-breaker. It must write every component that determined the choice. A
learned model is out of scope until the simpler policies demonstrate a clear,
stable benefit across held-out watersheds.

When no candidate is eligible or evidence is below the future confidence gate,
retain the current global-dominant fallback as the final continuity level, with
a distinct reason such as `low_confidence_global_fallback`. If no valid soil
exists, retain the existing STATSGO behavior. Never silently choose a candidate
because it happens to sort first.

## Phase 3: Fixture and Evaluation Design

### Deterministic Fixture Corpus

Create a compact test corpus under `tests/soils/fixtures/` and
`tests/nodb/fixtures/` (or the nearest established fixture location) with
synthetic SSURGO tables, a labeled soil-MUKEY raster/polygon representation,
an independent DEM/elevation raster, and minimal hillslope overlays for output
assignment. No test may call NRCS or require production run data.

The corpus must contain at least these watersheds:

1. **Local profile match:** an invalid raw MUKEY region with enough valid
   texture and depth evidence to prefer one boundary-adjacent valid MUKEY over
   the globally dominant soil.
2. **Elevation disambiguation:** equally plausible boundary-adjacent valid
   MUKEYs whose independent elevation distributions distinguish the intended
   candidate.
3. **Sparse invalid record:** no trustworthy retained profile attributes, where
   locality alone is tested and the chosen reason makes that limitation clear.
4. **No local support:** no valid map-adjacent or bounded-neighborhood
   candidate, proving the controlled global fallback remains available.
5. **Ambiguous tie:** equal score components, exercising the specified stable
   tie-break and reproducible diagnostic output.
6. **Non-substitution controls:** valid, urban, water, and current Fairpoint
   reclaimed profiles, proving they do not enter the invalid-selector path.
7. **Total failure:** no valid SSURGO MUKEY, proving the existing STATSGO path
   is unchanged.

Each invalid fixture must explicitly state its failure code and which raw
fields remain usable as comparison evidence. Include cases with omitted raw
fields that existing defaults already repair, so the study does not mistake
successful defaulting for residual invalidity.

### Evaluation Without Ground Truth for Truly Invalid Soils

True invalid MUKEYs do not have a known WEPP profile to recover. Therefore,
use two complementary evaluations:

1. **Masked-valid-soil trials:** hide otherwise valid raw dominant MUKEYs from
   the candidate set while preserving only the fields that would be available
   under each simulated failure class. The withheld generated soil supplies a
   reference for comparing chosen candidates. Split and report results by
   watershed so neighboring hillslopes do not leak into both train and test
   judgments.
2. **Observed-invalid review:** apply all policies to residual-invalid records,
   compare disagreement cases, and conduct domain review of a stratified sample
   with the raw SSURGO evidence, candidate evidence, terrain, and provenance
   visible. This is a plausibility/safety review, not fabricated ground truth.

For masked trials, evaluate exact-MUKEY recovery as a secondary metric only.
The primary measurements are distance from the withheld valid soil on physical
profile summaries and generated WEPP input parameters, local spatial
coherence, output validity, and policy stability under deterministic reruns.
Where a controlled model-run subset is feasible, compare resulting runoff and
soil-loss distributions against the withheld-soil baseline; define acceptable
error bands in the ADR rather than post hoc.

Require a policy to improve on the current baseline across held-out geographic
strata, not merely on one watershed. It must not increase the proportion of
failed builds, produce nonfinite/physically invalid soil inputs, or hide a
substitution from run artifacts. Report the number and area of cases that fall
through to global fallback.

## Proposed Delivery Sequence

1. Create a work package and, before code changes, record the data-contract
   and compatibility plan for the additive diagnostics/provenance fields.
2. Add structured diagnostics behind a non-disruptive collection mechanism;
   validate that normal soil building and legacy NoDb loading are unchanged.
3. Produce and review the empirical report. Decide whether the invalid rate and
   feature availability justify a selector; prioritize converter repairs when a
   small number of correctable failure classes dominate.
4. Add the deterministic fixture corpus and masked-trial harness. Implement the
   current policy as a testable baseline first.
5. Implement candidate discovery and the simple policies without changing the
   production default. Persist policy version, candidate evidence, chosen
   MUKEY, and reason in additive artifacts.
6. Select a policy only after review of held-out results and observed-invalid
   cases. Record the exact score, raster/DEM alignment and resampling rules,
   thresholds, confidence behavior, decision owner, evidence, risks, and
   rollback condition in a parameterization ADR.
7. Make the policy opt-in or shadow-evaluated first, compare it with the
   baseline on a defined observation window, then promote only if acceptance
   criteria hold. Retain a configuration-controlled rollback to the current
   global-dominant behavior.

## Acceptance Criteria for a Future Implementation

- The study publishes frequency, area impact, and reason-code distributions
  with explicit cohorts and denominators.
- Every substitution remains traceable from raw MUKEY and soil-map region to
  final MUKEY, policy version, candidate set, score components, confidence
  tier, and reason.
- Existing final mapping keys and the no-valid-SSURGO STATSGO behavior retain
  their current semantics.
- Fixture tests cover all seven scenarios above and prove deterministic reruns
  choose the same result.
- Masked-valid trials show an ADR-defined, geographically robust improvement
  over the global-dominant baseline without degrading WEPP soil validity or
  build completion.
- A parameterization ADR and affected user/operator/developer documentation
  are completed before any production default changes.
- Targeted NoDb/SSURGO tests, generated-output checks, and relevant `wctl`
  quality gates pass; change notes identify the compatibility behavior for old
  runs and artifacts.

## Risks and Guardrails

- **Missingness is informative but not a soil property.** Never reward a
  candidate simply because both records lack a value.
- **Map adjacency can cross real soil boundaries.** Treat shared soil-map
  boundary as one evidence family and test it against profile and terrain
  evidence rather than assuming adjacent MUKEYs are equivalent.
- **Elevation and terrain are proxies, not SSURGO truth.** Add only verified,
  aligned terrain rasters, record resampling, and keep their influence
  inspectable.
- **A successful default is not an invalid soil.** Keep repair provenance
  separate from residual-invalid selection statistics.
- **Continuity must not erase uncertainty.** Low-confidence cases retain a
  distinct global-fallback reason, and no-valid-SSURGO cases keep the STATSGO
  path.
- **Scientific behavior needs governance.** Any production score, threshold,
  or fallback-order change is a parameterization change and cannot be inferred
  from this planning document alone.

## References

- Current builder and provenance implementation:
  `wepppy/nodb/core/soils.py` (`Soils._build_gridded()`).
- Empirical study scaffold:
  `tools/ssurgo_empirical_study.py` and
  `tests/tools/test_ssurgo_empirical_study.py`.
- SSURGO converter and validity logic:
  `wepppy/soils/ssurgo/ssurgo.py` (`Horizon.valid()`, `WeppSoil.valid()`, and
  `SurgoSoilCollection.makeWeppSoils()`).
- Existing fallback provenance documentation:
  `wepppy/soils/ssurgo/ssurgo.md#gridded-dominant-mukey-fallback-provenance`.
- Initial mapped-area empirical evidence:
  `docs/investigations/2026-07-21-ssurgo-intelligent-fallback-pilot/README.md`.
- Active empirical-study package:
  `docs/work-packages/20260721_ssurgo_intelligent_fallback_study/`.
- Prior reclaimed-profile/fallback evidence:
  `docs/work-packages/20260622_ssurgo_reclaimed_soil_fallback/` and
  `docs/adrs/ADR-0008-ssurgo-reclaimed-soil-restrictive-layer-fallback.md`.
- Parameterization decision requirement:
  `docs/standards/parameterization-adr-standard.md`.
