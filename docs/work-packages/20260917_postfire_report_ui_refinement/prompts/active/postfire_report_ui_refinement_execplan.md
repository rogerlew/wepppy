# Refine the post-fire likelihood report UI

This ExecPlan is maintained under `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Make the saved report easier to scan and operate. Assessment metadata should
look like other WEPPcloud summaries, chart labels must stay readable when data
markers occupy the same location, and event filters should use familiar,
properly spaced inputs instead of full-width browser controls.

## Progress

- [x] (2026-09-17) Inspect source, contracts, shared components and tests.
- [x] (2026-09-17) Obtain two independent contract reviews; both passed after
  the contract clarified authority, spacing, pointer behavior and empty notices.
- [ ] Commit the standalone contract checkpoint.
- [ ] Implement template, JavaScript, CSS and regression tests.
- [ ] Rebuild generated assets and validate the authenticated report.
- [ ] Complete independent implementation review and close.

## Surprises & Discoveries

- The chart appends axis/P50 labels before its response line and scenario
  markers, so later SVG elements can paint over text.
- The event form uses unclassed native controls instead of the shared numeric,
  select, checkbox and button-row conventions.

## Decision Log

- Decision: preserve all filter names, query values and controller selectors;
  change only their markup and layout.
  Rationale: the problem is presentation, not query behavior.
  Date/Author: 2026-09-17, Codex.
- Decision: put chart text in a final SVG label layer with a theme-token stroke.
  Rationale: paint order prevents marker occlusion, while surface/text tokens
  keep the halo compatible with every theme.
  Date/Author: 2026-09-17, Codex.
- Decision: make the final label layer pointer-transparent and use an explicit
  3-pixel rounded halo.
  Rationale: labels must remain legible without blocking pointer activation of
  the markers beneath them.
  Date/Author: 2026-09-17, Codex after independent accessibility review.

## Outcomes & Retrospective

Pending implementation.

## Context and Orientation

`wepppy/weppcloud/templates/reports/postfire_debris_flow/report.htm` owns report
markup. `wepppy/weppcloud/controllers_js/postfire_report.js` renders accepted
metadata, chart SVG and event results. Shared field macros are in
`wepppy/weppcloud/templates/controls/_pure_macros.html`; the button row is in
`wepppy/weppcloud/templates/shared/console_macros.htm`. Theme tokens and shared
components live in `wepppy/weppcloud/static/css/ui-foundation.css`. The canonical
behavior is `docs/ui-docs/contracts/postfire-debris-flow-report-contract.md`.

## Plan of Work

Commit the reviewed contract amendment first. Then replace summary paragraphs
with one `wc-summary-pane` definition list while preserving the interpretation
note. Import and use shared numeric/select macros and the canonical checkbox and
button row for filters. Add a small responsive filter grid using existing spacing
tokens, at least a medium row gap and bounded field widths. Render all chart text
in a final pointer-transparent SVG group and give labels a text-color fill with a
surface-color stroke, explicit 3-pixel rounded halo and stroke-first paint order.
Retain all ARIA labels and keyboard interactions.

## Concrete Steps

From `/home/workdir/wepppy`, build the controller bundle in the application
container, run focused and full Jest, targeted template/route pytest, frontend
lint, an authenticated axe scan, theme checks and a Playwright browser check on
`thespian-cleanness`. Restart only the web service if templates are cached.

## Validation and Acceptance

The real report shows an Assessment summary pane. Chart labels remain above the
line and markers and use only theme tokens for fill/stroke. The filter form has
visible vertical separation; the two numeric inputs are bounded rather than
full width; Apply/Reset have normal button-row separation. Keyboard order,
labels, query values, reset behavior and event results remain unchanged. Check
desktop, mobile, default/dark/high-contrast themes, axe and reload.

## Idempotence and Recovery

Bundle rebuild and web restart are repeatable. Browser checks are read-only.
No model run or project mutation is required. Preserve unrelated working files.

## Artifacts and Notes

Retain contract reviews, test logs, screenshots, axe/theme results and final
review in this package. Intermediate failures remain as evidence.

## Interfaces and Dependencies

Use existing Jinja macros, `WCDom`, SVG creation helpers and CSS variables. Add
no dependencies and change no API, query or persistence contract.
