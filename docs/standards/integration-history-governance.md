# Integration and history preservation

## Authority and threat model

The operator authorized execution of the integration-history work package on
2026-11-16. This standard adopts its recommended defaults. It prevents accidental
loss of accepted work and makes weakening security controls explicit; it cannot
contain the repository owner or an agent holding credentials that can change rules.
Agent design reviews are not independent human GitHub approvals.

## Completion states and receipts

Report local acceptance, remote integration, validated integration, publication,
and deployment separately. A successful local test or issue closure is not remote
integration. Before claiming integration, freshly fetch the explicit repository and
branch and prove the accepted source commit is an ancestor of the observed remote
commit. Record the complete SHAs, repository/branch, UTC observation time, and
validation evidence. Missing objects, offline access, shallow ambiguity, stale refs,
or unsupported integration modes must fail explicitly.

Use merge commits to preserve reviewed source SHAs. Squash and rebase merges are
not supported by the initial receipt contract. Commit ancestry proves historical
inclusion, not current behavior: a later revert must still pass security-baseline
validation. Receipts describe an immutable observation, not a guarantee that the
remote remains unchanged forever. Require an expected remote SHA when a consumer
needs a specific snapshot. Store receipts after their subject commit, outside the
commit they identify, under the work package's artifacts in a subsequent audit
commit or retained CI artifact. Keep receipts for the lifetime of the integration
record; do not silently overwrite an existing receipt on retry.

## Task ownership and shared master

Authorized repository work may use a task branch and worktree without a separate
branch-creation question. One designated integrator writes shared master. Task
worktrees share Git refs and are not independent repositories. Routine shared-master
rebase, reset, deletion and ref replacement are prohibited. Fast-forward updates
and merges must retain all previously accepted ancestors. Divergence is a merge
and review obligation, not permission to discard local history.

Use the installed local protected-ref guard as accident prevention. Check its
installation before integration and preserve existing Git LFS hooks. A hook can
be disabled by someone controlling the checkout, so remote checks and truthful
closure receipts remain required. Recovery must preserve refs, tracked WIP and
untracked files before any exceptional operation. Never clean or reset another
task's checkout. Record the actor, reason, old/new SHAs and recovery evidence for
exceptions; do not add a routine bypass environment variable.

This package began in a shared dirty checkout. Its bootstrap uses one task branch
there without removing unrelated WIP; disjoint agent edits belong to that one task.
Subsequent tasks should use separate worktrees. The root integrator owns all commits
and index changes during this execution.

## Validation identity

Run tests against the checkout actually consumed by the container, not just the
host shell's current directory. wctl must reject a mismatched requested checkout
before starting pytest. Serialize edits and validation on the existing shared stack;
worktree creation does not authorize recreating or remounting another task's stack.
Validation receipts identify the candidate and any dirty source state. Ignored build
outputs and external dependencies require their own artifact evidence.

## Remote integration boundary

Require pull requests and an always-reported integration-governance check on master.
Disallow force pushes, branch deletion, squash and rebase integration. Enforce the
rule for administrators too. Initial required human approval count is zero: write
collaborators exist, but no second human has been assigned to this workflow. The
operator can later assign reviewers and raise this count; automated agents sharing
one identity do not satisfy independent human review.

The owner retains explicit break-glass ability to change repository settings. There
is no routine bypass actor in the rule. Before exceptional changes export effective
settings, document the reason and exact revision, then restore and read back rules.
Require the check to exist and succeed on a candidate before enabling it as required.
Canary rules use a disposable branch outside image-publishing triggers; prove both
rejection and valid integration using the real routine identity. Read back master
rules and verify a legitimate integration after enablement.

## Trusted baseline and release

Security policy is read from an approved base, not silently replaced by candidate
policy. Changes to protected parser, checker or workflow surfaces require explicit
owner authorization bound to the exact candidate SHA and policy digest. Store that
approval outside the candidate in repository configuration; it is not independent
review when the owner and automation share credentials. Behavioral checks remain
necessary, including valid conversion, malformed input and quota rejection.

Publish common or auxiliary images only after governance succeeds for the exact
source revision, including manual dispatch. Missing, canceled, stale or wrong-source
results must fail closed before registry writes. The canonical deploy workflow
must retain parser provenance/readiness and fail-closed rollback controls; no
parallel deployment mechanism is authorized. Baseline retirement is an explicit
reviewed policy change, not an impossible-to-update frozen implementation.

## Validation and incident recovery

Test with real disposable Git repositories: the original local-loss/remote-fast-forward
incident, merge-preserving success, stale/offline/shallow states, concurrent movement,
wrong remote, dirty/untracked WIP, hook absence/bypass, LFS coexistence and interrupted
receipt writes. Test a later revert despite preserved ancestry, same-change removal
of implementation and gate, wrong container checkout, and publication before eligibility.

Retain exact rule exports, source/check identities, receipts, readback, and failure
results. Observation covers the first five subsequent integrations plus a recovery
drill; do not manufacture five empty changes to claim operational evidence. Mark
implementation complete separately from this observation period.
