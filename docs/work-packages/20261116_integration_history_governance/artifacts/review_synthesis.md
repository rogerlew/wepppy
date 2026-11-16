# Independent design review synthesis

**Date**: 2026-11-16 UTC
**Disposition**: Scaffold reviewed; implementation and remote enforcement pending.
**Authority**: User requested scaffolding and dispatched review, not policy rollout.

## Review Coverage

Three agents independently inspected Git/history, security/CI, and correctness/QA.
Each reconciled findings with the scaffold. Sources:
[history](history_review.md), [security](security_review.md),
[correctness](correctness_review.md). These are design findings and implementation
acceptance requirements, not implementation sign-off or independent GitHub approvals.

## Findings and Disposition

| Priority | Finding | Evidence / implication | Action in plan |
|---|---|---|---|
| High | Accepted local work can disappear while remote push remains fast-forward | Actual parent change from `4194fd43b` to `ff1740239`; remote never saw parser deletion | M1: fresh remote receipt; preserve local master; no integrated closure on local-only acceptance |
| High | Current master has no observed protection or rulesets | Read-only GitHub API responses; historical settings unknown | M3: exact proposal, always-reported required check, authorized enablement/readback |
| High | Common-image publication does not await exact-candidate governance success | Master push/manual publisher has registry write authority without eligibility dependency | M4: gate exact-SHA publication; inventory auxiliary/manual/deploy variants |
| High | Candidate-owned security checks can approve their own weakening | Design threat; no observed exploitation claimed | M3: compare policy against approved baseline and require explicit policy-change review |
| High | Worktree isolation alone does not prove tested source identity | wctl tests run in container `/workdir/wepppy` | M2: verify consumed checkout; serialize validation on current stack initially |
| High | A pre-rebase check is insufficient for all local ref rewrites | Reset/ref replacement and editable hooks remain alternatives | M1: test supported update paths and hook installation/bypass; preserve LFS hooks; distinguish accident prevention from hostile-actor control |
| Medium | Exact ancestry receipts conflict with squash/rebase; later revert retains ancestry | Source history identity differs from final tree behavior | D1 and M3: merge-preserving default; independent behavioral baseline |
| Medium | Worktrees share refs; task branches conflict with current root policy | Existing explicit branch restriction | D2: deliberate policy adoption plus one master integrator |
| Medium | Path-filtered CI cannot be a universal reported check | Existing shape workflow filters changed paths | M3: unconditional small governance result; scoped expensive tests as appropriate |
| Medium | Closure receipt can become self-referential or stale | Receipt commit cannot contain its own SHA; remote branch can move | D5/M1: subject commit separate from receipt; immutable observed target and explicit freshness/retry contract |

All findings are represented in the plan. None is closed as an implemented control.
Implementation reviews must verify the corresponding executable behavior and actual
configured environment before closing them.

## Recommendations and Operator Decisions

| ID | Recommendation | Decision needed |
|---|---|---|
| D1 | Preserve reviewed commits with merge commits initially; exact accepted-SHA ancestry is the smallest receipt model | Adopt merge-only integration, or fund an explicit squash/rebase mapping and final-tree revalidation model? |
| D2 | Explicitly authorize task branches/worktrees, one integration owner, and serialized validation on the current stack | Change current no-new-branch-without-request policy to allow scoped task branches? |
| D3 | PR-only master, no force-push/deletion, unique always-run required check, and narrowly recorded exceptional recovery | Is another human collaborator available for required approval? Who may use break-glass, and can routine agent credentials avoid that authority? |
| D4 | Trust baseline policy from the approved base, require explicit review to weaken it, and test actual parser behavior | Who approves policy retirement, especially if one owner controls rules, credentials, and merges? |
| D5 | Receipt after the accepted source commit, fresh remote observation, separate integration/validation/release states; gate registry publication on exact-candidate success | Select durable receipt retention/location and confirm whether unqualified image publication is prohibited or deliberately permitted and labeled |

Recommended ordering: implement receipt and local preservation first; prove the
small governance check and tested-checkout identity; then enable remote rules;
then finish publication wiring and recovery evidence. Do not enable a required
check before it can report reliably on every candidate.

A personal-account owner can ultimately change repository rules. The baseline
threat model is accidental loss and unreviewed weakening, not containment of that
owner. Agent reviews under one shared GitHub identity are not an independent
human approval boundary.

## Enforcement Canary and Evidence

Prepare the exact rules payload and export current settings. After authorization,
use a disposable branch outside publication triggers, copied rules, and the actual
routine writer identity to prove both rejection and valid PR integration. Do not
push deliberately broken master or publish a bad image. Read back effective master
rules after authorized activation and verify a legitimate integration there.
A canary on another branch alone is insufficient proof of master enforcement.

Local acceptance uses real disposable bare Git remotes and clones, not mocked Git
responses. Test original topology, dirty/untracked WIP preservation, concurrency,
stale/shallow/offline state, wrong target, later revert, wrong container checkout,
hook bypass, LFS coexistence, receipt interruption and retry. Retain exact candidate,
check identity, generated receipt, reader result, and rule readback.

## Remaining Work

Resolve D1–D5, promote the canonical contract, implement and test controls, enable
only the authorized remote configuration, and obtain independent implementation
reviews. No remote settings, hooks, branches, CI workflows, image publications,
or production deployments were changed by this scaffold.
