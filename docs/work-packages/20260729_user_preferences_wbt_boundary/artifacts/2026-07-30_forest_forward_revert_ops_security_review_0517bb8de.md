# SURF-14A Forest Forward-Revert Operations and Security Review

## Metadata

- **Reviewer**: independent operations/security control agent
- **Date**: 2026-07-30 UTC
- **Package**:
  `docs/work-packages/20260729_user_preferences_wbt_boundary/`
- **Prerelease commit**:
  `b1f1f99c8f808528315abce001a70200ab068bc7`
- **Reviewed release commit**:
  `363ab8ac391bdb2f2afee6284c7e297bd4efbfb1`
- **Reviewed forward-revert commit**:
  `0517bb8de9b0343a64ab4102f35f4ae242fffa53`
- **Recommended dedicated remote ref**:
  `refs/heads/rollback/surf14a-20260730-0517bb8de`
- **Forest, production, product-source, or remote-ref mutation by this
  reviewer**: none
- **Break-glass basis**: none requested or used

This is an additive immutable review artifact. It does not revise any earlier
SURF-14A contract, source, acceptance, governance, or operations/security
review.

## Verdict

**APPROVE — commit `0517bb8de9b0343a64ab4102f35f4ae242fffa53`
is the exact contract-compliant Forest application rollback target for release
`363ab8ac391bdb2f2afee6284c7e297bd4efbfb1`.**

There are no open High, Medium, or Low operations/security findings.

Publishing the commit under the dedicated remote ref above is approved only as
an explicit non-force full-SHA push followed by independent remote-SHA
verification. The ref does not yet exist on `origin`; this review did not
publish it. Forest apply remains blocked until that publication and
verification are recorded in preflight.

Use of the rollback target is conditional on the complete quiesce, queue
drain, worker stop, exact-HEAD, additive-schema preservation, coordinated
restart, and post-action controls below. This review does not authorize a
database downgrade, restore, product deployment, Forest mutation, or
production/wepp1 action by itself.

## Exact Commit and Tree Evidence

The commit graph is linear and has the exact contract-required shape:

```text
b1f1f99c8f808528315abce001a70200ab068bc7
  |
  v
363ab8ac391bdb2f2afee6284c7e297bd4efbfb1
  |
  v
0517bb8de9b0343a64ab4102f35f4ae242fffa53
```

- `363ab8ac3` has the sole parent `b1f1f99c8`.
- `0517bb8de` has the sole parent `363ab8ac3`.
- `git merge-base --is-ancestor` passes for both edges.
- `git rev-list --count 363ab8ac3..0517bb8de` returns exactly one, and the
  reverse count is zero.
- The release tree is
  `86c3ea98b72df348c66738c48c0662a83f2fc17b`.
- Both prerelease `b1f1f99c8` and forward revert `0517bb8de` have tree
  `23ce939ec91ba0c9927b89535f86bc331fb94889`.
- `git diff --exit-code b1f1f99c8^{tree} 0517bb8de^{tree}` returns success,
  including the submodule-aware comparison.
- Both equal trees contain 62,806 entries. The release and revert each affect
  the same 56 paths in opposite directions.

The forward revert therefore restores the complete prerelease source,
tests, generated RQ graph, documentation, and package tree without a checkout
of an ancestor and without history rewriting. From the exact release commit,
rollback is a one-commit fast-forward.

`origin/master` currently resolves to the exact release commit. No local or
remote branch contains the forward revert, and the recommended remote ref is
absent. The commit object is presently local-only and must be made reachable by
the dedicated ref before Forest apply.

The base, release, and revert commits are all unsigned. This is not a new
trust regression, but it means ref names and short SHAs are insufficient
evidence. Every publication, fetch, preflight, and Forest checkout must compare
the full 40-character object ID and the expected parent and tree IDs.

## Additive Schema Preservation

Application rollback must preserve Alembic revision `c91f6b2a4d7e` and the
`user_preferences` table. This is safe for the reviewed target:

- the migration blob is identical at the prerelease, release, and revert
  commits:
  `9e0707a2999e677d1e11d92ccda748b977795ad9`;
- the `wepppy/weppcloud/app.py` blob is also identical at all three commits:
  `c5613ca6d2eb03fb51eed8ab7bdf8ced13e14c5d`;
- all three trees therefore know revision `c91f6b2a4d7e`, model the
  `user_preferences` table, and use the same four named constraints; and
- the release commit did not change the migration or SQLAlchemy schema model.

Revision `c91f6b2a4d7e` is the reviewed merge revision over parents
`7b3c068e7a1d` and `b7d9c3e2f1a4`. Its upgrade creates only the additive
preference table. Its downgrade drops that table
(`wepppy/weppcloud/migrations/versions/c91f6b2a4d7e_add_user_preferences.py:13`,
`wepppy/weppcloud/migrations/versions/c91f6b2a4d7e_add_user_preferences.py:59`).

Consequently, application rollback must not run `flask db downgrade`, drop
the table, alter the Alembic revision, restore an older database, or delete
preference rows. The reverted application is schema-compatible with the
post-migration database. A destructive downgrade after rows exist still
requires a fresh validated backup, separate operator approval, and a new
review.

Before restarting reverted code, reassert:

- Alembic current revision is exactly `c91f6b2a4d7e`;
- `user_preferences` and all four named constraints remain present;
- the recorded User count is unchanged; and
- canary preference rows and associations are either restored to their exact
  preflight state or preserved for evidence if recovery is incomplete.

Any mismatch stops rollback with all changed services down. It does not
authorize schema repair by guesswork.

## Dedicated Remote Ref Publication

The branch name
`refs/heads/rollback/surf14a-20260730-0517bb8de` passes
`git check-ref-format`, is fetched by the repository's normal heads fetchspec,
contains no secret or environment-specific material, and is currently absent
locally and remotely.

Publishing it is safe only under this bounded sequence:

1. Reproduce the full release, revert, parent, and tree object IDs from a clean
   trusted checkout.
2. Prove the remote ref does not already exist. If it exists at any value,
   stop for review rather than overwrite it.
3. Push the full revert SHA to the full ref name without `--force`, a wildcard,
   or a moving local branch name.
4. Query the remote ref after publication and require its advertised value to
   equal the full revert SHA.
5. Fetch the ref into a clean local or disposable checkout and reverify its
   sole parent, tree equality to `b1f1f99c8`, and one-commit fast-forward from
   `363ab8ac3`.
6. Record the full ref and SHA in Forest preflight before any service or
   database mutation. Retain the ref through post-action dual review and the
   hardening observation window.

A suitable explicit push shape is:

```text
git push origin \
  0517bb8de9b0343a64ab4102f35f4ae242fffa53:\
refs/heads/rollback/surf14a-20260730-0517bb8de
```

This review approves that publication shape but did not execute it. The remote
branch must not be used as a moving deployment selector: Forest sets
`SURF14A_ROLLBACK_SHA` to the full commit ID, fetches the ref for reachability,
and verifies the exact SHA before merge and restart. Ref protection against
force-push and deletion should be enabled when available; full-SHA checks
remain mandatory even with protection.

Publishing the dedicated ref does not change `origin/master`, deploy Forest,
run code, alter a database, or broaden repository history. It only makes the
already-reviewed rollback commit durably fetchable.

## Forest Rollback Preconditions

The rollback is a contained application rollback, not an emergency checkout.
Before changing the bind-mounted Forest tree:

1. Confirm the current Forest checkout is clean and HEAD is exactly release
   `363ab8ac391bdb2f2afee6284c7e297bd4efbfb1`. Any additional commit, local
   edit, generated file, or untracked deployment artifact is a stop condition.
2. Preserve the fresh validated custom-format backup and its `PGDMP` and
   `pg_restore -l` verification receipt from apply. A restore remains
   operator-owned and is not authorized by this review.
3. Stop enqueue surfaces `weppcloud`, `rq-engine`, and `scheduler`.
4. Prove both `default` and `batch` queues have zero queued and zero executing
   jobs and every registered worker is idle.
5. Stop `rq-worker` and `rq-worker-batch` gracefully with the reviewed
   30-minute timeout.
6. From a one-off container, prove both queues still have zero queued and zero
   executing jobs and the post-stop worker registry contains zero workers.
7. Preserve logs, error IDs, RQ job/tail/registry state, exact canary receipts,
   and database evidence before intervention. If drain or reconciliation
   cannot complete exactly, leave services stopped and obtain operator
   direction; never discard work to make rollback proceed.
8. Fetch the dedicated ref, reverify its full SHA, parent, and tree, then run
   only `git merge --ff-only` to the full rollback SHA. Assert
   `git rev-parse HEAD` equals it.
9. Do not run Alembic downgrade. Reverify additive schema, constraints, User
   count, and exact canary cleanup state.
10. Restart `weppcloud`, `rq-engine`, `rq-worker`, and `rq-worker-batch`
    together on the exact rollback commit, then start `scheduler` afterwards.

These requirements implement the normative sequence in
`docs/work-packages/20260729_user_preferences_wbt_boundary/artifacts/2026-07-30_contract_decision.md:264`
and
`docs/work-packages/20260729_user_preferences_wbt_boundary/artifacts/2026-07-30_contract_amendment_delineation_snapshot.md:343`.

The ordering prevents old-signature workers from consuming new-signature jobs
and prevents mixed release/revert consumers from mutating shared run or Redis
state. `git checkout`, reset, force-push, queue purge, registry deletion,
schema downgrade, and partial-service restart are not equivalent substitutes.

## Abort, Recovery, and Post-Action Evidence

Abort with the five changed services stopped on any:

- current-HEAD, remote-ref, commit-parent, tree, or full-SHA mismatch;
- dirty Forest checkout or non-fast-forward merge;
- queued, executing, non-idle, or unregistered-but-active worker evidence;
- failed graceful stop or nonzero post-stop worker registry;
- missing/unvalidated backup receipt;
- Alembic revision, table, constraint, User-count, or canary-state mismatch;
- inability to retain the exact RQ, database, filesystem, and log evidence; or
- unhealthy coordinated restart.

After rollback, the durable post-action record must include the release SHA,
rollback ref and SHA, pre/post HEAD checks, queue and worker receipts, service
stop/start order, unchanged schema revision and User count, constraint checks,
canary cleanup/restoration evidence, health checks, and any error IDs or
recovery action. Redact credentials, cookies, tokens, and connection secrets.

The requesting operator owns any restore or destructive downgrade decision.
Production/wepp1 remains outside scope.

## Final Control Decision

The detached forward revert `0517bb8de` is approved as the exact Forest
application rollback target for release `363ab8ac3`. Its ancestry is linear,
its tree is exactly the prerelease tree, and its migration/model blobs support
preserving the additive post-release schema.

It is also approved for publication under the dedicated non-force remote ref
specified above, subject to full-SHA remote verification. Forest remains
untouched and blocked until the ref is durably reachable and every deployment
precondition in this artifact and the normative contract is satisfied.
