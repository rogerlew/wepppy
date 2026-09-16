# Future report implementation plan

Status: planning handoff only. No steps below have been implemented or validated.
This is not an active authorization to write report code. Start a successor
implementation package/ExecPlan after owner ratification; use the current
[report contract](../../../ui-docs/contracts/postfire-debris-flow-report-contract.md),
not this closed execution record, as durable authority.

## Milestone 0 — Ratify the exact read interface

Read nearest WEPPcloud, controller, test and feature-registry instructions. Bind
the proposed page `/runs/<runid>/<config>/report/postfire_debris_flow/`, report
menu entry, query/detail/download paths, exact JSON fields, response/error
envelopes and allowed parameters in current canonical contracts. Reuse existing
run access and feature discoverability; no new report route may bypass them.
Specify accepted-attempt identity transport, stale/replaced response, legacy
support and export context. Inspect existing authorized report adapters before
choosing filenames. Do not add a general query engine or frontend state framework.
Amend the rainfall/results contract for the additive validated design/inverse
projection: current `results.py::ResultCatalog` exposes manifest/events only.
Re-triage future browser/query/download implementation as high security impact
unless documented scope proves otherwise; dedicated runtime security review is required.

Record base revision, exact owner-approved delta, compatibility/security plan,
field/state matrix and two independent contract reviews plus dedicated UX review.
Resolve findings and commit that checkpoint as an ancestor before code edits.
No scientific defaults or schema changes are included; any newly required
parameterization decision needs its own approved ADR before implementation.

## Milestone 1 — Read adapter and tests

Under `wepppy/weppcloud/routes/`, add the bounded report adapter to the appropriate
existing postfire route module after inspecting it. Compose accepted production
state with `open_results`, `list_events` and `get_event`; do not open tables
unchecked or acquire/rebuild anything. Test authenticated/unauthorized report,
query and downloads, legacy v1, v2 M1/M3, hash failures, valid absence, partial
results, failed replacement and stale snapshots. Use actual temporary files for
filesystem/provenance failures; mocks alone cannot validate those boundaries.

Extend `wepppy/nodb/mods/postfire_debris_flow/results.py` minimally to expose
validated saved design/inverse rows from the same immutable catalog snapshot.
`open_results` already validates those tables but discards them. Preserve existing
callers and byte/schema limits; do not add a second unchecked read. Retain saved
v2 validity-mask decoding and scalar consistency checks during validation, while
forbidding new upstream raster reads or scenario/predictor computation. Test the
additive projection's compatibility, corrupted tables/mask and replacement races.

Test `Cache-Control: no-store` on report/query/detail/CSV and inspect the reused
artifact-download route's cache behavior. Implement explicit spreadsheet-safe
text-cell export with hostile label/reason fixtures; ordinary CSV quoting does
not prevent formula interpretation. Do not rewrite unrelated shared exports.

Prove a report read leaves NoDb, climate/soil/source artifacts and all published
result bytes unchanged and creates no jobs. Add sanitized fixtures from more
than one watershed rather than hardcoding overpriced-sprawl. Test bounded
requests and duplicate dates; use exact event IDs and source-specific design rows.

## Milestone 2 — Familiar template/controller

Add a report template under `wepppy/weppcloud/templates/reports/postfire_debris_flow/`
extending `_base_report.htm`. Use one safe JSON seed and one controller initializer;
place report controller/tests under existing `controllers_js` conventions. Reuse
Unitizer and table classes, not copied Geneva domain logic. Build saved design
markers and equivalent four-row table, three-row threshold comparison, paginated
events/detail, provenance and downloads. No map or continuous curve in this scope.

Write controller tests before implementation for duration/filter/reset/pagination,
selection, probability formatting, SI/English updates, nullable values, keyboard
activation and late-response suppression. Do not sort only the visible event
page when the UI claims a catalog sort. Source/model labels are read-only saved
assessment values; accepted replacement must trigger coherent reload behavior.

## Milestone 3 — Integration and human acceptance

Use real accepted M1 and M3 development runs and existing fixture catalogs to
cover both frequency sources. Overpriced-sprawl is one regression example, not
the only acceptance basin. Select and record another compatible basin for M3;
report reads do not authorize rerunning it. If a required saved bundle is absent,
record the specific evidence gap and request bounded run authority separately.

In a production-equivalent development browser/service identity, compare visible
values and downloaded rows against exact accepted parquet values. Record run,
config, accepted model/attempt, input/output hashes, date semantics, source,
valid coverage and units. Exercise full-scale event paging; retain measured
load/query timings and browser responsiveness, not an invented SLA. No entire
event catalog should be seeded into HTML. Observe unchanged input/result hashes
and absence of new RQ jobs after opening/filtering/unitizing/downloading.

Demonstrate absent, empty, partial, unavailable, stale, failed-replacement and
assessment-replaced states using isolated copied fixtures where mutation would
otherwise affect an owner's run. Verify authorized normal artifact browse,
download and archive/restore paths, including failed/intermediate records.
Do not generate screenshots containing secrets or raw host paths.

The dedicated UX reviewer walks through the primary tasks with desktop and
narrow layouts, keyboard-only and supported themes. Capture screenshots and
task observations; state that expert agent review is not a study with end-users.
Keep essential caveats near results and detailed provenance expandable.

## Milestone 4 — Gates and delivery

From `/home/workdir/wepppy`, use the existing targeted suites plus new report
test modules (record their exact names in the active implementation ExecPlan):

    wctl run-pytest tests/nodb/mods --maxfail=1
    wctl run-pytest tests/weppcloud --maxfail=1
    wctl run-npm lint
    wctl run-npm test
    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path docs/ui-docs/contracts/postfire-debris-flow-report-contract.md

Confirm actual test directories before narrowing commands; no hypothetical new
test file is counted as evidence. Update user-facing module/help documentation
alongside implementation, and repeat correctness/security/UX review against code
and retained live evidence. Resolve all medium/high findings. Commit only with
authority; deployment is a separate request. Handoff implemented/wired/verified
states separately. Rollback removes only the additive report entry/adapter/UI
and never deletes accepted model artifacts or changes run preferences.
