# SURF-11 Pure UI Geneva Summary Report Contract

**Status**: Closed
**Package ID**: SURF-11
**Security impact**: `high` for authenticated run queries and map data

## Purpose

Verify the Geneva interactive summary from authenticated run-scoped query and
report routes through actual rendered controls, client initialization,
selection/filter/map behavior, Unitizer refresh, and unavailable/error states.

## Concise Intent Contract

The report route renders the canonical Pure report shell with the same
validated summary payload returned by the summary query. The client initializes
exactly once when the report root exists, renders storm parameters/chart/table,
keeps marker and table selection synchronized, refreshes summary filters, and
updates displayed values after Unitizer preference events.

The HRU map posts schema-versioned requests to the run-scoped rows/features
URLs embedded by the template, restricts measures to the registered Geneva map
set, and renders available, unavailable, and error states without exposing
paths or raw internals. Query/report responses remain no-store and preserve the
canonical Geneva top-level payload and error shapes.

## Scope

- `routes/nodb_api/geneva_bp.py` summary/report/HRU query producers;
- `templates/reports/geneva/summary.htm`;
- `controllers_js/geneva_summary_report.js` and generated bundle;
- Geneva query schema/collaborator evidence already owned by DOM-27; and
- direct render, Jest, route, and focused Geneva query/service tests.

## Exclusions

Geneva configuration/workflow/RQ execution remains DOM-27. Shared report-shell
behavior remains SURF-12 and preference persistence remains SHR-05. This
package does not change hydrologic formulas, map artifacts, schemas, queue
wiring, authorization policy, or external terrain-provider choice.

## Acceptance

Actual rendering proves exact filters, selected values, payload node, run URLs,
map/actions, accessibility, empty/error targets, and one production client
initialization path. Existing and extended Jest/route/service suites prove
filter, selection, Unitizer, map request/response, availability, validation,
no-store, and reload behavior. Any mismatch receives the smallest compatible
repair plus independent security/correctness review.

## Outcome

The production route, template, controller, schema, map, and Unitizer seams
conformed without a production repair. Direct rendering now fixes the
risk-bearing names, selected values, run URLs, payload, actions, lifecycle
targets, and accessibility hooks. A lifecycle regression proves the controller
remains the sole `DOMContentLoaded` initialization owner.

Independent review rejected a proposed duplicate template bootstrap before
commit because it would have double-bound requests. The duplicate was removed,
the lifecycle test was corrected, and final review passed with no unresolved
findings.
