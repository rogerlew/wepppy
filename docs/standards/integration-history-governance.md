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

Use commit-preserving integration, preferring merge commits. GitHub also accepts
a fast-forward of an already eligible PR head and records that PR as merged;
that preserves reviewed SHAs but does not require the merge-button/API transport.
Squash and rebase merges are
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

Initialize a new worktree index before staging. Run dependent shell operations
with fail-fast behavior and inspect the exact staged file list before committing;
`--no-checkout` alone leaves an index that can represent unintended deletions.

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
before starting pytest. Identify sparse checkouts through Git index/HEAD markers,
not only files present on disk; broken Git metadata must fail explicitly.
Serialize edits and validation on the existing shared stack;
worktree creation does not authorize recreating or remounting another task's stack.
Validation receipts identify the candidate and any dirty source state. Ignored build
outputs and external dependencies require their own artifact evidence.

## Remote integration boundary

Require PR-associated changes and always-reported integration governance checks
on master. Live canaries must distinguish an unassociated push from a green PR
head: GitHub rejects the former but can accept the latter as the PR merge.
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

## Operator commands

Install the local guard using `python3 tools/install_integration_hooks.py`; verify
it with `--check` before integration. Existing hook managers must integrate the
reference guard explicitly; the installer refuses to overwrite them. The installed
checker lives in the common hooks directory and uses `/usr/bin/python3 -I`
(Python 3.10 or newer), so removing a task worktree or its virtual environment
does not remove the guard. Upgrades require reviewing and backing up the owned
installed files before replacement; `--check` reports drift. A rejected
hard reset or rebase can already have changed index/worktree contents even though
the master ref is preserved. Stop after refusal, inspect preserved refs and WIP
backups, and recover deliberately. Never retry with the guard disabled.

Create a receipt after the accepted commit reaches the remote:

```bash
python3 tools/check_integration_history.py receipt --repo /workdir/wepppy \
  --remote origin --branch master --accepted FULL_ACCEPTED_SHA --output RECEIPT.json
python3 tools/check_integration_history.py verify --repo /workdir/wepppy \
  --remote origin --branch master --receipt RECEIPT.json
```

The required check names are `integration-governance` (behavior) and
`integration-governance-policy` (base-owned policy). A separate
`pull_request_target` workflow reads candidate Git objects as data and writes
its result on the exact PR head; it never runs candidate code. Public GitHub's
shared Actions app identity is not an isolation boundary against a determined
writer deliberately forging check names. Independent human review or a separately
controlled check provider is required to claim that stronger threat model.

For a deliberate policy change, obtain its digest with the base-owned
`tools/check_security_baseline.py policy --base FULL_BASE_SHA --candidate
FULL_CANDIDATE_SHA --digest-only`. After reviewing the exact diff, the operator
sets Actions variable `INTEGRATION_POLICY_APPROVAL` to `FULL_CANDIDATE_SHA:DIGEST`.
Approval is external to the candidate and does not transfer to another SHA. After
merge, authorize the merge SHA's policy transition and rerun its governance check
if the initial push check arrived before that approval. Publishing remains blocked
until the exact merge check succeeds. Record both transitions in the work package.

Initial bootstrap is special: the base has no checker or trusted workflow. Verify
the checker locally, set `INTEGRATION_GOVERNANCE_BOOTSTRAP_SHA256` to its reviewed
SHA-256, approve the initial exact candidate transition from recovery commit
`420e31b97e962dd6ea79694efe89f348c27ef83f`, and merge the reviewed bootstrap PR.
Only after the trusted workflow exists and the canary proves enforcement should
the two contexts become required. This one-time bootstrap does not authorize
ongoing direct pushes or a generalized missing-check fallback.

The existing deployment script now requires `tools/check_deployment_governance.py`
to pass before builds, worker suspension or activation. It rejects dirty/untracked
protected source and requires a successful exact-source master governance run.
Public GitHub read access suffices; an existing `GH_TOKEN` can increase API limits.
Unavailable or rate-limited evidence fails closed before activation. Existing
retained-image rollback and parser stop behavior remain separate safeguards.

GitHub documents this PR-association behavior in
[available repository rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#require-a-pull-request-before-merging).
The canary verified the effective classic protection directly; configuration alone
was not treated as proof of rejected operations.
