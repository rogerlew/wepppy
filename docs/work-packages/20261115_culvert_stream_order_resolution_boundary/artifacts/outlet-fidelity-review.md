# Independent review: fixed-outlet fidelity and representative counts

Reviewer: Codex correctness reviewer, independent of the implementer.
Date: 2026-11-16 (UTC).
Scope: `scripts/outlet_fidelity.py`, `scripts/representative_cardinality.py`,
owned WBT source, and completed output readback. Running scripts were not edited.

## Verdict

The corrected distance calculation and fixed-outlet comparison have a sound
basis for the current Santee inputs. Independent pointer tracing verifies the
completed native pass-four distances. The resumed representative matrix retains all six cases: five successes and
one explicit coarse4 failure. Neither successful distance calculations nor
these representative cardinalities establish a default, a safe resnap, or
basin preservation across all culverts.

## Findings

### F1 — Medium, resolved reporting defect; coarse4 tool failure remains open

The original cardinality script stopped when WBT raised. Complete original log
readback identifies the failed case as **coarse4 / cells100 / pass1**, after
successful native passes zero/one and coarse2/pass2. The exact error is:

    WhiteboxAppError: Invalid TOPAZ ID 0 for link 1515

An initial reviewer inference from incomplete live output incorrectly attributed
this to the second/native pass-one case. That inference is withdrawn. The full
log and final per-case artifacts govern this review.

The implementer added a narrow `WhiteboxAppError` boundary around TOPAZ, retains
an explicit failed-case row, and resumed the independent remaining cases. All
six planned cases are now represented; coarse4 fails again, while the other
five succeed. This resolves lost failure-row/denominator reporting. The coarse4
failure itself remains unresolved and is not an off-stream or zero-count result.
Retain its inputs and partial outputs for separate diagnosis; do not resnap or
invoke a fallback to conceal the failure.

### F2 — Medium, resolved for current inputs: null distance needs a reason

`outlet_fidelity.py:sample` maps out-of-grid, masked, and nonfinite samples to
null. A null distance therefore does not alone prove that the outlet's D8 path
cannot reach a surviving stream. Retain per-reference DEM validity and bounds,
and distinguish unreachable/terminal paths where that conclusion is reported.
An independent native pass-four trace confirms that payload point 2939 reaches
a terminal cell without a surviving stream; its null is supported. Final independent readback in `outlet-reference-validity-review.json` confirms
all 78 references are in valid DEM cells on every grid, so none of the current
null distances is caused by an out-of-bounds or invalid DEM sample. This
dispositions the ambiguity for these inputs; generic reuse still needs explicit
reason codes. All 4,992 expected distance rows and 468 expected area rows are
present, and every nonnull distance is finite and nonnegative.

### F3 — Low: distances and accumulation have cell-scale precision limits

Distances begin at the containing cell center, excluding the point's within-cell
offset. They measure downstream distance along the grid's D8 path, not a proposed
safe outlet relocation. D8 accumulation is stored as float32 in the owned tool;
large native counts may round by a pixel. The inspected native1040 accumulation
area is 21,692,732 m² while direct watershed membership gives 21,692,731 m².
This one-pixel discrepancy is consistent with float32 quantization and is not
evidence of material basin drift. Report area tolerances and avoid false exact
agreement requirements.

## Nodata correction: confirmed tool defect, bounded measurement repair

The source native DEM uses nodata=0. Owned
`whitebox-tools-app/src/tools/hydro_analysis/downslope_distance_to_stream.rs`
seeds stream distances with zero, then tests `stream_dist != nodata` before
propagating distance. Nodata=0 therefore collides with the valid zero-distance
seed and prevents valid upstream distance propagation. This explains the
previous misleading output; it is a measurement-tool defect, not an observation
about terrain connectivity.

The disposable negative-nodata DEM preserves the original transform, valid-data
mask, and every valid elevation with explicit equality assertions. These checks
make the workaround appropriate for this study without changing source inputs
or hiding terrain conditioning. The D8 distance tool and `D8Pointer` use the
same neighbor order and strictly positive steepest-slope tie rule in the owned
source. An independent pointer trace below further checks the executed result.
Retain the tool identity and invalidated original output's disposition; source
inspection alone does not identify the deployed binary revision.

## Independent completed-output checks

Evidence is retained in `outlet-fidelity-review-checks.json`.

- For native1 / cells100 / pass4, all 32 surviving payload points have exactly
  zero corrected stream distance. For the seven removed payload points, a
  direct walk over the retained D8 pointer reproduces every WBT result.
- Six removed points reach a surviving channel after about 214–521 m of D8
  travel. Point 2939 terminates without reaching one. These are payload-point
  results; retained WEPP outlets remain a separate reference class.
- For native1 / area8697 / pass0, parsed `netw.tsv` contains 1,489 unique channel
  records, matching the subcatchment-raster channel count. There is one outlet,
  all referenced upstream IDs exist, and all 1,489 channels connect to that
  outlet. The reported hillslope count is 3,718 and the independently delineated
  basin area is about 21.693 km².

## Scientific interpretation and remaining checks

The fidelity script explicitly distinguishes `payload_snapped` and
`retained_wepp_outlet`; the latter transforms retained WGS84 actual locations
into the current UTM CRS. Raw observed `Orig_Lon`/`Orig_Lat` positions are absent
from this script and must not be implied by its labels. Current hard-coded UTM
32617 is appropriate for Santee; retain CRS assertions if reusing the harness.

Representative cardinality uses the retained native1040 GeoJSON coordinate
unchanged and calls WBT Watershed on each grid's own pointer. WBT locates the
provided point directly; the script contains no snap step. Its counts therefore
refer to the basin draining to that fixed position on each grid, which can
change substantially after coarsening/conditioning. Always show basin area and
connectivity beside counts: fewer hillslopes in a shrunken or displaced basin
cannot establish successful network simplification.

The fixed source position yields only about 261 m² of accumulation on the
retained coarse source-vintage baseline, despite approximately 21.693 km² on
the native source. This supports the need to compare fixed coordinates before
resnapping, and to retain each baseline's original resolved outlet separately.
It does not establish that the baseline's own established watershed was small
or incorrect.

The cardinality script indexes the chosen coordinate without a bounds check;
current Santee outputs should explicitly prove it is inside every selected grid.
Before acceptance, retain full expected case/reference denominators, grid/mask
identity, unique topology IDs and one-outlet connectivity, final failure rows,
and precise reference-coordinate provenance. The prior coarsening/conditioning
and pixel-occupancy qualifications continue to apply.

## Completed representative-case audit

`representative-cardinality-review-checks.json` independently parses all six
final records and each successful network/raster. Every successful case has
one outlet, all channels connected to it, exact agreement between network TOPAZ
IDs and channel raster IDs, matching hillslope counts, a fixed outlet inside
its own basin, and matching direct basin area.

| Case | Channels | Hillslopes | Basin area (m²) | Result |
| --- | ---: | ---: | ---: | --- |
| Native1 / area8697 / pass0 | 1489 | 3718 | 21692731 | Verified |
| Native1 / area8697 / pass1 | 357 | 892 | 21692731 | Verified |
| Coarse2 / cells100 / pass2 | 1544 | 3834 | 21682536 | Verified |
| Coarse4 / cells100 / pass1 | — | — | — | TOPAZ failure; neither final network nor subcatchment raster exists |
| Coarse8 / cells100 / pass1 | 394 | 971 | 21862464 | Verified |
| Coarse10 / cells100 / pass1 | 254 | 617 | 21629800 | Verified |

These are fixed-1040 representative results, not all-culvert validation.
