# Resumed independent security review

Date: 2026-11-17
Reviewer: independent `security_reviewer` (`frozen_security`)
Reviewed source: `ee26389f099e9e950b5920d53790f8661548a5e3`
Initial reviewed ancestor: `de15403aadbd7a659ef4717e77223ff4890b18c1`
Comparison source: `0e861887e132b41b00a108292d7833d21750b146`
Exact local converter image:
`sha256:4487dec16cdb1a0ed735e60f10672c646ecc3b26d0586dbfce93479b9eae98fa`

## Findings and disposition

**HOLD package closeout: one High and one Medium security finding remain.**
The earlier narrow deletion/auth source PASS is superseded by the independently
confirmed clone consumers below. The reviewer did not author or modify runtime
code or tests. Frozen validation of deletion and upload paths cannot close these
uncovered paths. Production publication/deployment remain separately authorized.

### SEC-RESUME-01 - Public-run fork exposes source-private vector evidence

Severity: **High**. Status: **Open**.

`fork_project()` accepts authenticated public-run nonowners through ordinary
`authorize_run_access()` (`fork_archive_routes.py:952-965`), then registers the
caller as a destination owner (`:1528-1543`). `_build_fork_rsync_cmd()` includes
neither `vector_upload_attempts` nor `archives/private` in its default exclusions
(`project_rq_fork.py:580-603`); the real worker runs that command (`:1414-1433`).
The copied files are subsequently readable under the destination owner's normal
sensitive-artifact predicate (`browse/sensitive_vectors.py:74-93`). A caller
without source-evidence authority therefore obtains originals, rejected/hostile
uploads, source hashes and actor metadata by forking the public run.

The reviewer executed the exact committed command builder, extracted from the
`ee26389f0` Git blob, against a disposable sentinel project using real `rsync`.
The command exited zero and copied all three controls byte-for-byte:

- `roads/vector_upload_attempts/attempt/original/source.zip.upload`;
- `roads/vector_upload_attempts/attempt/normalization.json`; and
- `archives/private/bundle/private.zip`.

Only reviewer-created sentinel files were used; no user project or service state
was changed. The authorization-to-destination-owner exploit chain was traced in
source; a full HTTP fork/browser reproduction remains required for closure.

Required remediation: ratify the clone disposition without weakening existing
public-run fork behavior or silently dropping required provenance. Either keep
originals only in their source project with a non-disclosing reference, or copy
only under explicit source-private authority with bounded reservation, destination
receipt identity and private modes. Apply the decision at the actual copy boundary
and prove public nonowner, owner/root, anonymous where applicable, failure/retry,
and sensitive browse/download behavior. Until then source-private bytes must not
be copied into a destination controlled by a newly authorized principal.

### SEC-RESUME-02 - Clone and leaf reset bypass retained-evidence accounting

Severity: **Medium**. Status: **Open**.

The same broad copy assumption occurs in
`BatchRunner._run_batch_hillslopes_owned()` (`batch_runner.py:580-593`):
`copytree(base_wd, runid_wd)` duplicates attempts/private archives without a
retention reservation or destination provenance, while `_reset_run_workspace()`
renames/deletes an existing leaf without a rebuild obligation. Fork `rsync` has
the uncharged-copy behavior too. The operator/developer `test_run_rq()` consumer
(`project_rq.py:912,951,962`) likewise clones to `-latest` and recursively removes
its old destination without retention repair. It is not evidence of an additional
public endpoint, but is a confirmed consumer of the same broken assumption.

Repeated clones can multiply retained bytes outside global/principal admission;
leaf reruns can remove charged evidence while leaving stale totals. Copied
receipts also preserve source project/reservation identities, so they cannot be
claimed as destination acceptance/provenance records.

Required remediation: apply the ratified clone decision consistently to fork,
Batch generation/reset, and `test_run_rq()`. For copies, reserve and charge actual
destination retained bytes or keep source-only originals with an authorized
reference. For removal, use the existing exact-root durable accounting lifecycle
or a documented bounded prohibition before mutation. Retain real-copy and
reset/retry tests with exact global/principal totals, source/destination receipt
readback, and unrelated active reservation preservation. Record any other
confirmed clone consumer in the failure-class coverage inventory.


The new changes restore the existing retained-evidence contract: complete inputs
remain private and inert, while deletion and restoration retain recovery authority
until exact-root accounting is rebuilt. They do not add parser authority,
network destinations, privileges, authentication mechanisms or a new datastore.

## Security surfaces rechecked

| Surface | Evidence and disposition |
| --- | --- |
| Run and whole-Batch deletion | `_retention_delete_root()` rejects missing identity/root for retained evidence, outside-root/root targets, and direct target symlinks before project state mutation. Batch validates its name and retains the active-job check inside the catalog guard. Its new guard acquires global maintenance before Batch and generated child-run scopes, records the durable operation identity, removes/fsyncs, rebuilds accounting, and checks owned leases before marker clearance. |
| Failure and retry authority | The marker helper validates the configured root and existing marker directory, rejects ordinary and dangling symlink aliases, and keeps Redis authority when an atomic file write may have replaced the file before fsync failure. Admission mirrors surviving filesystem markers and refuses a pending or uninitialized ledger. Completion removes/fsyncs the filesystem marker before removing Redis authority. |
| Nested destructive operations | The `ee26389f0` successor takes the union of filesystem and Redis pending identities. It rejects a different operation before creating its marker or permitting destructive work. An identical operation/target can resume from either authority. This prevents parent deletion from removing a workspace needed to finish an earlier archive/child repair. |
| Private archive deletion and restore | Pending deletion retries revalidate lexical containment and symlink ancestry, including when missing provenance is allowed for the exact interrupted operation. Absent retries fsync the bundle parent. Restore validates retention identity and incoming/live sensitivity before catalog/RedisPrep mutation, rejects archive aliases, preserves private directory modes, and leaves obligations pending on partial removal, fsync or lease failure. |
| Authentication and provenance | Existing owner/root private-archive authorization, JWT scope/run binding and signed Flask session handling remain intact. The new five-boundary provenance tests exercise actual token decoding and actor extraction, real retention leases/Lua accounting, terminal receipts, source bytes/SHA-256 and principal totals. Account-store/controller/queue seams are explicit and do not claim full remote identity parity. |
| Logs and private artifacts | Receipts retain only the minimized verified actor identity and required sanitized submitted filename. Security events omit filenames, sessions, cookies, raw claims, roles, email and client IP. The prior QA wording that excluded filenames from every durable surface is correctly limited by the canonical private-receipt contract. |
| Parser and supply chain | No shape-converter parser/image source changed in the reviewed successor. The exact running final5 image ID was independently read back. Its retained qualification, parser binary/lock/source identities and scan dispositions remain the image evidence; final4 remains disqualified. No dependency, public endpoint or Python hostile-parser fallback was introduced. |

## Prior security finding closure

The prior dedicated security artifact at `4654150c9` held three findings. Their
remediated forms were traced in the frozen successor rather than assumed closed
from later summary text.

- **SEC-REREVIEW-01, archive disclosure/lease lifetime: closed.** The shared
  lease renews with owner checks and surfaces renewal failure to its owner.
  Archive creation takes the run scope before classification, checks it during
  traversal and before publication, rejects file/directory symlinks, and places
  sensitive archives below the private root. Existing lease-loss and alias
  regressions remain present in `test_project_rq_archive.py`.
- **SEC-REREVIEW-02, private archive authority/integrity: closed.** Archive
  creation invokes the current owner/root predicate and sends a minimized actor;
  private restore/delete resolution remains owner/root-only. Worker restore
  verifies private sidecar/hash/receipt authority before destructive mutation.
  The archive receipt canonical path is rooted at the project, and restored
  originals retain their inert suffix and private modes.
- **SEC-REREVIEW-03, Redis loss and rebuild ownership: closed.** Reservation Lua
  rejects an uninitialized ledger and pending rebuilds. Admission/readiness also
  reject durable filesystem obligations. Reconciliation renews/checks global and
  required scopes, preserves unrelated active reservation charges, watches its
  authority/reservation state for the replacement transaction, and reads back
  exact totals. Missing or ambiguous authority fails closed.

The new whole-Batch lifecycle closes the omitted consumer identified by frozen
QA. Its tests verify both `_base` and generated-child scope contention, deleted
and unrelated principal totals, and preservation of unrelated active charges.
The added nested-repair regression covers both marker authorities separately.

## Evidence inspected

The reviewer directly inspected committed source and the complete successor
production diff, both canonical contract amendments, prior security dispositions,
and the new tests:

- `tests/rq/test_vector_retention_deletion.py`;
- `tests/rq/test_vector_archive_recovery.py`;
- `tests/microservices/test_vector_upload_session_provenance.py`;
- existing normalizer, private archive/auth, and readiness regressions.

`git diff --check 0e861887e..ee26389f0` passed. Direct Docker image readback returned
the exact final5 ID recorded above. No runtime tests were initiated by this
reviewer; the integrator is executing the combined immutable-source suite and
retaining its commands, environment, hashes, node results and skips. Earlier
working-copy totals are not promoted here to frozen-source evidence.

## Residual limitations

The two clone findings above are acceptance blockers, not residual Low debt.
The operator clone disposition is pending; this review does not authorize a
behavior or provenance exception.

Previously recorded Low internal-peer hardening remains nonblocking: receiver
HTTP uses connect/per-read limits rather than an independent absolute wall
clock deadline, and trusted-converter unknown error-code bounds merit a later
small cleanup. The qualified converter and byte-bounded response path constrain
both; no public request-controlled URL or parser bypass was found.

Filesystem race protection assumes the established service identity and private
artifact roots. This review does not claim containment of a hostile process
already able to mutate those roots as the service user. Final production parity
must exercise the real mounted roots, groups, umask, auth storage and orchestration.
The retained image scan still requires its documented fresh publication-time scan;
this source review does not waive it.
