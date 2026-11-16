# History and integration control review

Date: 2026-11-16 (UTC). Reviewer: history_controls sub-agent.
Scope: evidence, proposed controls, and decision points; no controls installed,
Git state changed, or external records written by this reviewer.

## Evidence and confidence

The local reflog records `master` at `4194fd43b`, then soils commit `cd90ee1aa`
(parent `4194fd43b`), then a rebase at 2026-11-15 17:04:45 PST producing
`7755822d7` (parent `ff1740239`). The range `19c0dc107..4194fd43b` contains
20 commits. `ff1740239` merged `19c0dc107`, an earlier shape implementation;
it did not contain the later Rust work. The remote-tracking reflog records the
push of `7755822d7` after `ff1740239`. The remote-visible diff contains soils
code/tests and package documentation, with no shape-converter paths.

These facts establish the loss and the fast-forward blind spot. They do not
identify the exact rebase arguments, actor, reasoning, or historical GitHub
protection configuration. The current root instruction forbids creating or
switching to a new branch without explicit user direction. Current Git is
2.43.0; no configured `core.hooksPath`, `pull.rebase`, `pull.ff`, or
`rebase.updateRefs` was reported. Installed `pre-push` and `post-merge` hooks
invoke Git LFS; only a sample `pre-rebase` exists.

## Findings and recommendations

### H1 — High: remote fast-forward safety cannot preserve unpublished acceptance

A push comparing only old/new remote tips would accept the incident result.
Neither `--force-with-lease` nor a ban on force-pushes repairs this class of
failure. A local tip preserved only in a reflog remains vulnerable to later
expiry and cleanup.

Require distinct states: locally reviewed, remotely checkpointed, integrated,
and deployed. Allow local review completion without claiming integration.
Before an integrated/issue-resolved claim, a receipt must identify the repository,
remote branch, reviewed candidate SHA, newly fetched remote SHA, timestamp,
integration relationship, and validation evidence for the resulting tree.
Unreachable candidates, failed fetches, and shallow histories that prevent proof
must refuse the integration claim. Capture an immutable fetched object ID rather
than relying on a mutable `origin/master` name in subsequent checks.

For merge-preserving integration, require the reviewed candidate to be an
ancestor of the observed remote commit; Git documents distinct status codes for
non-ancestry and errors in [git-merge-base](https://git-scm.com/docs/git-merge-base).
Ancestry proves preservation of history, not preservation of behavior: merge
resolution and later reverts still require behavioral acceptance gates.

### H2 — High: local prevention needs a declared enforcement boundary

A policy sentence or `pull.ff=only` cannot prohibit an explicitly invoked
rebase/reset. A `pre-rebase` hook catches the normal rebase entry point but not
all ref rewrites. A local hook is an accident-prevention control, not a security
boundary against an agent that can disable hooks or edit the repository files.

Recommended small implementation: a guarded update/receipt command plus an
installed local hook that refuses non-fast-forward changes or deletion of
`refs/heads/master`. Evaluate the `reference-transaction` prepared phase on
supported Git versions in disposable repositories, including reset, rebase,
update-ref, branch deletion/recreation, and interrupted operations. Add a
pre-rebase refusal for early, clear feedback if needed. Never claim working-tree
atomicity merely because the ref update failed. Git documents these hook entry
points in [githooks](https://git-scm.com/docs/githooks).

Preserve existing Git LFS hooks when installing controls. Report missing or
misconfigured hooks through a preflight. Keep remote server enforcement as a
separate layer. Explicit emergency bypass must retain before/after SHAs,
reason, owner, backup ref, and requalification; routine agents should not receive
a generic self-authorized bypass flag.

### H3 — High: exact-SHA acceptance conflicts with squash/rebase integration

A legitimate squash or rebase creates new commit identities, so a universal
ancestor-of-original-SHA rule would reject supported integrations. Conversely,
accepting a PR's merged flag or a matching patch-id alone can hide changed merge
resolution or incomplete semantic integration.

Recommend merge-preserving integration for reviewed security work as the first
implementation. If squash/rebase must remain supported, explicitly map reviewed
candidate to the final integrated SHA and rerun the acceptance gates against
that tree. Record the merge method and required evidence in the receipt. Do not
silently substitute patch similarity for the stronger guarantee.

### M1 — Medium: concurrent-task isolation requires a policy decision

Separate worktrees isolate indexes and checked-out files, but share refs and
repository configuration; they do not alone prevent another actor rewriting
`master`. Root's current no-new-branch rule also conflicts with autonomous task
branches. Detached worktrees are a compatible interim option only if their
accepted tips are pinned and published; the working directory alone is not a
durable publication mechanism.

Recommend task branches/worktrees plus one serialized integration owner, after
explicitly revising the branch rule. If the user retains shared-master work,
require exclusive mutation ownership and preserve unrelated local commits.
Exercise concurrent fetch and changed-remote-tip cases, not only single-process
happy paths.

## Decision points

1. Adopt merge-preserving integration for reviewed/security work, or fund and
   specify the stronger squash/rebase mapping and revalidation path?
2. Authorize automatic task branch/worktree creation, replacing the existing
   per-task permission rule, or retain detached worktrees with pinned checkpoints?
3. Is local accidental-loss prevention the intended guarantee? Stronger hostile
   agent enforcement requires a separately controlled credential/execution
   boundary and exceeds a hook-only implementation.
4. Who owns emergency bypass, and where are bypass and integration receipts
   retained? Recommend repository-owned receipts tied to immutable remote SHAs,
   with externally enforced protection for their acceptance path.

## Required acceptance cases

Use real disposable Git repositories and remotes. Reconstruct the exact incident:
remote contains the earlier shape tip, local contains 20 accepted successors,
and an unrelated commit is replayed alone onto remote. Show that the proposed
control rejects the loss or refuses closure, despite a fast-forward push.
Also prove valid fast-forward and merge integration; stale/offline/shallow
remote observation; merge conflict resolution changing accepted behavior;
permitted squash/rebase policy; concurrent remote movement; protected-ref
rewrite/deletion; hook installation alongside Git LFS; missing-hook detection;
and preservation of unrelated dirty/untracked work.

The smallest useful first milestone is receipt-based integration claims plus
protected local-master updates. Neither needs a new service or database. Server
rules and semantic baseline gates remain necessary complementary controls.

## Scaffold reconciliation

Reviewed `package.md`, `tracker.md`, and `artifacts/incident_and_consumers.md`
after their creation. The scaffold correctly reports controls as unimplemented
and decisions as unratified. The findings above describe failure modes and
implementation gates, not a claim that the scaffold omitted all these requirements.

| Finding | Design disposition | Remaining gate |
|---|---|---|
| H1 | Covered by distinct completion states, remote receipts, and real-Git incident reproduction | Specify immutable observation/receipt fields; implement writer and reader; prove refusal on unknown/stale/offline history |
| H2 | Covered by protected local-master objective and explicit hook limitations | Select supported Git enforcement entry points; test reset/rebase/ref deletion, LFS coexistence, installation failure, and bypass |
| H3 | Explicitly captured by D1 | Ratify merge-preserving default or specify mapping and revalidation for squash/rebase |
| M1 | Explicitly captured by D2 | Ratify task-branch authority and define serialized integration ownership |

No additional substantive scope omission was found in these three scaffold
files. Two details should become explicit acceptance requirements in the ExecPlan:
retain existing Git LFS hook behavior when installing guards, and serialize the
shared-master integration writer even when contributors use separate worktrees.
These are implementation-design requirements within the proposed scope, not new
infrastructure requests. The active ExecPlan was not yet available for this
reconciliation. Implementation and environmental enforcement remain unreviewed.
