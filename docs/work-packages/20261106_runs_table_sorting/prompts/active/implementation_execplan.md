# Repair Runs table sorting and presentation

## Purpose

Users can repeatedly reverse Automatic deletion sorting, including after sorting
by Creation date, with disabled projects last. Columns keep stable widths, wrap
content, and show one help link above the table.

## Progress

- [x] (2026-11-06) Inspect current template, sort helper and shared scripts/styles.
- [x] (2026-11-06) Reproduce forest stale-worker behavior; checkpoint `5e35c480e` accepted.
- [x] (2026-11-06) Implement scoped layout/help and disabled-last ordering with failing-first regressions.
- [x] (2026-11-06) 29 route/Chromium and 1,069 frontend tests passed; reviews and docs complete.

- [x] (2026-11-06 17:33 UTC) Apply user-authorized wepp1 web-only hotfix; verify worker rotation and health.

## Surprises & Discoveries

No template code intentionally disables sort anchors. Actual pointer/navigation
and running application state must distinguish click-layout from sort-state bugs.
Prior Chromium evidence checked a link target but did not follow repeated sorts.
Forest workers returned stale normalization/template state; fresh code reversed
properly. Worker reload restored real navigation without replacing sorting.

## Decision Log

Reuse the existing server-side sorting and link transport if reproduction supports
it; do not introduce a new client sorting system without evidence. Keep disabled
rows last independently of direction. Use current authorization and TTL contracts.

On 2026-11-06 the user authorized a wepp1 web-only hotfix. Apply the reviewed
three-file delta with backups and Gunicorn HUP to avoid unrelated service recreation.

## Outcomes & Retrospective

Implemented and validated locally; forest navigation repaired by verified
Gunicorn HUP. Subsequent wepp1 web-only hotfix passed code/template and health
checks; see artifacts/2026-11-06_wepp1_hotfix.md. Broad Python rerun omitted under the
nearest documented handoff exception; see artifacts/validation.md.

## Context and Plan of Work

The template is `wepppy/weppcloud/templates/user/runs2.html`; its macro generates
sort URLs and its inline script fetches the full catalog before paging. The sort
helper is `_sort_metas` in `wepppy/weppcloud/routes/user.py`. Shared table styles
live in `static/css/ui-foundation.css`; scope new layout to Runs only. Reproduce
using actual styles and repeated navigation, then amend only confirmed consumers.
Move the existing Usersum help URL to the panel and update its published guide.

## Validation and Acceptance

Run focused route/inline-handler tests via `wctl run-pytest` and `wctl run-npm test`,
then frontend lint/full tests and required broad pytest. Chromium must click
Creation date, Automatic deletion, and several reversals, checking row order,
hit targets, current URL, stable column widths and exactly one help link. Check
long unbroken strings, empty catalog, unknown dates, disabled rows and narrow
viewports. No live user mutation is required. Record limits and real results.

## Recovery and Interfaces

Retain existing query keys, route endpoints, JSON fields, credentials and CSRF.
Revert only this package's changes if needed. No new dependency, queue, schema,
retention policy change. The authorized web-only hotfix recovery is documented
in artifacts/2026-11-06_wepp1_hotfix.md. Update this plan and tracker at handoff.

Created 2026-11-06 for the reported sort defect and explicit presentation changes.

Updated 2026-11-06: retained concrete failure/reload evidence and final validation.

Updated 2026-11-06: record the subsequent user-authorized wepp1 hotfix and verification.
