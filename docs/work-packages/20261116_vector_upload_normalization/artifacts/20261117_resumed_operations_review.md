# Resumed operations review

Date: 2026-11-17
Reviewer: independent `ops_security_control_agent` (`destructive_review`)
Reviewed source: `f964831084159eb4cf68cb533dc48235cb580989`
Reviewed tree: `afc0509041e57af28d954903f92d497753b6dd7b`
Comparison source: `0e861887e132b41b00a108292d7833d21750b146`
Exact local converter image:
`sha256:4487dec16cdb1a0ed735e60f10672c646ecc3b26d0586dbfce93479b9eae98fa`

Verdict: **PASS for the reviewed local operations changes. No unresolved High
or Medium finding remains in this scope.** OPS-ARCHIVE-02 is closed in the
final successor. This is an independent source and
test-design review, not a substitute for the integrator's revision-bound runtime
receipt. M5 also requires the other review lanes and the final validation gates.
Publication, deployment, and remote-host parity are not authorized by this review.

## Copy/reset successor review

The sharing/copy authority checkpoint is `bbb216c0b`; this review does not
reopen the operator's public/team inheritance decision. The final copy/reset
source initially reviewed was `54ee356fd16845e7abf6da59d7df616f8b5fa6ce`;
its remediation successor is `224184ecd778dd58844036084f272897b79f7cd7`.
The final accepted source above also incorporates the bounded durability and
archive-visibility amendments described below.

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

### OPS-COPY-01 - Medium - closed at 224184ecd

At `54ee356fd`, `vector_retention_lifecycle._sync_evidence()` fsynced files and
directories inside each discovered retained root, then only `target.parent`.
A newly copied `target/roads/vector_upload_attempts/...` therefore did not fsync
`target/roads` or `target`, whose entries link the retained subtree. The marker
could clear after ledger readback while those entries remained unproven durable.

The same class affected deferred stale cleanup. The helper did not synchronize
`recovery_paths`, and Batch's newly renamed `.stale.*` path was absent from the
pre-operation snapshot. Partial cleanup could remove entries in that retained
tree and then defer, leaving its ledger readback without corresponding durable
directory mutations.

Closure: `_sync_evidence()` now fsyncs linking ancestors through the target in
child-before-parent order and then its parent. `TreeOperation.sync_paths`
carries retained recovery trees, and Batch/Omni register newly renamed stale
workspaces after reset. All are synchronized before reconciliation and marker
clearance. Real-copy tests trace the ancestor synchronization, and both consumer
tests prove retained stale paths enter the real synchronizer while exact ledger
totals include their remaining bytes. Synchronization exceptions propagate
before marker clearance.

### Final containment and recovery amendments

The same successor includes already-reserved bytes in copy free-space admission;
logical quota admission and physical free-space admission therefore account for
unwritten obligations. It also discovers active descendant reservations while
holding global maintenance, then fences those scopes before parent copy/reset,
run deletion, Batch deletion, or archive restoration. Discovery uses both bound
attempt paths and qualified child project identities, covering the interval
before an attempt directory exists. Its inventory remains bounded, and unsafe
reservation paths fail explicitly.

Actual `prepare_vector_upload()` regressions retain a live child upload through
attempted parent mutation and verify original bytes, prepared receipt, unchanged
counters, and absence of a new destructive marker. Separate prebind reservation
cases cover children with no filesystem directory yet. Mutation succeeds after
the child releases its authority. Required scopes remain passed into the exact
rebuild, rather than being released before accounting.

Authorized fork replacement can finish the exact interrupted `fork_copy`
destination obligation before removing its partial tree and retrying the copy.
It does not clear a different pending operation. A real rsync fault test proves
the worker-copy failure, authorized same-identity cleanup, unchanged source
bytes, and successful recopy charged to the verified copier.

### Final durability and archive-visibility re-review

The final successor synchronizes every existing ancestor through the configured
root, including newly created shard/profile parents above `target.parent`.
It resolves the parent before walking this boundary, preserving the same
behavior for relative and alias target paths. The real-copy regression uses
`root/new-shard/projects/copy`, tests absolute and relative targets, and checks
child-before-parent synchronization through both new parent directories.

Archive creation now checks each directory and file member immediately before
writing it. A child upload that appears after public classification aborts the
archive before a sensitive member enters the temporary public ZIP. The existing
failure path removes the incomplete archive and preserves the original upload.
The regression starts a real retained upload after classification, observes the
actual ZIP write calls, verifies no sensitive writes, verifies unchanged source
bytes and receipt, and then reads the original bytes from a successful private
retry. Nested private archives also participate in sensitivity classification;
the corresponding test reads their exact bytes from the private parent archive.
These changes preserve the authorized sharing contract and introduce no new
operational authority. No High or Medium finding remains in this narrow delta.

### OPS-ARCHIVE-02 - Medium - closed at 467e9db1b

The bounded private ZIP writer correctly limits writes by final offset, allowing
header rewrites while checking the central directory and close writes. It uses
the existing admitted ZIP allowance and preserves the additional receipt margin.
At `111dd982c`, its failure path reached `archive_rq()` cleanup at lines 595-602:
`os.remove(archive_path_tmp)` failures are swallowed, then the reservation is
released whenever the final archive is absent. A rejected write followed by
failed temporary-file removal therefore leaves private retained bytes on disk
with neither their reservation nor a receipt. Successful unlink also needs
durable parent synchronization before the charge can be released.

Closure: failed unlink or containing-directory fsync now logs its failure and
retains the bound reservation. Successful cleanup releases accounting only
after synchronization. A bounded incomplete receipt preserves the verified
actor, project, reservation, and pending status for existing reconciliation.
Failure to persist that receipt is logged and also leaves the reservation held.

The regression now covers successful cleanup, failed unlink, failed directory
fsync, and failed receipt persistence after failed unlink. It reads actual file
extents, original source bytes, surviving temporary bytes, receipt content,
and global/principal accounting. Unlink and fsync cases then use the existing
reconciler and prove exact retained-byte charges to the archive actor while
preserving the source actor's charge. Successful reconciliation also exercises
released project authority. The receipt-persistence failure case demonstrates
fail-closed reservation retention; it does not claim a completed repair.

### Pending source accounting copy guard

At `f96483108`, an explicit noncommitted receipt accounting status prevents
copy admission. A terminal receipt that claims committed accounting is also
checked against its matching Redis reservation; a present noncommitted state
blocks copying. The checks execute under global maintenance and the discovered
project scopes, before admission, marker creation, and the caller's mutation.
Legacy receipts without accounting fields retain their existing compatibility.

The real-Redis regression covers both pending and committed receipt labels over
an unfinished source reservation. Each rejection leaves the target absent,
the copying principal uncharged, and no new rebuild marker. Existing source
reconciliation then permits the same copy and produces exact separate charges
for the source actor and copier. The bounded delta creates no new High or Medium
operations finding.

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

For the final copy/reset successor, the reviewer resolved the full `224184ecd`
commit and tree, inspected committed helper/caller/test changes against
`54ee356fd`, re-read the canonical contract and operator guidance, and ran
`git diff --check 54ee356fd 224184ecd` successfully. Direct Docker readback still
matched the exact final5 image ID.

The integrator reports direct selections of 142 passing tests, 50 root/fork/
OpenAPI checks, and 25 exact-image cases. Those aggregate reports are not
independently counted here as final frozen-source runtime evidence. The reviewer
read the launched wrapper commands in `/tmp/vun-224-focused.log` and
`/tmp/vun-224-full.log`; they select the isolated Git checkout
`/tmp/vun-224184ecd`, its retained fixtures, and final5 HTTP converter. Both
executions were still running at this review checkpoint. The final immutable-
source receipt must retain their completed results, commands/environment,
individual cases, and skips before local package acceptance. Review PASS does
not waive that gate.

For successor `13feaac9276bd95f2341102d2683aca5a43cd3a5`, the reviewer resolved
the commit/tree, inspected the complete `224184ecd..13feaac92` runtime,
test, and contract delta, and ran `git diff --check 224184ecd 13feaac92`
successfully. The integrator reports 91 passing archive checks. The reviewer
read the launched final command and progress in `/tmp/vun-13f-focused.log`:
the command selects `/tmp/vun-13feaac92`, its retained fixtures, and final5.
That execution was still running at this review checkpoint. The full
`224184ecd` suite remains ancestor evidence; completed results bound to the
final source are still required for local package acceptance.

For successor `111dd982cadb499333bc6b5eba2c07f9d4923d7c`, the reviewer resolved
the commit/tree and inspected the complete four-file `13feaac92..111dd982c`
delta plus its existing reservation and exception-cleanup callees.
`git diff --check 13feaac92 111dd982c` passed. The integrator reports 95 archive
tests. The reviewer read `/tmp/vun-111-delta.log`, which selects the isolated
`/tmp/vun-111dd982c` checkout and final5 and completed with 142 passed. This
runtime evidence does not close the untested cleanup fault in OPS-ARCHIVE-02.

For successor `467e9db1b752ebd8448b569b58eede661f6e64a5`, the reviewer resolved
the commit/tree, inspected the complete three-file `111dd982c..467e9db1b`
delta and its reconciliation contract, and ran
`git diff --check 111dd982c 467e9db1b` successfully. The reviewer read
`/tmp/vun-cleanup-reservation-validation.log`: 98 passed. Subsequent readback of
`/tmp/vun-467-delta.log` confirms the isolated `/tmp/vun-467e9db1b` archive
selection also completed with 98 passed.
No broad test selection was repeated by this reviewer.

For final source `f964831084159eb4cf68cb533dc48235cb580989`, the reviewer resolved
the commit/tree above, inspected the full three-file `467e9db1b..f96483108`
delta and the surrounding lease/marker order, and ran the corresponding
`git diff --check` successfully. `/tmp/vun-copy-pending-green2.log` reports
19 passed. The isolated helper/copy/exact selection in `/tmp/vun-f964-delta.log`
uses `/tmp/vun-f96483108` and final5 and was still running at this checkpoint.

The ancestor broad selection in `/tmp/vun-224-full.log` stopped with 1 failed,
7966 passed, and 205 skipped. Its failure is the Roads publication gate
`test_published_results_and_sources_are_current_or_explicitly_stale`, reporting
unreviewed source drift. QA is investigating; this source review neither
attributes that failure nor waives the outstanding validation gate.

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
