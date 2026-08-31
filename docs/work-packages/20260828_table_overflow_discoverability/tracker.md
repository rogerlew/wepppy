# Tracker – Table Overflow Discoverability

## Quick Status

**Timezone**: UTC
**Started**: 2026-08-29 01:25 UTC
**Current phase**: Closed
**Last updated**: 2026-08-29 02:16 UTC
**Next milestone**: None; package complete
**Security impact**: `none`
**Dedicated security review**: no
**Security artifact**: N/A

## Task Board

### Ready / Backlog

- None.

### In Progress

- None.

### Blocked

- None.

### Done

- [x] Inventory shared report/table rendering and current overflow behavior (2026-08-29 01:25 UTC).
- [x] Record operator authority and bounded behavior contract (2026-08-29 01:25 UTC).
- [x] Commit reviewed standalone checkpoint and verify ancestry (2026-08-29 02:04 UTC).
- [x] Implement shared overflow-only progressive enhancement (2026-08-29 02:05 UTC).
- [x] Implement exact three-decimal slope HTML display (2026-08-29 02:05 UTC).
- [x] Pass focused and broad validation gates (2026-08-29 02:05 UTC).
- [x] Resolve final-review findings and close the package (2026-08-29 02:16 UTC).

## Timeline

- **2026-08-29 01:25 UTC** – Package scaffolded at revision `75eb240c8dbf`.
- **2026-08-29 01:38 UTC** – Operator added exact three-decimal display for
  Hillslope Summary and Channel Summary slope values.
- **2026-08-29 01:42 UTC** – Initial independent reviews returned HOLD; the
  package added a finite canonical contract, exact lifecycle/ARIA rules, exact
  path and dirty-hunk controls, exact browser gates, and the slope delta.
- **2026-08-29 02:04 UTC** – Both corrected reviews were READY and standalone
  checkpoint `a1db47377033431e77b96a8bda2f3da8c3f5ab92` was committed.
- **2026-08-29 02:05 UTC** – Implementation and regression evidence completed;
  final independent correctness review started.
- **2026-08-29 02:16 UTC** – Final review READY with High 0, Medium 0, Low 0;
  generator-backed headers and first-nonempty-heading behavior verified.

## Decisions Log

### 2026-08-29 01:25 UTC: Shared overflow-only progressive enhancement

**Context**: Native horizontal scrolling exists, but hidden platform scrollbars
do not tell users that additional columns are available or how to reach them.

**Decision**: Enhance `.wc-table-wrapper` once at the shared Pure UI shell.
Only wrappers with measurable horizontal overflow receive instructions,
generated region semantics, and a generated keyboard stop. Re-evaluate after
layout or DOM changes. Preserve any authored accessibility attributes.

**Rationale**: A static hint on every table creates noise and unnecessary tab
stops. Per-template implementation would duplicate behavior and drift.

**Authority**: The operator explicitly directed scaffolding and execution and
stated that this instruction is authority; no additional ratification request
is required.

### 2026-08-29 01:38 UTC: Slope precision is display-only and column-specific

**Decision**: Format only HTML cells whose report header is exactly `Slope` in
the Hillslope Summary and Channel Summary tables with fixed-point three-decimal
formatting. Preserve the raw numeric `sorttable_customkey` and leave CSV routes,
report objects, other ratio-valued columns, and model artifacts unchanged.

**Rationale**: The operator requested presentation precision, not scientific
rounding or a data-contract change. Matching by exact report header avoids
changing unrelated ratio-valued metrics.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| Extra tab stops on fitting tables | Medium | Low | Activate only when `scrollWidth > clientWidth + 1` and test removal after resize | Open |
| Existing authored ARIA overwritten | Medium | Low | Track generated attributes and remove only generated values | Open |
| Shared-shell regression | Medium | Low | Dependency-free module, focused Jest and rendered-browser tests | Open |
| Dynamic tables miss enhancement | Low | Medium | Observe added wrappers and resized wrapper/table geometry | Open |

## Contract Review Disposition

- **A11Y-GOV-01 / A11Y-COR-01**: Resolved in the checkpoint candidate by adding
  `docs/ui-docs/contracts/table-overflow-discoverability-contract.md` and marking
  guide/implementation conformance pending.
- **A11Y-GOV-02 / A11Y-COR-05**: Resolved by exact checkpoint and implementation
  allowlists, explicit preexisting-path exclusions, and hunk-aware staging for
  the two overlapping documentation files.
- **A11Y-GOV-03**: Resolved by full-SHA ancestor verification, exact Playwright
  commands, the full Python gate or durable exception rationale, and a named
  final correctness artifact.
- **A11Y-COR-02**: Resolved by deterministic accessible-name precedence,
  authored-value precedence, token-level `aria-describedby` ownership, and
  generated-value cleanup rules in the canonical contract.
- **A11Y-COR-03**: Resolved with one eligibility predicate:
  `scrollWidth > clientWidth + 1`, positive width, and a descendant table;
  hidden, zero-width, absent, and malformed states are no-ops.
- **A11Y-COR-04**: Resolved by requiring rendered Right Arrow and Shift-wheel
  evidence plus theme-metrics validation of the shared focus token.
- **A11Y-COR-06**: Resolved by moving the package entry to In Progress.

Post-correction independent confirmation is READY with no findings.

## Verification Checklist

- [x] Focused Jest tests pass (`11 passed`).
- [x] Frontend lint and full Jest suite pass (`828 passed`).
- [x] Template/CSS contract tests pass (`162 passed`).
- [x] Rendered browser verifies overflow, hint, focus, Arrow, Shift-wheel, zoom,
  five AA themes, and no page overflow (`1 passed`).
- [x] Focused Axe scan reports no violations.
- [x] Full Python suite passes (`7279 passed, 63 skipped`).
- [x] Documentation lint passes for the checkpoint candidate.
- [x] `git diff --check` passes.
- [x] Independent correctness review passes (High 0, Medium 0, Low 0).
- [x] Operator verified the deployed hint, Tab reachability, Arrow scrolling,
  and Shift-wheel scrolling on Forest (2026-08-29).

## Progress Notes

### 2026-08-29 01:25 UTC: Discovery and scaffold

**Work completed**:

- Confirmed WEPP summary tables are handwritten but consistently wrapped.
- Confirmed the canonical wrapper already uses `overflow-x: auto`.
- Scoped the feature to discoverability and keyboard access, not clipping.
- Added the operator-requested, display-only slope precision boundary.

**Next steps**:

- None; the package is closed. Push, merge, and deployment remain outside scope.
