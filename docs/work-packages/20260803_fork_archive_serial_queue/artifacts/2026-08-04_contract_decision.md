# Contract Decision Draft - Fork/Archive Serial Queue Isolation

**Status**: Draft; operator approval, registration, dual review, and standalone
ancestor are pending.
**Prepared**: 2026-08-04 05:38 UTC
**Starting implementation revision**: record immediately before checkpoint
review; no production implementation is authorized by this draft.
**Proposed stable ID**: SURF-03A / GOV-00A-M1G

## Operator Direction

On 2026-08-03 PDT, Roger Lew requested one worker for a combined fork/archive
queue across development, Forest test production, and production, plus
fork/archive UI guidance explaining that accepted jobs may wait in the queue
before dispatch. This direction authorizes discovery and work-package
scaffolding. It does not yet record approval of every exact decision below.

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
   production NFS mount and no other containers. The service is opt-in in the
   worker-only compose and starts alone without `rq-worker`, `rq-worker-batch`,
   `f-esri`, or `weppcloudr`. The repurposed HPC compose, wepp1, and wepp2 do not
   consume it.
5. Queue order is FIFO under ordinary RQ semantics. A second job may remain
   queued for the complete duration of the first. No maximum queue-wait promise,
   automatic failover, or extra worker is introduced.
6. `wctl rq-info`, detailed job summary, rq-engine Admin recent/active listings,
   and WEPPcloud RQ info-details include `fork-archive` in their default queue
   set after `default` and `batch`. Explicit custom queue queries remain
   supported.
7. Both user consoles state that fork/archive/restore work runs one job at a
   time and an accepted job may remain queued before it starts. Fork/archive
   actions operate on project state when the worker begins, not an immutable
   submission-time snapshot. Restore guidance states that it replaces current
   project files and that users must not edit the project while it is queued or
   running.
8. `archive_rq` retains its existing worker-start NoDb lock recheck.
   `restore_archive_rq` adds the exact ratified dispatch-time revalidation
   before removing any current run-root entry. The checkpoint must decide
   whether lock revalidation alone is sufficient or whether a stronger
   run-revision conflict is required.
9. Fork retains its existing destination ownership/registration and
   readiness-gated success link. Before approval, characterize whether a queued
   destination appears as an incomplete entry in the Runs catalog or direct
   URL and record the accepted treatment.
10. Rollout starts the new worker before route cutover, inventories/drains
    legacy in-scope jobs from `default`, then deploys the enqueue-site change.
    Rollback reverts enqueue selection first and keeps the dedicated worker
    until all its queue registries are empty.

## Applicable Canonical Contracts and Owners

- `docs/work-packages/20260729_pure_ui_archive_console_contract/package.md`
  (SURF-03): archive/restore/delete actions, shared active slot, worker and
  filesystem safety.
- `docs/work-packages/20260729_pure_ui_fork_console_contract/package.md`
  (SURF-04): fork submission, tracking, cancellation, worker copy, and terminal
  presentation.
- `docs/work-packages/20260728_pure_ui_rq_info_details_contract/package.md`
  (SURF-17): ordered queue grouping and privileged operational metadata.
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

The HTTP API is backward compatible: no route, key, type, default, alias, error
envelope, archive format, or run artifact changes. Queue origin changes from
`default` to `fork-archive` for three job types. Jobs accepted before cutover
remain in their original queue and are not automatically migrated.

No project data/schema mutation is proposed. The longer queue wait changes
timing, which can expose existing execution-time semantics: fork/archive may
observe later project state, a restore confirmation may age before dispatch,
and a fork destination may remain registered but incomplete longer. These
timing effects require explicit acceptance and regression/operational evidence.

## Security and Operational Impact

Impact is high because this changes queue/deployment wiring, destructive
restore timing, run-tree copy/archive work, cancellation/rollback, and
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
- Forest and wepp3 worker placement, legacy-drain, cancellation, rollback, and
  observation evidence.

## Decisions Requiring Exact Operator Approval

- Include restore with fork and archive creation.
- Use literal names `fork-archive` and `rq-worker-fork-archive`.
- Keep the sole production consumer on wepp3 with no automatic wepp1/wepp2
  failover.
- Accept execution-time project state and the final UI wording.
- Select the exact restore dispatch-time conflict check.
- Select the accepted queued fork-destination catalog behavior.
- Preserve current archive-console actions without adding cancellation in this
  package.

## Checkpoint Gate

Implementation conformance is pending. Before production code, tests, compose,
or UI files change, this draft must be finalized; the Pure UI register and all
affected concise contracts must be amended; the operator must approve the exact
matrix; two independent read-only reviews and their disposition must be
recorded; and those documents must be committed together as a standalone
ancestor. Record the ancestor revision in the tracker and ExecPlan.
