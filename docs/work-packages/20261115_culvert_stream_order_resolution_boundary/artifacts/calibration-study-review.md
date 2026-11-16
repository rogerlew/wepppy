# Independent review: first-stage calibration matrix

Reviewer: Codex correctness reviewer, independent of the implementer.
Date: 2026-11-16 (UTC).
Scope: `prompts/active/calibration_study_execplan.md` and
`scripts/calibration_matrix.py`, plus read-only inspection of current outputs.
The running matrix script was not modified.

## Verdict

Suitable for an exploratory matrix with the qualifications below. No production
selector, resolution boundary, or outlet-preservation conclusion is established.
The script's same-path and hillslope-count disclaimers are appropriate. The
medium findings constrain interpretation and require disposition before using
this matrix to select defaults or claim contributing-area fidelity.

## Findings and scientific confounders

### C1 — Medium: near-integer bounds create valid extra edge cells

Lines 35–40 apply `ceil` to the source floating-point bounds. The source pixel
size is 1.0000000000089009 m; this tiny excess gives a 2 m grid of 3883 by 3673,
although the nominal 7764 by 7344 source dimensions divide evenly into 3882 by
3672. The analogous 4 m grid also gains an extra row and column. These are not
entirely masked padding: the inspected 2 m last column/row contain 15/33 valid
cells; at 4 m they contain 8/17. Area averaging can assign an elevation using a
very small source overlap, after which D8 accumulation counts that destination
cell as a whole cell.

Preserve these outputs as exploratory evidence. For a subsequent controlled
comparison, explicitly disposition coordinate-rounding tolerance and partial
edge-cell support; retain the selected bounds, validity masks, and support-area
policy. Do not describe `threshold_cells * resolution²` as exact source-domain
contributing area at partially supported boundaries. The impact on the Santee
interior outlets has not been established by this review.

### C2 — Medium: coarsening plus filling materially changes culvert elevations

Lines 37–49 correctly make the conditioning treatment explicit, but native 1 m
uses the supplied DEM while every coarse case additionally runs depression
filling. These are combined resolution/conditioning treatments, not a clean
resolution-only experiment. The 2 m summary reports a maximum raise of 10.480 m
and 948,631 changed cells. Independent point sampling found maximum raises at
payload culvert cells of 7.094 m (2 m), 5.897 m (4 m), and 3.277 m (8 m).

All 39 payload points remain valid at the inspected 2/4/8 m resolutions; their
loss from a stream mask therefore cannot simply be attributed to a missing DEM
sample. Retain conditioning quantiles and changes at each culvert and along its
flow path. Account for any removed hydro-enforced crossing before attributing a
lost outlet to stream pruning or making physical-fidelity claims.

### C3 — Medium: occupancy and source-point identity limit outlet claims

Lines 19–21 use payload point geometry. The source contains 39 unique points in
EPSG:32617, matching the DEM; all 39 are on valid native DEM cells. However, all
source features identify producer snapping with
`snap_metho=culvert_crossing_corridor`. `Orig_Lon`/`Orig_Lat` preserve distinct
raw WGS84 positions. These are original **payload** points, not necessarily raw
observations or resolved WEPP outlets. The implementer acknowledged this and
plans separate raw/payload/WEPP-outlet measurements.

Furthermore, `on_stream_cell` at lines 75–79 measures raster-cell occupancy:
a 10 m cell can contain a point about 7.1 m from its center, whereas a 1 m cell
permits about 0.71 m. A higher coarse-grid intersection fraction alone does not
prove better positional fidelity. Report fixed metric-distance bands alongside
occupancy, while retaining the existing caveat that nearest center distance
cannot establish same-drainage-path connectivity. Keep all three outlet
references distinct and use contributing-area/path checks for final claims.

### C4 — Low: pass zero includes a resolution-dependent short-stream treatment

Line 62 always removes short streams at twice the cell size before pass zero is
measured. Thus pass zero is zero **Strahler** passes after short-stream pruning,
not the unmodified extraction. The physical short-stream minimum varies from
about 2 m to 20 m across the matrix. This matches the intended workflow, but
report the minimum explicitly; a resolution comparison includes this treatment.

## Correctness checks and coverage

- Native source CRS is EPSG:32617; source and inspected coarse grids are square
  and north-up. The center-coordinate computation is correct for these inputs.
  The script only asserts CRS equality, so grid shape/rotation and point CRS
  should remain explicit assertions/readback if this harness is reused.
- Source nodata is 0, GDAL destination nodata is -9999, and WBT order nodata is
  -32768. Stream masks use both the raster mask and positive order values;
  nodata is not counted as a stream in the inspected path.
- The two extraction modes are genuinely different: 100 cells changes physical
  extraction area with resolution; 8697/resolution² approximately fixes it.
  The code retains fractional thresholds instead of silently rounding them.
- `values > passes` agrees with the production helper's subtractive order-mask
  pruning semantics. Existing retained Santee evidence verifies masks through
  three passes; the implementer reports the reconstructed 1 m control reproduces
  retained stream pixel counts. Retain direct mask/control evidence with the
  final study results, including four/five-pass representative checks.
- Empty surviving networks retain a row for every point with null nearest
  distance, rather than dropping failure cases.
- `stream_pixels` is neither channel cardinality nor comparable physical length
  across resolutions. The script correctly disclaims inferred hillslope counts.
  Physical length, headwaters/segments, fixed-outlet watersheds, same-path
  displacement, contributing area, and held-out validation remain later gates.
- The first-stage JSON does not retain source hashes, tool/binary identity,
  disk use, full grid/mask summaries, or the retained 9.32577 m reference. Add
  the planned manifest/reference readback before interpreting a completed study.
  `elapsed_seconds` is cumulative since resolution start, not per-pass cost.

## Evidence

`calibration-review-grid-snapshot.json` independently retains the available
2/4/8 m CRS, bounds, grid, edge validity counts, and pointwise fill changes.
The matrix completed 10 m after that snapshot; 10 m needs the same readback.
Native point CRS/count/validity was inspected directly from the full original
feature collection and source raster. No source data or runtime script changed.
