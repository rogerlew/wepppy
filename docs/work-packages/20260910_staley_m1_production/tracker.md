# Production M1 tracker

Status: executing contract checkpoint; 2026-09-10 07:23 UTC.
Baseline `304572530`; unrelated code-quality reports are dirty and excluded.

- [x] Read existing backend, Pure UI, feature-registry and runtime-contract precedents.
- [x] Draft concrete minimal UI and production workflow contracts; scaffold plan.
- [x] Record owner UI revisions: realtime preflight, dNBR name, no dates, Auto scale, filename/format guidance, disabled unavailable NOAA.
- [x] Record owner distribution-based Auto and uploaded-map panel-summary table; draft ADR-0063.
- [x] Evaluate/freeze detection criteria and fixture evidence in ADR-0063.
- [ ] Owner review of exact UI and decision register; finalize schemas/state matrix.
- [ ] Two independent contract reviews, disposition and standalone ancestor commit.
- [ ] NoDb artifact/state/readiness implementation and regression tests.
- [ ] Upload transport/worker/publication and RQ model execution.
- [ ] Minimal control, reload/freshness behavior and authorized file access.
- [ ] Real web/worker end-to-end evidence, required suites and independent reviews.
- [ ] Approved target binary/install preflight and owner's 10 m smoke-test handoff.

## Decisions and scope

User explicitly deferred reports and requested simple, organized UI using terms
familiar to land managers/hydrologists. Proposed control: prerequisites, dNBR,
one design-rainfall choice and one run action. No coefficients, model selector,
manual publish action or dashboard. Exact layout/defaults need owner approval.
No runtime code changed. The plan is blocked at its required contract checkpoint
until exact intended behavior is accepted; research/mockups can proceed first.

## Checkpoint record

Starting revision: `304572530`. Contract ancestor: not created. Owner acceptance
of detailed proposals: pending. Independent preimplementation reviews: pending.
The latest owner UI revisions are accepted intent; Auto resolution/retry details
and the remaining schemas/defaults still need the completed checkpoint.
Do not infer checkpoint completion from the presence or commit of this scaffold.

## Next step

Review [UI contract](../../ui-docs/contracts/postfire-debris-flow-control-contract.md)
and [decision register](artifacts/decision_register.md). Create the static review
preview and finalize transport/state/locale/freshness matrix before runtime edits.

Execution authorized by user. Static preview and exact transport/state contract
prepared; security contract review approved, correctness confirmation pending.
