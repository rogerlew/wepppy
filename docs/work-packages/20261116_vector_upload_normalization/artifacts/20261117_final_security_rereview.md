# Final security successor review: vector upload normalization

Date: 2026-11-17  
Reviewer: independent `final_security_review` security gate  
Reviewed revision: `4654150c96183eb7913f8f086526c88ad6ee3ce9`  
Verdict: **HOLD — one High and two Medium security findings remain open**

This successor review evaluates the exact committed revision above, not the
concurrent uncommitted remediation in the task worktree. It rechecks the prior
archive disclosure, symlink alias, Redis recovery, actor provenance, converter
transport/error handling, authorization/CSRF/scope, parser dispatch and hostile
quarantine findings. No runtime code, service, Redis data, image or deployment
state was modified by this review.

## Findings

| ID | Severity | Status | Finding |
| --- | --- | --- | --- |
| SEC-REREVIEW-01 | High | Open | A fixed, non-renewed project lease can expire during archive creation, reopening publication of newly created sensitive evidence in an ordinary public archive. The archive walk also follows file symlinks. |
| SEC-REREVIEW-02 | Medium | Open | Private archive authorization and integrity are incomplete: public-run nonowners can enqueue creation, the established API cannot address private archives, and restore does not verify the sensitivity sidecar/hash. |
| SEC-REREVIEW-03 | Medium | Open | Redis loss/reset and long reconciliation are not fail-closed: an empty ledger is accepted as ready, and the fixed reconciliation lock can expire before a rebuild transaction. |

### SEC-REREVIEW-01 — archive classification is not protected for the full archive operation

Severity: **High**  
Impact: confidentiality loss of retained originals, hostile bytes, source
hashes, actor IDs and failure diagnostics through an ordinary archive on a
public run.

The new archive implementation acquires the vector project lease before its
sensitivity scan, which closes the common disclosure path. The protection does
not last for the complete archive operation:

1. `_LEASE_SECONDS` is fixed at 600 seconds
   (`wepppy/microservices/vector_upload_normalization.py:43`).
   `_RedisScopeLease` can only assert or release ownership, and the factory sets
   the key once with `ex=600`; it has no owner-checked renewal method
   (`:568-634`).
2. `archive_rq()` acquires that lease, calculates the payload and decides
   `contains_sensitive` once (`wepppy/rq/project_rq_archive.py:341-380`).
3. It can then compress the entire project without another ownership check
   (`:394-427`). Large project archives can legitimately run longer than ten
   minutes.
4. Once the lease expires, a vector upload can acquire the same scope and create
   a `vector_upload_attempts` tree while the archive walk is still active. If the
   original decision was nonsensitive and the walk reaches that tree after it is
   created, the resulting archive is still published directly below `archives/`
   (`:381-383, 427`) rather than `archives/private/`. Established public-run
   download behavior then treats it as ordinary project content.

The archive inventory and ZIP write have a second alias gap. Payload sizing uses
`Path.stat()` and the ZIP loop passes file paths directly to `ZipFile.write()`
(`project_rq_archive.py:124-133, 415-422`). Both follow file symlinks. A symlink
outside a classified sensitive root can therefore repackage a sensitive target
(including a retained private archive) or another service-readable target
without the raw archive path matching the classifier. The browse and Files API
resolved-target fixes do not protect this separate archive producer.

Required closure:

- Hold an owner-bound renewable lease from before the sensitivity scan through
  archive fsync, classification-bound publication and sidecar publication.
  Check ownership before every externally visible commit; if ownership cannot be
  renewed or proven, fail without publishing an ordinary archive.
- Do not follow symlinks during payload inventory or ZIP creation. Open regular
  files with no-follow semantics and bind the archived bytes to the verified
  in-root descriptor, or reject the archive on any symlink.
- Add a deterministic slow-archive test that crosses 600 seconds (using a fake
  clock/lease), starts a concurrent upload and proves that no sensitive member
  can appear in an ordinary archive. Add file- and directory-symlink negatives
  for sensitive and out-of-root targets.
- Re-run owner/root and anonymous/authenticated-nonowner public-run ZIP member,
  mode, hash and byte readback after the race test.

### SEC-REREVIEW-02 — private archive authority and hash-bound restore are incomplete

Severity: **Medium**  
Impact: authenticated nonowners can cause expensive sensitive archive copies and
consume the shared unattributed quota; owners cannot use the established restore
API for those archives; and a private archive can be restored after tampering
without the control that was meant to bind its sensitive classification and
bytes.

Evidence:

- The archive endpoint still requires only `rq:enqueue` plus
  `authorize_run_access()` (`wepppy/microservices/rq_engine/fork_archive_routes.py:
  1421-1443`). `authorize_run_access()` deliberately admits an authenticated
  nonowner to a public run (`rq_engine/auth.py:196-221`). It does not invoke the
  owner/root mutation predicate at `auth.py:349-374`.
- Every private archive is charged to `RetentionActor("unattributed", None)`
  (`project_rq_archive.py:367-380`), so the caller's already verified human or
  service identity is neither recorded in the private archive receipt nor used
  for its principal quota. A public-run nonowner can therefore consume the
  shared 1 GiB unattributed bucket and create repeated large private copies until
  admission fails for unrelated unattributed work.
- The HTTP resolver accepts only one ZIP basename directly below `archives/`
  and rejects every nested `private/<bundle>/<archive>.zip` path
  (`fork_archive_routes.py:609-632`). The unit test bypasses this production
  resolver and invokes `restore_archive_rq()` directly with a nested path
  (`tests/rq/test_project_rq_archive.py:723-778`).
- The worker opens the resolved ZIP and calls `testzip()` but never requires,
  parses or verifies the adjacent `.sensitive.json` sidecar before destructive
  restore (`project_rq_archive.py:512-590`). Missing, malformed, mismatched or
  swapped sidecars therefore do not fail closed.
- The private archive receipt stores `canonical_path` relative to `archives/`
  rather than the run root (`project_rq_archive.py:445-461`). Reconciliation
  joins it to `root/project_root` (`vector_upload_normalization.py:437-449`), so
  exact revision `4654150c9` cannot prove the archive readback and rewrites the
  valid receipt as `incomplete`. The uncommitted worktree currently contains a
  correction, but it is outside this exact-revision verdict.

Required closure:

- Require current owner/root authority before any run archive creation that can
  contain sensitive evidence. Pass only a minimized verified retention actor to
  the worker; do not pass tokens, sessions, roles or raw claims.
- Add a containment-safe, no-symlink private archive identifier/resolver for
  owner/root restore and delete. Keep private names, stats, sidecars and bytes
  invisible to anonymous and authenticated nonowner public-run callers.
- In the worker, before opening the ZIP or deleting project state, read the
  mode-0600 sidecar with no-follow semantics and require the exact schema,
  basename, byte size, SHA-256 and `contains_vector_upload_attempts=true`.
  Missing/malformed/mismatched sidecars must stop restore.
- Store the canonical archive path relative to the run root and prove that
  reconciliation preserves the terminal archive receipt and exact committed
  charge.
- Add route-level tests for owner, root and authenticated public-run nonowner;
  sidecar absence/tampering/swap; nested-path traversal/symlinks; restored receipt
  status; and inert `.upload` handling after restore.

### SEC-REREVIEW-03 — filesystem-ledger epoch and rebuild locking are not fail-closed

Severity: **Medium**  
Impact: after Redis loss/reset, retained evidence is omitted from global and
principal accounting, allowing authorized users to bypass the 100 GiB/10 GiB
aggregate limits until the filesystem reserve is reached. A long rebuild can
also lose a concurrent reservation and corrupt accounting.

The successor correctly makes reservation hashes durable and adds bounded
receipt reconciliation. Eight abandoned pre-write reservations can now be
released, and bound attempts can be terminalized without parsing retained
payloads. Two required fail-closed properties remain absent:

1. `RedisRetentionLedger.reserve()` treats missing totals and principal hashes as
   zero; there is no durable filesystem epoch/recovery-required marker in the
   reserve Lua or Python admission path
   (`vector_upload_normalization.py:128-145, 278-353`). After a Redis reset, new
   reservations are therefore admitted while old project evidence remains on
   disk.
2. `tools/check_vector_upload_readiness.py:39-62` reads the totals hash but
   reports `status=ready` even when the result is `{}`. The documented operator
   preflight consequently does not detect the same reset/never-rebuilt state.
3. Reconciliation owns a lock with a fixed 300-second expiry
   (`vector_upload_normalization.py:375-385`). Receipt scanning and filesystem
   hashing can cover 10,000 entries and the shared run root, but the lock is never
   renewed or rechecked. If it expires, reserve Lua admits new work. The rebuild
   transaction then deletes and replaces totals/principal hashes from its earlier
   scan (`:469-547`), dropping that concurrent reservation from aggregate
   counters while leaving its reservation hash behind.

Required closure:

- Introduce an operator-initialized durable filesystem-ledger epoch/recovery
  marker that survives Redis loss. Admission and readiness must reject a missing,
  mismatched or recovery-required Redis epoch until a bounded audit/rebuild
  completes.
- Renew the filesystem-wide reconciliation lock with owner checks, or enforce a
  measured deadline below its TTL. Recheck ownership immediately before receipt
  mutation and the rebuild transaction; abort without replacing counters if it
  is lost.
- Add real Redis tests for complete Redis flush/restart with retained receipts,
  empty totals at readiness, initial clean-filesystem bootstrap, a rebuild longer
  than the lock TTL, a concurrent reservation at expiry and idempotent retry.
  Retain before/after Redis hashes plus filesystem receipt/hash readback.

## Prior findings rechecked

| Prior finding | Successor disposition |
| --- | --- |
| `SEC-FINAL-01` ordinary archive disclosure | **Partially closed.** The normal case now selects `archives/private/`, creates mode-0600 SHA-256 sidecar evidence and takes the scope lease before scanning. SEC-REREVIEW-01 and SEC-REREVIEW-02 prevent closure. |
| `SEC-FINAL-02` Files API resolved symlink alias | **Closed.** Parent listings classify every entry's real target and hide aliases; direct/meta requests classify both raw and resolved relative paths before returning metadata (`files_api.py:603-614, 1078-1083`). The focused alias regression is present at `tests/microservices/test_files_routes.py:177-199`. |
| `SEC-FINAL-03` reservation/receipt recovery absent | **Partially closed.** Reservation records no longer expire and bounded audit/apply/rebuild paths exist. SEC-REREVIEW-03 and the non-renewed scope lease in SEC-REREVIEW-01 remain. |
| `SEC-FINAL-04` signed human sessions become unattributed | **Closed for upload attempts.** The verified session principal's positive user ID is retained request-locally, and AgFields, Omni and Batch map it to the minimized human receipt actor. Session IDs are not persisted (`rq_engine/auth.py:147-157`; corresponding tests at `test_rq_engine_auth.py:390-420`, `test_rq_engine_ag_fields_routes.py:1427-1436`, `test_rq_engine_omni_routes.py:2113-2119`, and `test_rq_engine_upload_batch_runner_routes.py:652-658`). Private archive actor loss is part of SEC-REREVIEW-02. |
| `SEC-FINAL-05` unbounded converter response | **Byte-bound portion closed.** The receiver disables redirects, streams the response, checks declared and observed bytes against 34 MiB, closes the response and preserves exact source/canonical/provenance checks (`vector_upload_normalization.py:917-995`). The missing absolute wall deadline remains Low. |

## Controls reviewed without a new High/Medium finding

- Complete originals use exclusive no-follow mode-0600 writes under mode-0700
  attempt directories, receive a complete SHA-256 only after atomic publication,
  and retain a neutral `.upload` suffix. Oversize partials are removed without a
  misleading complete digest.
- Accepted binary uploads dispatch only to the configured shape-converter and
  return to canonical WGS84 GeoJSON before the receiving workflow's geometry and
  attribute validation. No Python hostile-input parser fallback was added.
- The converter URL is operator configuration rather than request data;
  redirects are disabled. No public SSRF path was found. The strict provenance,
  source digest and canonical digest comparisons remain in place.
- Stable Shapefile, GeoParquet, timeout, saturation and unavailable converter
  errors are translated into the receiving contract. Invalid successful bodies
  are translated to converter-unavailable instead of retention failure.
- Roads remains behind the existing Flask authorization decorator and global
  Flask-WTF CSRF middleware. RQ-engine uploads retain their JWT scopes, run
  authorization and feature-access checks. No Culvert upload/parser path was
  added.
- The shared classifier and resolved-target checks protect run and Batch browse,
  direct download, Files API, schema, D-Tale, GDAL and `aria2c.spec` paths.
  Originals are attachment-only `application/octet-stream` with
  `X-Content-Type-Options: nosniff`.
- Shape-converter's qualified image retains its bounded subprocess, process-group
  drain, cancellation and scratch-cleanup controls. Receiver HTTP uses connect and
  per-read timeouts. An absolute wall deadline against a compromised/dribbling
  internal peer remains a **Low** defense-in-depth follow-up.
- Unknown converter error strings are not allowlisted or explicitly length-
  bounded before receipt/event persistence. The qualified converter emits stable
  bounded codes, so this is **Low** trust-peer hardening rather than a public
  exploit; normalize unknown codes to one bounded receiver code when practical.

## Validation evidence

Review tests ran from a detached archive of exact revision `4654150c9`, avoiding
the task worktree's concurrent remediation:

```text
tests/microservices/test_sensitive_vector_artifacts.py
tests/microservices/test_vector_upload_exact_converter.py
12 passed, 5 skipped (exact-image environment was not configured)

tests/microservices/test_vector_upload_normalization.py -k 'not real_redis'
10 passed, 1 deselected

tests/rq/test_project_rq_archive.py
  - archive scope-before-scan test: passed
  - private archive/restore test: not executed to completion because sandbox
    network policy denied its localhost Redis connection
```

The broader host-side selection stalled after 12 tests and was stopped; it is not
counted as validation. The package's retained Docker/Redis results were read as
supporting evidence but do not override the exact source findings above. No
production integration, publication or deployment was attempted.

## Gate disposition

Revision `4654150c9` is **not security-acceptable for package closeout or
activation**. SEC-REREVIEW-01 through SEC-REREVIEW-03 require committed code and
regression-test closure followed by an independent security re-review of the new
exact revision. Binary image publication, remote production integration and
deployment remain separately authorized gates.
