# Source Snapshot

## Snapshot Metadata

| Field | Value |
| --- | --- |
| Issue date | March 31, 2026 |
| Repository snapshot | `bb0fbb1cb` |
| Intended final artifact | `VPAT 2.5Rev INT` |
| Template version | April 2025 |
| Current worksheet source at time of issue | `docs/ui-docs/acr-draft-int.md` |
| Current strategy source at time of issue | `docs/ui-docs/accessiblity.md` |
| Current manual pass source at time of issue | `docs/ui-docs/manual-at-pass-20260331.md` |
| Deployment posture at time of issue | Refresh the staging package before production deployment if any tracked conformance trigger changes |

## Closed Decisions Frozen In This Package

- Conformance baseline is limited to the AA-validated theme set.
- Sensory-preference themes remain user-visible in federal-buyer deployments as supplemental user-choice themes outside the conformance set.
- The manual-evidence boundary for this issue is the documented local browser / operating system / assistive-technology matrix rather than a separate spoken screen-reader matrix.

## Remaining Transfer Work

1. Freeze evaluator identity / responsible team more explicitly in future issues if buyer workflow requires named evaluator metadata beyond the current project contact.
2. Expand row-level EN 301 549 detail in a future revision if a buyer requests more granularity than the summary-table method used here.
3. Confirm support workflow accessibility and alternate-format handling in a future issue if those services become part of a tighter procurement scope.
