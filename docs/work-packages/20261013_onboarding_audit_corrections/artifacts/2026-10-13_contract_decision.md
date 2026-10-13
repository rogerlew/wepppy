# Contract decision checkpoint

Starting implementation revision: 21fbaa7e5e7664af5b3fa3db4be51d1af7167d45. Existing uncommitted User Guide/FAQ/audit changes belong to this conversation and are retained outside this checkpoint.

Operator authorization, 2026-10-13: “we should make wepp_261010 the default for agfields”; unknown SBS colors “should just leave the unidentified colors unassigned to a burn class.” Explicit authority supports these bounded changes, not model retuning or automatic class guesses.

Applicable authority: SBS raster contract and upload-endpoint contract amended here; NoDb persistence/concurrency, RQ response, CSRF and shared controller contracts unchanged. ADR-0089 governs requested executable default; ADR-0090 records admission policy and classification preservation. Discrepancy: intended change to admission, not a documentation-only correction. Implementation conformance pending.

Valid-state matrix: absent palette uses existing numeric classes; recognized palette unchanged; mixed recognized/unknown retains known labels and unknown entries; all-unknown readable palette now admitted with unknown entries; explicit source/configured NoData unchanged. Omitted mapping (None) uses existing default recognition; preserve existing empty-mapping semantics (an explicit empty mapping leaves colors unassigned). Unreadable/corrupt files, invalid projection, noninteger values, excess classes and native failures remain errors. An unreadable palette is not an unknown color.

Compatibility: additive accepted input state only; no schema, thresholds, formulas, endpoint fields or error envelope changes. Unknown output uses existing sentinel, never an automatic unburned assignment. Shared run/batch users of sanity checking inherit admission; HUC/direct validation already uses the classifier. Existing paths and limits are preserved.

Regression evidence: actual GDAL GeoTIFF with unknown/mixed palette through native summary, sanity check, class labels, four-class export and explicit mapping; assert output pixels and original NoData. Existing malformed/native-error and upload tests remain. Security impact low; independent reviewer must verify retained structural rejection and failure boundaries. No new runtime privilege or filesystem boundary.

Reviews: independent correctness and security reviews PASS in correctness-review.md and security-review.md. Resolved findings: distinguish omitted from explicitly empty mapping; align schema discovery metadata and Disturbed troubleshooting. No unresolved findings.

Schema discovery must publish color_table_mode as optional_unknown_colors_unassigned instead of optional_but_if_present_must_map_known_severity, retaining the existing key and matching the accepted admission semantics. Update associated expectations and user troubleshooting; this is descriptive metadata, not a new upload mode.
