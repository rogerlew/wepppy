# Adoption Recommendation Memo (Milestone 5)

## Recommendation

**Recommendation: `defer`** (current draft evidence).

## Why

1. Benchmark parity is incomplete across shortlisted overlap families (`BW-03`, `BW-04`, `BW-05` deferred).
2. Executed cases did not produce parity-comparable outcomes under the stricter grid-equivalence contract:
   - `BW-01` and `BW-02` are both marked `non-comparable` due grid mismatch (`same projection`, but different shape/geotransform).
   - Runtime deltas were recorded as diagnostic telemetry only and are not decision-grade evidence while parity preconditions are unmet.
3. Execution required split runtime environments (system Python for WEPPpy/GDAL vs dedicated venv for `raster_tools`), which introduces a fairness confound and weakens decision certainty.
4. Supplemental curiosity zonal timings (outside shortlist scope) also showed `raster_tools` slower than both zonal comparators, but with non-identical semantics, so they are directional-only evidence:
   - `small`: `raster_tools` median `2.9007s` vs `oxidized-rasterstats` `0.2669s` and `wepppyo3` `0.0465s`.
   - `large_local`: `raster_tools` median `34.1748s` vs `oxidized-rasterstats` `2.7439s` and `wepppyo3` `0.1057s`.

Evidence references:

- Cross-walk: `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/artifacts/capability_crosswalk_matrix.md`
- Plan/harness details: `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/artifacts/benchmark_plan.md`
- Results: `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/artifacts/benchmark_results.md`
- Claims-vs-code addendum (includes USDA PDF link + source-grounded claim audit): `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/artifacts/claims_vs_code_reality.md`
- Raw timings: `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/notes/raw/benchmark_runs_bw01_bw02.json`
- Supplemental zonal timings: `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/notes/raw/zonal_benchmark_wepppyo3_oxidized_rasterstats.json`
- Supplemental zonal timings: `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/notes/raw/zonal_benchmark_raster_tools.json`

## Decision Framing

This is a **defer for incorporation**, not a rejection of all `raster_tools` capabilities.
The current package evidence is sufficient to avoid immediate adoption but not sufficient to justify selective integration claims.

## Residual Risks / Gaps

- Deferred shortlisted benchmarks (`BW-03` to `BW-05`) leave overlap coverage incomplete.
- `raster_tools` runs reported repeated stderr (`sys.excepthook`) despite success exit status; root cause not investigated in this package.
- Executed benchmark rows remained non-comparable under strict semantic-equivalence guards (`same projection + shape + geotransform`).
- Supplemental zonal evidence is non-equivalent by design and therefore cannot substitute for shortlist parity-comparable benchmark evidence.

## Follow-up Work Package Proposal

If stakeholders want to revisit adoption, create a follow-up package that:

1. Runs all shortlisted cases in a single normalized runtime baseline to remove environment confounds.
2. Completes deferred cases and tightens parity assertions for each operation family.
3. Investigates `raster_tools` stderr behavior seen during successful runs.
4. Re-evaluates recommendation after full parity-complete benchmarks.
