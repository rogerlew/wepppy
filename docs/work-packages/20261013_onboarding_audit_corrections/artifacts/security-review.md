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

## Final implementation review

Disposition: **PASS**, 2026-10-13. Zero unresolved security findings. Reviewed
the working-tree implementation against committed checkpoint
`b4be200b40b07d4986e422667bca30d279072c6f`, excluding the generated usersum index.

The validator changes only the unrecognized readable-palette return from failure
to success and adds an explanatory comment. Both native summaries still execute;
projection, class-count and integer guards are unchanged. No upload authorization,
containment, error translation, classifier or export implementation is changed.
Schema discovery matches the accepted contract, retaining the existing key.
AgFields changes only its requested executable default; template help accurately
distinguishes new projects from saved choices. ORCID deferral is documentation
only. Mariana's contact guidance explicitly states a request does not grant
access, preserving membership and acknowledgment distinctions. Official FAQ
labeling does not change any access boundary.

Inspected the native GeoTIFF regression: unknown, mixed high/unknown and mixed
unburned/unknown palettes pass admission; actual four-class outputs retain
unknown sentinel and original NoData; explicit remapping changes only the
assigned pixel even when source NoData's color is assigned high. Existing
native-failure and upload checks ran in the retained focused result:
`/tmp/onboarding-sbs-green.log` reports **103 passed, 1 skipped**. Schema discovery
assertions retain integer and 256-class limits; `/tmp/onboarding-schema.log`
reports **79 passed**. These logs were read, not independently rerun by this
reviewer. This approval covers implementation security/conformance; it does not
claim a production deployment or full live upload workflow was exercised.
