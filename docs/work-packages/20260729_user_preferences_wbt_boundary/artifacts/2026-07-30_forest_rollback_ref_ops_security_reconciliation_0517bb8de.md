# SURF-14A Forest Rollback Ref Operations/Security Reconciliation

## Metadata

- **Reviewer**: independent operations/security control agent
- **Date**: 2026-07-30 UTC
- **Release commit**:
  `363ab8ac391bdb2f2afee6284c7e297bd4efbfb1`
- **Rollback commit**:
  `0517bb8de9b0343a64ab4102f35f4ae242fffa53`
- **Reconciled remote ref**:
  `refs/heads/rollback/surf-14a-363ab8ac3-0517bb8de`
- **Forest, source, or remote mutation by this reviewer**: none

This additive artifact preserves both immutable forward-revert reviews. It
reconciles only the remote ref name; it does not alter their commit, tree,
schema, quiesce, rollback, or authority conclusions.

## Decision

**APPROVED — governance's exact ref
`refs/heads/rollback/surf-14a-363ab8ac3-0517bb8de` is also the
operations/security-approved publication ref for rollback commit
`0517bb8de9b0343a64ab4102f35f4ae242fffa53`.**

The ref passes `git check-ref-format`, encodes both the release and rollback
short SHAs, is covered by the normal remote heads fetchspec, and is currently
absent locally and on `origin`. Its name changes no object or rollback
semantics. The exact rollback parent and prerelease-tree equality were
reverified.

For one unambiguous operator target, this governance-selected name supersedes
the earlier recommended name
`refs/heads/rollback/surf14a-20260730-0517bb8de` for publication and Forest
preflight. The earlier artifact remains historically accurate and unchanged;
the alternate ref must not also be created.

All prior operations/security conditions remain mandatory:

- create the reconciled ref once using an explicit non-force push of the full
  rollback SHA, aborting if it exists at any other object;
- independently verify the remote ref resolves to the exact 40-character SHA
  and reverify its sole parent and tree after fetch;
- record the exact ref and full SHA before Forest mutation and never move the
  ref after publication;
- retain exact release-HEAD, clean-checkout, enqueue-stop, queue-drain,
  worker-idle, graceful worker-stop, and zero-registry gates;
- move to the rollback only by `git merge --ff-only`, then assert exact HEAD;
- preserve additive revision `c91f6b2a4d7e`, its table and constraints, and do
  not downgrade or restore without separate operator authority;
- restart the four changed services together before `scheduler`; and
- retain the rollback ref and redacted execution evidence through post-action
  dual review and the observation window.

Production/wepp1 remains outside scope. This reconciliation authorizes no
publication or deployment action by the reviewer.
