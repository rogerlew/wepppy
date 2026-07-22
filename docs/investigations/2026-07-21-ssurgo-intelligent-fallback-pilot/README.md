# SSURGO Intelligent Fallback Empirical Study

## Summary

This read-only study establishes an empirical baseline for the proposed
intelligent SSURGO fallback. It uses the supplied 2025 gNATSGO MUKEY raster as
the complete mapped-area population and builds samples through the current
SSURGO-to-WEPP converter.

The approved expansion completed two separate cohorts on 2026-07-22. The
12,288-draw mapped-area cohort found 244 unbuildable draws (1.99%; 95% Wilson
interval 1.75%–2.25%): 211 residual-invalid profiles and 33 converter worker
failures. The 2,048-draw uniform-MUKEY cohort found 49 unbuildable map units
(2.39%; 95% Wilson interval 1.81%–3.15%): 46 residual-invalid and three worker
failures. Neither cohort had an NRCS data-access failure. These rates estimate
different populations and must not be combined.

Across 2,048 independent mapped-pixel draws, 40 draws (1.95%) could not
produce a WEPP soil: 35 were residual-invalid profiles and 5 failed during
conversion because their texture fractions implied negative silt. The 95%
Wilson interval for the combined unbuildable mapped-area rate is 1.44% to
2.65%. This is an **area-weighted pilot estimate**, not an estimate of the
unweighted national MUKEY rate.

The most common observed failures have no usable profile to repair: no returned
component (13 draws) or components with no returned horizons (12 draws).
Where horizon data exist but conversion still fails, missing sand and very-fine
sand are the most frequent observed missing required fields, and inconsistent
texture totals are a distinct conversion failure. These findings support a
two-stage future policy: first repair demonstrably recoverable converter inputs;
then select an existing valid local soil for the remaining residual-invalid
cases using the SSURGO map and, after validation, elevation.

No production run, fallback assignment, or source raster was modified.

## Masked-Valid Candidate Cohort (Milestone 3)

The read-only evaluator ran every eligible hillslope in two completed local
runs: three in `anaphylactic-vernacular` and 295 in `mammalian-ageism`. For
each case it temporarily removed the raw dominant MUKEY from the valid donor
set, recomputed the current global fallback baseline, and queried the smallest
successful local SSURGO window. Every case found local candidates at the
initial 250 m radius. The run SSURGO, subcatchment, and DEM rasters were
identically aligned 30 m EPSG:32610 grids; elevation summaries were calculated
with cropped, vectorized masks rather than iterating cells.

| Comparison | All 298 cases | Large run (295 cases) |
| --- | ---: | ---: |
| Local proposal differs from global baseline | 194 | 194 |
| Local has lower declared WEPP-feature distance | 108 | 108 |
| Global has lower declared WEPP-feature distance | 71 | 71 |
| Feature distance tie | 119 | 116 |
| Local has smaller source-to-donor elevation difference | 235 | 234 |
| Global has smaller source-to-donor elevation difference | 62 | 61 |
| Elevation difference tie | 1 | 0 |

The declared WEPP feature distance is the mean absolute difference over the
jointly available first-profile bulk density, clay, field capacity, organic
matter, rock fragments, sand, soil depth, and wilting point. It is an
unweighted exploratory metric, not a parameterization score. Elevation is
also diagnostic only: local donor elevation is its median within the successful
candidate window, while the global donor uses its median across the run map.

Exact withheld-MUKEY recovery is zero by construction because the experiment
removes the withheld MUKEY from the valid donor set. It is therefore not an
interpretable success metric for this protocol; feature and elevation
comparisons are the usable evidence.

**M4 decision: HOLD.** Local candidates show promising directional evidence,
especially for elevation, but the evidence is limited to two local runs and
does not define a normalized feature distance, a minimum practical effect, or
a production selection rule. Deterministic fixtures for the observed converter
failure classes also remain incomplete. No ADR or fallback-policy change is
justified yet.

## Geometry and Terrain Scoring Experiment (Milestone 3.5)

The scoring experiment adds a concurrent WEPPpyo3 bounded-window query keyed
by source MUKEY/bounds. It reports local candidate support and four-neighbor
shared raster-edge counts separately, so crop abundance is not misrepresented
as adjacency. Geometry-only selection uses normalized shared edge; it would
use support only if no candidate shares an edge. Terrain variants add 0%, 10%,
20%, or 30% of a rank-normalized source-to-candidate elevation difference.

External elevation comes from `/wc1/geodata/ned1/2024/.vrt`, warped bilinearly
from EPSG:4269 to the 30 m run SSURGO grid. NED 1 arc-second was selected over
NED13 because its source resolution is already approximately 30 m; NED13 would
increase remote I/O and resampling without increasing the information used by
the categorical soil map. The source MUKEY's elevation is measured inside its
own local map bounds, not from watershed topology.

| Variant | Local feature-distance better | Global better | Tie |
| --- | ---: | ---: | ---: |
| Geometry only | 131 | 58 | 109 |
| Geometry + 10% terrain | 132 | 60 | 106 |
| Geometry + 20% terrain | 139 | 62 | 97 |
| Geometry + 30% terrain | 140 | 62 | 96 |

All 298 cases had shared-edge candidates. Terrain changed the geometry choice
in 13, 33, and 51 cases at 10%, 20%, and 30% respectively. On the 295-case
substantive run, worker-one execution took 6.08 s and worker-four took 4.94 s;
their parsed result records and score summaries were identical.

This is a GO for the **scoring research experiment**, not for M4. The cohort
still covers only two local runs, does not evaluate retained-profile score
components by failure class, and does not yet use one coalesced crop to serve
multiple source requests. Production fallback behavior remains unchanged.

## Failure-Class Gates and Held-Out Check (Milestone 3.5)

The deterministic scoring corpus now exercises the primary profile-free
classes: `no_components` and `no_horizons` use only source-region geometry and
aligned terrain. It separately demonstrates a partial-profile choice using
only explicitly supplied fields, excludes profile features for a nonphysical
texture failure, and pins missing-DEM, stable tie, no-local-candidate, and
residual-unclassified behavior. The latter two retain an explicit global
fallback rather than selecting the first sorted donor.

The partial-profile fixture uses a transparent research hypothesis of 55%
profile, 30% geometry, and 15% terrain when all three evidence families are
available. Without permitted profile evidence it uses 70% geometry and 30%
terrain; absent terrain reassigns its weight to the available evidence. These
weights are fixture-scoped research values, not a production parameterization
or an ADR proposal.

Four runs not used in the initial 298-case cohort provided a small held-out
check: `juvenile-separatist` (16 cases), `old-fluorosis` (7),
`feline-wrangler` (3), and `forced-bop` (3). All 29 had shared-edge geometry
at the 250 m window. Their result does not reproduce the initial apparent
advantage:

| Variant | Local feature-distance better | Global better | Tie |
| --- | ---: | ---: | ---: |
| Geometry only | 2 | 3 | 24 |
| Geometry + 10% terrain | 1 | 3 | 25 |
| Geometry + 20% terrain | 2 | 3 | 24 |
| Geometry + 30% terrain | 2 | 3 | 24 |

This is valuable negative evidence. M4/ADR consideration remains **HOLD**:
the score has no consistent held-out improvement, the held-out sample is small,
and observed-invalid cases still need a stratified plausibility review with
source-field provenance. The full run artifacts are non-versioned under
`/tmp/ssurgo_masked_valid_20260723/`.

## Ranked Candidate-Set Study (Milestone 3.5)

The evaluator now retains every local candidate's withheld-soil feature
distance, rank order, and raw top-one/top-two score margin. This distinguishes
candidate discovery from ranking without treating a top-k set as a production
substitution. It reports the local-candidate oracle, top 1/2/3 potential,
candidate-count bucket, global-donor membership in the local set, run, and
failure class.

The original 298-case cohort has a substantial ranking gap: the geometry-only
top one was better than global in 131 cases, but the best available local
candidate was better in 183. Top-two and top-three coverage rises to 162 and
177 cases. The local candidate set contained the watershed-global donor in
228 cases, which explains many ties but does not remove the ranking signal.

The 29-case held-out cohort has both discovery and ranking limits. Its top one
was better in 2 cases, the local oracle in 6, and top three recovered all 6.
`old-fluorosis` and `juvenile-separatist` supply the ranking misses. In contrast,
all three `feline-wrangler` cases had a global donor better than every local
candidate, so a better local ranker cannot solve that regime. These results
support testing a shortlist and an abstention/confidence policy, but do not
support a fixed threshold yet.

The executed artifacts are
`/tmp/ssurgo_masked_valid_20260724/initial_candidate_study.json` and
`/tmp/ssurgo_masked_valid_20260724/heldout_candidate_study.json`.

## Larger Ranked-Candidate Cohort (Milestone 3.5)

The next read-only cohort supplied 18 additional completed runs and evaluated
322 masked-valid cases. Two runs had zero eligible hillslopes and remain in the
cohort manifest as explicit zero-case records rather than being silently
dropped. A one-worker repeat reproduced the four-worker result records and
every aggregate exactly.

For geometry-only ranking, top one beat global in 165 cases, top two in 242,
top three in 261, and the best available local candidate in 275. Conversely,
global beat every local candidate in 11 cases. This confirms both diagnostic
paths at meaningful scale: 110 cases have local-oracle headroom beyond the
top-ranked donor, while 11 need a broader candidate set or an abstention to the
global fallback.

Candidate count makes the distinction visible. In 24 one-candidate cases, the
local oracle could not improve on ranking by definition. In 73 two-to-three
candidate cases, local top one won 39 times but the oracle won 66; in 225
four-or-more candidate cases, the same counts were 117 and 200. A future
shortlist/abstention experiment should therefore report these buckets
separately, not use one pooled score threshold.

The artifacts are
`/tmp/ssurgo_masked_valid_20260725/larger_candidate_study.json` and its
byte-equivalent one-worker diagnostic counterpart
`larger_candidate_study_workers1.json`.

## Conditional Broader-Ring Experiment (Milestone 3.5)

Texture is deliberately not an evidence family in this experiment. No
texture-based score or fallback change was introduced. Instead, this slice
isolates candidate discovery: it re-ran the eleven larger-cohort cases for
which no 250 m local candidate matched or beat the current global fallback.
The cases, global baseline, withheld soil, valid donor set, DEM, and feature
distance were fixed. Each run forced one bounded local window at 500 m, 1 km,
or 2 km, making the candidate sets nested rather than changing the search
policy per case.

| Forced local radius | Median candidates | Local oracle better | Global better | Tie |
| --- | ---: | ---: | ---: | ---: |
| 250 m baseline | 4 | 0 | 11 | 0 |
| 500 m | 8 | 5 | 4 | 2 |
| 1 km | 13 | 8 | 1 | 2 |
| 2 km | 23 | 11 | 0 | 0 |

The broader set closes the candidate-discovery gap for this deliberately
selected stratum: every fixed 250 m oracle miss contains a feature-closer
local candidate by 2 km. It does not establish a donor rule. The existing
geometry rank selects a locally better top-one candidate in only three of the
eleven 2 km cases (top three: four), and its median top-two score margin falls
to 0.033. Outer-window candidates need ranking evidence beyond shared source
edges before a conditional expansion can be considered for M4.

The three four-worker artifacts are
`/tmp/ssurgo_masked_valid_20260726/oracle_miss_500m.json`,
`oracle_miss_1000m.json`, and `oracle_miss_2000m.json`. The 2 km one-worker
repeat (`oracle_miss_2000m_workers1.json`) is byte-identical to the four-worker
result. The evaluator's repeatable `--case-id <run-name>:<topaz-id>` filter
pins that fixed cohort for subsequent ranking experiments.

## First-Appearance Ring Ranking (Milestone 3.5)

The next read-only experiment kept the 2 km candidate horizon and derived
each candidate's first appearance from forced 250 m, 500 m, 1 km, and 2 km
windows. Its support evidence is a window-set difference: support in the
candidate's first ring, rather than a pixel-distance calculation. The three
predeclared rankers order candidates by (1) first ring, (2) first-ring support,
and (3) elevation only when the first two keys tie. This respects proximity as
the primary signal and does not use hillslope topology or texture.

It is not a viable ranker. On the fixed eleven-case 250 m oracle-miss cohort,
all three variants selected zero feature-closer top-one donors, despite the
2 km candidate set containing one in every case. On the fixed 322-case larger
cohort, the wider set raised the local oracle from 275 to 305 cases, but the
ring rankers did not turn that discovery headroom into a better top-one rule:

| Ranker | Top-one local better | Global better | Tie | Top-three local better |
| --- | ---: | ---: | ---: | ---: |
| 2 km geometry + 30% terrain | 185 | 62 | 75 | 276 |
| First ring only | 168 | 83 | 71 | 256 |
| First ring + support | 156 | 80 | 86 | 263 |
| First ring + support + elevation | 156 | 80 | 86 | 263 |

The elevation tertiary key made no selection change in this cohort. This is
negative evidence against a strict earliest-window policy, not a reason to
tune its weights after looking at these outcomes. The candidate-ring artifact
is `/tmp/ssurgo_masked_valid_20260726/ring_ranker_larger_cohort.json`; its
one-worker counterpart is byte-identical. It completed in 19.49 s with four
workers versus 21.17 s with one. The modest speedup reflects the evaluator's
current per-withheld-MUKEY batching, which limits concurrent work; it is a
tooling limitation to address before any broader cohort execution.

**M4 decision: HOLD.** A wider candidate set is now supported as discovery
evidence, but strict ring proximity is rejected as its ranker. The next
predeclared experiment should test a small hybrid family that treats ring as a
soft feature alongside source-contact geometry and elevation, with a separate
confidence/abstention proxy and geographically held-out evaluation.

## Validated Shallow-Mineral Vector Experiment (Milestone 3.5)

The next ranker uses the shallowest validated non-organic WEPP layer from the
withheld source and each candidate. Organic matter must be finite and at most
20%; layer thickness, bulk density, hydraulic conductivity, field capacity,
wilting point, cation exchange capacity, and rock fragments must be within
conservative physical bounds. Field capacity below wilting point invalidates
both values. The baseline excludes sand and clay; the requested additive
variant admits them only when both are finite, bounded 0%–100%, and total at
most 100%. A candidate needs at least three jointly validated source/candidate
parameters. The vector distance is robustly scaled per parameter; shared
source contact and elevation resolve only exact vector-distance ties.

This is permitted only for `partial_profile` and
`missing_required_attributes` source evidence. Masked-valid trials use an
explicit simulation label solely to measure the ranker; `no_components`,
`no_horizons`, and nonphysical texture failures receive no profile score and
must retain nonprofile/global fallback behavior.

| Cohort | Top-one local better | Global better | Tie | Top-three local better |
| --- | ---: | ---: | ---: | ---: |
| Fixed 250 m oracle-miss cases (11) | 10 | 1 | 0 | 10 |
| Larger 2 km cohort (322) | 287 | 16 | 19 | 294 |
| Larger 2 km cohort, validated sand/clay | 292 | 12 | 18 | 294 |
| Larger 2 km geometry + 30% terrain | 185 | 62 | 75 | 276 |

The 322-case one-worker artifact is byte-identical to its four-worker result.
Artifacts are `/tmp/ssurgo_masked_valid_20260726/shallow_mineral_oracle_miss.json`
and `shallow_mineral_larger_cohort.json` (with
`shallow_mineral_larger_cohort_workers1.json` as the repeat).

The texture-inclusive variant did not change the fixed 11-case result (10
local wins, one global) but improved the larger cohort by five local top-one
wins. Its four-worker artifact is
`/tmp/ssurgo_masked_valid_20260726/shallow_mineral_texture_larger_cohort.json`;
the one-worker repeat is byte-identical. This is additive evidence only: a
future policy may use sand/clay only after the same source-provenance and
physical-balance checks, never for the known nonphysical-texture failure class.

This is strong **masked-valid** evidence for failure-class-gated profile
matching, not an M4 decision. The study must next prove source-field
provenance and parameter validation on real partial-profile invalid soils, and
must repeat against geographically held-out runs before proposing a production
abstention rule or parameterization ADR.

## Real Residual-Invalid Source Audit and Geographic Holdout (Milestone 3.5)

The expanded mapped-area diagnostic records supplied 13 residual-invalid
MUKEYs with at least one retained horizon and at least one converter-eligible
horizon. A fresh SSURGO source read inspected the shallowest directly observed
non-organic layer without applying defaults. Twelve of the 13 have all six
nontexture comparison values directly observed: bulk density, hydraulic
conductivity, CEC, lower depth, and the two rock-fragment fields. One MUKEY
has no qualifying shallow vector. This validates that the proposed source
provenance gate can distinguish profile-bearing residual invalids from
profile-free cases.

The current empirical classifier labels these cases
`residual_invalid_unclassified`; it does not yet prove that their failed
converter paths are the narrower production class `partial_profile`. They are
therefore source-eligibility evidence, not outcome evidence for a real-invalid
donor selection. A future classifier must persist the direct source values,
their observation/default status, and the converter failure path before such a
selection can leave shadow mode.

The provenance-preserving classifier now creates the narrower research class
`profile_bearing_residual`, without rewriting the converter outcome. Its
real-invalid source shadow cohort contains 12 `profile_bearing_residual`
MUKEYs and one `profile_free_or_unusable_residual`; every included record
retains source horizon index, `chkey`, horizon name, organic matter, direct
values, rejected fields, and `converter_failure_class: unclassified`. It
makes no donor assignment.

The four geographically separated held-out runs (29 masked-valid cases) do
not reproduce the larger-cohort separation. Both shallow-mineral variants had
six local wins, six global wins, and 17 ties; the local oracle had nine wins
and 20 ties. Texture made no held-out selection change. This is neutral rather
than contradictory evidence, but it means no practical-effect or abstention
threshold is ready.

The held-out artifact is
`/tmp/ssurgo_masked_valid_20260726/shallow_mineral_geographic_holdout.json`.
**M4 decision: HOLD.** The next required work is local-candidate evidence for
the real-invalid shadow cohort, followed by a larger geographic holdout; do
not promote the masked-valid vector results to fallback behavior.

## Expanded Cohort Results

| Cohort | Draws | Unique MUKEYs | Residual-invalid | Worker failed | Unbuildable | 95% Wilson interval |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Mapped-area (IID pixels) | 12,288 | 10,676 | 211 (1.72%) | 33 (0.27%) | 244 (1.99%) | 1.75%–2.25% |
| Uniform MUKEY | 2,048 | 2,048 | 46 (2.25%) | 3 (0.15%) | 49 (2.39%) | 1.81%–3.15% |

The mapped-area cohort is the estimate relevant to gridded coverage. The
uniform-MUKEY cohort intentionally gives rare map units equal weight and
therefore answers a different prevalence question. The overlapping intervals
do not establish a material sampling-frame difference; they do establish that
the pilot's approximately 2% area-weighted rate was stable in the expanded
cohort.

The principal nonexclusive reason counts in the expanded mapped-area cohort
were `no_horizons` (176 draws), `no_components` (83),
`nonphysical_texture_balance` (33), `no_valid_horizons` (21), missing
very-fine sand (18), and missing sand (17). The uniform-MUKEY cohort was also
dominated by `no_horizons` (36) and `no_components` (8), with three
nonphysical-texture worker failures. Thirteen mapped-area draws and eight
uniform-MUKEY draws remained residual-invalid without a more specific
source-row classifier; fixture work should resolve that class before policy
design.

## Population and Method

| Item | Value |
| --- | ---: |
| Raster | `/wc1/geodata/ssurgo/gNATSGSO/2025/gNATSGO_mukey_202502.tif` |
| Raster attribute table | `gNATSGO_mukey_202502.tif.vat.dbf` |
| Grid | 30 m, EPSG:5070, 900 m² per pixel |
| Complete mapped pixels | 8,745,483,151 |
| Distinct MUKEYs | 320,669 |
| Sampling design | 2,048 IID uniform mapped-pixel draws with replacement |
| Seed | `20260721` |
| Unique sampled MUKEYs | 1,991 |
| Tabular source | NRCS Soil Data Access through `SurgoSoilCollection` |
| Converter | current `WeppSoil` logic, `initial_sat=0.75`, `ksflag=True` |

The complete raster inventory used the GeoTIFF's companion raster attribute
table (`mukey`, `Count`) rather than a full pixel scan. This is the correct
frequency source for this file and avoids treating an edge NoData block as a
national sample.

The sampled MUKEYs were fetched in 16 batches of at most 128 unique MUKEYs,
then built with eight local converter workers per batch. The sample is
area-weighted because each draw selects one pixel uniformly. Repeated draws of
the same MUKEY were retained as repeated statistical weight.

## Build Outcomes

| Outcome | Draws | Area-weighted rate |
| --- | ---: | ---: |
| Valid WEPP soil | 2,008 | 98.05% |
| Residual-invalid soil | 35 | 1.71% |
| Converter worker failure | 5 | 0.24% |
| Combined unbuildable | 40 | 1.95% |

The five worker failures were not network or Soil Data Access failures. Direct
single-process reproduction showed `ValueError` from Rosetta texture inputs:
all five profiles implied negative silt. Four paired defaulted/missing sand
with high reported clay; one had measured sand and clay totaling more than
100%. They are included in the combined unbuildable rate but remain distinct
from residual-invalid soils so future remediation can address them at the
converter boundary.

## Failure Evidence

Reason codes are not mutually exclusive. For example, a profile may have no
eligible component because its available horizons also lack required fields.

| Reason code | Draws | Area-weighted rate |
| --- | ---: | ---: |
| `no_components` | 13 | 0.63% |
| `no_horizons` | 12 | 0.59% |
| `no_eligible_component` | 10 | 0.49% |
| `no_valid_horizons` | 10 | 0.49% |
| `invalid_required_attributes` | 5 | 0.24% |
| `nonphysical_texture_balance` | 5 | 0.24% |
| `worker_failed` | 5 | 0.24% |
| `missing_sandtotal_r` | 5 | 0.24% |
| `missing_sandvf_r` | 5 | 0.24% |
| `missing_cec7_r` | 3 | 0.15% |
| `missing_claytotal_r` | 2 | 0.10% |
| `missing_dbthirdbar_r` | 2 | 0.10% |
| `missing_om_r` | 2 | 0.10% |
| `missing_ksat_r` | 1 | 0.05% |

Across the nonvalid sampled MUKEYs, raw horizon observations also contained
missing CEC (27 draw-weighted horizon values), sand (20), very-fine sand (20),
bulk density (15), clay (4), organic matter (3), and conductivity (2). Clay
was nonphysical in six additional draw-weighted horizon values. These are raw
horizon observations, not counts of unique MUKEYs, and should not be summed
across fields.

## Implications for the Fallback Design

The pilot supports the strategy's map-first direction.

1. **Do not use one fallback mechanism for every failure.** `no_components`
   and `no_horizons` cases have no profile evidence to impute; selecting a
   valid existing MUKEY from the local SSURGO map is more defensible than
   inventing a hybrid soil.
2. **Repair before selecting a donor when the defect is local and physical.**
   Missing texture/CEC/bulk-density fields and texture-balance errors should be
   evaluated as converter-repair candidates. Any changed default, formula, or
   threshold requires a parameterization ADR.
3. **Derive proximity from the soil raster, not hillslope topology.** The
   sample establishes that fallback is not a negligible edge condition; the
   next evidence must identify neighboring valid MUKEY regions and their
   shared-boundary/distance relationship to each invalid region.
4. **Evaluate elevation only as an aligned raster covariate.** It was not part
   of this pilot. A future test must specify its DEM, resampling, region summary
   statistic, and contribution to a score before using it in a choice.

## Limitations and Next Steps

- This is one date-stamped NRCS retrieval cohort. Source data can change, so
  repeatable cache/provenance capture is required before comparing future runs.
- The IID pixel design estimates mapped area, not the prevalence among unique
  MUKEYs, geographic regions, or individual watersheds.
- The sample does not yet construct connected MUKEY regions, shared boundaries,
  candidate valid soils, or elevation summaries. It cannot choose a fallback.
- The current research runner derived field-level completeness from returned
  component/horizon rows. The planned structured production collector should
  record the same information at the build boundary without relying on a
  separate rerun.

Next, build deterministic fixtures for the observed classes (no component, no
horizons, missing required texture fields, and nonphysical texture balance).
If those are complete, define a normalized feature comparison and an explicit
minimum practical effect before reconsidering an ADR-governed opt-in policy.

## Reproducibility Artifacts

The local, non-versioned study directory is
`/tmp/ssurgo_empirical_study_20260721/`:

- `gnatsgo_2025_mukey_inventory.json` — complete VAT-derived MUKEY pixel
  inventory.
- `gnatsgo_2025_area_weighted_pilot_2048.jsonl` — per-MUKEY diagnostic records
  with draw weights.
- `gnatsgo_2025_area_weighted_pilot_2048_summary.json` — aggregate outcomes.
- `gnatsgo_2025_area_weighted_pilot_2048_diagnostic_summary.json` — validated
  reason-code aggregation.
- `gnatsgo_2025_area_weighted_12288.jsonl` and `_summary.json` — expanded
  mapped-area cohort and draw-weighted result.
- `gnatsgo_2025_area_weighted_12288_diagnostic_summary.json` — validated
  unique-MUKEY reason aggregation for the expanded mapped-area cohort.
- `gnatsgo_2025_uniform_mukey_2048.jsonl` and `_summary.json` — distinct,
  equal-probability MUKEY cohort and result.
- `gnatsgo_2025_uniform_mukey_2048_diagnostic_summary.json` — validated
  reason aggregation for the uniform-MUKEY cohort.
- `/tmp/ssurgo_masked_valid_20260722/cohort_full.json` — read-only
  298-case masked-valid cohort with candidate support and elevation/feature
  comparisons. It can be recreated with
  `tools/ssurgo_masked_valid_evaluation.py --run <run> ...`; it is not
  committed because it contains local run paths and date-scoped run evidence.
- `/tmp/ssurgo_masked_valid_20260722/scoring_ned1_full.json` — NED1-backed
  geometry/terrain variant records and aggregate comparisons; the one- and
  four-worker repeat artifacts use the matching `scoring_ned1_workers*.json`
  names in the same non-versioned directory.

The raw diagnostic JSONL is intentionally not committed: it is a large,
date-sensitive external-data extract. The inventory and JSONL can be recreated
with `tools/ssurgo_empirical_study.py`, the recorded raster path, seed, and
converter settings above. The current scaffold is documented in
`docs/planning/ssurgo-intelligent-fallback-strategy.md`.
