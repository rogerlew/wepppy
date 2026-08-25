# SBS Display Transport Contract

**Owner**: WEPPcloud SBS display and validate-time render paths  
**Status**: Proposed by SBS-A11Y-02; implementation conformance pending  
**Security impact**: low; no request, authorization, persistence, or queue surface

## Purpose and Scope

Soil burn severity (SBS) display rasters transport categorical meaning to the
run-page map and GL Dashboard. Stored RGB is an encoding to decode, not the
authoritative display palette. This contract governs validate-time color-relief
generation, browser decoding, legends, and the GL Dashboard SBS tooltip. It does
not change ingestion recognition, class thresholds, class codes, coverage,
NoDb/RQ state, routes, payloads, exported `sbs_4class.tif`, or existing run
artifacts.

## Class and Display Contract

The severity classes remain `130` Unchanged/Unburned, `131` Low, `132`
Moderate, and `133` High. Alpha-zero pixels are masked/NoData and remain
transparent. Unassigned is a separate display state: it is neither a severity
class nor masked/NoData and renders as the opaque sentinel `#800098`.

Each client decodes every opaque SBS pixel by exact RGB match. Known historical
endpoint colors from the three supported palette generations decode to their
class, then render from the active standard or shifted display palette. An
opaque RGB outside that decode domain renders Unassigned. There is no nearest-
color, tolerance, or non-shifted passthrough path.

The run-page client and GL Dashboard may each hold their own decode and palette
tables because they use different module/build systems. Each client has exactly
one authoritative definition within its own source boundary, and a cross-client
parity test prevents drift. Python legend data uses one server-side definition.

Both clients show a labeled Unassigned legend entry and count. The GL Dashboard
tooltip reports the decoded class code and severity label, or `Unassigned`, not
raw RGBA.

## Producer Contract

The color-table classify branch writes an entry for every value in the union of
source color-table indices and observed, source-valid raster values. Source
NoData maps to transparent `0 0 0 0`; recognized severity values map to their
class transport RGB; every other source-valid value maps to opaque Unassigned
`128 0 152 255`. The breaks branch and BAER writer remain total over their
observed classes.

Both existing `gdaldem color-relief` bake sites use `-exact_color_entry` and
retain an `nv` entry. No source-valid value may become transparent merely
because it was absent from a sparse source palette.

## Historical Compatibility

Known endpoint colors from all three historical generations decode to their
severity class without rewriting the stored artifact.

Two lossy historical cases remain distinct:

- In the current color-table branch, a missing assignment was historically
  interpolated to an off-domain RGB. Rendering that opaque RGB as Unassigned
  reflects the missing assignment.
- In the pre-2018 breaks writer, between-break values were classified but their
  display RGB was interpolated. Exact RGB cannot reconstruct the original class;
  rendering those off-domain pixels as Unassigned is an approved conservative
  compatibility loss, not recovery of their original state.

Values historically clamped by `gdaldem` to a legitimate endpoint color are
indistinguishable from genuinely classified pixels and continue to decode as
that severity. Re-validation is the only complete repair for interpolated or
clamped legacy artifacts. Existing artifacts are not migrated automatically.

## Verification

Generated-output tests invoke real GDAL for the three producer paths: Disturbed
color-table classification (union totality plus exact lookup), Disturbed breaks
classification (observed-value totality plus exact lookup), and the BAER
class-map writer (observed-value totality plus exact lookup). Each covers NoData
and source-valid opacity. The color-table path also covers a value beyond the
source table count. Removing `-exact_color_entry` must make the adversarial test
fail.

Client tests cover the three historical endpoint generations, both clients,
both display modes, alpha-zero masking, unknown opaque pixels, the Unassigned
count lifecycle, legends, tooltip semantics, stored-byte immutability, and
cross-client/Python parity. A deterministic 4096 by 4096 RGBA benchmark covers
both clients and both display modes. After warm-up, the median of five runs for
each new decode path must be no more than 1.25 times the current shifted-mode
decoder baseline measured in the same test process; memory growth must remain
bounded to the source and one destination canvas.

## Decision Provenance

The normative behavior and historical compatibility policy were approved by
the operator in the 2026-08-24/25 SBS-A11Y-02 work-package conversation. The
work package, ADR-0045, GDAL probe, and sentinel analysis retain the detailed
research history; this document is the durable repository contract.
