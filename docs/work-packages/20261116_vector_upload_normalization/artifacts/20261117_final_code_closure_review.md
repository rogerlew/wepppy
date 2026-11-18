# Final code closure review: vector upload normalization

Date: 2026-11-17  
Reviewed revision: `061253c55a2a0e1cc8952143ebdf47cc40357a18`  
Comparison base: `4654150c96183eb7913f8f086526c88ad6ee3ce9`  
Exact local image: `sha256:ec801ab0c90e595dcc1a4f58b9be52398b8073a75a72591c34149b543a73ce03`  
Reviewer verdict: **HOLD — three High and six Medium findings remain.**

This review is pinned to the committed revision above. Concurrent uncommitted
work in the task worktree is not part of this verdict. No runtime code was
modified by this review.

## Findings

### VUN-CLOSURE-CODE-01 — High — reconciliation can mutate a still-active project operation

**Locations:**

- `wepppy/microservices/vector_upload_normalization.py:397-492`
- `wepppy/microservices/vector_upload_normalization.py:648-677`
- `wepppy/rq/project_rq_archive.py:394-535`

The filesystem-wide reconciliation lock blocks new reservations, but it does
not establish that an existing reservation is abandoned. At the reviewed
revision, `reconcile_retention()` treats a reservation as stale solely from its
`created_unix` age. Before rewriting its receipt, committing measured bytes, or
deleting its reservation, it never acquires or checks the reservation's recorded
project scope lease.

A live upload or private-archive operation can therefore hold and renew
`run:<runid>` while its reservation becomes older than 600 seconds. Reconciliation
can concurrently classify its `receiving`, `source_stored`, or missing receipt,
write a terminal receipt, and commit/delete the reservation. A long private
archive write is a concrete case: the reservation is bound before ZIP creation,
while `normalization.json` is published only after the archive is complete. The
reconciler can create `corrupt_attempt` against the active bundle and charge a
partial tree; the archive worker then publishes against a reservation that has
already been deleted. This can corrupt recovery evidence and undercount retained
bytes.

The global owner-token renewal added in this revision closes the prior
reconciler-vs-reconciler race, but not this reconciler-vs-active-project race.

**Required closure:** For every noncommitted apply mutation, derive the bounded
project scope from the reservation, acquire and retain that exact scope lease,
and skip active scopes without touching receipt or ledger state. Missing or
invalid project scope metadata must block mutation. Renew both the filesystem
and held project leases through the mutation. Prove with real Redis that an
active scope remains byte-for-byte and counter-for-counter unchanged, then can
be recovered only after the operation releases its lease.

### VUN-CLOSURE-CODE-02 — High — a descendant scan can replace global ledger totals with a partial inventory

**Locations:**

- `wepppy/microservices/vector_upload_normalization.py:357-376,493-587`
- `tools/reconcile_vector_upload_retention.py:13-33`

`reconcile_retention()` accepts any `filesystem_root` below the configured root
by checking only `root.relative_to(configured_root)`. Rebuild nevertheless uses
the filesystem-global ID, lock, totals key, and principal keys. The operator CLI
also accepts an arbitrary `--filesystem-root` and does not require equality with
the configured canonical root.

Running `--apply --rebuild-ledger` on one run directory therefore inventories
only that descendant, then transactionally deletes and replaces the totals and
all principal buckets for the entire configured filesystem. Evidence retained
in every sibling project disappears from accounting, allowing global and actor
quotas to be bypassed even though the files remain. This is an exact path-scope
error, not a documentation-only operator mistake.

**Required closure:** Ledger audit/rebuild must require the resolved argument to
equal the configured canonical filesystem root. Keep descendant acceptance only
for per-project reservation binding, not global reconciliation. Add negative
tests for a run root and other descendants and prove totals/principal keys remain
unchanged.

### VUN-CLOSURE-CODE-03 — High — process death can select a new workflow resource with only an `incomplete` receipt

**Locations:**

- `wepppy/microservices/vector_upload_normalization.py:457-492,1238-1312`
- `wepppy/nodb/mods/roads/roads.py:1198-1238`
- `wepppy/nodb/mods/ag_fields/ag_fields.py:316-345`
- `wepppy/microservices/rq_engine/omni_routes.py:788-859,1024-1097`
- `wepppy/microservices/rq_engine/upload_batch_runner_routes.py:264-303`

Every workflow still has a process-death window after canonical/NoDb mutation
but before the accepted receipt is durable. In-process exceptions can invoke the
new rollback code, but SIGKILL or worker loss cannot. On restart the reconciler
does not inspect authoritative Roads, AgFields, Omni, or Batch state. Any
`receiving`, `source_stored`, or `prepared` receipt is simply changed to
`incomplete`; it does not roll back the selected canonical resource or prevent
downstream code from loading it.

The result is a workflow that can actively use the replacement while its only
retention evidence says quarantined/incomplete. Conversely, an accepted-pending
receipt is recovered from canonical file hash alone, without reloading the
workflow's persisted selection/state. The contract's conservative status avoids
a false accepted label, but does not make the live resource conservative.

**Required closure:** Add workflow-specific read-only recovery authority under
the same scope lease. For every interrupted publication, compare the prepared
candidate/canonical hashes with reloaded controller/NoDb selection and the next
downstream artifact; either complete `accepted_recovered` only when all
authorities agree or restore/disable the replacement before releasing recovery.
Exercise process interruption at mutation, NoDb persistence, receipt replace,
and Redis commit for all four consumers.

### VUN-CLOSURE-CODE-04 — Medium — failed Roads/AgFields publication can leave false downstream side effects

**Locations:**

- `wepppy/nodb/mods/roads/roads.py:1198-1238`
- `wepppy/nodb/mods/ag_fields/ag_fields.py:316-345`
- `wepppy/query_engine/catalog_refresh.py:541-558`

Roads and AgFields now keep their canonical and NoDb snapshots until the receipt
commit callback, which fixes the primary file/state replacement defect. Their
fallible side effects are still emitted before that callback and are not part of
the rollback snapshot.

Roads appends `upload_completed` before receipt commit. If receipt persistence
then fails, the canonical file, retained outputs, and NoDb state are restored,
but `wepp/roads/roads.log` still records a completion for the rejected
replacement. AgFields calls `request_catalog_refresh()` before receipt commit.
In the default synchronous mode that call publishes catalog metadata for the new
Parquet; a later receipt failure restores the old GeoJSON/Parquet and NoDb state
without restoring or refreshing the catalog. In managed asynchronous mode it can
also leave a durable request for a publication that did not commit.

The new failure tests assert canonical bytes and detached NoDb reload, but do not
read back the Roads log or query catalog after the injected commit failure.

**Required closure:** Keep completion logging and catalog publication on the
committed side of the transaction, or include them in a reversible/reconciled
transaction. Inject receipt-commit failure after each side effect and prove the
log, catalog, canonical files, detached state, and downstream readers all agree
on the prior accepted resource.

### VUN-CLOSURE-CODE-05 — Medium — Batch replacement drops its rollback snapshot before receipt durability

**Locations:**

- `wepppy/microservices/rq_engine/upload_batch_runner_routes.py:264-303`
- `wepppy/microservices/vector_upload_normalization.py:1188-1236,1238-1263`
- `tests/microservices/test_rq_engine_upload_batch_runner_routes.py:364-408`

`publish_candidate()` backs up only the canonical resource, marks publication
successful immediately after `BatchRunner.register_geojson()`, and deletes the
backup in its `finally` block. Only after the callback returns does
`PreparedVectorUpload.publish()` hash the canonical file and persist the
terminal accepted receipt. If readback or receipt persistence fails in that
window, the new resource and BatchRunner state remain authoritative while the
request fails and the attempt becomes `incomplete`; the prior accepted resource
cannot be restored.

The retained Batch failure test makes `register_geojson()` fail before it
commits, so it proves the earlier mutation-failure branch but not failure after
successful registration or during accepted-receipt fsync/replace.

**Required closure:** Retain both the resource and BatchRunner state snapshot
through accepted-receipt durability, using the transactional callback pattern
or an equivalent grouped rollback. Inject post-registration readback and receipt
commit failures and prove canonical bytes, reloaded BatchRunner state, and the
next generated watershed artifact remain on the prior accepted resource.

### VUN-CLOSURE-CODE-06 — Medium — private archive control grants `Admin` beyond the owner/root contract

**Locations:**

- `wepppy/microservices/rq_engine/fork_archive_routes.py:682-697`
- `wepppy/weppcloud/routes/archive_dashboard/archive_dashboard.py:37-45,96-126`
- `wepppy/microservices/browse/sensitive_vectors.py:74-93`
- `tests/microservices/test_rq_engine_fork_archive_routes.py:1446-1488`

The canonical contract requires a verified current project owner or root for
run-sensitive evidence. Browse/download implements that rule. The archive API
and dashboard instead accept either `admin` or `root`. An Admin who is not a run
owner can therefore list private archive names/comments/sizes and enqueue
restore or deletion, while the same identity cannot download the archive through
the sensitive-artifact predicate. The route test is named owner-or-root and
covers owner, nonowner, and Root, but omits Admin, so this authority expansion is
not detected.

**Required closure:** Use the same owner/root sensitive-artifact predicate for
private archive list/create/restore/delete, or amend and independently ratify the
contract if Admin is intended to be a sensitive-evidence operator. Add a
nonowner Admin negative test across list, metadata, restore, delete, and download.

### VUN-CLOSURE-CODE-07 — Medium — exact-image coverage still stops before real reload and downstream artifacts

**Locations:**

- `tests/weppcloud/routes/test_roads_bp.py:474-497`
- `tests/microservices/test_rq_engine_ag_fields_routes.py:359-386`
- `tests/microservices/test_rq_engine_omni_routes.py:1292-1358`
- `tests/microservices/test_rq_engine_upload_batch_runner_routes.py:183-225`
- `docs/work-packages/20261116_vector_upload_normalization/artifacts/20261117_m3_m5_validation.md:27-41`

The successor materially improves exact-image evidence: all four suffixes now
cross five HTTP endpoints. However, those tests still substitute `RoadsStub`,
`DummyAgFields`, `DummyOmni`, and `DummyBatchRunner`/`DummyCollection`. Their
acceptance assertion parses the canonical GeoJSON immediately and compares one
feature. They do not reload the real controller/NoDb state or parse the next
workflow artifact required by the ExecPlan: Roads segments, AgFields rotation or
field artifacts, Omni run/dry-run report, or Batch generated watershed input.

Separate controller rollback tests cover selected direct-GeoJSON state reload,
but they do not compose exact-image conversion, every suffix, real receiving
state, and downstream artifact readback. The validation narrative accurately
describes canonical geometry/property checks; it is not evidence for the still
required downstream acceptance gate.

**Required closure:** For each supported suffix and all five receiving paths,
run the exact image through the real route/controller boundary, reload durable
state, and parse/compare the next consumed or generated artifact. Include a real
prior accepted resource and a failed replacement for each workflow.

### VUN-CLOSURE-CODE-08 — Medium — durable deletion can leave quota permanently charged

**Locations:**

- `wepppy/microservices/rq_engine/fork_archive_routes.py:1797-1816`
- `wepppy/rq/project_rq_delete.py:116-181`
- `wepppy/microservices/vector_upload_normalization.py:410-434,553-586`

Private-archive and whole-project deletion remove the filesystem tree first and
then invoke a global `committed_only` rebuild. The rebuild still refuses if any
unrelated noncommitted reservation exists anywhere on the filesystem. Thus a
normal upload in another project can make reconciliation fail after the target
archive/project is already durably gone. The route/job returns failure, but the
deleted committed charge remains in Redis.

Retry is not self-healing: private archive retry sees 404, and project deletion
skips reconciliation once the target no longer exists. Only a separately run
operator rebuild can release the leaked quota. Tests mock successful rebuild and
do not cover unrelated active reservations or idempotent post-delete retry.

**Required closure:** Make the post-delete accounting transition idempotent and
scoped, or persist a durable reconciliation obligation that a retry processes
even when the filesystem target is already absent. Prove deletion with an
unrelated active reservation, reconciliation failure after durable removal, and
eventual exact counter recovery without restoring deleted bytes.

### VUN-CLOSURE-CODE-09 — Medium — final4 provenance names a nonexistent source revision

**Locations:**

- `docs/work-packages/20261116_vector_upload_normalization/artifacts/20261117_m2_final4_qualification.md:5-12`
- `tools/check_vector_upload_readiness.py:60-72`

The exact-image qualification and readiness identity use source revision
`e172f9f8a11bd43e8471b96323add18af1559516`. That object does not exist in the
repository. The actual M2 commit sharing the prefix is
`e172f9f8a23c10774f87828181048c72188ba78a`. Because readiness compares the
configured value to the image sidecar, it can prove consistency with the same
incorrect string, but not provenance to a real committed source revision.

The parser source manifest and binary hash remain useful byte-level evidence;
they do not make the false revision field truthful. The exact image must not be
published under the current provenance claim.

**Required closure:** Rebuild the parser/image with a source revision that
resolves to the reviewed commit, regenerate the sidecar, image ID, exact-image
tests, SBOM and scan, and configure readiness from that new qualification.

## Prior-finding dispositions

| Prior finding | Disposition at `061253c55` |
| --- | --- |
| `VUN-CODE-01` — Batch resolved-path authorization / misplaced Culvert check | **Closed.** Raw and resolved Batch targets are classified in the Batch handler; Culvert no longer executes Batch-only authorization. |
| `VUN-CODE-02` — recursive hostile GeoJSON escapes cleanup | **Closed.** Strict JSON and coordinate traversal have explicit bounds, stable error translation, terminal receipt/accounting coverage, and unchanged-resource tests. |
| `VUN-CODE-03` — Roads/AgFields failed replacement rollback | **Partially closed.** Canonical and NoDb rollback now spans receipt commit, but log/catalog side effects remain inconsistent; see `VUN-CLOSURE-CODE-04`. |
| `VUN-CODE-04` — browser sessions lose human provenance | **Closed.** Signed positive human identity is retained without persisting session IDs, roles, or raw claims. |
| `VUN-CODE-05` — actual-boundary format equivalence and artifact readback absent | **Partially closed.** Exact-image HTTP coverage exists, but real reload/downstream proof remains open; see `VUN-CLOSURE-CODE-07`. |
| `VUN-REREVIEW-01` — private archive workflow/path | **Closed for path and integrity.** Dashboard/API support canonical nested identities, project-relative receipt paths begin `archives/private`, and restore verifies receipt/sidecar/hash. The separate Admin authority drift is `VUN-CLOSURE-CODE-06`. |
| `VUN-REREVIEW-02` — restore lacks vector scope lease | **Closed.** Restore acquires and renews the run scope through destructive replacement and releases it in `finally`. |
| `VUN-REREVIEW-03` — reconciliation global lease can expire and erase accounting | **Closed for global ownership.** The lease is renewed before inventory mutations and the rebuild transaction watches the owner token. The distinct active-project race is `VUN-CLOSURE-CODE-01`. |
| `VUN-REREVIEW-04` — post-publication Roads/AgFields work outside rollback | **Partially closed.** File/NoDb rollback spans the callback; non-transactional log/catalog effects remain. |
| `VUN-REREVIEW-05` — exact-image test bypasses workflows | **Partially closed.** Five HTTP boundaries are exercised, but with test doubles and no real reload/downstream artifact. |
| `VUN-REREVIEW-06` — readiness rejects healthy schema and lacks parser identity | **Closed.** The preflight accepts `status=ok`, `check=ready`, requires exact binary/Cargo.lock/source hashes, rejects redirects, and has negative tests. |

## Image and validation evidence

- The qualification and M3-M5 evidence name the requested exact image ID and
  parser identity: binary SHA-256
  `160854839d237acb4c369bc15f97d5e51ae3841aaaca37777ba2353cfdd79c47`,
  Cargo.lock SHA-256
  `ce923427941fabe153c8b282dcfddeb1168b60670055ab34f47911d039748f13`,
  and source revision `e172f9f8a11bd43e8471b96323add18af1559516`.
- Retained final4 SPDX SHA-256 is
  `08ca9f99d6adcb94e1308e10233c0de81b8c5371ff8e35c8c5327305dff86860`
  (103 packages, 2,845 package-owned files). Retained Grype SHA-256 is
  `ea3f87b8a648ca036f7ca1e3055463c692423170fe335706e384d40a1a0fd556`
  (59 High, 70 Medium, 17 Low, 50 Negligible, 16 Unknown). The qualification
  carries forward the final3 reachability/fix dispositions because package and
  OS layers are unchanged and retains publication-time rescanning as a gate.
- The scanner source binds the exported archive digest
  `sha256:f13d3f21cf3f8d41569e3a5cfbf789eaa767379a7ccd9327e2a6181349a17710`.
  The retained artifacts assert, rather than independently encode, the mapping
  from that archive to image ID `sha256:ec801ab...`; preserve an inspect/export
  manifest binding at publication qualification.
- Exact committed-source `py_compile` passed for the principal normalizer,
  archive, deletion, controller, dashboard, and readiness modules.

No additional async-event-loop regression was found: AgFields, Omni preparation,
and Batch normalization/publication use the threadpool, while Roads is a
synchronous Flask route.

## Residual external gates

The exact image is locally qualified but unpublished and undeployed. Registry
digest, remote host identity/mount/network parity, production canaries,
observation, publication-time scanning, and deployment remain separate operator
gates. Those external gates do not waive the High/Medium source and acceptance
findings above.
