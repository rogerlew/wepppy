# Fork/Archive Serial Queue Isolation

**Status**: GOV-00A-M1G checkpoint review (2026-08-04 UTC)
**Timezone**: UTC
**Stable ID**: SURF-03A / GOV-00A-M1G

## Overview

Production evidence shows that a full-output fork can materially increase
NAS/NFS queuing and that an archive worker can remain pinned in an NFS RPC wait
while its RQ heartbeat stays fresh. This package will isolate the top-level
fork, archive-create, and archive-restore jobs on one FIFO RQ queue serviced by
one worker process, so at most one of these NAS-intensive operations is
dispatched at a time in each supported deployment.

The user-facing fork and archive consoles will explain that accepted jobs may
remain queued before they start. The package also owns the operator visibility,
safe staged cutover, rollback, and data-integrity checks needed to make that
queue real in development, Forest test production, and production through a
dedicated wepp3 consumer.

## Objectives

- Route `fork_rq`, `archive_rq`, and `restore_archive_rq` to one proposed queue
  named `fork-archive` without changing their API response shapes.
- Run exactly one `rq-worker-fork-archive` worker process in development and
  Forest test production.
- Preserve a single production consumer on wepp3. Neither wepp1 nor wepp2 may
  consume `fork-archive` unless a later operator-approved topology change
  replaces this contract.
- Make the queue visible in `wctl rq-info`, job summaries, rq-engine Admin job
  listings, and the RQ info-details page.
- Add concise, accessible queue-wait guidance to the fork and archive consoles.
- Prevent the longer queue wait from silently weakening restore dispatch safety
  or exposing misleading fork-destination readiness.
- Prove a drain-first Forest and wepp3 rollout and a rollback that does not
  strand jobs already enqueued on either queue.

## Scope

### Included

- `wepppy/microservices/rq_engine/fork_archive_routes.py` queue selection for
  fork, archive creation, and archive restore.
- `wepppy/microservices/rq_engine/job_routes.py` and
  `wepppy/rq/cancel_job.py` for the `fork-archive`-specific queued-user versus
  started-Admin/Root cancellation boundary.
- `docker/docker-compose.dev.yml` and `docker/docker-compose.prod.yml` worker
  definitions for development and Forest test production.
- A wepp3-specific `rq-worker-fork-archive` definition in
  `docker/docker-compose.prod.wepp3.yml`, deployed alone without
  `rq-worker`, `rq-worker-batch`, `f-esri`, or `weppcloudr` dependencies.
- Explicit non-consumer validation for `docker/docker-compose.prod.wepp1.yml`
  on wepp1 and `docker/docker-compose.prod.worker.yml` on wepp2.
- Explicit exclusion of `docker/docker-compose.dev.hpc.yml`, which is being
  repurposed and is no longer a supported deployment target for this worker.
- Queue visibility defaults in `wepppy/rq/job_listings.py`,
  `wepppy/rq/job_summary.py`, `tools/wctl2/commands/rq.py`, rq-engine Admin
  descriptions, WEPPcloud RQ info details, and their tests.
- `wctl rq-info --service rq-worker-fork-archive` plus wepp3 host-local
  container/process/D-state inspection documented independently of Redis.
- RQ dependency graph/catalog regeneration and a live job-tree check.
- Fork/archive console templates, source/built archive client parity when
  needed, exact render/client regressions, and user guidance covering queued
  wait and execution-time state.
- Dispatch-time restore safety characterization and the smallest approved
  revalidation needed before destructive removal begins.
- Fork-destination catalog/readiness characterization for the longer interval
  between destination registration and worker dispatch.
- Developer and operator documentation, staged rollout, observation, incident
  triage, and rollback evidence.

### Explicitly Out of Scope

- `delete-archive`, which remains a synchronous single-file removal.
- Archive download delivery, ZIP format/compression, rsync copy semantics, and
  NFS mount or NAS hardware changes.
- Moving WEPP or other child jobs spawned by an undisturbifying fork; those jobs
  retain their existing queue topology.
- Adding a `fork-archive` consumer to wepp1 or wepp2, automatic failover,
  autoscaling, or a second worker.
- A new queue abstraction or environment-configurable queue name.
- A new archive-console cancellation button or cancellation changes for queues
  other than `fork-archive`.
- Scientific parameters, formulas, units, thresholds, fallbacks, or project
  data/schema changes.

## Implementation Fidelity and Evidence

- **Fidelity target**: faithful queue cutover preserving current submission
  authorization, payload, copy/extraction, terminal-state, and result contracts,
  with only the approved `fork-archive` cancellation authorization change.
- **Authoritative source paths**:
  `wepppy/microservices/rq_engine/fork_archive_routes.py`,
  `wepppy/microservices/rq_engine/job_routes.py`,
  `wepppy/rq/cancel_job.py`,
  `wepppy/rq/project_rq_fork.py`,
  `wepppy/rq/project_rq_archive.py`, and the SURF-03/SURF-04/SURF-07/SURF-17
  concise contracts.
- **Cutover proof required**: live jobs submitted through each public action
  have origin `fork-archive`; only one registered worker services that queue;
  a second job remains `queued` until the first becomes terminal; ordinary
  default/batch work continues independently.
- **Acceptance evidence type**: both focused fixtures and live development plus
  Forest job/worker evidence, followed by a bounded wepp3 canary.

## Stakeholders

- **Primary**: WEPPcloud users who fork, archive, or restore projects and
  operators responsible for NAS health.
- **Reviewers**: RQ maintainer, Docker/operator maintainer, fork/archive UI
  owners, and two independent checkpoint reviewers.
- **Security Reviewer**: an independent reviewer for queue, worker, filesystem,
  destructive restore, deployment, and rollback surfaces.
- **Informed**: Forest and wepp1/wepp2/wepp3 operators and maintainers of the RQ
  Admin dashboards and `wctl` tooling.

## Success Criteria

- [ ] The bounded enhancement is registered and its exact contract checkpoint,
  two independent reviews, and disposition are committed as a standalone
  ancestor before production implementation edits.
- [ ] Fork, archive-create, and restore jobs are enqueued with origin
  `fork-archive`; delete and undisturbify child jobs retain existing behavior.
- [ ] Dev and Forest test production compose render valid
  configurations with one worker process for `fork-archive`.
- [ ] The wepp3-specific compose renders one dependency-minimal service and
  does not mount the Docker socket or unrelated credentials.
- [ ] Production evidence proves wepp3 is the sole consumer and wepp1/wepp2
  remain non-consumers.
- [ ] Two submitted jobs demonstrate FIFO serialization: the second remains
  queued while the first is started, then dispatches after the first is
  terminal.
- [ ] Fork and archive consoles visibly and accessibly explain queue wait; the
  guidance covers execution-time copy/archive state and destructive restore.
- [ ] Restore revalidates the approved dispatch-time safety conditions before
  removing current run files.
- [ ] The longer pre-dispatch fork-destination window is characterized and has
  either passing readiness/catalog behavior or an operator-approved bounded
  follow-up recorded before production rollout.
- [ ] `wctl rq-info`, `--detail`, rq-engine Admin listings, and WEPPcloud RQ
  info details include the new queue by default.
- [ ] `wctl rq-info --service rq-worker-fork-archive` targets the dedicated
  container, and operator docs retain Redis-independent host-local checks.
- [ ] The RQ dependency catalog and static graph name `fork-archive` for all
  three enqueue sites and `wctl check-rq-graph` passes.
- [ ] Rollout drains or inventories legacy default-queue fork/archive/restore
  jobs before cutover; rollback leaves the dedicated worker running until its
  queue drains.
- [ ] Focused, frontend, Docker, wctl, graph, broad test, documentation, and
  independent security/correctness gates pass.

## Parameterization ADR Gate

- **Parameterization change present**: no.
- **ADR required**: no.
- **ADR links**: none.
- **Decision provenance captured**: yes. The operator requested a single
  fork/archive worker and queued-wait UI guidance, selected wepp3 production
  placement, explicitly approved the final matrix, superseded its cancellation
  clause with the queue-specific queued-user/started-Admin-or-Root rule, and
  directed execution on 2026-08-04 PDT. The canonical matrix is in
  `artifacts/2026-08-04_contract_decision.md`.

Queue topology is operational behavior, not scientific parameterization. Any
new timeout, age threshold, retry heuristic, or fallback behavior must be
re-triaged against `docs/standards/parameterization-adr-standard.md` before it
is added.

## Compatibility and Data Impact

Routes, successful response shapes, archive formats, and project schemas remain
unchanged. Queue origin changes for the three jobs. For `fork-archive` jobs
only, a non-Admin/Root caller who could previously cancel after start now
receives the canonical forbidden response; queued cancellation and every other
queue retain existing behavior. A dispatch handoff race fails closed and never
lets the non-Admin path issue a stop command. No project data migration is
required.

## Dependencies

### Prerequisites

- SURF-03 archive console and SURF-04 fork console verified contracts.
- SURF-17 RQ info-details queue grouping contract.
- The current NFS incident/benchmark evidence in
  `docs/infrastructure/ui-rcds-nfs-vs-dev-nfs.md`.
- Registration as a bounded cross-owner enhancement under
  `docs/standards/contract-first-change-standard.md`.
- Operator approval of the exact contract matrix, including restore scope,
  production worker placement, queued-state wording, and rollback.

### Blocks

- Supported production serialization of user-triggered fork/archive/restore
  work on the NAS-backed run tree.

## Related Packages

- **Depends on**:
  `../20260729_pure_ui_archive_console_contract/` and
  `../20260729_pure_ui_fork_console_contract/`.
- **Related**:
  `../20260728_pure_ui_rq_info_details_contract/`,
  `../20260729_fork_destination_readiness_hardening/`, and
  `../20260802_omni_fork_symlink_retarget_hardening/`.
- **Operational precedent**:
  `../20260619_dedicated_download_service/`.
- **Follow-up**: stronger run-revision conflict detection only if staging
  evidence and operator review justify a separate bounded scope.

## Timeline Estimate

- **Expected duration**: 3-5 focused sessions plus Forest validation and a
  wepp3 canary/observation window.
- **Complexity**: medium-high.
- **Risk level**: high because this changes queue/deployment wiring and extends
  the delay before destructive or state-copying filesystem operations begin.

## Security Impact and Review Gate

- **Security impact triage**: high.
- **Dedicated security review required**: yes.
- **Triage rationale**: queue wiring, worker deployment, run-tree copy/archive,
  destructive restore, cancellation/rollback, and privileged job telemetry are
  all changed or relied upon.
- **Security review artifact**:
  `docs/work-packages/20260803_fork_archive_serial_queue/artifacts/2026-08-04_security_review.md`.

## Hardening and Callus Softening

- **Failure signatures**: archive job
  `7495a2a5-a651-4e8d-ae82-377b52f1e5fb` pinned in
  `rpc_wait_bit_killable` for more than five hours; full-output fork job
  `381be2e3-65a9-4882-87ca-46cbf4ecf86e` contributed to NAS contention while
  fresh RQ heartbeats continued.
- **Related prior hardening efforts**: the NFS benchmark/incident note and the
  dedicated download service package.
- **Health signals**: never more than one started fork/archive/restore job;
  ordinary default/batch dispatch remains healthy; NAS queue/latency does not
  show concurrent fork/archive amplification.
- **Danger signals**: `fork-archive` has queued jobs and zero workers; a worker
  is in D state; default queue still receives new in-scope jobs; old default and
  new dedicated jobs overlap during rollout; restore begins after conflicting
  run mutation; users treat queued as failed.
- **Observation window**: Forest acceptance followed by at least 14 days after
  wepp3 rollout.
- **Temporary calluses introduced**: one-worker serialization is an intentional
  containment control owned by WEPPcloud operations. Review after the
  observation window; do not add a second worker to address queue latency
  without new NAS evidence and operator approval.
- **Callus softening hypothesis**: concurrency may be reconsidered only if
  representative NAS evidence shows safe parallelism and a separately reviewed
  topology change preserves the same rollback and UI contracts.

## References

- `docs/infrastructure/ui-rcds-nfs-vs-dev-nfs.md` - NFS incidents and loaded
  full-output fork benchmark.
- `docker/AGENTS.md` - canonical development, Forest test-production, and
  wepp1 application deployment map.
- `docker/docker-compose.dev.yml` - development worker pools.
- `docker/docker-compose.prod.yml` - Forest base production topology.
- `docker/docker-compose.prod.wepp1.yml` - wepp1 application override that must
  remain a non-consumer.
- `docker/docker-compose.prod.worker.yml` - wepp2 worker-only definition that
  must remain a non-consumer.
- `docker/docker-compose.prod.wepp3.yml` - sole production `fork-archive`
  worker definition.
- `wepppy/microservices/rq_engine/fork_archive_routes.py` - three enqueue sites.
- `wepppy/rq/job-dependencies-catalog.md` - canonical enqueue/dependency
  inventory.
- `wepppy/weppcloud/templates/controls/fork_console_control.htm` and
  `archive_console_control.htm` - user-visible guidance surfaces.
- `tools/wctl2/commands/rq.py` - operator queue visibility and registry repair.
- `docs/standards/contract-first-change-standard.md` - required checkpoint and
  bounded enhancement sequencing.

## Deliverables

- Accepted contract decision, queue matrix, reviews, and standalone ancestor.
- Queue/route/compose/UI/observability implementation with focused regressions.
- Updated RQ graph/catalog and developer/operator documentation.
- Forest and wepp3 rollout, serialization, worker-placement, rollback, and NFS
  observation evidence.
- Dedicated security and independent correctness review artifacts.

## Follow-up Work

- Decide from characterization evidence whether queued restore requires a
  stronger source-revision token beyond dispatch-time lock revalidation.
- Decide whether ordinary users need an archive-console cancellation affordance
  for long queued waits; keep it outside this package unless explicitly
  approved.
