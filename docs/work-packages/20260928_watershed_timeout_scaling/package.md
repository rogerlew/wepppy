# Watershed runtime budget

Status: Closed 2026-09-28. Owner: Codex. Amendment: WRT-01.

Implement the operator-approved years × hillslopes timeout in all four continuous
watershed submission paths, preserving unrelated stages and no-prep inputs.
Complexity budget: one bounded policy helper and additive child RQ metadata;
no infrastructure, dependencies, model-input changes or process-control changes.
Security impact: low; longer authorized worker occupancy and bounded parsing of
already-authorized prepared inputs. Independent contract and final correctness
reviews required; include security/noninterference review of admission bounds.

Acceptance: 27-hour persisted budget for 1,000 years × 1,908 hillslopes; 12-hour floor;
rounding boundaries; single-storm unchanged; all four graph paths; no partial
children on invalid workload; fork metadata retained; real Redis serialized
timeout/metadata and live job-tree evidence. Deployment is separate.

Delivered in `aa2d1cd2a`: bounded workload policy, four enqueue paths, additive
metadata, regression coverage and operator/developer documentation. Full suite:
9,977 passed / 99 skipped; final focused coverage: 98 passed; broader RQ coverage:
1,216 passed / 29 skipped. Four real Redis graphs verified; reviews approved.
See [validation](artifacts/validation.md) and
[completed plan](prompts/completed/watershed_timeout_execplan.md).
Durable authority: [WRT-01](../../schemas/wepp-run-input-contract.md#continuous-watershed-runtime-budget-wrt-01)
and [ADR-0076](../../adrs/ADR-0076-watershed-runtime-budget.md).
Deployment and production retry remain separate; subprocess cleanup is a known
separate issue, not bundled into this allowance change.
