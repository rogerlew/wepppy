# Final code successor closure review

- Review date: 2026-11-17
- Source revision: `04012d9b85b14db74a4f193101a4e2cf83e5041c`
- Shape-converter image: `sha256:4487dec16cdb1a0ed735e60f10672c646ecc3b26d0586dbfce93479b9eae98fa`
- Scope: M3-M5 vector-upload normalization, retention recovery, destructive
  retention callers, workflow publication, tests, contracts and final5 image
  provenance
- Verdict: **hold** -- one High and seven Medium findings remain

The source review used an archive exported from the exact revision above. Later
worktree edits were excluded. This review does not require a new read-only
authority adapter: the ratified contract explicitly requires workflows without
one to retain stale `source_stored` or `prepared` attempts as `incomplete`, and
forbids inferring acceptance from the canonical hash alone
(`vector-upload-normalization-contract.md:248-253`). Revision `04012d9b85`
implements that conservative nonterminal branch.

## Findings

### VUN-CODE-SR-01 -- High -- A surviving filesystem rebuild obligation does not block admission after Redis loss

`begin_retention_rebuild_obligation()` mirrors an obligation in Redis and in
`.vector-upload-rebuild-pending` (`vector_upload_normalization.py:868-921`), but
the reservation Lua checks only the Redis set
(`vector_upload_normalization.py:128-146`, `291-327`). The exact-root rebuild
does not inventory or rehydrate the filesystem markers before initializing the
ledger (`vector_upload_normalization.py:360-407`, `537-700`). Therefore Redis
loss can erase the set while leaving the durable marker; an operator rebuild
then makes the ledger initialized and releases the reconciliation lock, after
which new uploads are admitted despite the unfinished destructive obligation.
Readiness can report the file marker, but it is not admission authority for a
service that remains running.

This violates the fail-closed reservation requirement in
`vector-upload-normalization-contract.md:295-302`. The real-Redis test covers a
marker while both copies remain present and their normal completion
(`test_vector_upload_normalization.py:389-443`), not Redis namespace loss with
only the filesystem marker surviving.

Required closure: at exact-root reconciliation, safely inventory the
mode-private marker directory, reject symlinks and malformed entries, and
rehydrate Redis or refuse ledger initialization. Reservation must also consult
the durable authority or an equivalent reconciled generation. Add a test that
loses the Redis namespace, retains a file marker, rebuilds, and proves admission
still fails.

### VUN-CODE-SR-02 -- Medium -- Partial private-archive deletion can make its durable retry unreachable

Private archive resolution verifies the ZIP, sidecar and normalization receipt
before the delete route can identify and retry the operation
(`fork_archive_routes.py:625-681`, `1773-1803`). The first delete then calls
`shutil.rmtree()` on the bundle (`fork_archive_routes.py:1825-1849`). If that
call removes `normalization.json` or the sidecar but fails while leaving the ZIP,
the rebuild obligation correctly remains pending; however, the identical retry
returns `400 Private archive provenance is invalid` before it can reacquire the
lease, finish bundle removal, rebuild the ledger or clear the obligation.

Required closure: when the exact deterministic operation/target obligation is
already pending, permit a strict owner/root retry against the same contained,
non-symlink bundle identity without requiring provenance files that the prior
attempt may have removed. Retain the full provenance requirement for a new
delete. Inject partial `rmtree` failures at each provenance component and prove
retry convergence.

### VUN-CODE-SR-03 -- Medium -- One reconciliation pass recovers only the first stale reservation for a project scope

Reconciliation retains every acquired project lease until the end of the whole
pass (`vector_upload_normalization.py:387-404`, `428-436`, `708-716`). A second
stale noncommitted reservation for the same project calls the nonblocking lease
acquirer again, encounters the reconciler's own lease, and is reported as
`active_scope_skipped` (`vector_upload_normalization.py:420-435`, `802-816`).
The behavior is safe but leaves stale charges and can require one operator run
per same-project attempt, delaying recovery from the bounded in-flight ceiling.

Required closure: retain leases in a map keyed by project scope and reuse an
already owned lease for later reservations in the same pass. Cover two stale
reservations for one project and a genuinely active independently held scope.

### VUN-CODE-SR-04 -- Medium -- Exact-image evidence stops at canonical resources, not downstream artifacts and detached reload

The final5 qualification proves the five HTTP boundaries and semantic equality
of canonical GeoJSON (`20261117_m2_final5_qualification.md:19-39`), but the tests
replace the workflow authority with `RoadsStub`, an AgFields dummy, `DummyOmni`,
and `DummyBatchRunner`/`DummyCollection`
(`test_roads_bp.py:474-495`,
`test_rq_engine_ag_fields_routes.py:359-383`,
`test_rq_engine_omni_routes.py:1292-1356`, and
`test_rq_engine_upload_batch_runner_routes.py:204-243`). They read the accepted
canonical resource; they do not detach/reload the real controller or parse the
next consumed/generated artifact.

That does not satisfy the package's artifact-readback acceptance boundary:
Roads prepared segments, AgFields rotation/field artifacts, Omni dry-run/run
report state, and Batch `dem/target_watershed.geojson` remain unproved for every
supported suffix. The retained validation summary accurately describes only
canonical geometry/property comparison
(`20261117_m3_m5_validation.md:29-39`).

Required closure: exercise real controller/NoDb detached reload after each
format and read the workflow-specific downstream artifact semantically. Retain
exact commands, fixture hashes, image ID and any skip identities.

### VUN-CODE-SR-05 -- Medium -- Private delete performs attacker-amplifiable global scans on the ASGI event loop

`delete_archive()` is asynchronous, but a syntactically valid missing private
archive creates an obligation and synchronously performs an exact-root rebuild
before returning 404 (`fork_archive_routes.py:1753-1803`). An existing private
archive synchronously executes `rmtree` and the same global walk
(`fork_archive_routes.py:1812-1849`). No threadpool or queued boundary surrounds
that work. An authorized owner can therefore submit arbitrary missing private
names to force repeated `/wc1` scans and block rq-engine health, polling and
unrelated requests on the event loop. The tests mock the rebuild and do not
measure event-loop responsiveness.

Required closure: return an ordinary 404 for absence unless the exact operation
and target already have a pending retry obligation, and move the complete
lease/obligation/delete/rebuild sequence to a worker thread or queue while
preserving the response and authorization contract. Add a concurrent health or
poll request test with the filesystem operation paused.

### VUN-CODE-SR-06 -- Medium -- Destructive mutations are not made crash-durable before their obligation is cleared

The obligation helper durably writes its marker and clears it with a directory
fsync (`vector_upload_normalization.py:849-865`, `924-945`), but its destructive
callers do not durably commit the mutation that the rebuilt ledger observed.
Private delete removes the bundle without fsyncing its parent
(`fork_archive_routes.py:1830-1847`); project deletion checks absence then
rebuilds without fsyncing the run parent (`project_rq_delete.py:135-188`); and
private restore copies regular files and changes directory modes without fsyncing
the new files and directories before rebuild/clear
(`project_rq_archive.py:676-773`).

A process or host crash after ledger readback and marker removal can therefore
recover deleted directory entries or lose/truncate restored content while Redis
records the pre-crash in-memory view and no obligation remains.

Required closure: fsync affected container directories after removals and fsync
restored regular files plus directories bottom-up before reconciliation/marker
clear. Any fsync failure must retain the obligation. Add fault-injection tests
for each destructive caller.

### VUN-CODE-SR-07 -- Medium -- Caller project leases can expire during long destructive work or exact-root rebuild

The destructive callers acquire a 600-second project lease and renew it at
selected checkpoints, but `reconcile_retention(..., committed_only=True)` does
not receive or renew that caller lease. It renews only leases that it acquired
for noncommitted reservation recovery
(`vector_upload_normalization.py:392-404`, `418-436`). Private deletion asserts
before `rmtree` and before rebuild but not during either
(`fork_archive_routes.py:1825-1849`); project deletion has no renewal inside one
long `rmtree` or rebuild (`project_rq_delete.py:135-188`); restore checkpoints
individual entries but not the subsequent global rebuild
(`project_rq_archive.py:676-773`).

If one operation exceeds the TTL, another destructive operation can acquire the
same project scope and mutate it before the first operation notices ownership
loss. The global reconciliation lock does not prevent the second caller's
pre-rebuild filesystem mutation.

Required closure: pass a renewal/assertion callback or the caller lease into the
rebuild walk and checkpoint long traversal/removal work. Add short-TTL paused
tests that prove a second destructive caller cannot overlap and that ownership
loss stops before the next mutation.

### VUN-CODE-SR-08 -- Medium -- Receipt-failure rollback can overwrite a concurrent successful NoDb mutation

New transactional rollback restores whole controller snapshots without a
generation/CAS check. Batch snapshots `_geojson_state` and
`_runid_template_state` outside `BatchRunner.locked()`, lets
`register_geojson()` acquire and release its own lock, then reacquires the lock
and blindly restores both fields if receipt commit fails
(`upload_batch_runner_routes.py:264-303`; `batch_runner.py:1120-1153`). A
concurrent successful run-template update can commit between those points and
then be erased by rollback. The test dummy's `locked()` is a no-op
(`test_rq_engine_upload_batch_runner_routes.py:88-125`), so no interleaving is
covered.

AgFields has the same stale-snapshot shape across its expensive preprocessing,
locked publish and blind locked rollback
(`ag_fields.py:254-287`, `296-354`). Omni copies the whole NoDb file before its
workflow mutation and replaces it wholesale on receipt failure
(`omni_routes.py:808-859`). The vector project lease serializes vector attempts;
unrelated controller mutations do not use that lease.

Required closure: make rollback controller-owned and conditional on the exact
generation/state written by this transaction, or hold one controller transaction
through mutation and receipt commit. Add deterministic interleaving tests in
which an unrelated mutation commits before induced receipt failure and remains
present afterwards.

## Prior VUN-CODE finding dispositions

| Prior finding | Successor disposition |
| --- | --- |
| VUN-CODE-01 active reconciliation race | The project lease is acquired before noncommitted mutation and renewed. Closed for active-scope safety; SR-03 records the remaining same-scope liveness defect. |
| VUN-CODE-02 descendant-root rebuild | Rebuild is restricted to the exact configured root. Closed. |
| VUN-CODE-03 process-death recovery | Closed under the ratified contract: nonterminal workflows without an authority adapter remain `incomplete`; hash-only acceptance is not performed. No adapter redesign is required by this review. |
| VUN-CODE-04 Roads/AgFields side effects | Roads completion logging and AgFields catalog refresh occur after receipt commit and are best-effort. Closed for the reported ordering issue. |
| VUN-CODE-05 Batch late rollback | The serial failure path restores prior file/controller state. Closed as originally reported; SR-08 is the distinct concurrent-state overwrite case. |
| VUN-CODE-06 private archive authority | Delete/restore require root or the exact project owner. Closed. |
| VUN-CODE-07 exact-image downstream acceptance | Still open as SR-04. |
| VUN-CODE-08 deletion accounting | The global ledger is rebuilt under durable obligations. Partially closed; SR-01, SR-02, SR-06 and SR-07 are unresolved integrity/recovery cases. |
| VUN-CODE-09 final4 source revision | Closed. Final5 embeds a resolvable revision and matching source manifest. |

## Exact-image provenance review

The retained `docker save` archive hashes to
`c5b9f42ccf194780ef9b1099cb81f3fd605577bbeec89b6f10569d34db7cedbb`.
Its config blob independently rehashes to the reviewed image ID. The embedded
sidecar reports parser revision
`e172f9f8a23c10774f87828181048c72188ba78a`; that object resolves as a commit,
and all seven source file hashes and sizes match `git show` at that revision.
The binary hash is
`160854839d237acb4c369bc15f97d5e51ae3841aaaca37777ba2353cfdd79c47`
and Cargo.lock hash is
`ce923427941fabe153c8b282dcfddeb1168b60670055ab34f47911d039748f13`.
The SPDX and Grype files rehash to the values recorded in
`20261117_m2_final5_qualification.md:41-55`. Final5 therefore closes the prior
image/source-provenance defect. Publication and deployment remain out of scope.

## Validation and residual risk

The principal changed Python modules compile at the exact source revision. A
direct local pytest attempt passed six tests before the real-Redis selection was
blocked by the review sandbox's prohibition on localhost sockets; a broader
selection was stopped after producing no result and is not counted as green.
The retained package evidence reports 480 passed and 5 skipped, exact-image
boundary selections of 5 plus 5, and 315 shape-converter tests. This review
audited those tests and evidence but did not independently reproduce the full
production-equivalent run.

Low residual concerns include symlink/non-directory hardening of the obligation
directory itself and the converter's absence of one absolute wall deadline.
They do not change the hold verdict above. Remote-host parity, publication,
production canaries and deployment remain external acceptance gates and were
not performed.
