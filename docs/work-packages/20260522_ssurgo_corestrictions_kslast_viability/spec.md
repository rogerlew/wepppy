# Spec - SSURGO Corestrictions `kslast` Viability Assessment

## 1. Purpose

Determine whether SSURGO bedrock/restriction attributes are sufficiently available, physically plausible, and hydrologically useful to support a WEPP restrictive-layer `kslast` parameterization that is superior to or safer than the current legacy heuristic.

## 2. Assessment Questions

1. Are key fields available at useful coverage nationally and across major U.S. ecoregions?
2. Are field values internally consistent and physically plausible for restrictive-layer semantics?
3. Do candidate `corestrictions`-driven rules produce better or at least non-degrading behavior relative to legacy `kslast`?
4. What guardrails are needed to avoid pathological parameterization where SSURGO restriction signals are weak?

## 3. Data Inputs

- SSURGO tables:
  - `component` (`mukey`, `cokey`, `comppct_r`)
  - `chorizon` (`ksat_r`, depth fields)
  - `corestrictions` (`reskind`, `resdept_r`, `resdepb_r`, `resthk_r`, `reshard`)
  - `muaggatt` (`brockdepmin`)
- Existing WEPPpy soil build pipeline outputs.
- Reference run set used for cross-ecoregion hydrologic comparison.

## 4. Ecoregion Matrix (Initial Target)

Use EPA Level III ecoregions (or closest operational equivalent available in existing WEPPpy geography layers).

Target at least these hydroclimatic/geomorphic classes:

1. Marine West Coast Forest
2. Cascades
3. Sierra Nevada
4. Mediterranean California (California chaparral/oak woodlands)
5. Columbia Plateau / Intermountain basins
6. High Plains / Northern Great Plains
7. Central Corn Belt Plains
8. Ridge and Valley / Blue Ridge
9. Southeastern Plains
10. Southern Coastal Plain
11. Mississippi Alluvial Plain
12. Mojave/Chihuahuan Basin and Range

If data sufficiency is low in any region, keep it in scope and explicitly record insufficiency rather than silently substituting other regions.

## 5. Sampling Strategy

For each selected ecoregion:

- Construct component-level sample bins:
  - `corestrictions bedrock/restrictive present`
  - `corestrictions absent`
- Include dominant components first (`comppct_r` descending) and record weighting policy.
- Minimum target sample per ecoregion:
  - 150 components where restriction is present (if available)
  - 150 components where restriction is absent (if available)
- Where counts are insufficient, include all available and tag as low-confidence region.

## 6. Reasonableness and Consistency Checks

## 6.1 Field-level checks

- Null-rate and sentinel-value profiling by field.
- Range checks:
  - `resdept_r`, `resdepb_r`, `resthk_r`, `brockdepmin` non-negative and plausible (cm domain).
  - `ksat_r` positive where present (um/s domain in WEPPpy).
- Structural checks:
  - `resdepb_r >= resdept_r` when both present.
  - `resthk_r` approximately coherent with `(resdepb_r - resdept_r)` when all three exist.

## 6.2 Semantic checks

- Bedrock-like `reskind` classes should correlate with shallower restriction depths than non-bedrock restrictions.
- Hardness categories (`reshard`) should show directional consistency with lower inferred restrictive conductivity assumptions.
- Compare `brockdepmin` against component-level restriction depths for consistency envelope.

## 7. Candidate Parameterization Strategies

Evaluate at least two candidate families versus current legacy behavior:

- **Candidate A (Depth-gated legacy anchor)**:
  - Retain horizon-derived conductivity anchor, apply depth/hardness gates from `corestrictions`.
- **Candidate B (Restriction-class transfer function)**:
  - Map `reskind` + `reshard` + depth metrics to bounded `kslast` multipliers.

Each candidate must define:

- Input requirements and fallback path.
- Hard bounds for `kslast` (mm/h).
- Monotonicity expectations:
  - Shallower/stronger restrictions should not increase `kslast`.

## 8. Legacy Comparison Design

Baseline is current `ssurgo.py` behavior documented in `ssurgo.md` (`0.01` default/no-restriction and `/1000` restrictive-layer heuristic after unit conversion).

Compare on:

- Input-space changes:
  - `slflag` rate
  - `kslast` distribution by ecoregion
  - fraction hitting bounds/fallback
- Output-space changes (representative run set per ecoregion):
  - runoff volume
  - peak runoff
  - hydrograph smoothness indicators
  - infiltration/percolation-related terms where available

## 9. Decision Framework

Recommend `adopt` only if all are true:

- Coverage is operationally sufficient in most selected ecoregions.
- Reasonableness checks show no widespread contradictions.
- Candidate improves or is neutral for key hydrologic behaviors relative to legacy.
- Fallback rules cover low-data regions without instability.

Recommend `adopt with guardrails` if mixed by region but controllable with explicit region/data-quality switches.

Recommend `retain legacy` if inconsistencies are frequent or behavior gains are not robust.

## 10. Outputs

- `artifacts/coverage_report.md`
- `artifacts/reasonableness_checks.md`
- `artifacts/ecoregion_comparison_matrix.csv`
- `artifacts/legacy_vs_candidate_summary.md`
- `artifacts/recommendation_memo.md`

## 11. Non-Goals

- Production cutover in this package.
- Reparameterizing unrelated WEPP soil/hydrology terms.
- Creating new external dependencies without separate dependency-evaluation workflow.
