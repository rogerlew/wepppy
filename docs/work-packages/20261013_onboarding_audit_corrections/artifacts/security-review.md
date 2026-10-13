# Independent security contract review

Reviewer: `/root/selected_security`. Date: 2026-10-13.

Disposition: **PASS for preimplementation contract checkpoint**. No blocking
security findings. This is a static contract review, not final implementation
or deployment acceptance.

Reviewed the contract decision checkpoint, amended SBS raster and upload
contracts, ADR-0089/0090, `sbs_map.py` classifier/sanity/export boundaries,
run and batch upload callers, native-failure regression coverage, and the
AgFields config literal.

## Boundary and compatibility assessment

- Admission expansion is explicitly authorized and limited to readable palettes
  lacking recognized colors. Missing files, invalid projection, excessive
  classes, noninteger values, malformed/native failures remain failures.
- Retain the native palette-summary operation even if its recognition boolean
  no longer blocks admission. Removing the call would silently lose its failure
  boundary. Recognition failure must not be confused with a read failure.
- Preserve authorization, upload scope/size/type restrictions, filename
  containment, cleanup and canonical endpoint error envelopes. No changes to
  those controls are necessary to implement this contract.
- Existing dictionary classification can represent all-unknown palettes without
  numeric fallback: empty class lists still form a non-None palette mapping.
  Unknown values retain sentinel semantics; original and configured source
  NoData remain masked. Do not relabel unknown colors as unburned.
- AgFields changes only the requested new-project executable default. Saved
  selections and the historical parent fallback remain intact. ADR-0089 does
  not promise numerical parity with the prior executable.

## Implementation acceptance checks

The proposed native GeoTIFF regression plan is appropriate: verify unknown and
mixed palettes, unchanged known colors, manual mapping, actual four-class output
pixels, source NoData and propagation of native errors. Preserve numeric/no-palette
coverage and existing run/batch upload rejection tests. Config readback is
appropriate for the AgFields literal-only change.

The reread checkpoint and upload contract now explicitly require
`schema_defaults_routes.py` to publish the existing `color_table_mode` key with
`optional_unknown_colors_unassigned`; the root implementer also confirmed the
Disturbed ENDUSER troubleshooting correction is included. The checkpoint now
correctly distinguishes omitted mapping (`None`, default recognition) from an
explicit empty mapping (unassigned colors). These resolve the review's contract
clarifications; final implementation must conform to them.

Final implementation conformance and test results remain to be reviewed after
the checkpoint. No production files or runtime state were modified by this review.
