# SSURGO for M3 Soil Thickness

Assessment date: 2026-09-08. Code/schema and primary-source review only; no
run-specific completeness audit, numerical parity claim, or production change.

## Finding

SSURGO is a feasible source for an M3 cumulative soil-profile thickness estimate.
Current Soils builds already cache the relevant raw fields in the project.
Reuse those records and spatial map units rather than WEPP's processed profile
depth. Source substitution from STATSGO to SSURGO still needs validation and an
ADR before implementation.

## Original Predictor and Units

The [USGS source metadata](https://pubs.usgs.gov/ds/270/data/DVD-1/METADATA/Soil_att.htm)
defines `THICK` as cumulative thickness of all soil layers, in inches.
[Processing documentation](https://pubs.usgs.gov/ds/270/data/DVD-1/METADATA/Soils250K.htm)
describes summing layer bottom-minus-top depths. This is not automatically
depth to the first restrictive layer, bedrock depth, or root-zone depth.

USGS also distributes the original predictor as a
[STATSGO THICK COG](https://catalog.data.gov/dataset/statsgo-soil-thickness-thick-cloud-optimized-geotiff-for-the-continental-us),
explicitly in inches, nominally rasterized at 30 m. Its fine raster spacing
does not increase the original soil-map detail. It provides a useful comparison
baseline, not an approved automatic fallback. Its metadata identifies NaN and
nonphysical `-0.1` water values that must not enter a thickness mean.

For a valid SSURGO thickness `d_cm`, the M3 scaling is `d_cm / 254`.
Example: 100 cm = 39.3700787 inches, giving S = 0.393700787, not 1.0.

## Existing Project Data

| Existing source | Evidence and reuse |
| --- | --- |
| `Soils.ssurgo_cache_db_path` | Points to `soils/ssurgo_tabular_cache.sqlite`; separate STATSGO cache also exists |
| `component` | Cached `mukey`, `cokey`, `comppct_r` support map-unit/component joins and weights |
| `chorizon` | Cached `chkey`, `hzdept_r`, `hzdepb_r`, `hzthk_r`, `desgnmaster`, and `hzname` support raw interval analysis |
| `Soils.ssurgo_fn` | Project soil map-unit raster for spatial lookup; audit coverage and substitutions before use |
| `raw_ssurgo_domsoil_d`, `ssurgo_substitution_d` | Existing provenance helps identify substituted soil assignments |

Code evidence: `wepppy/nodb/core/soils.py` defines the cache paths and builds
collections for map-unit keys; `wepppy/soils/ssurgo/ssurgo.py` fetches component
and horizon records and defines the cache schema. The collection fetches
horizons for all cached components of requested map units, before selecting
WEPP-compatible profiles. Reading raw cache records avoids WEPP layer filtering.

The [NRCS Fundamental Query guide](https://sdmdataaccess.nrcs.usda.gov/documents/FundamentalQuery.pdf)
defines horizon top and bottom depths in centimeters and notes that multiple
records can share the same depth interval. Deduplication/overlap treatment is
therefore a real data concern, not just a hypothetical edge case.

## Existing Outputs That Cannot Be Reused Directly

- **WEPP `.sol` depth:** generated in mm, with possible minimum-depth changes,
  clipping, rounding, invalid-horizon filtering, and conductivity-based
  restrictive-layer handling. These serve simulation requirements and do not
  define the source STATSGO thickness predictor.
- **`SurgoSpatializer` `SolThk`:** currently sums `hzdepb_r` across horizons.
  These are cumulative bottom depths. For intervals 0-10 and 10-30 cm, it
  returns 10 + 30 = 40 cm rather than the actual 30 cm thickness. This is a
  confirmed unsuitable derivation for M3, left unchanged in this docs-only work.
- **Restriction-depth lookup:** current `corestrictions` cache holds `cokey`
  and `reskind`, not `resdept_r`. It cannot supply numeric restriction depth
  without extending acquisition/schema, and that would be a different predictor.
- **Dominant WEPP profile alone:** is not the same as a component-weighted
  map-unit estimate; substitutions must not be mistaken for original SSURGO.

## Proposed Derivation and Remaining Decisions

1. Require completed Soils data and inspect source provenance/cache coverage.
   Legacy, custom, or fallback-built soil inventories may not provide SSURGO
   horizons even when WEPP can run successfully.
2. Read raw horizons by component and validate finite top/bottom depths and
   positive intervals. Resolve duplicate/overlapping intervals, profile gaps,
   and which bedrock designations to exclude before defining thickness.
3. Compute cumulative soil-layer thickness from valid intervals. For a complete
   contiguous profile starting at zero this equals the deepest soil-horizon
   bottom; that shortcut is not valid for arbitrary incomplete records.
4. Propose weighting components using `comppct_r`, then map-unit contributions
   by their area in each assessment catchment. Resolve missing component
   percentages and partial coverage explicitly; no silent renormalization.
5. Convert cm to inches and divide by 100 for M3, preserving full precision.
   Write source and aggregation provenance in the eventual output artifact.
6. Compare against original STATSGO THICK for representative Western US projects,
   measuring both thickness differences and resulting M3 probability/threshold
   differences. More detailed soil mapping does not itself prove improved
   performance of the empirical model.

No fixed 150/200 cm depth, zero-fill, POLARIS layer-depth substitution, WEPP
clipped-depth substitution, or automatic network fallback is established.
Missing/invalid thickness needs an explicit unavailable result or submission
error according to the eventual catchment-coverage contract. Unknown depth must
not be described as confirmed zero soil thickness.

## Acceptance Before Runtime Work

Specify the depth and aggregation policy in an ADR and canonical contract,
audit representative project caches, and cover duplicate/gapped/bedrock
horizons, missing components, custom/legacy sources, and unit equivalence.
Any additive thickness artifact/schema needs a compatibility plan and tests
showing propagation to the actual assessment outputs. Keep existing Soils and
RUSLE artifacts unchanged unless separately authorized by the implementation
contract. Follow the owned geospatial stack for raster aggregation.
