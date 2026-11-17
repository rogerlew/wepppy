# Resumed operations review

Date: 2026-11-17
Reviewer: independent `ops_security_control_agent` (`destructive_review`)
Reviewed source: `54ee356fd16845e7abf6da59d7df616f8b5fa6ce`
Reviewed tree: `fccb328c62078e22e8283ffebac84c32b59009f4`
Comparison source: `0e861887e132b41b00a108292d7833d21750b146`
Exact local converter image:
`sha256:4487dec16cdb1a0ed735e60f10672c646ecc3b26d0586dbfce93479b9eae98fa`

Verdict: **HOLD: one Medium crash-durability finding remains in the copy/reset
successor; no High finding is open in this scope.** This is an independent source and
test-design review, not a substitute for the integrator's revision-bound runtime
receipt. M5 also requires the other review lanes and the final validation gates.
Publication, deployment, and remote-host parity are not authorized by this review.

## Copy/reset successor review

The sharing/copy authority checkpoint is `bbb216c0b`; this review does not
reopen the operator's public/team inheritance decision. The final copy/reset
source reviewed here is `54ee356fd16845e7abf6da59d7df616f8b5fa6ce`.

The following findings from implementation review are closed in that source:

- Every owned lease release is registered with `ExitStack`, so one release
  failure cannot skip remaining scopes or global-maintenance cleanup.
- Copies require full incoming-byte headroom. They receive no speculative
  reclaim credit for old target bytes that deferred stale cleanup may retain.
- Missing destination receipts with copied bytes fail instead of silently
  omitting those bytes; destination inventory validates accounting before clear.
- Configured containment preserves the default split-root profile topology;
  in-root copies are charged, and missing configuration cannot silently admit
  an evidence-bearing ordinary managed destination.
- Receipt-parent discovery accounts for flattened profile private archives
  whose mapped path lacks the original `archives/` component.
- A pending partial Batch copy must be removed successfully before recopying.
  It cannot be renamed to a second stale copy with uncompleted attribution.
  Tests assert failed removal prevents recopy, preserves the pending marker,
  and eventually restores exact original/copier principal totals.

### OPS-COPY-01 - Medium - copy durability omits linking ancestor directories and retained stale paths

`vector_retention_lifecycle._sync_evidence()` fsyncs files and directories inside
each discovered retained root, then only `target.parent`. A newly copied
`target/roads/vector_upload_attempts/...` therefore does not fsync `target/roads`
or `target`, whose entries link the retained subtree. The marker can be cleared
after ledger readback while those directory entries remain unproven durable.

The same class affects deferred stale cleanup. The helper does not synchronize
`recovery_paths`, and Batch's newly renamed `.stale.*` path is absent from the
pre-operation snapshot. Partial cleanup can remove entries in that retained
tree and then defer; a ledger computed from the remaining bytes must not be
declared durable without synchronizing those directory mutations too.

Required closure: fsync intervening directories through the target and parent
in child-before-parent order, register and synchronize retained recovery/stale
trees after mutation, and retain a real-copy descriptor-path trace that proves
the ancestor and deferred-stale boundaries were synchronized before marker
clearance. Failed synchronization must leave the deterministic obligation.

## Scope and independence

The reviewer inspected committed blobs and the exact successor diff for run and
whole-Batch deletion, the shared rebuild-obligation helpers, the related private
archive lifecycle amendments, and their deterministic recovery tests. Runtime
code and tests were not changed by this reviewer. The retained exact final5
qualification remains the parser/image evidence; this successor does not change
the parser image. Direct Docker readback confirmed that `vector-upload-final5`
uses the image ID above.

The review concentrates on the failure classes in `VUN-QA-FROZEN-03` and
`VUN-QA-FROZEN-06`: pre-mutation authority, lease lifetime, irreversible deletion,
durability, retry identity, and exact accounting. Downstream geometry/report
semantics and browser-session provenance belong to their separate review lanes.

## Finding dispositions

| Finding | Disposition and committed evidence |
| --- | --- |
| Whole-Batch deletion bypassed retention accounting | Closed. `delete_batch_rq()` validates the configured root, retains its active-job check inside the catalog guard, and uses `_batch_retention_delete_guard()`. That guard acquires global maintenance before the Batch and generated child-run upload scopes, records the deterministic `batch_delete` obligation, fsyncs removal, rebuilds the exact-root ledger, and clears obligations only after ownership/readback checks. |
| Missing run retention configuration could mutate TTL/catalog state | Closed. `_retention_delete_root()` runs before the catalog guard; missing identity/root, outside-root targets, the root itself, and symlink targets fail before deletion state or content mutation. TTL marking occurs after successful retention admission. |
| Interrupted or absent-target deletion lost recovery authority | Closed. Both deletion paths retain the globally qualified operation identity and can fsync/reconcile after the target is absent. Partial deletion, post-removal failure, parent fsync failure, and rebuild failure preserve repair obligations until a successful retry. |
| Lost ownership could outlive destructive work | Closed for the tested boundaries. Run deletion checks both global and project ownership before marker creation and each removal attempt. Batch deletion fences `_base` and generated run upload scopes. Reconciliation receives the required scopes, and callers recheck their owned leases before clearing obligations. Injected loss inside removal leaves repair pending. |
| Obligation write failure could erase its Redis authority | Closed. A persistence error no longer removes the Redis obligation because the file may already have been replaced before fsync failed. Both existing and dangling obligation-directory symlinks are rejected before chmod/write; completion validates the configured marker parent. |
| Accounting repair could damage unrelated evidence or reservations | Closed in the test design. Real-Redis tests check retained unrelated bytes, global committed/reserved/inflight totals, deleted principal charges, unrelated committed principal charges, and active principal reservations after retry. No database-wide cleanup is used. |
| Parent deletion could remove a workspace needed by an earlier private-archive repair | Closed by `ee26389f0`. Before creating its marker or permitting destructive mutation, `begin_retention_rebuild_obligation()` reads both authorities and rejects any pending identity other than the exact requested operation/target. The original operation can resume from either surviving authority, reconstruct both markers, and complete before the parent delete proceeds. |

`tests/rq/test_vector_retention_deletion.py` covers run and Batch success,
partial removal, failure after removal, parent fsync failure, global/scope token
loss, rebuild failure, missing/mismatched configuration, target and marker
symlinks, and both `_base` and generated-child scope contention. It calls the
real marker, lease, Lua reservation, and reconciliation functions with isolated
test identities. Metadata/status test doubles do not replace those boundaries.

`tests/rq/test_vector_archive_recovery.py` adds real-authority private-delete
and restore fault coverage: live/incoming identity rejection, partial removal,
file/directory fsync failure, scope loss, Redis-marker loss with the durable
marker retained, symlink substitution, retry convergence, and unrelated evidence
preservation. Private deletion repeats containment checks even when interrupted
repair permits missing provenance, and absent retry fsyncs the bundle parent.

## Successor re-review

The initial operations review covered
`de15403aadbd7a659ef4717e77223ff4890b18c1`. An independent code review then
identified that parent deletion could orphan an earlier private-delete obligation
by removing the workspace required to retry it. That finding superseded the
initial PASS for this failure class. The present review explicitly inspects the
minimal `de15403aa..ee26389f0` correction and updates the accepted source above.

The shared begin helper takes the union of filesystem and Redis pending
identities, excludes only its exact operation/target identity, and fails before
its mkdir/chmod/fsync/marker write if another identity remains. Existing callers
hold global maintenance around this check. It neither silently clears unrelated
repair records nor treats a missing copy as completion. Six real-Redis cases
cover run and Batch deletion with both markers, filesystem-only, and Redis-only
authority. They assert retained content and no TTL/cache/database mutation,
resume the identical earlier operation, reconcile/clear it, and then permit
parent deletion. This closes the reported recovery dependency defect without
changing parser/image authority or introducing a second recovery mechanism.

## Validation boundary

The reviewer directly performed:

- `git rev-parse de15403aa` and `git rev-parse 'de15403aa^{tree}'`;
- committed-source readback with `git show de15403aa:<path>` and the bounded
  successor diff;
- `git diff --check 0e861887e de15403aa`, which passed; and
- `docker inspect vector-upload-final5 --format '{{.Image}}'`, which returned
  the exact image ID recorded above.

For the successor, the reviewer also resolved `ee26389f0` and its tree, inspected
the complete three-file `de15403aa..ee26389f0` diff and the canonical contract,
and ran `git diff --check de15403aa ee26389f0` successfully.

The integrator reported earlier focused selections of 50 and 25 passing tests.
Those aggregate reports are not independently counted here as frozen-source
runtime evidence. The final immutable-source execution receipt must identify
this source revision, exact commands/environment, individual results, and skips
before local package acceptance. Review PASS does not waive that gate.

## Low residual observations

An already-missing Batch workspace with retention configured currently performs
a conservative exact-root repair even without first proving a matching pending
obligation. The public enqueue path requires an existing Batch, so this is a
bounded worker-retry cost, not a new public missing-name amplification path.
A later narrow optimization may retain the no-op for ordinary absence while
keeping matching interrupted retries repairable.

Global and project leases fence cooperative application writers. They do not
claim containment of a privileged actor replacing filesystem paths, changing
configuration, or modifying Redis outside the lifecycle. Production activation
still requires the established identity, mount, permission, readiness, recovery,
and artifact canaries. Existing rollout and immediate-disable guidance remains
applicable; this review neither activates receivers nor changes production state.
