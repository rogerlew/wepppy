# M3 Terrain Evaluation

Status: design investigation, 2026-09-08. Recommendations below are not a
ratified algorithm or evidence of numerical parity. No executable changes.
Canonical requirements remain in the [specification](../specification.md).

The user selected WBT implementation followed by the resolution study.
The [execution package](../../../../../docs/work-packages/20260908_staley_m3_wbt_terrain/package.md)
contains the fresh-agent handoff and active ExecPlan. Algorithm details below
remain candidates until that package establishes the contract and evidence.

## Definition and Complexity

The working M3 definition is vertical relief divided by square root of total
upstream planimetric area, using meters and square meters (dimensionless).
The local accepted manuscript section 5.2 omits the square root in prose;
the [USGS model guide](https://ghsc.code-pages.usgs.gov/lhp/pfdf/guide/models/s17.html)
specifies it. Exact relief semantics still require a numerical reference check.

Candidate physical calculation at outlet `o`:

```text
H(o) = maximum upstream elevation - elevation at outlet o
T(o) = H(o) / sqrt(upstream area including outlet cell)
```

For a monotonic drainage surface the maximum upstream elevation lies at an
upstream source, and the outlet is the minimum. On raw elevations routed using
a conditioned DEM, these equivalences can fail. Compare highest-source relief,
maximum-upstream-minus-outlet, and catchment max-minus-min explicitly before
choosing the scientific contract. Do not substitute a local terrain ruggedness
index or whole DEM rectangle statistics.

A D8 topological traversal propagating maximum upstream elevation and area
is O(N) time and O(N) working memory for N raster cells. Each cell contributes
to its downstream neighbor once; confluences combine upstream maxima and area.
Sample results at all assessment outlets after this shared pass. Nested
catchments do not require separate full-raster traversals or polygon creation.
The arithmetic is small; routing conventions, boundaries, elevation provenance,
NoData, cycle detection, and reproducibility are the substantive work.

## Existing Implementation Evidence and Ownership

- Local pfdf `watershed.relief` passes raw-DEM cell elevation drops and D8
  routing into a patched pysheds distance-to-ridge routine. Segment ruggedness
  samples this raster at outlets and divides by square root of upstream area.
  Its documentation alternates between nearest and highest ridge.
- The inspected upstream [pysheds recurrence](https://github.com/mdbartos/pysheds/blob/master/pysheds/_sgrid.py)
  selects a maximum weighted path, not a nearest ridge. This is source
  inspection, not a pinned installed-version comparison. Weight indexing,
  terminal-cell behavior, and raw-DEM nonmonotonic paths must be tested before
  asserting equivalence to maximum elevation minus outlet elevation.
- Local `weppcloud-wbt/whitebox-plugins/src/max_upslope_value/main.rs` already
  implements downstream maximum propagation, but derives D8 routing internally
  from its DEM. It is useful owned-stack precedent, not a verified drop-in
  implementation for the project's existing pointer raster.
- WEPPpy's `wbt/relief.tif` is a conditioned elevation DEM produced by
  `_create_relief`, not vertical catchment relief. Never consume it directly
  as Staley H. Keep routing DEM and elevation measurement source distinct.

Recommendation: put any required raster traversal in weppcloud-wbt Rust,
accepting the authoritative project D8 pointer and an explicitly selected
elevation raster. Reuse or extend the existing maximum-propagation capability
after verifying its contracts. Keep Staley coefficients, probabilities,
unitization, and dashboard orchestration in WEPPpy. Do not copy or translate
GPL pfdf source/tests; use independently derived synthetic expectations and
external numerical comparison. A parameterization ADR and implementation
ExecPlan must precede production changes.

## Catchment Comparisons and Resolution

Yes: identify fixed physical outlets and their full upstream catchments for
comparison. A WEPP hillslope or incremental subcatchment is not automatically
the entire contributing catchment of a channel outlet.

Recommended evaluation stages:

1. Small independently authored D8 fixtures: a descending chain, unequal
   tributaries, nested outlets, flats, conditioned pits, NoData boundaries,
   invalid cycles, and an interior raw-elevation maximum. Establish exact area
   inclusion and relief expectations before comparison to pfdf.
2. Same-grid comparison using identical elevation, D8 routing, masks, and outlet
   cells in WBT and the separate pfdf reference environment. Convert pointer
   encodings explicitly. Compare area and relief separately before ruggedness;
   differences may reflect reference behavior rather than WBT defects.
3. Resolution comparison at fixed geographic outlets with documented snapping:
   first controlled 10-to-30 m aggregation to isolate resolution, then available
   native products to assess practical source differences. Re-delineate at each
   resolution and report changes in area, boundary overlap, outlet elevation,
   maximum elevation, H, and T. Holding SBS fraction and soil thickness fixed,
   compare M3 probabilities and inverse thresholds to isolate terrain effects.

Start with a proposed 6-10 representative outlet catchments spanning small
headwaters, nested tributaries, steep dissected terrain, gentler terrain, and
conditioning-sensitive flats/depressions. This is an engineering comparison
panel, not validation of predictive skill. The local WBT
`test_fixtures/gatecreek_10m_30_2` contains routing, channel, outlet, and elevation
artifacts and is a candidate integration fixture; audit actual raster metadata,
source DEM availability, and geographic scope before selecting it. A fixture
name alone is not resolution evidence. Published-fire catchments would add
scientific relevance if reproducible inputs and outlets can be obtained.

10 m matches the paper's terrain-data resolution and is the recommended
reference. 30 m is computationally feasible but not yet accepted as equivalent.
At 0.02 km2, nominal cell counts are about 200 versus 22; this illustrative
scale is not a statement of the paper's calibration minimum. Upsampling 30 m
does not restore 10 m information. Numerical parity tolerances, acceptable
resolution effects, and any small-catchment restriction remain to be set from
the evaluation evidence; no arbitrary cutoff is proposed here.
