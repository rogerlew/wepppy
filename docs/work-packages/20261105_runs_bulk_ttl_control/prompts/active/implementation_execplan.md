# Sort runs by deletion date and protect selected runs

## Purpose / Big Picture

Users can sort Automatic deletion ascending to find the earliest eligible runs,
then disable automatic deletion for selected rows without opening each project.
Execute only this package; preserve all unrelated working-tree changes.

## Progress

- [x] (2026-11-05) Inspect template, sort helper, existing setter and canonical contracts.
- [x] Prepare bounded contract decision and amendments.
- [x] (2026-11-05) Obtain two independent reviews and resolve the medium response-integrity finding.
- [x] (2026-11-05) Commit accepted checkpoint as `6cbd4404b` after operator approval.
- [x] (2026-11-05) Add failing regressions, implement sorting and bulk protection.
- [x] (2026-11-05) Focused tests, frontend checks, Chromium smoke and independent correctness/security reviews.
- [x] (2026-11-05 Pacific) Full Python gate: 13,218 passed / 423 skipped; final documentation and handoff complete.

## Surprises & Discoveries

The current domain contract explicitly prohibits sorting after a misleading
Last Modified sort was removed. Sorting must use `ttl_deletion_at` instead.
The existing setter already supports ordinary authenticated authorized users;
no bulk API is needed. Selection currently excludes readonly rows. Review found
failed alias reloads could restore old rows on search; clearing cached arrays
and checking fetch generations resolves that misleading-selection risk.

## Decision Log

Use chronological expiration sorting with nulls last and the existing per-run
setter. This fulfills the 2026-11-05 request without new persistence, auth or
queue contracts. Exact normative details and rationale are in the decision
artifact and current domain contracts. Checkpoint commit authority granted by the operator on 2026-11-05.

## Outcomes & Retrospective

Checkpoint committed; implementation and focused validation complete. Both
independent implementation reviews passed after fixing stale alias-state reuse.
Full Python gate passed: 13,218 passed / 423 skipped. Frontend: 1,067 passed;
focused Python: 104 passed. Chromium confirmed the actual rendered action,
partial failures and mobile fit with mocked HTTP. Deployment is not claimed.

## Context and Orientation

`wepppy/weppcloud/templates/user/runs2.html` owns table rendering, selection,
CSRF headers and bulk deletion. `wepppy/weppcloud/routes/user.py` normalizes
sort keys and sorts legacy and projected metadata. The existing setter is
`POST /runs/<runid>/<config>/tasks/set_ttl_disabled` in
`wepppy/weppcloud/routes/nodb_api/project_bp.py`; keep it unchanged.

## Plan of Work

Complete the contract checkpoint first. Add the metadata sort allowlist key
and chronological timestamp handling, reuse the sortable-header macro, and
add the adjacent button using existing selected-row identifiers and URL helper.
Use sequential POSTs and explicit progress/partial failures; protect only
confirmed successful rows and keep failed selections available for retry.
Update the published run-ttl-deletion guide with the table workflow.

## Concrete Steps

From `/workdir/wepppy`, inspect and extend tests under `tests/weppcloud/routes/`
and the established frontend test harness. Run `wctl run-pytest` on changed
modules and existing TTL route tests, `wctl run-npm lint`, `wctl run-npm test`,
and `wctl run-pytest tests --maxfail=1`. Run `wctl doc-lint --path` for each
changed Markdown file. Record actual outcomes and blockers in the tracker.

## Validation and Acceptance

Ascending dates include overdue runs first; disabled/unknown dates sort last
in either direction. Header toggles direction and reports aria-sort. Clicking
the bulk button issues authorized CSRF-protected requests only for selected
rows, reports progress and mixed outcomes, and updates only confirmed successes.
Exercise the actual handler with a prefixed URL and ordinary user context.
Run independent correctness and security reviews; resolve high/medium findings.

## Idempotence and Recovery

Repeated disable requests preserve protection via the existing setter. Partial
failures are retryable. Revert only this package's edits if necessary; never
reset unrelated changes. No production deployment is authorized by this plan.

## Artifacts and Notes

Decision and reviews belong under this package's `artifacts/`. Record the
standalone contract ancestor in `tracker.md` before implementation.

## Interfaces and Dependencies

Reuse `ttl_deletion_at`, `ttl_disabled`, existing checkbox selection,
`buildRunUrl`, `csrfHeaders` and the existing setter response envelope. No new
dependency, schema, endpoint, scheduler change or TTL formula is introduced.

Plan created 2026-11-05 for the operator-requested bounded enhancement.

Updated 2026-11-05: implementation, focused validation and review evidence added;
full Python validation passed; local implementation is complete.

Final update: full gate passed after one hour. Independent review resolved stale
scope-cache/error races, and Chromium exposed the narrow-screen wrapping fix.
All production changes remain limited to the approved sorting/bulk UI scope.
