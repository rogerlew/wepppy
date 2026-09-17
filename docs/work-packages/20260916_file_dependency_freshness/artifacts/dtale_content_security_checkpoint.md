# D-Tale content generation security checkpoint

Independent review by `freshness_security`, 2026-09-17 UTC. Reviewed the proposed
`dtale_content_contract_decision.md`, final **D-Tale dataset generations** section
of the file-dependency contract, local D-Tale AGENTS, browse auth/filter/NoDir
contracts and maintained loader/lazy/map implementations. No production or test
files were changed; the additional probe uses only disposable isolated state.

## Findings and disposition

**PASS for the revised bounded checkpoint.** Two review precisions are now
explicit in the canonical contract. Implementation, UI presentation and runtime
acceptance remain required; this is not package closeout approval.

- **DT-S01, Medium, implementation OPEN:** failed optional overlay registration
  leaves the old fingerprint, upstream GeoJSON, map choices and defaults active
  after read denial or file removal. An independent real registration probe
  confirms this. The accepted amendment preserves table launch while removing
  affected stale overlay references, including absent path/controller cases.
  Replacing hashing alone must not introduce failure of an otherwise valid table
  because its optional map cannot be read.
- **Error-path precision, resolved in contract:** a schema change after a lazy
  precheck can make DuckDB fail before the success-path postcheck. The final
  contract requires observation after query failure too: detected drift produces
  the endpoint's explicit `changed_source` response, while a stable parser/query error retains its
  existing contract. This avoids silently preserving the demonstrated 500 path
  or relabeling all malformed files as generation changes.

The independent QA baseline already confirms same-size/restored-time CSV stale
rows, a lazy Parquet old-schema/new-path 500 and stale actual GeoJSON properties.
Those C11 findings remain implementation obligations. This review accepts the
proposed remedies without claiming the untouched current code is fixed.

## Evidence and concrete state boundaries

`dtale_live_freshness_probe.py/.json/.log` uses the real internal loader/grid
endpoints and current service: CSV rows 1/2 become 8/9 on disk but remain 1/2
in the grid; Parquet column `a` becomes `z` and the old schema causes a DuckDB
binder error; isolated registration retains the old GeoJSON label. A later mtime
change refreshes each result. Authenticated live requests do not log the token.
These are actual consumer failures, not deductions from a metadata predicate.

Additional reviewer command:

```text
wctl exec dtale python docs/work-packages/20260916_file_dependency_freshness/artifacts/dtale_optional_overlay_security_probe.py
```

The retained log exits 0 under UID 1000 / GID 993. A real GeoJSON registration
succeeds, then chmod read denial plus a changed mtime forces the actual parser
to log `PermissionError` and return `(None, None)`. Deleting the file also returns
`(None, None)`. Both leave `REGISTERED_GEOJSON`, `CUSTOM_GEOJSON`, `MAP_CHOICES`
and `MAP_DEFAULTS` referring to the old overlay. The probe imports the maintained
module in a separate process; it does not alter the live service's global state,
restart services, use external targets or mutate named projects.

Current `_fingerprint` supplies only mtime/size. `load_into_dtale` uses it for
eager/lazy reuse; `_register_geojson_asset` uses it for parsed map reuse.
`LazyParquetDtaleInstance` reads schema once, caches row count/sample, and opens
the pathname again for native count/page queries. `_format_lazy_rows` combines
that count with bounded requested slices. All those observations must refer to
one accepted generation; fixing only normal launch reuse leaves live lazy page
mixing unresolved.

## Authority and noninterference

The content hash is an observation, not access authority. Preserve the browse
bridge's run/group authentication, root-only path rules, traversal/resolved-path
validation, suffix/size limits and internal token boundary. The ordinary digest
helper follows the existing permitted symlink semantics and must run only after
the caller's authorization/path decisions. No broader roots, token logging,
upstream authorization changes or new external read capability are authorized.

NoDir resolution/materialization remains the browse bridge's responsibility.
The hash observes its resolved file. Do not introduce request-side thaw/freeze
cleanup, source repair, archive deletion or implicit fallback to another file.
Dataset IDs retain run/config/path/filter partitioning and remain stable on a
normal relaunch. Same-byte metadata operations should preserve a working session
and settings; a real content change rebuilds the existing ID through the normal
launch path.

The final amendment also requires the same selected resolved source path for
reuse. This correctly prevents equal-content selection changes from leaving a
lazy reader bound to an older source. Current `_resolve_target` uses lexical
`abspath`, so comparing the same alias string alone is insufficient to detect a
symlink retarget. Retain the selected resolved target observation at acquisition
and compare the newly selected target without changing path authority. Cover
both a same-byte symlink retarget and config-subdirectory fallback followed by
creation of a preferred root-level file. Do not use digest equality to authorize
a changed path.

Optional map absence, read failure, malformed JSON and unavailable controller
state retain table availability. Remove only the affected registration and
references, preserving unrelated datasets/assets and identifier aliases.
Failures during new dataset initialization must clear the partial state for
that dataset, never treat the one-row shell or old cached rows as a successful
new load, and never use service-wide cache clearing as routine recovery.

## Generation and error semantics

Observe before/after eager acquisition, lazy schema/sample/count construction,
filter compilation and map parsing. Publish the recorded fingerprint only when
those observations agree. Recheck both successful and failed native operations;
if a file changes during acquisition, returning a parser/filter error alone must
not bypass the generation decision. Stable invalid filters remain 422 and stable
parser errors retain the original reader contract.

Lazy instances bind to the accepted content fingerprint. Validate before/after
filesystem-backed pages/counts and before cached count/sample returns. An absent
or unreadable previously accepted input gives explicit reopen-from-browse
guidance without successful row data. The loader uses HTTP 409 with
`error.code="changed_source"`, `error.message` and matching `description`.
The grid uses the installed upstream HTTP 200 failure envelope:
`success=false`, top-level string `error` and `code="changed_source"`.
QA's upstream source-map inspection established that non-2xx grid responses drop
their body. `dtale_ui_contract_probe.cjs/.json` then confirms with actual Chromium
and installed UI bytes: the intercepted HTTP 409 response has no visible alert;
HTTP 200 with the same failure envelope displays the reopen guidance. The probe
reproduces the proxy prefix mapping; the earlier unmapped diagnostic is retained.
This establishes UI envelope compatibility, not full live mutation acceptance.
The choice preserves visible errors without changing frontend transport or
treating stale rows as a successful page.
A normal relaunch recompiles filters and schema consistently;
an old filter whose field is no longer valid then follows the existing 422
contract, rather than being dropped silently. Initial resolution of a missing
target remains 404, and size/row limit 413, unsupported type 415 and unsupported
lazy export 501 remain unchanged.

Explicit relaunch replaces the shared server dataset under its stable ID, so
other tabs using that ID may also need to reopen. The final contract states this
limit; it does not claim per-browser generation isolation or authorize a new
version-token protocol. The no-silent-refresh rule applies to lazy page reads.

Already loaded eager frames are explicitly point-in-time views until relaunch.
There is no promise to revoke their in-memory bytes because a file changes.
Lazy pages reopen the file and therefore need the separate generation guard.
The shared helper and before/after observations do not establish arbitrary-writer
isolation or a multi-file table-plus-overlay transaction. Preserve bounded native
DuckDB/PyArrow reads, the one-row shell and non-lazy endpoint delegation; never
recover by loading the complete Parquet file into pandas.

## Required acceptance

Use real readers/state for original CSV/Parquet/GeoJSON reproduction, same-byte
touch/link/restore reuse, changed schema/row count, active filters, read-time
mutation, initial and later read denial, cached count/sample access and partial
registration failure. Verify all stale map references disappear while valid
tables and unrelated maps remain usable. Include failures occurring inside a
native query after its initial verification, with stable-error control cases.

Verify the accepted failure message is visible in the installed D-Tale grid and
the loader's 409 survives the browse bridge, with a working normal relaunch path
for both same-schema and changed-schema edits.
Existing service-available tests must not accept 404 as a skip. Retain actual
browser/browse-to-D-Tale and map HTTP acceptance under normal service identity
after the approved development restart; isolated registration alone is not map
UI evidence.

The service defaults to a 512 MB file limit and single in-process worker. Hashing
adds streaming reads on cold/changed loads even when pages remain bounded in
memory. Measure complete launch/page costs on representative files, including
the one-second uncached admission period and repeated checks, not just mature
helper hits. The final budget follows the existing `_format_lazy_rows` sequence:
one guarded cached `rows()` call plus a before/after pair for each requested
`load_data()` range. A normal single-range page therefore permits three hash
checks; an uncached count may need its own pair, totaling four. During admission
or after eviction these checks may each read the full file, so measure actual
bytes and latency rather than equating checks with settled cache hits.

This budget correction is accepted before implementation: it preserves the
standalone count/sample guards and matches the existing accessor sequence.
The earlier two-check whole-response ceiling was too small for those independent
contracts. No reentrant validation mechanism is justified solely to avoid the
extra count observation. Representative large-source/admission/eviction latency
and working-set measurements remain explicit shipping gates; this correction is
not a performance acceptance result. Settled checks must read zero content bytes
and meet the existing sub-millisecond per-file budget. No new cache service, watcher, datastore,
dependency, persistent state migration or worker-topology change is justified.
