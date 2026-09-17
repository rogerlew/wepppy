# Report cache content provenance

## Scope and rationale (implemented)

This contract covers only `HillslopeWatbalReport` (baseline and Roads) and
`AverageAnnualsByLanduseReport` (baseline). It supplements the
[output-scope contract](output-scope-contract.md#hillslope-water-balance-summary-cache)
and [file dependency contract](file-dependency-freshness-contract.md). Preserve
report columns, units, calculations, native aggregation, query-engine joins,
output scope, access rules and normal report URLs. Other report caches are not
changed by this amendment.

Actual source rewrites, translator changes, Roads manifest changes and landuse
joins have returned old report values. Modification time cannot establish input
identity. New caches bind compact report rows and additive source provenance in
one Parquet file, so concurrent publication or a separate JSON write cannot bind
rows from one generation to another generation's dependencies.

## Consumed dependencies

Water-balance identity includes the scope, selected H.wat path and SHA-256,
distinct source WEPP IDs, and their effective Topaz mapping. Resolve that mapping
through the existing Watershed translator, preserving its in-memory summary
precedence over hillslope/channel parquet fallback. For Roads, retain the
optional manifest's target mapping and raw-ID fallback for unknown segments.
Use effective mapping values, not unrelated manifest fields or physical SQLite/
NoDb metadata, as semantic input. Missing or malformed optional Roads manifests
retain existing logging/fallback behavior. Unknown baseline IDs still fail.
An empty source has no translator dependency.

Store the native-discovered WEPP IDs in provenance. On a cache hit with identical
source bytes, use those IDs to reevaluate the mapping without rescanning the
large source. Changed source bytes require a new native ID scan. Provenance
cannot be attached retrospectively to legacy rows.

Landuse identity includes all three logical query inputs: loss hill parquet,
hillslope parquet and landuse parquet. Resolve each with the same catalog
`fs_path` and allowed parent-run rules as the actual query. Bind selected paths
and SHA-256 values; do not add a stricter containment policy or ignore catalog
redirection. Include the effective catalog-driven identifier alias expressions
used by the query, since schema metadata can alter its SQL even when file bytes
are unchanged. Query and verification must use the selected context, and a fresh
selection check before publication must detect changes in catalog selection.

Persist selected paths relative to the run root (including permitted parent-run
relationships), with actual resolved observations retained in attempt diagnostics.
Normal archive/restore relocation must not itself become a content change; the
current resolver still validates every selected physical path.

Use the shared verified ordinary-file digest implementation and its bounded
admission policy. Same-byte touches, links and replacement preserve currentness
when selected paths and effective mapping agree. Changed bytes must invalidate
regardless of size or restored timestamps. Read denial, malformed required
inputs and incoherent reads remain explicit errors, not historical-cache fallbacks.

## Compatibility and valid states

| State | Required outcome |
| --- | --- |
| Complete readable dependencies, valid matching provenance | Reuse compact rows after verifying identity. |
| Complete dependencies, changed identity | Rebuild through the native/query producer. Never return prior rows as current on rebuild failure. |
| Complete dependencies, legacy rows without provenance | Rebuild once when the existing required producer is available; never invent past provenance. |
| Legacy water-balance rows, native API unavailable | Preserve existing legacy availability only when the old source-newer-than-cache rule permits it; log historical/unverified use. A newer source still requires the producer and fails explicitly if unavailable. |
| Required source data removed, compatible cache retained | Preserve historical report access. Log historical/unverified use; never label it current or manufacture missing hashes. For verified caches, an observable change in a still-available dependency disallows historical fallback. |
| Cache absent or invalid, required input absent | Preserve explicit missing-input failure. |
| Present empty required sources | Preserve existing empty report/schema behavior and native/query validation. |
| Optional Roads manifest missing, empty or malformed | Preserve the existing effective mapping fallback; rebuild only if that mapping changes. |
| Required input inaccessible or malformed | Preserve explicit access/parser failure; do not treat it as archival absence. |
| Failed or interrupted build | Prior published cache remains intact; retain visible candidate work and failure evidence. |

Missing translator resources require explicit absence evidence for the selected
controller/parquet prerequisites. Do not catch arbitrary translator RuntimeError,
KeyError, schema errors or denied reads as historical absence. In-memory summary
precedence and valid empty ID sets remain distinct from missing files.
Malformed or unknown embedded provenance is not a legacy cache: fail explicitly
or rebuild from complete inputs, without historical fallback. Once a verified
cache is known to disagree with available dependencies, do not fall through to
an older baseline legacy file.

Expose an additive `cache_status` on each report instance: `current`,
`historical_unverified` or `built`. This is available to report consumers/operators
and documented in the report guide; it is not a new scientific CSV column or a
claim that existing HTML templates display a freshness badge. Log historical use
with its missing prerequisites.

Historical use is a point-in-time report, not a freshness assertion about a
partially archived project. Do not add columns to the scientific CSV or change
existing calculations. Document this compatibility distinction for users and
operators. Source-present legacy reads do not constitute proof of currentness.

## Publication and inspection

Retain the existing cache names under `wepp/reports/cache`, version `1` JSON
sidecars and baseline legacy location. Add versioned dependency metadata inside
the Parquet schema; readers acquire rows and this metadata from one opened file.
The version-only sidecar remains for older readers and must not carry a mutable
source/cache association. Existing older readers can still consume report rows;
rollback does not require a migration or deletion.

Before building, capture selected inputs and effective mapping. Produce into a
unique visible attempt directory under `wepp/reports/cache/<key>.attempts/<id>/`.
After native/query work, verify the selected dependencies again before publishing.
Observable drift raises an explicit error and leaves the accepted cache intact.
Do not use a final hash of changed inputs to label rows computed earlier.
Before/after observations assume existing producer behavior; they do not promise
arbitrary concurrent-writer transaction isolation.

Native water-balance aggregation remains streaming. Adding provenance may rewrite
only the compact native summary, never materialize H.wat in pandas. Preserve
Arrow column types, ordering, pandas schema metadata, existing file access bits
and first-creation umask. Moving native work to an attempt must retain its
existing canonical-destination validation: reject a nonregular destination
(including a symlink/directory), and reject canonical output/input path aliasing
before replacement. Validate again at publication; staging must not bypass these
existing constraints for water-balance publication. Landuse-cache publication
preserves its existing allowed file symlink: select the resolved destination,
verify that selection again before commit and atomically replace the target,
leaving the symlink intact. Do not apply the native water-balance symlink rejection
to landuse caches. Candidate report payloads must not broaden OS read access
relative to an existing restricted cache while being written or retained; apply
the applicable existing access mode from creation, with an appropriately
restricted attempt directory protecting native internal temporary files. With no
existing cache, retain worker-umask creation semantics. These are preservation of
existing access, not a new runtime identity or permission policy. Preserve actual
filesystem regression coverage, including restricted 0600/0640 caches.
Publish the complete rows/provenance file with atomic
replacement. Unique attempts prevent concurrent report requests from sharing
partial files. Atomic Parquet replacement is the commit point. Finish required
sidecar/prepublication status work first. A later diagnostic-status write failure
must be logged without reporting the completed cache publication as failed or
rolling it back over a concurrent writer. Embedded attempt identity permits
inspection when the attempt status remains ready-to-publish after that failure.
The last complete publication may win; each published generation
must contain its own matching provenance, and readers revalidate it normally.

Attempt status, selected input observations, native compact output, annotated
candidate and failure details are ordinary project artifacts. Follow the existing
features-export visible-attempt pattern: retain failed/intermediate work, expose
it through normal browse/download, and include the cache and attempts in canonical
archive/restore. Successful redundant staging copies may be removed only after a
complete canonical output exists. No hidden cache directory, custom endpoint,
background worker, new lock service or archive exclusion is introduced.

## Regression and performance acceptance

Verify actual native and DuckDB results for changed H.wat bytes, translator
mapping, Roads targets, loss values, hillslope area and landuse descriptions.
Include equal-size/restored-mtime edits, metadata-only changes, in-memory mapping
selection, catalog-selected parent assets, empty and historical/legacy states,
read denial, real build-time mutation, concurrent replacement, failed publication
and canonical archive/restore. Preserve baseline/Roads isolation.

Settled source checks must have zero content rereads and retain the shared
sub-millisecond per-file digest budget. Measure translator/query-context work
separately from digest cost. Cold and changed sources may be hashed before and
after building; native source ID scanning occurs on rebuild, not every matching
cache hit. The representative local budgets are recorded below; do not claim an
OS-cache-warm measurement represents cold storage.

For the measured 81,150,978-byte H.wat with 217 source IDs and a 292,036-byte
compact summary, settled additional validation must average at most 10 ms with
persisted-summary translation or 30 ms with parquet translation. Neither may
scan source IDs or rehash settled source bytes. Existing report construction
(excluding first-import warmup) measured 10–15 ms; report total includes that
work. Settled complete report construction must average at most 30 ms with
persisted-summary translation or 50 ms with parquet translation. Source hashing measured 265–294 ms per full check and native ID scan plus
summary about 1.01 seconds. Initial/changed rebuilds may perform two full source
hash checks and must complete within 2 seconds on this representative local
setup, including compact annotation/publication.

For the measured three landuse inputs totaling 59,450 bytes, additional settled
validation must average at most 10 ms without executing the report DuckDB query.
Existing cached construction measured 2.7 ms; combined resolver/alias/digest
validation measured 4.1 ms; complete settled report construction must average
at most 15 ms. Initial/changed construction must complete within
100 ms on this setup (existing query about 35 ms), with at most two hashes per
selected source. These are acceptance budgets, not runtime timeouts or universal
claims about source sizes/storage. Retain separate final runtime measurements,
cache-admission/eviction counts and actual Redis-backed controller acquisition;
the baseline used detached NoDb hydration and an OS-warm filesystem.

## Relocated landuse catalogs (implemented)

A catalog's stored root records its original activation directory. Report-local
selection MUST normalize that root to the requested RunContext base directory
for both query SQL and dependency observations; DuckDB's home directory alone
does not change SQL source selection. Clone catalog/context metadata in memory,
without rewriting the stored catalog or changing shared query-engine behavior.
Preserve schema/alias metadata.

Relative `fs_path` entries retain existing traversal checks. For an absolute
entry, preserve a selection already within the requested run's allowed roots.
Otherwise, validate its old selection and translate an old-catalog-root reference
to the same relative path in the requested root. Translate an inherited old-parent
reference only when both old and requested roots have the corresponding allowed
`_pups` parent relationship. Absence of an individual inherited file is historical
state, not failure to establish that relationship. A standalone restored child
without an allowed parent cannot silently use its former parent's file. Reject
ambiguous or outside-allowed selections through the existing resolver; preserve
current-root precedence when old/new ancestors overlap. Retain actual selected
paths in attempt diagnostics and portable relative identities in cache metadata.

This refines the portable-path obligation after actual copy/restore probes found
that a saved absolute catalog root continued selecting the old directory.
Maintained catalog activation always records its current base as root; supported
parent inheritance is encoded in `fs_path`, not by redirecting the catalog root.
Complete and partial relocations, absolute local and parent entries, existing
current-root references, forbidden paths and query/observation agreement require
real regression coverage. The initial report publication checkpoint remains the
ancestor for its other behavior; this refinement precedes normalization code.
