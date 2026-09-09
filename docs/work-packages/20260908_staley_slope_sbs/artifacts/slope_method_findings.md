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

| ID | Disposition | Evidence and limit |
| --- | --- | --- |
| S01 | Horn 3×3 adopted; generic Slope/FVSlope preserved. | ADR-0058; independent f64 oracle and six-terrain comparison. Original 2017 calibration equivalence unproven. |
| S02 | Raw meter DEM, full DEM before basin masking, strict center/eight-neighbor validity. | ADR-0058 execution disposition; analytical edges and separate conditioning contrasts. Esri gap reweighting characterized separately. |
| S03 | True/false/unknown with full-watershed bounds and no point T for U>0. | Owner accepted policy; known false operand still determines false. Tests cover missing slopes/SBS and valid zero. |
| S04 | Required explicit class map; normalized values 0–3, NoData 255. | Disturbed/SoilBurnSeverityMap source audit. Prepared grayscale with explicit SampleFormat and finite NoData avoids legacy reader reinterpretation; no implicit resampling or dNBR substitution. |
| S05 | Native 10/30 m existing main-watershed contrasts, no resolution gate. | Terrain report retains mask/area/outlet context, synthetic SBS and fixed numerical scenarios; no predictive-accuracy claim. |

See [validation](validation.md), [terrain report](terrain_report.md), and the
independent reviews for completed implementation and remaining production scope.
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
