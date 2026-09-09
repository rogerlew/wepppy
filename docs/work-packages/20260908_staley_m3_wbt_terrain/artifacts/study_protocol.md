# Resolution study protocol — proposed before results

This protocol was recorded before terrain/M3 outcomes. The user subsequently
adopted the M1 relief contract; the study has now run without changing its
criteria. These engineering criteria do not claim published Staley limits.

Use all three supplied pairs and matched nested channel outlets spanning
headwaters and larger catchments. Record full upstream masks, edge/NoData
contact, source metadata, requested coordinates, snapped centers, and snapping
distances. Do not clip to intersecting extents. `catchments.csv` is an initial
grid/outlet inventory only; all upstream-completeness assessments are pending.
Stored projected requested coordinates and requested geographic coordinates
are distinct records and need reconciliation before fixed-outlet comparisons.

Run controlled 10 m to 30 m area-average aggregation of the raw source, followed
by the same explicitly recorded owned conditioning/routing settings at both
resolutions. Retain full coverage and document partial aggregation blocks.
Compare native paired products separately; source, extent, alignment and
snapping changes make them workflow comparisons, not pure resolution effects.
Keep all generated rasters under `/tmp/staley-m3-terrain-study/`.

Report area, cell count, H, T, outlet elevation, contributing maximum,
catchment intersection/union overlap, and relative/absolute differences.
Numerical correctness uses exact cell counts and Float64 analytical expected
values with 1e-9 relative/absolute arithmetic tolerances; revise output-storage
tolerance explicitly before implementation if Float32 outputs are chosen.
Reference discrepancies are separate from this tolerance and require explanation.

For diagnostic M3 propagation use all combinations F = 0.25, 0.75 and
S = 0.25, 0.75 (25/75 inches of cumulative thickness). These span contrasting
burn/soil contributions without deriving or validating production soil inputs.
Use all three coefficient durations from Table 4. For each 10 m case choose
rainfall by its inverse probabilities 0.25, 0.50, 0.75; evaluate the same
rainfall at 30 m, rather than permitting saturation to hide differences.
Report absolute probability differences in percentage points and 50%/75%
inverse-threshold differences in mm/hour and percent.

Proposed engineering screen: every eligible paired outlet/scenario must have
absolute probability change <=5 percentage points and relative inverse-threshold
change <=10%. Also report sensitivity at 2/10 percentage points and 5/20%
threshold changes. These are study screens, not model calibration limits or
user-approved availability rules. Show individual failures; do not accept
30 m on an aggregate mean. Any population recommendation must be limited to
the represented catchment sizes, terrain and acquisition workflow. Unassessed
completeness or unsettled predictor semantics prevents an acceptance claim.

Record binary SHA-256, revision/diff, locked build command, CPU/RAM, grid sizes,
wall time and peak RSS from external process measurement. Separate compilation,
I/O, reference JIT warm-up and terrain-command measurements. Three repetitions
per representative grid provide median and range. Publish CSVs and standalone
plots with reproduction commands. Existing baseline test timings are not a
terrain performance benchmark.

## Frozen execution details before terrain outcomes

Controlled preprocessing uses the owned `FillDepressions --fix_flats=true
--flat_increment=0.00001` and `D8Pointer` commands at both resolutions. This
keeps an explicit common conditioning rule; native canonical breach outputs
remain a separate workflow comparison. Average resampling preserves the 10 m
upper-left origin and uses ceil dimensions at 30 m, retaining partial edge
blocks rather than cropping upstream terrain. Edge-contact coverage flags
remain mandatory evidence for accepting an outlet.

Assess each supplied terminal pair plus nested 10 m outlets nearest upstream
area targets 0.02, 0.1 and 1 km2 where the target is below half the terminal
area. Select nested points within the terminal catchment by minimum absolute
area difference (row-major tie break). Match each reference point to the nearest
cell with contributing area >=5000 m2 within 90 m at the other resolution;
report actual distance and area discrepancy. The 90 m search admits at most
three coarse-cell widths; it is a diagnostic pairing rule, not a production
snap default. No match is explicitly unavailable. Native terminal comparisons
retain supplied outlet cells to expose canonical-workflow differences; native
nested and controlled comparisons use fixed 10 m physical coordinates.

These preprocessing and selection settings are engineering study choices,
recorded before results and covered by ADR-0052. They do not modify WEPPpy
parameterization defaults or authorize global M3 availability rules.
