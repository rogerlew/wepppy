# Independent correctness review

Reviewer: independent `correctness_review` agent, 2026-09-09 UTC.
Scope: StaleySlopeSbs Rust implementation, registration, both Python bindings,
WBT local tool contract, canonical WEPPpy slope/SBS contract and ADR-0058.
No implementation files were edited by this reviewer.

## Findings and disposition

1. **High, resolved by explicit input restriction: palette samples were not
   categorical indices.** Initial `preflight` admitted TIFF photometric value 3,
   but the owned reader expands those values through the color table in
   `/workdir/weppcloud-wbt/whitebox-raster/src/geotiff/mod.rs`, `IM_PALETTED`
   decoding. This could reject normalized SBS or corrupt scalar DEM/mask values.
   `staley_slope_sbs.rs`, `preflight`, now rejects palette rasters before decoding.
   Both canonical contracts explicitly require a prepared numeric grayscale
   copy without a color table. Independent CLI evidence confirms rejection with
   no output directory. This closes the bounded backend defect; preparing the
   canonical paletted SBS source remains a later caller responsibility.

2. **Medium, resolved by explicit metadata validation: implicit NoData changed
   observation support.** The generic reader defaults absent/malformed NoData to
   -32768. An independently executed no-NoData flat DEM of valid -32768 values
   produced zero valid slopes; a no-NoData SBS using an explicit -32768 class
   was rejected as a collision. `preflight` now requires a parseable explicit
   GDAL_NODATA tag, and both contracts state the restriction. Absent NoData now
   fails before publication instead of producing a scientifically incorrect
   support result. Unsupported missing SampleFormat metadata likewise fails
   explicitly; signed Int16 SBS with declared 255 NoData is verified.

3. **Low, resolved validation fixture correction:** calling rasterio
   `write_colormap` without selecting `photometric='palette'` created a grayscale
   TIFF on this environment. A rejection test using that file would test the
   wrong layout. The maintained validation harness now explicitly selects the
   palette layout and the rejection case passed on the rebuilt binary.

4. **Medium, resolved: bare relative output failed with the default working
   directory.** `staley_slope_sbs.rs`, `run`, canonicalizes
   `destination.parent()` directly. With WBT's default empty working directory,
   `--output_dir=result` has an empty parent path, whose canonicalization fails
   with ENOENT. This breaks the documented CLI example on a fresh executable.
   Independently running a copied release binary with empty working-directory
   settings and valid relative sources returned code 1 for a bare output name
   and code 0 for `./output`. The path helper now resolves an empty working
   directory against `.`; the Rust regression retains this behavior. Independent
   final-binary CLI verification with isolated empty working-directory settings
   succeeded using bare relative inputs and output and matched the previously
   validated summary exactly.

## Independent generated-output evidence

Reviewed executable: `/workdir/weppcloud-wbt/target/release/whitebox_tools`.
SHA-256 at analytical validation:
`b2d5299599e51a641d50855aaad5566bc26fd43de1670483c450ebb1da2bae10`.
Runtime: `/workdir/wepppy/.venv/bin/python`, NumPy 1.26.0, rasterio 1.3.10.
Invocations used the registered CLI with all six required arguments and fresh
temporary directories; no installed binary or live project was modified.

Ten independent 17×19 grids (3,230 cells; NumPy generator seed 9172026) covered
flat and inclined analytical planes, random relief, center/neighborhood DEM
gaps, SBS gaps, negative/zero/positive masks, and explicit signed class mapping
`-7,14,22,130`. The oracle independently evaluated the canonical weighted
sum-form Horn stencil at complete neighborhoods. Maximum slope error was
6.963318810448982e-13 degrees. Every output cell matched for intersection and
support bits. The checks also verified all of the following:

- Full-domain slope support, strict outer edges, and basin masking after slope.
- Every count against input/output arrays, class-count sum equal to SBS-valid,
  and true + false + unknown equal to the full positive basin count.
- Every area equal to count × cell area, bounds Y/N and (Y+U)/N, and null T
  whenever unresolved intersection support remained.
- Output EPSG, affine transform, scalar dtype and distinct NoData values.
- Canonical source paths, byte lengths and independently computed FNV-1a-64
  fingerprints for all three inputs.

A separate one-cell basin on a 3×3 plane verified below/exact/above threshold
and valid zero: 22.999999°, 23°, 23.000001°, 0° yielded T=0, 1, 1, 0.
Both actual Python bindings executed the reviewed binary with spaces and an
apostrophe in every input/output path. Explicit palette, absent NoData and
absent SampleFormat inputs returned errors without creating output directories.

## Coverage and residual risk

Source review found the Horn derivatives, gradient-magnitude threshold,
three-state AND, whole-basin denominator and SBS-only counts consistent with
the canonical contract's **Numerical and input contract** and **Products and
support** sections. Registration is additive and mirrored bindings agree.
No changes to generic Slope, FVSlope, NoDb, auth, locking or RQ were introduced.

This review does not establish original Staley calibration preprocessing parity,
predictive accuracy, hostile-upload safety, or production integration. Input
files and their parent directories remain trusted and immutable by contract.
The reported raw-source parameter is caller intent, not proof that supplied
elevations have never been conditioned. Exact 23° rotated planes remain subject
to documented floating-point representation; no tolerance is added to the
scientific threshold.

Persistent support-raster, grid/dtype/NoData, area and source-fingerprint
assertions were added to the maintained validation harness. Its binding tests
now explicitly set constructor behavior and restore cwd, avoiding the generic
wrapper's cwd/settings side effect between invocations. These checks passed.

## Backend verdict before final metadata follow-up

**Pass for the bounded local backend: no open medium/high correctness findings.**
Reviewed executable SHA-256 at this checkpoint:
`f173878fe075cb982bc09b0304eefdfcce314366e39c5c1af8c2895fa1e93639`.
The reviewer independently reran the maintained harness and all 57 CLI/binding
checks passed, including preparation restrictions, unknown support, exact
threshold, distinct spatial overlaps, filesystem preservation and output
contracts. Reproduce from WBT using a fresh output directory:

```bash
/workdir/wepppy/.venv/bin/python tools/validate_staley_slope_sbs.py \
  --output /tmp/staley-review-durable-fresh \
  --binary target/release/whitebox_tools
```

Review evidence was generated at
`/tmp/staley-review-durable-final/validation.json`. Independent isolated
relative-path verification also passed. Source review confirmed NoData
whitespace handling follows the owned decoder and planar configuration 2 is
equivalent for the explicitly required single sample. The postdecode NoData
guard was subsequently found insufficient because of normalization inside
`Raster::new`; the final preflight correction is reviewed below.

General package build/test gates remain separate execution evidence. This
correctness sign-off covers the tool, bindings, maintained analytical
validation and the terrain-study follow-up below. The separate
[security review](security_review.md) owns malformed-input and resource-bound
acceptance. Production preparation/orchestration and original calibration
equivalence remain outside this review's acceptance scope.

## Terrain-study follow-up

**Pass: no additional correctness findings.** Independently reviewed WBT
`tools/staley_slope_sbs_study.py` and completed products at
`/tmp/staley-panel-accepted`, generated with the checkpoint binary identified above.
No study implementation edits were made by this reviewer.

Independent array/metadata checks reconciled all 48 terrain-result rows,
36 method-comparison rows, six conditioning contrasts, three native-resolution
basin contrasts and 432 probability scenarios. Every method's slope grid
matched the source DEM's CRS, transform and dimensions. Every watershed had
complete slope support for all four methods, so every pairwise comparison used
the full same-grid watershed and no comparison was changed by unequal missing
coverage. Basin counts, areas, steep counts, intersections, T values and bounds
matched the generated arrays and authoritative Horn summaries.

The synthetic SBS rasters exactly matched the stated projected-coordinate field
`(floor(cell_center_x/210m)+floor(cell_center_y/330m))%4` at both resolutions.
They contain only classes 0–3 and have complete SBS coverage. Existing pointer
rasters are held fixed across raw/conditioned runs; the estimator comparisons
use the same DEM within each terrain state, and conditioning is reported
separately. No dNBR source is used or relabeled SBS.

All 36 listed source hashes matched. Running
`python test_fixtures/staley_m3_resolution/verify.py` additionally verified all
66 archived fixture files across six runs, including routing and boundaries.
GDAL 3.10.1 Horn differed by at most 0.0014912664° within a basin and produced
zero basin threshold disagreements. The nearest owned Horn basin value was
0.0000862172° from 23°, and the study's saved-degree threshold counts matched
the authoritative gradient-threshold summary. This panel therefore does not
exercise the analytical exact-threshold floating-point edge case.

Direct independent logistic evaluation using the existing engine's Table-4
coefficients reproduced all 432 scenarios to floating-point precision: fixed
synthetic F=0.5, S=0.25, accumulation 5/10/20 mm and duration 15/30/60 minutes.
The maximum absolute method probability delta was 0.03028108 (3.0281 percentage
points). These are controlled parameter-sensitivity scenarios, not observed
outcome validation. Both bindings' Topanga 10 m raw summaries match the CLI.

Native 10/30 m pairs have different grids, basin areas and resolved outlet
positions. Independently measured outlet separations were 16.3711 m for Moscow
Mountain, 17.9093 m for Topanga and 6.9713 m for Arizona ponderosa; basin areas
changed by -1.0700%, -0.07813% and -0.09310%, respectively. Native T deltas are
therefore basin-level contrasts that also include extent/delineation and
sampling differences, not isolated resampling effects. No raster subtraction
across those grids was performed.

All 12 timed Horn invocations completed in 0.03356–0.43200 seconds with peak
process RSS 18.61–91.98 MiB. This establishes observed panel performance, not a
limit for the maximum supported input size. The real-terrain panel has no
missing in-basin observations and uses synthetic SBS; missing-data policies
remain covered by analytical fixtures, and real SBS preparation remains
successor work.

## Final delivery sign-off

**Pass: no open medium/high correctness findings for the delivered backend.**
Final executable SHA-256:
`6647d55c2d8d28680addd16adc4d9d406857a7ccb394cd4260a2d61d7d8ffc42`.

The final change rejects nonfinite declared NoData and NoData values that
overflow Float32 before invoking the owned reader. `Raster::new` normalizes
nonfinite sentinels and samples to -32768, so checking after decoding cannot
preserve original observation identity. Requiring explicit finite sentinels
is a documented preparation restriction in both canonical contracts; it does
not change successful supported-input slope/intersection calculations.
This review confirms the preflight checks occur before that normalization.

The reviewer independently reran the maintained analytical harness against
this exact executable: **60/60 CLI/binding checks passed**, with evidence at
`/tmp/staley-correctness-final-delivery/validation.json`. The reviewer also
reran the independent security probe: **24/24 cases passed**, including direct
NaN-NoData and Float32-NoData-overflow rejection with no output directories,
plus supported finite-sentinel, whitespace and single-band planar-2 workflows.
Evidence is at `/tmp/staley-correctness-final-rejections/security_results.json`;
the separate security reviewer closes SEC-03 in [security_review.md](security_review.md).

All five scientific CSVs from `/tmp/staley-panel-delivery` were independently
confirmed byte-identical to the previously reviewed panel and to the package
copies: terrain results, method comparisons, conditioning, native resolution
and probability scenarios. Delivery provenance pins the new executable and
matches [terrain_provenance.json](terrain_provenance.json). Updated timings
describe the rerun separately; prior numerical panel conclusions remain valid.
Current retained analytical evidence is
[analytical_validation.json](analytical_validation.json), and the panel
interpretation is [terrain_report.md](terrain_report.md).

Residual scope is unchanged: trusted local prepared numeric inputs, synthetic
SBS sensitivity, complete in-basin panel support, unequal native grids/outlets,
and no production installation or claim of calibration/predictive equivalence.
