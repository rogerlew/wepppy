# Calibrate culvert network simplification without losing outlets

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md` and extends
the boundary investigation with the operator-authorized resolution study.

## Purpose

Measure how DEM resolution, stream extraction area, and pruning affect network
size and intersections with all original Santee culvert points. Preserve source
coordinates: snapping must not hide lost intersections. No production mapping,
source project, or existing replay inputs are changed by this study.

## Progress

- [x] Operator approved 1, 2, 4, 8, 10 m plus retained 9.32577 m reference;
  100-cell and fixed 8,697 m² extraction; passes zero through five.
- [x] Build and validate initial isolated terrain measurement harness; native 1 m pass masks reproduce retained stream pixel counts.
- [x] Execute initial 72-case resolution/extraction/pruning matrix (including native retained baseline).
- [x] Complete corrected-grid rerun of coarse cases; retain initial results as diagnostic history.
- [x] Measure fixed original outlet and watershed relationships, including
  same-drainage-path displacement, contributing-area changes and fallback risk.
- [x] Delineate hillslopes for representative cases; validate predictions against
  actual cardinality and outlet connectivity.
- [x] Review results; operator chose nominal resolution bins and per-run fallback instead of further intermediate grids in this package.

## Surprises & Discoveries

Santee four-pass diagnostic yielded 783 hillslopes and 313 channels, compared
with baseline 726 and 298; three passes yielded 3,344 and 1,339. This supports
investigation, not a universal fourth-pass default.

## Decision Log

- Operator/Codex, 2026-11-16: investigate resampling and outlet preservation.
  Reason: a count-only target can remove channels serving small culverts.
- Codex, 2026-11-16: coarsen directly from source with area averaging. Anchor
  each grid at the original northwest origin; pad east/south to whole cells.
  Exact common extent and exact requested square cell sizes cannot both be
  retained for source dimensions not divisible by every factor. Record bounds
  and masks rather than silently changing cell size. Keep original watershed
  geometries and points as the comparison domain.
- Codex, 2026-11-16: use WBT depression filling after coarsening and record the
  elevation change separately. Averaging a conditioned DEM can create sinks;
  this is an explicit conditioning treatment, not proof of producer parity.
  Native 1 m uses the provided conditioned DEM unchanged.

## Plan of Work

Use `/wc1/culvert-resolution-replay/calibration` for large disposable outputs.
Read the full original source ZIP, not the one-point filtered payload. Keep all
39 source culvert points and polygons. Copy the retained baseline DEM and
stream raster read-only from wepp1 and treat it as a separate source-vintage
reference, not another resampling of the 1 m source.

First generate DEMs, D8 pointers and cell-count accumulation using GDAL/WBT.
Use threshold 100 and threshold 8697 / cellsize² without integer rounding.
For each extracted stream network, apply the existing two-cell-length short
stream pruning, calculate Strahler orders, and measure passes 0–5 from the
order masks. Verify equivalence with WBT pruning on retained Santee evidence.
Report stream pixels, physical length, headwaters, segment cardinality, and each
original point's intersection and nearest-channel distance. Nearest distance
alone is not evidence of same-drainage-path connectivity.

Then compare original reference outlets (where retained runs exist) separately
from culvert points; they are different references. Delineate representative
watersheds with preserved outlet coordinates. Record explicit failures when an
outlet is absent, never silently snap it or invoke the unpruned fallback.
Measure contributing-area fidelity and same-path distance before recommending
a pass selector. Validate any selector on additional held-out watersheds.

## Validation and Acceptance

Parse generated rasters and prove CRS, grid, valid data, conditioning delta,
order-mask semantics and per-point denominators. Preserve all failure rows.
A matrix of stream counts alone cannot close this study. Runtime, disk use,
source hashes and tool identity must accompany results. Existing 1 m supplied
streams and three/four-pass counts provide control cases. No policy changes or
new defaults follow automatically from this experiment.

## Outcomes & Retrospective

Study complete. Retained initial/corrected matrices, outlet distances and areas,
and six representative delineations (five successes and one explicit 4m TOPAZ
failure) were independently reviewed. See `artifacts/outlet-fidelity-findings.md`
and its review. The operator chose per-run candidate selection, subsequently
implemented and validated under `per_run_selection_execplan.md`. Broader site
calibration and investigation of the 4m failure remain separate follow-ups; the
coarse nominal defaults are provisional, not scientifically calibrated here.

## Initial execution findings — 2026-11-16

`calibration_matrix.py` produced 72 case records in the initial root, summarized
in `artifacts/calibration-initial-matrix.csv`. Native 1 m supplied snapped points
retain 39/39 intersections through pass three, 32/39 at four, and 26/39 at five.
The seven lost at four are 2917, 2913, 2915, 2909, 2907, 2939, and 2901.
The farthest nearest surviving stream center is about 229 m away.

These are producer-snapped payload points, not raw surveyed positions. Raw
`Orig_Lon`/`Orig_Lat` observations and 39 retained resolved WEPP outlets were
collected separately. `calibration_references.py` measures these as distinct
reference classes. Intersection occupancy becomes less stringent at coarse
resolutions; fixed-distance bands and same-flowpath checks remain necessary.

Independent review identified numerical ceil inflation of coarse grids. A
1e-6-cell near-integer tolerance now avoids extra rows/columns from metadata
noise. Corrected cases run in `/wc1/culvert-resolution-replay/calibration-grid-corrected`
(tool session 12533, log `/tmp/culvert-calibration-grid-corrected.log`). Initial
cases remain intact. Legitimate partial boundary cells remain a physical-area
approximation and must be recorded. Filling raises elevations locally near some
culvert points by several meters; coarsening and conditioning are therefore
combined treatments, not resolution alone. Do not recommend defaults from
these initial count/intersection tables.

Remaining: corrected-grid readback, full reference-class comparisons, same-path
and contributing-area fidelity, channel/hillslope cardinality across selected
cases, and final review. The four-pass cardinality benefit at 1040 does not
establish batch-wide outlet preservation.

### Corrected matrix completion

All 48 coarse-grid rerun cases completed; combined with 12 native 1 m and 12 retained-baseline cases, `artifacts/calibration-corrected-matrix.csv` contains 72 records. Native pass-four reference check confirms only 32/39 retained WEPP outlets remain on stream cells. This establishes that four passes is not universally outlet-preserving for this batch. Remaining scientific work: same-path displacement and contributing-area checks, and hillslope cardinality outside the existing 1040 three/four-pass controls. No adaptive rule or default accepted.

## Outlet-fidelity continuation — 2026-11-16

Running `scripts/outlet_fidelity.py` for native WBT D8 downstream distances and
fixed-reference accumulation areas across native, corrected coarse, and retained
baseline grids. Diagnostic source DEMs with nodata zero need an explicit disposable
negative-nodata conversion: WBT DownslopeDistanceToStream otherwise conflates
zero distance and nodata, producing all-zero results. The corrected harness
asserts identical valid masks, transforms, and valid elevations. Invalid first
results are retained separately as `outlet-distances-invalid-zero-nodata.json`
and must not be interpreted as connectivity evidence.

Native four-pass results: retained outlets 2901/2907/2909/2913/2915/2917 require
about 214/289/381/521/397/292 m downstream respectively to reach surviving streams.
2939 has no reachable channel according to this D8 diagnostic (possible boundary
or sink termination requires inspection). All seven lost-point watershed polygons
have zero remaining stream pixels, predicting unpruned per-run fallback rather
than a successful uniform four-pass simplification. This is coverage analysis,
not an actual seven-run fallback replay.

Representative Point_ID 1040 delineation at 1 m with fixed extraction area
8,697 m² and zero order passes produces 3,718 hillslopes and 1,489 channels.
Additional selected terrain cases are running with fixed outlet coordinates;
missing stream intersections are recorded as not delineated, never snapped.

## Outlet study results retained — 2026-11-16

Downstream-distance and fixed-reference accumulation sampling completed across all six grids (native distances focused on passes4/5; coarse/baseline passes0–5). Six representative1040 delineation cases completed: five successful, one explicit 4m TOPAZ failure. See `artifacts/outlet-fidelity-findings.md`, `outlet-area-summary.json`, and `representative-cardinality.json`. No default or automatic snapping changed. Remaining: review disposition, investigate 4m tool failure separately, broader cardinality coverage/held-out watersheds, and design approval before any outlet-preserving selector implementation.

Revision2026-11-16: recorded completed study and its transition to the reviewed per-run implementation.
