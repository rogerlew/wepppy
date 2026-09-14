# SSURGO horizon validity for M3 thickness

Assessed 2026-09-11 from repository source; no soil data or implementation changed.

## Existing rules and suitability

`wepppy/soils/ssurgo/ssurgo.py::Horizon.valid` tests WEPP parameter readiness:
non-organic master designation, numeric bottom depth, positive sand/clay/CEC,
and numeric organic matter, very-fine sand, conductivity and bulk density.
The constructor also estimates missing hydraulic/density properties and applies
configured defaults before validity is evaluated. `_get_horizons` keeps this
mask, and component selection accepts the first component with any valid layer.
`_analyze_restrictive_layer` can shorten the modeled profile at a conductivity
threshold. These are appropriate concerns for building WEPP soil inputs.

They are not sufficient as the sole M3 cumulative-thickness validator:

- `valid` does not test top depth, bottom greater than top, duplicate horizons,
  overlap, gaps or consistency with reported thickness.
- Missing texture/CEC can reject a horizon whose measured depth interval remains
  usable for thickness. Calling the full constructor would run unrelated
  property estimation just to inspect depth.
- Organic exclusion is an existing WEPP choice, not established evidence that
  M3 should exclude organic thickness. Bedrock/ambiguous material handling must
  be assessed against the intended M3 definition.
- A first usable component and conductivity-truncated WEPP profile do not
  establish an area/component-weighted cumulative soil thickness.

## Existing M3 precedent

`postfire_debris_flow/soil_thickness.py::derive_component` already validates raw
intervals, repeated IDs, top/bottom ordering, gaps/overlap and reported thickness.
Its `strict_soil` policy includes organic layers, excludes clearly identified R
bedrock, and flags ambiguous materials. `derive_mapunits` already records
component weights, partial support and reasons. These are offline study rules;
they are not automatically approved production heuristics.

Reuse the existing SSURGO acquisition/cache and inspect raw horizon records.
Compare and ratify the existing thickness helper's material/component rules;
do not implement a third parallel horizon parser or reuse clipped `.sol` depth.
A built WEPP soils project establishes the required workflow prerequisite but
not complete M3 thickness support. Full integration must retain source-specific
validity/fallback evidence and report residual masked coverage.

Next evidence: exercise cached raw horizons from the development basin and
existing offline fixtures; contrast WEPP-valid, depth-valid and rejected rows,
with explicit reasons and component/map-unit support. Resolve material inclusion
and fallback granularity from those results before changing the production
soil estimator. The wiring increment does not acquire data, rebuild soils or
ratify an arbitrary completeness threshold.

## Production research (2026-09-14)

The retained Staley manuscript, sections 3.2 and 5.1 and Table 4, uses STATSGO
soil thickness/100 for M3 and suggests thickness may reflect sediment
availability. It does not specify SSURGO material or component rules. The
[USGS publication record](https://pubs.usgs.gov/publication/70188478) identifies
the paper. Source substitution remains an explicit empirical-model limitation.

The accessible [USGS THICK catalog](https://catalog.data.gov/dataset/statsgo-soil-thickness-thick-cloud-optimized-geotiff-for-the-continental-us)
confirms inch units, a 2025 reformat of the 1995 source, nominal 30 m cells,
EPSG:5069, NaN outside coverage and negative water sentinel values. This is the
approved fallback dataset; a modern project STATSGO tabular cache is a different
source. Existing [historical extraction evidence](m3_soil_thickness.md#original-reference)
establishes cumulative layer thickness, not hydraulic restriction depth.

[NRCS Fundamental Query v1.1](https://sdmdataaccess.nrcs.usda.gov/documents/FundamentalQuery.pdf),
pages 4–6, defines representative component percentages and depth endpoints in
cm. It explicitly permits component totals below or above 100 and explains
paired transitional horizon records sharing depth intervals. Most other gaps
and overlaps are described as likely errors. Survey version/date tracks source
vintage. These facts require production handling beyond blanket overlap and
overfull-total rejection; they do not prescribe our aggregation policy.

[NRCS Tables and Columns v2.3.2](https://www.nrcs.usda.gov/sites/default/files/2022-08/SSURGO-Metadata-Tables-and-Columns-Report.pdf),
Horizon table, page 10, describes two-part E/B or E&Bt horizons stored on separate
rows at the same depths. Counting both rows as additional physical depth would
double-count that interval. Identify documented pairs explicitly; do not use
unconditional interval union to conceal arbitrary overlaps.

[NRCS Soil Profile guidance](https://www.nrcs.usda.gov/resources/education-and-teaching-materials/a-soil-profile)
distinguishes organic O, ordinary soil horizons including C, and hard-bedrock R.
This supports evaluating organic inclusion and R exclusion separately from
WEPP's parameterization filter. It does not resolve Cr/weathered material
against the calibrated THICK extraction. No production material policy is
approved by this research alone.

Recommended checkpoint: reuse raw-depth helpers with an explicit production
policy; evaluate paired intervals, material inclusion, usable-component weighting
and cellwise SSURGO/THICK fallback. Retain component completeness separately
from mapped valid coverage. Do not assume every component can be located within
a map-unit cell. Preserve offline defaults while comparing alternatives.

**Regression boundary:** do not change SSURGO/STATSGO soil-building validity,
selection, donor fallback, clipping, caches or `.sol` generation for M3. Consume
upstream records read-only; put the depth-specific adapter here. Verify source
preservation and generated WEPP soil-file parity on isolated projects.
The [production contract](production_m3.md) records this owner requirement and
the [active package](../../../../../docs/work-packages/20260914_staley_m3_integration/package.md)
contains the source audit and exact regression obligations.
