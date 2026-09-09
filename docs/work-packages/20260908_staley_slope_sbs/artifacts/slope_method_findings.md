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

## Recommendations needing disposition

| ID | Recommendation | Decision/evidence needed |
| --- | --- | --- |
| S01 | Dedicated planar Horn 3×3 surface slope on raw project DEM; preserve existing FVSlope and generic Slope. | Confirm scientific references, compare real-data methods and approve the engineering choice if original preprocessing cannot be established. No assumption that a newer/smoother algorithm better reproduces calibration. |
| S02 | Compute on the full available DEM before applying the watershed mask; require a valid center and eight valid neighbors, with no edge interpolation. | Document one-cell halo and residual unknown support; compare strict Horn with published Esri missing-neighbor behavior. Raw versus conditioned surface effects must be separated from algorithm effects. |
| S03 | Unknown SBS or slope remains unknown; report full-area counts, observed-support diagnostics and possible bounds, without a published point T on unresolved support until policy is accepted. | Owner choice: require a fully determined intersection, or permit a labeled partial estimate. No silent zero fill or arbitrary coverage cutoff. Handle logically known false intersections separately from unknown ones. |
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
