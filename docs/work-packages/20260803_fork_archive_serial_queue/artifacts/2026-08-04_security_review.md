# Security Review - Fork/Archive Serial Queue Isolation

## Metadata

- **Package**: `docs/work-packages/20260803_fork_archive_serial_queue/`
- **Reviewer**: independent operations/security control review (Archimedes)
- **Date**: 2026-08-04
- **Scope reviewed**: accepted checkpoint and implementation working-tree diff
- **Commit/branch context**: standalone contract ancestor `bc996d336`
- **Related artifacts**:
  - Contract decision:
    `artifacts/2026-08-04_contract_decision.md`
  - Correctness review: independent implementation review (Darwin)
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
| SEC-01 | High | Cancellation | A status-only check could race worker dequeue and let a non-admin cancel after dispatch. | Independent review plus focused regression. | WATCH the queue list and cancel in one transaction; fail closed if the entry moved. | Closed |
| SEC-02 | Medium | Restore | False-valued lock-status entries were initially treated as locked. | Restore regression. | Filter for `.nodb` entries whose lock state is truthy. | Closed |
| SEC-03 | Medium | Deployment | Enabling the shared Forest profile in the wepp1 layered stack could start a second production consumer. | Rendered prod+wepp1 profile. | Force the inherited service to `scale: 0` in the wepp1 override. | Closed |
| SEC-04 | Medium | Operations | Wepp3 lacked an installable wctl preset and executable cutover/rollback guidance. | Installer/runbook review. | Add the wepp3 preset and fence/drain/start/revert/stop ordering. | Closed |

## Verdict

- **Gate status**: `pass` for repository implementation; live rollout remains
  gated on the recorded preflight and acceptance evidence.
- **Unresolved findings**:
  - High: none
  - Medium: none
  - Low: none release-blocking
- **Release recommendation**: repository change may be committed. Do not cut
  over Forest or wepp3 until its live checklist and evidence are complete.

## Required Surface Checks

### Auth, Session, and Authorization

- [x] Existing fork/archive/restore JWT/session/CAP and run-access checks are unchanged.
- [x] Queue wait and cancellation do not bypass ownership or disclose another job.
- [x] Admin queue listings retain Admin/Root and `rq:status` boundaries.

### Secrets and Credential Handling

- [x] The dedicated worker mounts only the Redis secret required by its task path.
- [x] No Redis password or environment dump appears in commands, logs, or artifacts.
- [x] No new secret or inline credential is introduced.

### Input Validation and Output Safety

- [x] Queue names are server constants, not user-controlled request values.
- [x] UI guidance and job metadata remain safely escaped.
- [x] API response/error contracts remain canonical; the new denial is `403 forbidden`.

### File System and Run-Tree Boundaries

- [x] Fork/archive/restore remain confined to authorized run roots.
- [x] Restore revalidates approved dispatch-time safety before deleting files.
- [x] Fork destination readiness/catalog behavior cannot expose unrelated data.

### Queue, Worker, and Subprocess Surfaces

- [x] Exactly three intended enqueue sites move and graph/catalog evidence is current.
- [x] Dev and Forest define one worker process; production defines one on wepp3 and
  none on wepp1/wepp2.
- [x] Starting the wepp3 service does not start `rq-worker`, `rq-worker-batch`,
  `f-esri`, or `weppcloudr`.
- [x] Downstream undisturbify jobs retain their existing queues.
- [x] Queued/started cancellation and stale-marker cleanup remain correct.
- [x] Documented D-state recovery does not introduce an unauthorized second consumer.

### Network and External Integrations

- [x] No port, proxy, endpoint exposure, outbound request, or dependency is added.

### CI/CD and Deployment

- [x] All supported compose combinations render before deployment.
- [x] Drain-first cutover prevents legacy/new queue overlap.
- [x] Rollback keeps the worker until its queue and registries drain.
- [x] DB 9 flush is not used to conceal stranded jobs.

### Data Integrity, Locking, and Concurrency

- [x] Archive and restore active-job exclusion still covers queued states.
- [x] Restore conflict behavior is explicit and tested before destructive removal.
- [x] Fork/archive execution-time state and queued destination behavior match the accepted contract.
- [ ] No more than one in-scope job is started in live acceptance.

### Logging, Monitoring, and Incident Readiness

- [x] Default operator tools show `fork-archive`, queue depth, state, and worker.
- [x] Zero-worker and D-state danger signals are documented and observable.
- [ ] Forest/wepp3 evidence identifies worker host/container without secrets.
- [ ] Wepp3 Redis ingress is restricted, required secrets/mount permissions are
  present, and out-of-band fencing is tested.

## Validation Evidence

- Automated checks: full Python 5,828 passed/61 skipped; final focused 53
  passed; frontend 105 suites/756 tests; wctl 8 passed; stubs, graph drift,
  broad exceptions, Compose renders, and docs lint passed.
- Manual local serialization: pending.
- Forest cutover/rollback: pending.
- wepp3 canary/observation: pending.

## Residual Risk

- **Expected residual risks**: intentional head-of-line blocking; no automatic
  failover; an NFS D-state process may not respond to cancellation; project
  state can change during queue wait subject to the accepted conflict/guidance
  contract. Restore lock revalidation is a dispatch-time snapshot, not
  cross-mutator isolation. Interruption or privileged cancellation during
  restore can leave a partially restored project; the recovery is to delete
  that incomplete project and retry restore after the queue/NFS path is healthy.
- **Follow-up packages/issues**: stronger restore revision/isolation detection
  is deliberately outside this bounded package and requires separate evidence.

## Sign-off

- **Security reviewer**: Archimedes — approved repository implementation;
  all High/Medium findings closed, no release-blocking Low findings
- **Package owner**: Codex implementation complete; live rollout pending
