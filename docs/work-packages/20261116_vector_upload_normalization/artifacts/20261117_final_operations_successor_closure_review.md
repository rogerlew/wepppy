# Final operations successor closure review

Date: 2026-11-17
Reviewer: independent `ops_security_control_agent` (`final_ops_review`)
Source revision: `04012d9b85b14db74a4f193101a4e2cf83e5041c`
Source tree: `a4443399f4df4fb057755c0008c8dab5589a4588`
Exact local image: `wepppy/shape-converter:vector-upload-m2-final5`
Exact image ID:
`sha256:4487dec16cdb1a0ed735e60f10672c646ecc3b26d0586dbfce93479b9eae98fa`
Verdict: **HOLD M5/local receiver activation; no High and four Medium
operations findings remain. Continue local remediation only.**

## Review boundary

This review supersedes the operations closure review of revision `061253c55`.
It reviews only the exact committed revision and image above. Concurrent
working-tree remediation appeared during the review; all runtime claims were
therefore checked against committed blobs with `git show 04012d9b85:<path>`.
Uncommitted changes receive no credit. This review did not modify runtime code,
Redis, the shared checkout, registry state or any production host.

The canonical `wctl --project-dir` test wrapper correctly refused to run because
the active container was mounted to the shared checkout rather than this frozen
worktree. A host-virtualenv attempt was also unusable because it lacked the
container dependency/runtime wiring. Neither run is counted as candidate
validation. The retained candidate-container results and exact-image evidence
remain the validation authority for this review.

Production image publication, remote-host integration and deployment are
explicitly excluded actions. Missing production evidence is a later gate, not a
failed local test and not authorization granted by this review.

## Contract interpretation

The earlier operations review overstated two requirements:

- `vector-upload-normalization-contract.md:248-253` expressly permits a workflow
  without a read-only authority adapter to take the conservative recovery branch
  directly, retain all evidence and record `incomplete`. Canonical hash alone is
  not used as acceptance evidence. Process death that reaches this bounded state
  is therefore not an M5 blocker merely because it does not become
  `accepted_recovered`.
- The root-operator language at contract lines 262-265 and ADR-0145 lines 136-139
  constrains the only permissible future exception to no automatic expiry or
  partial deletion: if a root operator removes evidence, it must export and
  remove one complete terminal attempt/private bundle under the same lock with an
  audit. It does not require this work package to add a new destructive
  per-attempt CLI. The implemented owner/root private archive lifecycle and
  whole-project deletion satisfy the currently claimed M5 user/project lifecycle.
  Absence of a single-attempt operator command is **not a blocker**. If one is
  added later, the whole-bundle, same-lock, hash/readback and audit constraints
  become mandatory.

## Exact final5 and supply-chain evidence

Direct readback of the retained image archive confirmed:

- image archive SHA-256:
  `c5b9f42ccf194780ef9b1099cb81f3fd605577bbeec89b6f10569d34db7cedbb`;
- the archive manifest names config blob
  `4487dec16cdb1a0ed735e60f10672c646ecc3b26d0586dbfce93479b9eae98fa`,
  and rehashing that blob reproduces the exact image ID;
- `shape_parser_cli` SHA-256:
  `1b9b719b9b6633684addd117be01dd7754b648f0a45ab27eea644185a30b70b3`;
- `geoparquet_parser_cli` SHA-256:
  `160854839d237acb4c369bc15f97d5e51ae3841aaaca37777ba2353cfdd79c47`;
- both embedded sidecars name the real Git revision
  `e172f9f8a23c10774f87828181048c72188ba78a`; and
- all seven embedded GeoParquet source hashes match files read directly from
  that revision, including Cargo.lock SHA-256
  `ce923427941fabe153c8b282dcfddeb1168b60670055ab34f47911d039748f13`.

The final5 supply-chain artifacts parse successfully and match direct SHA-256
readback:

- SPDX 2.3 JSON, 103 packages and 2,845 files:
  `bd4b97c3ea517e214626f2371aaa0fca399e8a8f08354ed91625ea1258305fed`;
- Grype JSON:
  `5b21d0f4b905f00c10b306a2bfc8167e88e8700628c742009c6afa1501c89878`;
- Grype records: 59 High, 70 Medium, 17 Low, 50 Negligible and 16 Unknown.

The package graph and findings match final3/final4, so the retained reachability
and no-available-fix dispositions remain applicable. Final5 closes the false
source-revision finding and is accepted as the exact **local** image candidate.
A fresh publication-time scan and immutable registry digest remain mandatory.

## Prior operations finding disposition

| Prior finding | Successor disposition | Evidence and remaining control gap |
| --- | --- | --- |
| `VUN-FINAL-OPS-CR-01`, descendant root can replace global totals | **Closed** | Reconciliation now requires exact canonical equality with `VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT` before lock acquisition (`vector_upload_normalization.py:371-381`). A retained test rejects audit and apply/rebuild against a descendant without changing Redis. The rebuild snapshots and watches active reservation records and preserves their global/principal reserved charges (`:537-697`). |
| `VUN-FINAL-OPS-CR-02`, process-death publication recovery | **Closed under the ratified conservative contract** | Roads, AgFields and Batch retain in-process rollback snapshots through receipt commit. When no workflow authority adapter exists after process death, stale prepared/source evidence is classified `incomplete`, retained and charged (`vector_upload_normalization.py:500-535`), as contract lines 248-253 explicitly require. No successful job or canonical hash is substituted for acceptance. |
| `VUN-FINAL-OPS-CR-03`, final4 false source provenance | **Closed by final5** | Final5 uses a Git-resolvable revision, and the exact image's source manifest matches that revision byte-for-byte. Tar-to-config-to-image-ID, both parser hashes, SPDX and Grype evidence are retained and directly reproducible. Final4 remains disqualified. |
| `VUN-FINAL-OPS-CR-04`, deletion/rebuild retry lifecycle | **Substantially closed; successor details remain** | Project deletion, private archive deletion and private restore create deterministic mode-private filesystem and Redis obligations before destructive mutation. Admission/readiness consult Redis, readiness also consults the filesystem, exact-root rebuild preserves unrelated active reservations, and missing-target retry uses the same globally qualified identity. The four Medium findings below concern amplification, cross-authority recovery, crash durability and lease lifetime. A per-attempt deletion CLI is not required for M5. |

## Open Medium findings

### VUN-FINAL-OPS-SR-01 - Medium - missing private archives trigger global repair on the ASGI event loop

`delete_archive()` is an `async` rq-engine route, but the exact committed code
performs `shutil.rmtree()`, Redis lease operations and the bounded full-root
`reconcile_retention(..., rebuild_ledger=True)` synchronously on its event-loop
thread (`fork_archive_routes.py:1773-1803, 1812-1845`). More importantly, any
owner/root request naming a syntactically valid but nonexistent private archive
creates a new rebuild obligation and performs the same global rebuild before
returning 404. It does not first prove that the deterministic obligation already
existed from an interrupted deletion.

An authorized project owner can therefore submit distinct nonexistent private
bundle names and repeatedly force `/wc1` receipt inventory plus global Redis
transactions. Four concurrent requests can occupy all four configured rq-engine
workers, while the global reconcile lock produces additional contention and 500
responses. The retained route test proves that a retry rebuild occurs, but it
also expects a fresh rebuild on every missing-target retry; it does not distinguish
an actual interrupted operation from arbitrary absence.

Exact closure:

- for an absent private archive, compute the globally qualified deterministic
  identity and run repair only when that exact filesystem or Redis obligation is
  already pending; otherwise return 404 without creating state or scanning the
  filesystem;
- move bundle deletion and full-root reconciliation off the ASGI event loop to a
  bounded worker/thread or the established queue while preserving response and
  authorization contracts;
- retain owner/root checks, project scope and global reconcile ownership through
  the offloaded operation; and
- test many distinct missing names, one real interrupted retry and a concurrent
  cheap rq-engine request. Prove no obligation/rebuild for ordinary absence, one
  idempotent rebuild for the matching pending identity and no event-loop stall.

### VUN-FINAL-OPS-SR-02 - Medium - a filesystem obligation does not independently block runtime admission

The dual marker is intended to survive either authority's loss. Readiness checks
both `.vector-upload-rebuild-pending` and the Redis pending set
(`check_vector_upload_readiness.py:18-55`), but the runtime reservation Lua checks
only the Redis set (`vector_upload_normalization.py:128-146, 291-357`). Global
reconciliation/rebuild neither checks the filesystem obligation directory nor
reconstructs the Redis set from its validated records (`:360-720`).

After Redis loss or rollback, an initialized ledger can be rebuilt from receipts
while a pre-crash filesystem obligation still records an interrupted project
delete, private delete or restore. Activation preflight fails, but already
running web/rq-engine processes can admit new uploads because the Redis set is
empty. A new upload can then be accepted into a project whose recorded retry will
later delete or replace it. This violates the ratified requirement that **new
reservations**, not only activation, fail closed while either durable obligation
is pending.

Exact closure:

- validate the exact-root obligation directory and fail reservation before bytes
  are read when any regular marker is present; preserve the Redis Lua check for
  atomic races (begin records Redis before publishing the filesystem marker);
- during Redis-loss rebuild, validate bounded marker schema/identity and restore
  the pending Redis set, or refuse initialization until each recorded operation
  is retried;
- reject symlink/non-regular/over-bound obligation inventories; and
- test Redis pending-set loss with the filesystem marker retained, followed by
  ledger rebuild and a live reservation attempt. Admission must remain 507 until
  the exact retry rebuilds and clears both authorities.

### VUN-FINAL-OPS-SR-03 - Medium - the rebuild fence clears before destructive filesystem state is crash-durable

The obligation JSON is fsynced and `complete_retention_rebuild_obligation()`
fsyncs the marker directory before clearing Redis
(`vector_upload_normalization.py:849-865, 868-950`). The protected mutation is
not given the same durability:

- private archive delete calls `shutil.rmtree()` and immediately rebuilds without
  fsyncing the removed bundle's parent (`fork_archive_routes.py:1825-1845`);
- project delete checks only `not target.exists()` before rebuild and completion;
  it does not fsync the run parent after `runtime.rmtree()`
  (`project_rq_delete.py:135-188`); and
- private restore closes ordinary output files after `shutil.copyfileobj()` but
  does not fsync their contents or the replaced directory tree before rebuilding
  totals and clearing the obligation (`project_rq_archive.py:661-773`).

A host crash after ledger readback and marker clearance can therefore recover a
deleted directory entry, lose restored directory entries or expose truncated
restored evidence while Redis remains initialized to the pre-crash in-memory
inventory with no pending repair marker. Absence/readback before the crash is not
durability evidence.

Exact closure:

- fsync the containing directory after whole-bundle and whole-project removal,
  before ledger rebuild;
- fsync every restored regular file and then the affected directories in
  bottom-up order before rebuild/marker completion, using bounded no-follow
  traversal;
- keep both obligation authorities pending on any fsync failure; and
- inject file and directory fsync failures at each boundary. Prove no marker is
  cleared, readiness/reservation remain blocked and retry reaches exact ledger
  plus artifact readback before completion.

### VUN-FINAL-OPS-SR-04 - Medium - the destructive project fence is not renewed through long removal and rebuild

Project, private-delete and restore callers acquire the 600-second project scope
and assert it before destructive work, but a whole `rmtree()` or exact-root scan
can run longer than the lease without another assertion
(`project_rq_delete.py:121-191`; `fork_archive_routes.py:1781-1802, 1825-1845`;
`project_rq_archive.py:763-773`). `reconcile_retention()` renews its global token
and only the project scopes it acquired internally (`vector_upload_normalization.py:
387-403, 708-720`). In committed-only rebuild mode it skips noncommitted
reservations and is not given the caller's already-held scope, so it cannot renew
that caller fence.

The pending marker blocks ordinary new reservations, but it is not a destructive-
operation mutex: another delete/restore can add its own marker. If the caller
scope expires during a slow NFS removal or 10,000-receipt rebuild, a second
same-project destructive operation can acquire the scope and overlap the first.
The normal completion path can then clear one obligation against state changed by
the other operation.

Exact closure:

- pass the caller's existing scope into reconciliation so every global-lock
  checkpoint renews and verifies it, or use an equivalent owner-checked renewal
  guard for the entire removal/restore/rebuild/marker-clear interval;
- make long deletion traversal checkpoint the same fence rather than relying on
  one uninterruptible `rmtree()` call; and
- force a short lease in tests while removal and reconciliation are paused. Prove
  a competing same-scope delete/restore cannot acquire or mutate, loss of the
  original token stops before rebuild/marker clearance, and retry is idempotent.

## Accepted local controls

- Reservation admission fails closed until a verified rebuild sets
  `initialized=1`; missing Redis totals do not mean zero usage.
- Exact-root reconciliation, renewable global ownership, active project-scope
  skip, symlink refusal, watched reservation snapshots, active reservation
  preservation and post-transaction totals readback close the prior shared-ledger
  integrity findings.
- Normal-path destructive lifecycle creates deterministic mode-private filesystem
  plus Redis obligations before mutation, uses the same globally qualified retry
  identity and clears filesystem before Redis only after ledger readback.
- Production Compose now supplies the stable filesystem ID/root to web,
  rq-engine, default workers, the worker-only topology and the wepp3 archive
  worker. Blank identity and binary-disabled defaults fail closed.
- Private archives retain owner/root-only access, no Admin expansion, regular-file
  hash/receipt validation, mode-private storage and browse/Files denial.
- The rollout document has a minimum 60-minute post-canary window and measurable
  disable thresholds. Binary disable preserves direct GeoJSON; application
  rollback requires accepted-resource and downstream artifact readback.
- Final5's exact image, parser/source provenance, SBOM and vulnerability evidence
  are accepted for local review. No publication or deployment claim is made.

## Low follow-ups and later production gates

- Harden the obligation directory itself against a preexisting symlink or
  non-directory before `mkdir`/`chmod`, and bound/validate every marker entry in
  the operator recovery report.
- Add the default and fork/archive worker identities to the explicit readiness
  rehearsal instructions. They do not invoke the binary converter, but they do
  consume the stable filesystem and Redis retention authority.
- Give each rollout threshold a named query/dashboard, owner and sampling cadence,
  then retain the full production observation window under separate deployment
  authorization.
- At publication, rerun the vulnerability scan with a fresh database, publish
  final5's accepted successor by immutable registry digest and verify that digest
  plus both parser sidecars on every target.

## Control decision

Revision `04012d9b85` is not accepted for M5 completion or receiver activation
while `SR-01` through `SR-04` remain. The correct decision is **hold**, scoped to
local remediation. Keep binary admission disabled and do not publish or deploy.

There is no unresolved High finding, final5 is the accepted local exact image,
conservative `incomplete` recovery conforms to the ratified contract, and a new
per-attempt export/delete CLI is not required. After the four Medium operations
findings close on one committed revision, repeat the independent closure review.
Publication, remote integration and deployment remain separate authorization
gates with real-host identity, mount, Redis, Caddy, worker, canary, observation,
disable and recovery evidence still required.
