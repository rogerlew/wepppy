# Implement the batch hillslope-to-watershed RQ task boundary

This ExecPlan is a living document. Maintain it according to
`docs/prompt_templates/codex_exec_plans.md`, and update `Progress`, `Surprises &
Discoveries`, `Decision Log`, `Outcomes & Retrospective`, and
`../../tracker.md` at every stopping point.

## Purpose / Big Picture

A batch leaf currently performs delineation, landuse, soils, climate,
hillslope WEPP, hillslope interchange, watershed WEPP, postprocessing, WATAR,
and Omni submission inside one RQ job. After this change, the leaf crosses an
observable RQ task boundary after hillslope interchange. A dependent task then
freshly opens the run and completes watershed and downstream work. Operators
can see two ordered job IDs, retry partial work, and diagnose either phase
without adding another queue or worker service.

This is a faithful extraction of existing behavior, not a surrogate workflow.
Implemented means the phase APIs exist and are tested; wired means real RQ
submission uses the two tasks. Package closure requires both plus a real Forest
Compose handoff. The later openwepp.org deployment owns full-batch output and
12 GiB memory acceptance.

## Progress

- [x] (2026-09-11 04:52 UTC) Pulled `master` to starting revision `29a18e00f`.
- [x] (2026-09-11 04:52 UTC) Defined the existing-queue, two-task scope and the
  post-close Kubernetes integration boundary.
- [ ] Record the handoff/failure contract and add failing tests.
- [ ] Extract BatchRunner phases without changing scientific behavior.
- [ ] Wire the two-stage RQ chain and terminal finalizer dependencies.
- [ ] Update stubs, dependency catalog/graph, and durable documentation.
- [ ] Pass focused tests and the complete pytest suite.
- [ ] Complete independent correctness, QA/code, and security reviews.
- [ ] Commit/push the reviewed candidate and deploy it to Forest.
- [ ] Execute Forest RQ integration and close all evidence.
- [ ] Commit/push closeout and verify the immutable GHCR image build.

## Surprises & Discoveries

- Observation: RQ already forks a work-horse process for each job, while the
  Kubernetes worker container is long-lived. Therefore this package must not
  claim that task separation alone guarantees a new cgroup.
  Evidence: the deployed worker uses `WepppyRqWorker`; package memory acceptance
  is explicitly deferred to openwepp.org.

## Decision Log

- Decision: use the existing `batch` queue for both stages.
  Rationale: Roger explicitly rejected another pool; the smallest requested
  change is the task boundary itself.
  Date/Author: 2026-09-11, Roger Lew and Codex.
- Decision: retain terminal leaf semantics in the second task.
  Rationale: the leaf is not complete until watershed/downstream work finishes;
  early success metadata or triggers would race batch finalization.
  Date/Author: 2026-09-11, Codex.
- Decision: close after Forest wiring proof, full tests, push, and GHCR build;
  defer the live full batch and memory verdict.
  Rationale: the user requires integration testing after close on the
  openwepp.org deployment.
  Date/Author: 2026-09-11, Roger Lew and Codex.

## Outcomes & Retrospective

Pending implementation.

## Context and Orientation

`wepppy/rq/batch_rq.py::run_batch_rq` enqueues one
`run_batch_watershed_rq` job per selected `WatershedFeature`, then enqueues
`_final_batch_complete_rq` behind those jobs. The leaf job calls
`wepppy/nodb/batch_runner.py::BatchRunner.run_batch_project`, writes terminal
metadata, emits `BATCH_WATERSHED_TASK_COMPLETED`, and optionally submits Omni.

`BatchRunner.run_batch_project` initializes or resumes the run, performs all
enabled preparation, calculates `run_hillslopes` and `run_watershed`, runs
hillslopes and `ensure_hillslope_interchange`, then immediately runs watershed
WEPP, totalwatsed3, watershed interchange, query activation, and optional
WATAR. `RedisPrep` timestamps are the durable task-completion authority.

The new “handoff” is the durable condition proving stage one completed the
enabled prerequisites. It must be reconstructible from run state and job
metadata after worker loss; an in-memory return value alone is insufficient.
The RQ graph authority is `wepppy/rq/job-dependencies-catalog.md` and its
generated JSON. The response/error authority is
`docs/schemas/rq-response-contract.md`; NoDb ownership remains governed by
`docs/schemas/nodb-persistence-concurrency-contract.md`.

## Plan of Work

First, inspect the canonical contracts and characterize the existing leaf
success/failure behavior with tests. Decide whether the current false tuple is
sufficient or whether a stage-specific explicit exception/receipt is required.
Record the decision in `artifacts/2026-09-11_contract_decision.md` before
production edits. Preserve the external batch summary and retry behavior.

Next, extract cohesive phase methods from `BatchRunner.run_batch_project`.
Stage one owns initialization/resume, base resynchronization, DEM through
OpenET/RAP, hillslope cleanup/preparation/execution, and required hillslope
interchange. Stage two re-resolves the run directory and freshly hydrates every
controller it uses before watershed preparation/execution, totalwatsed3,
watershed interchange, query activation, and optional WATAR. Avoid a generic
phase framework; expose only the methods necessary for this boundary. Keep a
compatibility wrapper only if an existing non-RQ caller genuinely requires the
monolithic method, and test it.

Then update `batch_rq.py`. Give the two task functions stable descriptive names
and signatures, update `batch_rq.pyi`, and enqueue both onto `Queue("batch")`.
Persist both job IDs under unambiguous `jobs:*` metadata. Ensure stage two has a
real dependency on stage one and verifies the durable handoff before mutation.
Make `_final_batch_complete_rq` depend on terminal stage-two jobs. Preserve the
existing failure-tolerant final summary without leaving failed chains deferred.
Move Omni submission, dynamic Omni-finalizer attachment, terminal
`run_metadata.json`, and the completion trigger into stage two.

Add tests in the existing batch RQ and BatchRunner test modules. Cover a normal
two-stage leaf, disabled hillslope or watershed directives, already-completed
timestamps, stage-one failure, stage-two failure, cancellation between stages,
retry after each failure, duplicate submission, malformed/missing handoff,
WATAR, Omni dependency attachment, zero selected leaves, and mixed leaf
success/failure. Use real Redis/RQ dependency behavior where mocks would hide
registry transitions. Do not use a live production queue or delete retained
jobs.

Regenerate the RQ graph and update the catalog. Update operator/developer docs
that describe batch jobs and dashboard topology. Add no new queue/service to
Compose. Complete correctness, QA/code, and security review artifacts and
resolve every high or medium finding.

Commit and push the reviewed candidate to `master`, then deploy that exact SHA
to Forest using its installed canonical `wctl` development workflow. Do not
edit tracked source directly on Forest. Use unique test identifiers. Enqueue a
bounded integration leaf or purpose-built integration fixture and retain
evidence that the two job IDs were separate, both originated from `batch`, the
second began after the first finished, the run tree was visible, terminal
metadata was written once, and registries contain no leaked test work. Restore
Forest to its normal development state if the test changed temporary data.

After all code and Forest evidence is complete, move this ExecPlan to
`prompts/completed/`, close the package/tracker, commit and push closeout, and
wait for `.github/workflows/publish-weppcloud-image.yml`. Record the exact
source SHA, `ghcr.io/rogerlew/wepppy:sha-<SHA>`, digest, workflow URL/status,
and LFS verification result. A failed image build holds the package.

## Concrete Steps

Work from the repository root on Forest unless a step explicitly says
otherwise.

Inspect and establish the baseline:

    git status --short --branch
    git rev-parse HEAD
    wctl check-rq-graph
    wctl run-pytest tests/rq/test_batch_rq_retry_selection.py --maxfail=1

During implementation, run the focused batch and graph tests discovered from
the touched modules. After queue edits regenerate only through the canonical
tool:

    python tools/check_rq_dependency_graph.py --write
    wctl check-rq-graph

Before review and again after review fixes:

    wctl run-pytest tests --maxfail=1
    wctl check-rq-graph
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    python3 tools/code_quality_observability.py --base-ref origin/master
    wctl doc-lint --path docs/work-packages/20260910_batch_hillslope_watershed_boundary
    git diff --check

Use the canonical Forest deployment commands discovered from `wctl` and
`docker/docker-compose.dev.yml`; record exact commands and container revisions
in the Forest evidence rather than guessing them here. Recreate only services
required by the candidate. Confirm existing batch workers listen only on
`batch`; do not add another service.

Push only reviewed commits:

    git status --short --branch
    git diff --check
    git push origin master

Use GitHub CLI or the Actions UI/API to wait for the workflow associated with
the exact pushed closeout SHA. Do not substitute an older successful image.

## Validation and Acceptance

Focused tests must fail on the monolithic baseline for the missing two-job
topology and pass after implementation. The complete command
`wctl run-pytest tests --maxfail=1` must exit zero; record passed/skipped counts
and duration. Stubs, graph checks, doc lint, broad-exception enforcement, and
diff checks must pass.

Forest acceptance requires actual RQ `Job` and registry observations, not only
mocked enqueue calls. Evidence must show two different job IDs, queue `batch`
for both, stage-two dependency on stage one, chronological execution order,
fresh stage-two process/hostname observations, correct terminal metadata, and
empty test-specific queued/started/deferred state after cleanup. Exercise one
failure/retry transition without deleting unrelated jobs.

Package acceptance ends with a successful immutable GHCR publication for the
exact closeout commit. It explicitly does not include an openwepp.org rollout,
full batch, or memory-headroom claim.

## Idempotence and Recovery

All automated tests use temporary run trees and unique Redis keys/job IDs.
Forest integration must inventory matching jobs before mutation and target
cleanup by the unique test prefix. Never flush a Redis database, clear all
locks, or recursively remove `/wc1`. A failed Forest deployment rolls back to
the recorded pre-test SHA using the canonical `wctl` workflow. A failed stage
remains visible and retryable; do not mark it complete manually.

Git changes are ordinary commits. Revert the bounded implementation commit if
necessary; never rewrite public `master`. GHCR tags are immutable evidence and
must not be overwritten.

## Artifacts and Notes

Retain concise, sanitized evidence under this package. Do not retain secrets,
Redis passwords, environment dumps, full worker logs, proprietary run inputs,
or large model outputs. Record counts, timestamps, job IDs, revisions, digest,
and the minimum log excerpts needed to prove ordering and cleanup.

## Interfaces and Dependencies

Use existing `rq.Queue`, `rq.job.Dependency`, submission locking, job-ID
generation, Redis settings, `BatchRunner`, `RedisPrep`, StatusMessenger, and
NoDb APIs. Add no package dependency. Keep public task annotations synchronized
in `wepppy/rq/batch_rq.pyi`. The exact new phase/task names may follow repository
naming after inspection, but their responsibilities and two-job topology are
fixed by this plan.

Revision note: created 2026-09-11 to encode Roger Lew's requested existing-
queue RQ task boundary, Forest execution, full-suite/push/GHCR gates, and
post-close openwepp.org integration boundary.
