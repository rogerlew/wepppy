# C08/C09 implementation QA and performance

Independent secondary QA of the two report implementations and private
`_cache_freshness.py` after checkpoint `7d78e9810`. No production or test edits.
Disposition: **scoped QA and local performance PASS.** The relocation and
deterministic concurrency findings below are resolved. Runtime browse/download and
production-equivalent acceptance remain separate package work.

## Actual implementation performance

Retained script: `benchmark_report_implementation.py`. Successful measured run:
`reports_implementation_performance_final.json` and `.log`. Compact accepted
reports, native/query work and status files are retained in
`reports_implementation_outputs/report-implementation-qa-kr_98xyw/`.

The benchmark copies the real 81,150,978-byte H.wat, controller, catalog and three
landuse sources to a disposable `/tmp` run. Named originals are read-only under
an audit guard; all ten checked named generations remain unchanged. It invokes
actual report constructors, shared hashes, native aggregation and DuckDB query.
Only Watershed singleton acquisition is replaced by actual detached disk
hydration, with process-local Redis disabled, matching the conservative baseline.
An isolated hydrated object also exercises the actual Parquet translator fallback.

The final run keeps the copied catalog's saved root unchanged; production report
context normalization selects the disposable run consistently for hashing and
SQL. Revision 2's explicit disposable catalog-root workaround is retained as
earlier performance evidence only. The original failed attempt and its successful C08 measurements
remain in `reports_implementation_performance.json` and `.log`. Its hash counter
rejected a selected path outside the clone before the C09 query ran. Both query
SQL and observation actually select through the catalog root: the early QA
message suggesting a hash/query mismatch was corrected after inspecting
`query_engine.core.build_query_plan`.

| Actual operation | Mean | Hash/producer work |
| --- | ---: | --- |
| C08 legacy-to-verified build | 1,574.49 ms | Two full hashes, one ID scan, one native summary |
| C08 settled hit, 20 calls | 17.82 ms | One check/hit, zero content bytes, no native call |
| C08 settled hit after readmission, 20 calls | 16.36 ms | One check/hit, zero content bytes, no native call |
| C08 isolated Parquet-fallback hit, 20 calls | 32.52 ms | Zero content bytes, no ID scan/summary |
| C08 matching helper-cold hit | 346.15 ms | One full hash, no native call |
| C08 matching admission/readmission | 291.41 / 316.71 ms | One full hash each, no native call |
| C09 actual new build | 51.48 ms | Two hashes per input, one DuckDB query |
| C09 settled hit, 20 calls | 11.26 ms | Three checks/hit, zero content bytes, no query |
| C09 matching helper-cold hit | 8.48 ms | One hash per input, no query |
| C08 after 512-path digest eviction | 298.07 ms | One full hash, no ID scan/summary |
| C09 after 512-path digest eviction | 9.70 ms | One hash per input, no query |

C08 build reads exactly 162,301,956 digest bytes (two source lengths); C09 reads
118,900 (twice its 59,450-byte dependency set). Compared with warmed baseline
means of 10.32 ms for C08 and 2.73 ms for C09, the added persisted-summary and
landuse checks remain below 10 ms; C08 Parquet fallback remains below its 30 ms
additional budget. Both actual build times meet the ratified 2-second/100-ms
local budgets.

All measurement operations recorded zero physical `read_bytes`; these remain
OS-cache-warm results, including helper-cold operations. Instrumentation/audit
overhead is included. Source module hashes were unchanged across the run.
Both shared digest/observation caches reached their 512-entry bound before the
eviction checks. The final selected-entry-only normalization and missing-catalog
history refinements landed after this measured module snapshot; reviewed changes
add no source scan, hash pass or producer invocation to the measured hit/build
paths. This timing is not claimed as an exact-revision benchmark of those final
small branches.

C08's final 296,710-byte annotated cache and 292,036-byte native attempt preserve
0600; the new C09 9,858-byte cache and 7,450-byte query attempt use 0644 under the
service umask. Both result dataframes exactly equal the retained native/query
baseline. Adding provenance changes no report rows, order or scientific columns.

## Findings and coverage disposition

**RQA-01 — Medium, resolved: relocation with a saved catalog root.** A literal
copy of the representative run's catalog still selects the original named
sources. The correctness reviewer independently reproduced failure when the
old root disappears. Same-location archive restoration does not exercise this
case. Following the reviewed root-normalization checkpoint `32c7bed70`, the report
now normalizes the selected context in memory for both query and observation.
Regressions cover relative/absolute selected paths, complete and partial history,
allowed parent relocation, current-root selections, standalone parent rejection,
and selected symlink escapes, without rewriting the catalog. The final actual
benchmark succeeds without the fixture workaround. Normalization is restricted
to the three consumed entries: the actual constructor probe
`reports_unrelated_catalog_qa_probe.py/.json/.log` confirms an unusable unrelated
entry leaves a relocated current report and its rows unchanged. A durable test
also preserves an unrelated parent entry when restoring standalone.

**RQA-02 — Low, resolved test strengthening: concurrent generation coherence.**
The existing two-thread test compares identical results and permissions but does
not force both publications to overlap or identify both attempts. New coverage
uses a two-party barrier at `ready_to_publish`, verifies all three unique complete
attempts (original plus two concurrent builds), and matches the final embedded ID
and dependency observation to its attempt. A separate test replaces the canonical
path after its descriptor is opened: returned rows and proof remain from the
old opened generation while a new path reader sees the new rows. This directly
exercises the accepted publication/read contract.

Reviewed `reports_implementation_revision3.log` (35 passing) and the broader
`reports_affected_revision6.log` (83 passing). Revision 5's collection failure is
retained: the old landuse test installed empty optional-dependency modules during
collection, contaminating the new actual NoDb import. The test now uses installed
dependencies; the affected suite passes in its normal collection order. Meaningful
coverage includes all six actual source/mapping changes, native and DuckDB
build-time mutation with prior-byte retention, in-memory translator precedence,
unknown baseline IDs, metadata churn, partial historical states, actual normal-user
permission failures, narrow native-unavailable legacy compatibility, symlink
destination compatibility, malformed provenance, precommit failure retaining
work, postcommit status failure, and canonical archive/restore byte retention.
Existing H.wat tests retain numeric aggregation and empty-source coverage.

The old isolated landuse test now explicitly owns dataframe formatting; it does
not pretend to exercise provenance or filesystem selection. New real DuckDB
fixtures own those behaviors. The actual service-level benchmark complements
small regressions with 217 source IDs and 10,199 compact H.wat rows. It does not
prove normal Redis/singleton timing, browser behavior or cold/NFS storage cost.

## Maintainability and residual debt

The private helper is appropriately limited to these two consumers. It centralizes
descriptor-bound rows/proof reading, identity comparison and visible atomic
publication without changing every report's cache manager. Native aggregation
and DuckDB query/scientific postprocessing stay intact. The explicit commit flag
and narrow status-write catch preserve the producer/publication error while
preventing a late diagnostic failure from reporting a successful replacement as
failed. User documentation accurately distinguishes historical availability and
the object status from an HTML freshness badge.

The added state handling is justified by the explicit current, historical,
legacy and failed-build contracts. Avoid extending this private mixed dependency
dictionary protocol to additional report families without their own dependency
inventory. The translator's exact RuntimeError-text check is a deliberate narrow
compatibility boundary; if the translator later gains a typed missing-resource
error, replace that string dependency then. Neither point warrants a speculative
framework refactor in this wave.

One useful nonblocking test refinement is to assert the known changed numeric
or mapping result in each parameterized freshness case in addition to unequal
rows. Existing calculation tests and the exact representative output comparison
already provide independent correctness anchors.
