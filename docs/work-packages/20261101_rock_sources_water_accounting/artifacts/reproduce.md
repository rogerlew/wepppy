# Reproduce the source and scalar observations

Use fresh output directories. Retained raw evidence is under
`out/rock-sources-water-accounting-20261101/`; source URLs, payload identities and
request time are in `source-acquisition.json`. The completed phase has no
production code change, so it does not require repeating the prior hour-long
full repository suite. Validate these readers, source probes and documentation.

## Source acquisition

From `/home/workdir/wepppy`, the original bounded request was:

    python -B docs/work-packages/20261031_rock_representation/artifacts/fetch_surface_evidence.py --out out/rock-sources-water-accounting-20261101/surface-original-retry

This is a new request; historical timeout evidence remains unchanged. The exact
SQL is in the retained request.json and source-acquisition.json. To reproduce
readback without querying changing survey data:

    python -B docs/work-packages/20261101_rock_sources_water_accounting/artifacts/read_surface_records.py --xml out/rock-sources-water-accounting-20261101/surface-original-retry/response.xml --out /tmp/rock-surface-replay-NEW

Expect15rows,9components,8surface records. Inspect the JSON for null values and
10% unallocated composition in2711184. The reader deliberately emits no aggregate
surface cover. Its first failed100%-total assumption is retained in
surface-readback-v1; accepted readback is surface-readback-v2.

BC metadata was retrieved from the official URLs in source-acquisition.json via
Python urllib with a30-second request timeout. Original ZIPs and README payloads
are in `bc-metadata/`; the dictionary ZIP was extracted into `bc-metadata/dictionary/`
after rejecting member paths outside that directory. CanSIS HTML corroboration
is retained separately in `cansis-metadata/`. Do not assume current downloads
match historical bytes; compare hashes before using a prior receipt.

    wctl exec -T weppcloud /opt/venv/bin/python -B /workdir/wepppy/docs/work-packages/20261101_rock_sources_water_accounting/artifacts/read_bc_basis.py --dictionary /workdir/wepppy/out/rock-sources-water-accounting-20261101/bc-metadata/dictionary/Soils_Metadata_and_Templates.gdb --out /workdir/wepppy/out/BC-REPLAY-NEW

The reader uses the existing GDAL driver and actual SiftHorizon serializer.
Expect metadataIDs160,187,189,191 and an observed mass-field token20.0 for the
synthetic20volume% input, versus the independently checked33.75796mass% inventory.
No unavailable local production database is emulated as a real extraction.

## Native scalar observations

Read scalar-declaration.md and both prereviews before invoking. Source-file
hashes must match scalar-source-declaration.json; the runner rejects drift.

    python -B docs/work-packages/20261101_rock_sources_water_accounting/artifacts/run_scalar_probes.py --source /workdir/wepp-forest-release-20261009/src --out /tmp/rock-scalars-NEW

Expect17cases,16normal results and one expected diagnostic SIGFPE. The overall
reader exits0 only if the declared native-control and diagnostic outcomes match.
Each case retains commands, compile/execution results, exact private wrappers,
binary hashes and stdout/stderr. The diagnostic trap is a rejected expression
domain, not a promoted model change. Full-routine or full-model claims require
additional evidence.

The native incident record is
`/workdir/wepp-forest-release-20261009/docs/ablation/20261101_rock_water_scalars/`.
Its matrix records the diagnostic process as FAIL/SIGFPE while the readback
correctly records that this was the expected counterexample.

## Retention and checks

Run scoped `wctl doc-lint` for the package and canonical contract. Independent
reviews bind accepted report/reader/result identities. Archive only after all
writers finish; archive-receipt.json verifies every member and the complete raw
inventory. Publication manifest excludes itself and is created after the archive
receipt to avoid circular hashes. Public artifacts contain no native sources.
