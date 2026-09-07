# Fork Read Retry and Failure Reporting Hardening

**Status**: Open; contract checkpoint preparation
**Started**: 2026-09-07 UTC (2026-09-06 Pacific)
**Stable ID**: FORK-READ-01
**Security impact**: High (filesystem reads and RQ failure callbacks); dedicated security review required.

## Purpose and Scope

Fix transient required-NoDb reads during WEPP preparation and report failed
fork prerequisites without waiting for a blocked completion job. The incident
is recorded in [RCDS NFS evidence](../../infrastructure/ui-rcds-nfs-vs-dev-nfs.md#production-incident-fork-preparation-file-visibility-failures-2026-09-06).
Operator hypothesis: the fork's burst of small-file activity triggers the
visibility failures. Worker placement is evidence, not a demonstrated cause;
this package makes no wepp3-specific workaround or claim of NAS root cause.

Included: opt-in bounded read retries for ENOENT/ESTALE during initial WEPP
preparation controller loading; direct filesystem errors with errno preserved;
server-bound failure reporting for fork WEPP children; tests, contracts, ADR,
operator/user/developer guidance, and independent reviews.
Excluded: filesystem mount tuning, whole-job/write retries, model algorithms,
account registration, automatic production reruns, and production deployment.
No schema or model parameter changes. Existing optional controller absence
continues to return None; malformed/empty required data and permission errors
remain explicit failures. Existing artifacts and successful outputs are unchanged.

## Success Criteria

- [ ] Transient initial read failures recover without repeating mutations.
- [ ] Permanent failures preserve original exception/errno and bounded telemetry.
- [ ] Failed fork descendants set durable failure and notify source fork status.
- [ ] No stale/foreign callback changes another fork; successful terminal state is protected.
- [ ] Focused, real filesystem/Redis/RQ, broad and graph gates pass or gaps are recorded.
- [ ] Independent correctness, QA, and security findings are dispositioned.

## Related Work and Decisions

Reuse atomic NoDb publication and strict cache signatures from
[NoDb contract](../../schemas/nodb-persistence-concurrency-contract.md).
Related precedents: [deferred recovery](../20260821_deferred_job_retry_recovery/package.md),
[serial fork queue](../20260803_fork_archive_serial_queue/package.md), and
[Omni fork hardening](../20260802_omni_fork_symlink_retarget_hardening/package.md).
Keep their queue selection, ownership and strict dependency behavior. Unlike
writer-side readiness checks, this change bounds actual reads on the consumer.

Workflow retry parameterization is recorded in
[ADR-0049](../../adrs/ADR-0049-fork-preparation-read-retry.md).
The user authorized scaffolding and implementation in this session, including
retries, errno diagnostics, and prerequisite failure reporting.

## Observation and Rollout

Owner: WEPPcloud operators (Roger). Use recurrence-triggered observation:
record retries/recoveries/exhaustions with host, run, job, path, errno, attempts
and elapsed time. Danger signals are permanent errors being retried, increased
healthy-path latency, deferred forks without failure status, and repeated NAS
errors despite retries. Any recurrence opens a new incident referencing this
package. Review/remove retries only after an isolated NAS/load reproduction
shows they are unnecessary, preserving original-error and failure-status behavior.

Before production rollout, exercise the real fork/undisturbify workflow with
production-equivalent identities, mounts and orchestration. Local integration
and injected errors do not prove production NAS recovery. This is a rollout
gate, not permission to mutate the user's affected runs.
