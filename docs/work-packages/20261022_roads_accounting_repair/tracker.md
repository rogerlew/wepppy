# Roads modeled-area repair tracker

**Status**: Closed 2026-10-22 — local implementation and validation
**Date / timezone**: 2026-10-22 UTC

## Progress

- [x] Scaffold package and reproduce the report-input defects.
- [x] Obtain task-scoped commit and expanded implementation authority.
- [x] Record latest modeled-MOFE policy; remove geographic allocation requirement.
- [x] Draft canonical contract, ADR-0102 and related contract amendments.
- [x] Obtain final two independent approvals and disposition findings.
- [x] Commit standalone contract ancestor `83f7410e8`.
- [x] Implement native Roads weighted PASS, source-aware water accounting and release.
- [x] Integrate WEPPpy before routing, aggregate reports and cache provenance.
- [x] Validate scratch UM1 fresh routing and full-record reports.
- [x] Complete broad gates with retained environment/stubtest limitations and independent reviews.

## Decisions

Roger's latest direction: “we should just keep the mofe footprint areas” and
“we don't see why we need to determine the geographic overlap”. Modeled-area
response mixing and expansion now govern. Geographic audit is retained as
research evidence only, not a dependency or input to implementation.

The scientific matrix is B=max(A-C,0), T=B+C for point sources; replacements use
full strip+remainder source areas without baseline. Source WAT areas govern
continuous ledgers; native PASS-header areas govern single storms. Product-specific
weights reconcile serialization. Original raw archives and baseline results remain.

Both final contract reviews and both final implementation reviews passed. They
cover optional support weighting, cache readiness and Roads-only particle-header
compatibility. Geographic drafts do not govern the final implementation.

## Starting revisions and worktree boundary

WEPPpy `38df23fbf5696b9cc5b5cdbbd6f15fa297a5286e`;
wepppyo3 `3b630643ba06bd40262285f206112c9d3ee32b21`.
Native unrelated calendar/HBP edits and other preexisting changes are excluded
from task commits and explicitly disclosed if present in local build provenance.
Native implementation committed as `c941cb6`; WEPPpy integration committed as
`cf3043781`; isolated UM1 validation passes. No deployment or in-place UM1 repair.

## Closeout

All scoped implementation milestones are complete. Full-suite run: 10,883 passed,
126 skipped, then unrelated Chromium-path failure; corrected-path remainder:
183 passed. This is segmented validation. Existing OutputScope stubtest alias
limitation remains. Both independent reviews pass. No deployment or original-run
repair. See [execution evidence](artifacts/20261022_execution_validation.md) for
follow-ups and exact completion limits.
