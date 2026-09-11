# dNBR Input and Normalization Contract

Status: backend v1 contract, 2026-09-09; backend implementation and regression conformance verified.
The current increment is a local Python interface, not a browser upload endpoint,
NoDb controller, or RQ job. Future transport follows the SBS upload contract.

## Backend Interface

`normalize_dnbr(source, dem, watershed_mask, output_dir, *, scale_factor,
add_offset=0, source_refs=(), prefire_date=None, postfire_date=None,
assessment_type=None)` validates and creates a new completed directory with
`dnbr.tif` and `manifest.json`. `summarize_dnbr(dnbr, catchment_mask)` returns
full/partial/unavailable status, valid/total target cells, coverage fraction,
mean normalized dNBR and M1 F. Both means are the same dimensionless value.
Paths are local files. Caller supplies authoritative WBT DEM and binary mask;
mask value 1 denotes catchment, 0/NoData denotes outside. CRS, transform and
shape must agree exactly. The DEM must use projected meters and a north-up
square grid. The caller owns WBT/CONUS readiness and active-artifact publication.

## Formats, Limits and Encoding

Accept .tif/.tiff (GTiff), self-contained .img (HFA), and the safe identity-VRT
subset below, exactly one real integer/float numeric band. Reject complex,
RGB/palette imagery, missing CRS, singular/invalid georeferencing and invalid
encoding. Extensions and actual drivers must agree. Source and reference
rasters are bounded to 100 MiB per physical file and 25 million cells each;
these are resource limits, not geographic/scientific eligibility thresholds.
Identity VRT XML is limited to 64 KiB before parsing. Individual decoded raster
blocks must also fit the cell limit and 100 MiB, including padded TIFF tiles.

Scale is required, finite and positive; offset is finite. Normalize as
`raw * scale_factor + add_offset` exactly once, before resampling. Factor
0.001 represents x1000 values; factor 1 represents unscaled dNBR. Nondefault
GDAL scale/offset metadata must match the explicit pair or fail with an
encoding conflict. Default 1/0 metadata is unspecified and does not override
the caller. No histogram/dtype scale detection. Mask declared NoData, masks,
NaN and infinities before scaling. Reject overflow. Preserve negative and zero.
Report values outside theoretical [-2,2] as a diagnostic, never clip or silently
reject them: upstream processing can depart from the ideal NBR bounds.

## Local Reference Boundary

Read self-contained GTiff/HFA from in-memory encoded bytes with driver allowlists;
no external sidecar is part of this backend input. Materialize external masks
or IMG companion data into a self-contained raster before calling. Reject
recognized adjacent mask, auxiliary, overview and HFA companion files instead
of silently discarding their metadata or valid support. Reject
symlink inputs, nonregular paths and output/input aliases. The production
browser-upload containment boundary is specified in [production_m1.md](production_m1.md).

VRT is a restricted identity wrapper, not an executable GDAL program. Parse
XML before GDAL access; reject DTD/entities, derived/raw bands, pixel functions,
remote/absolute/traversing references and unsupported XML elements/attributes.
Permit one SimpleSource, band 1, relative SourceFilename explicitly allowlisted
by `source_refs`, pointing to one self-contained GTiff/HFA. Require full-size
identity SrcRect/DstRect (if present), matching dimensions, dtype, CRS and affine;
read the validated leaf directly. This supports ordinary identity VRT wrappers
without enabling mosaics, arbitrary paths, or nested VRTs. Other VRTs receive
an explicit unsupported-VRT error rather than an implicit conversion.

## Grid, Resampling, Overlap and Coverage

Write one Float32 GeoTIFF with NaN NoData on the exact DEM CRS/affine/shape.
Use compiled GDAL nearest-neighbor sampling of the normalized source. This
preserves actual observations and avoids interpolation across source holes;
it does not create new 10 m information from a 30 m input. Compare bilinear
behavior on shifted/holey fixtures as evidence, not a configurable silent mode.
No extrapolation, gap fill, clipping, or source stretching. Target DEM NoData
is invalid support. Any watershed cell on DEM NoData is an invalid reference.

At least one valid target sample must occur inside the actual watershed mask
before publication. Disjoint, boundary-touch-only and NoData-only overlap fail;
subpixel overlap that disappears at target sampling returns the explicit
`no_valid_target_overlap` error. The interface makes no claim that bounding-box
intersection alone establishes coverage. Retain normalized data outside the
watershed within the project grid, with watershed coverage reported separately.

Compute summaries over observed target-cell area (equal square cell weights),
not full area with implicit zeros. Partial coverage is accepted with no minimum
fraction; expose its fraction and warning. Empty dNBR support is unavailable
for that catchment, not zero hazard; empty catchment masks are invalid inputs.
Keep M1 T/S and M3 independent of dNBR support. M1 F receives normalized mean
without another /1000. Do not treat target-cell support as exact source-polygon
area or proof that missing observations are representative.

## Metadata, Dates, Output Lifecycle and Errors

Record input hashes, source/leaf identity, dtype, grid, NoData, declared encoding
and metadata, normalized range, out-of-range counts, nearest method, target
identity, mask identity and summary. Optional image dates are ISO YYYY-MM-DD;
if both exist require prefire < postfire. Unknown dates remain null; fire/event
filename dates are not image dates. Assessment type is null, initial or extended.
No scientific dates are inferred from upload time.

Reserve a previously absent, visible output directory and write its
incomplete.json before artifact writes. Existing directories (including empty/symlink ones)
are rejected, never replaced. Single-writer output ownership is required.
Failed calls retain incomplete artifacts and the marker for inspection and
archival; existing/source artifacts remain unchanged. Publish the success
manifest last and remove the incomplete marker only after success.
Source identity is checked by hashes; this local API updates no NoDb pointer. The production
controller must atomically select the completed artifact and invalidate M1
only; this backend does not claim to implement that lifecycle.

`DnbrError(ValueError)` carries a stable `code`: invalid_input, resource_limit,
invalid_raster, invalid_grid, invalid_mask, invalid_encoding, encoding_conflict,
unsafe_reference, unsupported_vrt, invalid_dates, output_exists,
no_valid_target_overlap, or source_changed. Filesystem operational errors remain
explicit OSError rather than becoming false input errors. No success manifest
or ready result may be returned for an incomplete artifact.

## Validation and Deferred Browser Work

Exercise real USGS Arizona rasters and synthetic matching/shifted/coarse/fine/
reprojected grids, source masks and sentinels, negative/zero values, equivalent
integer/float encodings, partial support and unavailable catchments. Verify
real output readback, source hashes, safe VRT/IMG paths and failed-output
preservation. Future browser transport must cover shared run access, CSRF,
100 MiB upload enforcement, UI state, NoDb publication/invalidation and error
translation in its own contract-first ancestor checkpoint. No endpoint is
registered by this backend contract.

Production browser staging, distribution-based Auto, retained-file correction and
atomic NoDb/RQ publication are implemented in [production_m1.md](production_m1.md).
They wrap this explicit local API without changing its encoding/grid rules.
