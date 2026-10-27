# RQ212 pre-implementation security checkpoint review

## Findings and verdict

No blocking security finding in the proposed contract amendment.

- **Checkpoint gate**: pass.
- **Unresolved security findings**: high 0; medium 0; low 0.
- **Release recommendation**: hold pending implementation, runtime evidence and final independent reviews.
- This approval permits the reviewed checkpoint to become the required ancestor; it does not certify source changes, deployment, historical-job compatibility or package completion.

## Metadata

- **Reviewer**: independent `checkpoint_security` agent (security_reviewer).
- **Reviewed**: 2026-10-27 19:10 UTC.
- **Starting revision**: `9231f2427d33b64f971992ac969fd9420c49afd3`.
- **Scope**: package, tracker, active ExecPlan, `20261027_contract_decision.md`, and the added “RQ 2.12 runtime migration (implementation pending)” section of `docs/schemas/rq-response-contract.md`.
- **Related review**: `20261027_checkpoint_correctness.md`; independent correctness approval remains separately required.
- No application source, dependency input or runtime was modified by this reviewer. Only this artifact was written.

## Security triage and authority

High impact is appropriate: an RQ runtime upgrade can alter serialized state, metadata propagation, cancellation and process cleanup even when application behavior is intended to remain unchanged. A final dedicated security review is mandatory.

The operator explicitly authorized the exact upgrade, local forest development rebuild/recreation, package-owned fault injection, independent reviews and required ancestor revision. The checkpoint confines execution to forest and `docker/docker-compose.dev.yml` through installed `wctl`; it excludes remote hosts, production deployment, branch changes and pushes. It prohibits Redis flushes, queue erasure, volume deletion and unrelated-job/data destruction. Those bounds match the request.

The canonical amendment retains current authentication, ownership, status/disclosure, strict prerequisites and approved finalizer behavior. It does not authorize widening serializers, changing identities/permissions or weakening NoDb and directory locks. No new webhook configuration, delivery or infrastructure is authorized.

## Threat surfaces and required final evidence

These are planned acceptance obligations, not findings against an unimplemented checkpoint.

| Surface | Plausible regression or misuse | Existing boundary retained | Required final evidence |
| --- | --- | --- | --- |
| Auth metadata | A job starts before actor/correlation/profile metadata is persisted, or one job inherits another actor | Request-derived metadata and per-job context reset | Actual worker consumption, root/child propagation and cross-job isolation; inspect persisted metadata without secrets |
| Cancellation | A caller stops another run's work, or an ordinary caller stops a dispatched fork/archive job | `job_routes.py` scope/run checks and Admin/Root restriction; `cancel_job.py` queue-membership transaction | Authorized success and unauthorized rejection through actual API; queued-versus-dispatched race and descendant behavior |
| Process containment | Stopping a workhorse leaves writers alive while directory locks are released | `rq_worker.py` containment, cleanup and retirement behavior | Real descendants, stop/timeout/SIGKILL, lock retention with remaining writers and worker replacement |
| Serialization and discovery | Execution IDs are confused with application job IDs; status normalization or legacy records bypass ownership/disclosure | Opaque IDs, existing serializers and public response contract | Real Redis execution records, worker current-job reporting, status/error serialization and protected maintenance disclosure |
| Historical state and rollback | An old worker consumes newer state, or restoring a snapshot discards newly accepted work | Explicit no-assumption policy, preserved jobs and isolated rollback proof | Six-state 1.16.2 fixtures; support matrix; tested preserving drain/cutover/recovery procedure |
| Webhook egress | New upstream enqueue arguments or persisted job configuration accidentally enable outbound delivery | No application webhook exposure and empty configuration | Search producer/config surfaces, inspect test jobs' persisted webhook configuration, and observe no webhook delivery in ordinary success/failure workflows |
| Supply chain | Upgrade resolves unrelated versions or mismatched worker libraries | Exact RQ target and minimal required transitives | Versioned distribution hashes/source, full pinned-environment resolution, exact versions inside every relevant running container |
| Artifacts and valid states | Security controls reject legitimate empty/legacy projects, hide diagnostics or accept stale model results | Existing project authorization and artifact lifecycle | Real API/model/report readback with original projects preserved and partial/failure artifacts retained |

The current `auth_actor.py` hook persists metadata after calling the underlying enqueue method; source review alone cannot establish whether it precedes worker consumption. This is an existing behavior to measure under both baselines, not authorization for an unrelated redesign. `rq_worker.py` explicitly refuses unsafe lock release and retires supervisors with uncertain/residual writers; verify those paths under the upgraded pool.

The inspected versioned RQ 2.12.0 source initializes `Job.webhooks` to an empty list and `send_webhooks()` iterates that list (`rq/job.py`, extracted under `/tmp/rq212-inventory/rq-2.12.0`). This supports the no-configuration design but does not replace actual no-delivery evidence. Test instrumentation must not persist tokens, cookies, passwords or connection credentials in package artifacts.

## Sequencing and residual uncertainty

The reviewed tree contains the documented unrelated Roads edits, which are outside this gate. No upgrade implementation was present at review. Both checkpoint reviews and their disposition must precede the standalone ancestor commit; final reviewers must verify ancestry and actual source revision.

Before changing or recreating services, account for the shared source bind mount as well as dependency images: a source edit may become visible to an old process before a rebuilt image runs. Retain active-job and effective-configuration snapshots, preserve the original image, and use the planned safe drain/cutover sequence. This is an execution obligation within existing authority, not a request for new infrastructure.

Historical-job support, full dependency compatibility, no-webhook runtime evidence, actual-project artifact parity and production-equivalent execution remain unproven at this checkpoint. None is accepted as residual release risk. The package must remain open until its required evidence and final reviews pass. Production remains outside scope.

## Validation

Read the checkpoint and canonical amendment, inspected current actor/cancellation/worker boundaries and the downloaded versioned RQ webhook initialization/delivery implementation, and checked the current diff/base revision. No runtime tests or operational actions were performed by this reviewer. `wctl doc-lint --path` for this artifact passed with 0 errors and 0 warnings; the `uk2us` preview produced no changes.

## Sign-off

Independent security checkpoint approval: `checkpoint_security`, 2026-10-27. Final security approval remains pending actual implementation and acceptance evidence.
