# dNBR Upload and Raster Normalization

Status: design scaffold, 2026-09-08. The operator has established SBS-like upload,
different source scales/extents, project-grid normalization, valid watershed
overlap, and resilience to partial coverage. Choices marked proposed remain
subject to the pre-implementation contract checkpoint and parameterization ADR.

## SBS Precedent

- [Upload endpoint contract](../../../../../docs/schemas/upload-endpoint-contract.md):
  run SBS accepts `.tif`, `.tiff`, `.img`, `.vrt`, capped at 100 MiB.
- [SBS map guide](../../baer/README.sbs_map.md): recommended single-band input,
  valid spatial reference, integer class values, at most 256 distinct classes.
- `upload_disturbed_routes.py` uses shared upload-boundary helpers, run access
  checks, canonical errors, and a synchronous validate/install path.
- Disturbed aligns SBS to the project DEM using `raster_stacker` with
  nearest-neighbor sampling because SBS is categorical.

The dNBR control should use the same upload/status/error presentation and file
format family. Inherit the 100 MiB cap unless explicitly revised. Shared upload
helpers handle transport and naming, not scientific raster validation.

## Source Data Types and Encoding

Pending confirmation: accept real integer and floating-point numeric rasters.
This supports both integer-scaled dNBR and unscaled continuous dNBR without
requiring users to quantize their data. SBS's integer-valued and 256-class
restrictions must not be accidentally inherited as dNBR checks. If integer-only
input is selected, preserve explicit scaling support and document that limit.

Propose exactly one numeric band. RGB/RGBA renderings and categorical SBS/BARC
values do not encode continuous dNBR; a color table alone does not establish
numeric semantics. Reject complex-valued data and unreadable/missing CRS or
georeferencing. Accept reprojectable source CRSs and differing resolutions;
do not require source UTM or pre-alignment.

Proposed normalization equation:

```text
normalized_dnbr = stored_value * scale_factor + add_offset
```

| Source encoding | Scale | Offset | Example |
| --- | --- | --- | --- |
| NBR difference multiplied by 1000 | 0.001 | 0 | 650 becomes 0.65 |
| Unscaled NBR difference | 1 | 0 | 0.65 remains 0.65 |
| Other documented numeric encoding | explicit finite positive factor | explicit finite offset | Defined by source provenance |

These are proposed presets, not auto-detection rules. Show the selected encoding
and resulting valid-data range for confirmation. A dtype or histogram cannot
reliably distinguish low-magnitude scaled values from normalized values.
GDAL scale/offset metadata can prepopulate a proposal; define precedence and
apply the transform exactly once. Conflicting metadata requires resolution,
not an undocumented override. Preserve source NoData/masks before scaling.

Keep normalized negative values (possible greening) and valid zero values.
Do not clip to 0-1, interpret zero as missing, or reconstruct dNBR from SBS.
Physical-range validation/tolerance must be set in the parameterization ADR;
do not add silent clipping as a fallback.

## Canonical Project Raster

Propose a single-band Float32 GeoTIFF, normalized NBR-difference values, and
explicit NaN NoData. Proposed path: `postfire_debris_flow/dnbr.tif` in the run.
Artifact paths, manifest keys, and exact mask representation are not yet fixed.

The reference grid is the authoritative WBT project DEM grid. Match its CRS,
affine transform, pixel origin, dimensions, resolution, and extent. Verify
actual metadata after processing; matching resolution alone can leave a
half-cell shift. Use the watershed mask for overlap and coverage, not the
rectangular DEM footprint. Crop larger sources and retain NoData where smaller
sources do not cover the project. Never stretch a source to fill the target.

Propose normalizing to physical dNBR before resampling, with validity handled
separately. Reuse owned raster tooling; do not introduce a new GIS dependency.
The resampling kernel and support-mask rule remain open: continuous dNBR is
not a categorical SBS map, so SBS's nearest-neighbor choice is a precedent to
evaluate rather than automatically copy. Compare candidate kernels on coarse,
fine, shifted, and reprojected grids before choosing. No gap filling or
extrapolation is implied by resampling.

## Overlap and Partial Coverage

Accept an upload if valid source data have positive-area overlap with the
actual watershed. An intersecting bounding box, boundary-only touch, or
intersection consisting entirely of NoData does not meet that requirement.
Processing must also establish valid target-grid support before reporting
ready. Very small overlap can disappear at target resolution; report this
explicitly without inventing synthetic coverage.

Proposed catchment reporting:

- Observed dNBR area and fraction of the full contributing catchment.
- Whether the mean is full-coverage, partial-coverage, or unavailable.
- Valid-data mean and the resulting M1 F, using observed-support area weights.
- Partial-coverage warning in the UI, report, and machine-readable provenance.

For a partial catchment, divide the weighted sum by observed area, not total
catchment area. Dividing by total area would implicitly assign dNBR zero to
missing pixels. This observed mean estimates the paper's full-catchment mean
and can be biased if the available footprint is unrepresentative; identify
that limitation alongside the coverage fraction.

Keep T and S on their independently defined full contributing-catchment domains;
the dNBR footprint must not redefine the watershed or SBS burned-area fraction.
No valid dNBR for a catchment means unavailable M1, not zero risk. Continue for
other assessable catchments. M3 is not affected by dNBR absence and is never
selected implicitly. No numerical minimum coverage fraction is approved.

## Metadata, Dates, and Lifecycle

Preserve original filename, content hash, band/dtype, CRS/grid, declared NoData,
scale/offset source, normalized range, target grid identity, processing version,
resampling method, and coverage diagnostics. Source imagery dates and initial
versus extended assessment type should be recorded when supplied; unknown dates
must remain unknown rather than inferred from upload time. Date-field
requiredness and date-order validation remain pending.

The uploaded source and successfully processed artifact are distinct states.
Stage a replacement and validate it before replacing a usable prior upload.
Failed uploads must not destroy the current source or results. A successful
replacement invalidates dependent M1 outputs; exact NoDb/RQ freshness fields
and atomic publication mechanics belong in the implementation checkpoint.
Do not claim M3 requires rebuilding merely because a dNBR file changes.

VRT/IMG format parity does not authorize arbitrary filesystem/network reads.
Resolve sidecar/reference handling within the authorized run upload boundary;
missing assets must produce a useful error. Validate VRT referenced sources
before opening them and prohibit access outside approved data locations or
unapproved remote URLs. Decide the concrete safe packaging/reference contract
before enabling these formats; the filename allowlist is insufficient.

## Validation Plan

Before runtime work, enumerate absent/ready/partial/stale/failed-replacement
states and define endpoint fields, canonical errors, and upload processing
orchestration. Test with real raster files and generated artifact readback:

1. Integer x1000 and normalized float fixtures produce equivalent F and M1
   results within the chosen Float32 tolerance, if float inputs are adopted.
2. Matching, shifted, finer, coarser, and differing-CRS inputs align exactly to
   the reference grid. Larger/smaller extents preserve appropriate coverage.
3. Reject disjoint, boundary-only, all-NoData, and NoData-only watershed overlap.
4. Accept partial coverage; means use observed area and coverage remains visible.
5. Catchments with zero support remain unavailable while other results succeed.
6. Valid negative/zero values survive scaling, masking, and aggregation.
7. Resampling neither bridges data gaps into valid observations nor contaminates
   values with source sentinels; target support mask and values agree.
8. Invalid replacement leaves prior valid artifacts intact; successful
   replacement invalidates M1 and preserves unrelated project data.
9. Unsupported data/CRS, size failures, and unsafe VRT references fail explicitly
   under production-equivalent upload and worker identities.

Amend shared upload/controller-state contracts in the implementation ancestor
checkpoint; this design does not register a working endpoint or alter SBS.
