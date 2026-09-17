# D-Tale content generation checkpoint

Starting revision90a8a3dc9, with the independent features implementation wave in
the working tree. Owner authorized this package and fixes for confirmed
consumers. Canonical authority: file-dependency-freshness-contract D-Tale dataset
generations, browse-auth, browse-parquet-filter, NoDir interface/thaw-freeze,
and nearest webservices/dtale/AGENTS lazy bounded-read rules. No auth, persistence,
model numerical or deployment authority change.

## Evidence and decision

QA exercised real authenticated internal/load and dtale/data endpoints on
unique disposable batch files under the normal service identity. Same-size/time
CSV values1/2→8/9 returned old rows. A real lazy Parquet a→z schema change reused
the old schema and produced a DuckDB500. Isolated real GeoJSON registration kept
old labels until mtime changed; map HTTP acceptance remains open. See retained
`dtale_freshness_review.md` and probe artifacts. No named project was mutated.

Replace metadata fingerprints with the already-reviewed ordinary-file digest.
Bind acquired data to before/after content observations. Lazy count/page reads
must match the accepted schema fingerprint before/after, including cached count/
sample returns. Observable drift or unreadability is an explicit changed_source
with reopen-from-browse guidance; normal relaunch keeps IDs/filter partitioning
and rebuilds from current bytes. Reject mixed generations rather than modifying
a live grid schema. No eager full-file fallback. Optional absent GeoJSON stays
optional and a missing previously registered source cannot supply a current
cached overlay. Eager already-open data remains a point-in-time view until
relaunch, consistent with its in-memory reader.

## Compatibility, state and regression plan

No persisted data/schema migration. Empty but reader-valid files remain valid;
malformed files retain parser failures. Missing target at initial resolution
retains404; disappearance during acquisition is409. Lazy paging uses upstream
HTTP200 with success=false, error:string guidance and code=changed_source. Missing
optional map assets do not prevent table launch. Existing limit413, filter422,
unsupported415 and lazy-export501 remain unchanged. NoDir paths remain logically
authorized/materialized through the browse bridge; no new request cleanup.

Test actual CSV/Parquet/GeoJSON values, same-byte metadata operations, schema
changes, read-time mutation, lazy page/count cache checks, deletion/read denial,
filter rebuilding, stable IDs and aliases, and partial-registration cleanup.
Retain actual endpoint/UI acceptance after development restart. Settled digest
checks must read zero content bytes and meet the existing<1ms per-file budget;
measure cold/changed startup and page costs separately with real files. Full
lazy paging remains bounded and no extra service/dependency/cache is introduced.

Independent correctness/security checkpoint reviews and a docs-only ancestor
commit precede implementation. This proposal is not yet implemented or deployed.

Review precision: optional GeoJSON parse/read failures and absent controller/path
state preserve table launch, removing only affected old registrations and map
choice/default references. Query failure also triggers an observation recheck:
detected drift yields changed_source even if DuckDB raised first, while stable malformed
source/query failures preserve their existing error.

Installed upstream source-map review found that grid transport drops non-2xx
bodies, preventing409 guidance from appearing. Use its existing HTTP200 error
envelope for lazy grid failures; retain409 on internal/load with structured
error and matching description for the browse bridge. Reject a new frontend
transport patch as unnecessary scope. Explicit relaunch resets the shared stable
ID, so other tabs may need reopen; no per-browser generation isolation is claimed.

Performance shipping evidence must include representative large Parquet pages
during the first-second admission interval and after observation-cache eviction,
not only settled helper timings. Budget a cold/changed grid response at native query cost plus at most two
verified full-file hash costs per requested row range and one for its cached
count (three checks for a normal single-range page). A first uncached count may
require its own before/after pair. Preserve standalone count/sample guards; do
not add a reentrant validation protocol solely to remove one cold check. Settled
checks must read zero content bytes. Measure actual accessor sequencing, bytes,
latency and working-set pressure explicitly; large-source acceptance remains a
shipping gate rather than an assumption.

Source-path precision: cache reuse requires the same resolved target as well as
content. Otherwise a same-byte symlink retarget would retain a lazy reader on
the old path and miss later changes to the newly selected source. Existing
resolution/containment still decides whether the new path is permitted.

Relaunch preserves the original pqf partition and recompiles its filter against
the new schema. A removed or incompatible filter field remains422; no silent
filter removal or reuse of the prior shell. Optional cleanup removes only the
matching overlay key and allows a remaining valid overlay to become default.
