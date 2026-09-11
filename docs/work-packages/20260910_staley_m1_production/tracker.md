# Production M1 tracker

Status: complete 2026-09-10; ExecPlan archived. Runtime changes uncommitted.
Baseline `304572530`; unrelated code-quality reports are dirty and excluded.

- [x] Read existing backend, Pure UI, feature-registry and runtime-contract precedents.
- [x] Draft concrete minimal UI and production workflow contracts; scaffold plan.
- [x] Record owner UI revisions: realtime preflight, dNBR name, no dates, Auto scale, filename/format guidance, disabled unavailable NOAA.
- [x] Record owner distribution-based Auto and uploaded-map panel-summary table; draft ADR-0063.
- [x] Evaluate/freeze detection criteria and fixture evidence in ADR-0063.
- [x] Owner execution authorization; exact UI and schemas/state matrix ratified.
- [x] Two independent contract reviews, disposition and standalone ancestor commits.
- [x] NoDb artifact/state/readiness implementation and regression tests.
- [x] Upload transport/worker/publication and RQ model execution.
- [x] Minimal control, reload/freshness behavior and authorized file access.
- [x] Real web/worker end-to-end evidence, required suites and independent reviews.
- [x] Development worker installation/preflight and owner 10 m test handoff;
  other-host deployment and the owner's real-basin acceptance remain separate.

## Execution record

Contract checkpoint `5c0a172ee` and accepted-only download amendment `595816476`
were approved by both independent reviewers before their runtime changes. Owner
execution request authorizes this package. NoDb, upload/RQ, live control and files
are implemented locally. Independent review findings are closed. Strict browser
acceptance passed: exact new jobs and accepted IDs, download, reload, unitization,
ambiguous replacement/correction and live invalidation/recovery. Local WBT install
and actual job trees are recorded in artifacts. Full Python: 8,312 passed, 77 skipped; focused production 14, frontend 841,
stubs, preflight, RQ graph and docs gates passed. No production host was changed.

See [validation](artifacts/validation.md), [correctness/UI review](artifacts/correctness_review.md)
and [security review](artifacts/security_review.md).
