# Independent contract reviews

Reviewed before production edits on 2026-09-11, starting source `0c34afdb5`.

## Correctness — /root/contract_correctness (reviewer)

- COR-C01, medium: cancellation/finalizer behavior ambiguous. Resolved by
  distinguishing explicit tree cancellation (no success trigger, finalizer
  canceled) from unexpected worker failure (gated observer/finalizer release).
- COR-C02, medium: runtime-state matrix missing. Resolved with explicit matrix,
  separate directives, and identity-versus-receipt error policy.
- Re-review: approved; no unresolved high/medium findings. Real RQ must exercise
  STOPPED/FAILED transitions and fast leaves/Omni publication ordering.

## Security — /root/contract_security (security_reviewer)

- CS-01, medium: failure handler could write a foreign run. Resolved by requiring
  independently validated task identity before any run-tree write; unauthorized
  identity receives job-local diagnostics only.
- CS-02, medium: incomplete state matrix. Resolved with present-empty optional
  state and working/failed/completed/restored receipts with expected outcomes.
- Re-review: approved 2026-09-11 05:12 UTC; no unresolved high/medium findings.
  Confirmed strict root-to-stage-one publication barrier preserves approval.

## Disposition

All findings resolved through canonical contract amendments before implementation.
The root dispatch barrier ensures linkage exists before fast scientific/Omni
jobs run. Direct RQ, filesystem/cache, containment and archive/browser evidence
remain mandatory implementation gates. These approvals cover the contract
checkpoint only, not implementation or deployment acceptance.
