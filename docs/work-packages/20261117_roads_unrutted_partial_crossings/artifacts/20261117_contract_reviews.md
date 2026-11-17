# RUPC-01 independent contract reviews

Date: 2026-11-17 (UTC). Scope: proposed strip contract, ADR-0146, related contracts,
work package and existing implementation. Both reviewers were read-only and did
not author the contract. Exact formula approval remains pending.

## Review A — reviewer agent `/root/contract_review_a`

Initial verdict: hold. Findings and disposition:

| Finding | Severity | Disposition |
| --- | --- | --- |
| Consumed area/rounding and tiny remainder policy undefined | High | Twelve-place dimensions, parsed positive dimensions and 1e-6 m² input closure; explicit retained small-remainder absorption and native WAT/PASS reconciliation. |
| Optional coalescing violates subdivision invariance | High | Mandatory exact connected-component union before eligibility and cap; deterministic geometry tie-break; no endpoint snapping. |
| Additive artifact schema unspecified | Medium | Named fields, units, record locations, null/error status and included/excluded road-area totals. |
| No-road control acceptance unspecified/confounded | Medium | Actual original baseline parameterization, two half-width profiles; annual/total runoff and sediment differences are diagnostics; geometry and correct aggregation remain gates. |

Post-fix confirmation: **pass**. Reviewer A confirmed A1–A4 closed with no
remaining medium/high findings. No implementation evidence claimed.

## Review B — security reviewer agent `/root/contract_review_b`

Initial verdict: hold. All three medium findings were resolved and the reviewer
confirmed **pass**, with no remaining medium/high findings:

| Finding | Resolution |
| --- | --- |
| Zero-contributor failure conflicts with water-accounting authority | Added missing canonical contract and cross-link; preserve valid empty baseline-equivalent success, fail attempted invalid contributors. |
| Optional coalescing preserves input segmentation dependence | Mandatory normalization and explicit connectivity/duplicate/tie-break rules. |
| Consumed geometry boundary undefined | Defined positivity/precision/absolute readback gate; preserve WAT/PASS accounting semantics. |

Reviewer requested alignment of acceptance matrix and decision draft; both updated.
High security triage remains appropriate for future native/file handling. This is
contract approval only; no runtime, containment or implementation review completed.
