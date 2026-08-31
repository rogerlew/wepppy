# Correctness and Accessibility Contract Review - Table Overflow Discoverability

## Metadata

- **Package**:
  `docs/work-packages/20260828_table_overflow_discoverability/`
- **Decision**: `A11Y-TABLE-20260829-1`
- **Reviewer**: Codex independent correctness/accessibility reviewer
- **Date**: 2026-08-29
- **Scope reviewed**: package, decision, tracker, active ExecPlan, dedicated
  canonical contract, synchronized table/accessibility guidance,
  project-tracker delta, shared wrapper CSS, Pure UI shell, WEPP Loss Summary
  template, observed wrapper consumers, and proposed evidence paths
- **Starting revision**: `75eb240c8dbffea6beb639c9707821d3d877ac2d`
- **Canonical contract**:
  `docs/ui-docs/contracts/table-overflow-discoverability-contract.md`
- **Synchronized guidance**: `docs/ui-docs/ui-style-guide.md`, Pattern #5, and
  `docs/ui-docs/accessiblity.md`, section 8
- **Security review**: not required; the proposed local DOM enhancement creates
  no request, persistence, execution, or trust boundary

## User Outcome

- **User goal**: discover and navigate columns that extend beyond a table's
  visible horizontal viewport.
- **Success presented to the user as**: only an actually overflowing wrapper
  displays accurate instructions, enters the applicable keyboard focus order,
  has meaningful accessible semantics, and retains a visible focus indicator.
- **Failures that may reach the user**: a false-positive hint/tab stop, an
  undetected overflow, misleading navigation instructions, a nameless or
  conflicting ARIA region, or removal of author-owned attributes.
- **Partial-state behavior**: refresh and cleanup must leave table content and
  layout unchanged and remove only module-owned hint/attributes.
- **Additional presentation goal**: render the exact `Slope` column in the
  Hillslope Summary and Channel Summary HTML tables with three fixed decimal
  places without changing raw sort keys, report values, or CSV output.

## Valid-State Matrix

| State | Valid? | Required behavior | Proposed evidence |
| --- | --- | --- | --- |
| No `.wc-table-wrapper` | yes | No-op without an exception or observer leak | Jest absent-state case |
| Wrapper fits | yes | No generated hint, role, description, or tab stop | Jest plus rendered fitting fixture |
| Wrapper exceeds `clientWidth + 1` and contains a table | yes | Hint, deterministic semantics/focus policy, and visible focus | Jest plus rendered overflowing fixture |
| Overflow appears or disappears after resize/zoom/content change | yes | Synchronize once; preserve author-owned state | Resize/content and 200-percent evidence |
| Wrapper inserted dynamically | yes | Register and synchronize without duplicate observers/hints | Mutation/idempotence Jest evidence |
| Authored focus/ARIA attributes | yes | Apply `aria-labelledby`, then `aria-label`, then generated-name precedence; preserve attribute/token ownership | Per-attribute, both-present, malformed-name, and transition Jest evidence |
| Wrapper hidden or zero-width, then revealed | yes | Do not create a false positive; synchronize when measurable | Eligibility and resize evidence |
| Wrapper without a table or with malformed descendants | supported no-op | No generated state and no exception | Jest malformed-state case |
| Numeric or zero `Slope` in either named table | yes | Exactly three decimal places, including trailing zeros | Direct rendering of both tables |
| Missing `Slope` in either named table | yes | Existing em dash | Direct rendering of both tables |
| Non-slope ratio, outlet value, raw sort key, or CSV wiring | yes | Existing presentation/data remains unchanged | Direct render/source-wiring assertions |

## User-Reachable Error Policy

| Condition | Expected or exceptional? | User-visible result | Contract status |
| --- | --- | --- | --- |
| Browser lacks observation APIs | supported legacy | Initial enhancement works; explicit refresh remains usable | ExecPlan lines 145-152 |
| Authored focus or ARIA policy conflicts with generated region behavior | expected composition state | Preserve authored policy; suppress generated role/name when both authored name sources are unusable | Canonical lines 37-44 and 53-63 |
| One-pixel geometry difference | expected measurement state | No enhancement until `scrollWidth > clientWidth + 1` | Canonical lines 23-27 |
| Malformed wrapper | supported no-op | No hint, tab stop, semantics, or exception | Canonical lines 23-27 and 94-101 |

## Review Checks

- [x] Operator authority explicitly approves scaffolding and execution without a
  second ratification request.
- [x] Overflow-only behavior and non-overflow cleanup are approved.
- [x] Canonical documents distinguish intended behavior from pending
  implementation conformance.
- [x] Generated region naming/description and authored-attribute precedence are
  deterministic for every valid combination.
- [x] Overflow and malformed-wrapper predicates are identical across the
  canonical contract, decision, tracker, and ExecPlan.
- [x] Evidence directly exercises every user-facing navigation instruction and
  the focus indicator across the applicable conformance presentation states.
- [x] The exact implementation/test paths and mixed-dirty documentation hunks
  are bounded for standalone checkpoint staging.
- [x] No table values, widths, wrapping, sorting, links, forms, downloads,
  persistence, routes, or backend behavior are authorized to change.
- [x] The HTML-only slope formatter is selected by exact header identity and
  preserves raw sort keys, report/model state, outlet/other columns, and CSV.

## Findings

| ID | Severity | User/state surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| TABLE-COR-01 | Medium | Canonical conformance state | A dedicated finite-set contract now owns the exact behavior and marks implementation conformance pending. Both guidance files use accepted/future wording and link to that contract without claiming deployed evidence. | Canonical lines 1-19; `docs/ui-docs/ui-style-guide.md:365-372`; `docs/ui-docs/accessiblity.md:173-185` | No further contract action. | Resolved |
| TABLE-COR-02 | Medium | Accessible name, role, focus, and authored attributes | The canonical contract now defines generated role/name/description behavior, exact `aria-labelledby` then `aria-label` precedence, the neither-authored fallback, the both-authored usable/unusable matrix, malformed-name suppression of generated role/name, and generated value/token cleanup. Both-present combinations and ownership transitions are required evidence. | Canonical lines 29-63 and 90-115 | No further contract action. Implement and execute every named combination after the checkpoint. | Resolved |
| TABLE-COR-03 | Medium | Overflow boundary and malformed/hidden wrappers | Every authoritative/executable source now uses descendant-table eligibility, positive width, and `scrollWidth > clientWidth + 1`; equal, one-pixel, hidden/zero-width, no-table, and transition states are explicitly testable outcomes. | Canonical lines 21-27 and 86-104; tracker lines 78-101; ExecPlan lines 72-76 and 171-181 | No further contract action. | Resolved |
| TABLE-COR-04 | Medium | Navigation and focus evidence | The canonical contract and acceptance plan require direct Right Arrow and Shift-wheel movement, focus-state evidence in all five named AA-validated themes, Axe, zoom/reflow, and no document overflow. The focused spec has an executable `--playwright-args` command accepted by `wctl run-playwright`. | Canonical lines 65-70 and 111-123; decision lines 96-107; ExecPlan lines 139-181 | No further contract action. Runtime evidence remains required. | Resolved |
| TABLE-COR-05 | Medium | Checkpoint and implementation containment | The decision now registers exact checkpoint and implementation allowlists, final review path, every preexisting dirty exclusion, the two mixed-file hunk exclusions, hunk-aware staging, cached-diff comparison, full-SHA recording, and ancestor verification before implementation. | Decision lines 108-169; ExecPlan lines 78-89 and 122-158 | No further contract action. Path-stage and verify exactly as specified. | Resolved |
| TABLE-COR-06 | Low | Project discovery | The package entry is now in In Progress and the WIP header count is updated to 26. | `PROJECT_TRACKER.md:37-40`, `406-429` | No further action. | Resolved |

## Verdict

- **Gate status**: `pass`
- **Unresolved findings**: High 0; Medium 0; Low 0
- **Release recommendation**: `checkpoint-ready`
- **Reviewer sign-off**: Codex independent correctness/accessibility reviewer,
  2026-08-29

The corrected contract checkpoint is **READY**. The operator's exact authority
covers both the overflow enhancement and the later HTML-only slope-display
addition; no further ratification should be requested. TABLE-COR-01 through
TABLE-COR-06 are resolved, and no High, Medium, or Low finding remains.

The worktree remains at starting revision
`75eb240c8dbffea6beb639c9707821d3d877ac2d`. None of the exact implementation or
test paths has changed from that revision. Regression evidence is necessarily
prospective: implementation may begin only after the reviewed, hunk-contained
documentation checkpoint is committed, its full SHA is recorded, and that SHA
is verified as an ancestor.
