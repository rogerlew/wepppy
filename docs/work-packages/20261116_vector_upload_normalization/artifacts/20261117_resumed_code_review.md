# Resumed final code review

Current bounded code-review verdict: **PASS** at
`f964831084159eb4cf68cb533dc48235cb580989`; see the final independent successor
review below. Earlier dated dispositions are retained as historical evidence.

- Reviewer: independent `reviewer` agent, `code_review`.
- Date: 2026-11-17 UTC.
- Reviewed source: `ee26389f099e9e950b5920d53790f8661548a5e3`.
- Comparison: `0e861887e132b41b00a108292d7833d21750b146`.
- Converter remains final5,
  `sha256:4487dec16cdb1a0ed735e60f10672c646ecc3b26d0586dbfce93479b9eae98fa`.
- Initial successor verdict: **PASS for the reviewed recovery diff**. The later
  copy/reset failure-class inventory below reopens package-level code acceptance.

## Scope and method

Read the committed production successor, applicable contracts, prior frozen QA
findings and new regression tests. The review covered retention obligations,
whole-Batch and run deletion, private archive deletion/restoration, scope ownership,
recovery ordering and error propagation. No implementation or test code was
authored by this reviewer. This artifact does not substitute for the separately
recorded full validation, QA, security or operations gates.

The successor preserves the ratified conservative recovery rule: file existence
or a matching canonical hash alone cannot promote uncertain publication to
accepted. No new recovery adapter, parser, dependency or deployment mechanism is
required by this review.

## Finding closed during review

**VUN-CODE-RESUME-01, Medium: a new parent deletion could destroy an earlier
destructive operation's retry target.** At predecessor
`de15403aadbd7a659ef4717e77223ff4890b18c1`, the common obligation helper admitted
a new project deletion while a private-archive deletion marker remained pending.
Deleting the parent then left the archive marker outside the removed workspace;
the archive route returned project-not-found before its repair function. The
surviving marker continued to block uploads, with no reachable identical retry.
Whole-Batch deletion could cause the same failure for a child operation.

A minimal reproduction using the actual predecessor helper and an in-memory
Redis-set substitute produced:

    new_parent_operation_was_admitted: true
    orphan_marker_survives: true
    project_exists_for_archive_retry: false
    pending_count: 1

Commit `ee26389f099e9e950b5920d53790f8661548a5e3` closes this defect in
`begin_retention_rebuild_obligation()`: the union of filesystem and Redis pending
identities must contain no identity other than the exact requested operation and
target. Rejection occurs before recording another obligation or destructive
mutation. Identical retries recover either missing mirror. The canonical contract
records the ordering rationale under the destructive retention lifecycle.

Independently executed the frozen helper exported with `git show` into the
existing development container, using `wctl exec`, temporary directories and
the same in-memory set substitute. All three authority states passed:

    both: parent rejected; exact repair restored both markers
    filesystem: parent rejected; exact repair restored both markers
    redis: parent rejected; exact repair restored both markers

This is direct helper evidence, not a claim of real-Redis workflow coverage.
The committed `test_parent_delete_waits_for_pending_archive_repair` additionally
contains the six run/Batch by authority cases for the integrator's actual Redis
validation run.

## Other reviewed closures

- Run deletion validates identity and containment before TTL or catalog mutation.
- Batch deletion fences its upload scope and generated child-run scopes, uses
  deterministic obligations, durably removes the workspace and reconstructs
  accounting even on absent-target retry. Its active-job check remains inside
  the catalog lifecycle guard and before retention mutation.
- Private archive retry revalidates containment despite incomplete provenance,
  fsyncs an absent bundle's parent, and rechecks both lease owners before clearing
  obligations. Restore rejects missing identity before project metadata mutation.
- Common obligation handling rejects symlink directories, retains Redis authority
  when file persistence fails, and validates marker-root identity before cleanup.
- The Batch concurrency regression now propagates worker failures, coordinates
  explicit blocked/retry/completed events and verifies the later mutation after
  detached reload; the earlier false-green thread crash path is removed.

## Residual limits

Batch deletion starts one renewal thread per generated child scope. The focused
tests establish fencing and cleanup but do not qualify resource use for unusually
large Batch workspaces. This is a low-priority measurement follow-up, not a
reproduced acceptance failure. Final5 parser/image qualification is retained from
the earlier exact-image evidence; this review did not rebuild or rescan the image.

Remote integration, image publication and production deployment remain separate
operator-authorized actions.

## Copy/reset failure-class addendum

Package-level code acceptance is **HOLD** while the operator's clone retention
disposition and the confirmed copy/reset consumers are resolved. See
`20261117_vector_retention_copy_reset_inventory.md` for the bounded source
inventory, verified-negative paths, control seams and required evidence. The
earlier recovery-diff PASS does not imply those inherited consumers were safe.

The independently reproduced Omni cleanup defect is closed at
`860ba6760074d7db018c1b1b5a7d6f633d580b3d`: both generated-contrast cleaners now
preserve `vector_upload_attempts`, and the new tests cover clean/stale/reset/clear
entrypoints. This fixes immediate deletion of retained originals without waiting
for a clone-policy decision. Fork copying, Batch copy/reset and profile snapshot
consumers remain subject to the inventory's explicit closure gate.

## Independent sharing/copy/reset successor review

Reviewer: `archive_review`, acting as the independent bounded correctness
reviewer. Final reviewed source:
`f964831084159eb4cf68cb533dc48235cb580989`; bounded successor comparison:
`54ee356fd16845e7abf6da59d7df616f8b5fa6ce`. Sharing contract checkpoint:
`bbb216c0bc48674f8b24f5e69f20ec58e57b795a`.

**PASS for this source review. No unresolved High or Medium finding remains in
the reviewed scope.** This supersedes the prior source-54 recovery HOLD and the
earlier copy-policy HOLD. It does not claim completion of the integrator's
full-suite validation or authorize publication/deployment.

### VUN-CODE-RESUME-02 - Medium - fork retry identity mismatch: closed

At source `54ee356fd`, an interrupted worker `fork_copy` left an obligation that
the authorized API's `fork_target_replace` could not consume. An independent
real-Redis reproduction returned 507 while retaining both target and marker.
The common pending-operation barrier was correct; the caller's recovery identity
was incompatible with the ordinary retry workflow.

At `224184ecd`, `_delete_fork_replacement_tree()` recognizes only an exact
`fork_copy` obligation for the same destination and completes deletion/rebuild
under that identity. Other operation/target obligations still block. The actual
rsync regression injects a worker interruption, calls the authorized replacement
helper, verifies source preservation and repaired accounting, then recopies and
checks the recipient's charge.

The independent reproduction repeated against
`weppcloud:/tmp/vun-224184ecd` passed:

    exact_fork_copy_cleanup: PASS
    both_repair_mirrors_cleared: PASS
    source_bytes_and_accounting_preserved: PASS
    subsequent_copy: PASS

### Other successor findings: closed in this bounded cross-review

- **VUN-CORRECTNESS-RESUME-03, High:** global maintenance now precedes bounded
  discovery of relevant active reservation scopes. Composite identities cover
  children before attempt binding; resolved attempt paths cover physical
  descendants. The helper and direct run/Batch deletion and archive restore
  acquire those scopes before mutation. Nested retained records also require
  configuration before deletion. Real prepared/pre-bind cases preserve original
  bytes, totals and child ownership, create no destructive marker, and allow
  retry after the upload completes.
- **VUN-CORRECTNESS-RESUME-04, Medium:** copy free-space admission includes all
  outstanding reserved bytes in addition to incoming allowance and the protected
  reserve. Its regression rejects before destination mutation.
- **OPS-COPY-01, Medium:** evidence synchronization includes linking ancestors
  through the configured root and retained recovery trees. Batch
  and Omni register newly created stale siblings after deferred cleanup. Tests
  exercise real directory fsync, ancestor order, retained stale bytes and exact
  accounting. Failure still exits before marker clearance.
- **Archive privacy follow-up:** sensitivity discovery includes nested private
  archives. A public archive checks every directory/file member before writing,
  so a late child upload aborts before retained content enters the public ZIP.
  The race regression verifies cleanup, unchanged original/receipt bytes and a
  successful private retry; the nested-private regression verifies ZIP readback.
- **SEC-ARCHIVE-GROWTH-01, Medium:** final `111dd982c` caps private ZIP output
  before every write using the current offset plus incoming byte count. The cap
  covers header rewrites, seeks and central-directory writes without double
  counting rewritten headers. It uses the existing admitted ZIP allowance;
  the separate receipt allowance, quotas and public archive behavior remain
  unchanged. `ExitStack` closes the ZIP before the bounded stream. Successful
  durable cleanup removes the temporary ZIP and releases its reservation.
  Four regressions cover exact-size success, central-directory overflow,
  seek/extent limits and real-ledger late child growth. Originals and exact
  source charges are preserved; successful cleanup leaves no ZIP/reservation.
- **Private archive cleanup fault follow-up:** final `467e9db1b` releases that
  reservation only after temporary removal and directory fsync succeed. Unlink
  or fsync failure keeps the reservation and records an incomplete receipt with
  the verified actor. Receipt-persistence failure is logged and also retains the
  reservation. Fault cases preserve originals and prove actual surviving bytes
  stay covered; existing reconciliation restores exact global/principal charges
  after unlink/fsync faults. Failed receipt persistence remains pending for the
  existing corrupt-receipt recovery path rather than freeing uncharged bytes.
- **Unreconciled source accounting:** final `f96483108` rejects explicit
  noncommitted receipt accounting during inventory and rejects a matching
  noncommitted Redis reservation before admission, repair-marker creation or
  copying. Existing maintenance/project ownership covers those checks. Legacy
  receipts without accounting fields and absent/pruned reservation records remain
  supported. Tests cover receipts marked pending and committed while their
  reservation remains noncommitted. Both reject, then copy successfully after
  actual reconciliation with exact source and copier principal charges.

The `cfd5329d4` ancestor extension initially compared a relative target parent
against the absolute configured root, skipping parent synchronization. This
review independently reproduced that residual. Revision `13feaac92` resolves the
parent before walking upward, and the regression covers both absolute and
relative destinations with two newly created parents. A direct final-source
real-fsync trace passed both ancestor coverage through the configured root and
child-before-parent ordering. This closes the last demonstrated path variant.

The unchanged reviewed controls include source provenance and copier attribution,
no speculative deletion credit, complete terminal-receipt inventory, source byte
verification, overlap/link refusal, borrowed-scope ownership, preserved owning
attempt roots, and existing fork access/ownership ordering. The canonical
contract's “Sharing, copies, and existing workspace resets” section records the
successor's descendant fencing, exact fork recovery and durability requirements.

### Evidence and independence

The reviewer read the production/test corrections through `f96483108`,
confirmed the isolated checkouts' Git HEADs, and passed the scoped
`git diff --check`. A frozen-source selection of the nine new regression test
functions exercised 15 parameterized cases: ancestor syncing, outstanding disk
reservations, actual Omni child upload, pre-bind child ownership, deferred
Batch/Omni stale paths, interrupted fork recovery, direct run/Batch deletion,
nested missing-identity refusal and parent archive restoration.

Result at `224184ecd`: **15 passed, 8 warnings, no skips, 119.14 seconds**.

The independent run used `wctl exec -w /tmp/vun-224184ecd`,
`PYTHONPATH=/tmp/vun-224184ecd`, `/opt/venv/bin/python -m pytest`,
`--basetemp=/tmp/vun-224-code-review-data -q --maxfail=1`. The integrator's
pre-freeze logs were also inspected: 50 helper/fork/OpenAPI tests passed in
`/tmp/vun-patch-check2.log`; 142 direct deletion/archive tests passed in
`/tmp/vun-active-descendant-validation.log`. Those preparatory totals are distinct
from this review's immutable-source run. The archive race suite's preparatory
log `/tmp/vun-archive-race-validation.log` records 91 passing tests. The
integrator reports 95 passing archive tests after the bounded-writer addition;
the security review independently matched those tested source hashes. The
integrator reports 98 archive tests passing after the cleanup-fault extension.
This review inspected the added bounded-writer and cleanup-fault cases without
rerunning broader tests. The copy-source reconciliation suite log
`/tmp/vun-copy-pending-green2.log` records **19 passed, 4 warnings, no skips**.
Final helper/copy/exact validation in `/tmp/vun-f964-delta.log` and earlier
receipts in `/tmp/vun-467-delta.log`, `/tmp/vun-111-delta.log`, and
`/tmp/vun-13f-focused.log` remain the integrator's runtime gates. The integrator
reports that the `224184ecd` broad baseline stopped after 7,966 passes and 205
skips at the Roads publication stale-hash gate; QA investigation remains separate
from this bounded source verdict. No full-suite PASS is inferred.

This reviewer excluded its own profile adapters/tests and earlier archive
remediation from independent approval; separate QA/security/operations reviews
cover them. The new successor archive descendant-scope and privacy amendments
were reviewed here. No production or test source was changed in this review.
Exact converter qualification, broader semantic artifact checks and production
parity retain their existing separate requirements.
