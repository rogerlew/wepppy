# ExecPlan - SSURGO Corestrictions `kslast` Viability Assessment

## Objective

Execute a reproducible viability assessment for using SSURGO `corestrictions` fields to parameterize WEPP restrictive-layer `kslast`, benchmarked against legacy behavior, across diverse U.S. ecoregions.

## Milestone Status

- [x] **M0 - Scope Freeze and Inputs**
  - Final ecoregion matrix fixed in artifacts (`query_provenance.json`).
  - Legacy baseline frozen from `wepppy/soils/ssurgo/ssurgo.py` + `wepppy/soils/ssurgo/ssurgo.md`.
  - Reproducible extraction harness recorded in `artifacts/run_corestrictions_kslast_viability.py`.

- [x] **M1 - Coverage and Completeness**
  - National full-table coverage extracted for `corestrictions`, `brockdepmin`, and `ksat_r`.
  - Ecoregion-stratified sampled coverage extracted with explicit denominators.
  - Artifacts: `coverage_report.md`, `national_coverage.csv`, `ecoregion_coverage.csv`.

- [x] **M2 - Reasonableness Diagnostics**
  - Range/consistency and semantic-direction checks run on sampled ecoregion cohorts.
  - Anomaly catalog captured in `reasonableness_anomalies.csv` + `reasonableness_checks.md`.

- [x] **M3 - Candidate Rule Evaluation**
  - Candidate A (depth-gated legacy anchor) and Candidate B (restriction-class transfer) implemented.
  - Hard bounds + fallback logic enforced.
  - Input-space legacy-vs-candidate comparison captured in `candidate_summary_by_ecoregion.csv` and `legacy_vs_candidate_summary.md`.

- [x] **M4 - Hydrologic Comparisons by Ecoregion**
  - Representative comparison completed as input-space + directional hydrologic proxy (not full WEPP hydrograph reruns).
  - Regional directional patterns documented in `legacy_vs_candidate_summary.md`.

- [x] **M5 - Recommendation and Handoff**
  - Final recommendation memo published: `recommendation_memo.md` (`retain legacy`).
  - Follow-up implementation-gating checklist included in memo.

## Progress

- **2026-05-23 00:54-01:08 UTC**
  - Built and executed reproducible SDA/EPA analysis harness.
  - Produced all required package artifacts under `artifacts/`.
  - Updated recommendation based on mixed coverage, anomaly burden, and fallback dependence.

## Surprises & Discoveries

- Full-region SDA polygon-ranked extraction was unstable/slow for several large eastern/southern regions.
- Final approach used a hybrid strategy:
  - polygon-ranked for first three regions where stable;
  - bounded point-sampled fallback for remaining regions.
- This produced explicit restrictive-present sample shortfalls in six regions due SDA extraction/runtime constraints; those regions were flagged low-confidence for inference.

## Decision Log

- **2026-05-23**: Keep assessment-only scope; no production `ssurgo.py` changes.
- **2026-05-23**: Accept hybrid sampling (polygon-ranked + bounded point-sample) to preserve reproducibility under SDA performance constraints.
- **2026-05-23**: Treat missing restrictive-present quotas as infrastructure-constrained sampling signals, not evidence of underlying SSURGO dataset absence.
- **2026-05-23**: Final recommendation set to `retain legacy` pending stronger regional evidence and run-fixture hydrologic validation.

## Outcomes & Retrospective

- Package delivered all required artifacts and reproducible scripts.
- Strongest blocker to higher-confidence adoption was not formula availability; it was infrastructure-constrained regional sampling depth under current SDA extraction/runtime limits.
- Follow-up should prioritize:
  1. Frozen WEPP run fixture matrix for full M4 hydrograph validation.
  2. More scalable regional extraction path (pre-materialized mukey cohorts or offline stratified caches).
  3. Additional restrictive-present sampling depth in infrastructure-constrained low-confidence ecoregions.

## Guardrails

- No production `ssurgo.py` parameterization changes in this package.
- Denominators and missing-data treatment are explicit in reports/CSVs.
- Conclusions remain conservative where extraction/runtime constraints limit sampling depth.
- Candidate formulas include hard bounds and explicit fallback behavior.
