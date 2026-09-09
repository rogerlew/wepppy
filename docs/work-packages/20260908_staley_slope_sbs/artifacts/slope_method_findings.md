# Initial slope-method findings and decision register

Recorded 2026-09-09 05:08 UTC. Research for scaffolding, not a completed comparison.

## Confirmed evidence

The local Staley 2017 accepted manuscript, methodology section 4 (printed pp.
12–13), specifies 10 m DEMs; section 5.2 and Table 4 define the joint moderate/
high-burn and ≥23° predictor. Inspection did not establish the differentiation
stencil, conditioning, edge policy or software version. Do not infer them from
an unrelated later implementation. Local PDF remains ignored under its rights
policy. [Publication](https://doi.org/10.1016/j.geomorph.2016.10.019).

Owned WBT `whitebox-tools-app/src/tools/hydro_analysis/fvslope.rs` measures
DEM drop to the D8 receiver divided by distance, clamping negative drops to
zero. This is a directional routing quantity. Its units are selectable; the
existing project value is not evidence of a surface-gradient method.

Owned WBT `whitebox-tools-app/src/tools/terrain_analysis/slope.rs` documents
and implements a Florinsky 5×5 fit for projected grids and a different method
for geographic grids. Calling generic `Slope` does not select Horn.

[Esri planar Slope](https://doc.esri.com/en/arcgis-pro/latest/tool-reference/spatial-analyst/how-slope-works.html)
documents a weighted 3×3 gradient with validity-dependent edge weights.
[GDAL gdaldem](https://gdal.org/en/stable/programs/gdaldem.html) provides Horn
and Zevenbergen–Thorne and documents its missing-neighbor policy. These provide
independent method references; neither proves what Staley used. GDAL can be an
offline comparator, not a replacement for the requested owned Rust execution.
Esri and strict-neighborhood GDAL differ near NoData despite agreement on the
full-neighborhood formula. Record these differences rather than claiming whole-
raster parity. USGS pfdf documentation fetches returned 403 during this pass;
no GPL source or tests were consulted or copied.

## Decisions and recommendations

| ID | Recommendation | Decision/evidence needed |
| --- | --- | --- |
| S01 | Horn 3×3 adopted by owner, ADR-0058. Raw project DEM remains recommended; preserve existing FVSlope and generic Slope. | Algorithm resolved 2026-09-09 UTC; verify implementation and characterize sensitivity. Source/edge policies remain open. Original calibration equivalence is unproven. |
| S02 | Compute on the full available DEM before applying the watershed mask; require a valid center and eight valid neighbors, with no edge interpolation. | Document one-cell halo and residual unknown support; compare strict Horn with published Esri missing-neighbor behavior. Raw versus conditioned surface effects must be separated from algorithm effects. |
| S03 | Accepted: preserve unknown intersection support; report full-area counts and bounds, with no point T where unresolved cells remain. | Owner accepted 2026-09-09 UTC, ADR-0058. No partial extrapolation, zero fill or coverage cutoff. A known false operand determines a false intersection even if the other operand is missing. |
| S04 | Explicit recognized SBS class mapping from the existing SBS owner; no dtype/range guesses, recoding of NoData as unburned, or bilinear class resampling. | Audit `Disturbed.sbs_4class_path` and `SoilBurnSeverityMap`; distinguish normalized four-class values from legacy landuse burn codes 130–133. Engineering contract, not an extra user classification workflow. |
| S05 | Evaluate both existing 10 m and 30 m project fixtures without imposing a new M1 resolution gate. | Measure T and downstream probability effects. M3's existing 10 m recommendation does not automatically apply to M1. Any M1 gate requires a separate evidence-backed owner decision. |

Strict support can still yield a determined intersection where one input is
missing: known unburned/low SBS proves false regardless of slope; known slope
below threshold proves false regardless of SBS. Track SBS coverage separately
so this logical deduction does not masquerade as full SBS observation.

## Evaluation panel

Reuse `/workdir/weppcloud-wbt/test_fixtures/staley_m3_resolution/` for Moscow
Mountain, Topanga and Arizona ponderosa at 10 m and 30 m. Use only each project's
main resolved outlet/boundary. Extents differ; do not subtract native rasters
as though cell aligned. Use same-grid method comparisons first. Supply labeled
synthetic SBS patterns to isolate algorithm effects; inventory whether a real
SBS map actually overlaps an existing fixture before claiming real-burn results.
dNBR fixtures are not SBS and must not be thresholded as a substitute.

## User-supplied pysheds reference check

Checked 2026-09-09 UTC:
[sgrid.py](https://raw.githubusercontent.com/mdbartos/pysheds/master/pysheds/sgrid.py)
`cell_slopes()` obtains downstream elevation differences and distances and calls
`_cell_slopes_numba`. The
[helper](https://raw.githubusercontent.com/mdbartos/pysheds/master/pysheds/_sgrid.py)
divides those arrays, using zero for zero distance. The fetched file contains
no identified Horn surface-gradient routine. This reference supports a routed
slope distinction, not a Horn or Staley calibration-parity claim. No code was
copied into this repository. Because master is mutable, downloaded file SHA-256:

- sgrid.py: `c50883a307433e98c734298b985abc8a3cd0fe26ec803df9db87463b30b405f4`
- _sgrid.py: `c815cc0e9501bb9773c0f17cdb6636186c83ba0dc10bd65b09a0352305fe13c0`

## Historical predecessor follow-up

The owner supplied historical USGS provenance, verified read-only on
2026-09-09 UTC. The preserved 2022-named script uses ArcGIS planar slope before
M1 thresholding and TauDEM accumulation. The 2023 migration changes the context
of current pysheds comparisons. Full hashes, lines, confidence limits and
scientific implications are promoted to the durable
[historical evidence note](../../../../wepppy/nodb/mods/postfire_debris_flow/docs/historical_slope_evidence.md).
This strengthens Horn selection; it does not establish original 2017 tooling
or authorize legacy zero filling. Treat modern pfdf divergence as a suspected
preprocessing regression to measure, not an oracle to reproduce.
