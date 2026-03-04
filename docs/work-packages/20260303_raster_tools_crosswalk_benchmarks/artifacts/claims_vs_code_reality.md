# Claims vs Code Reality Addendum

## Source Under Review

- USDA Rocky Mountain Research Station "Science You Can Use Tool" PDF:
  `https://research.fs.usda.gov/download/treesearch/80116.pdf`

## Verifiable Capability Claims (Supported by Source Evidence)

1. `raster_tools` is a substantial geospatial processing library with direct support for core raster workflows used in this package shortlist (`projection`, `clipping`) and additional surfaces (`rasterization`, `surface`, `zonal`) documented in the cross-walk.
2. The package includes model-inference integration points, but they are generic "bring your own model" interfaces:
   - `ModelPredictAdaptor` wraps callables/objects.
   - `model_predict_raster` and `model_predict_vector` require a user-supplied `model.predict(...)`.
3. Package benchmarks in this work-package successfully executed `raster_tools` reprojection/clipping and supplemental zonal timing runs, so operational invocation is demonstrated on this host.

## Claims Not Established by This Package (Or Contradicted Directionally)

1. Broad "AI" framing is not equivalent to a built-in AI stack in the reviewed code:
   - Default requirements do not include bundled AI/ML frameworks like `scikit-learn`, `torch`, or `tensorflow`.
   - The surfaced pattern is inference hooks around externally provided models.
2. Claim of "significantly less memory, space, and processing time than other related applications" is not supported by this package evidence:
   - `BW-01`/`BW-02` directional timing in this package was slower for `raster_tools` (`49.73x`, `16.92x`) and both cases were parity `non-comparable` due grid mismatch.
   - Supplemental zonal timing also showed slower medians for `raster_tools` than both zonal comparators, with explicit non-equivalent-semantics caveats.
3. Platform breadth and ecosystem claims in the PDF were not audited in this package (scope was WEPPpy overlap and benchmark evidence only).

## Evidence Required Before Accepting Marketing Claims as Engineering Fact

1. Comparable parity benchmarks across all shortlisted overlap rows (`BW-01` to `BW-05`) with strict equivalence contracts.
2. Runtime fairness controls (same environment baseline, startup overhead controls, reproducible datasets/commands).
3. Explicit memory and storage telemetry (peak RSS, temp file size, IO volume), not runtime alone.
4. Concrete AI workflow evidence (model training/inference pipelines, dependency stack, and measured value over non-ML baselines).

## References

- PDF under review: `https://research.fs.usda.gov/download/treesearch/80116.pdf`
- Cross-walk matrix: `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/artifacts/capability_crosswalk_matrix.md`
- Benchmark results: `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/artifacts/benchmark_results.md`
- Recommendation memo: `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/artifacts/adoption_recommendation.md`
- Raw evidence note: `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/notes/raw/m6_claims_vs_code_reality_evidence.txt`
- `raster_tools` model-predict interfaces:
  - `/home/workdir/raster_tools/raster_tools/general.py:337`
  - `/home/workdir/raster_tools/raster_tools/general.py:418`
  - `/home/workdir/raster_tools/raster_tools/raster.py:2090`
  - `/home/workdir/raster_tools/raster_tools/vector.py:783`
- `raster_tools` default requirements:
  - `/home/workdir/raster_tools/requirements/default.txt:1`
