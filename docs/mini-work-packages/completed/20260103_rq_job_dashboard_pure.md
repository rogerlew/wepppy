# Mini Work Package: RQ Job Dashboard Pure UI
Status: Completed (2026-01-03)
Last Updated: 2026-01-03
Primary Areas: `wepppy/weppcloud/routes/rq/job_dashboard/routes.py`, `wepppy/weppcloud/routes/rq/job_dashboard/templates/dashboard_pure.htm`, `docs/ui-docs/ui-style-guide.md`

## Objective
Replace the Bootstrap-based RQ job dashboard with a Pure CSS + `base_pure.htm` implementation that follows the Console Deck Layout pattern.

## Current State Review
- `dashboard_pure.htm` is now the canonical job dashboard template (Pure UI + `base_pure.htm`).
- Job tree rendering is client-side and re-renders on poll; it preserves open state by checking `<details open>`.
- Error states use `wc-status-chip` + `wc-pre` blocks for readable stack traces.

## Scope
- Add `dashboard_pure.htm` that extends `base_pure.htm` and uses Pure UI patterns.
- Update the route to render `dashboard_pure.htm`.
- Update the inline JS markup generator to output Pure CSS classes, `<details>` collapses, and accessible status blocks.
- Gate the dashboard with `requires_cap` for anonymous users.

## Non-goals
- Changing rq-engine/jobinfo payloads or polling cadence.
- Adding new backend endpoints or auth behavior.
- Styling beyond existing Pure UI tokens.

## Plan
- [x] Layout: adopt Pattern #8 (Console Deck Layout) with `console_page` + `console_header`.
- [x] Summary: use Pattern #2 (Snapshot Summary Pane) for job/run metadata.
- [x] Actions: move Cancel Job to the header toolbar (`pure-button`).
- [x] Job tree: replace Bootstrap collapse with `<details class="wc-collapse">` and render job rows as a Pure table or grid.
- [x] Progress: replace Bootstrap progress bar with a minimal `.wc-upload-progress`-style bar (template-local CSS).
- [x] Status: use `wc-status-chip` for job status and `wc-status` blocks for errors.
- [x] JS: preserve open states by reading `details.open` before re-render; remove Bootstrap collapse setup and data attributes.
- [x] Routing: swap `dashboard.htm` for `dashboard_pure.htm`; keep legacy template until smoke validation is done.
- [x] Validation: manual pass (job renders, nested groups open/close, cancel works, fallback URL works).
- [x] Cleanup: remove `dashboard.htm` after validation.

## Exit Criteria
- Dashboard renders via `base_pure.htm` with no Bootstrap/Font Awesome imports.
- Job tree is navigable and readable at desktop + mobile widths.
- Error states and cancel flow are still functional.
- `dashboard.htm` removed from the route template directory.
- Dashboard is gated via `requires_cap`.

## Progress Notes
- Implemented `dashboard_pure.htm` with Pure UI layout, summary pane, job tree, and progress bars.
- Updated route to render `dashboard_pure.htm` and added `requires_cap`.
- Fixed cancel endpoint to call `/rq/api/canceljob/<job_id>`.
- Adjusted job-order status logic so canceled/stopped jobs report terminal states and reflect counts in summaries.
- Removed legacy `dashboard.htm` after validation.
