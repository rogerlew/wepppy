# RQ 2.12.0 upgrade tracker

**Status**: Closed 2026-10-27
**Scope**: Local forest; production unchanged; native webhooks disabled/unexposed.

## Progress

- [x] M1: versioned distribution inventory, 1.16.2 API/model baseline and six-state historical fixtures.
- [x] Contract checkpoint independently approved and committed as ancestor `b1054fac7`.
- [x] M2: exact RQ 2.12.0, required croniter 6.0.0 and bounded compatibility repairs (`b5cac8166`; dashboard `91f62b9`).
- [x] M3: 598 installed targeted tests and 13 real Redis/process lifecycle cases pass without skips.
- [x] M4: all 17 forest runtimes upgraded, real model/API/archive acceptance and isolated original-state rollback proof pass.
- [x] M5: complete isolated regression (11,948 passed, 226 skipped), graph/stub/exception/doc gates, independent reviews and archived plan.

## Decisions and rationale

Exact 2.12.0 preserves current application contracts and excludes webhooks. Only RQ and croniter change in the installed shared distribution set; four pins prevent unrelated resolver drift. Existing topology, identities, mounts, permissions and queues remain unchanged. Normative rationale is in [RQ runtime migration](../../schemas/rq-response-contract.md#rq-212-runtime-migration); operational rules are in [migration and recovery](../../dev-notes/rq-2-12-migration.md).

Running 1.x work must drain. Mixed workers and in-place downgrade of 2.x-written state are unsupported. Original-state rollback was proven in isolation, not by overwriting accepted newer work.

## Validation and review

[Final validation ledger](artifacts/final_validation.md) links exact results and runtime identity. [Integrated acceptance](artifacts/acceptance_upgraded.md) proves an 18-node graph, 155 identical inputs, 25 scientifically identical Parquets, three identical CSV reports, authorization/cancellation/resubmission and actual restoration of 417 generated files.

[Correctness](artifacts/20261027_correctness_review.md) and [security](artifacts/20261027_security_review.md) reviews close all medium/high findings. Final health: 17 RQ 2.12.0 containers, 11 idle workers, web/API HTTP 200.

## Discoveries and limitations

The original working-tree full command stopped after 6,810 passes and 61 skips on preexisting Roads publication-hash drift. Actual RQ 1.16.2 reproduced it. All five unrelated dirty tracked files were preserved; a complete isolated run used their committed counterparts and passed. The Roads owner must separately reconcile their publication provenance. No test or stale-hash guard was weakened.

A stronger deleted-output restore check exposed existing NFS log-handle retention. An RQ-free reproduction established the mechanism; graceful local web/API recovery allowed canonical restore, exact hashes and report retrieval to pass. The durable guide retains this limitation and bounded recovery.

Only the package's disposable Redis test container was stopped; shared Redis, volumes, unrelated jobs and original projects were preserved. Test projects, protected snapshot, rollback image tags and evidence remain retained. No push or production deployment occurred.
