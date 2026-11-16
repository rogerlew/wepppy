# Incident evidence and consumer inventory

**Observed**: 2026-11-16 20:48 UTC. These are current/local observations, not a
historical GitHub audit log. Exact rebase argv and actor remain unproven.

## Observed history

- `4194fd43b` records issue 656 closure, descending from accepted Rust fix
  `a6be89141`. Local master reached it November 14 at 17:39 PST.
- `cd90ee1aa` added the soils change with parent `4194fd43b`.
- November 15 at 17:04:45 PST, local reflog records rebase onto `ff1740239`,
  replaying only soils as `7755822d7`, whose parent is `ff1740239`.
- The 20 commits in `19c0dc107..4194fd43b` were omitted. Local remote-tracking
  reflog records `ff1740239` then the push of `7755822d7` at 17:06:14 PST.
- `git diff --stat ff1740239 7755822d7` shows soils/docs changes, not parser
  deletion. The shape CI path filter therefore could not observe the local loss.
- Recovery merge `a5d9f0fc3` and integration repair `420e31b97` restore history;
  remote master was read back at `420e31b97e962dd6ea79694efe89f348c27ef83f`.
- GitHub REST `repos/rogerlew/wepppy/branches/master/protection` returned
  HTTP 404 with message `Branch not protected`; `repos/rogerlew/wepppy/rulesets`
  returned `[]`. This proves current observations only, not November 15 settings.

## Consumer and variant inventory

| Consumer / variant | Broken assumption or boundary | Disposition | Required evidence |
|---|---|---|---|
| Local shared master update | Rebase preserves all unrelated accepted work | Confirmed defect | Reproduce original topology using real Git; pre/post history and WIP comparison |
| Work-package and issue closure | Local accepted commit implies remote integration | Confirmed process gap | Receipt rejects unpushed accepted revision; separate completion states |
| Remote fast-forward acceptance | No force-push means no accepted work was lost | Confirmed insufficient control | Fast-forward scenario remains green remotely but fails local integration obligation |
| Path-filtered shape CI | Relevant deletion appears in remote diff | Confirmed blind spot | Always-reported baseline check on an unrelated-change candidate |
| Later explicit revert | Ancestry proves current behavior | Risk, not incident evidence | Reverted parser behavior fails baseline despite reachable accepted SHA |
| Concurrent sessions/worktrees | All tasks own the same mutable branch/worktree safely | Unverified exposure | Parallel disposable clones/worktrees; no cross-task WIP or ref loss |
| Common and auxiliary image publication | Push or artifact existence means release eligibility | Unverified exposure | Inventory every trigger and prove exact candidate/check binding |
| Deploy script and local bypass | Repository checks cover manual release paths | Unverified exposure | Inspect canonical deploy path and test bypass/rollback with no production mutation |
| Shallow clone/offline/stale refs | Local remote-tracking ref is fresh remote truth | Unverified exposure | Distinct unknown/error outcomes, no successful integration receipt |
| Admin/rules/check policy changes | Same candidate cannot disable its own gate | Unverified exposure | Trusted policy ownership and actual remote rejection tests |

Unverified exposure is an implementation investigation obligation, not a confirmed
finding. No blanket claim of other missing work or production rollback is made.
