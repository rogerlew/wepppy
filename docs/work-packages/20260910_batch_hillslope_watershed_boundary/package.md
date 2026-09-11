# Batch hillslope-to-watershed RQ task boundary

**Status**: Ready for execution on `forest`
**Started**: 2026-09-11 04:52 UTC
**Starting revision**: `29a18e00f87dc08f7832dc4f5cc8a7b87302562e`

## Overview

Split each batch watershed leaf at the existing hillslope-to-watershed boundary.
The first RQ task performs project setup through hillslope WEPP and hillslope
interchange. A dependent RQ task then performs watershed preparation, watershed
WEPP and postprocessing, WATAR when enabled, and Omni submission. Both tasks use
the existing `batch` queue and existing worker deployment. Do not add a queue,
worker pool, service, daemon, or dependency.

The change reduces the amount of one uninterrupted Python/RQ execution and
makes the scientific phase boundary explicit, independently retryable, and
observable. Whether it provides sufficient memory relief in the Kubernetes
deployment is deliberately an integration question for the subsequent
`openwepp.org` rollout; Forest package closure must not claim that result.

## Incident evidence

The openwepp.org OR-40 Phase 4 run approached the 12 GiB worker limit after
hillslope work. An isolated rerun found fresh-pod watershed WEPP peaked at
5.153 GiB and every subsequent post stage at or below 3.464 GiB. The batch
worker had also been observed idle with approximately 10.58 GiB charged,
including 9.60 GiB file cache. This package implements only the requested task
boundary. It does not change pod resources or kernel memory policy.

## Scope

### Included

- Refactor `BatchRunner.run_batch_project()` into explicit, reusable
  pre-watershed and watershed/downstream phase entry points without changing
  scientific calculations or generated artifact formats.
- Replace each monolithic `run_batch_watershed_rq` leaf with a hillslope-stage
  task and a dependent watershed-stage task on the existing `batch` queue.
- Make the final batch completion job depend on the terminal watershed-stage
  jobs, with explicit behavior when the hillslope stage fails.
- Preserve retry selection, run metadata, RedisPrep timestamps, NoDb cache and
  lock ownership, status messages, WATAR, Omni dependency attachment, and
  failure-tolerant batch finalization.
- Update `batch_rq.pyi`, RQ documentation, the generated dependency graph and
  `wepppy/rq/job-dependencies-catalog.md`.
- Add deterministic unit and real-Redis/RQ integration coverage for success,
  failure, retry, cancellation, and finalizer dependency behavior.
- Deploy the reviewed candidate to the Forest Docker Compose development stack
  and prove that the two functions execute as separate RQ jobs using the
  existing batch workers and shared run tree.
- Run the complete pytest suite, commit and push the reviewed implementation to
  `master`, and verify the automatic GHCR workflow publishes the immutable
  `ghcr.io/rogerlew/wepppy:sha-<commit>` image and reports its digest.

### Explicitly out of scope

- A new RQ queue, worker pool, Compose service, or Kubernetes workload.
- Kubernetes manifests, pod memory limits, cgroup configuration, Memory QoS,
  NFS/ZFS changes, or node scheduling policy.
- Hillslope preparation/interchange performance refactoring.
- Scientific algorithms, output schemas, WEPP binaries, wepppyo3 behavior, and
  Omni scenario fan-out.
- Running the full batch or claiming memory/OOM acceptance on Forest.
- Deploying the image to openwepp.org or running its integration batch. Those
  occur only after this package is closed and require a separate deployment
  work package in the open-wepp-org repository.

## Required behavior

For every selected watershed, `run_batch_rq` creates a two-job chain:

1. The hillslope task initializes or resumes the leaf and completes all enabled
   work through `ensure_hillslope_interchange`.
2. The watershed task runs only after the hillslope task reaches its contracted
   successful handoff, freshly hydrates run-scoped state, completes enabled
   watershed and downstream work, writes terminal `run_metadata.json`, emits
   the existing completion trigger, and attaches any Omni terminal dependency.
3. `_final_batch_complete_rq` waits for each leaf's terminal watershed task and
   dynamically attached Omni finalizers. One failed leaf must not strand the
   batch finalizer in `DeferredJobRegistry`.

The implementer must settle failure transport against the canonical RQ response
contract before editing production code. Do not infer success from an RQ job
that returned `(False, elapsed)`: the downstream task must receive an explicit,
tested handoff state and must never run watershed work over an incomplete
hillslope prerequisite.

## Compatibility and recovery

- Existing completed leaves remain complete and are skipped by normal retry
  selection.
- A leaf interrupted before the boundary remains retryable from its missing
  RedisPrep timestamps.
- A leaf interrupted after the handoff resumes watershed work without deleting
  valid hillslope outputs.
- Existing `run_metadata.json` readers retain their current terminal success or
  failure schema. Stage job IDs may be additive metadata only.
- NoDb state is freshly hydrated at the second task boundary. Stale-write
  enforcement and directory locks must not be weakened or globally cleared.
- Re-running submission must not create duplicate live watershed-stage jobs.
- Rollback is the preceding source/image revision. Existing partial leaves use
  normal retry classification; no Redis flush or run-tree deletion is allowed.

## Security impact and reviews

**Security impact**: `high`. Queue wiring and shared run-tree mutation change.

Package closure requires independent correctness, QA/code, and security reviews
with no unresolved high or medium findings. Reviews must cover dependency
integrity, duplicate submission, untrusted run identifiers, cancellation,
partial failure, NoDb ownership, and finalizer release. Use the repository
review templates and retain the completed artifacts under `artifacts/`.

## Success criteria

- [ ] Two separate RQ jobs exist per selected leaf and both use `batch`.
- [ ] Watershed work cannot start before a successful hillslope handoff.
- [ ] The second task freshly hydrates controllers and preserves valid
  hillslope/interchange outputs.
- [ ] Success, either-stage failure, cancellation, retry, already-complete,
  WATAR, and Omni behavior are explicit and covered.
- [ ] Batch finalization cannot race the second stage or remain permanently
  deferred after a failed leaf.
- [ ] `wctl check-rq-graph` passes and the checked-in graph/catalog describe the
  actual two-stage topology.
- [ ] Forest Compose evidence shows distinct hillslope and watershed RQ job IDs
  on existing batch workers, correct dependency order, one terminal metadata
  record, and no leaked/deferred test jobs.
- [ ] Focused tests and `wctl run-pytest tests --maxfail=1` pass.
- [ ] Documentation, stubs, broad-exception, code-quality, and diff checks pass.
- [ ] Independent reviews pass with no unresolved high/medium findings.
- [ ] The implementation and closeout are committed and pushed to `master`.
- [ ] The master-triggered GHCR workflow succeeds and its source SHA, immutable
  tag, and digest are recorded.
- [ ] No openwepp.org deployment or full batch integration is performed or
  claimed during package execution.

## Post-close integration gate

After this package closes, scaffold and execute a separate open-wepp-org rollout
package. Deploy the exact recorded GHCR digest, wait for an authorized batch
window, and run a representative batch on `openwepp.org`. Acceptance must prove
the two job IDs and dependency order in the live job tree, correct outputs and
retry/finalizer behavior, and cgroup memory headroom under the 12 GiB cap. A
Forest pass and successful image build are prerequisites, not substitutes, for
that integration result.

## Deliverables

- Updated BatchRunner phase API and batch RQ chain.
- Updated stubs, RQ graph/catalog, developer/operator documentation, and tests.
- Forest integration harness and sanitized evidence.
- Correctness, QA/code, security, and validation artifacts.
- Completed active ExecPlan and tracker.
- Pushed master commit and immutable GHCR digest evidence.
