# C08/C09 content provenance correctness checkpoint

Independent correctness/UX reviewer: `freshness_correctness`, 2026-09-17 UTC.
Reviewed the proposed report-cache contract, output-scope amendment and decision
artifact against the actual two producers/readers, translator, query context and
retained native/DuckDB baseline. No production/test edits or new named-run work.
**Scoped checkpoint PASS, including the measured performance budgets.** No
remaining preimplementation correctness blocker; implementation and final
runtime/observability acceptance remain required.

## Findings resolved during checkpoint review

**RP-C01 — Medium, resolved: selected-path identity must survive restoration.**
Absolute persisted paths would turn normal relocation into a false dependency
change. With a partially archived verified cache, one missing input and unchanged
remaining relocated inputs could then lose historical availability. The revised
contract uses portable paths relative to the run and permitted parent relation,
while retaining actual resolved paths in diagnostics. Current query resolution
still enforces physical path authority. Stored relative identity is not authority
to pass unchecked traversal paths to the query engine. Test partial archive
relocation as well as the all-sources-missing historical case.

**RP-C02 — Medium, resolved: historical fallback requires explicit state rules.**
The actual translator raises RuntimeError when summary/parquet prerequisites are
missing; it can also fail for other reasons. A generic exception fallback would
hide malformed inputs or broken IDs. The revision requires physical prerequisite
absence evidence, preserves in-memory precedence, and keeps unknown baseline IDs,
denied reads and observed parser failures explicit. Unknown/malformed provenance
does not become legacy metadata, and a verified mismatch cannot fall through to
an older baseline cache. These are necessary compatibility boundaries, not a
request to catch more exceptions.

**RP-C03 — Low, resolved: publication requires one defined commit point.**
The revised contract defines atomic Parquet replacement as commit. Prepare
compatibility sidecar/status work before it; after it, a diagnostic failure cannot
claim the prior cache remains unchanged or roll back another request's complete
publication. Embedded attempt identity ties inspection to the committed file.
Retain injected failures immediately before and after that point with two
concurrent candidates. Rows and embedded metadata must be read through the same
opened file; separate `read_schema(path)` and `read_table(path)` calls are not a
coherent generation read under replacement.

## Accepted scope and compatibility

The baseline is sufficiently concrete: actual native/DuckDB report constructors
demonstrate seven stale result cases and three cache-only compatibility states.
The amendment changes freshness for exactly those two keys, retaining formulas,
units, report columns, baseline/Roads partitioning, native aggregation and query
joins. No additional report cache, scientific parameter or dependency is included.

For water balance, source bytes plus the effective WEPP-to-Topaz mapping cover
the inputs actually passed to the native producer. Retaining the native ID set
avoids rescanning large source rows on each cache hit. Mapping still follows
`WatershedOperationsMixin.translator_factory`: both in-memory summary sets have
priority; otherwise both hillslope/channel parquet ID sets participate. The
Roads optional manifest changes identity only when its effective mapping changes.
Malformed/missing optional manifests retain logging/raw-ID behavior. Empty H.wat
has no translator requirement; unknown baseline IDs still fail.

For landuse, the three selected query inputs are all required. Selection must
match `ReportQueryContext` and `query_engine.core._resolve_dataset_path`, including
catalog `fs_path` and allowed parent assets. The revision also includes effective
catalog-driven identifier SQL aliases: `_apply_identifier_aliases` consumes schema
metadata independently of file bytes. Comparing only three path/hash pairs would
omit that query input. Compare the relevant selected context after work, without
invalidating merely because unrelated catalog entries changed.

Legacy means rows with no new provenance, whether at the modern version-1 cache
location or the supported baseline legacy location. Rebuild once with complete
inputs and an available producer; never assign current hashes to old rows.
The explicitly narrow native-unavailable water-balance exception retains the
existing source-newer rule and records historical/unverified status. Verified
cache hits need no native producer solely to rediscover their stored ID set.
Partial archival absence permits history only while available verified
dependencies still agree. Rebuild failures must not return prior rows as current.

One compact Parquet with additive metadata is the smallest coherent publication
unit here. It avoids a new cross-file association or locking protocol. Keep the
native streaming producer and rewrite only compact rows to add metadata, retaining
Arrow/pandas schema and filesystem behavior. The security precision preserves
native canonical destination type, input alias, mode and umask checks even though
native work moves to a unique attempt directory. This rejection applies to C08:
security's real C09 probe proves that its existing file symlink survives both
read and rebuild. The revised contract preserves C09 by atomically replacing its
selected target and rechecking that selection, leaving the link intact. The
restricted-candidate rule prevents staging from briefly exposing private cache
rows. Restrict new helper behavior to these consumers; the shared cache manager's
other reports remain outside scope. Cross-filesystem target replacement remains
an explicit unproven acceptance risk, not authorization for external staging.

## UX, artifacts and validation

The additive `report.cache_status` makes the decision inspectable as `current`,
`historical_unverified` or `built`. The contract explicitly does not present this
as an HTML freshness badge or alter scientific CSV columns. User/operator docs
must describe historical cache availability and how to inspect the verdict;
logging alone must not be described as visible report labeling. Preserve normal
URLs and the ability to obtain retained historical reports.

Visible attempts under the existing cache directory retain observations, native
compact output, annotated candidate and failure/status evidence. This matches
the existing features-export pattern and artifact-observability standard. The
contract requires real browse/download and canonical archive/restore acceptance;
filesystem existence or a directory-name assertion alone cannot establish it.
Preimplementation approval accepts this required design, not unexecuted evidence.

Required implementation coverage includes the retained seven numerical/mapping
cases; same-byte metadata changes; in-memory mapping precedence; redirected and
parent query assets plus alias metadata; empty sources; legacy/native-unavailable
and partial-history states; malformed provenance; access/parser errors; mutation
during actual native/query work; concurrent descriptor/publication generations;
unchanged prior cache on precommit failure; visible retained candidates and
byte-preserving restoration. Preserve report rows under rollback readers.

## Accepted performance budget and limits

Reviewed `reports_performance_baseline_revision3.json`, QA's method/disposition,
and the updated canonical/decision budgets. The representative source is actual
81,150,978-byte H.wat with 217 IDs and a 292,036-byte compact summary. Actual
native ID scan plus summary costs about 1.08 seconds in revision 3; full hashes
cost 267–285 ms each. Composed settled observation costs 4.10 ms with detached
NoDb hydration; the actual isolated parquet translator fallback costs 14.88 ms
and yields the same mapping. The warm C08 constructor itself averages 10.32 ms.

The proposed additional settled C08 budgets of 10 ms for persisted summaries
and 30 ms for parquet fallback have measured support. A representative initial/
changed build budget of 2 seconds includes at most two full source hashes,
native scan/summary, compact annotation and publication. Matching settled hits
must neither rescan source IDs nor hash source content.

The three real C09 inputs total 59,450 bytes. Composed resolver/alias/digest
observation costs 4.08 ms, existing cached construction 2.73 ms and actual query
33.02 ms. The 10 ms added settled-validation and 100 ms initial/changed build
budgets are appropriate local acceptance targets, with at most two hashes per
source and no aggregation query on matching hits. These are regression budgets,
not new request timeouts or universal per-request latency claims.

This closes the preimplementation budget gate. The revision's observation
composition is not an implemented cache-hit benchmark: rerun actual report
constructors after implementation, recording compact publication, hash counts,
admission and eviction. The baseline deliberately used detached disk hydration
with Redis disabled in its process and an OS-warm filesystem. Normal Redis-backed
controller acquisition, physical cold storage, Roads-specific cost, browser
requests, concurrent publication and archive restoration remain acceptance
boundaries. No new cache, watcher or service is justified by these measurements.
