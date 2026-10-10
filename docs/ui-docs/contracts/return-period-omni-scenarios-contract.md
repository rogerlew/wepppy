# Return-period simple report Omni comparisons

Status: intended behavior; implementation conformance pending.

## Scope and rationale

The WEPP return-period simple report must compare the current project with
selected completed Omni scenarios. Each scenario is ranked independently:
joining event dates would incorrectly imply that the same storm defines each
scenario's return period. Use concatenated rows, not a join on dates.
The operator requested this behavior on 2026-10-10.

This contract composes the existing [controller presentation contract](../controller-contract.md)
and [output-scope contract](../../schemas/output-scope-contract.md).
Authorization, report calculations, model inputs, and stored output schemas
remain unchanged. This is a report presentation and runtime CSV extension.

## Configuration and selection

The Configuration card must include a native Details control titled
`OMNI Scenarios Selection`, using the existing `wc-collapse` pattern. List
completed scenarios belonging to the current project in stable name order,
with a programmatically labeled checkbox for each. No scenarios are selected
on an initial URL without selection parameters. Use an explicit `Run report`
button to apply multiple selections together. Reuse `wc-choice` checkbox styling.

Use repeated `omni_scenario` query parameters containing exact scenario names.
Deduplicate selections and order them by the displayed scenario list. Preserve
all selections across year, month, method, Gringorten, channel, unit preference,
and CSV interactions; preserve recurrence intervals and output scope as well.
Clearing every checkbox removes all selection parameters.

Selection applies only to simple tables. The extraneous view retains its
current single-project tables and CSV. It preserves applied selection parameters
for returning to the simple view and explains that comparison is available in
the simple view; hide the selection controls while in the extraneous view.

## Completion and valid states

Discovery must be read-only and confined to this project's
`_pups/omni/scenarios` children. Use existing Omni scenario definitions and
completion evidence, including supported legacy results; do not equate directory
or `wepp.nodb` existence with successful completion. Do not create Omni state
merely to render a report. Completion and report readiness are distinct:
completed scenarios must be listed, but a completed scenario whose required
report inputs are unavailable must be disabled with an explanation.

Candidates must derive from configured Omni scenario definitions, using the
existing scenario-name generator rather than arbitrary directory names.
Completion requires the established child `wepp/output/loss_pw0.out.parquet`
artifact. Modern children also require the child `READONLY` finalization marker,
which cloning removes before rerunning. Available explicit current-attempt
running/failure evidence overrides stale artifacts. Existing successful
`executed`/`skipped` state entries alone are insufficient. Truly absent legacy
run-state metadata may use the established output artifact plus readable report
sources when no current-attempt evidence contradicts completion. A present-empty
modern run-state list is not legacy evidence; modern finalization evidence is
still required. Do not invent or reconstruct unavailable historical job state.

Report readiness requires both `return_period_events.parquet` and
`return_period_event_ranks.parquet` in the selected scope's output/interchange
directory. Discovery checks these without triggering regeneration; selected
children also require readable Wepp state. Selected reports must parse the
datasets through the normal report reader. Missing files disable
the choice with a reason. Invalid content surfaces the normal report error;
file presence is not semantic validation. Parent report preparation retains
its existing behavior. Normal Omni execution owns child asset preparation.

| Runtime state | Required outcome |
| --- | --- |
| Omni absent or never used | Render normal report and `No completed Omni scenarios available.` |
| Omni present, no completed scenarios | Same empty selection state; no exception |
| Completed, report-ready scenarios | Unchecked choices; selected reports use their own data |
| Legacy completed results without newer run-state metadata | Accept established completion artifacts and readable report sources |
| Running, failed, or incomplete scenario | Never offer as a completed choice, even when old output files remain |
| Completed but missing report inputs | List disabled with reason; direct selection returns explicit error |
| Valid report with no events after filtering | Show scenario-specific no-events message; do not fabricate zero rows |
| Deleted or unavailable selection | Explicit error identifying the unavailable selection; no silent omission |
| Unknown name, traversal, or escaping symlink | HTTP 400; do not read outside the authorized scenario root |
| Restored project | Discover supported completed artifacts through the same reader |

Validate selections against server-discovered names before opening selected
paths, and verify resolved child paths remain inside the resolved scenario
root. The resolved scenario root itself must remain inside the authorized
project root; a symlink must not redefine that boundary. Child NoDb and report
output paths must resolve inside that child. Existing shared climate/watershed
input links into the parent project remain valid; do not apply a blanket ban
on child input symlinks. Test both legitimate shared inputs and escaping paths.
Preserve established parent-run authorization and CAPTCHA gates.
Unknown/unavailable direct selections return HTTP 400 with an actionable
description. Unexpected read failures must surface through the established
report error boundary, with diagnostic logging; never substitute baseline data.

## Tables and CSV

With no selections, preserve the existing simple table and CSV columns.
With selections, prepend a `Scenario` column to every simple metric table and
its CSV. Label the current project `Current project`; label children with their
exact scenario names. Render current-project rows first, then selected scenarios
in displayed order, with recurrence intervals descending inside each group.
Each row contains that scenario's recurrence interval, event date, and metric
value. Resolve dates against that report's own calendar/display year and `y0`.
Do not borrow parent dates, values, units, or availability for child reports.
Use the parent report's unit preferences consistently for presentation.

Evaluate all reports with the same requested recurrence intervals, excluded
years/months, method, correction, channel, and output scope. Never substitute
baseline outputs when a selected Roads dataset is missing. Include metrics
available only in selected scenarios; retain core-metric no-events messaging.
Missing individual events produce no invented rows. If any scenario has rows,
render the table and allow download even if the current project has no rows.
A channel with no child events produces that child's no-events outcome.
For comparison evaluation, pass `meoization=False` to the existing report API
for both parent and children: its current memoized JSON does not distinguish
all method/interval choices and would otherwise permit stale comparisons.
No-selection cache behavior is unchanged; no new comparison cache is introduced.

Each existing `Download CSV` action exports that metric's concatenated table,
including all applied selections and the current project. Use the existing CSV
serializer and unit conversion; preserve numeric cells and existing headers
apart from the added `Scenario` column. A request with no rows across all
selected reports retains the existing no-data response. No new persisted CSV
or run-data schema is introduced.
Accepted child names retain the existing scenario generator's enum prefix;
test that discovery cannot inject arbitrary spreadsheet-formula labels into
the new Scenario cells. Do not change the shared CSV writer or numeric cells.

## Evidence and operational boundaries

Test absent, empty, populated, legacy, incomplete, missing-input, restored,
and hostile states independently from query combinations. Exercise zero, one,
and multiple selections; differing event dates and start years; duplicate
parameters; empty metrics; custom intervals; CTA/AM; exclusions; units;
baseline/Roads; and extraneous toggling.

Directly test real directory and symlink containment. Render the actual template,
exercise browser selection/navigation, and parse bytes from the actual CSV
serializer. Compare scenario labels, dates, intervals, values, and units between
source reports, HTML, and CSV. A successful HTTP status alone is insufficient.
Include a warmed-cache CTA-to-AM/custom-interval comparison regression, and
direct root/intermediate-symlink and child-output escape tests alongside a valid
clone with shared input links.
Existing scenario outputs remain visible and archived at their existing paths;
this report adds no storage, archive exclusions, jobs, or model execution.
Confirm archive/restored fixture discovery without altering archive semantics.

This extension requires no new service, dependency, permission, or deployment
workflow. Deployment and production validation must be reported separately
from implementation and local validation.
