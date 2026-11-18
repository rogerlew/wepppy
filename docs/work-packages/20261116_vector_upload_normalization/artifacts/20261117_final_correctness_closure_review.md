# Final vector-upload correctness closure review

## Review identity and verdict

- Exact candidate revision: `061253c55a2a0e1cc8952143ebdf47cc40357a18`
- Exact local shape-converter image:
  `sha256:ec801ab0c90e595dcc1a4f58b9be52398b8073a75a72591c34149b543a73ce03`
- Scope: independent M3-M5 correctness closure review of runtime, tests,
  contract, active ExecPlan, tracker, and retained validation evidence
- Disposition: **HOLD**
- Remaining findings: **3 High and 6 Medium**

This review supersedes the correctness rereview of `4654150c9`. It is based on
the committed candidate, not the working tree. Concurrent uncommitted changes
to reconciliation scope locking and its test are not credited to this revision.
No runtime code was modified by this review. Image publication, remote-host
integration, and deployment remain outside the authorized execution boundary.

The successor materially improves the candidate: reservation attempt paths are
now relative to the configured shared root; Roads and AgFields retain rollback
snapshots through receipt completion; accepted accounting failure remains
monotonic; the ratified recovery contract permits conservative `incomplete`
classification where no authoritative adapter exists; reconciliation renews
and checks its global owner token; private archive path, integrity, authority,
restore locking, and symlink handling are implemented; and exact-image input
crosses each real Flask/FastAPI route. Those changes close many prior findings,
but they do not close the defects below.

## Findings

### High 1: Batch replacement is not transactional through receipt completion

Batch still calls ordinary `PreparedVectorUpload.publish()` after its mutation
callback returns (`wepppy/microservices/rq_engine/upload_batch_runner_routes.py:
264-303`). The callback backs up only the canonical GeoJSON and deletes that
backup in its `finally` block as soon as `register_geojson()` returns (lines
266-295). It does not retain a snapshot of durable `BatchRunner` state.

The fallible canonical readback, candidate cleanup, accepted-receipt fsync/
replace, and Redis commit occur only after that callback has discarded the
backup (`wepppy/microservices/vector_upload_normalization.py:1139-1229`). A
readback mismatch or receipt-persistence failure can therefore return an error
with the replacement GeoJSON and registered Batch state still selected. A
failure while `BatchRunner.locked()` exits can likewise leave its in-memory or
durable `_geojson_state` changed even though the file-only callback rollback
runs (`wepppy/nodb/batch_runner.py:1120-1153`).

The retained Batch failure test injects only a registration exception before
the callback marks publication successful
(`tests/microservices/test_rq_engine_upload_batch_runner_routes.py:365-408`).
It does not inject canonical readback, receipt fsync/replace, Redis commit, or
partial NoDb persistence failures and does not reload a real `BatchRunner`.

Impact: a failed replacement can violate the contract that failed attempts
never replace the prior accepted watershed, and a fresh process can observe a
resource/state split.

Required closure: use the transactional publication boundary for Batch and keep
both the prior canonical file and prior serialized `BatchRunner` state available
until accepted-receipt completion. Inject failure after registration, NoDb dump,
canonical readback, each receipt replace, and Redis commit. Reload a real
`BatchRunner` and parse the generated `dem/target_watershed.geojson` to prove the
prior accepted resource after every pre-acceptance failure; preserve the
intentional accepted/pending-accounting outcome after Redis commit failure.

### High 2: recovery can terminalize an active project operation

`reconcile_retention()` takes and renews a filesystem-wide Redis owner token,
but the committed candidate never acquires the reservation's stored `project`
scope before terminalizing a noncommitted attempt
(`wepppy/microservices/vector_upload_normalization.py:357-492`). Staleness is
computed only from immutable reservation `created_unix` (lines 402-410); active
work does not update it. The ordinary receiving and archive paths independently
hold the project-scope key created by `RedisScopeLeaseFactory` (lines 648-677),
but the reconciler does not inspect that key.

This is reachable for an authorized long-running operation. The archive worker
has a 216,000-second job timeout and renews its run scope while walking a large
tree, yet its reservation can be older than 600 seconds. An operator `--apply`
run can then see the still-being-written private bundle without its terminal
receipt, classify or rewrite it as corrupt/incomplete, commit partial measured
bytes, and delete the reservation while the archive worker still owns and uses
the run scope. The archive worker later publishes more bytes and cannot commit
the deleted reservation. The same race applies to a slow prepared receiver.

The real-Redis lock-theft test proves loss of the *global* reconciliation token
stops mutation (`tests/microservices/test_vector_upload_normalization.py:
386-457`); it does not prove active project work wins recovery. The separate
uncommitted scope-lock correction visible during this review confirms the gap
but is outside `061253c55`.

Impact: the recovery tool can corrupt receipt state and undercount or strand
accounting for an operation that is still legitimately active.

Required closure: before mutating any noncommitted reservation, acquire its
stored project scope without waiting; record an `active_scope_skipped` audit
action if it is owned, fail closed when the scope metadata is missing, and hold
and renew every acquired project scope through receipt and ledger mutation.
Retain a real-Redis test where an active reservation is older than the stale
threshold, prove zero receipt/counter mutation, then release the project scope
and prove one idempotent recovery.

### High 3: a descendant root can rebuild the global ledger from a partial tree

The predecessor's wrong bound-path defect is fixed: `_RedisReservation` now
stores attempt paths relative to the configured root
(`wepppy/microservices/vector_upload_normalization.py:290-354`). However,
`reconcile_retention()` accepts any `filesystem_root` that is a descendant of
the configured canonical root via `root.relative_to(configured_root)` rather
than requiring equality (lines 357-376). The CLI accepts this operator-provided
path directly (`tools/reconcile_vector_upload_retention.py:17-33`).

A command using `/wc1/runs` while the configured root is `/wc1` scans the global
filesystem-ID reservation namespace but rebuilds committed totals only from
receipts below `/wc1/runs`. Batch receipts and other retained evidence are then
omitted, and the global/principal counters are atomically replaced with an
undercount that readiness accepts as initialized. This is a destructive global
accounting error, not merely an audit-report discrepancy.

Required closure: require the resolved reconciliation root to equal the resolved
configured root before acquiring the global lock. Add a test that a descendant
root is rejected in both audit and apply/rebuild modes without changing any key.

### Medium 1: restore and deletion do not maintain exact, retry-safe accounting

Private archive deletion removes the bundle while holding the run scope, releases
that scope, and only then attempts a global committed-only rebuild
(`wepppy/microservices/rq_engine/fork_archive_routes.py:1798-1813`). Any active
reservation anywhere on the shared filesystem blocks the rebuild after the
archive is already gone. The request returns an error with committed counters
still charged; retry returns `404` and does not repair them.

Whole-project deletion has the same non-atomic ordering: it removes the run and
then performs a global rebuild (`wepppy/rq/project_rq_delete.py:116-181`). If the
rebuild fails after durable removal, a later retry sees no target, skips
reconciliation, and can delete the database record while counters remain stale.
Its test mocks both the lease and reconciler and proves only call order
(`tests/rq/test_project_rq_delete_run.py:153-193`).

Restore holds the run scope and verifies private archive provenance before
destructive replacement, which closes the prior confidentiality/integrity race,
but it does not reconcile accounting after replacing the live attempt tree
(`wepppy/rq/project_rq_archive.py:580-760`). Attempts created after the archive
remain charged even when restore removes them; restored receipt bytes can also
differ from the pre-restore inventory. The private restore test verifies bytes
and modes, not before/after global and principal totals
(`tests/rq/test_project_rq_archive.py:809-876`).

These paths do not implement the contract's same-scope, whole-bundle, explicitly
audited and retry-safe removal lifecycle. The resulting drift is conservative in
the common case, but can permanently deny future admission.

Required closure: bind durable removal/restore intent to the exact affected
reservation IDs and principal buckets, preserve an idempotent recovery record,
and atomically update the ledger only after durable whole-bundle/project removal.
For restore, rebuild or apply exact deltas while still holding the run scope.
Test unrelated active reservations, failure before/after removal, retry after a
missing target, and exact global/principal readback after private delete, restore,
and project deletion.

### Medium 2: production worker services do not receive the retention identity

The production `weppcloud` and `rq-engine` services explicitly receive the
`VECTOR_UPLOAD_*` settings (`docker/docker-compose.prod.yml:141-147,
587-593`), but the shared `x-wepppy-env` anchor does not contain them (lines
17-50). Consequently the default RQ worker and the fork/archive worker inherit
no filesystem ID/root (`docker/docker-compose.prod.yml:638-685,738-764`). The
dedicated wepp3 fork/archive service also omits them
(`docker/docker-compose.prod.wepp3.yml:35-55`). The checked-in default env file
does not supply these variables.

This has two concrete effects under the canonical topology:

- a sensitive archive reaches `RedisRetentionLedger.reserve()` without a
  configured identity and fails closed, so evidence-bearing projects cannot use
  the archive workflow; and
- `delete_run_rq()` conditionally skips the scope/reconciliation lifecycle when
  the filesystem ID is absent (`wepppy/rq/project_rq_delete.py:116-125`), leaving
  deleted evidence charged.

The rollout instructions run readiness only under web/rq-engine identities
(`20261117_m3_m5_validation.md:63-70`), so they cannot detect the worker split.
Fail-closed archive creation prevents a confidentiality leak, but the production
workflow and deletion accounting are not usable as documented.

Required closure: put the stable ID/root in the shared application/worker
environment or explicitly add them to every consuming service, including the
wepp3 override. Extend preflight/resolved-Compose evidence to the default and
fork/archive worker identities and exercise sensitive archive plus project
deletion under those exact identities and mounts.

### Medium 3: exact-image route coverage stops before reload and downstream acceptance

The final4 tests now cross the actual Roads, AgFields, Omni run/dry-run, and
Batch HTTP routes for GeoJSON, Shapefile ZIP, `.parquet`, and `.geoparquet`.
That is a real improvement over the predecessor helper-only test. However, the
workflow authorities remain replaced in the acceptance selection:

- Roads uses `RoadsStub`
  (`tests/weppcloud/routes/test_roads_bp.py:25-254,474-496`);
- AgFields uses `DummyAgFields`
  (`tests/microservices/test_rq_engine_ag_fields_routes.py:20-78,359-383`);
- Omni uses `DummyOmni`
  (`tests/microservices/test_rq_engine_omni_routes.py:1296-1358`); and
- Batch uses `DummyBatchRunner` and `DummyCollection`
  (`tests/microservices/test_rq_engine_upload_batch_runner_routes.py:59-103,
  183-228`).

Those tests parse only the accepted canonical GeoJSON. They do not recreate a
real controller in a fresh process or parse the ExecPlan's next generated or
consumed artifact: Roads monotonic segments, AgFields rotation/field artifacts,
Omni run and dry-run build reports, or Batch target watershed.

The retained validation summary reports `480 passed, 5 skipped`, but does not
name `061253c55`, list the exact commands/test selection, record fixture hashes,
or retain per-downstream-artifact readback
(`20261117_m3_m5_validation.md:3-45`). The result is useful regression evidence,
but does not satisfy the ExecPlan rule that mocks, successful requests, and file
existence cannot establish artifact acceptance.

Verified-session provenance is also proved only at helper level: the AgFields,
Omni, and Batch tests construct or monkeypatch sanitized actor dictionaries
rather than send a signed session through authentication and inspect the
terminal receipt and real Redis principal bucket. The runtime mapping appears
correct, but the earlier required end-to-end provenance evidence is not present.

Required closure: retain one exact-candidate, exact-image run that submits all
four inputs to every route, reloads each real authority from durable state, and
semantically parses the named downstream artifact. Record exact commands,
revision, fixture hashes, results, skips, and environment limits.

### Medium 4: transactional rollback leaves false derived side effects

AgFields keeps its GeoJSON, Parquet, and NoDb snapshot through the transactional
receipt callback, which closes the predecessor's principal replacement defect.
But it calls `request_catalog_refresh()` after replacing the two files and before
the receipt commit callback
(`wepppy/nodb/mods/ag_fields/ag_fields.py:316-345`). With catalog refresh disabled
or for a standalone scope, `request_catalog_refresh()` synchronously calls
`update_catalog_entry()` on the new Parquet
(`wepppy/query_engine/catalog_refresh.py:541-552`).

If accepted-receipt persistence then fails, AgFields restores the old GeoJSON,
Parquet, and NoDb fields, but does not restore or re-refresh the query catalog.
The rollback test verifies files and a detached controller only
(`tests/nodb/mods/test_ag_fields_backend_contract.py:187-229`); it does not read
the catalog. The catalog can therefore describe the rejected replacement while
the authoritative files/state describe the prior upload, violating the required
downstream postcondition.

Roads has the parallel observability defect. It appends an
`upload_completed` record before invoking the publication commit callback
(`wepppy/nodb/mods/roads/roads.py:1209-1228`). A callback failure restores the
canonical file, retained Roads artifacts, and NoDb state, but the completion log
for the rejected replacement remains. Its rollback test likewise checks only
canonical bytes and detached controller state
(`tests/nodb/mods/test_roads_controller.py:162-186`).

Required closure: include catalog/log publication in the rollback boundary, or
publish those derived effects only after accepted receipt durability under an
explicit recoverable post-acceptance contract. Inject receipt failure after
synchronous catalog/log update and prove catalog plus Roads log readback match
the restored files and detached controller states.

### Medium 5: `Admin` is granted private-run evidence authority beyond the contract

The retained-evidence predicate correctly limits run evidence to the current
owner or Root (`wepppy/microservices/browse/sensitive_vectors.py:74-93`), and
the ratified contract explicitly requires owner or root/operator authority.
Private archive route and dashboard helpers instead grant both `Admin` and
`Root` without verifying ownership
(`wepppy/microservices/rq_engine/fork_archive_routes.py:682-697`;
`wepppy/weppcloud/routes/archive_dashboard/archive_dashboard.py:37-44`). An
unrelated Admin can therefore list metadata and request restore or deletion of
a private evidence archive even though the common sensitive download path would
deny its bytes.

This is authorization drift from the approved owner/root boundary and creates
inconsistent authority across list, download, restore, and delete.

Required closure: remove the generic Admin bypass or ratify a broader authority
in the canonical contract through the required security/governance review. Add
actual owner, unrelated Admin, Root, ordinary authenticated nonowner, and
anonymous tests across list, download, restore, and delete; denial must occur
before archive metadata or mutation.

### Medium 6: final4 readiness authenticates a nonexistent source revision

The final4 qualification records parser source revision
`e172f9f8a11bd43e8471b96323add18af1559516`
(`20261117_m2_final4_qualification.md:8`). That 40-hex object does not exist in
the repository: `git cat-file -e <revision>^{commit}` fails. The reviewed parser
commit is `e172f9f8a23c10774f87828181048c72188ba78a`, which is also the revision
recorded by the prior M2 validation artifact.

The release build gate validates only the 40-lowercase-hex shape of the supplied
string (`docker/Dockerfile.shape-converter:26-30`), and receiver readiness then
compares the configured expectation to the same image-provided string
(`tools/check_vector_upload_readiness.py:61-72`). Matching two copies of a typo
does not bind the image to source. The final4 binary, lock, SBOM, and scan hashes
remain useful retained evidence, but the asserted source provenance is false.

Required closure: rebuild the exact image from a clean named commit using the
real resolvable revision; verify the provenance manifest against files extracted
from that commit; rerun exact-image and five-boundary tests; and regenerate the
SBOM/scan. Strengthen release qualification so a syntactically valid but
unresolvable revision cannot be accepted as source identity.

## Prior-finding closure audit

| Prior finding | Result at `061253c55` |
| --- | --- |
| Wrong-root bound reservation recovery | **Core bound-path defect closed.** Bound paths are relative to the configured shared root and real Redis covers a bound prepared recovery. Partial-root global rebuild remains High 3. |
| Post-mutation failed replacement | **Partially closed.** Roads and AgFields use transactional receipt callbacks with detached reload tests; Omni retains its outer file/NoDb rollback. Batch remains High 1, and Roads/AgFields derived side effects remain Medium 4. |
| `prepared` crash recovery requires authoritative promotion | **Closed by ratified decision.** The amended contract explicitly requires a workflow without an authoritative recovery adapter to retain conservative `incomplete`; canonical hash alone is not promoted. |
| Candidate provenance and unratified `candidate_stored` | **Closed.** Candidate fields are persisted while using the ratified `source_stored`/`prepared` states. |
| Signed-session human provenance | **Runtime defect closed.** Verified positive account IDs are retained without session IDs. Actual signed-session receipt/ledger evidence remains part of Medium 3. |
| Direct-GeoJSON reservation sizing | **Closed.** Direct candidates reserve the endpoint allowance; binary candidates retain the bounded normalized allowance. |
| Accepted receipt downgraded after Redis failure | **Closed.** Accepted publication remains accepted with pending accounting and is recoverable. |
| Reconciliation global lock expiry/theft | **Closed.** The owner token is renewed and checked before mutations, and final rebuild is token-conditioned. Active project-scope ownership remains High 2. |
| Redis-loss readiness and exact parser identity | **Mechanism closed; candidate evidence invalid.** Admission requires initialized totals and readiness compares binary, Cargo lock, and source identity strings, but final4's source string is nonexistent (Medium 6). |
| Private archive public exposure, symlink walk, sidecar/hash, restore lock, and canonical path | **Substantially closed.** Accounting lifecycle remains Medium 1, worker configuration remains Medium 2, and the extra Admin authority remains Medium 5. |
| All-format actual-boundary evidence | **Partially closed.** All formats cross all five real HTTP endpoints with final4, but real reload, signed-session receipt proof, and downstream artifacts remain Medium 3. |
| Deep JSON nesting and converter response/error bounds | **Closed.** Receiving applies a depth cap, streams a bounded converter response, and retains stable translations. |

## Evidence assessment

The retained final4 SBOM and Grype files hash to the values recorded in the
qualification artifact:

- SPDX: `08ca9f99d6adcb94e1308e10233c0de81b8c5371ff8e35c8c5327305dff86860`;
- Grype: `ea3f87b8a648ca036f7ca1e3055463c692423170fe335706e384d40a1a0fd556`.

Those hashes do not cure final4's nonexistent source-revision claim in Medium 6.
This review audited the reported 480-pass application result and exact-image
route evidence but did not independently rerun or promote them because the
retained record lacks the exact command and revision binding required for final
acceptance. The working tree changed concurrently during review, so counting a
new run from it as `061253c55` would be incorrect.

## Disposition

Revision `061253c55` must not complete M5 or be activated. Fix the three High and
six Medium findings on one committed successor, rerun the exact candidate/
image evidence with real reload and downstream readback, and repeat the required
independent closure reviews. Final4 may remain a retained local image artifact,
but it is not provenance-qualified for publication or activation. Registry
publication, remote production parity, deployment, and rollout remain separate,
genuinely unperformed gates.
