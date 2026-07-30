# SURF-14A Forest Forward-Revert Governance Review

## Metadata

- **Reviewer**: independent governance control agent
- **Date**: 2026-07-30 UTC
- **Package**:
  `docs/work-packages/20260729_user_preferences_wbt_boundary/`
- **Review boundary**: detached commit
  `0517bb8de9b0343a64ab4102f35f4ae242fffa53` solely as the
  pre-reviewed Forest application-rollback target for release
  `363ab8ac391bdb2f2afee6284c7e297bd4efbfb1`
- **Forest, database, service, ref, or product-source mutation by this
  reviewer**: none

## Verdict

**APPROVE — scope-limited to publication as a new dedicated remote rollback
ref and to the accepted nondestructive Forest application-rollback path.**

The reviewed commit is a valid forward revert: it is the direct child of the
release commit, and its complete tree is byte-for-byte the prerelease tree at
`b1f1f99c8f808528315abce001a70200ab068bc7`. It is safe to publish at the new
dedicated ref
`refs/heads/rollback/surf-14a-363ab8ac3-0517bb8de`, provided the publication
is a non-force creation and the remote ref is verified to resolve to the exact
40-character rollback commit.

**Unresolved findings**: 0 High, 0 Medium, 0 Low.

This approval does not authorize deployment, a move of `master`, a force
update, Forest access, a database restore, an Alembic downgrade, a table drop,
or production/wepp1 action. No break-glass basis was requested or used.

## Immutable Commit Evidence

| Object | Commit | Parent | Tree |
| --- | --- | --- | --- |
| Prerelease | `b1f1f99c8f808528315abce001a70200ab068bc7` | `4e5845a04c5b4808d78f4c4806db24e5b90ff70f` | `23ce939ec91ba0c9927b89535f86bc331fb94889` |
| Release | `363ab8ac391bdb2f2afee6284c7e297bd4efbfb1` | `b1f1f99c8f808528315abce001a70200ab068bc7` | `86c3ea98b72df348c66738c48c0662a83f2fc17b` |
| Forward revert | `0517bb8de9b0343a64ab4102f35f4ae242fffa53` | `363ab8ac391bdb2f2afee6284c7e297bd4efbfb1` | `23ce939ec91ba0c9927b89535f86bc331fb94889` |

The following independent Git checks passed:

- the rollback object's type is `commit`, and connectivity validation passed;
- `git merge-base --is-ancestor <release> <rollback>` returned success;
- the rollback parent is exactly the release, so the accepted
  release-to-rollback move is a fast-forward;
- the prerelease and rollback tree object IDs are identical;
- `git diff --quiet <prerelease> <rollback>` returned success with no changed
  path; and
- neither a local branch nor a remote branch already names the reviewed
  rollback object. The proposed dedicated remote ref was absent when checked.

The rollback commit is not signed (`%G? = N`). This does not change its Git
object identity. Publication must therefore preserve the exact reviewed
40-character object ID and retain the authenticated push/ref audit trail.

## Migration and Schema Boundary

The forward revert does not change migration source. The complete
`wepppy/weppcloud/migrations/` tree and
`tests/weppcloud/test_user_preferences_migration.py` are identical between the
release and rollback commits. In particular,
`c91f6b2a4d7e_add_user_preferences.py` has blob
`9e0707a2999e677d1e11d92ccda748b977795ad9` in the prerelease, release, and
rollback commits.

Creating the remote ref executes no application or migration code. The
accepted Forest application rollback checks out reviewed old application code
only after quiesce/drain/stop controls and contains no migration command. The
additive `user_preferences` table remains in place. An Alembic downgrade,
database restore, table removal, or other schema mutation requires separate
reviewed operator authority and is outside this approval.

## Publication and Use Conditions

1. Create only
   `refs/heads/rollback/surf-14a-363ab8ac3-0517bb8de` by a non-force push of
   `0517bb8de9b0343a64ab4102f35f4ae242fffa53`; abort if that ref exists at any
   different object.
2. After publication, verify the remote ref resolves to that exact full object
   ID and record the result in the Forest preflight evidence.
3. Do not move the rollback ref after publication. Any replacement requires a
   new review and a new ref.
4. Use the ref only after a contracted Forest rollback trigger. Repeat the
   enqueue-stop, queue-drain, worker-idle, graceful worker-stop, and
   zero-registry checks before moving the bind-mounted tree.
5. Set the recorded `SURF14A_ROLLBACK_SHA` to the full reviewed object ID,
   fast-forward to it, and assert `git rev-parse HEAD` equals it before
   restarting `weppcloud`, `rq-engine`, `rq-worker`, and `rq-worker-batch`
   together, followed by `scheduler`.
6. Never run rollback workers against queued or executing release-signature
   jobs. Preserve Redis, job, service, and rollback evidence for post-action
   review.
7. Preserve the additive table. Do not run `flask db downgrade`, restore a
   database, delete rows, or drop schema under this approval.

## Review Notes

The release-to-revert patch restores two preexisting trailing-whitespace
lines in `wepppy/rq/project_rq.py`. This is not a rollback defect: changing
them would violate the required exact prerelease tree. The exact
prerelease-to-revert diff is empty.

The detached object currently has no branch retention. Timely publication to
the dedicated immutable ref is therefore appropriate to prevent accidental
loss while preserving separation from the release branch. Publication alone
does not authorize Forest execution. Post-action review and the package's
recorded rollback evidence remain mandatory.
