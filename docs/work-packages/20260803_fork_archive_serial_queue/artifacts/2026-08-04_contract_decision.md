# Contract Decision Draft - Fork/Archive Serial Queue Isolation

**Status**: Operator-approved canonical checkpoint candidate; dual review and
standalone ancestor are pending.
**Prepared**: 2026-08-04 05:38 UTC
**Starting implementation revision**:
`d63df477c887d59e813542a1c2f22730a7f75faa`
**Proposed stable ID**: SURF-03A / GOV-00A-M1G

## Operator Direction

On 2026-08-03 PDT, Roger Lew requested one worker for a combined fork/archive
queue across development, Forest test production, and production, plus
fork/archive UI guidance explaining that accepted jobs may wait in the queue
before dispatch. This direction authorizes discovery and work-package
scaffolding. On 2026-08-03 PDT, after the scaffold recorded the exact queue,
restore, visibility, UI, rollout, and rollback proposal and was pushed at
`d63df477c887d59e813542a1c2f22730a7f75faa`, Roger Lew directed Codex to
"execute Scaffold fork archive serial queue work package." Governance review
correctly found that direction did not approve decisions finalized afterward.
On 2026-08-04 PDT, after Codex restated the complete final matrix, Roger Lew
explicitly replied "I approve the final matrix." After further cancellation
discussion, Roger Lew gave the superseding direction that existing buttons
remain, authorized project users may cancel a `fork-archive` job while queued,
and only Admin or Root may cancel it after it starts. On 2026-08-04 PDT he
confirmed this exact queue-specific interpretation and directed Codex to
proceed. This authorizes the exact matrix below without advancing or closing
SURF-03, SURF-04, SURF-07, or SURF-17.

## Proposed Normative Delta

1. RQ queue name is `fork-archive` and compose service name is
   `rq-worker-fork-archive`.
2. The top-level `fork_rq`, `archive_rq`, and `restore_archive_rq` jobs enqueue
   on `fork-archive`. Their request authorization, payloads, response shapes,
   timeouts, job markers, status channels, copy/archive/restore implementation,
   and terminal semantics remain unchanged except for separately approved
   dispatch-time restore revalidation.
3. `delete-archive` remains synchronous. Any WEPP/model jobs started by an
   undisturbifying fork retain their existing queue selection.
4. Exactly one worker process consumes `fork-archive` in development and Forest
   test production. Production has one global consumer on wepp3, which has the
   production NFS mount and no other containers. A wepp3-specific compose file
   contains only this worker and starts without `rq-worker`, `rq-worker-batch`,
   `f-esri`, or `weppcloudr`. The repurposed HPC compose, wepp1, and wepp2 do not
   contain or consume it.
   - Development starts the service with the normal dev stack.
   - Forest uses an explicit `fork-archive` Compose profile in the production
     base stack.
   - Wepp1 does not activate that profile.
   - Wepp3 uses `docker/docker-compose.prod.wepp3.yml`; the wepp2 worker-only
     compose does not define the service.
5. Queue order is FIFO under ordinary RQ semantics. A second job may remain
   queued for the complete duration of the first. No maximum queue-wait promise,
   automatic failover, or extra worker is introduced.
6. `wctl rq-info`, detailed job summary, rq-engine Admin recent/active listings,
   and WEPPcloud RQ info-details include `fork-archive` in their default queue
   set after `default` and `batch`. Explicit custom queue queries remain
   supported. `wctl rq-info --service rq-worker-fork-archive` runs inspection
   inside the dedicated container; the wepp3 runbook also uses host-local
   Compose/process-state checks that do not depend on Redis.
7. Both user consoles state that fork/archive/restore work runs one job at a
   time and an accepted job may remain queued before it starts. Fork/archive
   actions operate on project state when the worker begins, not an immutable
   submission-time snapshot. Restore guidance states that it replaces current
   project files and that users must not edit the project while it is queued or
   running.
8. `archive_rq` retains its existing worker-start NoDb lock recheck.
   `restore_archive_rq` performs the same `.nodb` lock-status revalidation after
   archive integrity/member/disk checks and immediately before removing any
   current run-root entry. Any active lock fails the job explicitly without
   removing current files. No run-revision token or new lock abstraction is
   introduced; users are told not to edit while restore is queued or running.
9. Fork retains its existing destination ownership/registration and
   readiness-gated success link. Because destination directory/database
   registration precedes enqueue, an authorized queued destination can appear
   incomplete in the Runs catalog or by direct URL. This package accepts that
   existing compatibility behavior, does not advertise the destination link in
   the fork console before readiness, and records stronger catalog suppression
   as a separate follow-up rather than expanding this queue change.
10. Rollout starts the new worker before route cutover, inventories/drains
    legacy in-scope jobs from `default`, then deploys the enqueue-site change.
    Rollback first fences admission to all three actions, then keeps the
    dedicated worker online until all `fork-archive` executable registries are
    empty. If wepp3 is D-state, admission remains fenced until the host is
    fenced or the old process is proven dead. Only then may operators revert
    enqueue selection, stop the worker, and reopen admission.
11. Exact static console guidance is:
    - Fork: "Fork and archive operations run one at a time. Your accepted fork
      may remain queued before it starts. The fork copies the source project
      state available when the worker begins, so avoid editing the source while
      the job is queued or running."
    - Archive: "Fork, archive, and restore operations run one at a time. An
      accepted request may remain queued before it starts. Archive creation
      uses project state available when the worker begins. Restore replaces the
      current project files; do not edit the project while a restore is queued
      or running."
12. Existing cancellation buttons remain. For jobs whose origin is
    `fork-archive`, any caller who passes the existing run-access authorization
    may cancel while the job is queued. Once the job is started, rq-engine
    permits cancellation only when the authenticated caller has Admin or Root
    role; other callers receive an explicit forbidden response. The server
    enforces this fail-closed at the cancellation mutation boundary: a
    non-Admin/Root path may remove the job only while it is still queued and
    must reject intermediate/handoff/started states without invoking any stop
    command. Cancellation behavior for jobs
    from every other queue and host-level operator recovery remain unchanged.
    No new archive-console cancellation control is added.
13. The wepp3 worker mounts `/wc1` and only geodata and secret inputs proven
    necessary by focused import/startup evidence. It does not mount the Docker
    socket or unrelated Discord, provider, Flask, or Postgres credentials.

## Applicable Canonical Contracts and Owners

- `docs/work-packages/20260729_pure_ui_archive_console_contract/package.md`
  (SURF-03): archive/restore/delete actions, shared active slot, worker and
  filesystem safety.
- `docs/work-packages/20260729_pure_ui_fork_console_contract/package.md`
  (SURF-04): fork submission, tracking, cancellation, worker copy, and terminal
  presentation.
- `docs/work-packages/20260728_pure_ui_rq_info_details_contract/package.md`
  (SURF-17): ordered queue grouping and privileged operational metadata.
- `docs/work-packages/20260728_pure_ui_rq_job_dashboard_contract/package.md`
  (SURF-07): the existing shared cancellation button remains, while server-side
  authorization becomes queue-origin and state aware for `fork-archive` jobs.
- `docs/schemas/rq-response-contract.md`: response and error shapes remain
  unchanged.
- `docs/schemas/weppcloud-session-contract.md`: renewable session/auth failure
  behavior remains unchanged.
- `docs/schemas/nodb-persistence-concurrency-contract.md`: NoDb locks/cache and
  persistence safeguards must not be weakened.
- `docs/standards/contract-first-change-standard.md`: bounded cross-owner
  enhancement checkpoint and standalone ancestor gate.

SURF-03 currently excludes queue edges, and SURF-04 explicitly excludes queue
changes. This is therefore an intended bounded enhancement, not a conformance
fix. Register it before implementation; do not silently amend either verified
owner from production code.

## Compatibility and Data Impact

No route, successful response key/type, archive format, or run artifact changes.
Queue origin changes from `default` to `fork-archive` for three job types. For
those jobs only, a non-Admin/Root caller who could previously cancel after
start now receives the canonical forbidden response; queued cancellation and
other queues retain existing behavior. The handoff race fails closed without a
non-Admin stop command. Jobs accepted before cutover remain in their original
queue and are not automatically migrated.

No project data/schema mutation is proposed. The longer queue wait changes
timing, which can expose existing execution-time semantics: fork/archive may
observe later project state, a restore confirmation may age before dispatch,
and a fork destination may remain registered but incomplete longer. These
timing effects require explicit acceptance and regression/operational evidence.

## Security and Operational Impact

Impact is high because this changes queue/deployment wiring, destructive
restore timing, run-tree copy/archive work, cancellation authorization,
rollback, and
privileged operational metadata. The implementation adds no secret, port,
public route, dependency, or external egress. One worker reduces concurrent NAS
pressure but creates intentional head-of-line blocking and a single dispatch
point. A D-state worker must be treated as an NFS incident; starting a second
worker is not an approved recovery.

## Regression and Acceptance Plan

- Exact queue-constructor tests for fork, archive create, and restore.
- Structural compose tests for one primary consumer and worker-only
  non-consumption.
- wctl registry-repair/command tests and job-listing/Admin/RQ info tests for the
  new default queue.
- Actual-template guidance tests and existing client polling/recovery tests.
- Dispatch-time restore conflict test proving failure before deletion.
- Queued fork destination catalog/readiness characterization.
- Regenerated RQ graph/catalog with three `fork-archive` edges.
- Live two-job FIFO serialization plus independent default-queue dispatch.
- Forest and wepp3 worker placement, legacy-drain, rollback, and observation
  evidence. Cancellation regressions cover queued project-user success,
  queued-to-handoff race rejection without a stop command, started project-user
  rejection, and started Admin/Root success.

## Ratified Operator Decisions

- Include restore with fork and archive creation.
- Use literal names `fork-archive` and `rq-worker-fork-archive`.
- Keep the sole production consumer on wepp3 with no automatic wepp1/wepp2
  failover.
- Accept execution-time project state and the exact UI wording above.
- Recheck `.nodb` lock status immediately before restore deletion; do not add a
  revision token in this package.
- Accept existing authorized queued fork-destination visibility while retaining
  readiness-gated console navigation.
- Preserve existing cancellation buttons and add no archive-console button.
- For `fork-archive` only, allow existing authorized project users to cancel
  queued jobs and require Admin or Root after start; preserve all other queue
  cancellation behavior.

## Checkpoint Gate

Implementation conformance is pending. The register and affected concise
contracts are amended and the operator has approved the exact matrix. Before
production code, tests, compose, or UI files change, two independent read-only
reviews and their disposition must be recorded and these documents must be
committed together as a standalone ancestor. Record the ancestor revision in
the tracker and ExecPlan.
