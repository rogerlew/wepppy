# Independent contract correctness review

Reviewer: `/root/adr_contract_correctness` (reviewer agent). Date: 2026-11-05 UTC.
Read-only review of checkpoint, proposed specification and existing source.

## Findings

1. Medium: numeric order differs from chronology in current files. ADR-0028
   GridMET is dated 2026-08-31, while ADR-0029 is dated 2026-07-28. Explicitly
   resolve the pending ordering preference rather than claiming equivalence.
2. Medium: existing Link Resolution says all non-manifest Markdown targets use
   `/usersum/src/`; amend it for ADRs and state manifest precedence.
3. Low: relative-link language could promise new PDF/asset behavior unsupported
   by the existing Markdown-only rewriter. Clarify the bounded behavior.

Otherwise the bounded approach, complete inclusion, duplicate handling, legacy
metadata behavior, request freshness and real-filesystem/HTML validation are sound.
Approval is pending finding disposition and the mandatory ancestor checkpoint.

## Follow-up confirmation

The reviewer confirmed findings 2 and 3 closed after the link/asset amendments.
After the date-order revision, finding 1 is also closed: validated explicit dates
descending, visible missing/invalid dates last, deterministic ties satisfy the
requested chronology without invented metadata. Revised contract approved with
no blocking findings. Implementation must still test supported date formats,
ADR-0028/0029 inversion, duplicate IDs and rendered navigation. No runtime tests
were performed by this contract review.
