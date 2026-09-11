# Batch hillslope-to-watershed RQ task boundary tracker

## Quick status

- **Status**: Completed — 2026-09-11 06:14 UTC
- **Started**: 2026-09-11 04:52 UTC
- **Starting revision**: `29a18e00f87dc08f7832dc4f5cc8a7b87302562e`
- **Live authorization**: Forest Docker Compose development stack only
- **Queue topology**: existing `batch` queue and workers only
- **openwepp.org integration**: required after package close, not authorized in
  this package

## Task board

### Completed

- [x] Execute the active ExecPlan from current `master` on Forest.
- [x] Establish the two-stage failure and handoff contract with failing tests.
- [x] Implement the BatchRunner phase boundary and batch RQ dependency chain.
- [x] Update stubs and the RQ dependency graph/catalog.
- [x] Pass focused and complete pytest suites and repository quality gates.
- [x] Complete independent correctness, QA/code, and security reviews.
- [x] Commit and push the reviewed implementation to `master`.
- [x] Deploy the exact candidate to Forest and validate the real two-job handoff.
- [x] Verify the master-triggered GHCR build and retain its immutable digest.
- [x] Close without deploying or running a batch on openwepp.org.

### In progress

None. Implementation `0a1e2e1ef` and closeout `30a5d0505` are pushed.
All reviews, 8447 full-suite tests, 95 focused tests and Forest acceptance pass.
Exact closeout image publication succeeded; immutable coordinates and LFS
results are retained in the publication artifact.

### Blocked

None.

### Done

- [x] 2026-09-11 04:52 UTC: Updated local `master` to `29a18e00f`.
- [x] 2026-09-11 04:52 UTC: Scoped the requested existing-queue task boundary;
  rejected a new queue or worker pool.
- [x] 2026-09-11 04:52 UTC: Deferred Kubernetes deployment, batch execution, and
  12 GiB memory acceptance to a post-close open-wepp-org rollout package.

## Decision log

- **2026-09-11 04:52 UTC — Existing queue only.** Both stages use `batch`.
  The purpose is an explicit task boundary, not a new scheduling tier.
- **2026-09-11 04:52 UTC — Terminal ownership moves to stage two.** Watershed,
  downstream postprocessing, WATAR, Omni attachment, terminal metadata, and the
  leaf completion trigger belong to the second task.
- **2026-09-11 04:52 UTC — Forest validates wiring; openwepp validates memory.**
  Forest must prove the real RQ dependency and shared-run-tree handoff. Only the
  later Kubernetes deployment can establish whether this resolves the observed
  12 GiB workload failure.

## Required evidence

- `artifacts/2026-09-11_contract_decision.md`
- `artifacts/2026-09-11_correctness_review.md`
- `artifacts/2026-09-11_code_qa_review.md`
- `artifacts/2026-09-11_security_review.md`
- `artifacts/2026-09-11_validation.md`
- `artifacts/2026-09-11_forest_integration.md`
- `artifacts/2026-09-11_ghcr_publication.md`

## Handoff

The executed plan is under `prompts/completed/`. Forest is restored to its
normal worker configuration with the reviewed source loaded. Exact closeout-SHA
publication is verified. The separate openwepp.org rollout must validate
scientific output and memory headroom; no such claim is made here.
