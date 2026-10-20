# Water output documentation tracker

Status: Active — implementation and validation; index publication awaits operator exception.

- Starting WEPPpy revision: `1ecf04735`; native revision: `54d0867`.
- Audit: `docs/dev-notes/20261020_water_output_documentation_audit.md`.
- Active plan: [water_output_documentation_execplan.md](prompts/active/water_output_documentation_execplan.md).
- Contract checkpoint: `14c7eebb1`, two independent reviews approved after disposition.
- Implementation written; focused 281 checks passed, native Python 163 passed, interchange/reports 105 passed (1 skipped), fresh temporary-catalog discovery 7 passed; isolated Chromium checks passed. Native paired release `3b63064`; final review and broad validation underway.

## Decisions

Preserve all numerical behavior. Add guides under Technical Reference without changing protected navigation sections. Preserve the pre-existing dirty generated Usersum index; validate a fresh temporary index and publish only task-specific changes if safely separable, otherwise document the required rebuild without altering unrelated entries.

## Handoff state (2026-10-20 UTC)

Source implementation committed as `b47b768d7`; paired native `3b63064`.
Independent source/scientific and UX reviews pass with all medium/high findings
closed. Browser evidence uses an isolated fresh catalog, not the active index.
The operator's requested dirty-index exception is unanswered; package closure and
normal-catalog publication remain pending. No production deployment or push.

Broad pytest continues in development through the resumed run, with log
`/tmp/water-docs-broad-resumed.log` on the host and exec session `41660`.
The initial run completed 45 files before a stale expected native hash failed;
the entire startup-contract file was rerun after correcting that test. The
resumed sweep has passed startup/service tests and is running treatment-soil
artifact cases. Do not count the broad sweep as passed until it completes.
All focused, native, frontend, and isolated discovery checks have passed.

After index permission, preserve an exact backup, merge only package-owned new
entries and changed guide text/nav entries, validate the actual freshly loaded
catalog and normal-user routes/search/browser, and retain publication evidence.
Then record broad outcome, remove the active-plan root pointer, and close the
package using the normal completed-plan move. Machine-unit compatibility work
remains separate and documented in the user variable reference.
