# Security Review - Fork/Archive Serial Queue Isolation

## Metadata

- **Package**: `docs/work-packages/20260803_fork_archive_serial_queue/`
- **Reviewer**: pending independent reviewer
- **Date**: pending
- **Scope reviewed**: pending accepted checkpoint and implementation diff
- **Commit/branch context**: pending standalone contract ancestor
- **Related artifacts**:
  - Contract decision:
    `artifacts/2026-08-04_contract_decision.md`
  - Correctness review: pending
  - Forest/wepp3 rollout evidence: pending

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: queue wiring, worker deployment, run-tree copy/archive,
  destructive restore, cancellation/rollback, and privileged job telemetry are
  changed or relied upon.
- **Threat model assumptions**:
  - Existing fork/archive/restore authentication and run authorization remain
    unchanged and are covered by retained regressions.
  - wepp1, wepp2, and wepp3 share the production Redis/NAS contract, so any
    additional consumer on wepp1 or wepp2 can break the intended one-worker
    boundary.
  - wepp3 otherwise runs no containers; the dedicated service must not acquire
    dependencies that silently start unrelated worker/report containers.
  - Accepted jobs may wait for hours, making submission-time authorization,
    confirmation, lock, and source/destination state potentially stale by
    dispatch.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-TBD | TBD | Pending review | Complete after the accepted checkpoint and implementation exist. | Pending | Independent review required. | Open |

## Verdict

- **Gate status**: `fail` (not yet reviewed)
- **Unresolved findings**:
  - High: pending
  - Medium: pending
  - Low: pending
- **Release recommendation**: hold until independent review is complete and no
  high/medium finding remains.

## Required Surface Checks

### Auth, Session, and Authorization

- [ ] Existing fork/archive/restore JWT/session/CAP and run-access checks are unchanged.
- [ ] Queue wait and cancellation do not bypass ownership or disclose another job.
- [ ] Admin queue listings retain Admin/Root and `rq:status` boundaries.

### Secrets and Credential Handling

- [ ] The worker mounts only the same required secret-file inputs as the adjacent worker.
- [ ] No Redis password or environment dump appears in commands, logs, or artifacts.
- [ ] No new secret or inline credential is introduced.

### Input Validation and Output Safety

- [ ] Queue names are server constants, not user-controlled request values.
- [ ] UI guidance and job metadata remain safely escaped.
- [ ] API response/error contracts remain unchanged.

### File System and Run-Tree Boundaries

- [ ] Fork/archive/restore remain confined to authorized run roots.
- [ ] Restore revalidates approved dispatch-time safety before deleting files.
- [ ] Fork destination readiness/catalog behavior cannot expose unrelated data.

### Queue, Worker, and Subprocess Surfaces

- [ ] Exactly three intended enqueue sites move and graph/catalog evidence is current.
- [ ] Dev and Forest have one worker process; production has one on wepp3 and
  none on wepp1/wepp2.
- [ ] Starting the wepp3 service does not start `rq-worker`, `rq-worker-batch`,
  `f-esri`, or `weppcloudr`.
- [ ] Downstream undisturbify jobs retain their existing queues.
- [ ] Queued/started cancellation and stale-marker cleanup remain correct.
- [ ] D-state recovery does not introduce an unauthorized second consumer.

### Network and External Integrations

- [ ] No port, proxy, endpoint exposure, outbound request, or dependency is added.

### CI/CD and Deployment

- [ ] All supported compose combinations render before deployment.
- [ ] Drain-first cutover prevents legacy/new queue overlap.
- [ ] Rollback keeps the worker until its queue and registries drain.
- [ ] DB 9 flush is not used to conceal stranded jobs.

### Data Integrity, Locking, and Concurrency

- [ ] Archive and restore active-job exclusion still covers queued states.
- [ ] Restore conflict behavior is explicit and tested before destructive removal.
- [ ] Fork/archive execution-time state and queued destination behavior match the accepted contract.
- [ ] No more than one in-scope job is started in live acceptance.

### Logging, Monitoring, and Incident Readiness

- [ ] Default operator tools show `fork-archive`, queue depth, state, and worker.
- [ ] Zero-worker and D-state danger signals are documented and observable.
- [ ] Forest/wepp3 evidence identifies worker host/container without secrets.
- [ ] Wepp3 Redis ingress is restricted, required secrets/mount permissions are
  present, and out-of-band fencing is tested.

## Validation Evidence

- Automated checks: pending.
- Manual local serialization: pending.
- Forest cutover/rollback: pending.
- wepp3 canary/observation: pending.

## Residual Risk

- **Expected residual risks**: intentional head-of-line blocking; no automatic
  failover; an NFS D-state process may not respond to cancellation; project
  state can change during queue wait subject to the accepted conflict/guidance
  contract.
- **Follow-up packages/issues**: pending characterization of stronger restore
  revision detection and archive-console queued cancellation.

## Sign-off

- **Security reviewer**: pending
- **Package owner**: pending
