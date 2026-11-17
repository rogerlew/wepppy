# Final M3-M5 correctness rereview

## Review identity and verdict

- Exact candidate revision: `4654150c96183eb7913f8f086526c88ad6ee3ce9`
- Scope: successor review of M3-M5 correctness, recovery, provenance,
  archive/restore, and artifact-readback acceptance
- Reviewer disposition: **HOLD**
- Remaining findings: **2 High, 3 Medium**

This review is based on the committed candidate, not the working tree. The
working tree also contained post-review broad-exception annotations and a fix
to the private-archive receipt's canonical path; neither is counted as part of
this candidate. Publication and deployment remain outside this review.

The successor closes candidate-provenance capture, authenticated-session actor
attribution, direct-GeoJSON reservation sizing, and the narrow accepted-receipt
monotonicity defect. It does not close the two earlier High findings: bound
attempts cannot be found reliably by filesystem-wide reconciliation, and a
failure or crash after workflow mutation can still leave the new workflow
resource/state authoritative without a recovery path that proves or rolls back
the replacement.

## Findings

### High 1: bound reservation paths are relative to the wrong root, so crash recovery can remain permanently blocked

All receiving routes pass their project directory as `filesystem_root`:
`wepppy/weppcloud/routes/nodb_api/roads_bp.py:374`,
`wepppy/microservices/rq_engine/ag_fields_routes.py:681`,
`wepppy/microservices/rq_engine/omni_routes.py:724`,
`wepppy/microservices/rq_engine/upload_batch_runner_routes.py:234`, and
`wepppy/rq/project_rq_archive.py:378`. `RedisRetentionLedger.reserve()` accepts
any descendant of the configured root and stores that project directory on the
reservation (`wepppy/microservices/vector_upload_normalization.py:289-353`).
`_RedisReservation.bind_attempt()` consequently records the attempt path
relative to the project directory at lines 210-218.

Reconciliation has different semantics: it scans the global ledger for the
configured filesystem ID and resolves every stored path relative to the one
operator-supplied filesystem-wide root at lines 356-412. The Compose default is
`/wc1`, while a Roads attempt under `/wc1/runs/<runid>` is stored as
`roads/vector_upload_attempts/<uuid>`. Reconciliation at `/wc1` therefore looks
for `/wc1/roads/...`, reports `blocked_missing_attempt`, and leaves the charge
active. Running reconciliation at one project directory is not a safe
workaround because the same command scans the global reservation namespace and
can rebuild global counters from only that subtree.

The real-Redis test at
`tests/microservices/test_vector_upload_normalization.py:261-310` creates eight
unbound reservations and exercises only `release_prewrite`; it never binds an
attempt or recovers `source_stored`, `prepared`, or accepted/pending state.

Impact: eight crashes after attempt binding but before reservation commit can
still exhaust the global in-flight ceiling indefinitely. This leaves the prior
High reservation-recovery finding open.

Required fix: store and validate attempt paths relative to the configured
canonical shared root, require filesystem-wide reconciliation to use that
exact root, and retain the project scope needed for safe locking. Add a real
Redis restart test with bound attempts in at least two project roots and all
recoverable states, including eight abandoned bound attempts followed by a
successful new admission.

### High 2: post-mutation failure and `prepared` crash recovery still do not preserve the old accepted workflow state

`PreparedVectorUpload.publish()` returns from the workflow mutation before it
performs canonical readback, receipt persistence, and ledger commit
(`wepppy/microservices/vector_upload_normalization.py:1075-1149`). Workflow
callbacks can restore their snapshots only when the callback itself raises.
They cannot roll back a canonical-readback or receipt-persistence failure after
the callback returned, and process death between mutation and terminal receipt
has the same gap. The generic handler records `incomplete` but does not invoke a
workflow rollback callback.

Recovery does not resolve the ambiguity required by the contract. It compares
the canonical hash only for `status=accepted`; every other nonterminal status,
including `prepared`, is changed directly to `incomplete` without checking the
canonical hash and authoritative NoDb state
(`wepppy/microservices/vector_upload_normalization.py:435-451`). This conflicts
with `docs/schemas/vector-upload-normalization-contract.md:234-252`, which
requires `source_stored`/`prepared` recovery to compare exact canonical hashes
and authoritative state and record `accepted_recovered` when unambiguous.

The successor improves rollback inside Roads, AgFields, Omni, and Batch
callbacks, but that does not cover this publication window. The generic test at
`tests/microservices/test_vector_upload_normalization.py:167-186` explicitly
leaves the newly copied canonical file in place and merely asserts an
`incomplete` receipt. It does not prove old accepted bytes, authoritative state,
fresh-process reload, or downstream artifacts. No retained test kills the
process after mutation for each workflow or injects failure after canonical
readback/receipt fsync.

Impact: an errored or interrupted replacement can leave new workflow bytes or
durable state authoritative while the attempt is only quarantined as
`incomplete`. This leaves the prior failed-replacement High finding open.

Required fix: either give the publication coordinator a workflow rollback
callback that remains usable through readback and receipt persistence, or
persist enough expected canonical and authoritative state to implement
workflow-specific `prepared` recovery under the existing locks. For every
workflow, inject failures/process death after file replacement, state dump,
canonical readback, receipt fsync, and Redis commit; then reload in a fresh
process and prove the old resource/state/downstream artifacts or an unambiguous
`accepted_recovered` outcome.

### Medium 1: retained exact-image evidence does not exercise actual workflow boundaries, reload, or downstream artifacts

`tests/microservices/test_vector_upload_exact_converter.py:22-45` substitutes a
fake ledger and lease. Its five workflow labels all call
`prepare_vector_upload()` directly and publish with `shutil.copy2()` at lines
85-106. It never invokes a Flask/FastAPI route, Roads, AgFields, Omni, Batch
Runner, a fresh controller/process reload, queue behavior, or a downstream
artifact. It proves useful converter/normalizer semantic equivalence across
four suffixes, but not per-workflow acceptance.

The retained summary at
`docs/work-packages/20261116_vector_upload_normalization/artifacts/20261117_m3_m5_validation.md:24-28`
describes those five parameter profiles as workflow acceptance. It does not
record the exact successor revision, executed commands, fixture hashes, or
per-artifact readback, as required by the ExecPlan at lines 283-340. Repository
inspection finds no exact-image test that parses Roads segments, AgFields
rotation/field artifacts, Omni run and dry-run reports, or Batch's generated
target watershed after a fresh reload.

Required fix: pass every supported format through every actual receiving
boundary using the exact image, recreate authoritative controllers/state, and
semantically parse the next consumed/generated artifact. Retain exact commands,
revision, image digest, fixture hashes, results, skips, and environment limits.

### Medium 2: private archive integrity and restore coordination remain incomplete

The successor correctly routes sensitive archives below `archives/private`,
writes mode-`0600` archive/sidecar files, and retains an archive SHA-256. Restore
does not consume that integrity evidence: `restore_archive_rq()` opens the
selected ZIP and runs `testzip()` at
`wepppy/rq/project_rq_archive.py:512-562`, but it never loads or verifies the
`.sensitive.json` archive size/SHA-256 marker and does not acquire the vector
project-scope retention lock before destructive restore. The retained test at
`tests/rq/test_project_rq_archive.py:735-784` restores an untampered archive; it
does not prove that a missing, altered, or mismatched sidecar fails before
project mutation.

The committed receipt also records `canonical_path=archive_name` at
`wepppy/rq/project_rq_archive.py:445-460`, omitting the `archives/` component
relative to `project_root`. Accepted reconciliation therefore resolves the
wrong canonical file. A working-tree correction exists but is not part of
`4654150c9`.

Required fix: verify the private sidecar schema, exact archive size, and SHA-256
before any restore mutation; take the same project retention lock during
restore; fix the committed canonical receipt path; and test missing/tampered/
cross-bundle sidecars, lock contention, and byte/mode-preserving restore without
automatic parsing or retry of restored evidence.

### Medium 3: `candidate_stored` is an unratified durable receipt state

The canonical contract limits `vector-normalization-v1` receipt status to
`receiving`, `source_stored`, `prepared`, `accepted`, `accepted_recovered`,
`rejected`, or `incomplete`
(`docs/schemas/vector-upload-normalization-contract.md:179-181`). The successor
durably writes `status=candidate_stored` before workflow validation at
`wepppy/microservices/vector_upload_normalization.py:1317-1330`. Reconciliation
has no explicit semantics for that state and converts it through the generic
unknown/nonterminal branch.

This does not negate the useful fix that now captures candidate hash and parser
provenance before receiving validation, but it creates state-machine drift for
recovery tooling and receipt consumers. Keep the ratified `source_stored`
status while adding candidate fields, or amend and independently review the
contract and every recovery/consumer branch before accepting the new state.

## Prior-finding closure audit

| Prior finding | Rereview result |
| --- | --- |
| High 1, crashed reservation recovery | **Open.** A reconciler exists, but bound paths are relative to project roots while recovery resolves them from the filesystem root; the real-Redis test covers only unbound pre-write release. |
| High 2, failed replacement safety | **Open.** Callback-local rollback improved, but post-callback readback/persistence failure and `prepared` crash recovery remain unresolved. |
| Medium 1, rejected candidate provenance | **Closed.** Candidate size/SHA-256 and sanitized converter/parser provenance are persisted before workflow validation at `vector_upload_normalization.py:1317-1330`. |
| Medium 2, browser-session attribution | **Closed.** The successor preserves a verified positive human user ID for signed sessions and has route-specific actor tests. |
| Medium 3, direct Omni GeoJSON reservation sizing | **Closed.** Direct GeoJSON now reserves the endpoint-sized candidate allowance; binary formats retain the bounded normalized allowance. |
| Medium 4, format/reload/downstream acceptance | **Open.** Exact-image testing stops at the shared normalizer and a copied canonical file. |
| Medium 5, private archive/restore | **Partially closed, still Medium.** Private creation and untampered restore exist; sidecar enforcement, restore locking, and the committed receipt path are incomplete. |
| Medium 6, accepted receipt downgraded after accounting failure | **Narrow defect closed.** `publish()` keeps accepted workflow/receipt state and marks accounting pending; full recovery remains blocked by High 1/High 2. |
| Low 1, Roads `.json` contract drift | **Closed.** Endpoint documentation and tests now agree with admission. |

## Validation and evidence audit

Static review covered the exact committed implementation, focused tests,
canonical contract, active ExecPlan, and retained M3-M5 validation artifact.
The canonical focused `wctl` test attempt from this worktree started no tests
because the running container was mounted from another checkout and correctly
reported `WCTL_CHECKOUT_MISMATCH`; it is not counted as candidate validation.
Retained test totals were audited as reported evidence, not rerun or promoted to
actual-boundary acceptance.

The successor must not pass M5 while either High finding remains, and the
current format-equivalence run must not be described as workflow/downstream
artifact acceptance. Image publication, remote integration, production rollout,
and deployment were not performed and remain separate operator actions.
