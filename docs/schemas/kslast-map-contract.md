# Project-grid kslast map contract

Status: accepted design, 2026-09-09; implementation pending. Authority for WEPPpy bedrock-map preparation in ordinary and MOFE workflows. Provenance: [ADR](../adrs/20260909_kslast_area_weighted.md).

## Grid and artifacts

When a kslast map is configured, prepare run-local `soils/kslast.tif` on exactly the `watershed.subwta` CRS, affine transform, dimensions, and extent. Use nearest-neighbor resampling, a floating dtype, and explicit destination nodata. Honor source nodata/masks; uncovered destination pixels remain nodata, including when the source does not declare nodata. Keep nodata in the saved raster, not permanently filled with the default.

WEPPpy normalizes NaN/infinity and nonpositive conductivity values to nodata, reports invalid-value counts, and interprets valid conductivity in mm/h. Do not infer an upper plausibility cutoff or units from raster magnitudes. Corrupt/missing configured raster or unusable CRS is a hard error, not a coverage fallback. No-map configuration preserves existing scalar/no-override behavior and does not consume a stale generated map.

## Aggregation and fallback

For each eligible hillslope key, calculate the arithmetic area-weighted mean on the aligned project grid. Ignore key-raster nodata and channels. WEPPpy must exclude background/non-hillslope keys (including zero) explicitly; the native kernel must not infer conductivity-domain key policy. Constant projected pixel area makes this equivalent to a pixel-count-weighted mean. This is not an exact source-pixel intersection or geodesic area calculation. Geographic grids are unsupported by the initial area kernel and must fail explicitly rather than be treated as equal ground area.

For valid area V, missing area M, values k_i and configured default d:

    mean = (sum(area_i * k_i over V) + area(M) * d) / area(V union M)

A partial or fully uncovered hillslope uses d only for missing area. Any missing area without a configured default is an explicit error identifying affected keys/coverage before soil worker submission. For mapped preparation, the configured default must be finite and positive when supplied. No arbitrary coverage cutoff is used. A fully covered hillslope needs no default. Zero valid coverage with a valid default produces that default and records 100% missing coverage.

## Generic native boundary

`wepppyo3.raster_characteristics.identify_area_weighted_mean_single_raster_key` is domain-neutral. It accepts aligned key and parameter rasters, optional finite `default_value`, band index, and existing key/channel exclusion options. Finite negative and zero parameter/default values are valid generic data unless designated nodata. WEPPpy alone applies conductivity-specific positivity rules. Raster masks, declared nodata and nonfinite parameter values are missing. Key nodata/excluded keys do not enter denominators.

Return a deterministic mapping from string key to a record containing `mean`, `valid_cell_count`, `missing_cell_count`, and `total_cell_count`. Count totals must agree; no eligible key is silently omitted. No eligible keys returns an empty mapping. Invalid band/CRS/grid alignment, I/O failure, nonfinite default, or missing parameter cells without a default raises a bounded descriptive Python exception. Validate dimensions, CRS equivalence, all affine coefficients and data lengths; do not zip unmatched arrays. Reject singular/nonfinite transforms. Keep numerical accumulation stable and results finite.

## WEPP preparation and provenance

One shared preparation path computes per-hillslope results for ordinary and MOFE soil preparation. Every OFE receives its hillslope result, subject to the existing developed-soil modification exemption. Do not compute separate per-OFE spatial averages. Do not sample centroids, including as a fallback.

Publish additive `soils/kslast_summary.json` with source/grid identity, aggregation/resampling policy, configured default, normalization counts, and per-key result/coverage records. Log default fractions and retain provenance in generated soil comments. Rebuild from current source/grid inputs on prep; changing only the default must recompute summaries and soil overrides. Validate before atomic artifact publication and before worker scheduling, using canonical NoDir/NoDb writer boundaries. Existing schemas/keys remain unchanged. Failed preparation must not report stale outputs as current success.

## Rationale and verification

Ignoring missing cells silently assumes the mapped portion represents the whole hillslope. Area-based default substitution makes that assumption explicit and preserves coverage evidence. Generic Rust semantics avoid coupling reusable raster statistics to soil physics. Nearest-neighbor stacking preserves mapped classes; arithmetic aggregation can still be dominated by a small high-conductivity fraction, which is intended.

Required examples: 80% at 0.0001 plus 20% default 0.05 gives 0.01008; 99% at 0.0001 plus 1% at 0.5 gives 0.005099. Verify prepared soil values and fresh full WEPP execution, not only kernel results. Existing saved run artifacts require a new authorized preparation/run to adopt this behavior.

## Directory-only runtime boundary

Current runtime paths have retired NoDir materialization. Mapped prep requires
an existing soils directory; archive-only roots fail before publication. In
mixed legacy roots the directory is authoritative and the archive is left
untouched. Use the active soils maintenance lock for one artifact writer.
No archived-root thaw or archive rewrite is introduced.

Warp with explicit Float64 NaN nodata so no finite invalid source conductivity
collides with a destination sentinel. Normalize the staged result to negative
nodata (-9999) before aggregation/publication; no nonpositive value is valid
conductivity. Generic raster_stacker rejects finite sentinel collisions before
creating output, rather than silently relabeling valid source data.
