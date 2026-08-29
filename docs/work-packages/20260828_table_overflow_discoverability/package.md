# Table Overflow Discoverability

**Status**: Open (2026-08-29)
**Timezone**: UTC
**Initiative branch**: `feature/project-owned-config`
**Starting revision**: `75eb240c8dbffea6beb639c9707821d3d877ac2d`

## Overview

Wide report tables already scroll horizontally through the shared
`.wc-table-wrapper`, but that interaction can be invisible to users whose
platform hides scrollbars. This package makes horizontal overflow discoverable
and keyboard reachable without changing table data, column sizing, or report
layout. It also applies the operator-requested three-decimal HTML display
precision to slope values in the WEPP Loss Summary hillslope and channel tables.

## Objectives

- Enhance every overflowing `.wc-table-wrapper` through one shared behavior.
- Show concise instructions for mouse, trackpad, and keyboard navigation only
  while horizontal overflow exists.
- Give only overflowing wrappers an accessible, visibly focused keyboard stop.
- Preserve authored ARIA and focus attributes and leave non-overflowing tables
  unchanged.
- Prove behavior at initial load, resize/zoom, and dynamic table insertion.
- Render Hillslope Summary and Channel Summary `Slope` cells with exactly three
  decimal places while preserving raw numeric sort keys and CSV source data.

## Scope

### Included

- The canonical scrollproof-table pattern and shared accessibility guidance.
- A dependency-free shared browser module loaded by the Pure UI shell.
- Overflow-only instructions, focusability, accessible-region semantics, and
  lifecycle refresh behavior.
- Jest, template/CSS contract, and rendered-browser regression evidence.
- The HTML display formatting of the exact `Slope` column in the two named WEPP
  Loss Summary tables.

### Explicitly Out of Scope

- Fixing clipped columns or changing column widths, wrapping, or table data.
- Changing outlet values, other numeric columns, report objects, model output,
  stored values, or CSV downloads.
- Converting handwritten tables to a Jinja macro.
- Enhancing tables that do not use `.wc-table-wrapper`.
- Deployment, merge, or production changes.

## Stakeholders

- **Primary**: WEPPcloud report users, including mouse and keyboard users.
- **Reviewers**: Independent contract and final correctness reviewers.
- **Security reviewer**: Not required; no request, persistence, or trust boundary changes.

## Success Criteria

- [ ] An overflowing wrapper displays navigation instructions and can receive keyboard focus.
- [ ] Left and Right Arrow move the focused horizontal scroll region in a rendered browser.
- [ ] A non-overflowing wrapper has no generated hint, role, or tab stop.
- [ ] Authored `tabindex`, `role`, and accessible-description attributes are preserved.
- [ ] Behavior updates after viewport/zoom changes and dynamically added wrapped tables.
- [ ] Focused frontend, template, accessibility, and documentation gates pass.
- [ ] Hillslope and channel slope cells display trailing zeros to exactly three
  decimal places without changing sorting or CSV values.
- [ ] Independent correctness review has no unresolved medium/high findings.

## Parameterization ADR Gate

- **Parameterization change present**: no; this is HTML display formatting only
- **ADR required**: no
- **Decision provenance captured**: yes; operator authorization was given in
  conversation on 2026-08-29 UTC.

## Security Impact and Review Gate

- **Security impact triage**: none
- **Dedicated security review required**: no
- **Triage rationale**: local DOM presentation and keyboard behavior only; no
  auth, input, network, storage, execution, or authorization surface changes.

## References

- `docs/ui-docs/ui-style-guide.md#pattern-5-scrollproof-data-table`
- `docs/ui-docs/contracts/table-overflow-discoverability-contract.md`
- `docs/ui-docs/accessiblity.md`
- `docs/standards/contract-first-change-standard.md`
- `wepppy/weppcloud/static/css/ui-foundation.css`
- `wepppy/weppcloud/templates/base_pure.htm`

## Deliverables

- Shared table-overflow accessibility module and styling.
- Regression tests and rendered-browser evidence.
- Completed work-package tracker, execution plan, decision, and review artifacts.
