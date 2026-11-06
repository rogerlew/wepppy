# Repair Runs table sorting and presentation

## Purpose

Users can repeatedly reverse Automatic deletion sorting, including after sorting
by Creation date, with disabled projects last. Columns keep stable widths, wrap
content, and show one help link above the table.

## Progress

- [x] (2026-11-06) Inspect current template, sort helper and shared scripts/styles.
- [ ] Reproduce navigation/hit targets and complete independently reviewed checkpoint.
- [ ] Implement bounded fixes with regression tests.
- [ ] Validate, review and document results.

## Surprises & Discoveries

No template code intentionally disables sort anchors. Actual pointer/navigation
and running application state must distinguish click-layout from sort-state bugs.
Prior Chromium evidence checked a link target but did not follow repeated sorts.

## Decision Log

Reuse the existing server-side sorting and link transport if reproduction supports
it; do not introduce a new client sorting system without evidence. Keep disabled
rows last independently of direction. Use current authorization and TTL contracts.

## Outcomes & Retrospective

Pending reproduction and implementation.

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
retention policy or deployment operation. Update this plan and tracker at handoff.

Created 2026-11-06 for the reported sort defect and explicit presentation changes.
