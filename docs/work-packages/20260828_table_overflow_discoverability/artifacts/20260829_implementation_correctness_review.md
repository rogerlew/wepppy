# Table Overflow Discoverability Implementation Correctness Review

Date: 2026-08-29
Decision: `A11Y-TABLE-20260829-1`
Ratified checkpoint: `a1db47377033431e77b96a8bda2f3da8c3f5ab92`
Reviewed candidate: uncommitted implementation on
`feature/project-owned-config` at checkpoint HEAD
Review mode: independent correctness, accessibility, and UX review

## Verdict

**READY** — High: 0, Medium: 0, Low: 0.

The final candidate conforms to the canonical table-overflow and WEPP slope
display contract. The review found one High runtime defect and two Medium
contract/evidence defects in earlier candidate states; all were corrected and
re-reviewed before this verdict. No unresolved finding remains.

This is suitable as internal engineering and release evidence for the bounded
change. It is not a complete assistive-technology matrix or a buyer-facing
ACR/VPAT claim.

## Contract conformance

### Overflow eligibility and lifecycle

- The shared module activates only for a canonical wrapper containing a table,
  with positive `clientWidth` and `scrollWidth > clientWidth + 1`.
- Fitting, one-pixel-boundary, hidden, zero-width, absent, and no-table states
  remain no-ops. Resize callbacks cover both activation and cleanup.
- The module inserts one visible hint immediately before an eligible wrapper,
  adds a generated sequential focus stop only when no authored `tabindex`
  exists, and uses native Arrow and Shift-wheel scrolling without intercepting
  input events.
- Resize observation covers wrappers and their current tables, including tables
  introduced dynamically. Mutation handling synchronizes only affected
  wrappers and registers newly inserted wrappers without a document-wide rescan.
- Initialization and the explicit refresh API remain usable when ResizeObserver
  or MutationObserver is unavailable.

### Accessible semantics and ownership

- Authored `tabindex`, `role`, `aria-label`, `aria-labelledby`, and
  `aria-describedby` values are preserved under the canonical precedence rules.
- Generated description IDs are appended after authored tokens and removed
  without reordering or deleting authored tokens.
- A usable `aria-labelledby` takes precedence over a usable `aria-label`.
  Neither generated role nor generated name is added when authored name
  attributes exist but both are unusable.
- Generated labels use the first non-empty caption, then the nearest section's
  first non-empty heading, then `Scrollable data table`. Cleanup removes only
  values still matching module-owned state.
- The focus-visible rule is limited to an actively overflowing wrapper and uses
  the shared AA-validated accent token without changing widths, wrapping, or
  native overflow behavior.

### WEPP slope presentation

- Hillslope and Channel Summary header iterators are materialized exactly once
  per report before cell rendering. This is compatible with the real
  generator-backed `ReportBase.hdr` property.
- Only numeric cells whose materialized header is exactly `Slope` use fixed
  three-decimal HTML presentation. Zero retains trailing zeros and missing
  values retain the em dash.
- Non-slope ratio cells continue through the existing unitizer. The raw value
  remains the `sorttable_customkey`, and the server-generated CSV route and
  report-table selectors remain unchanged.

## Finding disposition

### TABLE-IMPL-01 — High — Resolved

The initial template indexed `hill_rpt.hdr` and `chn_rpt.hdr` directly. The real
`ReportBase.hdr` is a generator property, so Jinja resolved those indexed values
as undefined and actual report slope cells did not reach the new formatter. A
list-backed synthetic test masked the failure.

The final template materializes each iterator once and reuses that list for the
header and cell identity. The regression now exposes `hdr` as a fresh generator
property and proves both reports render the requested values. The requested
runtime behavior is now functional.

### TABLE-IMPL-02 — Medium — Resolved

The initial fallback-name implementation queried only the first heading and
used the generic label when that heading was empty. The contract requires the
nearest section's first non-empty heading. The final implementation scans the
heading sequence, and a focused regression covers an empty first heading
followed by a usable heading.

### TABLE-IMPL-03 — Medium — Resolved

The initial evidence did not directly exercise Tab traversal, hint visibility,
overflow introduced after a hidden state, or the exact CSV URL wiring. The
final Playwright case uses Tab from the preceding control and asserts the
wrapper is focused and the hint visible. Jest now covers hidden-to-overflow
activation through ResizeObserver, and the rendered-template regression checks
both CSV URLs with `format=csv`.

## Scope and regression review

The behavior implementation remains within the ratified production and test
boundary:

- `wepppy/weppcloud/static/js/table_overflow_accessibility.js`
- `wepppy/weppcloud/templates/base_pure.htm`
- `wepppy/weppcloud/static/css/ui-foundation.css`
- `wepppy/weppcloud/templates/reports/wepp/summary.htm`
- the dedicated Jest and Playwright specifications
- `tests/weppcloud/routes/test_pure_controls_render.py`
- `tests/weppcloud/test_ui_foundation_css.py`

Package, canonical-status, style-guide, accessibility-guide, ExecPlan, and
tracker edits synchronize implementation status without changing the ratified
behavior. All other dirty paths match the package's recorded exclusions. No
route, API, authentication, authorization, persistence, RQ, NoDb, report-data,
model-output, or scientific parameterization behavior changed.

## Validation evidence

Independently rerun on the final candidate:

- `wctl run-npm test -- table_overflow`: 1 suite, 11 tests passed.
- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py tests/weppcloud/test_ui_foundation_css.py --maxfail=1`:
  162 tests passed.
- Repository diff check: passed.

Package-provided final gates:

- Repository-wide Python: 7,279 passed, 63 skipped.
- Full Jest: 828 tests passed.
- Focused Chromium/Playwright: 1 test passed, including visible hint, real Tab
  traversal, Right Arrow, Shift-wheel, five AA theme focus states, 200-percent
  zoom, document containment, and Axe with no violation.
- Frontend lint and scoped documentation lint: passed.

## Residual risk

Residual risk is limited to browser/platform combinations outside the supported
Chromium evidence and dynamic DOM patterns not represented by the focused
fixture. Native scrollbar visibility and Shift-wheel behavior can still vary by
operating-system policy, which is why the UI provides multiple input methods.
No open risk warrants holding this bounded change.
