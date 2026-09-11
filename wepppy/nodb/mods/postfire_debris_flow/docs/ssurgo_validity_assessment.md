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
