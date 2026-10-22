# Roads modeled-area repair tracker

**Status**: Active — final broad-suite validation
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
- [ ] Complete broad gates and independent correctness/security reviews.

## Decisions

Roger's latest direction: “we should just keep the mofe footprint areas” and
“we don't see why we need to determine the geographic overlap”. Modeled-area
response mixing and expansion now govern. Geographic audit is retained as
research evidence only, not a dependency or input to implementation.

The scientific matrix is B=max(A-C,0), T=B+C for point sources; replacements use
full strip+remainder source areas without baseline. Source WAT areas govern
continuous ledgers; native PASS-header areas govern single storms. Product-specific
weights reconcile serialization. Original raw archives and baseline results remain.

Independent design reviews support this direction; final approvals must cover
the current contract, optional diagnostic support, derived cache readiness and
Roads-only compatibility for differing particle diameters. Earlier reviews of
geographic drafts are not approvals of the final checkpoint.

## Starting revisions and worktree boundary

WEPPpy `38df23fbf5696b9cc5b5cdbbd6f15fa297a5286e`;
wepppyo3 `3b630643ba06bd40262285f206112c9d3ee32b21`.
Native unrelated calendar/HBP edits and other preexisting changes are excluded
from task commits and explicitly disclosed if present in local build provenance.
Native implementation committed as `c941cb6`; WEPPpy integration and isolated UM1
validation pass. No deployment or in-place UM1 repair.

## Next action

Finish broad-suite rerun after updating the expected native hash; record results,
commit integration and close the plan. Both independent final reviews pass.
See [execution evidence](artifacts/20261022_execution_validation.md).
