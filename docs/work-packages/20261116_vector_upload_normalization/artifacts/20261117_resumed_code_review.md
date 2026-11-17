# Resumed final code review

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
