# Implement batch outcomes for partial results


This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`. M1–M4 implementation and local validation are complete. The reviewed contract checkpoint precedes runtime implementation.

## Purpose / Big Picture


Deliver successful batch and culvert results when a sibling times out. A 32-success/one-timeout case must download 32 valid runs, report the omission, and retain the failed leaf's traceback. Polling, project inspection, metrics, and geometry must agree.

## Progress


- [x] (2026-11-16 06:13 UTC) Scaffold package and draft decision.
- [x] (2026-11-16 06:29 UTC) M1 source/consumer inventory and exact proposed canonical schema prepared; see artifacts/20261116_inventory.md and docs/schemas/batch-outcome-contract.md.
- [x] (2026-11-16) M1: Independent correctness/security contract reviews and finding disposition pass; artifacts record reviewed hash.
- [x] M1: Operator ratified; checkpoint `390108471` and climate compatibility addendum `0aec93f1c` committed before their respective runtime changes.
- [x] M2: Finalization and additive polling implementation for both workflows.
- [x] M3: Client adoption, direct artifact acceptance, migration guide.
- [x] M4: Focused gates and independent reviews pass; full run stopped at operator request (766 passed / 32 skipped). Server `f13e4ce6f`, external client `c56fa19a7`.

## Surprises & Discoveries

M1: both finalizer edges already tolerate failure. Ordinary Omni strict downstream edges can still strand the batch finalizer after scenario failure. Successful leaf RQ evidence can expire before a 12-hour sibling timeout unless retention is extended. Culvert resume and standalone finalize are additional consumers. See artifacts/20261116_inventory.md and independent review findings.


Culvert finalization already permits partial success, but generic RQ aggregation propagates failed children and the client aborts before download. Caught application exceptions returning `failed` behave differently. All 33 runs in `1f2933b8-12a7-48cc-b508-5f2719baa8a7` failed SSURGO; the operator removed incident-ID recovery from scope because stream-order reduction was revised to avoid the original timeout.

## Decision Log

2026-11-16: Proposed immutable attempt-specific baseline WEPP ZIPs for both workflows, retaining legacy diagnostic archives and WATAR/Omni project downloads. Prep-only selections are explicit skips; selected-only ordinary retry cohorts exclude historical complete runs. The operator ratified these choices before checkpoint `390108471`. See the canonical proposal and inventory.


2026-11-16 06:13 UTC: Add finalizer-owned `batch` outcome on jobinfo and jobstatus, preserving RQ status and exception visibility. Artifact availability and execution diagnostics answer different questions. Ratified by the operator at 06:31 UTC.

## Outcomes & Retrospective


Server finalizers and polling are wired to immutable per-attempt artifacts. The
companion client uses manifest-selected successes for metrics and both geometry
layers, preserving legacy behavior when `batch` is absent. Local evidence includes
real Redis/RQ timeout and dependency transitions, actual authorized HTTP download,
production Culvert finalizer execution, canonical archive/restore, and client
Parquet/GeoJSON readback. Test producers use synthetic scientific files; feature
grants and selected NoDb adapters have fixture boundaries. Full scientific execution,
deployed Celery integration and production-equivalent identities/mounts remain
release acceptance gates; no deployment is claimed. See the validation artifact.

Review found cancellation races in long publication locks, out-of-lock manifest
writes and stale metadata. Short shared dispatch/commit leases, refreshed cancellation
trees and consistent terminal manifests close these without a new service.

## Context and Orientation


Work from `/workdir/wepppy` and read root/nearest AGENTS instructions. A leaf executes one run; a finalizer settles results after the relevant leaves terminate. `wepppy/rq/job_info.py` constructs recursive jobinfo and aggregate jobstatus; `wepppy/microservices/rq_engine/job_routes.py` exposes them. Ordinary batch finalization is in `wepppy/rq/batch_rq.py::_final_batch_complete_rq`. Culvert orchestration and artifacts use `culvert_rq.py::_final_culvert_batch_complete_rq`, `culvert_rq_pipeline.py`, and `culvert_rq_manifest.py` in the same directory. Inspect ordinary batch linked dependencies and artifact surfaces; do not assume culvert topology applies unchanged.

The external client is `Culvert_web_app/culvert_app/tasks/wepp_cloud_integration_task.py`. It currently aborts on aggregate failure, filters metrics through file-read exceptions, and processes geometry independently. Explicit successful-run selection and omission warnings are required for all layers. Record external repository delivery separately from server implementation.

## Plan of Work


M1: Read the contract-first, artifact observability/validation, and hardening lifecycle standards. Inventory `docs/schemas/rq-response-contract.md`, webhook contract, nearest subsystem contracts, finalizers, consumers and download routes. Complete `artifacts/20261116_contract_decision.md` with exact schema types, errors, counts, ordinary batch artifact shape, atomic publication, attempt identity, retention and finalizer crash detection. Promote canonical amendments as implementation pending, reconcile conflicts, obtain operator approval and two independent read-only reviews, and disposition findings. Commit the canonical checkpoint as a standalone ancestor before runtime edits and record its revision. Preserve existing dirty contract changes. Checkpoint `390108471` records completed M1.

M2: Implement the ratified summary using existing RQ and persistence. Both polling endpoints must expose the same authoritative current-attempt summary. Finalization waits for relevant work but tolerates failed dependencies; worker death without metadata is reconciled from RQ. Validate successful outputs, publish the artifact atomically, then expose availability. A finalizer failure must settle visibly even if normal publication never executes. Keep sanitized leaf exceptions, generic status aggregation, and restricted catalog disclosure intact. Update the dependency catalog if queue wiring changes.

M3: Wire culvert polling to terminal batch outcome and result availability, including aggregate failed with partial success. Filter metrics, hillslopes, channels and counts by explicit validated successful IDs; failed runs must not appear as zero erosion. Preserve explicit legacy behavior. Update `docs/culvert-at-risk-integration/dev-package/weppcloud-wbt-unnest-basins-migration-guide.md` with the ratified schema, polling examples, timeout/all-failed cases, and rollout guidance. End-to-end closure requires real consumer adoption, not just a server response example.

M4: Obtain independent correctness and security reviews using repository templates; close medium/high findings. Complete focused/broad regressions and artifact evidence, then update tracker/project board. Deployment and incident requeue are separate authorized activities.

## Concrete Steps


From `/workdir/wepppy`, inspect `git status --short`. Use `rg` to locate batch/culvert/polling tests under `tests/rq` and `tests/microservices`; run `wctl run-pytest <discovered-test-paths>`. For wiring edits run `wctl check-rq-graph` and update `wepppy/rq/job-dependencies-catalog.md`. For changed interfaces/stubs run applicable `wctl run-stubtest <module>` and `wctl check-test-stubs`. Before implementation closeout run `wctl run-pytest tests --maxfail=1`; run npm lint/tests when frontend code changes. Run `wctl doc-lint --path <changed-file>` for documentation. Record exact commands and results in artifacts; do not claim unrun tests.

## Validation and Acceptance


Exercise every state in the draft decision matrix for both workflows. Use a real RQ worker with a short test timeout to reproduce the 12-hour failure class. Verify finalizer scheduling after failure, persist/read actual summaries, call both polling endpoints, download real artifacts, and compare semantic run IDs in metrics and geometry. A failed ID must appear in diagnostics and be absent from successful outputs. Test actual publication failure, missing outputs despite success markers, and retry fencing. Mock-only serializer tests cannot prove these boundaries. Show valid access works and hostile/foreign paths fail without broader disclosure. Include normal project inspection and archive/restore behavior.

## Idempotence and Recovery


Repeated finalization cannot mix attempts or advertise an old archive as newly ready. Use isolated test projects and preserve production evidence. Missing additive fields never imply success. Record reader rollback/retention behavior and avoid production mutation during local acceptance.

## Artifacts and Notes


Retain checkpoint revision, two contract reviews/disposition, independent correctness/security review artifacts, test receipts, real timeout evidence, polling JSON, and artifact-ID comparisons. Timestamp in UTC and redact credentials. Base revision is `df8b5249c70a3d98fd27f2b3b3b16ac1d96deb52`; existing dirty files are not presumed part of this package.

## Interfaces and Dependencies


The additive `batch` fields are ratified in the canonical contract. Promote exact schema and compatibility rules to the canonical RQ response contract before implementing. Reuse existing infrastructure; no new queue/service/datastore or model changes. Resolve ordinary batch artifact representation, finalizer failure settlement, and attempt retention in M1.

Revision note: 2026-11-16 06:13 UTC — initial contract-first scaffold; implementation and wiring remain separate acceptance milestones.

Revision note: 2026-11-16 — executed M1 inventory, prepared exact proposed contract and initiated independent reviews; runtime remains behind ratification and checkpoint.

Operator approval (2026-11-16 06:31 UTC): “i approve. proceed with commit and implementation”. This ratifies the reviewed contract (pre-status-update SHA-256 `42d00a1931ea77e862412349ff91414bfae47d3dc33dd57faf0eb6ac7f8fed92`) and authorizes the standalone checkpoint and implementation commits. Runtime implementation and local conformance evidence follow in the validation artifact.

Progress update: M2/M3 implementation is in the working trees; focused/local boundary validation and independent implementation reviews are active. Incident identity/recovery is excluded per operator clarification.

Decision update (2026-11-16): Preserve cancellability by building ZIPs outside the
resource lease and committing manifest/ZIP/summary only after cancellation and
execution-state rechecks. Enqueue and parent linkage share the same short lease;
cancellation refreshes the tree after acquisition. Poll-settled failures also write
matching member manifests. This implements the ratified cancellation/immutability
contract rather than changing cancellation semantics.

Final operator direction: “i don't think we need to run the full suite of tests”.
The broad run was interrupted; final acceptance uses focused regression, real
Redis/RQ boundary and client readback receipts. No full-suite pass is claimed.
Implementation delivery is complete. Deployment acceptance remains separate.
