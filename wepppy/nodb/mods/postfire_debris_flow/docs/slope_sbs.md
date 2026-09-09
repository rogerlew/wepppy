# Staley slope/SBS intersection design

Status: proposed backend contract, 2026-09-09 UTC; implementation pending.
User selected owned weppcloud-wbt tooling. Algorithm/source and missing-support
policy below are recommendations awaiting evidence and disposition, not
accepted production parameterization. The model's ≥23° spatial intersection
and existing project watershed scope are already accepted.

## Purpose and ownership

Compute M1 T from the area of the existing watershed simultaneously steep and
moderately/highly burned. Rust performs the raster calculation and reduction;
WEPPpy later supplies canonical artifacts and handles workflow publication.
The existing watershed delineation, routing slope and generic WBT Slope remain
unchanged. No nested catchments, re-snapping, dNBR-derived SBS, or soil/K work.

## Proposed slope method

Use raw project elevation on the authoritative projected meter grid. Compute
planar Horn 3×3 slope before masking to the watershed, allowing neighbors
outside the basin to inform slopes inside it. For a full neighborhood
`a b c / d e f / g h i`, horizontal spacing dx and vertical spacing dy:

    gx = ((c + 2*f + i) - (a + 2*d + g)) / (8*dx)
    gy = ((g + 2*h + i) - (a + 2*b + c)) / (8*dy)
    slope_degrees = atan(hypot(gx, gy)) * 180/pi

Explicitly normalize horizontal/elevation units; do not infer vertical units
from CRS alone. Initial proposed input is north-up square projected-meter
GeoTIFFs with declared meter elevations, matching owned terrain precedents.
Exact accepted CRS/dtypes and validation limits belong in the final tool spec.

Recommended edge policy: missing center or any missing neighbor yields unknown
slope, with no interpolation. The watershed mask is applied after neighborhood
calculation; clipping the DEM to the basin first would create artificial gaps.
Threshold the unrounded calculation inclusively at 23 degrees; record precision
and test boundary behavior, including equivalence to gradient >= tan(23°).
Do not classify display-rounded degrees or use 23 percent slope.

This is an engineering recommendation. The manuscript inspected specifies
10 m DEMs and the threshold, but original stencil/conditioning equivalence
has not been established. Existing FVSlope is directional D8 drop/distance;
projected generic WBT Slope is Florinsky 5×5. Neither is implicitly equivalent.

## Intersection and support proposal

Use the full existing routed watershed mask including channels and unburned
terrain. Require exact grid agreement for mask, DEM and prepared categorical
SBS. The Rust intersection must not silently resample inputs. Trace canonical
SBS class semantics through its owner before fixing supported codes; never
assume legacy burn landuse codes equal the normalized SBS raster encoding.
Nearest class alignment, if needed, belongs to an explicit preparation step.

For each in-watershed cell classify the intersection as true, false or unknown.
True means slope >=23° and SBS moderate/high. Either a known slope below 23°
or known unburned/low SBS proves false; otherwise a missing operand leaves
unknown. Unknown class codes remain distinguishable from declared NoData.
Validate malformed class maps explicitly. This three-state proposal avoids
counting missing observations as low severity or flat terrain.

Report total basin cells/area, SBS-valid area, slope-valid area, jointly valid
area, true/false/unknown intersection counts and provenance. With N full basin
cells, Y true and U unknown, report bounds Y/N and (Y+U)/N as missing-data
bounds, not confidence intervals. If U=0, T=Y/N is determined. If U>0, whether
a labeled partial point estimate is allowed requires owner disposition; do not
silently shrink the denominator or publish the lower bound as T. Any observed-
support ratio is a separately labeled diagnostic. A valid zero T differs from
unavailable T. Empty watershed is invalid, not a zero-area model result.

Expose sufficient SBS-only counts for later M3 F, independently of slope
coverage, but do not expand this package into M3 runtime integration.

## Outputs, validation and pending decisions

Finalize registered tool name(s), CLI flags, both binding signatures, output
schema/version, nodata/dtypes, resource limits and failure/publication behavior
before source edits. Expected inspectable products are a slope raster,
intersection/support raster(s), and a summary with counts, units, parameters,
source identities and tool revision. Preserve existing outputs and emit success
only after all required artifacts are complete. No production NoDb/RQ schema
or caller is established here.

Use analytical planes in multiple orientations, threshold cases, flat terrain,
NoData neighborhoods, partial SBS and same-grid real terrain comparisons.
Benchmark Horn, existing FVSlope and Florinsky, separating conditioning from
algorithm effects; compare 10/30 m without imposing an unapproved M1 gate.
Document full-neighborhood parity and edge differences against independent
published formulas/GDAL. A comparison is method sensitivity, not validation
against observed debris-flow outcomes.

See the [work package](../../../../../docs/work-packages/20260908_staley_slope_sbs/package.md)
and its [evidence/decision register](../../../../../docs/work-packages/20260908_staley_slope_sbs/artifacts/slope_method_findings.md).
Create a parameterization ADR when selecting the algorithm and support policy.
The accepted contract must be updated with the roadmap as work progresses.
