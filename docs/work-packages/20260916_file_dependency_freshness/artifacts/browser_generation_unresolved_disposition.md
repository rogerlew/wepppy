# B-F01 and browser-family justified unresolved disposition

Recorded: 2026-09-17 UTC. Independent QA disposition: **justified unresolved**,
with the active B-F01 defect still open. Follow-up owner: the file-dependency
freshness package orchestrator, until a bounded browser UX checkpoint assigns
implementation ownership. Revisit before M6 closeout or the next browser
refresh-contract change, whichever occurs first. This artifact changes neither
normative behavior nor runtime code and does not declare the package complete.

## Authority and exact scope

[Package: Complexity budget](../package.md#complexity-budget) requires every
inventory entry to be recorded as “fixed, verified-safe, nondependency or a
justified unresolved finding.” It also excludes new services, watchers and a
universal freshness framework. This is an explicit inventory disposition using
that allowance, not a claim that missing UX requirements make stale scientific
values safe. The ExecPlan's generic confirmed-failure closeout gate still needs
an explicit package-level reconciliation; this independent artifact alone does
not waive that gate or any changed-code review/runtime requirement.

The evidence and exact source trace are retained in
[browser_generation_scope_qa.md](browser_generation_scope_qa.md) and
[remaining_services_tools_browser_inventory.md](remaining_services_tools_browser_inventory.md).
The canonical [GL specification](../../../ui-docs/gl-dashboard.md), particularly
Data Flow, Layer Lifecycle and State Management, defines interactive lazy
loading and changed-scenario invalidation. It does not define generation
detection after a rerun, automatic refresh while a page remains open, or a
coherent immutable page snapshot. The module README explicitly gives graphs
their own scenario selection, distinct from map scenario selection.

| Entry | Evidence class | Explicit disposition |
| --- | --- | --- |
| B-F01, active GL yearly caches | **Confirmed defect:** actual active module plus real Parquet/DuckDB retains year 2000 value 25 after replacement, then reads new year 2001 value 76; a fresh manager reads new year 2000 value 75. | Justified unresolved pending the browser generation/refresh contract. Do not report fixed, verified-safe, nondependency or coherent snapshot. |
| Related GL graph caches | Concrete cache/force/scenario path traced; no independent complete graph failure probe. | Unresolved candidate, included in the future GL refresh boundary; not promoted to a separately confirmed defect. |
| GL batch geometry promises | Batch/config/kind reuse excludes membership/content; normal within-page membership refresh failure not reproduced. | Unresolved candidate requiring the batch refresh contract and a supported-workflow reproduction. |
| Storm-event climate minimum-year cache | Scientific filter dependency cached by run ID; actual end-to-end event misfilter not reproduced. | Unresolved candidate requiring its own refresh trace and output reproduction. |
| Parquet schema preview | URL promise retained after collapse/reopen. | Unresolved schema-refresh UX candidate, not a demonstrated backend freshness/access bypass. |
| Combined watershed viewer | Variable changes clear results; unit/range changes reuse them. | Unresolved within-page regeneration policy/candidate. |

The excluded legacy Leaflet reproduction B-L01 and the inventory's narrowly
verified managed geometry/SBS availability paths keep their previous
dispositions. Neither is used to dismiss the active GL finding or to certify
all browser caches.

## Why this is unresolved rather than a speculative implementation

The actual producer writes stable native interchange Parquet names, refreshes
the query-engine catalog and publishes job status. The run page consumes
completion and refreshes its report; its GL link opens a **new tab**. The
standalone GL page has no corresponding completion subscription or cross-tab
bridge. Query responses expose records/schema/count, not a validated dataset
generation. There is no established missing callback whose restoration would
resolve every affected cache without choosing new behavior.

Automatically replacing data, invalidating an open analysis, introducing a
generation API, or pinning a scientific snapshot would each choose a different
user workflow and validation boundary. The package authorizes investigation and
bounded fixes; the present canonical UX contract does not choose among those
behaviors. Inventing a polling service or treating a job timestamp/TTL as byte
identity would exceed the retained evidence and complexity allowance. Clearing
only the proven yearly dictionary would also leave related lower-level graph
and geometry dependencies unresolved.

Existing recovery is to wait for production to finish and open the refreshed
run-page GL link in a new tab, or reload the old document. This resets page-local
caches and obtains fresh queries. It does **not** guarantee a snapshot across
later independent queries, update an already open tab automatically, or prove
all HTTP/service caches current. Same-scenario selection is a no-op; changing
scenario resets the yearly map caches but not every graph cache. Recovery
guidance is therefore a limitation/workaround, not remediation or risk removal.

## Smallest future contract decision and exit criteria

Choose explicitly what an already open analysis does after a completed source
regeneration: require reopening with an accurately stated currentness boundary,
or detect changed generations before retaining/mixing dependent results. Define
whether the guarantee covers the whole view or the datasets consumed by one
operation. Do not call the current lazy view a snapshot to avoid that decision.

Then retain a bounded checkpoint for the chosen action: participating caches,
baseline/roads and scenario identity, authorization, in-flight response handling,
visible error/reload behavior, and measured cost. Acceptance must include the
actual producer → query service → open browser path and the retained old/new
year probe. Related candidates need individual supported-workflow disposition;
the single active-module probe does not prove them all defective. No new service
or background protocol is presumed necessary.

Residual user risk remains: an open dashboard can display results from different
file generations after a run is regenerated. This finding must remain visible
in final limitations and cannot appear among completed fixes. Other confirmed
in-scope fixes, full inventory disposition, independent changed-code reviews,
performance gates and development-stack/runtime acceptance remain mandatory.
