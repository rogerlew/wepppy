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

## Implementation dispositions — 2026-11-16

The table above records the initial investigation, not unresolved implementation
status. The executed dispositions are:

| Consumer | Implemented boundary and evidence | Remaining scope |
|---|---|---|
| Shared master and false closure | Stable local ref guard; fresh exact-SHA receipt; 22 real-Git tests reproduce the 20-commit omission and reject false integration | Hook adoption on other checkouts; hooks cannot contain their owner or undo prior index/worktree mutation |
| Work-package and issue closure | Canonical state definitions, closure template and remote receipt | Issue messaging/closure is separately authorized; no automatic issue changes |
| Remote fast-forward | Protected PR association plus required checks; original accepted source retained in PR #661 merge | GitHub permits eligible PR-head fast-forward transport; no claim of merge-button-only enforcement |
| Path-filtered baseline and later revert | Always-reported behavior and trusted base-owned policy checks; real Rust smoke and policy/revert fixtures | Initial security baseline is shape-converter, not every subsystem |
| Concurrent worktrees | One integrator, isolated task branches, sanitized live-container nonce and sparse-tree detection | Shared ref namespace and stack remain; no independent stack per task |
| Common/auxiliary publication | Exact SHA and latest successful master-push governance run required before registry-write job, including dispatch | Common-image live publication observed; auxiliary path validated by workflow/eligibility tests, no auxiliary publication invoked |
| Deployment | Canonical entry point rejects dirty protected inputs and missing exact-source eligibility before build/activation | No production deployment; retained existing runtime/parity gates still apply |
| Shallow/offline/stale refs | Isolated fresh fetch, immutable observation, explicit errors and no-clobber receipts | Receipt is a historical snapshot, not a permanent assertion about a moving branch |
| Admin/check policy changes | Both checks bound to Actions app15368; external exact candidate/digest approval; negative live canary rejected | Owner settings changes and deliberate same-app check forgery are outside the accidental-loss threat model |

See [execution evidence](20261116_execution.md) and the three independent
implementation reviews for validation identities. The separate disposable
recovery drill passed; five real integrations remain the operational observation
requirement.
