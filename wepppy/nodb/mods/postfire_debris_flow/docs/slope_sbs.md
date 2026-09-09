# Staley slope/SBS intersection design

Status: Horn 3×3 and uncertainty-preserving support accepted, 2026-09-09 UTC;
implementation pending.
User selected owned weppcloud-wbt tooling and explicitly adopted Horn.
[ADR-0058](../../../../../docs/adrs/ADR-0058-staley-horn-slope.md) records the choice.
Owner subsequently accepted preserving uncertainty: unresolved intersection
cells produce bounds and no point T. DEM source and neighborhood edge handling
remain recommendations awaiting disposition. The model's ≥23° spatial intersection
and existing project watershed scope are already accepted.

## Purpose and ownership

Compute M1 T from the area of the existing watershed simultaneously steep and
moderately/highly burned. Rust performs the raster calculation and reduction;
WEPPpy later supplies canonical artifacts and handles workflow publication.
The existing watershed delineation, routing slope and generic WBT Slope remain
unchanged. No nested catchments, re-snapping, dNBR-derived SBS, or soil/K work.

## Accepted slope algorithm and proposed preprocessing

Recommended preprocessing: use raw project elevation on the authoritative
projected meter grid. Compute
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

Horn is an accepted engineering choice with confirmed historical workflow
support: the preserved USGS script named for 2022 invokes ArcGIS planar Slope
before the M1 ≥23° intersection. Complete-neighborhood derivatives match Horn.
The [historical evidence](historical_slope_evidence.md) distinguishes that path
from the later pysheds directional-slope helper. Original 2017 calibration
stencil/conditioning equivalence remains unestablished. Existing FVSlope is directional D8 drop/distance;
projected generic WBT Slope is Florinsky 5×5. Neither is implicitly equivalent.

## Accepted intersection and uncertainty policy

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
Validate malformed class maps explicitly. This three-state policy avoids
counting missing observations as low severity or flat terrain.

Report total basin cells/area, SBS-valid area, slope-valid area, jointly valid
area, true/false/unknown intersection counts and provenance. With N full basin
cells, Y true and U unknown, report bounds Y/N and (Y+U)/N as missing-data
bounds, not confidence intervals. If U=0, T=Y/N is determined. If U>0,
processing succeeds with coverage and bounds, but point T is unavailable. Do
not extrapolate a partial point estimate, shrink the denominator, or publish
the lower bound as T. An observed-support ratio, if exposed, is a separately
labeled diagnostic and must not enter the model as T. A downstream single M1
probability that requires unavailable T remains unavailable; propagation of
probability bounds would require a separate result contract. A valid zero T differs from
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
published formulas/GDAL. GDAL is a comparator, not established historical USGS
slope software. Current pfdf directional-slope agreement is not an acceptance
criterion: investigate its divergence as a potential preprocessing regression. A comparison is method sensitivity, not validation
against observed debris-flow outcomes.

See the [work package](../../../../../docs/work-packages/20260908_staley_slope_sbs/package.md)
and its [evidence/decision register](../../../../../docs/work-packages/20260908_staley_slope_sbs/artifacts/slope_method_findings.md).
ADR-0058 records algorithm selection and uncertainty preservation; amend or
supplement it when source and neighborhood edge policies are accepted.
The accepted contract must be updated with the roadmap as work progresses.
