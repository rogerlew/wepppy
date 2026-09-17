# D-Tale implementation correctness review

Independent reviewer: `freshness_correctness`, 2026-09-17 UTC. Compared the
working implementation with checkpoint ancestor `fbac92404`; reviewed service,
stub, native-reader tests, canonical amendment and retained benchmark. No
production/test edits. **Scoped PASS after the corrections verified below.**
Original findings and failed observations remain retained; runtime acceptance is
separate from this implementation disposition.

## Findings

**DT-I01 — Medium, resolved: overlay replacement left stale identifier metadata.**
The initial `_register_geojson_asset` implementation in
`wepppy/webservices/dtale/dtale.py` appended a
new `(label, key, featureidkey)` choice without replacing the existing key's
choice and updates defaults only for `make_default` or missing defaults. The
actual Channels registration can replace `channel_id` with `reach_id` in the
GeoJSON record while its default still selects nonexistent `channel_id` and both
choice tuples remain. `_build_geojson_upload_with_defaults` uses that stale
default for the feature-ID dropdown. This defeats coherent overlay refresh even
though the bytes themselves now refresh correctly. Update matching-key choice
metadata and defaults that reference the replaced shared overlay, preserving
unrelated choices/default selections. Test a changed identifier and references
from more than one dataset.

**DT-I02 — Low, resolved: valid remaining overlay lost default through ordering.**
`_ensure_geojson_assets` processes channels before AgFields. If an AgFields
boundary was the default, channels become available, and that boundary is then
removed, channels are registered while the old default still exists. Boundary
cleanup subsequently removes the default, leaving a valid channel choice but no
default. Retain a validated surviving default after the complete cleanup pass,
including early controller-discovery returns. Do not revive removed overlays or
change the preferred subcatchment rule. The checkpoint explicitly permits a
remaining valid overlay to become default.

**DT-I03 — Low, resolved: eager initialization failure retained partial global state.**
`load_into_dtale` calls `_initialize_dtale_dataset` outside its cleanup boundary.
A fault injected after actual upstream `startup` publication returns HTTP500
while D-Tale global state still holds the rows and no `DATASETS` tag is present.
The lazy acquisition branch cleans equivalent rejected initialization. Add a
narrowly scoped cleanup/rethrow boundary around eager state publication, keeping
the original failure and unrelated datasets. This is fault-injected cleanup
evidence, not a claim that ordinary CSV startup fails or returns mixed data.

All three results are retained in `dtale_implementation_correctness_probe.py`,
`.log` and `.json`. The probe ran in an isolated process with actual installed
D-Tale, actual GeoJSON parsing/registration and actual eager startup. Only NoDb
controller acquisition and the final startup failure were injected. Disposable
temporary files were removed; no named run or running service state was changed.

## Correction verification

Re-ran the same substantive probe after the fixes, retaining separate
`dtale_implementation_correctness_probe_after.log` and `.json` without replacing
the original evidence. All three observed failures are corrected: the refreshed
overlay has one current choice and a matching `reach_id` default; removing the
old boundary selects the surviving Channels default with its location candidates;
and eager startup failure leaves neither global frame nor wrapper metadata.

Reviewed the implementation correction: shared choice lists deduplicate only
the matching overlay key, and only defaults referencing that key get its new
identifier metadata. Unrelated selections remain intact. Removal chooses a
remaining registered choice and carries its stored location candidates. The
eager initialization catch protects only the third-party publication call,
logs context, removes the target's partial state and rethrows the original
exception. This is an explicit cleanup boundary, not error suppression.

No remaining major correctness finding in this bounded diff.
`dtale_review_regressions.log` records **11 passed**, including eager rejection,
overlay identifier refresh across two datasets, surviving default/location
candidates, and actual filter relaunch from one selected row to two, followed by
HTTP422 on removal of its filter field. The existing affected run records
13 passed and 4 preexisting browse-environment skips; those skips are not
service-enabled acceptance. The retained D-Tale stubtest passes. The separate
security after-probe records two successful eager/lazy cleanup cases.

## Correct behavior reviewed

Byte identity uses the owned shared helper and preserves its access/read failure
rules. Loader reuse requires both logical and resolved target agreement, closing
the same-byte symlink-retarget error without changing dataset IDs. Lazy schema,
count and page reads check the accepted source before/after native acquisition;
`finally` checks also classify drift when DuckDB raises first. Cached counts are
assigned only after the post-read check succeeds, and cached counts/samples are
checked before return. Stable-generation native exceptions remain native errors.

Lazy grid failures use the reviewed upstream HTTP200 error envelope without row
data; loader acquisition failures use structured HTTP409 plus description.
Actual parser tests verify CSV byte refresh, touch reuse, Parquet schema drift,
same-byte symlink retarget, real DuckDB failure after a source edit, stable native
errors, and lazy partial-state cleanup. Optional missing/malformed/absent path
tests verify removal from all four maintained map registries. Authentication,
logical path policy, file/row limits, filter partitioning, lazy bounded reads,
unsupported export and upstream non-lazy delegation remain structurally intact.

`dtale_freshness_tests_revision2.log` records **8 passed**. The retained initial
failure is a test URL-prefix mismatch rather than a production exception; using
the Flask route after normal proxy prefix stripping is correct. No failed log
was replaced. The review regressions above add filter refresh and shared-overlay
coverage. Empty-source, initial parser-error and read-denial cases remain useful
direct coverage beyond the eight initial tests.

## Performance and acceptance limits

Reviewed `benchmark_dtale_large_parquet.py` and the initial implementation JSON:
real read-only 81,150,978-byte Parquet, 3,646,034 rows, 32 columns, service UID1000/
GID993. The ordinary page sequence is one cached-count check plus two page
checks. Cold page: 0.859 seconds and exactly three full hashes (243,452,934 bytes).
After actual 512-path observation/digest eviction: 0.886 seconds and the same
three hashes. Settled pages average 55 ms, or 57 ms after eviction, with zero
hash bytes; settled helper checks average 0.116 ms. These fit the approved native
query plus corresponding full-hash cost budget. The source generation stayed
unchanged; cold means helper-cache cold, with no OS page-cache flush claim.

These are actual isolated accessors, not HTTP/browser launch timings. QA's prior
Chromium response-interception probe establishes error-envelope presentation;
it does not substitute for a real changed backend reaching the browser after
service restart. Supported browse/filter/map flows, representative GeoJSON cost,
permission/mount parity and archive restoration remain package acceptance gates.
The before/after checks remain bounded observations, not arbitrary-writer or
per-browser snapshot isolation.
