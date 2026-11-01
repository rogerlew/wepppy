# Reproduce the bounded rock audit

Run from the WEPPpy checkout with the retained response archive restored at its original `out/roads-parameterization-program-20261031/` paths. Inputs and native build provenance remain private; the public readers contain no legacy native source. The accepted source declaration and binary reuse receipts must remain unchanged. NumPy is required for the RUSLE arithmetic controls. The native identity reader checks the complete retained 977-member build.

Set `PACKET=docs/work-packages/20261029_roads_parameterization_program/artifacts/rock-cover-audit-r4` and select fresh output directories; readers refuse existing destinations.

    python -B "$PACKET/read_inputs.py" --repo . --out /tmp/rock-input-UNUSED
    python -B "$PACKET/audit_rusle_sources.py" --repo . --out /tmp/rock-proxy-UNUSED
    python -B "$PACKET/audit_native_sources.py" --repo . --out /tmp/rock-native-UNUSED

Expected: 36 histories, 354 soil horizons, 108 initial OFE records and three input CSVs byte-identical to this packet; 73 consumed input files unchanged; five unit and three normalization controls with 27 bound files unchanged; 977 native build members exact. The RUSLE test executes actual AST function bodies with injected raster I/O, not a full controller or raster build.

The source audit JSON includes the executing reader's hash: publication renaming preserves bytes, so that field remains identical. Absolute path and mtime bindings are local provenance and may differ in a restored checkout; expected arithmetic and CSV bytes must not. Native identity output binds source files and line indices, without reproducing their contents.

For the headline table, select horizon1 and mode0 from soil-fragments.csv, join B1-B9 case labels, and order each lane's OFEs 1/2/3. Verify mode1 values match before deduplicating. These are file-level mass percentages, not native capped values or surface cover.

Inputs v1, source-audit v1 and native-reader v1 remain in the private archive with their failed control/path checks. Accepted readers are v2 in each case. Reviewer and parent replays use new destinations. No native execution or application test suite is needed for these read-only analyses; no production code changed.
