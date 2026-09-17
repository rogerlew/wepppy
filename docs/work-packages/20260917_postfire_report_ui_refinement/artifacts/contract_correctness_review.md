# Contract correctness review: post-fire report UI refinement

## Metadata

- **Package:** `docs/work-packages/20260917_postfire_report_ui_refinement/`
- **Reviewer:** `/root/report_ui_contract_correctness`
- **Date:** 2026-09-17
- **Starting revision:** `4b14bcddb14cfe600a0194cb71743d41d33a5c26`
- **Scope:** Contract decision, active ExecPlan, post-fire report contract
  amendment, accessibility strategy amendment, current report template and
  controller, shared field macros, summary pane and theme CSS.
- **Canonical contracts:**
  `docs/ui-docs/contracts/postfire-debris-flow-report-contract.md` and
  `docs/ui-docs/controller-contract.md#established-presentation-conventions`.

## User outcome and compatibility

The requested outcome is represented correctly at a high level: Assessment
summary uses the existing definition-list summary pane; chart text paints in a
final SVG layer with a theme-token halo; and Storm events uses the existing
numeric/select/checkbox/button-row conventions without changing query or
scientific behavior. The final-label-layer approach is compatible with the
current SVG, and `--wc-color-text` against `--wc-color-surface` is the correct
theme-token pair. `numeric_field` already supplies a bounded 120-pixel numeric
control, while the preserved `data-pfr-field` hooks keep controller behavior
independent of generated form names.

No route, authorization, persistence, model, saved-result or artifact boundary
changes. Absent/error reports and the chart's textual no-data fallback remain
unchanged. Available current, stale, partial and supported legacy reports are
valid states for the new summary presentation. Filters retain blank, populated,
invalid, loading, empty-match, retry, reset and pagination states.

## Findings

| ID | Severity | Finding | Required disposition | Final status |
| --- | --- | --- | --- | --- |
| CCR-01 | Medium | The decision calls the UI style guide, theme system and accessibility strategy “applicable authority” and says the accessibility map receives a “normative amendment.” The contract-first standard's finite canonical set makes the post-fire report contract and shared controller contract authoritative here; the other documents are supporting guidance or an evidence map. | Split the decision into **canonical authority** (exact contract paths/sections) and **supporting guidance/evidence**. Describe the accessibility edit as an evidence-plan update rather than normative authority. | Resolved. The amended decision names the two canonical contracts separately and classifies the other documents as guidance/evidence. |
| CCR-02 | Medium | The accessibility addition sits under “Current Coverage (Already in Repo)” and says targeted validation “covers” the new behavior even though the report contract explicitly says implementation conformance is pending. This overstates current accessibility evidence. | Mark this report refinement and its validation as pending until retained checks pass, or place it in a pending-coverage section. Promote it to current coverage only at closeout. | Resolved. The item now lives under **Pending Targeted Remediation**, uses future validation language and states the promotion condition. |
| CCR-03 | Medium | “Responsive token-based spacing” is not an objectively testable answer to the user's reported tight vertical spacing. Any spacing token, including the current tight values, could satisfy that text. The regression line also does not explicitly exercise the rebuilt sort and descending controls. | Name the acceptance geometry: macro fields in a responsive grid/stack with at least `--wc-space-md` row gap, a canonical button row separated from fields, and narrow-width stacking without horizontal overflow. Require template/controller assertions for all four filter hooks, numeric ranges/steps, every sort option, descending checked/unchecked submission, Apply/Reset order and unchanged query encoding. | Resolved. The contract and decision now state the minimum gaps, bounded/reflow behavior and complete filter regression matrix. |
| CCR-04 | Low | The amendment requires a Notices term/definition but does not define the valid no-notice value. The current renderer produces an empty string, which would create an empty definition in the new pane. | State that no assessment-specific notices render as “None” (or another explicit neutral value); populated notices retain their full text. Add empty/populated notice assertions. | Resolved. The contract and state matrix require “None recorded.” for the empty state. |

## Accepted design details

- The summary-pane requirement matches the shared component's exact
  `wc-summary-pane` / `wc-summary-pane__list` / item / term / definition
  hierarchy.
- Rendering every visible SVG text node in a group appended after the response
  polyline, P50 mark and scenario circles directly addresses marker occlusion.
  The class should have a visible nonzero stroke and stroke-first paint order;
  default, dark and high-contrast computed-style plus visual checks are suitable
  evidence.
- Existing numeric/select/checkbox macros and `button_row` are the right
  conventions. Preserve `pfr-minimum`, `pfr-year`, `pfr-sort`, the four
  `data-pfr-field` values, percent range 0–100, decimal likelihood input,
  integral year input and DOM focus order.
- Keeping the interpretation paragraph immediately after the summary pane
  preserves the existing scientific caveat and report hierarchy.

## Verdict

- **Re-review date:** 2026-09-17
- **Gate status:** pass
- **Unresolved findings:** High 0; Medium 0; Low 0
- **Checkpoint recommendation:** approve the amended contract checkpoint for
  the required standalone ancestor commit. Production implementation remains
  pending and must conform to the stated rendered, controller and browser
  evidence matrix.

No implementation files were edited during this review.
