# Independent correctness contract review

Reviewer: `/root/contract_correctness` (reviewer agent), read-only.
Date: 2026-11-16 06:27 UTC. Base: df8b5249c70a3d98fd27f2b3b3b16ac1d96deb52.
Reviewed contract: docs/schemas/batch-outcome-contract.md.
SHA-256: 42d00a1931ea77e862412349ff91414bfae47d3dc33dd57faf0eb6ac7f8fed92.
Related: 20261116_inventory.md and 20261116_contract_security_review.md.

## User outcome and valid states

Deliver successful siblings despite timeout; keep leaf diagnostics and consistent
metrics/geometry. Review covered absent/legacy, empty, populated partial/full,
prep-only, optional modules, malformed identity, retry, explicit finalize,
cancellation, publication failure and restore. Directive cases remain separate
from stored-state cases. The inventory records confirmed consumers and gaps.

## Findings and author disposition

| Finding | Severity | Resolution in reviewed proposal |
| --- | --- | --- |
| Successful leaf identity expires before long sibling timeout | High | Required leaf and Omni records retain execution evidence through explicit cleanup |
| Strict Omni descendants strand batch finalization | High | Named worker/polling recovery triggers, bounded same-attempt graph validation/cancellation, preserved batch finalizer, atomic state checks |
| Ordinary artifact shape undefined | High | Baseline WEPP derivative only; WATAR/Omni keep existing download surfaces; exact operator ratification required |
| Polling writes unspecified | Medium | Explicit narrow reconciliation exception, nonblocking lease and canonical 503 |
| Automatic retry prematurely settles | Medium | Retry-eligible failures remain unsettled |
| Prep-only count/reason ambiguous | Medium | Skipped/no_result_outputs; ordinary execution completion unchanged |
| Restart rejects available partial result | Medium | Resume probe adopts batch outcome as well as polling loop |
| Standalone finalize identity absent | Medium | New publication attempt with frozen source receipts and retry fencing |

Primary author disposition: all findings accepted and incorporated. Independent
post-fix reviewer confirmed no remaining high/medium design findings at the
recorded hash. No findings are waived or treated as runtime verification.

## Verdict and pending evidence

Pass as a technical candidate for operator ratification only. No implementation
or release approval. Operator ratification and standalone ancestor commit remain.

Evidence chain is a proposed acceptance plan, not executed proof: real RQ timeout
with successful siblings; both HTTP polling endpoints; semantic downloaded ZIP
readback; real failed Omni scenario; delayed finalization beyond default result
expiry; publication failure/finalizer death; retry/cancellation races; normal
inspection and archive/restore; actual external-client resume and consistent
metrics/geometry filtering. Runtime tests were not performed in this review.
