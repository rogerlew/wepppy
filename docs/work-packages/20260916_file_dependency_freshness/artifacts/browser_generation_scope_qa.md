# B-F01 browser generation scope and UX review

**Disposition: B-F01 remains OPEN, with a confirmed mixed-generation result and
an unresolved UX/currentness contract.** The current GL specification defines
page initialization, interactive lazy reads and scenario-change invalidation.
It defines neither automatic refresh after a completed rerun nor an immutable
whole-page scientific snapshot. No existing normative trigger was found that
would authorize treating a small missing event handler as the complete fix.
This review does not waive B-F01 or the related browser candidates.

## Contract and reproduced behavior

The [GL specification](../../../ui-docs/gl-dashboard.md) says “real-time
exploration” in its overview, but its concrete **Data Flow**, **Layer Lifecycle**
and **State Management** sections specify:

- Detection on page load and scenario change; rendering on layer/year changes.
- Fetching summaries when not cached, and clearing cached summaries when the
  scenario path changes. The year-slider flow describes selecting/querying a
  year, without defining validation of already loaded years after file changes.
- Page-global state shared among module instances. Module URL cache-busting
  prevents mixed JavaScript versions; it does not observe scientific file bytes.

The local module README additionally says the map scenario selector does not
govern graphs: graphs have their own scenario lists/loaders. Neither document
defines generation identity, completion-event subscriptions, a refresh control,
or a stale-page notification. “Real-time exploration” is insufficient evidence
for a background refresh protocol; documented caching is also insufficient to
claim a coherent snapshot of data that is lazily fetched later.

The retained [active-module probe](gl_dashboard_generation_probe.json) remains
valid: after real Parquet replacement, cached year 2000 returns **25**, first
loading year 2001 returns **76**, and a fresh manager returns new year 2000
**75**. Its query seam uses real DuckDB, but it is not a deployed-browser or
live-job test. Only two queries occurred in the old manager. Calling the view
a snapshot would misdescribe that demonstrated mixture.

## Actual producer and normal refresh path

1. `rq/wepp_rq_stage_post.py:345` invokes the native watershed interchange.
   `wepp/interchange/watershed_loss_interchange.py:23` selects stable
   `loss_pw0.all_years.{hill,chn,out}.parquet` names; its native
   `watershed_loss_to_parquet` call publishes the converted results. The post
   stage then force-refreshes the query-engine catalog and publishes status.
2. The run-page WEPP controller handles `WEPP_RUN_TASK_COMPLETED` at
   `controllers_js/wepp.js:440`, refreshes its report and emits its local
   completion event. `templates/controls/wepp_reports.htm:130` links to GL in
   a **new tab** (`target="_blank"`, `rel="noopener"`). This is the existing
   normal reentry path after producing new results.
3. `routes/gl_dashboard.py:121` authorizes the run and builds current context,
   including baseline/roads paths and available scenarios. The standalone
   `templates/gl_dashboard.htm:1028` loads the GL bundle. Its base template
   supplies session heartbeat/UI helpers, not the run-page WEPP controller or
   a producer-completion subscription. No cross-tab bridge was found.
4. `static/js/gl-dashboard.js:1291` initializes detection and the ordinary
   query helpers. `data/query-engine.js` POSTs to the existing authenticated
   query endpoint with the selected scenario in the body. The response at
   `query_engine/app/server.py:891` contains records/schema/row count and
   optional formatting/SQL, not a dataset generation token.
5. `data/wepp-data.js:430` returns a cached base year before transport;
   yearly active and channel refreshes have the same shape. A genuinely new
   document initializes empty page caches and issues new queries. A changed
   scenario clears the three yearly map caches at `scenario/manager.js:245`
   and redetects overlays; selecting the same scenario returns immediately.
   This is not a complete graph-data reset.

Thus reopening/reloading after completed production is an existing recovery
path. Re-selecting the same scenario, moving the year slider, or toggling a
layer is not evidence that all displayed results are current. Fresh page state
also does not promise an atomic snapshot across future independent queries.

## Related browser families remain finite and open

| Family | Traced behavior | Remaining disposition |
| --- | --- | --- |
| GL graph loaders | `force` bypasses only `graphDataCache`; hill/channel/outlet/area caches can still return old rows. Map scenario changes do not clear all of them. | Include in any accepted GL refresh boundary; no independent full graph failure probe yet. |
| GL batch GeoJSON | `layers/detector.js:214` caches a merged resource promise by batch/config/kind, including unavailable results; run membership is absent from the key. | Within-page membership/geometry refresh policy unresolved; no reproduced normal-refresh failure. |
| Storm-event warm-up year | `event-data.js:541` retains climate `MIN(year)` by run ID, then uses it in subsequent event filters. | Scientific dependency candidate; actual event misfilter and its intended refresh boundary remain unproven. |
| Parquet schema preview | URL-keyed promise survives collapse/reopen; a new document resets it. | Schema-refresh UX unresolved; not evidence of server authorization bypass. |
| Combined watershed viewer | Variable changes clear `dataCache`; range/unit changes restyle retained data. | Run regeneration while open needs its own explicit generation disposition. |

Managed find/flash geometry reloads and SBS availability events already traced
in [the inventory](remaining_services_tools_browser_inventory.md) retain their
narrow dispositions; they do not settle these other caches. B-L01 remains an
excluded legacy entrypoint, not a newly promoted production defect.

## Smallest justified next step

Keep the confirmed finding and related candidates unresolved until the canonical
GL UX contract chooses the boundary after regeneration: an explicit reopen
workflow with accurately stated limitations, or detecting a changed generation
before retaining/mixing dependent results. Reopen guidance can describe the
existing recovery path, but documentation alone cannot be presented as closing
the mixed-generation defect or establishing a snapshot guarantee.

The present evidence does not justify adding a polling service, live protocol,
global cache clearing on every slider movement, or using a job timestamp/TTL
as scientific byte identity. A future bounded checkpoint must cover all caches
participating in the chosen refresh action, preserve baseline/roads and scenario
authorization, reject stale in-flight responses after reset, and test actual
producer → query service → open browser behavior. Reviewed unit/smoke coverage
exercises scenarios, controls and ranges; it does not establish that workflow.

Review was read-only apart from this artifact. No runtime/test changes, service
activity, fresh benchmark load or named-run mutation occurred. A minor navigation
issue remains: the nearest GL AGENTS/README point at `wepppy/docs/ui-docs/` while
the normative document actually resides at `docs/ui-docs/gl-dashboard.md`.
