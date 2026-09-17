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
- [x] (2026-09-17) Commit standalone contract checkpoint `714693a00`.
- [x] (2026-09-17) Implement template, JavaScript, CSS, user guidance and
  regression tests.
- [x] (2026-09-17) Rebuild assets, restart the complete stack and pass focused,
  full frontend, route, theme-metrics and authenticated browser acceptance.
- [x] (2026-09-17) Resolve the independent review's disabled-link loading-state
  finding and receive final approval with no open findings.

## Surprises & Discoveries

- The chart appends axis/P50 labels before its response line and scenario
  markers, so later SVG elements can paint over text.
- The event form uses unclassed native controls instead of the shared numeric,
  select, checkbox and button-row conventions.
- Pure form specificity overrode the shared numeric control width inside this
  report, so the browser initially measured 232- and 200-pixel inputs. A
  report-scoped canonical-width rule restores both to 120 pixels.
- Authenticated axe testing found 4.08:1 contrast on event-date links against
  striped rows. The existing theme hover token provides sufficient contrast in
  the required default, light high-contrast and AA dark themes.

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

The report now uses the shared semantic summary pane, keeps every chart label
above data marks with a pointer-transparent theme-token halo, and presents Storm
events filters with canonical bounded controls and consistent spacing. The
complete stack was restarted and the saved `thespian-cleanness` M3 report passed
authenticated desktop/narrow acceptance in default, light high-contrast and AA
dark themes, including zero axe violations, pointer overlap, keyboard marker
selection, loading state and real filter requests.

Browser evidence found and drove two additional scoped fixes: Pure form
specificity had stretched the numeric controls, and event links needed both an
AA-contrast enabled color and preservation of the shared disabled color. Final
independent review approved the implementation with no open findings.

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
