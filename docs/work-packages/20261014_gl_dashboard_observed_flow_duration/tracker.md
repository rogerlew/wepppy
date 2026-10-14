# Observed flow-duration tracker

Started: 2026-10-14 UTC. Phase: final validation. Security impact: high.

## Progress

Scaffold and canonical amendment prepared. Both independent reviews approved. Starting revision:
ebaed5a23cc9132424db90a38241f1e9f090fafc. Checkpoint ancestor: 4e02ee2e0.

## Decisions

User authorized scaffolding and execution, including the repository-required
checkpoint workflow. Scope is the Observed overlay only; no other active package
is being executed. Full-record, optional-off policy is in the canonical contract's
Observed streamflow overlay section and ADR-0093.

## Validation

Focused Python 34 passed; flow-duration Jest 24 passed; full frontend 986 passed; lint and docs pass.
Real-project readback and Chromium graph integration pass. Full Python is running.
Independent correctness and dedicated security reviews approve with zero unresolved
findings; see artifacts/20261014_correctness_review.md and
artifacts/20261014_security_review.md. Evidence: artifacts/validation.md.
No deployment claimed.
