# SBS-A11Y-02 Promoted-Contract Checkpoint Disposition

**Date**: 2026-08-25 UTC  
**Status**: Approved; no unresolved high/medium findings

## Policy Decision

The operator established that closed work packages are transient to their time
and place of execution. Durable governance must be promoted outside
`docs/work-packages/`; later work amends the promoted contract and never reopens
the closed package. The contract-first standard, root agent guidance, and work-
package closure process now state that rule. SBS behavior is promoted to
`docs/ui-docs/contracts/sbs-display-transport-contract.md`.

## Correctness Review Disposition

| Finding | Disposition |
| --- | --- |
| Historical compatibility remained contradictory | Fixed. The state matrix separates known endpoints, current color-table missing assignments, and pre-2018 classified between-break values. The latter is consistently an approved conservative loss. |
| JavaScript ownership was not implementable | Fixed. One definition is required per separate runtime boundary: Python server, run-page classic bundle, and Dashboard ES modules, with parity tests. No shared loading path is introduced. |
| Sentinel analysis restated a withdrawn opacity referral | Fixed. The stale superseded section was removed; `#800098` is explicitly the operator-selected `8.07` candidate and `#5000A0` the `9.97` alternative. |
| Review and approval status was stale | Fixed. ADR-0045 and compatibility are approved; two post-fix reviews and the checkpoint ancestor are the only remaining gates. |

## Security and Scope Review Disposition

| Finding | Disposition |
| --- | --- |
| Compatibility and status contradictions | Fixed as above. |
| Browser availability evidence was not measurable | Fixed. Both clients and modes benchmark a deterministic 4096 by 4096 RGBA input; median of five post-warm-up runs must be at most 1.25 times the current shifted decoder baseline in the same process, with memory bounded to source plus one destination canvas. |
| GDAL evidence did not map to real producer paths | Fixed. The promoted contract names Disturbed color-table, Disturbed breaks, and BAER class-map paths and their specific opacity/NoData/out-of-range obligations. |
| Route scope wording was inaccurate | Fixed. The route serves the raster but its behavior is unchanged and any authorization remediation is separately scoped. |

Both independent reviewers confirmed that no unresolved high/medium finding
remains. Review artifacts:

- `2026-08-25_promoted_contract_review.md`
- `2026-08-25_promoted_security_scope_review.md`

No production implementation may begin until this checkpoint is committed as a
standalone ancestor and its revision is recorded in the tracker.
