# Usersum vendor link graph tracker

## Progress

- [x] Audit the existing build and test Comrak link rewriting.
- [x] Ratify the contract and record checkpoint `3aae1556e`.
- [x] Implement the graph walk and heading lint.
- [x] Verify copied artifacts and Usersum routes.
- [ ] Run broad suite in a runtime with the native parser artifacts and integrate the feature branch.

## Decisions

The operator requested a feature branch and contract-first work package on
2026-11-20 UTC. The branch is `task/usersum-linked-vendor-docs`.
See the [ExecPlan](prompts/active/implementation_execplan.md) and
[contract checkpoint](artifacts/20261120_contract_decision.md).

The [historical source checkpoint](artifacts/20261120_archive_contract_decision.md)
is `cda1ef9e9`. The [correctness](artifacts/20261120_correctness_review.md)
and [security](artifacts/20261120_security_review.md) reviews record the local
acceptance evidence. The isolated focused suite passed 123 tests. The broad
preflight passed the browser check with the existing runtime and stopped
before collection because shape and GeoParquet parser artifacts were missing.
The receipt is `.wctl-test-runs/0998248bb93541e0aa4b32697483b406/receipt.json`.
