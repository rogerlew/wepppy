# Contract accessibility and noninterference review

Reviewer: `/root/report_ui_contract_accessibility`
Review mode: independent, read-only contract review
Date: 2026-09-17 UTC
Starting implementation: `4b14bcddb`

## Scope

I reviewed the proposed presentation amendment in
`docs/ui-docs/contracts/postfire-debris-flow-report-contract.md`, the matching
contract decision and ExecPlan, the shared accessibility strategy, and the
existing report template, controller, field macros, summary-pane styles and
controller tests. The review covers semantic structure, keyboard and pointer
noninterference, theme compatibility, valid report states, hostile text
handling and the proposed regression evidence. It does not approve an
implementation or deployment.

## Findings

### PFUI-CAR-01 — Medium — final SVG labels can intercept marker activation

Painting every label after the P50 and scenario markers solves visual
occlusion, but it also makes the label the pointer hit target wherever the
label overlaps a marker. The current delegated click handler responds only to
`[data-pfr-scenario]`; an overlaid SVG `text` or label-layer `g` has no such
hook. The proposed contract does not require the final visual label layer to
ignore pointer input, so the fix can make a visible marker unclickable at the
same overlap the operator asked to correct.

Required disposition: amend the canonical requirement and checkpoint to make
the final visual label layer noninteractive, for example with
`pointer-events: none`, while leaving each scenario marker and P50 element
focusable and named. Retain a real-browser regression that checks an
overlapping label/marker point selects the marker with a pointer, and that Tab
plus Enter/Space still selects the same scenario. A jsdom `.click()` called
directly on the circle is not evidence for browser hit testing.

Status: resolved in the amended canonical contract, checkpoint and ExecPlan.

### PFUI-CAR-02 — Low — halo geometry is not yet testable

The text/surface token pair and `paint-order` are theme-compatible, but the
contract does not state a stroke width. SVG's default one-unit stroke can be
too slight to separate text from a same-color response line or marker after
responsive scaling.

Required disposition: specify a deliberate label-halo width and rounded join
(for example `stroke-width: 3px` and `stroke-linejoin: round`) and verify the
computed token-backed fill, stroke, width and paint order in the rendered
chart. The planned default, dark and light-high-contrast browser views should
confirm the halo remains legible without hard-coded light/dark colors.

Status: resolved in the amended canonical contract, checkpoint and ExecPlan.

### PFUI-CAR-03 — Low — empty notices need a semantic value

The proposed `wc-summary-pane` structure is appropriate: a `dl` containing
paired `dt` and `dd` rows preserves label/value relationships. In the common
state where the accepted assessment has no notice, however, the existing
renderer produces an empty string. Moving that value into a definition row
would leave “Notices” with an empty definition.

Required disposition: define the no-notice value as explicit text such as
“None recorded.” Keep legacy unavailable values as “Not recorded” and keep
currentness, coverage and warning explanations as text rather than status
communicated by color alone.

Status: resolved in the amended canonical contract and checkpoint.

## Confirmed compatibility and security properties

- `wc-summary-pane` uses native definition-list semantics and theme tokens.
  Separate rows for model, completed time, watershed area, currentness,
  coverage and notices satisfy the proposed information structure without
  changing assessment authority.
- `numeric_field`, `select_field`, `checkbox_field` and `button_row` provide
  explicit labels, native controls, focus styling and bounded numeric widths.
  Their `attrs` path can preserve every existing `data-pfr-field`, range,
  step and described-by hook. Keeping the current source order preserves
  keyboard order and Enter-to-submit behavior.
- Blank, populated, browser-invalid and reset filter states can keep their
  existing query behavior. Available, stale, partial and legacy result states
  can share the new presentation, while absent/error states remain outside the
  results container.
- The proposed work adds no endpoint, model, query, persistence, download or
  authorization behavior. Server-derived values remain assigned with
  `textContent`; shared macros add only static authored labels and attributes.
  I found no new injection, disclosure or cross-run access surface.
- The saved-results tables continue to provide the numeric alternative to the
  chart, and marker accessible names remain independent of visual text.

## Required regression evidence

In addition to the package's existing test plan, implementation acceptance
should retain:

1. actual rendered-template assertions for one `wc-summary-pane` `dl`, paired
   terms/definitions, explicit no-notice text, macro-generated labels and
   unchanged IDs/data hooks/ranges;
2. controller tests for current, stale, legacy/no-coverage, warning and
   no-warning summaries plus blank, populated, invalid and reset filters;
3. SVG structure/style checks proving data marks precede the final visual
   label layer and the label class uses text/surface tokens, explicit halo
   geometry, paint order and pointer noninterference;
4. a real-browser pointer hit test at an intentional label/marker overlap,
   keyboard marker selection and visible focus, and axe over the populated
   report; and
5. default, dark and light-high-contrast views at desktop and narrow widths,
   including long warning text and the Storm events filter reflow.

## Post-fix confirmation

I re-reviewed the amended checkpoint on 2026-09-17 UTC. The canonical report
contract now requires the final label layer to be pointer-transparent, retains
pointer and keyboard selection, and requires a three-pixel rounded
theme-token halo. The decision artifact and ExecPlan carry the same geometry
and noninterference requirements. The regression plan now includes a
real-browser hit test at an intentional overlap plus Tab, Enter and Space
selection; it does not substitute a direct jsdom circle click for browser hit
testing. PFUI-CAR-01 and PFUI-CAR-02 are therefore closed.

The contract and checkpoint also require the no-notice summary definition to
read “None recorded.” PFUI-CAR-03 is closed. The accessibility strategy now
accurately lists this work as pending targeted remediation rather than current
coverage, so the documentation does not claim evidence before implementation.

## Verdict

The amended contract checkpoint **passes** this accessibility, theme,
security and noninterference review with zero unresolved High, Medium or Low
findings. It is approved for the standalone documentation checkpoint commit
and subsequent implementation. This approval covers intended behavior and the
evidence plan only; production implementation, browser evidence and deployment
remain unreviewed.
