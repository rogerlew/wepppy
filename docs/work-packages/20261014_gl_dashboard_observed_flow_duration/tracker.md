# Observed flow-duration tracker

Started: 2026-10-14 UTC. Phase: closed (local implementation and validation). Security impact: high.

## Progress

Scaffold, canonical amendment and implementation complete. Both independent reviews approved. Starting revision:
ebaed5a23cc9132424db90a38241f1e9f090fafc. Checkpoint ancestor: 4e02ee2e0. Implementation commit: 4969c7323.

## Decisions

User authorized scaffolding and execution, including the repository-required
checkpoint workflow. Scope is the Observed overlay only; no other active package
is being executed. Full-record, optional-off policy is in the canonical contract's
Observed streamflow overlay section and ADR-0093.

## Validation

Focused Python 34 passed; flow-duration Jest 24 passed; full frontend 986 passed; lint and docs pass.
Real-project readback and Chromium graph integration pass. Full Python passed: 10,812 tests, 126 skipped in 48m02s.
Independent correctness and dedicated security reviews approve with zero unresolved
findings; see artifacts/20261014_correctness_review.md and
artifacts/20261014_security_review.md. Evidence: artifacts/validation.md.
No deployment claimed.

## Closeout

Closed 2026-10-14 UTC. Observed uploads can be added to both daily source plots
with full-record population and shared conversion. The final plan is under
prompts/completed/. User/operator guide, developer README and ADR-0093 are updated.
The existing origin/master broad-exception audit failure in climate_build_helpers.py
is retained in validation.md; package-scoped enforcement passes. Production
deployment was not requested or performed. No run artifact migrations or repairs
are needed; rollback removes the additive overlay implementation.
