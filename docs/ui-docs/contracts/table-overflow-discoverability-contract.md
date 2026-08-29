# Table Overflow Discoverability and WEPP Slope Display Contract

**Status**: Implemented and locally validated 2026-08-29
**Decision provenance**: `A11Y-TABLE-20260829-1`
**Authorized**: 2026-08-29 UTC by the WEPPcloud operator

## Scope

This contract owns two finite Pure UI presentation behaviors:

1. discoverability and keyboard access for horizontally overflowing elements
   that use the canonical `.wc-table-wrapper`; and
2. fixed three-decimal HTML presentation of the exact `Slope` column in the
   Hillslope Summary and Channel Summary tables rendered by
   `reports/wepp/summary.htm`.

It does not own table dimensions, wrapping, data, sorting, model output, report
objects, CSV output, routes, persistence, or tables outside the canonical
wrapper.

## Overflow Eligibility and Behavior

A wrapper is eligible only when it contains a descendant `table`, has a
positive `clientWidth`, and `scrollWidth > clientWidth + 1`. The one-pixel
tolerance prevents fractional layout noise from adding an unstable focus stop.
An absent wrapper, hidden or zero-width wrapper, or wrapper without a table is
an expected no-op.

While eligible overflow exists, shared Pure UI behavior must:

- insert one visible instruction immediately before the wrapper stating that
  more columns are available and naming horizontal scroll, Shift plus mouse
  wheel, and focus followed by Left/Right Arrow;
- make the wrapper sequentially focusable by adding `tabindex="0"` only when
  the wrapper has no authored `tabindex`;
- add `role="region"` only when no authored `role` exists;
- preserve a usable authored accessible name. Evaluate `aria-labelledby` first:
  it is usable when at least one listed ID resolves to an element with non-empty
  trimmed text. Otherwise use a non-empty trimmed authored `aria-label` when
  present. If either authored attribute exists but neither is usable, preserve
  both and generate neither a role nor a name. Only when neither accessible-name
  attribute is authored, generate an `aria-label` from, in order, the table's
  non-empty caption, the nearest ancestor section's first non-empty heading, or
  `Scrollable data table`;
- append the generated hint ID to `aria-describedby` without removing or
  reordering authored description IDs; and
- expose an obvious focus-visible outline using the shared AA-validated accent
  token.

The behavior must re-evaluate registered wrappers after relevant size changes
and must register wrappers inserted dynamically. It must be idempotent.

When eligibility ends, the behavior must remove the generated hint and only
attributes or attribute tokens it owns. It must not remove an authored
`tabindex`, `role`, usable accessible name, or description ID. If an authored or other
runtime value replaces a generated value, cleanup leaves the replacement
intact. When one or both authored accessible-name attributes exist but neither
is usable under the precedence rule above, preserve them, do not add a generated
role or name, and still permit the generated focus stop and description. This
avoids a nameless generated region without overwriting malformed authored
semantics.
Observation APIs are progressive enhancement: when unavailable,
initial synchronization and an explicit shared refresh method remain usable.

## Input Behavior

The focused wrapper relies on native browser horizontal scrolling. The shared
behavior does not intercept or synthesize Arrow, wheel, touch, or trackpad
events. Rendered-browser acceptance must demonstrate horizontal movement from
Right Arrow and Shift plus mouse wheel on the supported Playwright browser.
Instructions do not promise that every operating-system input setting behaves
identically.

## WEPP Loss Summary Slope Precision

In the HTML Hillslope Summary and Channel Summary tables, a numeric value whose
current report header is exactly `Slope` must render in fixed-point notation
with exactly three digits after the decimal point. This includes zero and
trailing zeros. Missing values retain the existing em dash.

The formatter must select by exact header identity, not by the shared `ratio`
unit, because other ratio-valued columns retain their existing presentation.
The raw numeric value remains the sortable key. The report object, stored and
model values, outlet table, other columns, and server-generated CSV remain
unchanged. This is display formatting, not scientific parameterization.

## State and Compatibility Matrix

- No wrapper: no-op.
- Fitting, hidden, or zero-width wrapper: no hint or generated tab stop.
- Overflowing wrapper with table: one hint and generated semantics as needed.
- Overflow starts or ends after size change: generated state synchronizes.
- Wrapper added dynamically: it is registered once and synchronized.
- Authored focus or ARIA semantics: preserved according to the precedence and
  ownership rules above.
- Empty or broken authored accessible-name reference: no generated region or
  name; authored values remain intact, while hint and focus behavior may apply.
- Both name attributes present: usable `aria-labelledby` takes precedence;
  otherwise a usable `aria-label` applies; only the neither-usable combination
  suppresses generated role/name.
- Wrapper without a table: no-op even if another descendant is wide.
- Numeric `Slope`, zero `Slope`, and missing `Slope`: fixed three decimals,
  fixed three decimals, and em dash respectively in both requested tables.
- Non-slope ratio value: existing presentation remains unchanged.

No supported legacy table loses native overflow. The enhancement adds no
request, auth, storage, persistence, or execution failure visible to users.

## Required Evidence

Conformance requires deterministic unit tests for eligibility, lifecycle,
idempotence, dynamic insertion, every both-present accessible-name precedence
combination, and attribute-token ownership. Direct template rendering must cover numeric, zero, and missing
slope values in both tables, a non-slope ratio value, raw sort keys, and
unchanged CSV wiring.

A real-browser test must verify the visible hint, Tab reachability,
focus-visible style, Right Arrow movement, Shift-wheel movement, and absence of
document-level horizontal overflow. It must exercise the wrapper focus state in
every AA-validated theme (`default`, `light-high-contrast`, `ayu-mirage`,
`ayu-mirage-bordered`, and `cursor-dark-midnight`) and verify a nonzero visible
outline whose color resolves to the shared accent token. A focused Axe scan plus
200-percent zoom/narrow viewport check must report no new accessibility
violation.

## Rationale

Native scrollbars can be hidden by platform policy, so overflow alone does not
communicate that more columns or horizontal input methods exist. Activating
only on measured overflow avoids misleading instructions and unnecessary tab
stops. One shared behavior prevents report-by-report drift. Exact-header slope
formatting satisfies the requested readability change without altering data or
unrelated ratios.
