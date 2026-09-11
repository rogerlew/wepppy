# Staley slope/SBS intersection design


Pending production amendment (2026-09-11): [ADR-0066](../../../../../docs/adrs/ADR-0066-staley-valid-support.md)
and [model selection](model_selection.md) record scalar valid-support estimates,
coverage artifacts and the initial M3 NED13/2022 10 m source requirement.
Existing local tool outputs remain unchanged; scientific composition follows
its own checkpoint after UI/task wiring.

Status: Horn 3×3 and uncertainty-preserving support accepted, 2026-09-09 UTC;
local backend implemented and validated.
User selected owned weppcloud-wbt tooling and explicitly adopted Horn.
[ADR-0058](../../../../../docs/adrs/ADR-0058-staley-horn-slope.md) records the choice.
Owner subsequently accepted preserving uncertainty: unresolved intersection
cells produce bounds and no point T. Execution adopts raw project DEM and strict nine-valid-cell neighborhoods. The model's ≥23° spatial intersection
and existing project watershed scope are already accepted.

## Purpose and ownership

Compute M1 T from the area of the existing watershed simultaneously steep and
moderately/highly burned. Rust performs the raster calculation and reduction;
WEPPpy later supplies canonical artifacts and handles workflow publication.
The existing watershed delineation, routing slope and generic WBT Slope remain
unchanged. No nested catchments, re-snapping, dNBR-derived SBS, or soil/K work.

## Accepted slope algorithm and preprocessing

Selected preprocessing: use raw project elevation on the authoritative
projected meter grid. Compute
planar Horn 3×3 slope before masking to the watershed, allowing neighbors
outside the basin to inform slopes inside it. For a full neighborhood
`a b c / d e f / g h i`, horizontal spacing dx and vertical spacing dy:

    gx = ((c + 2*f + i) - (a + 2*d + g)) / (8*dx)
    gy = ((g + 2*h + i) - (a + 2*b + c)) / (8*dy)
    slope_degrees = atan(hypot(gx, gy)) * 180/pi

Explicitly normalize horizontal/elevation units; do not infer vertical units
from CRS alone. Initial input is north-up square projected-meter
GeoTIFFs with declared meter elevations, matching owned terrain precedents.
Exact accepted CRS/dtypes and validation limits are specified below.

Selected edge policy: missing center or any missing neighbor yields unknown
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
SBS. The Rust intersection must not silently resample inputs. Normalized SBS codes are 0–3 with 255 NoData, confirmed through Disturbed and
SoilBurnSeverityMap; never assume legacy landuse burn codes are equivalent.
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

## Frozen local backend interface (2026-09-09 execution)


Registered tool `StaleySlopeSbs`, toolbox Hydrological Analysis. Required CLI:

    whitebox_tools -r=StaleySlopeSbs --dem=raw.tif --sbs=sbs.tif --mask=bound.tif --elevation_units=m --sbs_classes=0,1,2,3 --output_dir=fresh-result

Both Python bindings expose
`staley_slope_sbs(dem, sbs, mask, output_dir, elevation_units, sbs_classes, callback=None)`.
The comma-separated four distinct integer codes mean unburned, low, moderate,
high in that order. Normalized WEPPpy `sbs_4class.tif` uses 0,1,2,3 and 255
NoData; custom categorical sources require explicit mapping. Palette colors
are presentation only. Prepare a numeric grayscale copy without a color table
for this interface: the legacy owned decoder expands palette indices to RGB,
so paletted inputs are explicitly rejected instead of misreading class codes.
A signed Int16 grayscale GeoTIFF copy is a supported preparation target (GDAL
writes explicit SampleFormat for signed data). Unsigned TIFFs that omit
SampleFormat are rejected because the current owned reader needs that tag. A dNBR raster is not an accepted SBS substitute.

## Numerical and input contract

Raw meter elevations on a north-up square WGS84 UTM pixel-area grid (EPSG
32601–32660 or 32701–32760). All three grids must have identical dimensions,
CRS, scale and tiepoint. No warp, interpolation, conditioning or delineation.
Use full-DEM Horn 3×3 before watershed masking; missing center or any neighbor,
including off-grid neighbors, makes slope unavailable. Evaluate f64 gradient
magnitude >= tan(23 degrees), with no rounding or tolerance in classification.
Slope output covers the full DEM. Finite valid positive mask cells define the
whole watershed, including channels; zero/negative/NoData cells are outside.
Reject empty watersheds, undeclared nonfinite values and unrecognized SBS
classes anywhere in the supplied grid. An explicit parseable GDAL_NODATA tag (finite value only) is required in each
input; absent/malformed/nonfinite declarations are rejected to avoid the legacy reader
implicitly treating valid -32768 as missing. Float32 inputs also require a
NoData value representable as finite Float32; the owned reader otherwise
normalizes nonfinite sentinels/pixels to -32768 and loses observation identity. NoData is tested before class mapping;
a class code colliding with SBS NoData is invalid. Elevation units must be
explicitly `m`, and any embedded contradictory vertical units are rejected.

Initially support single-image, single-band, uncompressed classic GeoTIFF
scalar rasters with explicit SampleFormat (8/16/32-bit integers or 32/64-bit floating point); no BigTIFF,
RGB, palettes, tiles or multiband. Inputs are local immutable trusted files, not uploads.
Preflight bounded TIFF metadata before owned raster decoding: at most 10 million
cells, 512 MiB per file, 256 tags, 16 MiB per metadata tag and 64 MiB aggregate metadata and 256 GeoKeys. These are resource
bounds, not scientific resolution/coverage gates. Reject unsupported layouts
explicitly. No new external runtime dependencies.

## Products and support

A fresh output directory contains `slope.tif` (F64 degrees, NoData -32768),
`intersection.tif` (U8: 0 false, 1 true, 2 unknown, 255 outside basin),
`support.tif` (U8: bit 0 slope valid, bit 1 SBS valid, 255 outside basin), and
`summary.json` (schema_version 1, status complete). Three-state AND: either
known false operand proves false; both true proves true; otherwise unknown.
SBS-only class counts are independent of slope support.

Summary keys: tool, tool_version, schema_version, status, parameters, sources,
grid, counts, areas_m2, T, T_lower, T_upper. Counts include basin, slope_valid,
sbs_valid, jointly_valid, steep, sbs_unburned, sbs_low, sbs_moderate, sbs_high,
intersection_true, intersection_false, intersection_unknown. Areas mirror counts
multiplied by cell area. With N basin, Y true, U unknown: bounds Y/N and (Y+U)/N;
T is Y/N only for U=0 and JSON null otherwise. Sources include canonical paths,
byte lengths and explicitly labeled FNV-1a-64 content fingerprints (diagnostic,
not cryptographic authentication). Reproduction evidence additionally pins
SHA-256 inputs and executable. Parameters record algorithm, edges, threshold,
units, class mapping and raw-source intent. Grid records EPSG, rows, columns,
resolution and upper-left origin. Tool version is Cargo package version;
reproduction evidence identifies the exact rebuilt executable separately.

## Failure and publication

Require an existing output parent and a nonexistent final directory; atomic
create_dir reserves the destination with Unix mode 0700 subject to umask.
Existing files/directories/symlinks are rejected. Validate and compute before
creating it. Write each product inside this exclusively owned directory, then
write summary.json last as the completion marker. Consumers must require a
parseable summary with status complete and all three products. Failed or
interrupted writes leave a visibly incomplete reserved directory and return an
error; retry with a fresh directory. Never overwrite prior results or sources.
Local parent directories and inputs must not be concurrently modified by other
principals; this is not a hostile shared-directory publication API. No durability
claim across power loss, public upload parsing, or NoDb publication is made.

## Compatibility and verification

Additive tool and bindings; generic Slope/FVSlope and generated project artifacts
remain unchanged. Analytical tests, current CLI/binding products, filesystem
failures and the existing six main-watershed terrain fixtures verify this scope.
Controlled synthetic SBS must be labeled; sensitivity is not predictive accuracy.
NoData behavior intentionally differs from Esri missing-neighbor reweighting.

## Acceptance and remaining integration

The backend passed 157 Rust tests, 60 analytical CLI/binding checks, 24 security
checks and the six main-watershed terrain panel. Exact evidence and limitations:
[validation](../../../../../docs/work-packages/20260908_staley_slope_sbs/artifacts/validation.md),
[terrain report](../../../../../docs/work-packages/20260908_staley_slope_sbs/artifacts/terrain_report.md).
The tool is built locally, not installed into live containers. Stage 3 remains
partial: prepared-input publication, K, dNBR composition and production predictor
orchestration require successor contracts and workflow validation.
